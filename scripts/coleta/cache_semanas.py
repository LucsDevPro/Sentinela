# -*- coding: utf-8 -*-
"""Cache por semana (data/semanas/): ler, salvar, mesclar e coletar uma semana.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import semanas_evisita as sem
from .parametros import (
    AGENTES_PONTO_ESTRATEGICO,
    AGENTES_POR_EQUIPE,
    CAMINHO_CACHE_NOMES_AGENTES,
    MAX_WORKERS,
    PASTA_SEMANAS,
    PRIMEIRA_SEMANA_CICLO_EXPLICITO,
    TETO_DURACAO_MEDIA_MIN,
    _atualizar_cache_nomes_agentes,
    _cache_nomes_agentes,
    _registrar_ciclos_coletados,
    ciclo_para_semana,
    ciclo_tratamento_configurado,
    ciclo_tratamento_para_semana,
)
from .processamento import processar, processar_ponto_estrategico

log = logging.getLogger("evisita")


# ============================================================
# CACHE POR SEMANA (data/semanas/) — coleta e consolidação
# ============================================================
# Cada semana vira UMA planilha própria (visitas + colunas calculadas) mais
# um JSON pequeno com os números de pendência (fechados/recusados) daquela
# semana. Consolidar N semanas é: carregar as N planilhas, juntar tudo e
# recalcular os resumos por agente em cima do conjunto combinado — os
# mesmos cálculos de sempre (resumo_agente etc.), só que agora alimentados
# pelo cache em vez de uma coleta ao vivo.

_COLS_BOOL_SEMANA = [
    "alerta_rapida", "alerta_longa", "acima_teto_media", "alerta_neg",
    "dup_por_id", "dup_por_chegada_imovel", "duplicada",
    "par_suspeito_anterior", "sequencia_suspeita",
    "fim_de_semana", "dentro_expediente", "fora_expediente",
    "visita_horario_almoco",
]
_COLS_DATETIME_SEMANA = ["dt_chegada", "dt_saida"]


def _caminho_semana(html_id, sufixo="", pasta_semanas=PASTA_SEMANAS):
    nome = f"{html_id}{sufixo}"
    return os.path.join(pasta_semanas, nome)


# Cache EM MEMÓRIA (só dura o processo) da leitura crua da aba "visitas" de cada semana. Ler uma planilha com
# pd.read_excel custa ~1,5 s e a mesma semana era relida em cada etapa (detecção, Acumulado, cada mês do
# histórico): a detecção sozinha gastava 53 de 56 s nisso. Guarda o resultado CRU do read_excel (as conversões
# de _carregar_df_semana rodam a cada chamada, então mudar uma constante como TETO_DURACAO_MEDIA_MIN continua
# valendo) e sempre devolve uma CÓPIA. A chave inclui data de modificação e tamanho: se a planilha mudar, relê.
# SENTINELA_SEM_CACHE_LEITURA=1 desliga (útil para comparar resultados).
_CACHE_LEITURA = {}          # (caminho absoluto, mtime_ns, tamanho) -> DataFrame cru
_CACHE_LEITURA_MAX = 64      # ~1,6 MB por semana: 64 semanas cabem em ~100 MB
_LOCK_CACHE = threading.Lock()   # a coleta lê semanas em threads: só as operações no dicionário ficam sob o lock


def _ler_aba_visitas(caminho_xlsx):
    if os.environ.get("SENTINELA_SEM_CACHE_LEITURA") == "1":
        return pd.read_excel(caminho_xlsx, sheet_name="visitas")
    st = os.stat(caminho_xlsx)
    chave = (os.path.abspath(caminho_xlsx), st.st_mtime_ns, st.st_size)
    with _LOCK_CACHE:
        df = _CACHE_LEITURA.get(chave)
    if df is None:
        df = pd.read_excel(caminho_xlsx, sheet_name="visitas")      # fora do lock: leituras em paralelo seguem paralelas
        with _LOCK_CACHE:
            for k in [k for k in _CACHE_LEITURA if k[0] == chave[0]]:    # versão velha do mesmo arquivo
                _CACHE_LEITURA.pop(k, None)
            while len(_CACHE_LEITURA) >= _CACHE_LEITURA_MAX:
                _CACHE_LEITURA.pop(next(iter(_CACHE_LEITURA)), None)
            _CACHE_LEITURA[chave] = df
    return df.copy()


def _salvar_df_semana(df, caminho_xlsx):
    os.makedirs(os.path.dirname(caminho_xlsx), exist_ok=True)
    df.to_excel(caminho_xlsx, sheet_name="visitas", index=False)
    with _LOCK_CACHE:
        for k in [k for k in _CACHE_LEITURA if k[0] == os.path.abspath(caminho_xlsx)]:
            _CACHE_LEITURA.pop(k, None)


def _carregar_df_semana(caminho_xlsx):
    """Recarrega uma planilha de semana cacheada, corrigindo os tipos que o
    Excel não guarda sozinho (datas viram texto/serial, booleanos podem
    virar 'True'/'False' em string etc.)."""
    if not os.path.exists(caminho_xlsx):
        return pd.DataFrame()
    df = _ler_aba_visitas(caminho_xlsx)
    for col in _COLS_DATETIME_SEMANA:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "dia" in df.columns:
        df["dia"] = pd.to_datetime(df["dia"], errors="coerce").dt.date
    for col in _COLS_BOOL_SEMANA:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower().map(
                {"true": True, "1": True, "1.0": True,
                 "false": False, "0": False, "0.0": False}
            ).fillna(False)
    # "acima_teto_media" é recalculada aqui em vez de confiar no valor
    # cacheado: se TETO_DURACAO_MEDIA_MIN mudar (ex.: de 15 pra 20min), uma
    # semana já coletada ANTES da mudança não deve continuar presa ao teto
    # antigo — a próxima consolidação já reflete o teto atual, sem precisar
    # recoletar nada do e-Visita.
    if "duracao_min" in df.columns:
        df["acima_teto_media"] = df["duracao_min"] > TETO_DURACAO_MEDIA_MIN
    return df


def _mesclar_com_cache_anterior(html_id, df_tratamento, pendencia_por_agente, ids_falha):
    """Evita que uma recoleta PIOR apague dados bons que já estavam no cache.

    Regra: a recoleta SUBSTITUI os dados de cada agente (nunca soma por cima,
    então não há duplicata) — exceto para agentes que falharam nesta rodada
    (`ids_falha`: sem página 1, sessão caída, erro) ou que vieram com páginas
    faltando e MENOS visitas do que já estava salvo: pra esses, mantém o que
    já existia no cache. Devolve (df, pendencia) já mesclados."""
    df_ant = _carregar_df_semana(_caminho_semana(html_id, ".xlsx"))
    caminho_pend = _caminho_semana(html_id, "_pendencia.json")
    pend_ant = {}
    if os.path.exists(caminho_pend):
        try:
            with open(caminho_pend, encoding="utf-8") as f:
                pend_ant = json.load(f)
        except (json.JSONDecodeError, OSError):
            pend_ant = {}

    df_novo = df_tratamento if df_tratamento is not None else pd.DataFrame()
    if df_ant.empty and not pend_ant:
        return df_novo, pendencia_por_agente

    manter = {str(i) for i in ids_falha}
    for id_ag, p in pendencia_por_agente.items():
        if p.get("paginas_falhas"):
            n_novo = 0 if df_novo.empty else int((df_novo["id_agente"].astype(str) == str(id_ag)).sum())
            n_ant = 0 if df_ant.empty else int((df_ant["id_agente"].astype(str) == str(id_ag)).sum())
            if n_ant > n_novo:
                manter.add(str(id_ag))

    # Agente que JÁ tinha visitas salvas e agora volta sem nenhuma (resposta vazia
    # por instabilidade do site) ou com menos da metade: nunca piora — mantém o antigo.
    if not df_ant.empty:
        for id_ag, n_ant in df_ant["id_agente"].astype(str).value_counts().items():
            n_novo = 0 if df_novo.empty else int((df_novo["id_agente"].astype(str) == id_ag).sum())
            if n_novo == 0 or (n_ant >= 10 and n_novo < 0.5 * n_ant):
                manter.add(id_ag)

    pendencia_final = dict(pendencia_por_agente)
    frames = []
    if not df_novo.empty:
        frames.append(df_novo[~df_novo["id_agente"].astype(str).isin(manter)])
    if not df_ant.empty:
        # agentes que a recoleta não trouxe NENHUMA linha mas falharam, ou a
        # serem mantidos explicitamente
        frames.append(df_ant[df_ant["id_agente"].astype(str).isin(manter)])
    for id_ag in manter:
        if id_ag in pend_ant:
            pendencia_final[id_ag] = pend_ant[id_ag]
    if manter:
        log.warning("🛡️ Semana %s: mantidos dados já salvos de %s agente(s) que falharam/vieram incompletos "
                     "nesta recoleta: %s", html_id, len(manter), sorted(manter))
    df_final = pd.concat(frames, ignore_index=True) if frames else df_novo
    return df_final, pendencia_final


def salvar_cache_semana(html_id, df_tratamento, pendencia_por_agente, df_pe=None, ids_falha=()):
    """Grava em disco tudo que foi coletado para UMA semana: a planilha de
    visitas (tratamento), a planilha de Ponto Estratégico (se houve) e um
    JSON com os números de pendência (fechados/recusados) por agente.

    Nunca piora um cache existente: uma recoleta vazia não apaga a planilha
    nem o JSON de pendência anteriores, e agentes que falharam mantêm os
    dados antigos (ver _mesclar_com_cache_anterior)."""
    os.makedirs(PASTA_SEMANAS, exist_ok=True)
    df_tratamento, pendencia_por_agente = _mesclar_com_cache_anterior(
        html_id, df_tratamento, pendencia_por_agente, ids_falha)
    if df_tratamento is not None and not df_tratamento.empty:
        _salvar_df_semana(df_tratamento, _caminho_semana(html_id, ".xlsx"))
    caminho_pend = _caminho_semana(html_id, "_pendencia.json")
    if pendencia_por_agente or not os.path.exists(caminho_pend):
        with open(caminho_pend, "w", encoding="utf-8") as f:
            json.dump(pendencia_por_agente, f, ensure_ascii=False, indent=2)
    if df_pe is not None and not df_pe.empty:
        _salvar_df_semana(df_pe, _caminho_semana(html_id, "_pe.xlsx"))
    log.info("💾 Semana %s (Semana do Ano %s) cacheada em %s",
              html_id, sem.html_para_semana(html_id, sem.ano_da_semana_html(html_id)), PASTA_SEMANAS)


def coletar_uma_semana(session, html_id, id_ano, id_ciclo):
    """Coleta TODOS os agentes (tratamento + Ponto Estratégico, quando
    aplicável) para uma única semana (HTML ID) e já salva o cache em disco
    antes de retornar. Retorna um dict com estatísticas de integridade pra
    logar no resumo final."""
    if html_id >= PRIMEIRA_SEMANA_CICLO_EXPLICITO and ciclo_tratamento_configurado(html_id) is None:
        motivo = (f"semana {html_id} sem id_ciclo de Tratamento em CICLOS_TRATAMENTO — "
                  f"coleta pulada (o ciclo padrão {id_ciclo} devolveria dados vazios)")
        log.error("❌ %s", motivo)
        return {"html_id": html_id, "sessao_caiu": False,
                "agentes_ausentes": [("-", "-", motivo)], "agentes_incompletos": [],
                "total_agentes": 0}
    id_ciclo_semana = ciclo_tratamento_para_semana(html_id, id_ciclo)
    cfg = {"semana_inicio": html_id, "semana_fim": html_id, "id_ano": id_ano, "id_ciclo": id_ciclo_semana}
    trabalhos = [(eq, ag) for eq, agentes in AGENTES_POR_EQUIPE.items() for ag in agentes]
    log.info("🚀 Semana %s (%s) | %s agentes | ano %s | ciclo %s",
              html_id, sem.rotulo_semana_html(html_id), len(trabalhos), id_ano, id_ciclo_semana)

    frames, pendencia_por_agente = [], {}
    sessao_caiu = False
    agentes_ausentes, agentes_incompletos = [], []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futuros = {ex.submit(processar, eq, ag, session, cfg): (eq, ag) for eq, ag in trabalhos}
        for fut in as_completed(futuros):
            eq, ag = futuros[fut]
            try:
                ret = fut.result()
                if ret["ok"]:
                    frames.append(ret["df"])
                    pendencia_por_agente[str(ret["id_agente"])] = {
                        "nome_agente": ret["nome_agente"],
                        "equipe": ret["equipe"],
                        "imoveis_fechados": ret["resumo"]["imoveis_fechados"],
                        "imoveis_recusados": ret["resumo"]["imoveis_recusados"],
                        "fechados_por_area": ret["fechados_por_area"],
                        "recusados_por_area": ret["recusados_por_area"],
                        "visitas_recusados_raw": ret["visitas_recusados_raw"],
                        "paginas_falhas": ret["paginas_falhas"],
                    }
                    r = ret["resumo"]
                    log.info("✅ %s | %s visitas | Duplicadas: %s",
                              ret["nome_agente"], r["total_visitas"], r["visitas_duplicadas"])
                    if ret.get("paginas_falhas"):
                        agentes_incompletos.append((ret["nome_agente"], eq, ret["paginas_falhas"]))
                elif ret.get("erro") == "sessao_expirada":
                    sessao_caiu = True
                    agentes_ausentes.append((ag, eq, "sessão expirou durante a coleta"))
                elif ret.get("erro") == "falha_pagina1":
                    agentes_ausentes.append((ag, eq, "falha ao coletar página 1 (mesmo após retries)"))
                else:
                    log.warning("⚠️ Sem visitas para agente %s (%s) na semana %s", ag, eq, html_id)
            except Exception as e:
                log.error("❌ Erro processando agente %s (%s) na semana %s: %s", ag, eq, html_id, e)
                agentes_ausentes.append((ag, eq, f"erro inesperado: {e}"))

    if sessao_caiu:
        log.error("A sessão expirou durante a coleta da semana %s — refaça o login e rode de novo.", html_id)

    df_tratamento = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # Ponto Estratégico — só busca se houver ciclo cadastrado pra essa semana.
    df_pe = pd.DataFrame()
    id_ciclo_pe = ciclo_para_semana(html_id)
    if AGENTES_PONTO_ESTRATEGICO and id_ciclo_pe is None:
        log.warning("⚠️ Ponto Estratégico: semana %s cai num ciclo sem id_ciclo cadastrado em "
                     "CICLOS_PONTO_ESTRATEGICO — pulando (confira o id_ciclo no site e cadastre-o).", html_id)
    elif AGENTES_PONTO_ESTRATEGICO:
        cfg_pe = {"semana_inicio": html_id, "semana_fim": html_id, "id_ano": id_ano, "id_ciclo": id_ciclo_pe}
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futuros_pe = {ex.submit(processar_ponto_estrategico, ag, session, cfg_pe): ag
                          for ag in AGENTES_PONTO_ESTRATEGICO}
            frames_pe = []
            for fut in as_completed(futuros_pe):
                ag = futuros_pe[fut]
                try:
                    ret = fut.result()
                    if ret["ok"]:
                        frames_pe.append(ret["df"])
                        log.info("✅ Ponto Estratégico — Agente %s (semana %s)", ret["nome_agente"], html_id)
                    else:
                        log.warning("⚠️ Ponto Estratégico — sem dados pro agente %s na semana %s (%s)",
                                     ag, html_id, ret.get("erro", "sem visitas"))
                except Exception as e:
                    log.error("❌ Erro no Ponto Estratégico, agente %s, semana %s: %s", ag, html_id, e)
        if frames_pe:
            df_pe = pd.concat(frames_pe, ignore_index=True)

    ids_falha = [ag for ag, _eq, _motivo in agentes_ausentes if ag != "-"]
    salvar_cache_semana(html_id, df_tratamento, pendencia_por_agente, df_pe, ids_falha=ids_falha)

    # Só registra o ciclo como "coletado" se a coleta foi íntegra — senão a
    # semana volta sozinha pra fila na próxima execução.
    if (html_id >= PRIMEIRA_SEMANA_CICLO_EXPLICITO and not sessao_caiu
            and not agentes_ausentes and not agentes_incompletos and not df_tratamento.empty):
        _registrar_ciclos_coletados(html_id)
    elif html_id >= PRIMEIRA_SEMANA_CICLO_EXPLICITO:
        log.warning("⚠️ Semana %s coletada de forma incompleta/vazia — ciclo NÃO registrado; "
                     "será reprocessada na próxima execução.", html_id)

    return {
        "html_id": html_id, "sessao_caiu": sessao_caiu,
        "agentes_ausentes": agentes_ausentes, "agentes_incompletos": agentes_incompletos,
        "total_agentes": len(trabalhos),
    }


def _salvar_agentes_nomes(resultados, caminho=CAMINHO_CACHE_NOMES_AGENTES):
    """Atualiza (MERGE — nunca apaga o que já tinha) o mapa ID -> Nome de
    cada agente, toda vez que consolida. É a mesma função por trás do
    cache usado por extrair_nome_agente() (ver _cache_nomes_agentes()) —
    aqui é só o ponto em que os nomes vindos da CONSOLIDAÇÃO (que pode
    rodar sobre um recorte pequeno, tipo um mês só, dentro de
    atualizar_historico_do_cache) entram nesse mesmo cache. Sem o merge,
    consolidar um mês em que um agente não teve nenhum lançamento
    SOBRESCREVIA o arquivo inteiro e apagava o nome dele — que só ficava
    conhecido de novo na próxima vez que ele aparecesse com dados.

    Também serve pra cronograma_editor.html mostrar nomes de verdade no
    menu em vez de só "ID 116", sem precisar digitar nada — é só colar
    esse arquivo lá."""
    for r in resultados:
        _atualizar_cache_nomes_agentes(r["id_agente"], r["nome_agente"], r["equipe"], caminho)
    log.info("💾 Nomes dos agentes atualizados em %s (%s agentes no cache).",
              caminho, len(_cache_nomes_agentes(caminho)))
