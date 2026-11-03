# -*- coding: utf-8 -*-
"""Orquestração: processar() e processar_ponto_estrategico().

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import pandas as pd
from .parametros import (
    ID_ATIVIDADE_PONTO_ESTRATEGICO,
    ID_PENDENCIA_ABERTOS,
    ID_PENDENCIA_FECHADOS,
    ID_PENDENCIA_RECUSADOS,
    TENTATIVAS_POR_PAGINA,
)
from .pontos import COLETAR_FECHADOS_RECUSADOS
from .sessao import SessaoExpiradaError, clonar_session, coletar_visitas_agente
from .calculos import calcular_tempos, resumo_agente

log = logging.getLogger("evisita")


# ============================================================
# ORQUESTRAÇÃO
# ============================================================

def processar(equipe, id_ag, session_base, cfg):
    session = clonar_session(session_base)
    try:
        nome, visitas, paginas_falhas = coletar_visitas_agente(session, id_ag, cfg,
                                                                  id_pendencia=ID_PENDENCIA_ABERTOS)
    except SessaoExpiradaError as e:
        log.error("Sessão expirou processando agente %s: %s", id_ag, e)
        return {"ok": False, "id_agente": id_ag, "nome_agente": f"Agente_{id_ag}",
                "equipe": equipe, "erro": "sessao_expirada"}
    except Exception as e:
        log.error("❌ Falha ao coletar página 1 do agente %s mesmo após %s tentativas: %s — "
                    "AGENTE FICARÁ AUSENTE DO RELATÓRIO", id_ag, TENTATIVAS_POR_PAGINA, e)
        return {"ok": False, "id_agente": id_ag, "nome_agente": f"Agente_{id_ag}",
                "equipe": equipe, "erro": "falha_pagina1"}

    if not visitas:
        return {"ok": False, "id_agente": id_ag, "nome_agente": nome, "equipe": equipe}

    # Coleta adicional de fechados/recusados, só para contagem de pendência
    # (não entra na análise de tempo/qualidade, que é sempre sobre os abertos).
    visitas_fechados, visitas_recusados = [], []
    paginas_falhas_pendencia = []
    if COLETAR_FECHADOS_RECUSADOS:
        try:
            _, visitas_fechados, pf_fechados = coletar_visitas_agente(
                session, id_ag, cfg, id_pendencia=ID_PENDENCIA_FECHADOS, obter_nome=False)
            paginas_falhas_pendencia.extend(pf_fechados)
        except SessaoExpiradaError:
            raise
        except Exception as e:
            log.warning("Não foi possível coletar FECHADOS do agente %s: %s", id_ag, e)

        try:
            _, visitas_recusados, pf_recusados = coletar_visitas_agente(
                session, id_ag, cfg, id_pendencia=ID_PENDENCIA_RECUSADOS, obter_nome=False)
            paginas_falhas_pendencia.extend(pf_recusados)
        except SessaoExpiradaError:
            raise
        except Exception as e:
            log.warning("Não foi possível coletar RECUSADOS do agente %s: %s", id_ag, e)

    df = calcular_tempos(visitas, nome, id_ag, equipe, semana_html_id=cfg["semana_inicio"])
    resumo = resumo_agente(df)

    total_abertos = resumo["total_visitas"]
    total_fechados = len(visitas_fechados)
    total_recusados = len(visitas_recusados)
    total_geral_pendencia = total_abertos + total_fechados + total_recusados
    pct_pendencia = round(((total_fechados + total_recusados) / total_geral_pendencia * 100), 2) if total_geral_pendencia > 0 else 0

    resumo["imoveis_fechados"] = total_fechados
    resumo["imoveis_recusados"] = total_recusados
    resumo["total_geral_pendencia"] = total_geral_pendencia
    resumo["pct_pendencia"] = pct_pendencia

    # Contagem por área (só contagem — não precisa de análise de tempo/qualidade)
    fechados_por_area = {}
    for v in visitas_fechados:
        fechados_por_area[v["area"]] = fechados_por_area.get(v["area"], 0) + 1
    recusados_por_area = {}
    for v in visitas_recusados:
        recusados_por_area[v["area"]] = recusados_por_area.get(v["area"], 0) + 1

    visitas_recusados_raw = [{**v, "nome_agente": nome, "equipe": equipe} for v in visitas_recusados]

    return {
        "ok": True,
        "id_agente": id_ag,
        "nome_agente": nome,
        "equipe": equipe,
        "resumo": resumo,
        "df": df,
        "paginas_falhas": paginas_falhas + paginas_falhas_pendencia,
        "fechados_por_area": fechados_por_area,
        "recusados_por_area": recusados_por_area,
        "visitas_recusados_raw": visitas_recusados_raw,
    }


def processar_ponto_estrategico(id_ag, session_base, cfg_pe):
    """
    Coleta as visitas de Ponto Estratégico de um agente (URL/id_atividade
    próprios) e quebra o resultado POR SEMANA, calculando o mesmo conjunto
    completo de métricas do Resumo Geral (reaproveita resumo_agente) para
    cada semana separadamente.
    """
    session = clonar_session(session_base)
    try:
        nome, visitas, paginas_falhas = coletar_visitas_agente(
            session, id_ag, cfg_pe, id_pendencia=ID_PENDENCIA_ABERTOS,
            id_atividade=ID_ATIVIDADE_PONTO_ESTRATEGICO, tem_foto="")
    except SessaoExpiradaError as e:
        log.error("Sessão expirou processando Ponto Estratégico do agente %s: %s", id_ag, e)
        return {"ok": False, "id_agente": id_ag, "erro": "sessao_expirada"}
    except Exception as e:
        log.error("❌ Falha ao coletar Ponto Estratégico do agente %s: %s — "
                    "AGENTE FICARÁ AUSENTE DESSA ABA", id_ag, e)
        return {"ok": False, "id_agente": id_ag, "erro": "falha_pagina1"}

    if not visitas:
        return {"ok": False, "id_agente": id_ag, "nome_agente": nome}

    df = calcular_tempos(visitas, nome, id_ag, "Ponto Estratégico", semana_html_id=cfg_pe["semana_inicio"])

    semanas = []
    for semana_num, sub in df.groupby("semana", observed=True):
        if sub.empty:
            continue
        resumo_semana = resumo_agente(sub)
        chegada_min = sub["dt_chegada"].min()
        chegada_max = sub["dt_chegada"].max()
        periodo = (f"{chegada_min.strftime('%d/%m')} a {chegada_max.strftime('%d/%m')}"
                   if pd.notna(chegada_min) and pd.notna(chegada_max) else "")
        semanas.append({
            "nome_agente": nome,
            "equipe": "Ponto Estratégico",
            "semana": int(semana_num),
            "periodo_semana": periodo,
            "resumo": resumo_semana,
        })

    return {
        "ok": True,
        "id_agente": id_ag,
        "nome_agente": nome,
        "df": df,
        "paginas_falhas": paginas_falhas,
        "semanas": semanas,
    }
