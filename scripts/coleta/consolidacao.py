# -*- coding: utf-8 -*-
"""Consolidação das semanas em cache em Analise_Consolidada.xlsx.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import json
import pandas as pd
from .parametros import PASTA_SEMANAS, _cache_nomes_agentes, semanas_ja_coletadas
from .deteccao import _cronograma_efetivo, atualizar_deteccoes_pendentes, detectar_ausencias_e_paralisacoes
from .calculos import resumo_agente
from .saida_excel import salvar_excel_consolidado
from .cache_semanas import _caminho_semana, _carregar_df_semana, _salvar_agentes_nomes

log = logging.getLogger("evisita")


def _montar_df_total_e_resultados(htmls):
    """Carrega o cache de cada semana em `htmls` e monta df_total + resultados
    (um dict por agente, já com resumo_agente() calculado) — a parte "pesada"
    de consolidar_semanas(), extraída à parte pra poder rodar a detecção de
    férias/paralisação (detectar_ausencias_e_paralisacoes) em cima do
    histórico INTEIRO sem precisar gerar o Excel também. Retorna
    (df_total, resultados, frames_pe) — frames_pe é a lista de DataFrames do
    Ponto Estratégico (pode estar vazia)."""
    htmls = sorted(set(htmls))
    frames, frames_pe = [], []
    pendencia = {}
    for h in htmls:
        df_h = _carregar_df_semana(_caminho_semana(h, ".xlsx"))
        if not df_h.empty:
            frames.append(df_h)
        df_pe_h = _carregar_df_semana(_caminho_semana(h, "_pe.xlsx"))
        if not df_pe_h.empty:
            frames_pe.append(df_pe_h)
        pend_path = _caminho_semana(h, "_pendencia.json")
        if os.path.exists(pend_path):
            with open(pend_path, encoding="utf-8") as f:
                for id_ag, info in json.load(f).items():
                    pendencia.setdefault(id_ag, []).append(info)

    if not frames:
        return pd.DataFrame(), [], frames_pe

    df_total = pd.concat(frames, ignore_index=True)

    resultados = []
    for id_ag, sub in df_total.groupby("id_agente"):
        sub = sub.sort_values("dt_chegada").reset_index(drop=True)
        nome = sub["nome_agente"].iloc[0]
        equipe = sub["equipe"].iloc[0]
        if str(nome).startswith("Agente_"):
            # Nome genérico já GRAVADO num arquivo de semana antigo (de
            # antes de existir esse cache, ou de uma coleta em que a
            # resolução falhou naquele momento). Não precisa recoletar a
            # semana pra corrigir — se o nome de verdade já foi aprendido
            # DEPOIS (em qualquer outra semana, ou colado manualmente em
            # data/agentes_nomes.json), usa ele aqui na hora de consolidar.
            nome_cache = _cache_nomes_agentes().get(str(id_ag), {}).get("nome")
            if nome_cache:
                nome = nome_cache
        resumo = resumo_agente(sub)

        pend_semanas = pendencia.get(str(id_ag), [])
        total_fechados = sum(p["imoveis_fechados"] for p in pend_semanas)
        total_recusados = sum(p["imoveis_recusados"] for p in pend_semanas)
        total_abertos = resumo["total_visitas"]
        total_geral_pendencia = total_abertos + total_fechados + total_recusados
        resumo["imoveis_fechados"] = total_fechados
        resumo["imoveis_recusados"] = total_recusados
        resumo["total_geral_pendencia"] = total_geral_pendencia
        resumo["pct_pendencia"] = round(((total_fechados + total_recusados) / total_geral_pendencia * 100), 2) \
            if total_geral_pendencia > 0 else 0

        fechados_por_area, recusados_por_area, visitas_recusados_raw, paginas_falhas = {}, {}, [], []
        for p in pend_semanas:
            for area, qtd in p.get("fechados_por_area", {}).items():
                fechados_por_area[area] = fechados_por_area.get(area, 0) + qtd
            for area, qtd in p.get("recusados_por_area", {}).items():
                recusados_por_area[area] = recusados_por_area.get(area, 0) + qtd
            visitas_recusados_raw.extend(p.get("visitas_recusados_raw", []))
            paginas_falhas.extend(p.get("paginas_falhas", []))

        resultados.append({
            "ok": True, "id_agente": id_ag, "nome_agente": nome, "equipe": equipe,
            "resumo": resumo, "df": sub, "paginas_falhas": paginas_falhas,
            "fechados_por_area": fechados_por_area, "recusados_por_area": recusados_por_area,
            "visitas_recusados_raw": visitas_recusados_raw,
        })
    resultados.sort(key=lambda r: (r["equipe"], r["nome_agente"]))
    return df_total, resultados, frames_pe


def rodar_deteccao_completa(pasta_semanas=PASTA_SEMANAS):
    """Roda a detecção de possíveis férias/paralisação coletiva em cima do
    CACHE INTEIRO (todas as semanas já coletadas, não só as do período sendo
    gerado agora) — é assim que evita cortar errado um período de férias que
    atravessa a virada do mês. Atualiza data/deteccoes_pendentes.json e
    retorna a lista de cronograma "efetiva" (cronograma manual + detecções
    confirmadas), pronta pra passar em consolidar_semanas(lista_cronograma=...)."""
    todas = semanas_ja_coletadas(pasta_semanas)
    if not todas:
        return _cronograma_efetivo([])
    df_total, resultados, _ = _montar_df_total_e_resultados(todas)
    eventos = detectar_ausencias_e_paralisacoes(df_total, resultados)
    deteccoes = atualizar_deteccoes_pendentes(eventos)
    return _cronograma_efetivo(deteccoes)


def agentes_do_periodo(htmls):
    """Lista (id_agente, nome, equipe) de todo agente com pelo menos uma visita em `htmls`.
    Usada pela visão SEMANAL: quem trabalhou em outra semana do mês mas passou esta semana
    inteira sem lançar nenhuma visita não aparece no cache da semana — e sumiria do ranking
    semanal com a nota 100 que ele não merece (ver consolidar_semanas(agentes_extra=...))."""
    vistos = {}
    for h in sorted(set(htmls)):
        df_h = _carregar_df_semana(_caminho_semana(h, ".xlsx"))
        if df_h.empty:
            continue
        for id_ag, sub in df_h.groupby("id_agente"):
            nome, equipe = sub["nome_agente"].iloc[0], sub["equipe"].iloc[0]
            if str(nome).startswith("Agente_"):
                nome = _cache_nomes_agentes().get(str(id_ag), {}).get("nome") or nome
            vistos[id_ag] = (id_ag, nome, equipe)
    return list(vistos.values())


def consolidar_semanas(htmls, pasta_saida, lista_cronograma=None, agentes_extra=None):
    """Carrega o cache de cada semana em `htmls`, junta tudo e recalcula os
    resumos por agente (e por semana, no caso do Ponto Estratégico) em cima
    do conjunto combinado. Gera o Analise_Consolidada.xlsx com a MESMA
    função de sempre (salvar_excel_consolidado), só que alimentada pelo
    cache em vez de uma coleta ao vivo — o formato do Excel final não muda
    em nada.

    `lista_cronograma`: cronograma "efetivo" (manual + detecções
    confirmadas) já calculado por rodar_deteccao_completa() em cima do
    histórico INTEIRO. Se não passado, calcula um fallback só com os dados
    de `htmls` (uso avulso/manual) — mas isso pode sub-detectar um período
    de férias que continua fora desse recorte, então sempre que possível
    passe o resultado de rodar_deteccao_completa()."""
    htmls = sorted(set(htmls))
    df_total, resultados, frames_pe = _montar_df_total_e_resultados(htmls)

    if df_total.empty:
        log.error("Nenhuma semana com dados encontrada no cache (%s) para consolidar.", htmls)
        return None

    _salvar_agentes_nomes(resultados)

    if lista_cronograma is None:
        eventos = detectar_ausencias_e_paralisacoes(df_total, resultados)
        deteccoes = atualizar_deteccoes_pendentes(eventos)
        lista_cronograma = _cronograma_efetivo(deteccoes)

    semanas_ponto_estrategico = []
    if frames_pe:
        df_pe_total = pd.concat(frames_pe, ignore_index=True)
        for (id_ag, semana_num), sub in df_pe_total.groupby(["id_agente", "semana"], observed=True):
            if sub.empty:
                continue
            nome = sub["nome_agente"].iloc[0]
            resumo_semana = resumo_agente(sub)
            chegada_min, chegada_max = sub["dt_chegada"].min(), sub["dt_chegada"].max()
            periodo = (f"{chegada_min.strftime('%d/%m')} a {chegada_max.strftime('%d/%m')}"
                       if pd.notna(chegada_min) and pd.notna(chegada_max) else "")
            semanas_ponto_estrategico.append({
                "nome_agente": nome, "equipe": "Ponto Estratégico", "semana": int(semana_num),
                "periodo_semana": periodo, "resumo": resumo_semana,
            })

    # Resumo Semanal (tratamento) — mesma quebra por semana, só que pros
    # agentes normais, pra alimentar o filtro de semana do dashboard. Só
    # vale a pena gerar se o período consolidado cobrir mais de 1 semana.
    semanas_tratamento = []
    if len(htmls) > 1:
        for (id_ag, semana_num), sub in df_total.groupby(["id_agente", "semana"], observed=True):
            if sub.empty:
                continue
            nome = sub["nome_agente"].iloc[0]
            equipe = sub["equipe"].iloc[0]
            resumo_semana = resumo_agente(sub)
            chegada_min, chegada_max = sub["dt_chegada"].min(), sub["dt_chegada"].max()
            periodo = (f"{chegada_min.strftime('%d/%m')} a {chegada_max.strftime('%d/%m')}"
                       if pd.notna(chegada_min) and pd.notna(chegada_max) else "")
            semanas_tratamento.append({
                "nome_agente": nome, "equipe": equipe, "semana": int(semana_num),
                "periodo_semana": periodo, "resumo": resumo_semana,
            })

    # Agentes do mês que NÃO lançaram nenhuma visita neste período (visão semanal): entram só no
    # cálculo de ausências e do ranking (saida_excel), partindo dos 100 pontos e perdendo os
    # turnos sem lançamento — as demais abas continuam só com quem teve visita.
    agentes_sem_visita = []
    ids_com_visita = {str(r["id_agente"]) for r in resultados}
    for id_ag, nome, equipe in (agentes_extra or []):
        if str(id_ag) in ids_com_visita:
            continue
        vazio = df_total.iloc[0:0].copy()
        agentes_sem_visita.append({
            "ok": True, "id_agente": id_ag, "nome_agente": nome, "equipe": equipe,
            "resumo": resumo_agente(vazio), "df": vazio, "paginas_falhas": [],
            "fechados_por_area": {}, "recusados_por_area": {}, "visitas_recusados_raw": [],
            "sem_visita_no_periodo": True,
        })

    caminho = salvar_excel_consolidado(resultados, df_total, pasta_saida,
                                        semanas_ponto_estrategico, semanas_tratamento, lista_cronograma,
                                        agentes_sem_visita=agentes_sem_visita)
    log.info("🎉 Consolidado %s semana(s) (HTML %s-%s) em: %s", len(htmls), htmls[0], htmls[-1], caminho)
    return caminho
