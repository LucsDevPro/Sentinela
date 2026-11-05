# -*- coding: utf-8 -*-
"""Detecção automática de férias, atestado e chuva (13b) e ausências sem abono.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import json
from datetime import date, datetime, timedelta
import pandas as pd
from .parametros import CRONOGRAMA_AUSENCIAS, _motivo_neutro
from .pontos import AVISO_AFASTAMENTO_PERIODO_MAX_DIAS, CONFIRMAR_CHUVA_AUTOMATICAMENTE, CONFIRMAR_FERIAS_AUTOMATICAMENTE
from .auxiliares import _obter_motivo_cronograma

log = logging.getLogger("evisita")


# --- 13b) DETECÇÃO AUTOMÁTICA DE FÉRIAS/ATESTADO E CHUVA -------------------
# A detecção roda em DUAS ETAPAS SEPARADAS, nessa ordem obrigatória:
#
#   1) FÉRIAS/ATESTADO — por agente. Regras, nessa ordem:
#        a) Menos de LIMITE_DIAS_UTEIS_FERIAS (7) dias ÚTEIS consecutivos
#           sem lançamento (ignora sábado, domingo e feriados em
#           FERIADOS_NACIONAIS) = só "ausência" pontual (falta/folga/
#           atestado) — não vira evento nenhum, fica de fora.
#        b) >= 7 dias úteis = candidato a férias. Nenhuma OCORRÊNCIA passa
#           de LIMITE_DIAS_CORRIDOS_OCORRENCIA (30) dias CORRIDOS — uma
#           ausência mais longa que isso é dividida em várias ocorrências
#           consecutivas de até 30 dias cada (ver _dividir_em_ocorrencias),
#           pra nunca virar um período gigante sem fim visível.
#        c) Cada ocorrência NOVA entra como PENDENTE (CONFIRMAR_FERIAS_AUTOMATICAMENTE
#           = False, desde 02/11/2026): continua contando como Turno sem
#           Lançamento até a coordenação confirmar férias/atestado (validar.html
#           ou deteccao_editor.html). Com a flag em True volta o modo antigo
#           (confirmada sozinha). Exceções que não dependem da flag: ocorrência
#           com mais de 30 dias ou de agente sem abono automático entra como
#           "falta". Quando a ocorrência SOBREPÕE a de outro agente da mesma
#           equipe, fica marcada com "revisao_classificacao_necessaria" — não
#           muda o cálculo, é só um sinalizador pro supervisor conferir se é
#           coincidência de duas férias ou uma paralisação coletiva que a
#           etapa 2 (chuva) não pegou por não ter sido a equipe INTEIRA parada.
#
#   2) CHUVA — por EQUIPE, dia a dia, só entre os agentes ATIVOS daquele dia
#      (isto é, depois de EXCLUIR quem já está em Férias/Atestado confirmado
#      nesse dia, etapa 1). Se todos os agentes ativos de uma equipe
#      ficaram sem lançamento no mesmo dia útil, esse dia é CHUVA para
#      aquela equipe — entra como PENDENTE (CONFIRMAR_CHUVA_AUTOMATICAMENTE =
#      False, desde 02/11/2026): até a coordenação escolher o motivo (chuva,
#      reunião, capacitação...) vale a regra de Possível Evento por turno.
#      Com a flag em True volta o modo antigo (confirmada sozinha como Chuva).
#      Dias consecutivos com o mesmo padrão viram um único evento. A escolha
#      do "categoria_coletiva" (em data/deteccoes_pendentes.json, via
#      deteccao_editor.html ou validar.html) fica protegida e não é
#      sobrescrita nas próximas coletas.
#
# NADA disso muda cálculo nenhum sozinho até ser gravado em
# data/deteccoes_pendentes.json — só QUANDO CONFIRMADO o período entra no
# mesmo mecanismo do cronograma (e aí sim some da aba Ausências e da
# pontuação — ver _cronograma_efetivo() logo abaixo). Com as flags
# CONFIRMAR_*_AUTOMATICAMENTE em False (padrão atual), isso só acontece
# depois da confirmação da coordenação; "pendente" não entra no cálculo como
# ausência abonada. A marcação de "revisao_classificacao_necessaria" acima é
# só informativa.
LIMITE_DIAS_UTEIS_FERIAS = 7

# Nenhuma OCORRÊNCIA de férias/atestado passa disso, em dias CORRIDOS (não
# úteis) — uma ausência mais longa é dividida em várias ocorrências
# consecutivas de até esse tamanho cada (ver _dividir_em_ocorrencias()).
LIMITE_DIAS_CORRIDOS_OCORRENCIA = 30

# Quantos dias de folga uma detecção pode variar (início/fim recalculados
# um pouco pra frente/trás) entre duas coletas sucessivas e AINDA ser
# tratada como "a mesma" ausência/chuva (funde e atualiza) em vez de virar
# um evento duplicado do lado do antigo — ver _periodos_se_tocam(). Trade-off:
# valor MAIOR funde mais fácil (menos risco de duplicata por causa de
# lançamento atrasado aparecendo depois, mas mais risco de juntar sem
# querer duas ausências de fato diferentes que só calharam de ficar
# próximas). Valor MENOR é o oposto. 3 dias já resolveu os casos reais
# vistos até agora (lançamento atrasado costuma aparecer 1-2 dias depois);
# se um dia aparecer fusão errada de duas ausências realmente distintas,
# é aqui que se ajusta pra baixo.
TOLERANCIA_DIAS_MESMO_EVENTO = 3

# Equipes que NÃO passam pela detecção automática de férias/chuva — times
# com dinâmica diferente do resto, onde faz mais sentido cadastrar
# férias/ausências na mão em data/cronograma_ausencias.json do que confiar
# na detecção automática:
#   - "Equipe Bloqueio": time pequeno, atividade sazonal, entra e sai da
#     rotina normal.
#   - "Ponto Estratégico": ciclo/semana próprios, bem diferentes do
#     tratamento normal (ver AGENTES_PONTO_ESTRATEGICO) — férias/atestado
#     desse grupo são sempre informadas manualmente, nunca por ausência de
#     lançamento.
# Comparação sem diferenciar maiúsculas/minúsculas.
EQUIPES_SEM_DETECCAO_AUTOMATICA = ["Equipe Bloqueio", "Ponto Estratégico"]

# Feriados NACIONAIS (dia útil que não é dia de trabalho) — formato "dd/mm/aaaa".
# Cobrem 2026 e 2027. Ficaram de fora os "pontos facultativos" (Carnaval,
# Corpus Christi, Quarta-feira de Cinzas) e os feriados que caem em sábado/
# domingo não fazem diferença na conta. Feriado estadual/municipal NÃO está
# aqui: acrescente na lista se a equipe também não trabalha nele.
FERIADOS_NACIONAIS = [
    # 2026
    "01/01/2026",  # Confraternização Universal
    "03/04/2026",  # Sexta-feira Santa
    "21/04/2026",  # Tiradentes
    "01/05/2026",  # Dia do Trabalho
    "07/09/2026",  # Independência do Brasil
    "12/10/2026",  # Nossa Senhora Aparecida
    "02/11/2026",  # Finados
    "15/11/2026",  # Proclamação da República (domingo)
    "20/11/2026",  # Consciência Negra
    "25/12/2026",  # Natal
    # 2027
    "01/01/2027",  # Confraternização Universal
    "26/03/2027",  # Sexta-feira Santa
    "21/04/2027",  # Tiradentes
    "01/05/2027",  # Dia do Trabalho (sábado)
    "07/09/2027",  # Independência do Brasil
    "12/10/2027",  # Nossa Senhora Aparecida
    "02/11/2027",  # Finados
    "15/11/2027",  # Proclamação da República
    "20/11/2027",  # Consciência Negra (sábado)
    "25/12/2027",  # Natal (sábado)
]

# A PARTIR DE QUANDO a lista vale: só feriados desta data em diante entram na
# contagem de dias úteis (cálculo antigo, ranking novo e detecção de férias).
# None = valem em todos os meses do programa (Julho/2026 em diante). Pra
# começar a valer só a partir de uma data, coloque a data.
FERIADOS_VALEM_A_PARTIR_DE = None

def _feriados_em_vigor():
    """Feriados de FERIADOS_NACIONAIS que valem na contagem (>= FERIADOS_VALEM_A_PARTIR_DE)."""
    if FERIADOS_VALEM_A_PARTIR_DE is None:
        return list(FERIADOS_NACIONAIS)
    return [f for f in FERIADOS_NACIONAIS
            if datetime.strptime(f, "%d/%m/%Y").date() >= FERIADOS_VALEM_A_PARTIR_DE]

_FERIADOS_PADRAO = _feriados_em_vigor()

CATEGORIAS_PARALISACAO_COLETIVA = ["Chuva", "Capacitação", "Reunião/atividade coletiva", "Outra atividade coletiva"]


def _dias_uteis_no_intervalo(data_min, data_max, feriados=_FERIADOS_PADRAO):
    """Lista, em ordem, todo dia ÚTIL (seg-sex, fora feriados) entre
    data_min e data_max (objetos date, inclusive nas duas pontas)."""
    feriados_set = {pd.to_datetime(f, format="%d/%m/%Y", errors="coerce").date() for f in feriados}
    dias, d = [], data_min
    while d <= data_max:
        if d.weekday() < 5 and d not in feriados_set:  # 0=segunda ... 4=sexta
            dias.append(d)
        d += timedelta(days=1)
    return dias


def _dias_uteis_do_mes_civil(data_ref, feriados=_FERIADOS_PADRAO):
    """Lista (não só a contagem) dos dias úteis do MÊS CIVIL INTEIRO (dia 1
    ao último dia) que contém `data_ref` — usada por _dias_uteis_mes_civil
    (só a contagem) e por _preparar_ranking (que precisa dos dias em si,
    pra descontar chuva/capacitação/reunião do alvo por equipe)."""
    primeiro_dia = data_ref.replace(day=1)
    if data_ref.month == 12:
        ultimo_dia = data_ref.replace(day=31)
    else:
        ultimo_dia = data_ref.replace(month=data_ref.month + 1, day=1) - timedelta(days=1)
    return _dias_uteis_no_intervalo(primeiro_dia, ultimo_dia, feriados)


def _dias_uteis_alvo_periodo(data_min, data_max, feriados=_FERIADOS_PADRAO):
    """Devolve a lista de dias úteis que serve de ALVO ("1 mês de
    calibração") pro fator de normalização — o critério muda dependendo do
    tipo de período:

    - Período dentro de 1 ÚNICO mês civil (ex.: mês corrente em andamento):
      ALVO = dias úteis JÁ PASSADOS nesse mês, do dia 1 até data_max — NÃO
      o mês inteiro. Se hoje é o 14º dia útil do mês, o alvo é 14, não 21
      — porque o mês ainda não fechou, comparar com o mês inteiro infla o
      fator de todo mundo artificialmente enquanto o período está no meio.

    - Período cobrindo VÁRIOS meses (ex.: Acumulado): ALVO continua sendo o
      mês civil INTEIRO mais recente do período (não os dias decorridos do
      período todo) — aqui o objetivo é o oposto: escalar pra baixo um
      período longo pra caber na calibração de "1 mês" (ver docstring de
      calcular_pontuacao). Se usássemos dias decorridos do período INTEIRO
      (que pode somar 80+ dias), o fator viraria sempre ~1 e o problema
      original de pontuação despencando em períodos longos voltaria.
    """
    if data_min is not None and (data_min.year, data_min.month) == (data_max.year, data_max.month):
        primeiro_dia = data_max.replace(day=1)
        return _dias_uteis_no_intervalo(primeiro_dia, data_max, feriados)
    # Período de tamanho "mensal" que atravessa a virada de mês (ex.: Setembro
    # = 31/08 a 02/10, pois a semana 326 termina em 03/10): o alvo é o mês
    # civil onde cai a MAIORIA dos dias úteis do período (Setembro), e não o do
    # último dia (Outubro, que dava 22 dias úteis pra um mês de 21). Períodos
    # longos (Acumulado) continuam usando o mês do último dia, como sempre.
    if data_min is not None and (data_max - data_min).days <= AVISO_AFASTAMENTO_PERIODO_MAX_DIAS:
        por_mes = {}
        for d in _dias_uteis_no_intervalo(data_min, data_max, feriados):
            por_mes[(d.year, d.month)] = por_mes.get((d.year, d.month), 0) + 1
        if por_mes:
            ano, mes = max(por_mes, key=lambda k: (por_mes[k], k))
            return _dias_uteis_do_mes_civil(date(ano, mes, 1), feriados)
    return _dias_uteis_do_mes_civil(data_max, feriados)


def _dias_uteis_mes_civil(data_ref, feriados=_FERIADOS_PADRAO):
    """Nº de dias úteis do MÊS CIVIL INTEIRO (dia 1 ao último dia) que contém
    `data_ref` — não é o número de dias já passados, é o mês completo,
    então serve como referência estável de "1 mês de calibração" mesmo com
    o mês ainda em andamento. Usado por calcular_pontuacao() no lugar de um
    número fixo tipo 22, porque nem todo mês tem a mesma quantidade de dias
    úteis (feriados, fins de semana caindo diferente)."""
    return len(_dias_uteis_do_mes_civil(data_ref, feriados))


def _dias_paralisacao_coletiva_no_mes(id_agente, equipe, dias_do_mes, lista_cronograma):
    """Quantos dias, dentre `dias_do_mes` (dias úteis do mês civil), foram
    paralisação COLETIVA da equipe do agente (Chuva/Capacitação/Reunião/
    Outra atividade coletiva — ver CATEGORIAS_PARALISACAO_COLETIVA) —
    NÃO conta férias/atestado individuais aqui, porque essas já são
    tratadas à parte (excluídas de dias_trabalhados/qtd_ausencias, sem
    precisar encolher o alvo do mês pra isso). Usada por _preparar_ranking
    pra tirar do alvo de normalização os dias em que NINGUÉM da equipe
    tinha como trabalhar mesmo — não é justo cobrar esses dias de ninguém,
    nem "inflando" o fator de quem não pôde trabalhar por causa deles."""
    total = 0
    for dia in dias_do_mes:
        motivo = _obter_motivo_cronograma(id_agente, equipe, dia, lista_cronograma)
        if motivo and any(cat.lower() in motivo.lower() for cat in CATEGORIAS_PARALISACAO_COLETIVA):
            total += 1
    return total


def _runs_consecutivos_uteis(dias_uteis, faltando_set):
    """dias_uteis: lista ordenada de dias úteis do período. faltando_set:
    subconjunto sem lançamento. Retorna (dia_inicio, dia_fim, duracao) pra
    cada sequência MÁXIMA consecutiva DENTRO da ordem de dias_uteis — ou
    seja, um fim de semana ou feriado no meio não quebra a sequência, mas um
    dia ÚTIL com lançamento quebra."""
    runs, atual = [], []
    for d in dias_uteis:
        if d in faltando_set:
            atual.append(d)
        else:
            if atual:
                runs.append((atual[0], atual[-1], len(atual)))
            atual = []
    if atual:
        runs.append((atual[0], atual[-1], len(atual)))
    return runs


def detectar_ausencias_e_paralisacoes(df_total, resultados):
    """Ponto de entrada da detecção — roda em cima do df_total/resultados já
    consolidados (mesma coisa usada pra gerar o Excel). Retorna uma lista de
    eventos candidatos (ainda sem status; quem decide status é
    atualizar_deteccoes_pendentes(), que faz o merge com o que já existia).

    Roda em DUAS ETAPAS, nessa ordem (ver comentário da seção 13b acima):
      1) _detectar_ferias_individuais() — por agente, isolado dos demais.
      2) _detectar_chuva_coletiva() — por equipe/dia, só entre os agentes
         que a etapa 1 NÃO classificou como Férias/Atestado naquele dia.

    IMPORTANTE: cada agente só é avaliado a partir da PRÓPRIA primeira
    visita, nunca da data mínima global do sistema. Sem isso, um agente
    (ou equipe inteira) que começou a trabalhar depois do início do
    período rastreado — ex.: uma atividade sazonal que só começa mais
    tarde — teria todo o intervalo ANTES de existir contado como "dias sem
    lançamento", gerando férias/chuva falsas logo no início do período de
    cada um."""
    if df_total.empty:
        return []
    data_max = df_total["dia"].max()
    equipes_ignoradas = {e.lower() for e in EQUIPES_SEM_DETECCAO_AUTOMATICA}

    eventos_ferias, ferias_por_agente, janela_por_agente = _detectar_ferias_individuais(
        df_total, resultados, data_max, equipes_ignoradas)
    eventos_chuva = _detectar_chuva_coletiva(
        df_total, resultados, data_max, equipes_ignoradas, ferias_por_agente, janela_por_agente)
    return eventos_ferias + eventos_chuva


def _dividir_em_ocorrencias(ini, fim, limite_dias_corridos=LIMITE_DIAS_CORRIDOS_OCORRENCIA):
    """Quebra [ini, fim] (datas) em pedaços de no máximo `limite_dias_corridos`
    dias CORRIDOS cada (não úteis), preservando a ordem cronológica — evita
    que uma ausência muito longa vire UMA ocorrência só, gigante, sem fim
    visível. A cada `limite_dias_corridos`, fecha a ocorrência atual e abre
    uma nova pro resto, se a ausência continuar."""
    pedacos, cursor = [], ini
    while cursor <= fim:
        fim_pedaco = min(cursor + timedelta(days=limite_dias_corridos - 1), fim)
        pedacos.append((cursor, fim_pedaco))
        cursor = fim_pedaco + timedelta(days=1)
    return pedacos


def _periodos_se_sobrepoem(a_ini, a_fim, b_ini, b_fim):
    """True se [a_ini,a_fim] e [b_ini,b_fim] têm pelo menos 1 dia em comum —
    SEM nenhuma tolerância (diferente de _periodos_se_tocam, que é usada só
    pra reconhecer 'a mesma ausência' entre duas coletas sucessivas do MESMO
    agente). Usada aqui pra decidir se as ocorrências de dois agentes
    DIFERENTES da mesma equipe realmente coincidiram no calendário."""
    return a_ini <= b_fim and b_ini <= a_fim


def _detectar_ferias_individuais(df_total, resultados, data_max, equipes_ignoradas):
    """ETAPA 1 — Férias/Atestado, por agente (ver regras completas no
    comentário da seção 13b acima). Resumo:
      1) >= LIMITE_DIAS_UTEIS_FERIAS dias úteis seguidos sem lançamento =
         candidato a férias (menos que isso é só "ausência", fica de fora).
      2) Cada candidato é dividido em ocorrências de até
         LIMITE_DIAS_CORRIDOS_OCORRENCIA dias corridos.
      3) Toda ocorrência é devolvida aqui; quem decide pendente × confirmada
         é atualizar_deteccoes_pendentes (flags CONFIRMAR_*_AUTOMATICAMENTE).
         Ao sobrepor a de outro agente da equipe, ganha
         "revisao_classificacao_necessaria" pro supervisor conferir o motivo.

    Retorna (eventos_ferias, ferias_por_agente, janela_por_agente):
      - ferias_por_agente: {id_agente: [(inicio, fim), ...]} com TODAS as
        ocorrências desta rodada (independente de sobrepor ou não) — é o
        que a etapa 2 usa pra excluir esses dias da análise de chuva.
      - janela_por_agente: {id_agente: [dias_uteis...]} — o intervalo de
        dias úteis avaliado pra cada agente (da própria primeira visita até
        data_max), reaproveitado pela etapa 2."""
    info_agente = {res["id_agente"]: (res["nome_agente"], res["equipe"]) for res in resultados}
    janela_por_agente = {}
    candidatos_por_agente = {}  # id_agente -> [(ini, fim), ...] já divididos em ocorrências de até 30 dias

    for res in resultados:
        if res["equipe"].lower() in equipes_ignoradas:
            continue  # equipe cadastrada em EQUIPES_SEM_DETECCAO_AUTOMATICA — não avalia
        df_ag = res["df"]
        if df_ag.empty:
            continue
        primeiro_dia_agente = df_ag["dia"].min()  # não a data mínima global — a do PRÓPRIO agente
        dias_uteis_agente = _dias_uteis_no_intervalo(primeiro_dia_agente, data_max)
        if not dias_uteis_agente:
            continue
        janela_por_agente[res["id_agente"]] = dias_uteis_agente

        dias_com_visita = set(df_ag["dia"])
        faltando = {d for d in dias_uteis_agente if d not in dias_com_visita}
        for ini, fim, dur in _runs_consecutivos_uteis(dias_uteis_agente, faltando):
            if dur < LIMITE_DIAS_UTEIS_FERIAS:
                continue  # <7 dias úteis = só ausência pontual, não vira candidato a férias
            # Férias têm no máximo 30 dias corridos: só o 1º pedaço é
            # candidato a férias. O que passar disso (2º pedaço em diante)
            # vira ocorrência marcada "excesso_30_dias" — o merge grava como
            # FALTA, não como férias (a coordenação ainda pode ajustar).
            for k, (ini_oc, fim_oc) in enumerate(_dividir_em_ocorrencias(ini, fim)):
                candidatos_por_agente.setdefault(res["id_agente"], []).append((ini_oc, fim_oc, k > 0))

    # Índice por equipe, pra checar sobreposição entre agentes DIFERENTES.
    ocorrencias_por_equipe = {}
    for id_ag, ocorrencias in candidatos_por_agente.items():
        equipe = info_agente[id_ag][1]
        for ini_oc, fim_oc, _excesso in ocorrencias:
            ocorrencias_por_equipe.setdefault(equipe, []).append((id_ag, ini_oc, fim_oc))

    eventos, ferias_por_agente = [], {}
    for id_ag, ocorrencias in candidatos_por_agente.items():
        nome, equipe = info_agente[id_ag]
        for ini_oc, fim_oc, excesso in ocorrencias:
            sobrepoe = any(
                outro_id != id_ag and _periodos_se_sobrepoem(ini_oc, fim_oc, o_ini, o_fim)
                for outro_id, o_ini, o_fim in ocorrencias_por_equipe.get(equipe, [])
            )
            evento = {
                "tipo": "possiveis_ferias", "id_agente": id_ag, "nome_agente": nome, "equipe": equipe,
                "inicio": ini_oc.strftime("%d/%m/%Y"), "fim": fim_oc.strftime("%d/%m/%Y"),
                "duracao": len(_dias_uteis_no_intervalo(ini_oc, fim_oc)),
            }
            if excesso:
                evento["excesso_30_dias"] = True
            if sobrepoe and not excesso:
                evento["revisao_classificacao_necessaria"] = True
                evento["nota_revisao_classificacao"] = (
                    "Esse período se sobrepõe com a ausência de outro agente da mesma equipe. Pode ser "
                    "coincidência de duas férias individuais, ou pode ser uma paralisação coletiva que a "
                    "detecção de chuva não pegou (por não ter sido a equipe INTEIRA parada no mesmo dia). "
                    "Já está confirmado como Férias e excluído da pontuação normalmente — essa "
                    "marcação é só pra revisar o motivo com calma, não bloqueia nada."
                )
            eventos.append(evento)
            ferias_por_agente.setdefault(id_ag, []).append((ini_oc, fim_oc))

    return eventos, ferias_por_agente, janela_por_agente


def _detectar_chuva_coletiva(df_total, resultados, data_max, equipes_ignoradas,
                              ferias_por_agente, janela_por_agente):
    """ETAPA 2 — Chuva, por equipe, dia a dia, só entre os agentes ATIVOS
    daquele dia (ou seja: dentro da própria janela de trabalho E fora de
    qualquer período de Férias/Atestado já confirmado pela etapa 1). Se
    TODOS os agentes ativos de uma equipe num dia útil não lançaram nada,
    esse dia é Chuva pra aquela equipe. Dias consecutivos com o mesmo
    padrão viram um único evento (a paralisação "acaba" no primeiro dia em
    que a maioria volta — um agente isolado que continua sumido não
    prolonga o evento sozinho, porque nesse dia ele já não está mais entre
    "todos os agentes ativos sem lançamento": os outros voltaram)."""
    def em_ferias(id_ag, dia):
        return any(ini <= dia <= fim for ini, fim in ferias_por_agente.get(id_ag, ()))

    info_agente = {res["id_agente"]: (res["nome_agente"], res["equipe"]) for res in resultados}
    dias_lancados_por_agente = df_total.groupby("id_agente")["dia"].apply(set).to_dict()

    por_equipe_ids = {}
    for res in resultados:
        if res["equipe"].lower() in equipes_ignoradas:
            continue
        if res["id_agente"] not in janela_por_agente:
            continue
        por_equipe_ids.setdefault(res["equipe"], []).append(res["id_agente"])

    eventos = []
    for equipe, ids in por_equipe_ids.items():
        janelas_set = {i: set(janela_por_agente[i]) for i in ids}
        todos_dias = sorted(set().union(*janelas_set.values()))

        dias_chuva = set()
        for dia in todos_dias:
            ativos = [i for i in ids if dia in janelas_set[i] and not em_ferias(i, dia)]
            if not ativos:
                continue  # ninguém ativo nesse dia (todo mundo de férias, ou fora da janela) — não dá pra falar em chuva
            if all(dia not in dias_lancados_por_agente.get(i, set()) for i in ativos):
                dias_chuva.add(dia)

        for ini, fim, dur in _runs_consecutivos_uteis(todos_dias, dias_chuva):
            dias_do_evento = [d for d in todos_dias if ini <= d <= fim]
            ativos_no_evento = sorted({i for d in dias_do_evento for i in ids
                                        if d in janelas_set[i] and not em_ferias(i, d)})
            eventos.append({
                "tipo": "paralisacao_coletiva", "equipe": equipe,
                "agentes_envolvidos": ativos_no_evento,
                "nomes_envolvidos": sorted({info_agente[i][0] for i in ativos_no_evento}),
                "inicio": ini.strftime("%d/%m/%Y"), "fim": fim.strftime("%d/%m/%Y"), "duracao": dur,
            })
    return eventos


def _periodos_se_tocam(ini1, fim1, ini2, fim2, tolerancia_dias=TOLERANCIA_DIAS_MESMO_EVENTO):
    """True se dois períodos [ini1,fim1] e [ini2,fim2] (objetos date) se
    sobrepõem OU estão a poucos dias um do outro — tratados como o MESMO
    evento contínuo, não dois eventos separados. A tolerância existe porque
    o início calculado de uma férias/atestado AINDA EM ANDAMENTO pode variar
    ±alguns dias de uma coleta pra outra (ex.: um lançamento atrasado que só
    aparece no site depois muda onde a sequência "sem lançamento" começa a
    contar) — sem essa folga, cada pequena variação virava um evento
    DUPLICADO em vez de atualizar o mesmo.

    O padrão vem de TOLERANCIA_DIAS_MESMO_EVENTO (constante lá em cima,
    perto de LIMITE_DIAS_UTEIS_FERIAS) — se um dia aparecer um caso de
    fusão ERRADA (duas férias de fato diferentes, só que próximas,
    grudando sem querer sozinhas), é ali que se ajusta, não aqui."""
    from datetime import timedelta
    return ini1 <= fim2 + timedelta(days=tolerancia_dias) and ini2 <= fim1 + timedelta(days=tolerancia_dias)


def atualizar_deteccoes_pendentes(eventos_detectados, caminho="data/deteccoes_pendentes.json"):
    """Funde os eventos detectados agora com o que já existia no arquivo,
    preservando decisões já tomadas.

    Chave de comparação (igual pros dois tipos, ver mesmo_grupo()): mesmo
    agente (férias) ou mesma equipe (chuva) E período que se SOBREPÕE ou
    está a poucos dias de distância (ver _periodos_se_tocam) — não exige
    início exato igual, porque tanto uma férias/atestado quanto uma chuva
    ainda em andamento podem ter o início recalculado alguns dias pra
    frente/trás entre coletas sucessivas (ex.: um lançamento atrasado que só
    aparece no site depois) sem deixar de ser o MESMO evento. Quando casa,
    funde os dois períodos (usa o início mais antigo e o fim mais recente
    dos dois) em vez de criar uma entrada nova ao lado da antiga.

    Comportamento:
      - "possiveis_ferias" (agente sozinho, >= LIMITE_DIAS_UTEIS_FERIAS dias
        úteis sem lançamento): entra PENDENTE (continua contando como Turno
        sem Lançamento) até a coordenação confirmar férias/atestado; com
        CONFIRMAR_FERIAS_AUTOMATICAMENTE = True nasce confirmada (modo antigo).
        Excesso de 30 dias ou agente sem abono automático entra como "falta".
        Marcar como "falta" (deteccao_editor.html, validar.html ou o JSON)
        faz o período contar normalmente, com o motivo documentado.
      - "paralisacao_coletiva" (todos os agentes ATIVOS — ou seja, já fora
        de qualquer Férias/Atestado — de uma equipe sem lançamento no mesmo
        dia): entra PENDENTE até a coordenação escolher o motivo (chuva,
        capacitação, reunião...); com CONFIRMAR_CHUVA_AUTOMATICAMENTE = True
        nasce confirmada como Chuva (modo antigo, ver seção 13b). A escolha
        do "categoria_coletiva" fica protegida e não é sobrescrita nas
        próximas coletas, mesmo que o padrão de dias sem lançamento continue.
    """
    sem_abono_cfg = _carregar_agentes_sem_abono()
    anteriores = []
    if os.path.exists(caminho):
        try:
            anteriores = json.loads(open(caminho, encoding="utf-8").read())
        except (json.JSONDecodeError, OSError):
            anteriores = []

    STATUS_PROTEGIDOS = ("confirmada", "falta", "rejeitada")  # "rejeitada" = nome antigo de "falta", mantido por compatibilidade

    def parse(s):
        return datetime.strptime(s, "%d/%m/%Y").date()

    def mesmo_grupo(a, b):
        """Dois eventos são 'o mesmo', pra fins de merge, se forem do mesmo
        agente (férias) ou da mesma equipe (chuva), os períodos se tocarem
        (ver _periodos_se_tocam) E a fusão dos dois não passar do teto de
        LIMITE_DIAS_CORRIDOS_OCORRENCIA dias corridos — sem essa segunda
        checagem, duas ocorrências de férias cortadas de propósito em
        pedaços de até 30 dias (ver _dividir_em_ocorrencias) voltariam a
        virar uma só, gigante, na primeira limpeza automática seguinte."""
        chave_a = a.get("id_agente") if a["tipo"] == "possiveis_ferias" else a.get("equipe")
        chave_b = b.get("id_agente") if b["tipo"] == "possiveis_ferias" else b.get("equipe")
        if chave_a != chave_b:
            return False
        ini_a, fim_a = parse(a["inicio"]), parse(a["fim"])
        ini_b, fim_b = parse(b["inicio"]), parse(b["fim"])
        if not _periodos_se_tocam(ini_a, fim_a, ini_b, fim_b):
            return False
        fundido_dias = (max(fim_a, fim_b) - min(ini_a, ini_b)).days + 1
        return fundido_dias <= LIMITE_DIAS_CORRIDOS_OCORRENCIA

    def fundir_lista(anteriores_tipo):
        """Auto-limpeza: funde duplicatas que já existem numa lista de
        eventos do MESMO tipo (geradas quando a comparação ainda era por
        início exato, antes desta correção) — sem isso, ficariam presas
        lado a lado pra sempre, já que o merge mais abaixo só evita criar
        duplicata NOVA, não junta as que já estão salvas. Idempotente —
        depois da primeira limpeza não sobra mais nada pra fundir."""
        fundidas, usadas = [], set()
        for i, e1 in enumerate(anteriores_tipo):
            if i in usadas:
                continue
            grupo = [e1]
            usadas.add(i)
            for j in range(i + 1, len(anteriores_tipo)):
                if j in usadas:
                    continue
                e2 = anteriores_tipo[j]
                # Não funde entradas de status diferente (ex.: férias + falta
                # de excesso) nem as ajustadas à mão pela coordenação.
                if any(mesmo_grupo(m, e2) and m.get("status") == e2.get("status")
                       and not (m.get("ajustado_manual") or e2.get("ajustado_manual")) for m in grupo):
                    grupo.append(e2)
                    usadas.add(j)
            if len(grupo) > 1:
                base = max(grupo, key=lambda x: x.get("detectado_em", ""))  # mantém a mais recente como "base"
                ini_final = min(parse(m["inicio"]) for m in grupo)
                fim_final = max(parse(m["fim"]) for m in grupo)
                base["inicio"] = ini_final.strftime("%d/%m/%Y")
                base["fim"] = fim_final.strftime("%d/%m/%Y")
                base["duracao"] = len(_dias_uteis_no_intervalo(ini_final, fim_final))
                base.pop("revisao_necessaria", None)
                base.pop("nota_revisao", None)
                quem = base.get("nome_agente") or base.get("equipe") or base.get("id_agente")
                log.info("🧹 Duplicata fundida: %s (%d entradas viraram 1 — %s a %s).",
                          quem, len(grupo), base["inicio"], base["fim"])
                fundidas.append(base)
            else:
                fundidas.append(e1)
        return fundidas

    anteriores_ferias = fundir_lista([e for e in anteriores if e["tipo"] == "possiveis_ferias"])
    anteriores_chuva = fundir_lista([e for e in anteriores if e["tipo"] == "paralisacao_coletiva"])

    def casar_e_fundir(novo, anteriores_tipo, usados):
        """Procura em anteriores_tipo um evento PROTEGIDO que seja 'o
        mesmo' que `novo` (ver mesmo_grupo) e ainda não usado nesta rodada.
        Se achar, funde os dois (união dos períodos) e devolve o registro
        atualizado; senão devolve None."""
        for i, ant in enumerate(anteriores_tipo):
            if i in usados or ant.get("status") not in STATUS_PROTEGIDOS:
                continue
            if ant.get("ajustado_manual"):
                # Período ajustado À MÃO pela coordenação: é a palavra final.
                # Uma detecção que SOBREPÕE o período só o "consome" (não
                # estica nem encolhe); os dias fora dele ficam sem abono, ou
                # seja, contam como falta, sem criar entrada nova.
                if (ant["tipo"] == novo["tipo"] and ant.get("id_agente") == novo.get("id_agente")
                        and _periodos_se_sobrepoem(parse(ant["inicio"]), parse(ant["fim"]),
                                                   parse(novo["inicio"]), parse(novo["fim"]))):
                    usados.add(i)
                    return ant
                continue
            if not mesmo_grupo(ant, novo):
                continue
            usados.add(i)
            ini_final = min(parse(novo["inicio"]), parse(ant["inicio"]))
            fim_final = max(parse(novo["fim"]), parse(ant["fim"]))
            ant["inicio"] = ini_final.strftime("%d/%m/%Y")
            ant["fim"] = fim_final.strftime("%d/%m/%Y")
            ant["duracao"] = len(_dias_uteis_no_intervalo(ini_final, fim_final))
            ant.pop("revisao_necessaria", None)
            ant.pop("nota_revisao", None)
            # revisao_classificacao_necessaria reflete o estado ATUAL
            # (sobrepõe outro agente da equipe ou não) — sempre atualiza
            # pro que a detecção de agora diz, não é "sticky" (liga e
            # nunca desliga sozinho, diferente de revisao_necessaria).
            if novo.get("revisao_classificacao_necessaria"):
                ant["revisao_classificacao_necessaria"] = True
                ant["nota_revisao_classificacao"] = novo.get("nota_revisao_classificacao")
            else:
                ant.pop("revisao_classificacao_necessaria", None)
                ant.pop("nota_revisao_classificacao", None)
            return ant
        return None

    usados_ferias, usados_chuva = set(), set()
    finais = []
    for novo in eventos_detectados:
        if novo["tipo"] == "paralisacao_coletiva":
            fundido = casar_e_fundir(novo, anteriores_chuva, usados_chuva)
            if fundido:
                finais.append(fundido)
            else:  # paralisacao_coletiva nova
                if CONFIRMAR_CHUVA_AUTOMATICAMENTE:
                    novo["status"] = "confirmada"
                    novo["categoria_coletiva"] = "Chuva"
                    novo["confirmado_automaticamente"] = True
                else:  # pendente: coordenação confirma o motivo (chuva, reunião, capacitação...); até lá vale o Possível Evento por turno
                    novo["status"] = "pendente"
                    novo["categoria_coletiva"] = None
                    novo["confirmado_automaticamente"] = False
                novo["detectado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                finais.append(novo)
            continue

        fundido = casar_e_fundir(novo, anteriores_ferias, usados_ferias)
        if fundido:
            finais.append(fundido)
        else:
            sem_abono = _agente_sem_abono_em(novo.get("id_agente"), parse(novo["inicio"]), sem_abono_cfg)
            if novo.get("excesso_30_dias") or sem_abono:
                # Passou de 30 dias de férias, ou agente sem abono automático:
                # entra como FALTA (conta no ranking); só vira abono se a
                # coordenação lançar/ajustar à mão.
                novo["status"] = "falta"
                novo["motivo"] = ("Falta (passou de 30 dias de férias)" if novo.get("excesso_30_dias")
                                  else "Falta (agente sem abono automático)")
                novo["confirmado_automaticamente"] = True
            elif CONFIRMAR_FERIAS_AUTOMATICAMENTE:
                novo["status"] = "confirmada"
                novo["motivo"] = "Férias"
                novo["confirmado_automaticamente"] = True
            else:  # pendente: continua contando como Turno sem Lançamento até a coordenação confirmar férias/atestado
                novo["status"] = "pendente"
                novo["motivo"] = None
                novo["confirmado_automaticamente"] = False
            novo["categoria_coletiva"] = None
            novo["detectado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            finais.append(novo)

    n_revisao = 0
    for i, anterior in enumerate(anteriores_ferias):
        if i not in usados_ferias and anterior.get("status") in STATUS_PROTEGIDOS:
            if not anterior.get("revisao_necessaria"):
                n_revisao += 1
            anterior["revisao_necessaria"] = True
            anterior["nota_revisao"] = ("O padrão que gerou esta detecção não aparece mais na análise atual "
                                         "— pode ser correção de dados, ou uma correção no sistema que revelou "
                                         "um falso positivo. Confira se a decisão ainda faz sentido.")
            finais.append(anterior)
    for i, anterior in enumerate(anteriores_chuva):
        if i not in usados_chuva and anterior.get("status") in STATUS_PROTEGIDOS:
            if not anterior.get("revisao_necessaria"):
                n_revisao += 1
            anterior["revisao_necessaria"] = True
            anterior["nota_revisao"] = ("O padrão que gerou esta detecção não aparece mais na análise atual "
                                         "— pode ser correção de dados, ou uma correção no sistema que revelou "
                                         "um falso positivo. Confira se a decisão ainda faz sentido.")
            finais.append(anterior)

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(finais, f, ensure_ascii=False, indent=2)
    n_pend = sum(1 for e in finais if e.get("status") == "pendente")
    n_ferias_auto = sum(1 for e in finais if e["tipo"] == "possiveis_ferias"
                         and e.get("confirmado_automaticamente") and e.get("status") == "confirmada")
    n_chuva_auto = sum(1 for e in finais if e["tipo"] == "paralisacao_coletiva"
                        and e.get("confirmado_automaticamente") and e.get("status") == "confirmada")
    if n_ferias_auto:
        log.info("🌴 %s período(s) de férias/atestado confirmado(s) automaticamente (>= %s dias úteis seguidos).",
                  n_ferias_auto, LIMITE_DIAS_UTEIS_FERIAS)
    if n_chuva_auto:
        log.info("🌧️ %s período(s) de chuva confirmado(s) automaticamente por equipe (todos os agentes ativos "
                  "sem lançamento no mesmo dia).", n_chuva_auto)
    if n_pend:
        log.info("🔎 %s detecção(ões) pendente(s) de decisão manual em %s.", n_pend, caminho)
    if n_revisao:
        log.warning("⚠️ %s decisão(ões) antiga(s) marcada(s) pra revisão em %s — o padrão que gerou "
                     "não aparece mais na análise atual (abra deteccao_editor.html).", n_revisao, caminho)
    return finais


def _cronograma_efetivo(deteccoes):
    """CRONOGRAMA_AUSENCIAS + as detecções com status "confirmada" (as
    individuais de férias/atestado e as paralisações coletivas só entram aqui
    depois de confirmadas pela coordenação, salvo se as flags
    CONFIRMAR_*_AUTOMATICAMENTE estiverem em True) — convertidas pro mesmo formato, é
    essa lista combinada que _obter_motivo_cronograma()/_preparar_cronograma()
    usam de verdade. "pendente" e "falta"/"rejeitada" NÃO entram aqui —
    continuam contando normalmente (uma falta marcada como "falta" é uma
    ausência de verdade, documentada, mas não excluída dos cálculos)."""
    efetivo = list(CRONOGRAMA_AUSENCIAS)
    for e in deteccoes:
        if e.get("status") != "confirmada":
            continue
        if e["tipo"] == "possiveis_ferias":
            motivo = _motivo_neutro(e.get("motivo") or "Férias")
            sufixo = "" if "(automático)" in motivo or "(confirmada)" in motivo else " (automático)"
            efetivo.append({"alvo": "agente", "id_agente": e["id_agente"], "motivo": f"{motivo}{sufixo}",
                             "inicio": e["inicio"], "fim": e["fim"]})
        else:  # paralisacao_coletiva confirmada (Chuva, por padrão)
            motivo = e.get("categoria_coletiva") or "Chuva"
            membros = e.get("membros")
            if membros:
                # Compatibilidade com eventos salvos pela lógica ANTIGA
                # (baseada em interseção de férias que se tocavam) — cada
                # membro podia ter um período individual diferente dos
                # demais, então aí sim precisa de uma linha por agente.
                for m in membros:
                    efetivo.append({"alvo": "agente", "id_agente": m["id_agente"], "motivo": f"{motivo} (confirmada)",
                                     "inicio": m["inicio"], "fim": m["fim"]})
            else:
                # Formato novo (detecção day-by-day por equipe): todo mundo
                # da equipe ficou parado no MESMO intervalo — uma única
                # linha "alvo: equipe" já cobre e exclui TODOS os agentes
                # dessa equipe nesses dias (_obter_motivo_cronograma casa
                # por equipe, não precisa listar agente por agente), então
                # a aba Cronograma mostra só "Equipe X — Chuva — dia a dia"
                # em vez de uma linha repetida pra cada agente da equipe.
                efetivo.append({"alvo": "equipe", "equipe": e["equipe"], "motivo": f"{motivo} (confirmada)",
                                 "inicio": e["inicio"], "fim": e["fim"]})
    return efetivo


CAMINHO_AGENTES_SEM_ABONO = "data/agentes_sem_abono.json"


def _carregar_agentes_sem_abono(caminho=CAMINHO_AGENTES_SEM_ABONO):
    """{id_agente: date_desde ou None}. Agentes listados NÃO ganham abono
    automático (férias/ausência justificada): o que a detecção achar vira
    FALTA a partir de `desde` (ou sempre, se vazio). Formato do arquivo:
    {"2951": {"desde": "01/10/2026", "motivo": "texto livre, sem dado de saúde"}}"""
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            bruto = json.load(f)
        if not isinstance(bruto, dict):
            raise ValueError("não é um objeto {id: {...}}")
    except (json.JSONDecodeError, OSError, ValueError) as e:
        log.warning("⚠️ %s inválido (%s) — ignorando agentes sem abono.", caminho, e)
        return {}
    res = {}
    for k, v in bruto.items():
        try:
            desde = None
            if isinstance(v, dict) and v.get("desde"):
                desde = datetime.strptime(v["desde"], "%d/%m/%Y").date()
            res[int(k)] = desde
        except (ValueError, TypeError):
            log.warning("⚠️ Entrada inválida em %s ignorada: %r", caminho, k)
    return res


def _agente_sem_abono_em(id_agente, dia, cfg):
    if id_agente not in cfg:
        return False
    desde = cfg[id_agente]
    return desde is None or dia >= desde
