# -*- coding: utf-8 -*-
"""Preparação das abas simples (resumo, área, duplicadas, suspeitas, almoço...).

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import pandas as pd
from .parametros import (
    HORA_ALMOCO_FIM_MIN,
    HORA_ALMOCO_INICIO_MIN,
    HORA_EXPEDIENTE_MANHA_INICIO,
    HORA_EXPEDIENTE_TARDE_FIM,
)
from .auxiliares import NOMES_DIA_SEMANA, _fmt_hora_min
from .calculos import _classificar, resumo_por_area


def _formatar_campos_resumo(resumo_dict):
    """
    Formata os campos calculados de um dicionário 'resumo' (vindo de
    resumo_agente): classificação por % rápidas, horários HH:MM, custo em R$.
    Reaproveitado tanto pelo Resumo Geral quanto pela aba Ponto Estratégico
    (que aplica o mesmo cálculo por semana).
    """
    r = dict(resumo_dict)  # cópia — evita mutar o dict original em memória
    classif, fill = _classificar(r.get("pct_rapidas", 0))

    for key in ["inicio_manhã", "fim_manhã", "inicio_tarde", "fim_tarde"]:
        if r.get(key):
            try:
                r[key] = r[key].strftime("%H:%M")
            except AttributeError:
                r[key] = str(r[key])

    if r.get("custo_hora_util") is not None:
        r["custo_hora_util"] = f"R$ {r['custo_hora_util']:.2f}".replace(".", ",")
    else:
        r["custo_hora_util"] = "—"

    return r, classif, fill


def _preparar_resumo(res):
    r, classif, fill = _formatar_campos_resumo(res["resumo"])
    return {
        **r,
        "nome_agente": res["nome_agente"],
        "equipe": res["equipe"],
        "classificacao": classif,
        "_fill": fill,
    }


def _preparar_area(df_ag, res):
    df_area = resumo_por_area(df_ag, res.get("fechados_por_area"), res.get("recusados_por_area"))
    if df_area.empty:
        return []
    registros = []
    for _, row in df_area.iterrows():
        _, fill = _classificar(row["pct_rapidas"])
        registros.append({
            **row.to_dict(),
            "nome_agente": res["nome_agente"],
            "equipe": res["equipe"],
            "_fill": fill,
        })
    return registros


def _preparar_duplicadas(df_total):
    """
    Monta a lista de visitas duplicadas com endereço completo, para facilitar
    localizar e excluir os registros repetidos diretamente no sistema.
    """
    if df_total.empty:
        return []

    dup = df_total[df_total["duplicada"]].copy()
    if dup.empty:
        return []

    def _motivo(row):
        motivos = []
        if row["dup_por_id"]:
            motivos.append("ID de visita repetido")
        if row["dup_por_chegada_imovel"]:
            motivos.append("Mesmo horário de chegada + imóvel")
        return " / ".join(motivos) if motivos else "Duplicada"

    dup["motivo_duplicacao"] = dup.apply(_motivo, axis=1)

    # Agrupa visualmente as duplicatas: mesmo agente + imóvel + chegada ficam juntas
    dup = dup.sort_values(["nome_agente", "area", "imovel", "dt_chegada"])

    registros = []
    for _, row in dup.iterrows():
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "motivo_duplicacao": row["motivo_duplicacao"],
            "_fill": "FFD9B3",  # laranja claro para destacar
        })
    return registros


def _preparar_suspeitas(df_total):
    """
    Monta a lista de visitas marcadas como 'sequência suspeita' (chegadas no
    mesmo minuto que a visita anterior do mesmo agente), com endereço completo
    e o número da cadeia a que pertencem, para facilitar a checagem manual.
    """
    if df_total.empty:
        return []

    susp = df_total[df_total["sequencia_suspeita"]].copy()
    if susp.empty:
        return []

    # Ordena por agente e depois pela cadeia/horário, para que cada grupo
    # suspeito apareça junto, na ordem em que ocorreu.
    susp = susp.sort_values(["nome_agente", "dt_chegada"])

    registros = []
    for _, row in susp.iterrows():
        # Só exibe a diferença quando ELA é a responsável pelo alerta desta
        # linha (par com a visita ANTERIOR). Se o alerta veio do par com a
        # visita seguinte, o diff em relação à anterior é irrelevante/enganoso.
        diff_seg = row["diff_chegada_anterior_seg"] if row["par_suspeito_anterior"] else None
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "grupo_sequencia_suspeita": row["grupo_sequencia_suspeita"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "diff_chegada_anterior_seg": "" if diff_seg is None or pd.isna(diff_seg) else int(diff_seg),
            "_fill": "FFE0B3",  # amarelo/laranja claro para destacar
        })
    return registros


def _preparar_negativas(df_total):
    """
    Monta a lista de visitas com duração NEGATIVA (data de saída registrada
    antes da chegada) — provável bug de gravação no sistema. Traz endereço
    completo para facilitar a investigação junto ao suporte do e-Visita.
    """
    if df_total.empty:
        return []

    neg = df_total[df_total["alerta_neg"]].copy()
    if neg.empty:
        return []

    neg = neg.sort_values(["nome_agente", "dt_chegada"])

    registros = []
    for _, row in neg.iterrows():
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "duracao_min": row["duracao_min"],
            "observacao": "Data/hora de saída anterior à chegada — provável erro de gravação no sistema",
            "_fill": "D9D9D9",  # cinza para destacar como problema técnico, não de conduta
        })
    return registros


def _preparar_acima_teto_media(df_total):
    """
    Monta a lista de visitas com duração acima de TETO_DURACAO_MEDIA_MIN
    (20min por padrão) — pra auditoria de possível manipulação de horário
    de saída (lançamento pelo computador). Essas visitas entram no cálculo
    de média/mediana com duração limitada ao teto, mas aqui aparecem com a
    duração REAL registrada, pra facilitar a checagem.
    """
    if df_total.empty:
        return []

    acima = df_total[df_total["acima_teto_media"]].copy()
    if acima.empty:
        return []

    acima = acima.sort_values("duracao_min", ascending=False)

    registros = []
    for _, row in acima.iterrows():
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "duracao_min": row["duracao_min"],
        })
    return registros


def _motivo_fora_expediente(row):
    if row["fim_de_semana"]:
        return f"Fim de semana ({NOMES_DIA_SEMANA.get(row['dia_semana_num'], '')})"
    minutos = row["minutos_chegada"]
    hora = row["hora_chegada"]
    if HORA_ALMOCO_INICIO_MIN <= minutos < HORA_ALMOCO_FIM_MIN:
        return f"Horário de almoço ({_fmt_hora_min(HORA_ALMOCO_INICIO_MIN)}-{_fmt_hora_min(HORA_ALMOCO_FIM_MIN)})"
    if hora < HORA_EXPEDIENTE_MANHA_INICIO:
        return f"Antes do expediente (antes das {HORA_EXPEDIENTE_MANHA_INICIO}h)"
    if hora >= HORA_EXPEDIENTE_TARDE_FIM:
        return f"Depois do expediente (após as {HORA_EXPEDIENTE_TARDE_FIM}h)"
    return "Fora do expediente (próximo ao horário de almoço, dentro da tolerância de 15min)"


def _preparar_fora_expediente(df_total):
    """
    Monta a lista de visitas registradas fora do horário oficial de serviço
    (7h-11h e 13h-17h, dias úteis) — inclui fins de semana, antes/depois do
    expediente e horário de almoço (com motivo especificado por linha).
    """
    if df_total.empty:
        return []

    fora = df_total[df_total["fora_expediente"]].copy()
    if fora.empty:
        return []

    fora["motivo"] = fora.apply(_motivo_fora_expediente, axis=1)
    fora["dia_semana"] = fora["dia_semana_num"].map(NOMES_DIA_SEMANA)
    fora = fora.sort_values(["nome_agente", "dt_chegada"])

    registros = []
    for _, row in fora.iterrows():
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "dia_semana": row["dia_semana"],
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "motivo": row["motivo"],
            "_fill": "FFCCCC" if row["fim_de_semana"] else "FFE8CC",
        })
    return registros


def _preparar_almoco(df_total):
    """Lista apenas as visitas registradas no horário de almoço (11h15-12h45, com tolerância de 15min)."""
    if df_total.empty:
        return []

    alm = df_total[df_total["visita_horario_almoco"]].copy()
    if alm.empty:
        return []

    alm = alm.sort_values(["nome_agente", "dt_chegada"])

    registros = []
    for _, row in alm.iterrows():
        registros.append({
            "nome_agente": row["nome_agente"],
            "equipe": row["equipe"],
            "id_visita": row["id_visita"] if pd.notna(row["id_visita"]) else "",
            "area": row["area"],
            "quarteirao": row["quarteirao"],
            "logradouro": row["logradouro"],
            "imovel": row["imovel"],
            "data_chegada": row["data_chegada"],
            "data_saida": row["data_saida"],
            "_fill": "FFF2CC",
        })
    return registros
