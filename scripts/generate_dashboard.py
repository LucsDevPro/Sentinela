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
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xlsx_scan import get_tables  # noqa: E402
import semanas_evisita as sem_evisita  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Precisam bater com as constantes de mesmo nome em scripts/coletar_evisita.py
# — usadas só pra dar contexto/comparação na tabela "Outras Atividades" do
# Custos (equipes fora do e-Visita, com produção lançada manualmente em
# data/outras_atividades.json).
DIAS_UTEIS_MES_REF = 22
META_VISITAS_DIA_REF = 20
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
# scripts/coletar_evisita.py::salvar_excel_consolidado).
RESUMO_SEMANAL_COLS = {"Semana": "semana", "Período": "periodo", **RESUMO_COLS}
RANKING_COLS = {
    "Posição": "posicao", "Agente": "agente", "Equipe": "equipe",
    "Dias Trabalhados": "dias_trabalhados", "Dias Úteis Esperados no Mês": "dias_uteis_esperados",
    "Turnos Sem Trabalhar": "turnos_sem_trabalhar",
    "Pontuação Final": "pontos", "Classificação": "classificacao",
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
    teto_media = primeira_tabela(path, "Visitas Acima de 15min", ["ID Visita"])
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
    resumo = sem_bloqueio(resumo)
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

def build_kpi_custos(resumo):
    if resumo.empty or "CustoNum" not in resumo.columns:
        return dict(custo_medio=0, custo_min=0, custo_min_agente="—", custo_max=0, custo_max_agente="—",
                    horas_dia_media=0, horas_semana_media=0, horas_uteis_media=0)
    idx_min, idx_max = resumo["CustoNum"].idxmin(), resumo["CustoNum"].idxmax()
    return dict(
        custo_medio=resumo["CustoNum"].mean(),
        custo_min=resumo.loc[idx_min, "CustoNum"], custo_min_agente=resumo.loc[idx_min, "Agente"],
        custo_max=resumo.loc[idx_max, "CustoNum"], custo_max_agente=resumo.loc[idx_max, "Agente"],
        horas_dia_media=resumo["Média Horas Trabalhadas/Dia"].mean(),
        horas_semana_media=resumo["Média Horas Trabalhadas/Semana"].mean(),
        horas_uteis_media=resumo["Média Horas Úteis/Dia"].mean(),
    )

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
        custo_data=agent_series("CustoNum", ascending=False),
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
        ferias_atestado_rows=[r for r in _cronograma_rows_calc
                               if not r["auto"] and ("férias" in r["motivo"].lower() or "atestado" in r["motivo"].lower())],
        pendencias=records(pendencias.sort_values("% Pendência", ascending=False), PENDENCIA_COLS) if not pendencias.empty else [],
        ponto_estrategico=records(pe.sort_values("Semana"), PE_COLS) if not pe.empty else [],
        pe_agente=pe["Agente"].iloc[0] if not pe.empty else "—",
        pe_semanas=pe["Semana"].nunique() if not pe.empty else 0,
        custos=records(resumo.sort_values("CustoNum", ascending=False), RESUMO_COLS),
        ranking=records(data["ranking"].sort_values("Posição"), RANKING_COLS) if not data["ranking"].empty else [],
        ranking_detalhe=records(data["ranking_detalhe"], RANKING_DET_COLS) if not data["ranking_detalhe"].empty else [],
        kpi_ranking=build_kpi_ranking(data["ranking"]),
        resumo_bloqueio=records(data["resumo_bloqueio"], RESUMO_COLS) if not data["resumo_bloqueio"].empty else [],
        pendencias_bloqueio=records(data["pendencias_bloqueio"], PENDENCIA_COLS) if not data["pendencias_bloqueio"].empty else [],
        chart_data=build_chart_data(data),
        css=(SCRIPTS_DIR / "style.css").read_text(encoding="utf-8"),
        chartjs=(SCRIPTS_DIR / "chart.umd.js").read_text(encoding="utf-8"),
        bootstrap_js=(SCRIPTS_DIR / "bootstrap.js").read_text(encoding="utf-8"),
    )

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
    if CONFIG_HOME_PATH.exists():
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
            alvo = ROOT / "historico" / e["arquivo"].replace(".xlsx", ".html")
            href = os.path.relpath(alvo, OUT_PATH.parent).replace(os.sep, "/")
            itens.append({"label": "📅 " + e["label"], "href": href,
                          "atual": alvo.resolve() == OUT_PATH.resolve()})
    return itens

def main():
    if not XLSX_PATH.exists():
        print(f"ERRO: planilha não encontrada em {XLSX_PATH}", file=sys.stderr)
        sys.exit(1)
    data = load_all(XLSX_PATH)
    ctx = build_context(data)
    ctx["periodos"] = carregar_periodos()
    ctx["logo_href"] = os.path.relpath(ROOT / "assets" / "logo_ponta_pora.png", OUT_PATH.parent).replace(os.sep, "/")

    env = Environment(loader=FileSystemLoader(str(SCRIPTS_DIR / "templates")), autoescape=True)
    env.filters.update(br=br, badge=badge, id_link=id_link, class_key=class_key, row_class=row_class,
                        rank_badge=rank_badge)
    env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}
    html = env.get_template("base.html").render(**ctx)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"OK: {OUT_PATH} gerado a partir de {XLSX_PATH} ({len(html):,} bytes)")

if __name__ == "__main__":
    main()
