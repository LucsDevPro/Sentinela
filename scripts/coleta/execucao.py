# -*- coding: utf-8 -*-
"""Coleta blindada, resumo do GitHub e main().

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import time
from .parametros import (
    MAX_SEMANAS_FALHAS_SEGUIDAS,
    ORCAMENTO_COLETA_MIN,
    PASTA_SEMANAS,
    decidir_semanas_a_coletar,
    semanas_ja_coletadas,
)
from .auxiliares import parse_args
from .sessao import abrir_sessao, evisita_no_ar
from .cache_semanas import coletar_uma_semana
from .consolidacao import consolidar_semanas, rodar_deteccao_completa
from .historico import atualizar_historico_do_cache

log = logging.getLogger("evisita")


def coletar_semanas_blindado(semanas, id_ano, id_ciclo, abrir=None, coletar=None, agora=None):
    """Coleta várias semanas SEM que uma falha derrube as demais:
      - erro inesperado numa semana vira um item do resumo e a próxima segue;
      - sessão caída no meio → abre sessão nova e refaz a semana uma vez;
      - se MAX_SEMANAS_FALHAS_SEGUIDAS semanas falharem por inteiro, para
        (e-Visita provavelmente fora do ar) e as restantes ficam pra próxima execução;
      - respeita ORCAMENTO_COLETA_MIN: não começa semana nova depois disso.
    O cache de cada semana é salvo por coletar_uma_semana (nunca piora o anterior)."""
    abrir = abrir or abrir_sessao
    coletar = coletar or coletar_uma_semana
    agora = agora or time.monotonic
    t0 = agora()
    resumo, sessao, falhas_seguidas = [], None, 0

    def pulada(h, motivo):
        return {"html_id": h, "sessao_caiu": False, "agentes_ausentes": [("-", "-", motivo)],
                "agentes_incompletos": [], "total_agentes": 0, "pulada": True}

    for i, h in enumerate(semanas):
        restantes = semanas[i:]
        if (agora() - t0) / 60 > ORCAMENTO_COLETA_MIN:
            for x in restantes:
                resumo.append(pulada(x, f"orçamento de {ORCAMENTO_COLETA_MIN} min esgotado — fica para a próxima execução"))
            break
        if falhas_seguidas >= MAX_SEMANAS_FALHAS_SEGUIDAS:
            for x in restantes:
                resumo.append(pulada(x, f"{falhas_seguidas} semanas seguidas falharam (e-Visita instável) — fica para a próxima execução"))
            break
        try:
            if sessao is None:
                sessao = abrir()
            r = coletar(sessao, h, id_ano, id_ciclo)
            if r.get("sessao_caiu"):
                log.warning("🔁 Sessão caiu na semana %s — abrindo sessão nova e refazendo a semana.", h)
                sessao = abrir()
                r = coletar(sessao, h, id_ano, id_ciclo)
        except Exception as e:
            log.error("❌ Semana %s abortada: %s — seguindo para a próxima.", h, e)
            sessao = None
            r = {"html_id": h, "sessao_caiu": False, "abortada": True, "agentes_incompletos": [],
                 "agentes_ausentes": [("-", "-", f"semana abortada: {e}")], "total_agentes": 0}
        falhou_tudo = r.get("abortada") or (r["total_agentes"] > 0 and len(r["agentes_ausentes"]) >= r["total_agentes"])
        falhas_seguidas = falhas_seguidas + 1 if falhou_tudo else 0
        resumo.append(r)
    return resumo


def _resumo_github(semanas, resumo_integridade, extras=()):
    """Escreve o resultado da coleta no resumo da execução do GitHub Actions
    ($GITHUB_STEP_SUMMARY) e emite anotações ::error::/::warning:: — assim
    quem abre a aba Actions vê de cara o que foi coletado e o que falhou,
    sem precisar ler 1h de log. Fora do GitHub (sem a variável) não faz nada
    além de imprimir as anotações."""
    linhas = ["## 📥 Resumo da coleta no e-Visita", ""]
    linhas += list(extras)
    if not resumo_integridade:
        linhas.append("Nada novo para coletar nesta execução.")
    else:
        linhas.append(f"Semanas processadas: **{', '.join(str(r['html_id']) for r in resumo_integridade)}**")
        linhas.append("")
        problemas = 0
        for r in resumo_integridade:
            for id_ag, eq, motivo in r["agentes_ausentes"]:
                problemas += 1
                if id_ag == "-":   # problema da SEMANA inteira (abortada/pulada), não de um agente
                    icone = "⏭️" if r.get("pulada") else "❌"
                    linhas.append(f"- {icone} Semana {r['html_id']}: {motivo}")
                    print(f"::warning title=Semana {r['html_id']} não coletada::{motivo}")
                    continue
                linhas.append(f"- ❌ Semana {r['html_id']} — agente {id_ag} ({eq}): {motivo}")
                print(f"::error title=Coleta incompleta (semana {r['html_id']})::agente {id_ag} ({eq}): {motivo}")
            for nome, eq, paginas in r["agentes_incompletos"]:
                problemas += 1
                linhas.append(f"- ⚠️ Semana {r['html_id']} — {nome} ({eq}): páginas {paginas} não coletadas")
                print(f"::warning title=Páginas faltando (semana {r['html_id']})::{nome} ({eq}): páginas {paginas}")
        if not problemas:
            linhas.append("✅ Coleta íntegra em todas as semanas processadas.")
        else:
            linhas += ["", "Os dados que já estavam salvos desses agentes foram **mantidos**; as semanas "
                           "afetadas serão reprocessadas na próxima execução."]
    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n\n")


def main():
    args = parse_args()

    if args.semana is not None:
        semanas_a_coletar = [args.semana]
        log.info("▶️  Modo manual: recoletando só a semana %s (HTML ID).", args.semana)
    else:
        semanas_a_coletar = decidir_semanas_a_coletar(pasta_semanas=args.pasta_semanas)

    if not semanas_a_coletar:
        log.info("Nada novo para coletar — semana atual já está em cache.")
    else:
        log.info("📋 Semanas a coletar nesta execução: %s", semanas_a_coletar)

        no_ar, detalhe = evisita_no_ar()
        if not no_ar:
            # e-Visita fora do ar: NÃO tenta coletar. Segue com o cache que existe
            # (o site é publicado normalmente) e as semanas ficam pra próxima execução.
            log.error("🌐 e-Visita fora do ar (%s) — coleta pulada; publicando com os dados que já existem.", detalhe)
            print(f"::warning title=e-Visita fora do ar::{detalhe} — coleta pulada, tentando de novo na próxima execução")
            _resumo_github(semanas_a_coletar, [], extras=[
                f"⚠️ **e-Visita fora do ar** ({detalhe}). Nada foi coletado; o site foi atualizado com os dados já salvos. "
                f"As semanas {', '.join(str(x) for x in semanas_a_coletar)} serão tentadas de novo na próxima execução.", ""])
            semanas_a_coletar = []
    if semanas_a_coletar:
        resumo_integridade = coletar_semanas_blindado(semanas_a_coletar, args.id_ano, args.id_ciclo)

        ausentes_total = sum(len(r["agentes_ausentes"]) for r in resumo_integridade)
        incompletos_total = sum(len(r["agentes_incompletos"]) for r in resumo_integridade)
        if ausentes_total or incompletos_total:
            log.error("=" * 60)
            log.error("⚠️  RESUMO DE INTEGRIDADE DA COLETA — LEIA COM ATENÇÃO")
            for r in resumo_integridade:
                for id_ag, eq, motivo in r["agentes_ausentes"]:
                    log.error("  - [Semana %s] Agente %s (%s): %s", r["html_id"], id_ag, eq, motivo)
                for nome, eq, paginas in r["agentes_incompletos"]:
                    log.error("  - [Semana %s] %s (%s): páginas %s não coletadas",
                               r["html_id"], nome, eq, paginas)
            log.error("Recomendação: rode `python scripts/coletar_evisita.py --semana <HTML_ID>` "
                       "pra recoletar só a(s) semana(s) afetada(s).")
            log.error("=" * 60)
        else:
            log.info("✅ Coleta íntegra em todas as semanas processadas.")
        _resumo_github(semanas_a_coletar, resumo_integridade)

    # Consolidação: sempre reconstrói o Analise_Consolidada.xlsx a partir de
    # TODO o cache disponível (não só das semanas coletadas agora), e
    # reconstrói o histórico por mês em cima do mesmo cache.
    todas_semanas = semanas_ja_coletadas(args.pasta_semanas if args.semana is None else PASTA_SEMANAS)
    if not todas_semanas:
        log.error("Nenhuma semana em cache — não há o que consolidar.")
        return

    # Detecção de possíveis férias/paralisação coletiva roda UMA VEZ em cima
    # de TODO o histórico (não semana a semana) — evita cortar errado um
    # período que atravessa a virada do mês. O resultado (cronograma
    # "efetivo": manual + confirmadas) é reaproveitado tanto no Acumulado
    # quanto em cada página do histórico, pra todo mundo ver a mesma coisa.
    lista_cronograma = rodar_deteccao_completa(args.pasta_semanas)

    caminho = consolidar_semanas(todas_semanas, args.saida, lista_cronograma)
    if caminho:
        log.info("🎉 CONCLUÍDO! Analise_Consolidada.xlsx gerado a partir de %s semana(s) em cache.",
                   len(todas_semanas))
    atualizar_historico_do_cache(pasta_semanas=args.pasta_semanas, lista_cronograma=lista_cronograma)
