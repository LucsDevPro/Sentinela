# -*- coding: utf-8 -*-
"""Testes de: férias até 30 dias (excesso vira falta), agentes sem abono, ajuste
manual de férias, ausências (primeira visita histórica, feriado, equipe sob
demanda), desconto de dia inteiro sem lançamento e formulário de férias."""
import sys
import types
import json
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
# Estes testes cobrem o MODO AUTOMÁTICO (opcional) da detecção; o padrão novo
# (detecção entra como pendente) é coberto por test_turno_evento.py.
ce.CONFIRMAR_FERIAS_AUTOMATICAMENTE = True
ce.CONFIRMAR_CHUVA_AUTOMATICAMENTE = True
import datetime as _dt  # noqa: E402
ce.HOJE_OVERRIDE = _dt.date(2027, 1, 1)  # hoje fixo nos testes

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



import tempfile
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import lancar_ausencia as lau  # noqa: E402


def det_tmp():
    return os.path.join(tempfile.mkdtemp(), "det.json")


def evento(id_ag, ini, fim, status=None, **extra):
    e = {"tipo": "possiveis_ferias", "id_agente": id_ag, "nome_agente": f"Agente {id_ag}", "equipe": "Equipe 1",
         "inicio": ini, "fim": fim, "duracao": 1}
    if status:
        e.update({"status": status, "motivo": "Férias", "detectado_em": "01/10/2026 08:00"})
    e.update(extra)
    return e


# ---------------------------------------------------------------- 30 dias ---
def teste_excesso_30_dias_vira_falta():
    dias_trab = dias_uteis_entre("01/08/2026", "27/08/2026")
    a = montar_resultado(201, "Longo", "Equipe 1", dias_trab)
    volta = d("12/10/2026")  # ausente 28/08 a 11/10 (~45 dias corridos)
    a["df"] = pd.concat([a["df"], pd.DataFrame({"dia": [volta]})], ignore_index=True)
    df = montar_df_total([a])
    eventos = ce.detectar_ausencias_e_paralisacoes(df, [a])
    caminho = det_tmp()
    final = ce.atualizar_deteccoes_pendentes(eventos, caminho=caminho)
    fer = sorted([e for e in final if e["id_agente"] == 201], key=lambda e: d(e["inicio"]))
    checar("Excesso — 45 dias vira 2 ocorrências", len(fer) == 2, str(fer))
    if len(fer) == 2:
        checar("Excesso — 1º pedaço (até 30 dias) é férias confirmada", fer[0]["status"] == "confirmada")
        checar("Excesso — o que passa de 30 dias vira FALTA", fer[1]["status"] == "falta", str(fer[1]))
    # idempotência: rodar de novo com os mesmos eventos não muda nada
    final2 = ce.atualizar_deteccoes_pendentes(
        ce.detectar_ausencias_e_paralisacoes(df, [a]), caminho=caminho)
    chave = lambda L: sorted((e["inicio"], e["fim"], e["status"]) for e in L if e["id_agente"] == 201)
    checar("Excesso — segunda rodada idêntica (idempotente)", chave(final) == chave(final2),
           f"{chave(final)} vs {chave(final2)}")
    # falta decidida continua falta quando o período cresce
    dados = json.load(open(caminho, encoding="utf-8"))
    for e in dados:
        if e["id_agente"] == 201 and e["status"] == "falta":
            e["fim"] = "09/10/2026"
    json.dump(dados, open(caminho, "w", encoding="utf-8"))
    volta2 = d("19/10/2026")
    a["df"] = pd.concat([a["df"][a["df"]["dia"] != volta], pd.DataFrame({"dia": [volta2]})], ignore_index=True)
    df2 = montar_df_total([a])
    final3 = ce.atualizar_deteccoes_pendentes(ce.detectar_ausencias_e_paralisacoes(df2, [a]), caminho=caminho)
    fer3 = [e for e in final3 if e["id_agente"] == 201 and e["status"] == "falta"]
    checar("Excesso — falta cresce junto, sem virar férias nem duplicar", len(fer3) == 1 and fer3[0]["fim"] >= "09/10/2026", str(fer3))


def teste_agente_sem_abono():
    original = ce._carregar_agentes_sem_abono
    ce._carregar_agentes_sem_abono = lambda *a, **k: {202: d("01/10/2026"), 203: None}
    try:
        caminho = det_tmp()
        ev = [evento(202, "05/10/2026", "15/10/2026"), evento(202, "10/08/2026", "20/08/2026"),
              evento(204, "05/10/2026", "15/10/2026")]
        final = ce.atualizar_deteccoes_pendentes(ev, caminho=caminho)
        st = {(e["id_agente"], e["inicio"]): e["status"] for e in final}
        checar("Sem abono — depois da data vira falta", st[(202, "05/10/2026")] == "falta", str(st))
        checar("Sem abono — antes da data segue a regra normal", st[(202, "10/08/2026")] == "confirmada", str(st))
        checar("Sem abono — outro agente não é afetado", st[(204, "05/10/2026")] == "confirmada", str(st))
    finally:
        ce._carregar_agentes_sem_abono = original


def teste_ajuste_manual_e_palavra_final():
    caminho = det_tmp()
    manual = evento(205, "01/10/2026", "20/10/2026", "confirmada", ajustado_manual=True)
    falta = evento(205, "21/10/2026", "27/10/2026", "falta", ajustado_manual=True)
    json.dump([manual, falta], open(caminho, "w", encoding="utf-8"))
    # a detecção acha 01/10 a 27/10 (27 dias) de uma vez
    final = ce.atualizar_deteccoes_pendentes([evento(205, "01/10/2026", "27/10/2026")], caminho=caminho)
    fer = sorted([(e["inicio"], e["fim"], e["status"]) for e in final if e["id_agente"] == 205])
    checar("Manual — período ajustado à mão não é esticado nem fundido com a falta vizinha",
           fer == [("01/10/2026", "20/10/2026", "confirmada"), ("21/10/2026", "27/10/2026", "falta")], str(fer))


# ---------------------------------------------------------- ausências -----
def teste_ausencias_primeira_visita_e_feriado():
    dias_a = [d("14/10/2026"), d("15/10/2026"), d("16/10/2026")]
    todos = dias_uteis_entre("05/10/2026", "16/10/2026")
    ra = montar_resultado(301, "Voltou tarde", "Equipe 1", dias_a)
    rb = montar_resultado(302, "Sempre aqui", "Equipe 1", todos)
    rc = montar_resultado(303, "Bloqueio", "Equipe Bloqueio", dias_a)
    res = [ra, rb, rc]
    from datetime import time as _t
    linhas = [{"id_agente": r["id_agente"], "dia": dia, "hora_chegada": h}
              for r in res for dia in r["df"]["dia"] for h in (9.0, 14.0)]
    df = pd.DataFrame(linhas)
    for r in res:
        r["df"] = df[df["id_agente"] == r["id_agente"]].reset_index(drop=True)
    hist_antigo = {301: d("01/06/2026"), 302: d("01/06/2026"), 303: d("01/06/2026")}
    regs = ce._preparar_ausencias(df, res, [], primeira_visita=hist_antigo)
    por = lambda i: sorted({r["dia_fmt"] for r in regs if r["id_agente"] == i})
    esperado = ["05/10/2026", "06/10/2026", "07/10/2026", "08/10/2026", "09/10/2026", "13/10/2026"]
    checar("Ausências — quem já trabalhava antes do período perde os dias do começo", por(301) == esperado, str(por(301)))
    checar("Ausências — feriado nacional (12/10) NÃO conta como ausência", "12/10/2026" not in por(301))
    checar("Ausências — equipe sob demanda (Bloqueio) mantém a regra antiga", por(303) == [], str(por(303)))
    regs2 = ce._preparar_ausencias(df, res, [], primeira_visita={301: d("14/10/2026"), 302: d("01/06/2026"), 303: d("01/06/2026")})
    checar("Ausências — quem de fato começou em 14/10 não ganha falta antes disso",
           sorted({r["dia_fmt"] for r in regs2 if r["id_agente"] == 301}) == [], "")


# ------------------------------------------------------------ pontuação ---
def teste_pontuacao_dia_inteiro():
    cwd = os.getcwd()
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    try:
        if not os.path.exists("data/semanas/326.xlsx"):
            print("[PULOU] Pontuação — sem data/semanas/326.xlsx")
            return
        _, resultados, _ = ce._montar_df_total_e_resultados([326])
        res = resultados[0]
        p0, _, _, d0 = ce.calcular_pontuacao(res, 4, 10, normalizar_periodo=False, dias_inteiros_sem_lancamento=0)
        p2, _, _, d2 = ce.calcular_pontuacao(res, 4, 10, normalizar_periodo=False, dias_inteiros_sem_lancamento=2)
        pn, _, _, dn = ce.calcular_pontuacao(res, 4, 10, normalizar_periodo=True, dias_inteiros_sem_lancamento=2)
        checar("Pontuação — cada dia inteiro sem lançamento desconta a mais (1,0)",
               abs((p0 - p2) - 2.0) < 1e-6 or (p0 == 0.0 and p2 == 0.0), f"{p0} {p2}")
        checar("Pontuação — mostra a linha 'Dia inteiro sem lançamento' no detalhe",
               any("Dia inteiro" in x["motivo"] for x in d2))
        checar("Pontuação — método antigo (meses/Acumulado antigos) não muda",
               not any("Dia inteiro" in x["motivo"] for x in dn))
    finally:
        os.chdir(cwd)


# ----------------------------------------------------------- formulário ---
NOMES = {"85": {"nome": "Adriano Teste", "equipe": "Equipe 1"}}


def corpo_ferias(acao, ini, fim, ag="Adriano Teste — Equipe 1 (ID 85)"):
    return (f"### Agente\n\n{ag}\n\n### O que fazer\n\n{acao}\n\n"
            f"### Primeiro dia\n\n{ini}\n\n### Último dia\n\n{fim}\n")


def teste_formulario_ferias():
    d0 = tempfile.mkdtemp()
    nomes, cron, det = (os.path.join(d0, n) for n in ("n.json", "c.json", "d.json"))
    json.dump(NOMES, open(nomes, "w")); json.dump([], open(cron, "w"))
    json.dump([evento(85, "28/09/2026", "27/10/2026", "confirmada"),
               evento(85, "28/10/2026", "29/10/2026", "falta")], open(det, "w"))
    P = lambda corpo: lau.processar(corpo, "", cron, nomes, det)
    ler = lambda: sorted((e["inicio"], e["fim"], e["status"]) for e in json.load(open(det)))

    ok, msg = P(corpo_ferias("Definir ou ajustar férias", "28/09/2026", "20/10/2026"))
    checar("Férias — ajuste encurta o período final", ok and ("28/09/2026", "20/10/2026", "confirmada") in ler(), str(ler()))
    e = [x for x in json.load(open(det)) if x["fim"] == "20/10/2026"][0]
    checar("Férias — ajuste fica protegido (ajustado_manual)", e.get("ajustado_manual") is True)
    antes = open(det).read()
    ok, msg = P(corpo_ferias("Definir ou ajustar férias", "01/01/2026", "31/03/2026"))
    checar("Férias — mais de 30 dias é recusado e nada é gravado", (not ok) and open(det).read() == antes, msg)
    ok, msg = P(corpo_ferias("Cancelar férias (os dias viram falta)", "10/10/2026", "12/10/2026"))
    L = ler()
    checar("Cancelar — dias cancelados viram falta e o resto continua férias",
           ok and ("10/10/2026", "12/10/2026", "falta") in L and ("28/09/2026", "09/10/2026", "confirmada") in L
           and ("13/10/2026", "20/10/2026", "confirmada") in L, str(L))
    antes = open(det).read()
    ok, msg = P(corpo_ferias("Cancelar férias (os dias viram falta)", "01/03/2026", "05/03/2026"))
    checar("Cancelar — período sem férias não altera nada", (not ok) and open(det).read() == antes, msg)
    ok, msg = P(corpo_ferias("Definir ou ajustar férias", "01/11/2026", "10/11/2026"))
    checar("Férias — período novo cria entrada manual", ok and ("01/11/2026", "10/11/2026", "confirmada") in ler(), str(ler()))
    ok, _ = P(corpo_ferias("Definir ou ajustar férias", "01/11/2026", "10/11/2026", ag="Fulano (ID 999)"))
    checar("Férias — agente fora da lista é recusado", not ok)
    ok, _ = P(corpo_ferias("Definir ou ajustar férias", "31/02/2026", "10/11/2026"))
    checar("Férias — data inválida é recusada", not ok)
    # atestado continua indo para o cronograma
    corpo_at = ("### Agente\n\nAdriano Teste — Equipe 1 (ID 85)\n\n### Primeiro dia do atestado\n\n27/10/2026\n\n"
                "### Último dia do atestado\n\n27/10/2026\n")
    ok, _ = P(corpo_at)
    checar("Atestado — segue gravando no cronograma", ok and len(json.load(open(cron))) == 1)


if __name__ == "__main__":
    teste_excesso_30_dias_vira_falta()
    teste_agente_sem_abono()
    teste_ajuste_manual_e_palavra_final()
    teste_ausencias_primeira_visita_e_feriado()
    teste_pontuacao_dia_inteiro()
    teste_formulario_ferias()
    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} teste(s) falharam: {FALHAS}")
        sys.exit(1)
    print("✅ Todos os testes de ausências passaram.")
