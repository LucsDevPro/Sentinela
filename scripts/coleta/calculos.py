# -*- coding: utf-8 -*-
"""Cálculos por agente: tempos, pontuação (ranking), horas trabalhadas e resumos.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
from itertools import groupby
from datetime import time as dt_time
import pandas as pd
import semanas_evisita as sem
from .parametros import (
    DIAS_UTEIS_MES,
    HORA_ALMOCO_FIM_MIN,
    HORA_ALMOCO_INICIO_MIN,
    HORA_EXPEDIENTE_MANHA_FIM,
    HORA_EXPEDIENTE_MANHA_INICIO,
    HORA_EXPEDIENTE_TARDE_FIM,
    HORA_EXPEDIENTE_TARDE_INICIO,
    LIMIAR_SEQUENCIA_SUSPEITA_SEG,
    PCT_RAPIDAS_ATENCAO_ATE,
    PCT_RAPIDAS_OK_ATE,
    SALARIO_AGENTE,
    TEMPO_MAX_VISITA_MIN,
    TEMPO_MIN_VISITA_MIN,
    TETO_DURACAO_MEDIA_MIN,
    meta_da_equipe,
)
from .pontos import (
    BONUS_MIN_FRACAO_DIAS_ESPERADOS,
    HORA_LIMITE_FIM_MANHA,
    HORA_LIMITE_FIM_TARDE,
    HORA_LIMITE_INICIO_MANHA,
    HORA_LIMITE_INICIO_TARDE,
    NOTA_FAIXA_ATENCAO,
    NOTA_FAIXA_BOM,
    NOTA_FAIXA_EXCELENTE,
    NOTA_MAXIMA,
    NOTA_MINIMA,
    PONTOS_GANHO_DIA_COM_META,
    PONTOS_GANHO_PONTUALIDADE_PERFEITA,
    PONTOS_GANHO_SEM_AUSENCIA,
    PONTOS_GANHO_SEM_VISITA_RAPIDA,
    PONTOS_INICIAIS,
    PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO,
    PONTOS_PERDA_DIA_SEM_META,
    PONTOS_PERDA_FIM_MANHA_ANTECIPADO,
    PONTOS_PERDA_FIM_TARDE_ANTECIPADO,
    PONTOS_PERDA_FORA_EXPEDIENTE,
    PONTOS_PERDA_INICIO_MANHA_ATRASADO,
    PONTOS_PERDA_INICIO_TARDE_ATRASADO,
    PONTOS_PERDA_SEQUENCIA_SUSPEITA,
    PONTOS_PERDA_TURNO_SEM_LANCAMENTO,
    PONTOS_PERDA_VISITA_ALMOCO,
    PONTOS_PERDA_VISITA_DUPLICADA,
    PONTOS_PERDA_VISITA_LONGA,
    PONTOS_PERDA_VISITA_NEGATIVA,
    PONTOS_PERDA_VISITA_RAPIDA,
    PRESENCA_MINIMA_FRACAO,
    TETO_FATOR_NORMALIZACAO,
)

log = logging.getLogger("evisita")


# ============================================================
# CÁLCULOS
# ============================================================

def calcular_tempos(visitas, nome, id_agente, equipe, semana_html_id=None):
    """`semana_html_id`: quando a coleta já é feita semana a semana (o caso
    normal agora), passe o HTML ID da semana que está sendo processada — o
    df inteiro é marcado com essa semana de forma exata, sem precisar
    adivinhar pela data de cada visita. Se omitido, a semana de cada visita
    é inferida a partir da própria data de chegada (fallback, usado só se
    algum dia essa função for chamada fora do fluxo de coleta por semana)."""
    if not visitas:
        return pd.DataFrame()

    df = pd.DataFrame(visitas)
    df["id_agente"] = id_agente
    df["nome_agente"] = nome
    df["equipe"] = equipe

    # O e-Visita só fornece precisão de minutos (sem segundos) nos horários.
    df["dt_chegada"] = pd.to_datetime(df["data_chegada"], format="%d/%m/%Y %H:%M", errors="coerce")
    df["dt_saida"] = pd.to_datetime(df["data_saida"], format="%d/%m/%Y %H:%M", errors="coerce")

    n_invalidas = int(df["dt_chegada"].isna().sum() + df["dt_saida"].isna().sum())
    if n_invalidas:
        log.warning("    ⚠️ %s (%s): %s datas inválidas/não reconhecidas nas visitas",
                     nome, id_agente, n_invalidas)

    df["duracao_min"] = ((df["dt_saida"] - df["dt_chegada"]).dt.total_seconds() / 60).round(2)

    df = df.sort_values("dt_chegada").reset_index(drop=True)
    df["dia"] = df["dt_chegada"].dt.date
    # Semana do e-Visita (NÃO é semana ISO — ver scripts/semanas_evisita.py).
    # Se a chamada já sabe a semana (fluxo normal: coleta semana a semana),
    # usa ela direto; senão infere pela data de cada visita (fallback).
    if semana_html_id is not None:
        df["semana_html"] = semana_html_id
    else:
        df["semana_html"] = df["dt_chegada"].apply(
            lambda d: sem.html_id_da_data(d.date()) if pd.notna(d) else pd.NA)
    df["semana"] = df["semana_html"].apply(
        lambda h: sem.html_para_semana(int(h), sem.ano_da_semana_html(int(h))) if pd.notna(h) else pd.NA)
    df["alerta_rapida"] = df["duracao_min"] < TEMPO_MIN_VISITA_MIN
    df["alerta_longa"] = df["duracao_min"] > TEMPO_MAX_VISITA_MIN
    # Visita acima do teto usado no cálculo de média/mediana (ver
    # TETO_DURACAO_MEDIA_MIN) — listada à parte pra auditoria, mesmo que não
    # passe de TEMPO_MAX_VISITA_MIN (que é o limite de "longa").
    df["acima_teto_media"] = df["duracao_min"] > TETO_DURACAO_MEDIA_MIN
    df["alerta_neg"] = df["duracao_min"] < 0  # duração negativa = saída antes da chegada (bug do sistema)

    # Duplicadas — guarda o motivo separado (id repetido x mesmo horário+imóvel)
    df["dup_por_id"] = df["id_visita"].notna() & df.duplicated(subset=["id_visita"], keep=False)
    df["dup_por_chegada_imovel"] = df.duplicated(subset=["dt_chegada", "imovel"], keep=False)
    df["duplicada"] = df["dup_por_id"] | df["dup_por_chegada_imovel"]

    # Sequência suspeita: diferença de chegada em relação à visita anterior
    # (já ordenado por dt_chegada). Menos de LIMIAR_SEQUENCIA_SUSPEITA_SEG
    # segundos entre uma chegada e outra sugere lançamento em lote.
    diff_seg = df["dt_chegada"].diff().dt.total_seconds()
    mask_suspeita = diff_seg.between(0, LIMIAR_SEQUENCIA_SUSPEITA_SEG).fillna(False)
    df["diff_chegada_anterior_seg"] = diff_seg
    df["par_suspeito_anterior"] = mask_suspeita  # True se ESTA visita e a anterior formam par suspeito
    df["sequencia_suspeita"] = False
    idx_atual = df.index[mask_suspeita]
    df.loc[idx_atual, "sequencia_suspeita"] = True
    df.loc[idx_atual - 1, "sequencia_suspeita"] = True

    # Agrupa visitas conectadas na mesma "cadeia" suspeita (para facilitar
    # visualizar quais visitas pertencem ao mesmo lote de lançamento).
    grupo_atual = 0
    grupos = []
    for i, (susp, par_ant) in enumerate(zip(df["sequencia_suspeita"], df["par_suspeito_anterior"])):
        if not susp:
            grupos.append(None)
            continue
        if par_ant and i > 0 and grupos[i - 1] is not None:
            grupos.append(grupos[i - 1])
        else:
            grupo_atual += 1
            grupos.append(grupo_atual)
    df["grupo_sequencia_suspeita"] = grupos

    # Turnos — separa o horário de almoço (com tolerância de 15min: 11h15-12h45),
    # quando não deveria haver visitas registradas, para não contaminar as
    # estatísticas de Manhã/Tarde.
    df["hora_chegada"] = df["dt_chegada"].dt.hour
    df["minutos_chegada"] = df["dt_chegada"].dt.hour * 60 + df["dt_chegada"].dt.minute
    df["turno"] = pd.cut(
        df["minutos_chegada"], bins=[0, HORA_ALMOCO_INICIO_MIN, HORA_ALMOCO_FIM_MIN, 24 * 60],
        labels=["Manhã", "Almoço", "Tarde"], right=False,
    )
    df["visita_horario_almoco"] = df["turno"] == "Almoço"

    # Dia da semana e horário oficial de expediente (7h-11h e 13h-17h, dias
    # úteis). Qualquer visita fora disso — inclusive sábado/domingo — é
    # marcada como "fora do expediente".
    df["dia_semana_num"] = df["dt_chegada"].dt.weekday  # 0=Segunda ... 6=Domingo
    df["fim_de_semana"] = df["dia_semana_num"] >= 5
    df["dentro_expediente"] = (~df["fim_de_semana"]) & (
        ((df["hora_chegada"] >= HORA_EXPEDIENTE_MANHA_INICIO) & (df["hora_chegada"] < HORA_EXPEDIENTE_MANHA_FIM))
        | ((df["hora_chegada"] >= HORA_EXPEDIENTE_TARDE_INICIO) & (df["hora_chegada"] < HORA_EXPEDIENTE_TARDE_FIM))
    )
    df["fora_expediente"] = df["dt_chegada"].notna() & ~df["dentro_expediente"]

    return df


def _media_horario(series_dt):
    """
    Calcula o horário médio (datetime.time) de uma série de timestamps.
    pandas não sabe tirar média direto de objetos datetime.time, então
    convertemos para segundos desde a meia-noite, tiramos a média e
    convertemos de volta.
    """
    validos = series_dt.dropna()
    if validos.empty:
        return None
    segundos = validos.dt.hour * 3600 + validos.dt.minute * 60 + validos.dt.second
    media_seg = int(round(segundos.mean()))
    h, resto = divmod(media_seg, 3600)
    mi, s = divmod(resto, 60)
    return dt_time(hour=h % 24, minute=mi, second=s)


def _maior_sequencia_consecutiva(pares_suspeitos):
    """
    Recebe a lista de pares (visita[i] vs visita[i-1]) marcados como suspeitos
    e retorna o maior número de VISITAS encadeadas nessa condição.
    Ex.: pares suspeitos em 3 posições seguidas = 4 visitas na mesma cadeia.
    """
    maior_run_pares = 0
    for valor, grupo in groupby(pares_suspeitos):
        if valor:
            maior_run_pares = max(maior_run_pares, len(list(grupo)))
    return maior_run_pares + 1 if maior_run_pares > 0 else 0


def _fmt_hhmm_tupla(t):
    """Formata tupla (hora, minuto) como 'HHhMM' (ex.: (8, 30) -> '08h30')."""
    return f"{t[0]:02d}h{t[1]:02d}"


def _avaliar_pontualidade_diaria(df):
    """
    Para cada dia trabalhado, verifica se o início/fim de cada turno
    (Manhã/Tarde) violou os horários de referência configurados
    (HORA_LIMITE_INICIO_MANHA etc.) — usado pelo sistema de pontuação.
    Ignora visitas com duração negativa (horário não confiável).
    Retorna um dict com a CONTAGEM de dias com cada tipo de violação.
    """
    resultado = {
        "inicio_manha_atrasado": 0, "fim_manha_antecipado": 0,
        "inicio_tarde_atrasado": 0, "fim_tarde_antecipado": 0,
    }
    if df.empty:
        return resultado

    validos = df[~df["alerta_neg"]]
    if validos.empty:
        return resultado

    config_turnos = [
        ("Manhã", "inicio_manha_atrasado", "fim_manha_antecipado",
         HORA_LIMITE_INICIO_MANHA, HORA_LIMITE_FIM_MANHA),
        ("Tarde", "inicio_tarde_atrasado", "fim_tarde_antecipado",
         HORA_LIMITE_INICIO_TARDE, HORA_LIMITE_FIM_TARDE),
    ]

    for turno, campo_inicio, campo_fim, limite_inicio, limite_fim in config_turnos:
        sub = validos[validos["turno"] == turno]
        if sub.empty:
            continue
        por_dia = sub.groupby("dia").agg(inicio=("dt_chegada", "min"), fim=("dt_saida", "max"))
        limite_inicio_min = limite_inicio[0] * 60 + limite_inicio[1]
        limite_fim_min = limite_fim[0] * 60 + limite_fim[1]
        inicio_min = por_dia["inicio"].dt.hour * 60 + por_dia["inicio"].dt.minute
        fim_min = por_dia["fim"].dt.hour * 60 + por_dia["fim"].dt.minute
        resultado[campo_inicio] = int((inicio_min > limite_inicio_min).sum())
        resultado[campo_fim] = int((fim_min < limite_fim_min).sum())

    return resultado


def _classificar_pontuacao(pontos):
    if pontos >= NOTA_FAIXA_EXCELENTE:
        return "🟢 EXCELENTE", "D6F5D6"
    if pontos >= NOTA_FAIXA_BOM:
        return "🟡 BOM", "FFF9B0"
    if pontos >= NOTA_FAIXA_ATENCAO:
        return "🟠 ATENÇÃO", "FFD9A0"
    return "🔴 CRÍTICO", "FFB3B3"


def br_num(v):
    """Número em texto pt-BR sem zeros inúteis (3 → '3', 2.5 → '2,5')."""
    return f"{v:.1f}".rstrip("0").rstrip(".").replace(".", ",") if v != int(v) else str(int(v))


def calcular_pontuacao(res, qtd_ausencias, alvo_dias_mes=DIAS_UTEIS_MES, normalizar_periodo=True, ajustes=(),
                       dias_inteiros_sem_lancamento=0, aplicar_presenca_minima=False):
    """
    Calcula a pontuação final de um agente a partir de PONTOS_INICIAIS,
    aplicando todos os critérios de perda/ganho configurados. Retorna
    (pontos_final, classificacao, cor, lista_detalhamento).

    `ajustes`: lista de (motivo, pontos) — ajustes MANUAIS do gestor (ver
    data/ajustes_ranking.json e _carregar_ajustes_ranking). Entram no
    Detalhamento/Extrato como linha própria "Ajuste manual: <motivo>", sem
    normalização, antes do limite de 0 a 100.

    `normalizar_periodo=False` (ranking de Outubro/2026 em diante, ver
    RANKING_SEM_NORMALIZACAO_A_PARTIR_DE): NÃO aplica o fator de normalização
    descrito abaixo — fator fixo em 1,0, então Peso Efetivo = Peso Nominal
    para todos os agentes e pontos = 100 + Σ(qtd × peso nominal). Todo o resto
    do texto abaixo descreve o método ANTIGO (normalizar_periodo=True), que
    segue valendo para os períodos anteriores e para o Acumulado.

    IMPORTANTE — normalização "por 1 mês de calibração": PONTOS_INICIAIS
    (100) foi calibrado assumindo ~1 mês (`alvo_dias_mes` dias úteis)
    trabalhado. Sem normalizar, um agente avaliado num período maior (ex.:
    o Acumulado, somando vários meses) acumula 3-4x mais OCORRÊNCIAS
    BRUTAS de cada critério do que em 1 mês — mesmo com o desempenho
    EXATAMENTE IGUAL, dia a dia — e a pontuação despencava pro chão
    (comprovado: mesmo padrão de desempenho dava 102 pontos em 1 mês e 0
    pontos em 4 meses seguidos, sem essa correção).

    `alvo_dias_mes` é o Nº DE DIAS ÚTEIS de referência ("1 mês de
    calibração") — calculado por _dias_uteis_alvo_periodo, que usa dois
    critérios diferentes dependendo do tipo de período:
      - Mês corrente/em andamento (período dentro de 1 único mês civil):
        conta só os dias úteis JÁ PASSADOS até a última data do período —
        se hoje é o 14º dia útil do mês, o alvo é 14, não o mês inteiro
        (21). Comparar com o mês inteiro enquanto ele não fechou infla o
        fator de todo mundo artificialmente.
      - Acumulado (período cobrindo vários meses): o alvo continua sendo o
        mês civil INTEIRO mais recente do período (não os dias decorridos
        do período todo) — aqui o objetivo é o OPOSTO: escalar pra baixo
        um período longo pra caber na calibração de "1 mês". Se usássemos
        dias decorridos do período INTEIRO (que pode somar 80+ dias), o
        fator viraria sempre ~1 e o bug do parágrafo acima voltaria a
        acontecer no Acumulado.
    Não é uma constante chutada tipo 22 fixo em nenhum dos dois casos,
    porque nem todo mês tem o mesmo número de dias úteis (feriados, fins
    de semana caindo diferente).

    O fator é LIMITADO a TETO_FATOR_NORMALIZACAO (2x, por padrão) — sem
    esse teto, o efeito inverso acontece pra quem trabalhou POUCOS dias no
    período (ex.: alguém que ficou de férias quase o mês inteiro): com só
    2 dias trabalhados, o fator sem teto seria alvo/2 ≈ 10-11x, transformando
    6 visitas rápidas (peso 0,3 = 1,8 ponto normal) em quase 20 pontos
    perdidos — um punhado de dias ruins vira um mês inteiro ruim, o que
    não é justo nem realista (a amostra é pequena demais pra extrapolar
    com confiança). Com o teto em 2x, o mesmo caso vira só 3,6 pontos.
    """
    r = res["resumo"]
    df = res["df"]
    pontos = float(PONTOS_INICIAIS)
    detalhes = []
    if not normalizar_periodo:
        fator_normalizacao = 1.0
    else:
        fator_normalizacao = min(alvo_dias_mes / r["dias_trabalhados"], TETO_FATOR_NORMALIZACAO) \
            if r["dias_trabalhados"] > 0 else 1.0

    def aplicar(motivo, qtd, peso, sinal, normalizar=True):
        nonlocal pontos
        if not qtd or not peso:
            return
        qtd_calc = qtd * fator_normalizacao if normalizar else qtd
        delta = sinal * qtd_calc * peso
        pontos += delta
        # Mostra as TRÊS peças da conta separadas, pra qualquer gestor
        # conseguir bater "qtd × peso nominal × fator = pontos" na mão,
        # sem precisar confiar cegamente no número final. Antes só existia
        # o "peso efetivo" (peso × fator) numa coluna só chamada "peso",
        # o que gerava questionamento tipo "89 × 0,30 deveria dar 26,7, não
        # 53,4" — porque o fator ficava escondido. Ver calcular_pontuacao().
        peso_efetivo = round(peso * fator_normalizacao, 4) if normalizar else peso
        detalhes.append({
            "nome_agente": res["nome_agente"],
            "equipe": res["equipe"],
            "motivo": motivo,
            "qtd": qtd,  # sempre a contagem BRUTA real, pra não confundir quem for auditar
            "peso_nominal": peso,
            "fator_normalizacao": round(fator_normalizacao, 3) if normalizar else 1.0,
            "peso": peso_efetivo,  # mantido por compatibilidade (peso EFETIVO)
            "pontos": round(delta, 2),
        })

    pont_diaria = _avaliar_pontualidade_diaria(df)
    aplicar(f"Início manhã após {_fmt_hhmm_tupla(HORA_LIMITE_INICIO_MANHA)}",
            pont_diaria["inicio_manha_atrasado"], PONTOS_PERDA_INICIO_MANHA_ATRASADO, -1)
    aplicar(f"Fim manhã antes de {_fmt_hhmm_tupla(HORA_LIMITE_FIM_MANHA)}",
            pont_diaria["fim_manha_antecipado"], PONTOS_PERDA_FIM_MANHA_ANTECIPADO, -1)
    aplicar(f"Início tarde após {_fmt_hhmm_tupla(HORA_LIMITE_INICIO_TARDE)}",
            pont_diaria["inicio_tarde_atrasado"], PONTOS_PERDA_INICIO_TARDE_ATRASADO, -1)
    aplicar(f"Fim tarde antes de {_fmt_hhmm_tupla(HORA_LIMITE_FIM_TARDE)}",
            pont_diaria["fim_tarde_antecipado"], PONTOS_PERDA_FIM_TARDE_ANTECIPADO, -1)

    aplicar("Turno sem lançamento (não é chuva/reunião/férias)",
            qtd_ausencias, PONTOS_PERDA_TURNO_SEM_LANCAMENTO, -1)
    if not normalizar_periodo:
        aplicar("Dia inteiro sem lançamento (2 turnos)", dias_inteiros_sem_lancamento,
                PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO, -1, normalizar=False)
    aplicar("Visita rápida", r["visitas_rapidas"], PONTOS_PERDA_VISITA_RAPIDA, -1)
    aplicar("Visita longa", r["visitas_longas"], PONTOS_PERDA_VISITA_LONGA, -1)
    aplicar("Visita duplicada", r["visitas_duplicadas"], PONTOS_PERDA_VISITA_DUPLICADA, -1)
    aplicar("Visita em sequência suspeita", r["visitas_seq_suspeita"], PONTOS_PERDA_SEQUENCIA_SUSPEITA, -1)
    aplicar("Visita com duração negativa", r["visitas_negativas"], PONTOS_PERDA_VISITA_NEGATIVA, -1)
    aplicar("Visita fora do expediente/fim de semana", r["visitas_fora_expediente"], PONTOS_PERDA_FORA_EXPEDIENTE, -1)
    aplicar("Visita no horário de almoço", r["visitas_horario_almoco"], PONTOS_PERDA_VISITA_ALMOCO, -1)

    # "Dia com/sem meta batida" é contagem LITERAL (1 dia = 1 ponto,
    # conforme pedido) — sem o fator_normalizacao. Diferente dos outros
    # critérios (que representam uma TAXA de erro/acerto, onde faz sentido
    # normalizar pra período parcial não distorcer), aqui "meta batida" já É
    # a contagem de dias — normalizar inflava esse número pra quem trabalhou
    # poucos dias no período (ex.: 11 dias com meta batida virando 18,6
    # pontos pra um agente que só trabalhou 13 dias no mês por causa de
    # férias — 11 dias bem trabalhados tem que valer 11 pontos, não 18,6).
    dias_sem_meta = max(r["dias_trabalhados"] - r["dias_atingiu_meta"], 0)
    aplicar("Dia sem bater a meta diária", dias_sem_meta, PONTOS_PERDA_DIA_SEM_META, -1, normalizar=False)

    aplicar("Dia com meta diária batida", r["dias_atingiu_meta"], PONTOS_GANHO_DIA_COM_META, +1, normalizar=False)

    bonus_rapida = r["visitas_rapidas"] == 0 and r["total_visitas"] > 0
    bonus_ausencia = qtd_ausencias == 0 and r["dias_trabalhados"] > 0
    bonus_pontual = sum(pont_diaria.values()) == 0 and r["dias_trabalhados"] > 0
    # Método novo: bônus só pra quem trabalhou >= 50% dos dias esperados.
    # Método antigo (períodos até Setembro/2026 e Acumulado): sem essa regra.
    bonus_elegivel = True
    if not normalizar_periodo:
        bonus_elegivel = (alvo_dias_mes > 0
                          and r["dias_trabalhados"] >= BONUS_MIN_FRACAO_DIAS_ESPERADOS * alvo_dias_mes)
    if bonus_elegivel:
        if bonus_rapida:
            aplicar("Bônus: nenhuma visita rápida no período", 1, PONTOS_GANHO_SEM_VISITA_RAPIDA, +1, normalizar=False)
        if bonus_ausencia:
            aplicar("Bônus: nenhum turno sem lançamento no período", 1, PONTOS_GANHO_SEM_AUSENCIA, +1, normalizar=False)
        if bonus_pontual:
            aplicar("Bônus: pontualidade perfeita no período", 1, PONTOS_GANHO_PONTUALIDADE_PERFEITA, +1, normalizar=False)
    elif bonus_rapida or bonus_ausencia or bonus_pontual:
        # Linha informativa (0 ponto) pra ficar claro por que o bônus não veio.
        detalhes.append({
            "nome_agente": res["nome_agente"], "equipe": res["equipe"],
            "motivo": (f"Bônus não concedido: trabalhou {r['dias_trabalhados']} de {alvo_dias_mes} dias esperados "
                       f"(mínimo {int(BONUS_MIN_FRACAO_DIAS_ESPERADOS * 100)}%)"),
            "qtd": 0, "peso_nominal": 0, "fator_normalizacao": 1.0, "peso": 0, "pontos": 0.0,
        })

    # Presença mínima: nota proporcional (ver PRESENCA_MINIMA_FRACAO).
    if aplicar_presenca_minima and not normalizar_periodo and alvo_dias_mes > 0:
        presenca = r["dias_trabalhados"] / alvo_dias_mes
        if presenca < PRESENCA_MINIMA_FRACAO:
            fator_presenca = presenca / PRESENCA_MINIMA_FRACAO
            bruto = max(min(pontos, NOTA_MAXIMA if NOTA_MAXIMA is not None else pontos),
                        NOTA_MINIMA if NOTA_MINIMA is not None else pontos)
            delta = bruto * fator_presenca - pontos
            pontos += delta
            detalhes.append({
                "nome_agente": res["nome_agente"], "equipe": res["equipe"],
                "motivo": (f"Presença abaixo do mínimo: {br_num(r['dias_trabalhados'])} de {br_num(alvo_dias_mes)} dias esperados "
                           f"({presenca * 100:.0f}%, mínimo {int(PRESENCA_MINIMA_FRACAO * 100)}%) — nota × {fator_presenca:.2f}"),
                "qtd": 1, "peso_nominal": round(abs(delta), 4), "fator_normalizacao": 1.0,
                "peso": round(abs(delta), 4), "pontos": round(delta, 2),
            })

    for motivo_ajuste, pontos_ajuste in ajustes:
        aplicar(f"Ajuste manual: {motivo_ajuste}", 1, abs(pontos_ajuste),
                1 if pontos_ajuste > 0 else -1, normalizar=False)

    if NOTA_MINIMA is not None:
        pontos = max(pontos, NOTA_MINIMA)
    if NOTA_MAXIMA is not None:
        pontos = min(pontos, NOTA_MAXIMA)

    pontos = round(pontos, 2)
    classif, fill = _classificar_pontuacao(pontos)
    return pontos, classif, fill, detalhes


def _horas_trabalhadas_diarias(df):
    """
    Para cada dia trabalhado, calcula:
      - horas_span: jornada total (primeira chegada até última saída do dia),
        DESCONTANDO a sobreposição com o horário de almoço (o servidor não
        deveria estar em expediente nesse intervalo).
      - horas_uteis: soma das durações de visita naquele dia (tempo
        efetivamente dentro de imóveis/atividade), em horas — cada visita
        entra CAPADA em TETO_DURACAO_MEDIA_MIN (20min) nessa soma. Isso é
        proposital: lançamentos feitos pela web (fora do horário real da
        visita) às vezes vêm com durações artificialmente longas, o que
        infla horas trabalhadas e distorce custo/hora pra menos (parece
        mais eficiente do que é). Capar em 20min neutraliza essa distorção
        sem precisar identificar quais lançamentos vieram da web — o
        "alerta_neg"/"acima_teto_media" continuam mostrando a duração REAL
        (sem cap) pra quem quiser auditar o lançamento em si.
    Visitas com duração negativa são ignoradas (horário de saída não confiável).
    """
    validos = df[~df["alerta_neg"]].copy()
    if validos.empty:
        return pd.DataFrame(columns=["horas_span", "horas_uteis"])

    validos["duracao_min_capada"] = validos["duracao_min"].clip(upper=TETO_DURACAO_MEDIA_MIN)

    agg = validos.groupby("dia").agg(
        inicio=("dt_chegada", "min"),
        fim=("dt_saida", "max"),
        soma_min=("duracao_min_capada", "sum"),
    )

    def _overlap_almoco_horas(row):
        dia = row.name
        h_ini, m_ini = divmod(HORA_ALMOCO_INICIO_MIN, 60)
        h_fim, m_fim = divmod(HORA_ALMOCO_FIM_MIN, 60)
        almoco_ini = pd.Timestamp.combine(dia, dt_time(hour=h_ini, minute=m_ini))
        almoco_fim = pd.Timestamp.combine(dia, dt_time(hour=h_fim, minute=m_fim))
        ini_sobreposto = max(row["inicio"], almoco_ini)
        fim_sobreposto = min(row["fim"], almoco_fim)
        segundos = (fim_sobreposto - ini_sobreposto).total_seconds()
        return max(segundos, 0) / 3600

    agg["overlap_almoco_h"] = agg.apply(_overlap_almoco_horas, axis=1)
    agg["horas_span"] = ((agg["fim"] - agg["inicio"]).dt.total_seconds() / 3600) - agg["overlap_almoco_h"]
    agg["horas_span"] = agg["horas_span"].clip(lower=0)
    agg["horas_uteis"] = agg["soma_min"] / 60

    return agg[["horas_span", "horas_uteis"]]




def resumo_agente(df):
    # Média/mediana de duração EXCLUEM visitas com duração negativa (bug do
    # sistema — saída registrada antes da chegada). Ver aba "Visitas Negativas".
    dv = df[df["duracao_min"].notna() & (df["duracao_min"] >= 0)].copy()
    dv["duracao_capada"] = dv["duracao_min"].clip(upper=TETO_DURACAO_MEDIA_MIN)
    por_dia = df.groupby("dia")["imovel"].count()

    total_duplicadas = int(df["duplicada"].sum())
    pct_duplicadas = round((total_duplicadas / len(df) * 100), 2) if len(df) > 0 else 0

    total_seq_suspeita = int(df["sequencia_suspeita"].sum())
    pct_seq_suspeita = round((total_seq_suspeita / len(df) * 100), 2) if len(df) > 0 else 0
    maior_seq_suspeita = _maior_sequencia_consecutiva(df["par_suspeito_anterior"].tolist())

    total_almoco = int(df["visita_horario_almoco"].sum())
    pct_almoco = round((total_almoco / len(df) * 100), 2) if len(df) > 0 else 0

    total_fora_expediente = int(df["fora_expediente"].sum())
    pct_fora_expediente = round((total_fora_expediente / len(df) * 100), 2) if len(df) > 0 else 0

    # Horas trabalhadas (jornada) e horas úteis (tempo em visita), por dia e por semana
    diario_horas = _horas_trabalhadas_diarias(df)
    media_horas_trabalhadas_dia = round(diario_horas["horas_span"].mean(), 2) if not diario_horas.empty else 0
    media_horas_uteis_dia_exata = diario_horas["horas_uteis"].mean() if not diario_horas.empty else 0
    media_horas_uteis_dia = round(media_horas_uteis_dia_exata, 2) if not diario_horas.empty else 0

    if not diario_horas.empty:
        dia_para_semana = df.groupby("dia")["semana"].first()
        horas_por_semana = diario_horas["horas_span"].groupby(dia_para_semana).sum()
        media_horas_trabalhadas_semana = round(horas_por_semana.mean(), 2) if not horas_por_semana.empty else 0
    else:
        media_horas_trabalhadas_semana = 0

    # Custo da hora útil: salário mensal fixo / horas úteis mensais estimadas
    # (média diária de horas em visita, SEM arredondar, extrapolada para
    # DIAS_UTEIS_MES dias — arredondar antes distorceria o custo final).
    horas_uteis_mes_estimado = media_horas_uteis_dia_exata * DIAS_UTEIS_MES
    custo_hora_util = round(SALARIO_AGENTE / horas_uteis_mes_estimado, 2) if horas_uteis_mes_estimado > 0 else None

    # Horários por turno: início = primeira chegada do dia; fim = última saída
    # do dia; depois tira-se a média dessas primeiras/últimas entre os dias
    # trabalhados (em vez de fazer a média de TODOS os horários de chegada,
    # o que incluía visitas do meio do turno e distorcia o resultado).
    stats = {}
    for t in ["Manhã", "Tarde"]:
        sub = df[(df["turno"] == t) & (~df["alerta_neg"])]
        if not sub.empty:
            por_dia_turno = sub.groupby("dia").agg(inicio=("dt_chegada", "min"), fim=("dt_saida", "max"))
            stats[f"inicio_{t.lower()}"] = _media_horario(por_dia_turno["inicio"])
            stats[f"fim_{t.lower()}"] = _media_horario(por_dia_turno["fim"])
        else:
            stats[f"inicio_{t.lower()}"] = None
            stats[f"fim_{t.lower()}"] = None

    return {
        "total_visitas": len(df),
        "dias_trabalhados": df["dia"].nunique(),
        "media_min": round(dv["duracao_capada"].mean(), 2) if not dv.empty else 0,
        "mediana_min": round(dv["duracao_capada"].median(), 2) if not dv.empty else 0,
        "visitas_rapidas": int(df["alerta_rapida"].sum()),
        "visitas_longas": int(df["alerta_longa"].sum()),
        "visitas_negativas": int(df["alerta_neg"].sum()),
        "pct_rapidas": round(df["alerta_rapida"].mean() * 100, 2),
        "visitas_por_dia": round(len(df) / max(df["dia"].nunique(), 1), 2),
        "dias_atingiu_meta": int((por_dia >= meta_da_equipe(df["equipe"].iloc[0] if ("equipe" in df.columns and len(df)) else None)).sum()),
        "visitas_duplicadas": total_duplicadas,
        "pct_duplicadas": pct_duplicadas,
        "visitas_seq_suspeita": total_seq_suspeita,
        "pct_seq_suspeita": pct_seq_suspeita,
        "maior_seq_suspeita": maior_seq_suspeita,
        "visitas_horario_almoco": total_almoco,
        "pct_horario_almoco": pct_almoco,
        "visitas_fora_expediente": total_fora_expediente,
        "pct_fora_expediente": pct_fora_expediente,
        "media_horas_trabalhadas_dia": media_horas_trabalhadas_dia,
        "media_horas_trabalhadas_semana": media_horas_trabalhadas_semana,
        "media_horas_uteis_dia": media_horas_uteis_dia,
        "custo_hora_util": custo_hora_util,
        **stats,
    }


def resumo_por_area(df, fechados_por_area=None, recusados_por_area=None):
    if df.empty:
        return pd.DataFrame()
    fechados_por_area = fechados_por_area or {}
    recusados_por_area = recusados_por_area or {}

    # Exclui visitas com duração negativa do cálculo de tempo médio/mediana
    # (mesmo motivo do resumo por agente — bug do sistema, ver aba "Visitas Negativas").
    dv = df[df["duracao_min"].notna() & (df["duracao_min"] >= 0)].copy()
    dv["duracao_capada"] = dv["duracao_min"].clip(upper=TETO_DURACAO_MEDIA_MIN)
    agg = dv.groupby("area").agg(
        qtd_visitas=("imovel", "count"),
        tempo_medio=("duracao_capada", "mean"),
        tempo_mediana=("duracao_capada", "median"),
        rapidas=("alerta_rapida", "sum")
    ).reset_index()

    q_lista = df.groupby("area")["quarteirao"].apply(
        lambda x: ", ".join(sorted(set(x.dropna().astype(str))))
    ).reset_index(name="quarteiroes")
    q_qtd = df.groupby("area")["quarteirao"].nunique().reset_index(name="qtd_quarteiroes")

    agg = agg.merge(q_lista, on="area").merge(q_qtd, on="area")
    agg["tempo_medio"] = agg["tempo_medio"].round(2)
    agg["tempo_mediana"] = agg["tempo_mediana"].round(2)
    agg["pct_rapidas"] = (agg["rapidas"] / agg["qtd_visitas"] * 100).round(2)

    agg["qtd_fechados"] = agg["area"].map(fechados_por_area).fillna(0).astype(int)
    agg["qtd_recusados"] = agg["area"].map(recusados_por_area).fillna(0).astype(int)
    total_geral_area = agg["qtd_visitas"] + agg["qtd_fechados"] + agg["qtd_recusados"]
    agg["pct_pendencia_area"] = ((agg["qtd_fechados"] + agg["qtd_recusados"]) / total_geral_area.replace(0, pd.NA) * 100).round(2).fillna(0)

    agg["alerta"] = agg["pct_rapidas"].apply(lambda p: _classificar(p)[0])
    return agg.sort_values("tempo_medio")


def _classificar(pct_rapidas):
    """
    Classificação baseada no % DE VISITAS RÁPIDAS (< TEMPO_MIN_VISITA_MIN):
      - até 10%      -> 🟢 NORMAL/OK
      - 11% a 20%    -> 🟡 ATENÇÃO
      - acima de 20% -> 🔴 CRÍTICO
    """
    if pct_rapidas <= PCT_RAPIDAS_OK_ATE:
        return "🟢 NORMAL", "D6F5D6"
    if pct_rapidas <= PCT_RAPIDAS_ATENCAO_ATE:
        return "🟡 ATENÇÃO", "FFF9B0"
    return "🔴 CRÍTICO", "FFB3B3"
