# -*- coding: utf-8 -*-
"""Atualização do histórico mensal a partir do cache.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import re
import json
import shutil
from datetime import datetime, timedelta
import semanas_evisita as sem
from .parametros import (
    GERAR_PAGINAS_SEMANAIS,
    MESES_ADICIONAIS,
    MESES_ARQUIVADOS,
    PASTA_ARQUIVO_SEMANAL,
    PASTA_SEMANAS,
    PRIMEIRA_SEMANA_DETALHE_SEMANAL,
    PRIMEIRA_SEMANA_VISAO_SEMANAL,
    _faixa_mes_oficial,
    _grupo_mes_oficial,
    nome_periodo,
    semanas_ja_coletadas,
)
from .ausencias_ranking import _hoje_local
from .consolidacao import agentes_do_periodo, consolidar_semanas, rodar_deteccao_completa

log = logging.getLogger("evisita")


def atualizar_historico_do_cache(pasta_semanas=PASTA_SEMANAS, pasta_historico="data/historico",
                                  pasta_saida_tmp="output/_tmp_historico", lista_cronograma=None):
    """Reconstrói as entradas AUTOMÁTICAS de data/historico/ a partir do cache
    de semanas. Até PRIMEIRA_SEMANA_DETALHE_SEMANAL (exclusive), agrupa por
    mês civil (uma planilha por mês, como sempre foi) — a partir dela, CADA
    SEMANA vira sua própria página, pra dar mais detalhe e permitir revisar a
    última semana fechada isoladamente (Ausências, Alertas, Cronograma etc.
    só daquela semana, sem misturar com o resto do mês).

    `lista_cronograma`: mesma ideia de consolidar_semanas() — passe o
    resultado de rodar_deteccao_completa() pra não recalcular a detecção (e
    não sub-detectar por causa do recorte de cada mês/semana individual).

    Cada entrada do manifest.json tem um campo "origem": "cache" (escrita por
    esta função, pode ser sobrescrita à vontade) ou "manual" (adicionada por
    fora — ex.: uma planilha antiga de Jan-Maio/2026 coletada com outros
    parâmetros — e NUNCA tocada aqui, mesmo que não tenha nenhuma semana
    correspondente no cache).

    Pra adicionar uma entrada manual: coloque o arquivo .xlsx em
    data/historico/, e acrescente uma entrada em data/historico/manifest.json
    com "origem": "manual" (ver README, seção "Planilha antiga / fora do
    sistema de coleta"). Essa entrada nunca some, mesmo que o cache de
    semanas mude — e como ela nunca passa por consolidar_semanas(), nunca
    entra em data/Analise_Consolidada.xlsx nem em acumulado.html."""
    htmls = semanas_ja_coletadas(pasta_semanas)

    manifest_path = os.path.join(pasta_historico, "manifest.json")
    manifest_anterior = []
    if os.path.exists(manifest_path):
        try:
            manifest_anterior = json.loads(open(manifest_path, encoding="utf-8").read())
        except (json.JSONDecodeError, OSError):
            manifest_anterior = []
    entradas_manuais = [e for e in manifest_anterior if e.get("origem") == "manual"]
    # Visões SEMANAIS (tipo "semana") de um mês que acabou de ser arquivado
    # (entrou em MESES_ARQUIVADOS) congelam junto com ele: a última versão
    # gerada vira "manual" e nunca mais é refeita.
    _ids_arq = {h for ini_a, fim_a, _ in MESES_ARQUIVADOS for h in range(ini_a, fim_a + 1)}
    ja_manuais = {e["arquivo"] for e in entradas_manuais}
    for e in manifest_anterior:
        if (e.get("tipo") == "semana" and e.get("origem") != "manual" and e.get("semana_inicio") in _ids_arq
                and e["arquivo"] not in ja_manuais
                and os.path.exists(os.path.join(pasta_historico, e["arquivo"]))):
            entradas_manuais.append(dict(e, origem="manual", parcial=False))

    if not htmls:
        log.warning("Nenhuma semana em cache — mantendo só as entradas manuais do histórico (se houver).")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(entradas_manuais, f, ensure_ascii=False, indent=2)
        return

    if lista_cronograma is None:
        lista_cronograma = rodar_deteccao_completa(pasta_semanas)

    grupos = {}  # chave -> lista de html_ids do grupo
    ids_arquivados = {h for ini, fim, _ in MESES_ARQUIVADOS for h in range(ini, fim + 1)}
    for h in htmls:
        if h in ids_arquivados:
            continue  # mês arquivado (ver MESES_ARQUIVADOS) — já tem entrada "manual" fixa, não gera nada novo pra ele
        mes_oficial = _grupo_mes_oficial(h)
        if mes_oficial:
            grupos.setdefault(("mes-oficial", mes_oficial), []).append(h)
        elif GERAR_PAGINAS_SEMANAIS and h >= PRIMEIRA_SEMANA_DETALHE_SEMANAL:
            grupos[("semana", h)] = [h]  # cada semana é o grupo dela mesma, sozinha (modo antigo, desligado por padrão)
        else:
            # Fallback só pra semanas fora da tabela MESES_OFICIAIS e ainda
            # antes do corte semanal — não deveria acontecer no uso normal,
            # mas evita quebrar se alguém coletar um período não cadastrado.
            grupos.setdefault(("mes",) + sem.mes_da_semana_html(h), []).append(h)

    os.makedirs(pasta_historico, exist_ok=True)
    os.makedirs(pasta_saida_tmp, exist_ok=True)
    entradas_cache = []
    for chave in sorted(grupos, key=lambda k: min(grupos[k])):
        semanas_grupo = sorted(grupos[chave])
        ini, fim = semanas_grupo[0], semanas_grupo[-1]
        if chave[0] == "semana":
            nome_arquivo = f"semana_{ini}.xlsx"
            label = sem.rotulo_semana_html(ini)
        elif chave[0] == "mes-oficial":
            label = chave[1]  # nome exato de MESES_OFICIAIS, ex.: "Julho/2026"
            # Nome do arquivo = faixa OFICIAL do mês (estável, mesmo com o mês
            # incompleto) — ver comentário de MESES_OFICIAIS.
            ini_of, fim_of = _faixa_mes_oficial(label)
            nome_arquivo = f"semanas_{ini_of}-{fim_of}.xlsx"
        else:
            nome_arquivo = f"semanas_{ini}-{fim}.xlsx" if ini != fim else f"semana_{ini}.xlsx"
            label = nome_periodo(ini, fim)

        caminho_tmp = consolidar_semanas(semanas_grupo, pasta_saida_tmp, lista_cronograma)
        if not caminho_tmp:
            continue
        destino = os.path.join(pasta_historico, nome_arquivo)
        shutil.copy2(caminho_tmp, destino)

        if chave[0] == "mes-oficial":
            sem_ini, sem_fim = ini_of, fim_of
        else:
            sem_ini, sem_fim = ini, fim
        entradas_cache.append({
            "arquivo": nome_arquivo, "label": label, "origem": "cache",
            "semana_inicio": sem_ini, "semana_fim": sem_fim,
            "semana_ano_inicio": sem.html_para_semana(sem_ini, sem.ano_da_semana_html(sem_ini)),
            "semana_ano_fim": sem.html_para_semana(fim, sem.ano_da_semana_html(fim)),
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        })
        log.info("🗂️  Histórico atualizado: %s (%s — %s semana(s) coletada(s))", destino, label, len(semanas_grupo))

        # Visões semanais do mês vigente (mês aberto): uma planilha por semana
        # já coletada, com as MESMAS regras do ranking mensal aplicadas só
        # àquela semana. Meses arquivados não passam por aqui (ver acima).
        if chave[0] == "mes-oficial":
            for h in (x for x in semanas_grupo if x >= PRIMEIRA_SEMANA_VISAO_SEMANAL):
                nome_sem = f"semana_{h}.xlsx"
                # Agentes do mês que passaram esta semana sem lançar nada entram no ranking semanal (100 − descontos).
                caminho_sem = consolidar_semanas([h], pasta_saida_tmp, lista_cronograma,
                                                 agentes_extra=agentes_do_periodo(semanas_grupo))
                if not caminho_sem:
                    continue
                shutil.copy2(caminho_sem, os.path.join(pasta_historico, nome_sem))
                sexta = sem.data_fim_semana_html(h) - timedelta(days=1)
                n_sem = h - ini_of + 1
                entradas_cache.append({
                    "arquivo": nome_sem, "tipo": "semana", "mes": label,
                    "label": f"{label} · Semana {n_sem}", "numero_semana": n_sem, "origem": "cache",
                    "semana_inicio": h, "semana_fim": h,
                    "periodo": f"{sem.data_inicio_semana_html(h).strftime('%d/%m')} a {sem.data_fim_semana_html(h).strftime('%d/%m')}",
                    "parcial": _hoje_local() <= sexta,
                    "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
                })

    # Consolidados ADICIONAIS (MESES_ADICIONAIS) — somam várias semanas que
    # já têm (e continuam tendo) página individual própria no loop acima.
    # Não mexe em nada do que já foi gerado ali; só acrescenta mais um
    # arquivo por cima, cobrindo só as semanas do intervalo que já estão em
    # `htmls` (soma o que já tem, mesmo que o mês ainda não tenha fechado).
    for ini, fim, label in MESES_ADICIONAIS:
        semanas_disponiveis = sorted(h for h in htmls if ini <= h <= fim)
        if not semanas_disponiveis:
            continue  # nenhuma semana desse intervalo coletada ainda
        nome_arquivo = f"semanas_{ini}-{fim}.xlsx" if ini != fim else f"semana_{ini}.xlsx"
        caminho_tmp = consolidar_semanas(semanas_disponiveis, pasta_saida_tmp, lista_cronograma)
        if not caminho_tmp:
            continue
        destino = os.path.join(pasta_historico, nome_arquivo)
        shutil.copy2(caminho_tmp, destino)
        fim_disponivel = semanas_disponiveis[-1]
        entradas_cache.append({
            "arquivo": nome_arquivo, "label": label, "origem": "cache",
            "semana_inicio": ini, "semana_fim": fim,
            "semana_ano_inicio": sem.html_para_semana(ini, sem.ano_da_semana_html(ini)),
            "semana_ano_fim": sem.html_para_semana(fim_disponivel, sem.ano_da_semana_html(fim_disponivel)),
            "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        })
        log.info("🗂️  Histórico (consolidado adicional) atualizado: %s (%s — %s de %s semana(s) já coletada(s))",
                  destino, label, len(semanas_disponiveis), fim - ini + 1)

    # Entradas manuais primeiro (geralmente mais antigas, tipo Jan-Maio),
    # depois as automáticas em ordem cronológica — mas isso é só estético,
    # a ordem não afeta nada funcionalmente.
    manifest = entradas_manuais + entradas_cache
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    shutil.rmtree(pasta_saida_tmp, ignore_errors=True)
    if entradas_manuais:
        log.info("🔒 %s entrada(s) manual(is) do histórico preservada(s): %s",
                  len(entradas_manuais), [e.get("label") for e in entradas_manuais])

    # Limpeza: apaga planilhas .xlsx órfãs em data/historico/ — arquivos que
    # sobraram de um agrupamento antigo (ex.: nome mudou porque os limites
    # de mês foram corrigidos) e não são mais referenciados por NENHUMA
    # entrada do manifest (cache ou manual). Evita ficar com uma planilha
    # velha e desatualizada (sem o cronograma/férias, por exemplo) escondida
    # na pasta, sem ninguém saber que ela não é mais usada.
    #
    # EXCEÇÃO (preserva histórico): planilhas de página SEMANAL
    # (semana_<N>.xlsx) não são apagadas — vão para
    # data/historico/arquivo_semanal/, fora do menu e fora da geração de HTML.
    arquivos_referenciados = {e["arquivo"] for e in manifest}
    for f_nome in os.listdir(pasta_historico):
        if f_nome.endswith(".xlsx") and f_nome not in arquivos_referenciados:
            origem = os.path.join(pasta_historico, f_nome)
            if re.fullmatch(r"semana_\d+\.xlsx", f_nome):
                pasta_arq = os.path.join(pasta_historico, PASTA_ARQUIVO_SEMANAL)
                os.makedirs(pasta_arq, exist_ok=True)
                shutil.move(origem, os.path.join(pasta_arq, f_nome))
                log.info("📦 Página semanal arquivada (fora do menu): %s -> %s/", f_nome, PASTA_ARQUIVO_SEMANAL)
            else:
                os.remove(origem)
                log.info("🗑️  Removida planilha órfã do histórico (não referenciada no manifest): %s", f_nome)
