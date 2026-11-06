# -*- coding: utf-8 -*-
"""Preparação das abas de ausências, cronograma, pendências e ranking.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import re
import json
from datetime import date, datetime, timedelta
import pandas as pd
from .parametros import (
    CRONOGRAMA_AUSENCIAS,
    DIAS_UTEIS_MES,
    HORA_EXPEDIENTE_MANHA_FIM,
    HORA_EXPEDIENTE_MANHA_INICIO,
    HORA_EXPEDIENTE_TARDE_FIM,
    HORA_EXPEDIENTE_TARDE_INICIO,
    _cache_nomes_agentes,
)
from .pontos import (
    AVISO_AFASTAMENTO_FRACAO_MAX,
    AVISO_AFASTAMENTO_PERIODO_MAX_DIAS,
    AVISO_AFASTAMENTO_TURNOS_MIN,
    CLASSIF_POSSIVEL_EVENTO,
    CLASSIF_TURNO_SEM_LANCAMENTO,
    CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE,
    EVENTO_COLETIVO_A_PARTIR_DE,
    LIMITE_AGENTES_EVENTO_TURNO,
    MOTIVOS_EVENTO_COLETIVO,
    _ranking_sem_normalizacao,
)
from .auxiliares import NOMES_DIA_SEMANA, _meios_turnos_no_dia, _obter_motivo_cronograma
from .deteccao import (
    EQUIPES_SEM_DETECCAO_AUTOMATICA,
    _dias_paralisacao_coletiva_no_mes,
    _dias_uteis_alvo_periodo,
    _dias_uteis_no_intervalo,
    _feriados_em_vigor,
)
from .calculos import calcular_pontuacao

log = logging.getLogger("evisita")


_CACHE_PRIMEIRA_VISITA = {}


def _primeira_visita_historica(pasta="data/semanas"):
    """{id_agente: date da PRIMEIRA visita em TODO o cache de semanas}.

    Por que existe: _preparar_ausencias avaliava cada agente só a partir da
    primeira visita DENTRO do período (ex.: o mês). Quem passava as primeiras
    semanas do mês sem visita (e sem férias/atestado lançado) simplesmente
    não ganhava falta nenhuma por esses dias — parecia 'entrou depois'. Com a
    primeira visita de todo o histórico, só quem de fato começou depois do
    início do período é poupado. Cache em memória por (arquivos, mtime)."""
    try:
        arquivos = sorted(
            f for f in os.listdir(pasta) if re.fullmatch(r"\d+\.xlsx", f))
    except OSError:
        return {}
    chave = (pasta, tuple((f, os.path.getmtime(os.path.join(pasta, f))) for f in arquivos))
    if chave in _CACHE_PRIMEIRA_VISITA:
        return _CACHE_PRIMEIRA_VISITA[chave]
    primeira = {}
    try:
        import openpyxl
        for f in arquivos:
            wb = openpyxl.load_workbook(os.path.join(pasta, f), read_only=True, data_only=True)
            ws = wb["visitas"] if "visitas" in wb.sheetnames else wb[wb.sheetnames[0]]
            linhas = ws.iter_rows(values_only=True)
            cab = next(linhas, None)
            if not cab or "id_agente" not in cab or "data_chegada" not in cab:
                continue
            i_ag, i_dt = cab.index("id_agente"), cab.index("data_chegada")
            for lin in linhas:
                try:
                    ag, dt = lin[i_ag], lin[i_dt]
                    if ag is None or not dt:
                        continue
                    dia = datetime.strptime(str(dt)[:10], "%d/%m/%Y").date()
                    ag = int(ag)
                except (ValueError, TypeError, IndexError):
                    continue
                if ag not in primeira or dia < primeira[ag]:
                    primeira[ag] = dia
            wb.close()
    except Exception as e:  # nunca derruba a coleta por causa disso
        log.warning("⚠️ Não consegui ler a primeira visita histórica (%s) — usando só o período.", e)
        return {}
    _CACHE_PRIMEIRA_VISITA.clear()
    _CACHE_PRIMEIRA_VISITA[chave] = primeira
    return primeira


# Dia "de hoje" (fuso de Ponta Porã/MS). O dia em andamento NUNCA gera
# ausência nem entra nos dias esperados de quem ainda não visitou: o agente
# pode simplesmente não ter lançado ainda. Os testes trocam isso por uma data fixa.
HOJE_OVERRIDE = None

def _hoje_local():
    if HOJE_OVERRIDE is not None:
        return HOJE_OVERRIDE
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Campo_Grande")).date()
    except Exception:
        return date.today()


def _preparar_ausencias(df_total, resultados, lista_cronograma=None, primeira_visita=None):
    """
    Para cada agente, dia útil e turno (Manhã 7h-11h / Tarde 13h-17h) dentro
    do período coberto pelos dados coletados, verifica se houve pelo menos
    uma visita registrada. Se não houve, lista como possível ausência
    (folga, atestado, falta — precisa confirmar com a escala da equipe).

    IMPORTANTE: cada agente só é avaliado a partir da PRÓPRIA primeira
    visita, nunca da data mínima global (mesma correção aplicada em
    detectar_ausencias_e_paralisacoes — ver o comentário lá pro porquê:
    sem isso, um agente/equipe que começou depois do início do período
    rastreado aparece com uma enxurrada de "possível ausência" falsa pra
    cada dia antes de sequer ter começado a trabalhar).
    """
    if df_total.empty:
        return []

    dia_max = df_total["dia"].max()

    turnos_oficiais = [
        ("Manhã", HORA_EXPEDIENTE_MANHA_INICIO, HORA_EXPEDIENTE_MANHA_FIM),
        ("Tarde", HORA_EXPEDIENTE_TARDE_INICIO, HORA_EXPEDIENTE_TARDE_FIM),
    ]

    registros = []
    cobertos_evento = {}  # (dia_fmt, turno) -> agentes sem lançamento, cobertos por chuva/reunião (só contam no limite se a opção estiver ligada)
    ativos = {}  # (equipe, dia_fmt, turno) -> agentes avaliados e NÃO cobertos pelo cronograma (trabalharam ou não)
    feriados_validos = {datetime.strptime(f, "%d/%m/%Y").date() for f in _feriados_em_vigor()}
    dia_min_periodo = df_total["dia"].min()
    if primeira_visita is None:
        primeira_visita = _primeira_visita_historica()
    for res in resultados:
        df_ag = df_total[df_total["id_agente"] == res["id_agente"]]
        if df_ag.empty:
            continue
        dia_min_agente = df_ag["dia"].min()  # primeira visita do agente NESTE período
        # Quem já trabalhava ANTES do período começar é avaliado desde o 1º
        # dia do período (não desde a 1ª visita dele no período): dias sem
        # visita no começo do mês contam. Só quem de fato começou depois
        # (1ª visita histórica dentro do período) é poupado dos dias antes.
        # (Equipes que trabalham sob demanda — EQUIPES_SEM_DETECCAO_AUTOMATICA,
        # ex.: Bloqueio — mantêm a regra antiga: não têm "dia esperado" fixo.)
        hist = primeira_visita.get(res["id_agente"])
        sob_demanda = res["equipe"].lower() in {e.lower() for e in EQUIPES_SEM_DETECCAO_AUTOMATICA}
        if hist is not None and hist < dia_min_periodo and not sob_demanda:
            dia_min_agente = dia_min_periodo
        dias_uteis = pd.bdate_range(start=dia_min_agente, end=dia_max)
        dias_com_visita = set(df_ag["dia"])

        for dia_ts in dias_uteis:
            dia = dia_ts.date()
            if dia >= _hoje_local():
                continue  # dia em andamento (ou futuro): ainda não dá pra cobrar lançamento
            if dia in feriados_validos and dia not in dias_com_visita:
                continue  # feriado nacional sem visita: não é ausência (antes contava como 2 turnos sem lançamento)
            if dia not in dias_com_visita:
                # Nenhuma visita nesse dia inteiro: ausência nos dois turnos
                turnos_ausentes = turnos_oficiais
            else:
                sub_dia = df_ag[df_ag["dia"] == dia]
                turnos_ausentes = [
                    (nome, ini, fim) for nome, ini, fim in turnos_oficiais
                    if not ((sub_dia["hora_chegada"] >= ini) & (sub_dia["hora_chegada"] < fim)).any()
                ]

            dia_fmt = dia.strftime("%d/%m/%Y")
            nomes_ausentes = {t[0] for t in turnos_ausentes}
            if not sob_demanda:
                for turno_nome, _, _ in turnos_oficiais:
                    if turno_nome not in nomes_ausentes:  # trabalhou nesse turno: conta como ativo
                        ativos[(res["equipe"], dia_fmt, turno_nome)] = ativos.get((res["equipe"], dia_fmt, turno_nome), 0) + 1

            for turno_nome, _, _ in turnos_ausentes:
                # Antes de descontar: chuva, treinamento, atestado, férias, folga,
                # reunião... (tudo que está no cronograma, inclusive as detecções confirmadas).
                motivo = _obter_motivo_cronograma(res["id_agente"], res["equipe"], dia, lista_cronograma,
                                                  turno=turno_nome)
                if motivo:
                    if not sob_demanda and motivo in MOTIVOS_EVENTO_COLETIVO:
                        kc = (dia_fmt, turno_nome)
                        cobertos_evento[kc] = cobertos_evento.get(kc, 0) + 1
                    continue  # dia/turno já explicado (cronograma, ou detecção confirmada) — não é ausência a investigar
                if not sob_demanda:
                    ativos[(res["equipe"], dia_fmt, turno_nome)] = ativos.get((res["equipe"], dia_fmt, turno_nome), 0) + 1
                registros.append({
                    "id_agente": res["id_agente"],
                    "nome_agente": res["nome_agente"],
                    "equipe": res["equipe"],
                    "dia_fmt": dia_fmt,
                    "dia_semana": NOMES_DIA_SEMANA.get(dia_ts.weekday(), ""),
                    "turno": turno_nome,
                    "classificacao": CLASSIF_TURNO_SEM_LANCAMENTO,
                    "sob_demanda": sob_demanda,
                    "observacao": f"{CLASSIF_TURNO_SEM_LANCAMENTO} — sem visita registrada nesse turno e sem justificativa no cronograma "
                                  "(possível folga, atestado ou falta; confirmar com a escala). Desconta pontos.",
                    "_fill": "E8E8E8",
                })

    # Ausência COLETIVA no turno -> "Possível Evento Externo ou Interno" (sem desconto).
    # Ver LIMITE_AGENTES_EVENTO_TURNO acima: 20+ agentes no mesmo turno, ou a
    # equipe inteira (agentes ativos) sem lançamento naquele turno.
    ausentes_equipe, ausentes_global = {}, {}
    for r in registros:
        if r["sob_demanda"]:
            continue
        ke = (r["equipe"], r["dia_fmt"], r["turno"])
        kg = (r["dia_fmt"], r["turno"])
        ausentes_equipe[ke] = ausentes_equipe.get(ke, 0) + 1
        ausentes_global[kg] = ausentes_global.get(kg, 0) + 1

    for r in registros:
        if r.pop("sob_demanda"):
            continue
        ke = (r["equipe"], r["dia_fmt"], r["turno"])
        n_equipe, n_ativos = ausentes_equipe[ke], ativos.get(ke, 0)
        kg = (r["dia_fmt"], r["turno"])
        n_cobertos = cobertos_evento.get(kg, 0) if CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE else 0
        n_global = ausentes_global[kg] + n_cobertos
        muitos = n_global >= LIMITE_AGENTES_EVENTO_TURNO
        toda_equipe = n_ativos >= 2 and n_equipe >= n_ativos
        if not (muitos or toda_equipe):
            continue
        if (EVENTO_COLETIVO_A_PARTIR_DE is not None
                and datetime.strptime(r["dia_fmt"], "%d/%m/%Y").date() < EVENTO_COLETIVO_A_PARTIR_DE):
            continue  # período anterior à regra: continua Turno sem Lançamento
        motivos = []
        if muitos:
            extra = f", {n_cobertos} já cobertos por chuva/reunião" if n_cobertos else ""
            motivos.append(f"{n_global} agentes sem lançamento neste turno (limite de {LIMITE_AGENTES_EVENTO_TURNO}{extra}) — possível evento externo ou interno")
        elif toda_equipe:
            motivos.append(f"toda a equipe ({n_equipe} de {n_ativos} agentes ativos) sem lançamento neste turno — possível chuva isolada ou reunião da equipe")
        r["classificacao"] = CLASSIF_POSSIVEL_EVENTO
        r["observacao"] = (f"{CLASSIF_POSSIVEL_EVENTO} — " + " e ".join(motivos) +
                           ". Sem desconto de pontos; confirme o motivo (chuva, reunião, capacitação, evento) no cronograma.")
        r["_fill"] = "FFD9A0"

    for r in registros:
        r.pop("sob_demanda", None)
    registros.sort(key=lambda r: (r["equipe"], r["dia_fmt"], r["turno"], r["nome_agente"]))
    return registros


def _preparar_cronograma(resultados, data_min=None, data_max=None, lista_cronograma=None):
    """
    Lista, de forma unificada e ordenada por data, todo o cronograma de
    ausências programadas (chuva, folga, atestado, reunião/treinamento,
    férias, levantamento de índice, ovitrampa, recuperação de casas — alvo
    agente/equipe/todos — mais as detecções automáticas CONFIRMADAS, se
    `lista_cronograma` for o resultado de _cronograma_efetivo()).

    Se data_min/data_max forem passados (o período coberto pela planilha
    sendo gerada, tirado de df_total), só entram registros cujo período se
    sobrepõe a esse intervalo — é isso que faz o Cronograma ficar
    INDEPENDENTE por mês: gerando Agosto, só aparecem os registros de
    Agosto; gerando Julho, só os de Julho, mesmo que
    data/cronograma_ausencias.json tenha entradas de vários meses juntas.
    """
    nomes_por_id = {res["id_agente"]: res["nome_agente"] for res in resultados}
    lista = lista_cronograma if lista_cronograma is not None else CRONOGRAMA_AUSENCIAS

    registros = []
    for entrada in lista:
        try:
            entrada_inicio = pd.to_datetime(entrada.get("inicio", ""), format="%d/%m/%Y", errors="coerce")
            entrada_fim = pd.to_datetime(entrada.get("fim", ""), format="%d/%m/%Y", errors="coerce")
        except (ValueError, TypeError):
            entrada_inicio = entrada_fim = pd.NaT
        if data_min is not None and data_max is not None and pd.notna(entrada_inicio) and pd.notna(entrada_fim):
            # Sobreposição de intervalos: sobra fora se o registro termina
            # antes do período começar OU começa depois do período terminar.
            if entrada_fim.date() < data_min or entrada_inicio.date() > data_max:
                continue

        alvo = entrada.get("alvo", "agente")
        if alvo == "todos":
            alvo_fmt = "Todos os agentes"
        elif alvo == "equipe":
            alvo_fmt = entrada.get("equipe", "—")
        else:
            id_ag = entrada.get("id_agente")
            # Cronograma pode ser gerado num RECORTE (um mês/semana só, nas
            # páginas de histórico) — se o agente não teve NENHUM
            # lançamento dentro desse recorte específico (o caso mais
            # comum: o mês inteiro de férias, tipo aqui), ele não aparece
            # em `resultados` (que só cobre o recorte) e cai no genérico,
            # MESMO que o nome dele já seja conhecido globalmente. Cai pro
            # cache persistente antes de desistir — sem isso, "Julho/2026"
            # isolado mostra "Agente_86" mesmo com o Acumulado (que enxerga
            # o ano inteiro, inclusive os meses em que ele trabalhou)
            # mostrando o nome certo.
            nome_no_cache = _cache_nomes_agentes().get(str(id_ag), {}).get("nome")
            alvo_fmt = nomes_por_id.get(id_ag) or nome_no_cache or f"Agente_{id_ag}"
        motivo = entrada.get("motivo", "")
        motivo_base = motivo.replace(" (confirmada)", "").replace(" (automático)", "")
        if entrada.get("turno"):
            motivo = f"{motivo} ({entrada['turno']})"
        registros.append({
            "dia_inicio": entrada.get("inicio", ""),
            "dia_fim": entrada.get("fim", ""),
            "motivo": motivo,
            "alvo_fmt": alvo_fmt,
            "_fill": {"Chuva": "D6E4F0", "Reunião/Treinamento": "D6E4F0", "Reunião/atividade coletiva": "D6E4F0",
                      "Férias": "E0D6F0", "Férias/Atestado": "E0D6F0", "Folga": "E0D6F0", "Meia folga": "E0D6F0", "Atestado": "F0DCD6",
                      "Ausência justificada": "F0DCD6", "Meia ausência justificada": "F0DCD6", "Capacitação": "D6E4F0",
                      "Levantamento de Índice": "D6F0DC", "Instalação de Ovitrampa": "D6F0DC",
                      "Recolha de Ovitrampa": "D6F0DC", "Recuperação de Casas": "D6F0DC",
                      "Outra atividade coletiva": "E8E8E8"}.get(motivo_base, "E8E8E8"),
            "_ordenacao": entrada_inicio,
        })

    registros.sort(key=lambda r: r["_ordenacao"] or pd.Timestamp.min)
    for r in registros:
        del r["_ordenacao"]
    return registros


def _preparar_pendencias_resumo(resultados):
    """
    Resumo de pendência por agente (abertos/fechados/recusados/total/% pendência),
    com uma linha de TOTAL GERAL consolidando todos os agentes ao final.
    """
    registros = []
    soma_abertos = soma_fechados = soma_recusados = 0
    for res in resultados:
        r = res["resumo"]
        abertos = r["total_visitas"]
        fechados = r.get("imoveis_fechados", 0)
        recusados = r.get("imoveis_recusados", 0)
        total_geral = r.get("total_geral_pendencia", abertos + fechados + recusados)
        pct = r.get("pct_pendencia", 0)

        soma_abertos += abertos
        soma_fechados += fechados
        soma_recusados += recusados

        registros.append({
            "nome_agente": res["nome_agente"],
            "equipe": res["equipe"],
            "abertos": abertos,
            "fechados": fechados,
            "recusados": recusados,
            "total_geral": total_geral,
            "pct_pendencia": pct,
        })

    soma_geral = soma_abertos + soma_fechados + soma_recusados
    pct_geral = round(((soma_fechados + soma_recusados) / soma_geral * 100), 2) if soma_geral > 0 else 0
    registros.append({
        "nome_agente": "TOTAL GERAL",
        "equipe": "—",
        "abertos": soma_abertos,
        "fechados": soma_fechados,
        "recusados": soma_recusados,
        "total_geral": soma_geral,
        "pct_pendencia": pct_geral,
        "_fill": "D9D9D9",
    })
    return registros


def _observacao_ranking(res, qtd_ausencias, dias_periodo, alvo_exibido, sem_normalizacao,
                        lista_cronograma, data_min, data_max):
    """Texto da coluna Observação do ranking: avisa quando o agente parece ter
    um afastamento (férias/licença/atestado) que não está no cronograma —
    trabalhou bem menos dias que o esperado E tem vários turnos sem lançamento.
    Só em períodos de ~1 mês (no Acumulado os números não são comparáveis).
    Devolve "" quando não há nada a avisar."""
    if not dias_periodo or data_min is None or data_max is None:
        return ""
    if (data_max - data_min).days > AVISO_AFASTAMENTO_PERIODO_MAX_DIAS:
        return ""
    if sem_normalizacao:
        esperados = alvo_exibido   # já desconta o cronograma
    else:
        dias_trab = set(res["df"]["dia"]) if "dia" in res["df"].columns else set()
        esperados = len(dias_periodo) - sum(
            1 for d in dias_periodo
            if d not in dias_trab and _obter_motivo_cronograma(res["id_agente"], res["equipe"], d, lista_cronograma))
    trab = res["resumo"]["dias_trabalhados"]
    if esperados > 0 and trab < AVISO_AFASTAMENTO_FRACAO_MAX * esperados and qtd_ausencias >= AVISO_AFASTAMENTO_TURNOS_MIN:
        return (f"⚠️ Possível afastamento não registrado: trabalhou {trab} de {esperados} dias esperados "
                f"e tem {qtd_ausencias} turnos sem lançamento — conferir férias/licença/atestado no cronograma")
    return ""


CAMINHO_AJUSTES_RANKING = "data/ajustes_ranking.json"

def _carregar_ajustes_ranking(caminho=CAMINHO_AJUSTES_RANKING):
    """Ajustes MANUAIS de pontuação, lançados pelo gestor em
    data/ajustes_ranking.json. Cada item:
        {"id_agente": 116, "data": "15/10/2026", "pontos": 2.0,
         "motivo": "Instabilidade do e-Visita — visitas lançadas depois"}
    `pontos` positivo soma, negativo desconta. O ajuste vale em todo período
    que contenha `data` (o mês dela e o Acumulado), aparece no Detalhamento e
    no Extrato do agente com o motivo, e respeita o limite de 0 a 100.
    Itens inválidos são ignorados com aviso no log (validar_json.py barra
    esses erros antes da coleta). Devolve lista de dicts já validados, com
    "data" como objeto date."""
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8") as f:
            itens = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Ajustes de ranking ignorados — %s ilegível: %s", caminho, e)
        return []
    validos = []
    for i, it in enumerate(itens if isinstance(itens, list) else []):
        try:
            validos.append({
                "id_agente": int(it["id_agente"]),
                "data": datetime.strptime(str(it["data"]), "%d/%m/%Y").date(),
                "pontos": float(it["pontos"]),
                "motivo": str(it["motivo"]).strip() or "sem motivo informado",
            })
        except (KeyError, TypeError, ValueError) as e:
            log.warning("Ajuste de ranking #%s ignorado (%s): %s", i + 1, e, it)
    return validos


# DESEMPATE DO RANKING: quando duas ou mais pessoas fecham o período com a MESMA nota (hoje isso é comum:
# a nota é limitada a 100), quem tem a maior MÉDIA dos meses anteriores fica na frente. A média é a mesma
# da tabela "Média Mensal por Agente" do dashboard (média simples das notas mensais), mas só dos meses
# FECHADOS ANTES do período sendo calculado — o próprio mês empatado não entra, senão o empate se
# decidiria pelo que acabou de empatar. Quem não tem histórico fica atrás de quem tem; se a média
# também empatar, vale a ordem de antes (estável).
CAMINHO_MANIFEST_HISTORICO = "data/historico/manifest.json"
PASTA_HISTORICO = "data/historico"
_RE_LABEL_MES = re.compile(r"^[^\W\d_]+/\d{4}$")


def _ler_notas_ranking(caminho):
    """{nome_agente: pontuação final} da tabela principal da aba Ranking de uma planilha mensal."""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        if "Ranking" not in wb.sheetnames:
            return {}
        out, i_ag, i_pt = {}, None, None
        for vals in wb["Ranking"].iter_rows(values_only=True):
            if i_ag is None:
                if vals and "Agente" in vals and "Pontuação Final" in vals:
                    i_ag, i_pt = list(vals).index("Agente"), list(vals).index("Pontuação Final")
                continue
            if not vals or vals[i_ag] is None:
                break
            try:
                out[str(vals[i_ag]).strip()] = float(vals[i_pt])
            except (TypeError, ValueError):
                continue
        return out
    finally:
        wb.close()


def _media_historica_por_agente(data_min, manifest=CAMINHO_MANIFEST_HISTORICO, pasta=PASTA_HISTORICO):
    """{nome_agente: média das notas dos meses anteriores ao período que começa em `data_min`}.
    Vazio se não houver data, manifesto ou meses anteriores (aí o desempate simplesmente não age)."""
    if data_min is None:
        return {}
    try:
        from semanas_evisita import html_id_da_data
        inicio = html_id_da_data(data_min - timedelta(days=(data_min.weekday() + 1) % 7))
        with open(manifest, encoding="utf-8") as f:
            entradas = json.load(f)
        notas = {}
        for e in entradas:
            if e.get("tipo") == "semana" or not _RE_LABEL_MES.match(str(e.get("label", ""))):
                continue
            if int(e.get("semana_fim", 0)) >= inicio:      # mês do próprio período (ou posterior): fora
                continue
            caminho = os.path.join(pasta, e["arquivo"])
            if not os.path.exists(caminho):
                continue
            for nome, pts in _ler_notas_ranking(caminho).items():
                notas.setdefault(nome, []).append(pts)
        return {n: sum(v) / len(v) for n, v in notas.items() if v}
    except Exception as exc:  # desempate é acessório: nunca pode derrubar a coleta
        log.warning("Desempate por média histórica indisponível: %s", exc)
        return {}


def _preparar_ranking(resultados, regs_ausencias, data_max=None, lista_cronograma=None, data_min=None, ajustes=None):
    """
    Calcula a pontuação de cada agente (calcular_pontuacao) e monta:
      - lista principal ordenada por pontuação (posição 1 = maior pontuação)
      - lista de detalhamento (todos os critérios aplicados, por agente)

    `data_min`/`data_max`: primeira/última data do período sendo consolidado
    (df_total["dia"].min()/.max()). Usadas pra decidir o ALVO ("1 mês de
    calibração") do fator de normalização — ver _dias_uteis_alvo_periodo e a
    docstring de calcular_pontuacao(). Se `data_max` não vier (uso avulso/
    testes), cai no DIAS_UTEIS_MES fixo de sempre.

    `lista_cronograma`: cronograma efetivo (ver _cronograma_efetivo) — usado
    pra descontar do alvo de cada agente os dias em que a EQUIPE dele
    inteira ficou parada por chuva/capacitação/reunião (ver
    _dias_paralisacao_coletiva_no_mes). Sem isso, esses dias contariam como
    "deveria ter trabalhado" no alvo, mesmo não sendo culpa de ninguém.
    """
    ajustes_todos = _carregar_ajustes_ranking() if ajustes is None else ajustes
    # Ranking novo (sem normalização): ver RANKING_SEM_NORMALIZACAO_A_PARTIR_DE.
    sem_normalizacao = _ranking_sem_normalizacao(data_min, data_max)
    if sem_normalizacao and data_max is not None:
        # Método novo: os dias úteis esperados são os do PRÓPRIO período — do
        # domingo que abre a primeira semana (ex.: 04/10 pra Outubro) até a
        # última data. NÃO do dia 1º do mês civil: 01 e 02/10 pertencem à
        # semana 326 (Setembro) e inflariam o esperado de Outubro em 2 dias.
        inicio_periodo = data_min - timedelta(days=(data_min.weekday() + 1) % 7)
        dias_do_mes = _dias_uteis_no_intervalo(inicio_periodo, data_max)
    else:
        dias_do_mes = _dias_uteis_alvo_periodo(data_min, data_max) if data_max is not None else []
    alvo_dias_mes_base = len(dias_do_mes) if dias_do_mes else DIAS_UTEIS_MES

    ausencias_por_agente = {}  # id_agente -> contagem — NUNCA por nome (agentes
    # diferentes podem ter o mesmo nome; contar por nome misturaria as
    # ausências de um com a pontuação do outro)
    turnos_por_dia = {}  # (id_agente, dia) -> nº de turnos sem lançamento
    eventos_por_dia = {}  # (id_agente, dia_fmt) -> turnos classificados como possível evento (sem desconto)
    for r in regs_ausencias:
        id_ag = r.get("id_agente")
        if id_ag is None:
            continue
        if r.get("classificacao") == CLASSIF_POSSIVEL_EVENTO:
            k_ev = (id_ag, r.get("dia_fmt"))
            eventos_por_dia[k_ev] = eventos_por_dia.get(k_ev, 0) + 1
            continue  # não é Turno sem Lançamento: não desconta
        ausencias_por_agente[id_ag] = ausencias_por_agente.get(id_ag, 0) + 1
        chave_dia = (id_ag, r.get("dia_fmt"))
        turnos_por_dia[chave_dia] = turnos_por_dia.get(chave_dia, 0) + 1
    dias_inteiros_por_agente = {}
    for (id_ag, _dia), n_turnos in turnos_por_dia.items():
        if n_turnos >= 2:
            dias_inteiros_por_agente[id_ag] = dias_inteiros_por_agente.get(id_ag, 0) + 1

    principal, todos_detalhes = [], []
    for res in resultados:
        qtd_ausencias = ausencias_por_agente.get(res["id_agente"], 0)
        if dias_do_mes and sem_normalizacao:
            # Método novo: "esperado" = dias úteis do período menos os dias
            # JUSTIFICADOS pelo cronograma (férias, atestado, folga, chuva,
            # reunião...) em que o agente NÃO trabalhou. Dia justificado em
            # que ele trabalhou mesmo assim continua contando como esperado
            # (senão "trabalhados" passaria de "esperados"). Só exibição:
            # nenhum fator usa esse número.
            dias_trab = set(res["df"]["dia"]) if "dia" in res["df"].columns else set()
            justificados = 0.0
            for d in dias_do_mes:
                if d not in dias_trab and _obter_motivo_cronograma(
                        res["id_agente"], res["equipe"], d, lista_cronograma):
                    justificados += 1
                else:
                    # meia folga / meia ausência justificada: 0,5 dia por turno
                    justificados += 0.5 * _meios_turnos_no_dia(
                        res["id_agente"], res["equipe"], d, lista_cronograma)
                    # turnos classificados como possível evento coletivo: 0,5 dia cada
                    justificados += 0.5 * eventos_por_dia.get((res["id_agente"], d.strftime("%d/%m/%Y")), 0)
            # Dia em andamento: quem ainda não visitou hoje não "deve" o dia de hoje.
            hoje = _hoje_local()
            if hoje in dias_do_mes and hoje not in dias_trab:
                justificados += 1
            alvo_dias_mes = max(alvo_dias_mes_base - justificados, 0)
        elif dias_do_mes:
            dias_coletivos = _dias_paralisacao_coletiva_no_mes(
                res["id_agente"], res["equipe"], dias_do_mes, lista_cronograma)
            alvo_dias_mes = max(alvo_dias_mes_base - dias_coletivos, 1)
        else:
            alvo_dias_mes = alvo_dias_mes_base
        ajustes_agente = [(a["motivo"], a["pontos"]) for a in ajustes_todos
                          if a["id_agente"] == res["id_agente"] and data_min is not None and data_max is not None
                          and data_min <= a["data"] <= data_max]
        pontos, classif, fill, detalhes = calcular_pontuacao(
            res, qtd_ausencias, alvo_dias_mes, normalizar_periodo=not sem_normalizacao,
            ajustes=ajustes_agente,
            aplicar_presenca_minima=(sem_normalizacao and res["equipe"].lower()
                                     not in {e.lower() for e in EQUIPES_SEM_DETECCAO_AUTOMATICA}),
            dias_inteiros_sem_lancamento=(
                0 if res["equipe"].lower() in {e.lower() for e in EQUIPES_SEM_DETECCAO_AUTOMATICA}
                else dias_inteiros_por_agente.get(res["id_agente"], 0)))
        principal.append({
            "nome_agente": res["nome_agente"],
            "equipe": res["equipe"],
            # Dias trabalhados x Dias úteis esperados no mês (já descontando
            # chuva/capacitação/reunião da própria equipe) ficam expostos
            # aqui pra QUALQUER gestor — mesmo sem entender a fórmula por
            # trás — enxergar de cara se a pontuação de alguém foi ajustada
            # por ter trabalhado menos (ou mais) dias que o esperado no mês,
            # sem precisar abrir a aba de Detalhe. Ver calcular_pontuacao().
            "dias_trabalhados": res["resumo"]["dias_trabalhados"],
            "dias_uteis_esperados": alvo_dias_mes,
            # Turnos sem trabalhar (ausência não justificada — já exclui
            # chuva/reunião/capacitação/férias, ver detectar_ausencias_e_
            # paralisacoes) exposto direto na tabela principal também, não
            # só na aba de Detalhe — é o critério de maior peso (−1,5/turno)
            # e o gestor precisa ver de cara quantos turnos cada agente
            # perdeu, sem precisar contar linha por linha no Detalhamento.
            "turnos_sem_trabalhar": qtd_ausencias,
            "pontos": pontos,
            "classificacao": classif,
            "observacao": _observacao_ranking(res, qtd_ausencias, dias_do_mes, alvo_dias_mes,
                                              sem_normalizacao, lista_cronograma, data_min, data_max),
            "_fill": fill,
        })
        for d in detalhes:
            d["_fill"] = "FFE0E0" if d["pontos"] < 0 else "E0FFE0"
        todos_detalhes.extend(detalhes)

    media_hist = _media_historica_por_agente(data_min)
    for r in principal:   # média arredondada em 1 casa, como aparece na tabela "Média Mensal por Agente"
        m = media_hist.get(str(r["nome_agente"]).strip())
        r["_media_hist"] = -1.0 if m is None else round(m, 1)
    principal.sort(key=lambda r: (r["pontos"], r["_media_hist"]), reverse=True)
    for i, r in enumerate(principal, 1):
        r["posicao"] = i

    todos_detalhes.sort(key=lambda d: (d["nome_agente"], d["motivo"]))
    return principal, todos_detalhes


def _preparar_recusados_detalhe(resultados):
    """Lista individual de todos os imóveis com visita recusada pelo morador."""
    registros = []
    for res in resultados:
        for v in res.get("visitas_recusados_raw", []):
            registros.append({
                "nome_agente": v["nome_agente"],
                "equipe": v["equipe"],
                "id_visita": v["id_visita"] if v.get("id_visita") else "",
                "area": v["area"],
                "quarteirao": v["quarteirao"],
                "logradouro": v["logradouro"],
                "imovel": v["imovel"],
                "data_chegada": v["data_chegada"],
                "data_saida": v["data_saida"],
                "_fill": "F4CCCC",
            })
    registros.sort(key=lambda r: (r["nome_agente"], r["data_chegada"]))
    return registros
