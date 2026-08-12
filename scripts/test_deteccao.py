# -*- coding: utf-8 -*-
"""
Testes da detecção automática de Férias/Atestado e Chuva
(scripts/coletar_evisita.py::detectar_ausencias_e_paralisacoes e afins).

Cobre os 6 cenários obrigatórios do pedido de ajuste:
  1) Férias individual (>5 dias úteis seguidos = confirmado sozinho)
  2) Férias não contamina chuva (agentes de férias são ignorados na conta)
  3) Chuva é por equipe (uma equipe parada não afeta a outra)
  4) Chuva por vários dias vira um único evento, que encerra quando a
     maioria volta
  5) Ponto Estratégico nunca gera férias automática
  6) Motivo manual (categoria_coletiva) não é sobrescrito nas próximas rodadas

Roda sem precisar do Selenium instalado: os módulos que coletar_evisita.py
importa só pra falar com o navegador (selenium) são substituídos por stubs
vazios antes do import — os testes aqui só exercitam as funções de
detecção/agregação, que não usam nada disso.

Uso: python3 scripts/test_deteccao.py
"""
import sys
import types
from datetime import date, datetime

import pandas as pd

# --- stubs pros módulos de navegador, só pra permitir o import -------------
for nome in ("selenium", "selenium.webdriver", "selenium.webdriver.common",
             "selenium.webdriver.common.by", "selenium.webdriver.chrome",
             "selenium.webdriver.chrome.options", "selenium.webdriver.support",
             "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions"):
    mod = types.ModuleType(nome)
    sys.modules.setdefault(nome, mod)
sys.modules["selenium"].webdriver = sys.modules["selenium.webdriver"]
sys.modules["selenium.webdriver"].common = sys.modules["selenium.webdriver.common"]
sys.modules["selenium.webdriver"].chrome = sys.modules["selenium.webdriver.chrome"]
sys.modules["selenium.webdriver"].support = sys.modules["selenium.webdriver.support"]
sys.modules["selenium.webdriver.common"].by = sys.modules["selenium.webdriver.common.by"]
sys.modules["selenium.webdriver.common.by"].By = type("By", (), {})
sys.modules["selenium.webdriver.chrome"].options = sys.modules["selenium.webdriver.chrome.options"]
sys.modules["selenium.webdriver.chrome.options"].Options = type("Options", (), {})
sys.modules["selenium.webdriver.support"].ui = sys.modules["selenium.webdriver.support.ui"]
sys.modules["selenium.webdriver.support.ui"].WebDriverWait = type("WebDriverWait", (), {})
sys.modules["selenium.webdriver.support"].expected_conditions = sys.modules[
    "selenium.webdriver.support.expected_conditions"]

import os
os.environ.setdefault("EVISITA_CPF", "00000000000")
os.environ.setdefault("EVISITA_SENHA", "teste")

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import coletar_evisita as ce  # noqa: E402

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "OK  " if condicao else "FALHOU"
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def d(s):
    return datetime.strptime(s, "%d/%m/%Y").date()


def montar_resultado(id_agente, nome, equipe, dias_com_visita):
    """Monta um item de `resultados` só com o necessário pras funções de
    detecção (id_agente/nome_agente/equipe/df, coluna 'dia')."""
    df = pd.DataFrame({"dia": sorted(dias_com_visita)}) if dias_com_visita else pd.DataFrame({"dia": []})
    return {"id_agente": id_agente, "nome_agente": nome, "equipe": equipe, "df": df}


def montar_df_total(resultados):
    linhas = []
    for r in resultados:
        for dia in r["df"]["dia"]:
            linhas.append({"id_agente": r["id_agente"], "dia": dia})
    return pd.DataFrame(linhas)


def dias_uteis_entre(ini, fim):
    return [dd for dd in ce._dias_uteis_no_intervalo(d(ini), d(fim))]


# ============================================================ Teste 1 ====
def teste_1_ferias_individual():
    # Agente trabalha até 03/08 (segunda), some por mais de 5 dias úteis.
    # 04/08 (ter) a 12/08 (qua) = 7 dias úteis sem lançamento -> férias.
    dias_trab = dias_uteis_entre("20/07/2026", "03/08/2026")
    res = montar_resultado(1, "Fulano", "Equipe 1", dias_trab)
    df_total = montar_df_total([res])
    # data_max precisa cobrir o período de ausência avaliado
    df_total = pd.concat([df_total, pd.DataFrame([{"id_agente": 1, "dia": d("13/08/2026")}])], ignore_index=True)
    res["df"] = pd.concat([res["df"], pd.DataFrame({"dia": [d("13/08/2026")]})], ignore_index=True)

    eventos = ce.detectar_ausencias_e_paralisacoes(df_total, [res])
    ferias = [e for e in eventos if e["tipo"] == "possiveis_ferias"]
    checar("Teste 1 — férias individual detectada", len(ferias) == 1, f"eventos={eventos}")
    if ferias:
        checar("Teste 1 — duração > 5 dias úteis", ferias[0]["duracao"] > 5, str(ferias[0]))


# ============================================================ Teste 2 ====
def teste_2_ferias_nao_contamina_chuva():
    # Equipe com 5 agentes. 2 de férias (>5 dias úteis sumidos). Os outros 3
    # ficam ativos e, num dia específico dentro da janela, TODOS os 3
    # deixam de lançar -> deve virar Chuva só com esses 3, sem Adriano/Wagner.
    dias_base = dias_uteis_entre("01/06/2026", "30/06/2026")
    dia_chuva = d("15/06/2026")
    assert dia_chuva in dias_base

    dias_ativos_normais = [dd for dd in dias_base if dd != dia_chuva]  # trabalham todo dia, exceto o dia de chuva

    adriano = montar_resultado(10, "Adriano", "Equipe X", [dd for dd in dias_base if dd < d("08/06/2026")])
    wagner = montar_resultado(11, "Wagner", "Equipe X", [dd for dd in dias_base if dd < d("08/06/2026")])
    juliana = montar_resultado(12, "Juliana", "Equipe X", dias_ativos_normais)
    katia = montar_resultado(13, "Katia", "Equipe X", dias_ativos_normais)
    selba = montar_resultado(14, "Selba", "Equipe X", dias_ativos_normais)

    resultados = [adriano, wagner, juliana, katia, selba]
    df_total = montar_df_total(resultados)

    eventos = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    ferias = [e for e in eventos if e["tipo"] == "possiveis_ferias"]
    chuva = [e for e in eventos if e["tipo"] == "paralisacao_coletiva"]

    nomes_ferias = sorted(e["nome_agente"] for e in ferias)
    checar("Teste 2 — Adriano e Wagner viram férias", nomes_ferias == ["Adriano", "Wagner"], str(nomes_ferias))

    chuva_no_dia = [e for e in chuva if e["inicio"] == "15/06/2026"]
    checar("Teste 2 — existe evento de chuva no dia 15/06", len(chuva_no_dia) == 1, str(chuva))
    if chuva_no_dia:
        checar("Teste 2 — chuva envolve só Juliana/Katia/Selba (sem Adriano/Wagner)",
               sorted(chuva_no_dia[0]["nomes_envolvidos"]) == ["Juliana", "Katia", "Selba"],
               str(chuva_no_dia[0]["nomes_envolvidos"]))


# ============================================================ Teste 3 ====
def teste_3_chuva_por_equipe():
    dias_base = dias_uteis_entre("01/06/2026", "12/06/2026")
    dia_teste = d("10/06/2026")

    # Equipe 1: todos os 2 agentes param no dia_teste
    e1_a = montar_resultado(20, "E1-A", "Equipe 1", [dd for dd in dias_base if dd != dia_teste])
    e1_b = montar_resultado(21, "E1-B", "Equipe 1", [dd for dd in dias_base if dd != dia_teste])
    # Equipe 2: maioria trabalhando no dia_teste (só 1 de 2 falta)
    e2_a = montar_resultado(22, "E2-A", "Equipe 2", [dd for dd in dias_base if dd != dia_teste])
    e2_b = montar_resultado(23, "E2-B", "Equipe 2", dias_base)  # trabalha todo dia, inclusive dia_teste

    resultados = [e1_a, e1_b, e2_a, e2_b]
    df_total = montar_df_total(resultados)
    eventos = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    chuva = [e for e in eventos if e["tipo"] == "paralisacao_coletiva"]

    chuva_e1 = [e for e in chuva if e["equipe"] == "Equipe 1" and e["inicio"] == "10/06/2026"]
    chuva_e2 = [e for e in chuva if e["equipe"] == "Equipe 2" and e["inicio"] == "10/06/2026"]
    checar("Teste 3 — Equipe 1 tem chuva no dia", len(chuva_e1) == 1, str(chuva))
    checar("Teste 3 — Equipe 2 NÃO tem chuva nesse dia (maioria trabalhando)", len(chuva_e2) == 0, str(chuva))


# ============================================================ Teste 4 ====
def teste_4_chuva_varios_dias_um_evento():
    dias_base = dias_uteis_entre("01/07/2026", "20/07/2026")
    # 04,05,06,07,08/08... usemos datas dentro do range: 06,07,08,09,10/07 (seg-sex)
    dias_chuva = [d("06/07/2026"), d("07/07/2026"), d("08/07/2026"), d("09/07/2026"), d("10/07/2026")]
    for dd in dias_chuva:
        assert dd in dias_base

    dias_com_visita = [dd for dd in dias_base if dd not in dias_chuva]

    a = montar_resultado(30, "A", "Equipe 1", dias_com_visita)
    b = montar_resultado(31, "B", "Equipe 1", dias_com_visita)
    resultados = [a, b]
    df_total = montar_df_total(resultados)
    eventos = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    chuva = [e for e in eventos if e["tipo"] == "paralisacao_coletiva"]

    checar("Teste 4 — um único evento de chuva (não 5 separados)", len(chuva) == 1, str(chuva))
    if chuva:
        checar("Teste 4 — período 06/07 a 10/07", chuva[0]["inicio"] == "06/07/2026" and chuva[0]["fim"] == "10/07/2026",
               str(chuva[0]))
        checar("Teste 4 — dia seguinte (13/07, maioria voltou) não entra no evento",
               chuva[0]["fim"] != "13/07/2026")


# ============================================================ Teste 5 ====
def teste_5_ponto_estrategico_nao_gera_ferias():
    dias_base = dias_uteis_entre("01/06/2026", "01/07/2026")
    # 10 dias úteis sem lançamento pro agente de Ponto Estratégico
    dias_com_visita = [dd for dd in dias_base if dd < d("15/06/2026")]
    pe = montar_resultado(40, "PE-Agente", "Ponto Estratégico", dias_com_visita)
    outro = montar_resultado(41, "Normal", "Equipe 1", dias_base)  # agente normal trabalhando full, controle
    resultados = [pe, outro]
    df_total = montar_df_total(resultados)
    eventos = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    ferias_pe = [e for e in eventos if e["tipo"] == "possiveis_ferias" and e.get("id_agente") == 40]
    checar("Teste 5 — Ponto Estratégico não gera férias automática", len(ferias_pe) == 0, str(eventos))


# ============================================================ Teste 6 ====
def teste_6_motivo_manual_preservado(tmp_path="/tmp/deteccoes_teste.json"):
    import os
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    dias_base = dias_uteis_entre("01/06/2026", "12/06/2026")
    dia_teste = d("10/06/2026")
    a = montar_resultado(50, "A", "Equipe 1", [dd for dd in dias_base if dd != dia_teste])
    b = montar_resultado(51, "B", "Equipe 1", [dd for dd in dias_base if dd != dia_teste])
    resultados = [a, b]
    df_total = montar_df_total(resultados)

    eventos1 = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    deteccoes1 = ce.atualizar_deteccoes_pendentes(eventos1, caminho=tmp_path)
    chuva1 = [e for e in deteccoes1 if e["tipo"] == "paralisacao_coletiva"]
    checar("Teste 6 — evento confirmado automaticamente como Chuva",
           len(chuva1) == 1 and chuva1[0]["categoria_coletiva"] == "Chuva", str(chuva1))

    # Supervisor corrige manualmente pra Capacitação
    import json
    with open(tmp_path, encoding="utf-8") as f:
        dados = json.load(f)
    for e in dados:
        if e["tipo"] == "paralisacao_coletiva":
            e["categoria_coletiva"] = "Capacitação"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    # Roda de novo com o MESMO padrão (mesmos dados) — não pode sobrescrever a correção
    eventos2 = ce.detectar_ausencias_e_paralisacoes(df_total, resultados)
    deteccoes2 = ce.atualizar_deteccoes_pendentes(eventos2, caminho=tmp_path)
    chuva2 = [e for e in deteccoes2 if e["tipo"] == "paralisacao_coletiva"]
    checar("Teste 6 — correção manual (Capacitação) preservada na próxima rodada",
           len(chuva2) == 1 and chuva2[0]["categoria_coletiva"] == "Capacitação", str(chuva2))

    os.remove(tmp_path)


if __name__ == "__main__":
    teste_1_ferias_individual()
    teste_2_ferias_nao_contamina_chuva()
    teste_3_chuva_por_equipe()
    teste_4_chuva_varios_dias_um_evento()
    teste_5_ponto_estrategico_nao_gera_ferias()
    teste_6_motivo_manual_preservado()

    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} teste(s) falharam: {FALHAS}")
        sys.exit(1)
    else:
        print("✅ Todos os testes passaram.")
