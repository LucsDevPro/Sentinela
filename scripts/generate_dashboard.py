#!/usr/bin/env python3
"""
Gera index.html (S E N T I N E L A - HUB) a partir de data/Analise_Consolidada.xlsx.

Este script só carrega e prepara os dados; toda a montagem do HTML fica nos
templates Jinja2 em scripts/templates/. Ver README.md para detalhes.

Uso:
    python scripts/generate_dashboard.py
    python scripts/generate_dashboard.py data/Analise_Consolidada.xlsx index.html
"""
import sys
import os
import re
import json
from pathlib import Path
from datetime import date, datetime, timezone, timedelta

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx_scan import get_tables  # noqa: E402
import semanas_evisita as sem_evisita  # noqa: E402
import icones  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAZY = os.environ.get("SENTINELA_SEM_LAZY") != "1"   # partes pesadas em arquivos separados (padrão)

# Precisam bater com as constantes de mesmo nome em scripts/coleta/
# — usadas só pra dar contexto/comparação na tabela "Outras Atividades" do
# Custos (equipes fora do e-Visita, com produção lançada manualmente em
# data/outras_atividades.json).
DIAS_UTEIS_MES_REF = 22
META_VISITAS_DIA_REF = 20
TETO_VISITA_MIN = 20       # = TETO_DURACAO_MEDIA_MIN de scripts/coleta/parametros.py (cada visita conta no máx. 20 min nas horas úteis)

# Painel "Custos & Produtividade": faixas de cor e regra de confiabilidade.
# Os gráficos (templates/charts.js) e as legendas (sections/custos.html) leem
# estes mesmos valores — mudou aqui, muda em todo lugar.
CUSTO_FAIXA_MEDIO = 100     # R$/h útil: até aqui = verde
CUSTO_FAIXA_ALTO = 150      # acima daqui = vermelho (entre os dois = amarelo)
HORAS_UTEIS_BAIXO = 1.5     # h/dia em visita: abaixo = vermelho
HORAS_UTEIS_ALTO = 2.5      # h/dia em visita: a partir daqui = verde
CUSTO_GRAFICO_MAX = 300      # R$/h: o gráfico de custo corta as barras aqui (quem passa disso aparece com barra cheia)
OUTRAS_ATIVIDADES_PATH = ROOT / "data" / "outras_atividades.json"


def carregar_outras_atividades():
    """Lê data/outras_atividades.json (equipes/atividades fora do e-Visita,
    com produção lançada manualmente) e calcula, pra cada equipe/mês: custo
    total da equipe, visitas por dia por pessoa, custo por visita, e quantas
    vezes abaixo da meta (META_VISITAS_DIA_REF) a produção por pessoa está —
    é essa comparação objetiva que demonstra o quão baixa é a produção,
    sem precisar de opinião."""
    if not OUTRAS_ATIVIDADES_PATH.exists():
        return []
    try:
        equipes = json.loads(OUTRAS_ATIVIDADES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    linhas = []
    for eq in equipes:
        membros = eq.get("membros", [])
        n_membros = max(len(membros), 1)
        salario = eq.get("salario_por_membro", 0)
        custo_equipe_mensal = salario * n_membros
        for prod in eq.get("producao_mensal", []):
            visitas = prod.get("visitas", 0)
            visitas_dia_pessoa = visitas / DIAS_UTEIS_MES_REF / n_membros if visitas else 0
            custo_por_visita = custo_equipe_mensal / visitas if visitas else None
            vezes_abaixo_meta = (META_VISITAS_DIA_REF / visitas_dia_pessoa) if visitas_dia_pessoa > 0 else None
            linhas.append({
                "equipe": eq.get("equipe", "—"),
                "membros": ", ".join(membros),
                "n_membros": n_membros,
                "mes": prod.get("mes", "—"),
                "visitas": visitas,
                "visitas_dia_pessoa": visitas_dia_pessoa,
                "custo_equipe_mensal": custo_equipe_mensal,
                "custo_por_visita": custo_por_visita,
                "vezes_abaixo_meta": vezes_abaixo_meta,
            })
    return linhas

SCRIPTS_DIR = Path(__file__).resolve().parent

# A homepage (index.html) é configurável em data/config_home.json — assim
# dá pra trocar qual período aparece na home sem mexer em código Python, só
# editando esse JSON (na mão ou pelo home_editor.html, que gera o texto
# certo pra colar nele). Formato:
#   {"arquivo": "data/historico/semanas_313-317.xlsx", "label": "Julho/2026"}
# "arquivo" é relativo à raiz do repositório. Se o config não existir (ou
# apontar pra um arquivo que sumiu), cai de volta pro acumulado de tudo
# (data/Analise_Consolidada.xlsx) pra nunca gerar uma home quebrada.
CONFIG_HOME_PATH = ROOT / "data" / "config_home.json"
ACUMULADO_XLSX = ROOT / "data" / "Analise_Consolidada.xlsx"


def resolver_home_xlsx():
    if CONFIG_HOME_PATH.exists():
        try:
            cfg = json.loads(CONFIG_HOME_PATH.read_text(encoding="utf-8"))
            caminho = ROOT / cfg["arquivo"]
            if caminho.exists():
                return caminho
            print(f"AVISO: data/config_home.json aponta para '{cfg['arquivo']}', que não existe. "
                  f"Usando o acumulado de tudo (data/Analise_Consolidada.xlsx) como home.")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"AVISO: data/config_home.json inválido ({e}). Usando o acumulado de tudo como home.")
    return ACUMULADO_XLSX


HOME_XLSX = resolver_home_xlsx()

XLSX_PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else HOME_XLSX
OUT_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "index.html"

SALARIO_MENSAL = 4863.00
EVISITA_URL = "https://evisita.saude.ms.gov.br/endemias/sis_visita/{}/detalhes"
DIA_ORDER = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

# A Equipe Bloqueio trabalha de forma diferente (majoritariamente sem o
# aplicativo) — seus resultados não entram nos gráficos/tabelas gerais
# (que comparam contra o padrão de quem usa o app todo dia); eles aparecem
# só na aba Ponto Estratégico, isolados dos agentes do tratamento.
EQUIPE_BLOQUEIO = "Equipe Bloqueio"

def sem_bloqueio(df):
    if df.empty or "Equipe" not in df.columns:
        return df
    return df[df["Equipe"] != EQUIPE_BLOQUEIO].copy()

def somente_bloqueio(df):
    if df.empty or "Equipe" not in df.columns:
        return df.iloc[0:0].copy()
    return df[df["Equipe"] == EQUIPE_BLOQUEIO].copy()

# ============================================================ filtros ====

def br(v, decimals=0):
    """Formata número no padrão pt-BR. Tolerante a valor ausente/indefinido
    (ex.: coluna nova que ainda não existe num Analise_Consolidada.xlsx
    gerado por uma versão antiga do coletar_evisita.py) — nesses casos
    mostra "—" em vez de quebrar o dashboard inteiro."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    try:
        s = f"{float(v):,.{decimals}f}"
    except Exception:
        return "—"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")

def class_key(text):
    t = str(text or "")
    if "CRÍTICO" in t or "CRITICO" in t:
        return "critico"
    if "ATENÇÃO" in t or "ATENCAO" in t:
        return "atencao"
    return "normal"

def badge(text):
    k = class_key(text)
    label = {"critico": "🔴 CRÍTICO", "atencao": "🟡 ATENÇÃO", "normal": "🟢 NORMAL"}[k]
    return Markup(f'<span class="badge badge-{k}">{label}</span>')

def row_class(text):
    k = class_key(text)
    return f"row-{k}" if k != "normal" else ""

def rank_class_key(text):
    """Classificação do ranking tem 4 faixas (Excelente/Bom/Atenção/Crítico),
    diferente das 3 faixas (Normal/Atenção/Crítico) usadas no resto do dashboard."""
    t = str(text or "")
    if "EXCELENTE" in t:
        return "excelente"
    if "BOM" in t:
        return "bom"
    if "ATENÇÃO" in t or "ATENCAO" in t:
        return "rank-atencao"
    return "critico"

def rank_badge(text):
    k = rank_class_key(text)
    return Markup(f'<span class="badge badge-{k}">{text}</span>')

def id_link(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return Markup(f'<a class="id-link" href="{EVISITA_URL.format(s)}" target="_blank" rel="noopener">{s}</a>')

def parse_custo(v):
    if isinstance(v, (int, float)):
        return float(v) if not pd.isna(v) else None
    s = str(v).replace("R$", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def parse_br_date(s):
    try:
        return datetime.strptime(str(s).strip(), "%d/%m/%Y")
    except (ValueError, TypeError):
        return None

def n(v):
    """Converte numpy/pandas scalar para tipo nativo Python (uso em dados p/ JSON)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return str(v)

# ================================================= renomeia colunas ====
# Nomes de coluna da planilha -> chaves curtas usadas nos templates.

RESUMO_COLS = {
    "Agente": "agente", "Equipe": "equipe", "Classificação": "classificacao",
    "Imóveis Abertos": "abertos", "Dias Trabalhados": "dias_trabalhados", "Visitas/Dia": "visitas_dia",
    "Média (min)": "media_min", "Mediana (min)": "mediana_min", "Rápidas": "rapidas", "% Rápidas": "pct_rapidas",
    "Longas": "longas", "Negativas": "negativas", "Dias c/ Meta": "dias_meta",
    "Visitas Duplicadas": "duplicadas", "Visitas em Sequência Suspeita": "seq_suspeita",
    "Visitas no Almoço (11h15-12h45)": "no_almoco", "Fora do Expediente/Fim de Semana": "fora_expediente",
    "Imóveis Fechados": "fechados", "Imóveis Recusados": "recusados",
    "Total Geral (Abertos+Fechados+Recusados)": "total_geral", "% Pendência": "pct_pendencia",
    "Média Horas Trabalhadas/Dia": "horas_trab_dia", "Média Horas Trabalhadas/Semana": "horas_trab_semana",
    "Média Horas Úteis/Dia": "horas_uteis_dia", "Custo Hora Útil (R$)": "custo_hora",
    "Média Início Manhã": "inicio_manha", "Média Fim Manhã": "fim_manha",
    "Média Início Tarde": "inicio_tarde", "Média Fim Tarde": "fim_tarde",
}
AREA_COLS = {
    "Agente": "agente", "Equipe": "equipe", "Área": "area",
    "Qtd Imóveis Abertos": "abertos", "Tempo Médio (min)": "tempo_medio", "Mediana (min)": "mediana",
    "Qtd Quarteirões": "qtd_quarteiroes", "Quarteirões": "quarteiroes_lista",
    "Rápidas": "rapidas", "% Rápidas": "pct_rapidas",
    "Qtd Fechados": "fechados", "Qtd Recusados": "recusados", "% Pendência": "pct_pendencia", "Alerta": "alerta",
}
ALERT_COLS = {
    "Agente": "agente", "Equipe": "equipe", "ID Visita": "id_visita", "Cadeia": "cadeia",
    "Área": "area", "Quarteirão": "quarteirao", "Logradouro": "logradouro",
    "Imóvel": "imovel", "Data Chegada": "chegada", "Data Saída": "saida", "Motivo": "motivo",
    "Duração (min)": "duracao_min", "Observação": "observacao", "Dia da Semana": "dia_semana",
    "Diferença p/ Anterior (s)*": "diferenca_s",
}
AUSENCIA_COLS = {
    "ID Agente": "id_agente", "Agente": "agente", "Equipe": "equipe", "Dia": "dia", "Dia da Semana": "dia_semana",
    "Turno": "turno", "Observação": "observacao",
}
PENDENCIA_COLS = {
    "Agente": "agente", "Equipe": "equipe", "Imóveis Abertos": "abertos", "Imóveis Fechados": "fechados",
    "Imóveis Recusados": "recusados", "Total Geral": "total_geral", "% Pendência": "pct_pendencia",
}
PE_COLS = {
    "Semana": "semana", "Período": "periodo", "Agente": "agente", "Equipe": "equipe",
    "Classificação": "classificacao", "Imóveis Abertos": "abertos", "Dias Trabalhados": "dias_trabalhados",
    "Visitas/Dia": "visitas_dia", "Média (min)": "media_min", "Rápidas": "rapidas", "% Rápidas": "pct_rapidas",
    "Média Horas Úteis/Dia": "horas_uteis_dia", "Custo Hora Útil (R$)": "custo_hora",
}
# Igual RESUMO_COLS, só que com Semana/Período na frente — usado pelo filtro
# de semana do Resumo Geral (aba "Resumo Semanal" do Excel, ver
# scripts/coleta/saida_excel.py::salvar_excel_consolidado).
RESUMO_SEMANAL_COLS = {"Semana": "semana", "Período": "periodo", **RESUMO_COLS}
RANKING_COLS = {
    "Posição": "posicao", "Agente": "agente", "Equipe": "equipe",
    "Dias Trabalhados": "dias_trabalhados", "Dias Úteis Esperados no Mês": "dias_uteis_esperados",
    "Turnos Sem Trabalhar": "turnos_sem_trabalhar",
    "Pontuação Final": "pontos", "Classificação": "classificacao",
    "Observação": "observacao",
}
RANKING_DET_COLS = {
    "Agente": "agente", "Equipe": "equipe", "Critério": "criterio",
    "Quantidade": "qtd",
    "Peso Nominal (tabela de critérios)": "peso_nominal",
    "Fator de Normalização": "fator_normalizacao",
    "Peso Efetivo (nominal × fator)": "peso",
    "Pontos Aplicados": "pontos",
}

def cap_first(v):
    """Primeira letra maiúscula, sem mexer no resto do texto (não usa
    .title()/.capitalize() pra não estragar nomes com 'de'/'da'/'dos')."""
    if isinstance(v, str) and v:
        return v[0].upper() + v[1:]
    return v

# Colunas que não devem ser tocadas pela padronização de texto: já têm
# formatação própria e case-sensitive (badge/emoji), mexer quebraria a
# detecção de cor em class_key()/rank_class_key().
_NAO_PADRONIZAR_TEXTO = {"classificacao"}

def ranking_sem_nan(rows):
    """Célula vazia da coluna Observação chega como NaN (que o Jinja trataria
    como texto verdadeiro e imprimiria "nan") — vira string vazia."""
    for r in rows:
        v = r.get("observacao")
        if v is None or (isinstance(v, float) and pd.isna(v)):
            r["observacao"] = ""
    return rows

def records(df, colmap):
    renamed = df.rename(columns=colmap)
    cols = [c for c in colmap.values() if c in renamed.columns]
    rows = renamed[cols].to_dict(orient="records")
    for row in rows:
        for k, v in row.items():
            if k not in _NAO_PADRONIZAR_TEXTO:
                row[k] = cap_first(v)
    return rows

# ==================================================== carrega abas ====

def primeira_tabela(path, aba, subset=None):
    """Lê a primeira tabela de uma aba com segurança: se a aba não existir
    (planilha de versão antiga) ou não tiver nenhuma tabela detectável (aba
    sem nenhuma linha — cada vez mais comum agora que a coleta pode ser de
    só 1 semana, com menos chance de ter alerta pra registrar), devolve um
    DataFrame vazio em vez de quebrar o dashboard inteiro."""
    try:
        tabs = get_tables(path, aba)
    except KeyError:
        return pd.DataFrame()
    if not tabs:
        return pd.DataFrame()
    df = tabs[0]
    if subset:
        subset = [c for c in subset if c in df.columns]
        if subset:
            df = df.dropna(subset=subset)
    return df.copy()

def load_all(path):
    resumo = primeira_tabela(path, "Resumo Geral", ["Imóveis Abertos"])
    area = primeira_tabela(path, "Por Área", ["Qtd Imóveis Abertos"])
    dup = primeira_tabela(path, "Visitas Duplicadas", ["ID Visita"])
    susp = primeira_tabela(path, "Visitas Suspeitas", ["ID Visita"])
    neg = primeira_tabela(path, "Visitas Negativas", ["ID Visita"])
    fora = primeira_tabela(path, "Fora do Expediente", ["ID Visita"])
    almoco = primeira_tabela(path, "Visitas no Almoço", ["ID Visita"])
    teto_media = primeira_tabela(path, "Visitas Acima de 20min", ["ID Visita"])
    ausencias = primeira_tabela(path, "Ausências", ["Agente"])
    cronograma = primeira_tabela(path, "Cronograma", ["Motivo"])

    pend_tabs = []
    try:
        pend_tabs = get_tables(path, "Recusados e Pendências")
    except KeyError:
        pass
    pendencias = pend_tabs[0].dropna(subset=["Agente"]).copy() if len(pend_tabs) > 0 else pd.DataFrame()
    recusados_detalhe = pend_tabs[1].dropna(subset=["ID Visita"]).copy() if len(pend_tabs) > 1 else pd.DataFrame()

    try:
        pe_tabs = get_tables(path, "Ponto Estratégico")
    except KeyError:
        # A aba só é criada pelo coletor quando existe pelo menos 1 agente
        # configurado em AGENTES_PONTO_ESTRATEGICO — se a lista estiver vazia,
        # a aba não existe nessa planilha, e não é erro.
        pe_tabs = []
    if pe_tabs:
        pe = pe_tabs[0].copy()
        pe = pe[pe["Agente"].notna() & (pe["Agente"].astype(str).str.strip() != "Selecione")]
    else:
        pe = pd.DataFrame()

    try:
        rs_tabs = get_tables(path, "Resumo Semanal")
    except KeyError:
        # Só existe quando o período consolidado cobre mais de 1 semana
        # (ver salvar_excel_consolidado no coletor) — planilhas de uma
        # semana só (ou geradas por versão anterior do coletor) não têm
        # essa aba, e não é erro.
        rs_tabs = []
    resumo_semanal = rs_tabs[0].dropna(subset=["Agente"]).copy() if rs_tabs else pd.DataFrame()

    if not resumo.empty:
        resumo["CustoNum"] = resumo["Custo Hora Útil (R$)"].apply(parse_custo)
        resumo["_cls"] = resumo["Classificação"].apply(class_key)
    else:
        resumo["CustoNum"] = pd.Series(dtype=float)
        resumo["_cls"] = pd.Series(dtype=object)

    try:
        rk_tabs = get_tables(path, "Ranking")
    except KeyError:
        # Planilha gerada por uma versão do coletor anterior ao Ranking —
        # dashboard continua funcionando normalmente, só sem essa aba.
        rk_tabs = []
    ranking = rk_tabs[0].dropna(subset=["Agente"]).copy() if len(rk_tabs) > 0 else pd.DataFrame()
    ranking_detalhe = rk_tabs[1].dropna(subset=["Agente"]).copy() if len(rk_tabs) > 1 else pd.DataFrame()

    # Separa a Equipe Bloqueio: sai de tudo que é "tratamento" (resumo geral,
    # área, alertas, ausências, pendências, ranking) e fica isolada, guardada
    # à parte pra aparecer só na aba Ponto Estratégico.
    resumo_bloqueio = somente_bloqueio(resumo)
    resumo = adicionar_custo_real(sem_bloqueio(resumo))
    area = sem_bloqueio(area)
    dup, susp, neg, fora, almoco, teto_media = (sem_bloqueio(x) for x in (dup, susp, neg, fora, almoco, teto_media))
    ausencias = sem_bloqueio(ausencias)
    pendencias_bloqueio = somente_bloqueio(pendencias)
    pendencias = sem_bloqueio(pendencias)
    recusados_detalhe = sem_bloqueio(recusados_detalhe)
    ranking = sem_bloqueio(ranking)
    ranking_detalhe = sem_bloqueio(ranking_detalhe)
    resumo_semanal = sem_bloqueio(resumo_semanal)
    if not ranking.empty:
        # Reordena a posição depois de tirar a Equipe Bloqueio, senão fica
        # com buracos (1, 2, 4, 5...) em vez de sequencial.
        ranking = ranking.sort_values("Pontuação Final", ascending=False).reset_index(drop=True)
        ranking["Posição"] = range(1, len(ranking) + 1)
        ranking["_cls"] = ranking["Classificação"].apply(rank_class_key)

    return dict(resumo=resumo, area=area, dup=dup, susp=susp, neg=neg, fora=fora, almoco=almoco,
                teto_media=teto_media,
                ausencias=ausencias, cronograma=cronograma, pendencias=pendencias,
                recusados_detalhe=recusados_detalhe, ponto_estrategico=pe,
                ranking=ranking, ranking_detalhe=ranking_detalhe,
                resumo_bloqueio=resumo_bloqueio, pendencias_bloqueio=pendencias_bloqueio,
                resumo_semanal=resumo_semanal)

# =================================================== agregações ====

def compute_all_absent(ausencias, resumo):
    """Turnos em que TODA UMA EQUIPE ficou sem nenhuma visita registrada
    (reunião, chuva localizada, etc.) — calculado por equipe, não pelo total
    geral, porque outras equipes podem estar trabalhando normalmente em
    outra parte da cidade no mesmo turno."""
    cols = ["Dia", "Dia da Semana", "Turno", "Equipe", "n_ausentes", "tamanho_equipe"]
    if ausencias.empty:
        return pd.DataFrame(columns=cols)
    team_size = resumo.groupby("Equipe")["Agente"].nunique()
    grp = ausencias.groupby(["Dia", "Dia da Semana", "Turno", "Equipe"])["Agente"].nunique().reset_index(name="n_ausentes")
    grp["tamanho_equipe"] = grp["Equipe"].map(team_size)
    return grp[grp["n_ausentes"] >= grp["tamanho_equipe"]].copy()

def build_cronograma_rows(cronograma, all_absent):
    """Junta o cronograma manual (data/cronograma_ausencias.json — chuva,
    folga, atestado, reunião/treinamento, férias) com as paralisações de
    equipe inteira detectadas automaticamente (all_absent), evitando listar
    duas vezes o mesmo turno quando o cronograma já cobre aquela equipe/dia
    (por "equipe" ou por "todos os agentes").

    Tolera planilhas de Cronograma no formato ANTIGO (colunas Agente/Equipe/
    Turno, de antes da unificação) sem quebrar — só não tenta casar essas
    linhas com as paralisações automáticas, exibe como estão."""
    manual, covered = [], set()
    if cronograma is not None and not cronograma.empty:
        tem_quem = "Quem" in cronograma.columns
        for _, r in cronograma.iterrows():
            d_ini, d_fim = parse_br_date(r["Dia Início"]), parse_br_date(r["Dia Fim"])
            periodo = r["Dia Início"] if r["Dia Início"] == r["Dia Fim"] else f"{r['Dia Início']} a {r['Dia Fim']}"
            if tem_quem:
                quem = r["Quem"]
            else:
                # Formato antigo (planilha gerada antes desta versão do coletor)
                quem = r.get("Agente") or r.get("Equipe") or "—"
            manual.append(dict(periodo=periodo, motivo=r["Motivo"], quem=quem, auto=False))
            if d_ini and d_fim and tem_quem:
                cobre_todos = str(quem).strip().lower() == "todos os agentes"
                for _, ar in all_absent.iterrows():
                    ad = parse_br_date(ar["Dia"])
                    if ad and d_ini <= ad <= d_fim and (cobre_todos or ar["Equipe"] == quem):
                        covered.add((ar["Dia"], ar["Turno"], ar["Equipe"]))
    auto = []
    for _, ar in all_absent.sort_values(["Dia", "Equipe"]).iterrows():
        key = (ar["Dia"], ar["Turno"], ar["Equipe"])
        if key in covered:
            continue
        auto.append(dict(periodo=ar["Dia"], motivo="Nenhum agente da equipe registrou visita neste turno",
                          quem=f"Todos da {ar['Equipe']} ({int(ar['n_ausentes'])}/{int(ar['tamanho_equipe'])})",
                          auto=True))
    return manual + auto

_DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def agrupar_cronograma_por_dia(rows):
    """Agrupa as linhas de build_cronograma_rows por DIA (ou por período, quando o lançamento cobre vários dias),
    em ordem cronológica. Cada grupo: titulo, n, motivos (curtos, sem repetir), auto_n, rows. A página mostra cada
    grupo recolhido (<details>) para a tabela não virar uma parede de linhas."""
    grupos, ordem = {}, []
    for r in rows:
        k = r["periodo"]
        if k not in grupos:
            grupos[k] = []
            ordem.append(k)
        grupos[k].append(r)

    def chave(k):
        d = parse_br_date(str(k)[:10])
        d2 = parse_br_date(str(k)[-10:])
        return (0, d, d2) if d else (1, date.max, date.max)

    saida = []
    for k in sorted(ordem, key=chave):
        linhas = grupos[k]
        d = parse_br_date(str(k)[:10])
        if " a " in str(k):
            titulo = str(k)
        elif d:
            titulo = f"{_DIAS_CURTOS[d.weekday()]} {k}"
        else:
            titulo = str(k)
        motivos = []
        for r in linhas:
            m = "Equipe parada (auto)" if r.get("auto") else str(r["motivo"])
            if m not in motivos:
                motivos.append(m)
        saida.append(dict(titulo=titulo, n=len(linhas), motivos=motivos, auto_n=sum(1 for r in linhas if r.get("auto")), rows=linhas))
    return saida


def build_kpi_geral(resumo):
    total_agentes = len(resumo)
    total_abertos = int(resumo["Imóveis Abertos"].sum())
    total_fechados = int(resumo["Imóveis Fechados"].sum())
    total_recusados = int(resumo["Imóveis Recusados"].sum())
    total_geral = int(resumo["Total Geral (Abertos+Fechados+Recusados)"].sum())
    pct_pendencia = (total_fechados + total_recusados) / total_geral * 100 if total_geral else 0
    n_normal = int((resumo["_cls"] == "normal").sum())
    n_atencao = int((resumo["_cls"] == "atencao").sum())
    n_critico = int((resumo["_cls"] == "critico").sum())
    return dict(total_agentes=total_agentes, total_abertos=total_abertos, total_fechados=total_fechados,
                total_recusados=total_recusados, total_geral=total_geral, pct_pendencia=pct_pendencia,
                n_normal=n_normal, n_atencao=n_atencao, n_critico=n_critico)

# ---- leitura rápida das planilhas (custos) --------------------------------

def _ler_tabela_rapida(path, aba, colunas):
    """Primeira tabela de uma aba (modo somente-leitura, bem mais rápido que carregar
    o arquivo inteiro). Devolve [{coluna: valor}] só com as `colunas` pedidas."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if aba not in wb.sheetnames:
            return []
        header, idx, out = None, {}, []
        for vals in wb[aba].iter_rows(values_only=True):
            if header is None:
                if vals and all(c in vals for c in colunas):
                    header = list(vals)
                    idx = {c: header.index(c) for c in colunas}
                continue
            if not vals or vals[idx["Agente"]] is None:
                break  # fim da tabela principal
            out.append({c: vals[i] for c, i in idx.items()})
        return out
    finally:
        wb.close()


def _num(v):
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None


def _ler_presenca(path):
    """{agente: (dias_trabalhados, dias_esperados)} da aba Ranking. Nos períodos
    com o método novo de ranking, 'esperados' = dias úteis do período JÁ DESCONTADOS
    férias, atestado, folga e paralisações coletivas (chuva, reunião, capacitação)
    em que o agente não trabalhou — ver _preparar_ranking no coletor."""
    out = {}
    for r in _ler_tabela_rapida(path, "Ranking", ["Agente", "Dias Trabalhados", "Dias Úteis Esperados no Mês"]):
        d, e = _num(r["Dias Trabalhados"]), _num(r["Dias Úteis Esperados no Mês"])
        if d is not None and e is not None:
            out[str(r["Agente"]).strip()] = (d, e)
    return out


def _meses_historico():
    """[(label, caminho)] dos meses fechados, do mais antigo pro mais recente."""
    manifest_path = ROOT / "data" / "historico" / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        entradas = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    entradas = sorted((e for e in entradas if LABEL_MES_RE.match(str(e.get("label", "")))),
                      key=lambda e: e.get("semana_inicio", 0))
    return [(e["label"], ROOT / "data" / "historico" / e["arquivo"]) for e in entradas
            if (ROOT / "data" / "historico" / e["arquivo"]).exists()]


_PRESENCA_CACHE = {}


def _presenca_da_pagina():
    """Presença da página que está sendo gerada. Página de um mês (ou de uma semana):
    lê o próprio Ranking. Acumulado: o Ranking dele usa a regra antiga (esperados = 1
    mês de referência), então soma os dias trabalhados e esperados de cada mês."""
    chave = str(XLSX_PATH)
    if chave in _PRESENCA_CACHE:
        return _PRESENCA_CACHE[chave]
    if Path(XLSX_PATH).name == "Analise_Consolidada.xlsx":
        total = {}
        for _label, caminho in _meses_historico():
            for ag, (d, e) in _ler_presenca(caminho).items():
                t = total.get(ag, (0.0, 0.0))
                total[ag] = (t[0] + d, t[1] + e)
        pres = total
    else:
        pres = _ler_presenca(XLSX_PATH)
    _PRESENCA_CACHE[chave] = pres
    return pres


# ---- painel Custos & Produtividade -----------------------------------------

def _preparar_custos(d, presenca):
    """Acrescenta ao DataFrame (já com _hu/_ht/_hs/_dias/_vd) a presença e o custo real.

    Dois custos por hora, de propósito:
      * NO RITMO = salário ÷ (horas úteis/dia × 22). Só vale enquanto o agente trabalha:
        quem falta muito não é penalizado por isso.
      * REAL     = salário dos dias que ele DEVIA trabalhar ÷ horas úteis que produziu.
        Os dias esperados já descontam férias, atestado, folga e paralisações coletivas
        (ver _ler_presenca); só falta sem justificativa encarece a hora.
    Sem a aba Ranking (planilha antiga), cai pro dia do agente que mais trabalhou."""
    d = d.copy()
    ref_fallback = float(d["_dias"].max()) if len(d) else 0.0
    dias, esp = [], []
    for ag, dias_res in zip(d["Agente"], d["_dias"]):
        p = presenca.get(str(ag).strip())
        dias.append(p[0] if p else dias_res)
        esp.append(p[1] if p else ref_fallback)
    d["_dias"], d["_esp"] = dias, esp
    # trabalhou mais que o esperado (dia extra): o custo não cai abaixo do "no ritmo"
    d["_esp"] = d[["_esp", "_dias"]].max(axis=1)
    # sem nenhum dia esperado (afastado o período todo) ou sem dia trabalhado: não há custo a medir
    d = d[(d["_esp"] > 0) & (d["_dias"] > 0)].copy()
    d["_pres"] = (d["_dias"] / d["_esp"]).clip(upper=1.0)
    d["_folha"] = SALARIO_MENSAL * d["_esp"] / DIAS_UTEIS_MES_REF
    d["_custo_real"] = d["CustoNum"] / d["_pres"]
    return d


def _custos_base(resumo):
    d = resumo.copy()
    for col, novo in [("Média Horas Úteis/Dia", "_hu"), ("Média Horas Trabalhadas/Dia", "_ht"),
                      ("Média Horas Trabalhadas/Semana", "_hs"), ("Dias Trabalhados", "_dias"),
                      ("Visitas/Dia", "_vd")]:
        d[novo] = pd.to_numeric(d[col], errors="coerce") if col in d.columns else float("nan")
    d = d[d["CustoNum"].notna() & (d["_hu"] > 0) & (d["_dias"] > 0)].copy()
    if d.empty:
        return d, 0
    d = _preparar_custos(d, _presenca_da_pagina())
    if d.empty:
        return d, 0
    return d, int(round(d["_esp"].max()))


def adicionar_custo_real(resumo):
    """Põe a coluna CustoReal no resumo (usada pelo gráfico de custos)."""
    resumo = resumo.copy()
    resumo["CustoReal"] = float("nan")
    if resumo.empty or "CustoNum" not in resumo.columns:
        return resumo
    d, _ = _custos_base(resumo)
    resumo.loc[d.index, "CustoReal"] = d["_custo_real"]
    return resumo


def _custo_ritmo_agregado(d):
    """Folha ÷ horas úteis do mês de todos juntos (só dias trabalhados). A média
    simples dos custos individuais dá número maior: quem tem poucas horas úteis
    pesa o mesmo que quem tem muitas."""
    horas_mes = (d["_hu"] * DIAS_UTEIS_MES_REF).sum()
    return SALARIO_MENSAL * len(d) / horas_mes if horas_mes > 0 else None


def _custo_real_agregado(d):
    horas = (d["_hu"] * d["_dias"]).sum()
    return d["_folha"].sum() / horas if horas > 0 else None


def _custo_visita_agregado(d):
    visitas = (d["_vd"] * d["_dias"]).sum()
    return d["_folha"].sum() / visitas if visitas > 0 else None


def build_kpi_custos(resumo):
    vazio = dict(custo_real=None, custo_ritmo=None, custo_min=0, custo_min_agente="—", custo_max=0, custo_max_agente="—",
                 custo_visita=None, horas_dia_media=0, horas_semana_media=0, horas_uteis_media=0,
                 aproveitamento=None, presenca=None, n_agentes=0, dias_ref=0, custo_media_simples=None)
    if resumo.empty or "CustoNum" not in resumo.columns:
        return vazio
    d, ref = _custos_base(resumo)
    if d.empty:
        return vazio
    idx_min, idx_max = d["_custo_real"].idxmin(), d["_custo_real"].idxmax()
    return dict(
        custo_real=_custo_real_agregado(d),
        custo_ritmo=_custo_ritmo_agregado(d),
        custo_media_simples=d["CustoNum"].mean(),
        custo_min=d.loc[idx_min, "_custo_real"], custo_min_agente=d.loc[idx_min, "Agente"],
        custo_max=d.loc[idx_max, "_custo_real"], custo_max_agente=d.loc[idx_max, "Agente"],
        custo_visita=_custo_visita_agregado(d),
        horas_dia_media=d["_ht"].mean(),
        horas_semana_media=d["_hs"].mean(),
        horas_uteis_media=d["_hu"].mean(),
        aproveitamento=(d["_hu"].sum() / d["_ht"].sum() * 100) if d["_ht"].sum() > 0 else None,
        presenca=d["_pres"].mean() * 100,
        n_agentes=len(d), dias_ref=ref,
    )


def _faixa_custo(v):
    if v is None or pd.isna(v):
        return ""
    return "alto" if v > CUSTO_FAIXA_ALTO else "medio" if v > CUSTO_FAIXA_MEDIO else "ok"


def _faixa_presenca(pct):
    return "alto" if pct < 50 else "medio" if pct < 80 else "ok"


def build_custos_rows(resumo):
    """Linhas da tabela de custos: as colunas da planilha + presença, aproveitamento,
    custo real, custo por visita e faixas de cor. Ordenada do custo real mais alto pro mais baixo."""
    if resumo.empty or "CustoNum" not in resumo.columns:
        return []
    d, _ = _custos_base(resumo)
    ordenado = resumo.copy()
    ordenado["_ord"] = d["_custo_real"].reindex(ordenado.index)
    ordenado = ordenado.sort_values("_ord", ascending=False, na_position="last")
    linhas = records(ordenado, RESUMO_COLS)
    for (idx, _), row in zip(ordenado.iterrows(), linhas):
        r = d.loc[idx] if idx in d.index else None
        row["custo_ritmo_num"] = n(ordenado.loc[idx, "CustoNum"])
        if r is None:
            row.update(presenca=None, aproveitamento=None, custo_real=None, custo_visita=None,
                       faixa_ritmo="", faixa_real="", faixa_presenca="", dias_esperados=None)
            continue
        pres = r["_pres"] * 100
        row["presenca"] = pres
        row["dias_esperados"] = r["_esp"]
        row["dias_trabalhados"] = r["_dias"]
        row["faixa_presenca"] = _faixa_presenca(pres)
        row["aproveitamento"] = (r["_hu"] / r["_ht"] * 100) if r["_ht"] > 0 else None
        row["custo_real"] = r["_custo_real"]
        row["faixa_ritmo"] = _faixa_custo(row["custo_ritmo_num"])
        row["faixa_real"] = _faixa_custo(r["_custo_real"])
        visitas = r["_vd"] * r["_dias"]
        row["custo_visita"] = r["_folha"] / visitas if visitas > 0 else None
    return linhas


def build_custos_equipes(resumo):
    """Uma linha por equipe, com o mesmo cálculo dos números gerais."""
    if resumo.empty or "CustoNum" not in resumo.columns:
        return []
    d, _ = _custos_base(resumo)
    linhas = []
    for equipe, g in d.groupby("Equipe"):
        real = _custo_real_agregado(g)
        pres = g["_pres"].mean() * 100
        linhas.append(dict(
            equipe=equipe, n=len(g), presenca=pres, faixa_presenca=_faixa_presenca(pres),
            horas_trab_dia=g["_ht"].mean(), horas_uteis_dia=g["_hu"].mean(),
            aproveitamento=(g["_hu"].sum() / g["_ht"].sum() * 100) if g["_ht"].sum() > 0 else None,
            custo_ritmo=_custo_ritmo_agregado(g), custo_real=real, faixa=_faixa_custo(real),
            custo_visita=_custo_visita_agregado(g), folha=SALARIO_MENSAL * len(g),
        ))
    return sorted(linhas, key=lambda x: x["equipe"])


def build_custos_mensais():
    """Custo real da hora útil de cada agente MÊS A MÊS + média dos meses.
    Mesma conta do painel (férias/atestado descontados antes), aplicada a cada mês fechado."""
    meses, por_agente = [], {}
    for label, caminho in _meses_historico():
        try:
            linhas = _ler_tabela_rapida(caminho, "Resumo Geral",
                                        ["Agente", "Equipe", "Dias Trabalhados", "Visitas/Dia",
                                         "Média Horas Úteis/Dia", "Média Horas Trabalhadas/Dia", "Custo Hora Útil (R$)"])
        except Exception:
            continue
        linhas = [l for l in linhas if l["Equipe"] != EQUIPE_BLOQUEIO and str(l["Equipe"] or "").startswith("Equipe")]
        if not linhas:
            continue
        df = pd.DataFrame(linhas)
        df["CustoNum"] = df["Custo Hora Útil (R$)"].apply(parse_custo)
        for col, novo in [("Média Horas Úteis/Dia", "_hu"), ("Média Horas Trabalhadas/Dia", "_ht"),
                          ("Dias Trabalhados", "_dias"), ("Visitas/Dia", "_vd")]:
            df[novo] = pd.to_numeric(df[col], errors="coerce")
        df = df[df["CustoNum"].notna() & (df["_hu"] > 0) & (df["_dias"] > 0)]
        if df.empty:
            continue
        df = _preparar_custos(df, _ler_presenca(caminho))
        if df.empty:
            continue
        idx = len(meses)
        meses.append(label)
        for _, r in df.iterrows():
            a = por_agente.setdefault(r["Agente"], {"agente": r["Agente"], "equipe": r["Equipe"], "valores": {}})
            a["equipe"] = r["Equipe"]
            a["valores"][idx] = dict(v=r["_custo_real"], faixa=_faixa_custo(r["_custo_real"]),
                                     pres=r["_pres"] * 100, ritmo=r["CustoNum"])
    agentes = []
    for a in por_agente.values():
        valores = [a["valores"].get(i) for i in range(len(meses))]
        vs = [v["v"] for v in valores if v]
        media = sum(vs) / len(vs)
        agentes.append(dict(agente=a["agente"], equipe=a["equipe"], meses=valores, media=media,
                            faixa=_faixa_custo(media), n_meses=len(vs),
                            media_ritmo=sum(v["ritmo"] for v in valores if v) / len(vs),
                            presenca=sum(v["pres"] for v in valores if v) / len(vs)))
    agentes.sort(key=lambda x: x["media"], reverse=True)
    return {"meses": meses, "agentes": agentes}


def build_ausencias_agg(aus):
    heat = {d: {"Manhã": 0, "Tarde": 0} for d in DIA_ORDER}
    if aus is None or aus.empty or "Agente" not in aus.columns:
        # Aba "Ausências" vazia (0 registros) — cada vez mais comum agora que
        # o cronograma cobre mais dias e a coleta pode ser de 1 semana só.
        # Não é erro, é uma boa notícia (ninguém com ausência a investigar).
        return dict(heat=heat, top15=[], dia_critico="—", dia_critico_n=0,
                    turno_critico="—", turno_critico_n=0)
    for _, r in aus.iterrows():
        if r["Dia da Semana"] in heat and r["Turno"] in heat[r["Dia da Semana"]]:
            heat[r["Dia da Semana"]][r["Turno"]] += 1
    # Agrupa por ID quando disponível — NUNCA por nome sozinho, porque
    # agentes diferentes podem ter o mesmo nome (juntaria as ausências de
    # gente diferente na mesma linha do Top 15). Planilhas antigas (geradas
    # antes da coluna "ID Agente" existir) caem no fallback por nome.
    if "ID Agente" in aus.columns:
        grp = aus.groupby("ID Agente")
        top15_raw = grp.size().sort_values(ascending=False).head(15)
        nome_por_id = aus.drop_duplicates("ID Agente").set_index("ID Agente")["Agente"]
        top15 = [[nome_por_id.get(idx, str(idx)), int(v)] for idx, v in top15_raw.items()]
    else:
        top15_raw = aus.groupby("Agente").size().sort_values(ascending=False).head(15)
        top15 = [[k, int(v)] for k, v in top15_raw.items()]
    by_dia, by_turno = aus["Dia da Semana"].value_counts(), aus["Turno"].value_counts()
    return dict(
        heat=heat, top15=top15,
        dia_critico=by_dia.idxmax() if len(by_dia) else "—", dia_critico_n=int(by_dia.max() if len(by_dia) else 0),
        turno_critico=by_turno.idxmax() if len(by_turno) else "—", turno_critico_n=int(by_turno.max() if len(by_turno) else 0),
    )

TEAM_COLORS = ["#1080D6", "#6B62D6", "#29AEE0", "#F2994A", "#8D6E63"]

def build_team_cards(resumo, teams):
    cards = []
    for i, team in enumerate(teams):
        sub = resumo[resumo["Equipe"] == team]
        total = len(sub)
        n_crit = int((sub["_cls"] == "critico").sum())
        n_atencao = int((sub["_cls"] == "atencao").sum())
        n_normal = int((sub["_cls"] == "normal").sum())
        cards.append(dict(
            nome=team, color=TEAM_COLORS[i % len(TEAM_COLORS)], agentes=total,
            total_geral=int(sub["Total Geral (Abertos+Fechados+Recusados)"].sum()),
            n_critico=n_crit, n_atencao=n_atencao, n_normal=n_normal,
            pct_critico=n_crit / total * 100 if total else 0,
            pct_atencao=n_atencao / total * 100 if total else 0,
            pct_normal=n_normal / total * 100 if total else 0,
        ))
    return cards

# --- Média mensal por agente -------------------------------------------------
# Tabela "agente × mês" com a pontuação final de cada agente em cada mês e a
# MÉDIA dessas pontuações. Não recalcula nada: lê a aba Ranking já pronta de
# cada mês listado em data/historico/manifest.json (então meses antigos nunca
# mudam). Só entram meses nomeados "Mês/Ano" (Maio/2026...), nunca semanas.
# Faixas da média (as mesmas da legenda do Ranking): ≥90 / ≥75 / ≥60 / abaixo.
LABEL_MES_RE = re.compile(r"^[^\W\d_]+/\d{4}$")

def _classe_por_pontos(p):
    if p >= 90:
        return "excelente"
    if p >= 75:
        return "bom"
    if p >= 60:
        return "rank-atencao"
    return "critico"

def _ler_ranking_rapido(path):
    """Lê só a tabela principal da aba Ranking de uma planilha (modo
    somente-leitura, bem mais rápido que carregar o arquivo inteiro).
    Devolve [(agente, equipe, pontos, classificacao)]."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if "Ranking" not in wb.sheetnames:
            return []
        header, out = None, []
        for vals in wb["Ranking"].iter_rows(values_only=True):
            if header is None:
                if vals and "Agente" in vals and "Pontuação Final" in vals:
                    header = list(vals)
                    i_ag, i_eq = header.index("Agente"), header.index("Equipe")
                    i_pt, i_cl = header.index("Pontuação Final"), header.index("Classificação")
                continue
            if not vals or vals[i_ag] is None:
                break  # fim da tabela principal
            try:
                out.append((str(vals[i_ag]).strip(), vals[i_eq], float(vals[i_pt]), vals[i_cl]))
            except (TypeError, ValueError):
                continue
        return out
    finally:
        wb.close()

def _sparkline(valores, w=92, h=24):
    """Mini-gráfico (SVG inline) da pontuação mês a mês, escala fixa 0–100 pra
    os gráficos de agentes diferentes serem comparáveis. Meses sem registro
    ficam de fora da linha. Precisa de pelo menos 2 meses."""
    pts = [(i, v["pontos"]) for i, v in enumerate(valores) if v]
    if len(pts) < 2:
        return Markup("")
    n = max(len(valores) - 1, 1)
    xy = [(2 + (w - 4) * i / n, 2 + (h - 4) * (1 - max(0.0, min(100.0, p)) / 100)) for i, p in pts]
    linha = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    ux, uy = xy[-1]
    return Markup(f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true">'
                  f'<polyline points="{linha}" fill="none" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
                  f'<circle cx="{ux:.1f}" cy="{uy:.1f}" r="2.3"/></svg>')

def build_media_mensal():
    manifest_path = ROOT / "data" / "historico" / "manifest.json"
    if not manifest_path.exists():
        return {"meses": [], "agentes": []}
    try:
        entradas = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"meses": [], "agentes": []}
    entradas = sorted((e for e in entradas if LABEL_MES_RE.match(str(e.get("label", "")))),
                      key=lambda e: e.get("semana_inicio", 0))
    meses, por_agente = [], {}
    for e in entradas:
        caminho = ROOT / "data" / "historico" / e["arquivo"]
        if not caminho.exists():
            continue
        linhas = [l for l in _ler_ranking_rapido(caminho) if l[1] != EQUIPE_BLOQUEIO]
        if not linhas:
            continue
        idx = len(meses)
        meses.append(e["label"])
        for agente, equipe, pontos, classif in linhas:
            a = por_agente.setdefault(agente, {"agente": agente, "equipe": equipe, "valores": {}})
            a["equipe"] = equipe  # fica a equipe do mês mais recente
            a["valores"][idx] = {"pontos": pontos, "cls": rank_class_key(classif)}
    agentes = []
    for a in por_agente.values():
        valores = [a["valores"].get(i) for i in range(len(meses))]
        pts = [v["pontos"] for v in valores if v]
        media = sum(pts) / len(pts)
        # Tendência = último mês disponível menos o mês anterior disponível.
        delta = round(pts[-1] - pts[-2], 1) if len(pts) >= 2 else None
        agentes.append({"agente": a["agente"], "equipe": a["equipe"], "meses": valores,
                        "media": round(media, 1), "n_meses": len(pts), "cls": _classe_por_pontos(media),
                        "delta": delta,
                        "delta_txt": ("—" if delta is None else (f"+{br(delta, 1)}" if delta > 0 else br(delta, 1))),
                        "delta_cls": ("" if delta is None else ("up" if delta > 0.05 else ("down" if delta < -0.05 else "flat"))),
                        "spark": _sparkline(valores)})
    agentes.sort(key=lambda x: x["media"], reverse=True)
    for i, a in enumerate(agentes, 1):
        a["posicao"] = i
    return {"meses": meses, "agentes": agentes}


def _worker_url():
    try:
        return str(json.loads((ROOT / "data" / "config_worker.json").read_text(encoding="utf-8")).get("url") or "").strip()
    except (OSError, json.JSONDecodeError):
        return ""

def _mes_contestavel(ctx):
    """Mês ("Outubro/2026") ao qual a página se refere, se estiver ABERTO (contestação só vale
    para mês aberto); senão None (Acumulado, meses fechados)."""
    if ctx.get("acumulado_so_media") or XLSX_PATH.resolve() == ACUMULADO_XLSX.resolve():
        return None
    mes = None
    if ctx.get("pagina_semana"):
        mes = ctx["pagina_semana"]["mes"]
    elif ctx.get("nav_semanas"):
        mes = ctx["nav_semanas"]["mes"]
    else:
        try:
            man = json.loads((ROOT / "data" / "historico" / "manifest.json").read_text(encoding="utf-8"))
            e = next((e for e in man if e.get("arquivo") == XLSX_PATH.name and e.get("tipo") != "semana"), None)
            mes = e["label"] if e else None
        except (OSError, json.JSONDecodeError):
            mes = None
    if not mes:
        return None
    try:
        import sys as _s
        _s.path.insert(0, str(SCRIPTS_DIR))
        import meses_arquivados as _ma
        if any(n == mes for _, _, n in _ma.carregar(str(ROOT / "data" / "meses_arquivados.json"))):
            return None
    except Exception:
        pass
    return mes

def _ids_por_nome():
    try:
        nomes = json.loads((ROOT / "data" / "agentes_nomes.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(v.get("nome", "")).strip().lower(): int(k) for k, v in nomes.items() if str(k).isdigit()}

def build_extratos(ranking_rows, detalhe_rows, sem_normalizacao, periodo_label):
    """Dados do "Extrato por agente" (folha de uma página com a conta da
    pontuação, pra imprimir/salvar em PDF e entregar ao agente). Tudo vem do
    ranking e do detalhamento já calculados — nenhuma conta nova aqui."""
    por_agente = {}
    for d in detalhe_rows:
        por_agente.setdefault(d.get("agente"), []).append({
            "criterio": d.get("criterio"), "qtd": d.get("qtd"),
            "peso_nominal": d.get("peso_nominal"), "fator": d.get("fator_normalizacao"),
            "peso": d.get("peso"), "pontos": d.get("pontos"),
        })
    extratos = {}
    ids = _ids_por_nome()
    for r in ranking_rows:
        extratos[r["agente"]] = {
            "id_agente": ids.get(str(r["agente"]).strip().lower()),
            "agente": r["agente"], "equipe": r.get("equipe"), "posicao": r.get("posicao"),
            "dias_trabalhados": r.get("dias_trabalhados"), "dias_esperados": r.get("dias_uteis_esperados"),
            "turnos_sem": r.get("turnos_sem_trabalhar"), "pontos": r.get("pontos"),
            "classificacao": r.get("classificacao"), "observacao": r.get("observacao") or "",
            "detalhes": por_agente.get(r["agente"], []),
        }
    return {"periodo": periodo_label, "sem_normalizacao": bool(sem_normalizacao),
            "pontos_iniciais": 100, "total_agentes": len(ranking_rows), "agentes": extratos}

def _periodo_label(periodos):
    for p in periodos:
        if p.get("atual"):
            t = p["label"]
            m = re.search(r"\((.+)\)", t)
            if m:
                return m.group(1)
            return re.sub(r"^[^\w]+\s*", "", t)
    return ""

def build_kpi_ranking(ranking):
    if ranking.empty:
        return dict(media=0, lider_nome="—", lider_pontos=0, n_excelente=0, n_bom=0, n_atencao=0, n_critico=0)
    lider = ranking.sort_values("Posição").iloc[0]
    return dict(
        media=ranking["Pontuação Final"].mean(),
        lider_nome=lider["Agente"], lider_pontos=lider["Pontuação Final"],
        n_excelente=int((ranking["_cls"] == "excelente").sum()),
        n_bom=int((ranking["_cls"] == "bom").sum()),
        n_atencao=int((ranking["_cls"] == "rank-atencao").sum()),
        n_critico=int((ranking["_cls"] == "critico").sum()),
    )

def build_chart_data(data):
    resumo = data["resumo"]
    teams = sorted(resumo["Equipe"].unique())

    def by_team(col, agg="sum"):
        g = resumo.groupby("Equipe")[col]
        return [n(v) for v in (g.sum() if agg == "sum" else g.mean()).reindex(teams)]

    team_stack = {k: [int(((resumo.Equipe == t) & (resumo._cls == k)).sum()) for t in teams]
                  for k in ("normal", "atencao", "critico")}

    def agent_series(col, sort_col=None, ascending=True, extra=None):
        d = resumo.sort_values(sort_col or col, ascending=ascending)
        out = []
        for _, r in d.iterrows():
            item = {"label": r["Agente"], "v": n(r[col]), "cls": r["Classificação"]}
            if extra:
                item.update({k: n(r[c]) for k, c in extra.items()})
            out.append(item)
        return out

    pend = data["pendencias"]
    pend_top15 = ([{"label": r["Agente"], "pct": n(r["% Pendência"])}
                   for _, r in pend.sort_values("% Pendência", ascending=False).head(15).iterrows()]
                  if not pend.empty else [])

    pe = data["ponto_estrategico"]
    pe_trend = ([{"semana": str(r["Semana"]), "visitas_dia": n(r["Visitas/Dia"]), "abertos": n(r["Imóveis Abertos"])}
                 for _, r in pe.sort_values("Semana").iterrows()] if not pe.empty else [])

    rk = data["ranking"]
    rank_colors = {"excelente": "#12B76A", "bom": "#F2D93B", "rank-atencao": "#F2994A", "critico": "#E4572E"}
    ranking_chart = ([{"label": r["Agente"], "v": n(r["Pontuação Final"]), "color": rank_colors[r["_cls"]]}
                      for _, r in rk.sort_values("Pontuação Final", ascending=False).iterrows()]
                     if not rk.empty else [])

    return dict(
        teams=teams,
        class_counts=[int((resumo["_cls"] == k).sum()) for k in ("normal", "atencao", "critico")],
        team_abertos=by_team("Imóveis Abertos"), team_rapidas=by_team("Rápidas"),
        team_stack=team_stack,
        team_status={"abertos": by_team("Imóveis Abertos"), "fechados": by_team("Imóveis Fechados"),
                     "recusados": by_team("Imóveis Recusados")},
        agents_pct=agent_series("% Rápidas", ascending=False),
        custo_data=agent_series("CustoReal", ascending=False),
        horas_data=agent_series("Média Horas Úteis/Dia", ascending=True),
        horas_trab_dia_data=agent_series("Média Horas Trabalhadas/Dia", ascending=True),
        horas_trab_semana_data=agent_series("Média Horas Trabalhadas/Semana", ascending=True),
        pend_top15=pend_top15, pe_trend=pe_trend, ranking_chart=ranking_chart,
    )

# ========================================================= main ====

def build_context(data):
    resumo, area, aus = data["resumo"], data["area"], data["ausencias"]
    pe, pendencias = data["ponto_estrategico"], data["pendencias"]

    all_absent = compute_all_absent(aus, resumo)
    all_absent_keys = set(zip(all_absent["Dia"], all_absent["Turno"], all_absent["Equipe"]))

    aus_records = records(aus, AUSENCIA_COLS)
    for rec, (_, r) in zip(aus_records, aus.iterrows()):
        rec["allabsent"] = (r["Dia"], r["Turno"], r["Equipe"]) in all_absent_keys

    kpi = build_kpi_geral(resumo)
    alertas_totais = len(data["dup"]) + len(data["susp"]) + len(data["neg"]) + len(data["fora"]) + len(data["almoco"])
    crit_sorted = resumo[resumo["_cls"] == "critico"].sort_values("% Rápidas", ascending=False)

    resumo_semanal_df = data.get("resumo_semanal")
    if resumo_semanal_df is not None and not resumo_semanal_df.empty:
        resumo_semanal_recs = records(resumo_semanal_df.sort_values(["Semana", "Agente"]), RESUMO_SEMANAL_COLS)
        # Rótulo vem da data OFICIAL da semana do e-Visita (não do min/max de
        # chegada de cada agente, que varia agente a agente e duplicaria a
        # mesma semana com rótulos levemente diferentes).
        semanas_disponiveis = []
        for s in sorted(resumo_semanal_df["Semana"].unique()):
            try:
                html_id = sem_evisita.semana_para_html(int(s))
                label = sem_evisita.rotulo_semana_html(html_id)
            except Exception:
                label = f"Semana {int(s)}"
            semanas_disponiveis.append({"semana": int(s), "label": label})
    else:
        resumo_semanal_recs, semanas_disponiveis = [], []

    _cronograma_rows_calc = build_cronograma_rows(data["cronograma"], all_absent)

    return dict(
        title="S E N T I N E L A - HUB",
        now_str=datetime.now(timezone(timedelta(hours=-4))).strftime("%d/%m/%Y %H:%M"),
        salario_mensal=SALARIO_MENSAL,
        teams=sorted(resumo["Equipe"].unique()),
        team_cards=build_team_cards(resumo, sorted(resumo["Equipe"].unique())),
        kpi=kpi, kc=build_kpi_custos(resumo),
        alertas_totais=alertas_totais,
        n_ausencias=len(aus),
        n_allabsent_rows=sum(1 for rec in aus_records if rec["allabsent"]),
        crit_count=len(crit_sorted), criticos=records(crit_sorted.head(5), RESUMO_COLS),
        resumo=records(resumo, RESUMO_COLS),
        resumo_semanal=resumo_semanal_recs,
        semanas_disponiveis=semanas_disponiveis,
        outras_atividades=carregar_outras_atividades(),
        area=records(area.sort_values("% Rápidas", ascending=False), AREA_COLS),
        areas_unicas=sorted(area["Área"].unique()),
        dup=records(data["dup"], ALERT_COLS), susp=records(data["susp"], ALERT_COLS),
        neg=records(data["neg"], ALERT_COLS), fora=records(data["fora"], ALERT_COLS),
        almoco=records(data["almoco"], ALERT_COLS),
        teto_media=records(data["teto_media"], ALERT_COLS),
        recusados_detalhe=records(data["recusados_detalhe"], ALERT_COLS),
        n_recusados=len(data["recusados_detalhe"]),
        ausencias=aus_records,
        ausencias_agg=build_ausencias_agg(aus),
        cronograma_rows=_cronograma_rows_calc,
        cronograma_dias=agrupar_cronograma_por_dia(_cronograma_rows_calc),
        ferias_atestado_rows=[r for r in _cronograma_rows_calc
                               if not r["auto"] and ("férias" in r["motivo"].lower() or "atestado" in r["motivo"].lower())],
        pendencias=records(pendencias.sort_values("% Pendência", ascending=False), PENDENCIA_COLS) if not pendencias.empty else [],
        ponto_estrategico=records(pe.sort_values("Semana"), PE_COLS) if not pe.empty else [],
        pe_agente=pe["Agente"].iloc[0] if not pe.empty else "—",
        pe_semanas=pe["Semana"].nunique() if not pe.empty else 0,
        custos=build_custos_rows(resumo),
        custos_equipes=build_custos_equipes(resumo),
        custos_mensais=build_custos_mensais(),
        dias_uteis_mes=DIAS_UTEIS_MES_REF, meta_visitas_dia=META_VISITAS_DIA_REF,
        custo_faixa_medio=CUSTO_FAIXA_MEDIO, custo_faixa_alto=CUSTO_FAIXA_ALTO, custo_grafico_max=CUSTO_GRAFICO_MAX,
        horas_uteis_baixo=HORAS_UTEIS_BAIXO, horas_uteis_alto=HORAS_UTEIS_ALTO,
        teto_visita_min=TETO_VISITA_MIN,
        ranking=ranking_sem_nan(records(data["ranking"].sort_values("Posição"), RANKING_COLS)) if not data["ranking"].empty else [],
        ranking_tem_observacao=bool(not data["ranking"].empty and "Observação" in data["ranking"].columns),
        ranking_detalhe=records(data["ranking_detalhe"], RANKING_DET_COLS) if not data["ranking_detalhe"].empty else [],
        kpi_ranking=build_kpi_ranking(data["ranking"]),
        media_mensal=build_media_mensal(),
        # Período sem fator de normalização (ranking de Outubro/2026 em diante):
        # todo critério do detalhamento tem fator 1,0. Períodos antigos (e o
        # Acumulado) têm fatores diferentes de 1 e seguem exibindo o fator.
        ranking_sem_normalizacao=bool(
            not data["ranking_detalhe"].empty
            and "Fator de Normalização" in data["ranking_detalhe"].columns
            and ((pd.to_numeric(data["ranking_detalhe"]["Fator de Normalização"], errors="coerce")
                  .fillna(1.0) - 1.0).abs() < 1e-9).all()),
        resumo_bloqueio=records(data["resumo_bloqueio"], RESUMO_COLS) if not data["resumo_bloqueio"].empty else [],
        pendencias_bloqueio=records(data["pendencias_bloqueio"], PENDENCIA_COLS) if not data["pendencias_bloqueio"].empty else [],
        chart_data=build_chart_data(data),
        css=(SCRIPTS_DIR / "style.css").read_text(encoding="utf-8"),
        bootstrap_js=(SCRIPTS_DIR / "bootstrap.js").read_text(encoding="utf-8"),
    )

def build_comparacao_semanal(nav, pagina_semana):
    """Nota média de cada equipe, semana a semana, dentro do mês (só na página do MÊS, com 2+
    semanas). Inclui coluna final «Mês completo» com a média do ranking do mês (mesma fórmula:
    soma das notas ÷ qtd agentes). Semana em andamento fica marcada como parcial.
    None quando não se aplica."""
    if not nav or pagina_semana:
        return None
    try:
        man = json.loads((ROOT / "data" / "historico" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    semanas = sorted((e for e in man if e.get("tipo") == "semana" and e.get("mes") == nav["mes"]),
                     key=lambda e: e.get("numero_semana", 0))
    colunas, equipes = [], {}
    for e in semanas:
        cam = ROOT / "data" / "historico" / e["arquivo"]
        if not cam.exists():
            continue
        linhas = [l for l in _ler_ranking_rapido(cam) if l[1] and l[1] != EQUIPE_BLOQUEIO]
        if not linhas:
            continue
        idx = len(colunas)
        colunas.append({"label": f"Semana {e['numero_semana']}", "periodo": e.get("periodo", ""), "parcial": bool(e.get("parcial"))})
        acc = {}
        for _, eq, pts, _c in linhas:
            acc.setdefault(eq, []).append(pts)
        for eq, v in acc.items():
            equipes.setdefault(eq, {})[idx] = round(sum(v) / len(v), 1)
    if len(colunas) < 2:
        return None

    # Coluna «Mês completo»: ranking do mês (entrada do manifest com label == mes e tipo != semana)
    media_mes = {}
    e_mes = next((e for e in man if e.get("tipo") != "semana" and e.get("label") == nav["mes"]), None)
    if e_mes:
        cam_mes = ROOT / "data" / "historico" / e_mes["arquivo"]
        if cam_mes.exists():
            linhas_mes = [l for l in _ler_ranking_rapido(cam_mes) if l[1] and l[1] != EQUIPE_BLOQUEIO]
            acc_mes = {}
            for _, eq, pts, _c in linhas_mes:
                acc_mes.setdefault(eq, []).append(pts)
            media_mes = {eq: round(sum(v) / len(v), 1) for eq, v in acc_mes.items()}
            if media_mes:
                idx_mes = len(colunas)
                mes_parcial = any(c.get("parcial") for c in colunas)
                colunas.append({"label": "Mês (até agora)" if mes_parcial else "Mês completo",
                                "periodo": nav["mes"], "parcial": mes_parcial})
                for eq, media in media_mes.items():
                    equipes.setdefault(eq, {})[idx_mes] = media

    return {
        "mes": nav["mes"],
        "semanas": colunas,
        "equipes": {eq: [vals.get(i) for i in range(len(colunas))] for eq, vals in sorted(equipes.items())},
        "media_mes": media_mes,
    }


def carregar_periodos():
    """Monta a lista de opções do seletor de período no cabeçalho:
      1. 🏠 Início — index.html na raiz, o período configurado em
         data/config_home.json (editável pelo home_editor.html).
      2. 📊 Acumulado (todas as semanas) — acumulado.html, sempre a soma de
         TUDO já coletado, sem depender de configuração nenhuma.
      3. Cada mês arquivado em data/historico/ (manifest.json), mais recente
         primeiro.
    Calcula o link relativo à página que está sendo gerada agora, pra
    funcionar tanto a partir da raiz quanto de dentro de historico/."""
    index_path = ROOT / "index.html"
    acumulado_path = ROOT / "acumulado.html"
    home_label = "🏠 Início"
    if HOME_XLSX == ACUMULADO_XLSX and CONFIG_HOME_PATH.exists():
        # config_home.json aponta pra um período que ainda não foi gerado (ex.:
        # mês novo antes da primeira coleta) — a home caiu no acumulado, então
        # o rótulo não pode prometer o mês configurado.
        home_label = "🏠 Início (Acumulado)"
    elif CONFIG_HOME_PATH.exists():
        try:
            home_label = "🏠 Início (" + json.loads(CONFIG_HOME_PATH.read_text(encoding="utf-8"))["label"] + ")"
        except (json.JSONDecodeError, KeyError):
            pass
    itens = [
        {
            "label": home_label,
            "href": os.path.relpath(index_path, OUT_PATH.parent).replace(os.sep, "/"),
            "atual": OUT_PATH.resolve() == index_path.resolve(),
        },
        {
            "label": "📊 Acumulado (todas as semanas)",
            "href": os.path.relpath(acumulado_path, OUT_PATH.parent).replace(os.sep, "/"),
            "atual": OUT_PATH.resolve() == acumulado_path.resolve(),
        },
    ]
    manifest_path = ROOT / "data" / "historico" / "manifest.json"
    if manifest_path.exists():
        try:
            entries = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            entries = []
        for e in reversed(entries):  # mais recente primeiro
            if e.get("tipo") == "semana":
                continue  # visões semanais ficam na barra "Semana 1 | 2 | … | Mês completo", não no seletor
            alvo = ROOT / "historico" / e["arquivo"].replace(".xlsx", ".html")
            href = os.path.relpath(alvo, OUT_PATH.parent).replace(os.sep, "/")
            itens.append({"label": "📅 " + e["label"], "href": href,
                          "atual": alvo.resolve() == OUT_PATH.resolve()})
    return itens

def carregar_nav_semanas():
    """Barra "Semana 1 | Semana 2 | ... | Mês completo" do mês vigente.
    Devolve None quando a página atual não é um mês com visões semanais nem
    uma dessas semanas. Retorna (nav, pagina_semana):
      nav = {"mes", "itens":[{label, periodo, href, atual, parcial}]}
      pagina_semana = None (página do mês) ou {numero, periodo, parcial, mes}."""
    manifest_path = ROOT / "data" / "historico" / "manifest.json"
    if not manifest_path.exists():
        return None, None
    try:
        entradas = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, None
    base = OUT_PATH.parent
    def rel(alvo):
        return os.path.relpath(alvo, base).replace(os.sep, "/")
    def html_de(e):
        return ROOT / "historico" / e["arquivo"].replace(".xlsx", ".html")
    atual = None
    home = ROOT / "index.html"
    if OUT_PATH.resolve() == home.resolve():
        arq_home = ""
        try:
            arq_home = os.path.basename(json.loads(CONFIG_HOME_PATH.read_text(encoding="utf-8")).get("arquivo", ""))
        except (OSError, json.JSONDecodeError):
            pass
        atual = next((e for e in entradas if e.get("arquivo") == arq_home), None)
    else:
        atual = next((e for e in entradas if html_de(e).resolve() == OUT_PATH.resolve()), None)
    if not atual:
        return None, None
    mes = atual.get("mes") if atual.get("tipo") == "semana" else atual.get("label")
    semanas = sorted((e for e in entradas if e.get("tipo") == "semana" and e.get("mes") == mes),
                     key=lambda e: e.get("numero_semana", 0))
    if not semanas:
        return None, None
    e_mes = next((e for e in entradas if e.get("tipo") != "semana" and e.get("label") == mes), None)
    itens = []
    for e in semanas:
        itens.append({"label": f"Semana {e['numero_semana']}", "periodo": e.get("periodo", ""),
                      "href": rel(html_de(e)), "parcial": bool(e.get("parcial")),
                      "atual": atual is e})
    if e_mes:
        mes_href = rel(home) if (home.exists() and CONFIG_HOME_PATH.exists() and
                                 os.path.basename(json.loads(CONFIG_HOME_PATH.read_text(encoding="utf-8")).get("arquivo", "")) == e_mes["arquivo"]
                                 and atual.get("tipo") != "semana") else rel(html_de(e_mes))
        itens.append({"label": "Mês completo", "periodo": mes, "href": mes_href, "parcial": False,
                      "atual": atual is e_mes})
    pagina = None
    if atual.get("tipo") == "semana":
        pagina = {"numero": atual.get("numero_semana"), "periodo": atual.get("periodo", ""),
                  "parcial": bool(atual.get("parcial")), "mes": mes}
    return {"mes": mes, "itens": itens}, pagina


# Blocos onde espaço em branco TEM significado (código e texto pré-formatado) —
# nunca mexemos neles ao enxugar o HTML.
_BLOCOS_LITERAIS_RE = re.compile(r"(<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<textarea\b.*?</textarea>)",
                                 re.S | re.I)
_ESPACOS_RE = re.compile(r"\s{2,}")

def enxugar_html(html):
    """Reduz o tamanho da página sem mudar o que aparece: o HTML dos templates
    é cheio de indentação (metade dos bytes do Acumulado eram só espaço em
    branco). Aqui toda sequência de 2+ espaços/quebras de linha FORA de
    <script>/<style>/<pre>/<textarea> vira 1 espaço — o navegador já colapsa
    espaços em branco do mesmo jeito, então o resultado visual é idêntico."""
    partes = _BLOCOS_LITERAIS_RE.split(html)
    for i in range(0, len(partes), 2):  # índices pares = fora dos blocos literais
        partes[i] = _ESPACOS_RE.sub(" ", partes[i])
    return "".join(partes)


def periodo_em_andamento(semana_fim_html, hoje):
    """Sexta-feira em que o período termina SE ele ainda está em andamento (hoje <= essa sexta); senão None.
    `semana_fim_html` é o HTML ID da última semana OFICIAL do período (semana_fim do manifest)."""
    if not semana_fim_html:
        return None
    sexta = sem_evisita.data_fim_semana_html(int(semana_fim_html)) - timedelta(days=1)
    return sexta if hoje <= sexta else None


def _selo_periodo(ctx):
    """'dd/mm' da sexta final quando a página é de um MÊS ainda em andamento; senão ''."""
    if ctx.get("pagina_semana") or ctx.get("acumulado_so_media"):
        return ""
    try:
        man = json.loads((ROOT / "data" / "historico" / "manifest.json").read_text(encoding="utf-8"))
        e = next(x for x in man if x.get("arquivo") == Path(XLSX_PATH).name and x.get("tipo") != "semana")
        from zoneinfo import ZoneInfo
        fim = periodo_em_andamento(e.get("semana_fim"), datetime.now(ZoneInfo("America/Campo_Grande")).date())
        return fim.strftime("%d/%m") if fim else ""
    except Exception:
        return ""


def main():
    if not XLSX_PATH.exists():
        print(f"ERRO: planilha não encontrada em {XLSX_PATH}", file=sys.stderr)
        sys.exit(1)
    data = load_all(XLSX_PATH)
    ctx = build_context(data)
    ctx["periodos"] = carregar_periodos()
    # Acumulado (vários meses somados): o ranking mostra só a MÉDIA das notas
    # mensais (aba Média Mensal), não um ranking somado.
    ctx["acumulado_so_media"] = XLSX_PATH.resolve() == ACUMULADO_XLSX.resolve()
    ctx["nav_semanas"], ctx["pagina_semana"] = carregar_nav_semanas()
    ctx["periodo_parcial"] = _selo_periodo(ctx)
    rotulo_extrato = None
    if ctx["pagina_semana"]:
        # Página de uma semana: o seletor de período aponta para o MÊS dela e
        # o extrato diz "Semana N (dd/mm a dd/mm)".
        ps = ctx["pagina_semana"]
        for p in ctx["periodos"]:
            p["atual"] = p["label"] == "📅 " + ps["mes"] or p["label"] == f"🏠 Início ({ps['mes']})"
        rotulo_extrato = f"Semana {ps['numero']} de {ps['mes']} ({ps['periodo']})" + (" — parcial" if ps["parcial"] else "")
    ctx["extratos"] = build_extratos(ctx["ranking"], ctx["ranking_detalhe"],
                                     ctx["ranking_sem_normalizacao"], rotulo_extrato or _periodo_label(ctx["periodos"]))
    ctx["extratos"]["mes"] = _mes_contestavel(ctx)
    # "Como é calculado" agora é uma aba do álbum (transparencia.html só redireciona, para links antigos)
    ctx["transparencia_href"] = os.path.relpath(ROOT / "album.html", OUT_PATH.parent).replace(os.sep, "/") + "#como-calcula"
    ctx["comparacao_semanal"] = build_comparacao_semanal(ctx["nav_semanas"], ctx["pagina_semana"])
    cs = ctx["comparacao_semanal"]
    if cs and cs.get("media_mes"):
        for card in ctx.get("team_cards") or []:
            card["nota_media_mes"] = cs["media_mes"].get(card["nome"])
    ctx["agente_href"] = os.path.relpath(ROOT / "agente.html", OUT_PATH.parent).replace(os.sep, "/")
    ctx["contestacao_href"] = os.path.relpath(ROOT / "contestacao.html", OUT_PATH.parent).replace(os.sep, "/")
    ctx["worker_url"] = _worker_url() if _mes_contestavel(ctx) else ""
    ctx["logo_href"] = os.path.relpath(ROOT / "assets" / "logo_ponta_pora.png", OUT_PATH.parent).replace(os.sep, "/")

    # --- Peso das páginas: Chart.js vira arquivo compartilhado (cacheado pelo
    # navegador entre as páginas) e as partes pesadas (tabelas de alertas e
    # extratos) vão para partes/<página>.*.js, carregadas só quando usadas.
    assets_dir = ROOT / "assets"
    assets_dir.mkdir(exist_ok=True)
    chart_src = SCRIPTS_DIR / "chart.umd.js"
    chart_dst = assets_dir / "chart.umd.js"
    if not chart_dst.exists() or chart_dst.read_bytes() != chart_src.read_bytes():
        chart_dst.write_bytes(chart_src.read_bytes())
    ctx["chartjs_href"] = os.path.relpath(chart_dst, OUT_PATH.parent).replace(os.sep, "/")
    ctx["fontes_href"] = os.path.relpath(assets_dir / "fontes.css", OUT_PATH.parent).replace(os.sep, "/")
    ctx["tema_href"] = os.path.relpath(assets_dir / "tema.js", OUT_PATH.parent).replace(os.sep, "/")
    ctx["projecao_href"] = os.path.relpath(ROOT / "projecao.html", OUT_PATH.parent).replace(os.sep, "/")
    ctx["album_href"] = os.path.relpath(ROOT / "album.html", OUT_PATH.parent).replace(os.sep, "/")
    ctx["comparar_href"] = os.path.relpath(ROOT / "comparar.html", OUT_PATH.parent).replace(os.sep, "/")
    ctx["sprite"] = icones.sprite()
    try:
        ctx["xlsx_href"] = os.path.relpath(XLSX_PATH, OUT_PATH.parent).replace(os.sep, "/") if Path(XLSX_PATH).exists() else ""
    except ValueError:
        ctx["xlsx_href"] = ""
    partes_dir = ROOT / "partes"
    partes_dir.mkdir(exist_ok=True)
    stem = OUT_PATH.stem
    ctx["alertas_src"] = ctx["extratos_src"] = ""
    if LAZY:
        ctx["alertas_src"] = os.path.relpath(partes_dir / f"{stem}.alertas.js", OUT_PATH.parent).replace(os.sep, "/")
        ctx["extratos_src"] = os.path.relpath(partes_dir / f"{stem}.extratos.js", OUT_PATH.parent).replace(os.sep, "/")

    env = Environment(loader=FileSystemLoader(str(SCRIPTS_DIR / "templates")), autoescape=True)
    env.filters.update(br=br, badge=badge, id_link=id_link, class_key=class_key, row_class=row_class,
                        rank_badge=rank_badge)
    env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}
    if LAZY:
        frag = icones.iconizar(enxugar_html(env.get_template("sections/alertas_tabelas.html").render(**{**ctx, "alertas_src": ""})))
        (partes_dir / f"{stem}.alertas.js").write_text(
            "window.SENT_PARTES=window.SENT_PARTES||{};window.SENT_PARTES.alertas="
            + json.dumps(frag, ensure_ascii=False) + ";", encoding="utf-8")
        (partes_dir / f"{stem}.extratos.js").write_text(
            "window.EXTRATOS=" + json.dumps(ctx["extratos"], ensure_ascii=False) + ";", encoding="utf-8")
    html = icones.iconizar(enxugar_html(env.get_template("base.html").render(**ctx)))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"OK: {OUT_PATH} gerado a partir de {XLSX_PATH} ({len(html):,} bytes)")

if __name__ == "__main__":
    main()
