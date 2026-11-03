# -*- coding: utf-8 -*-
"""Testes da regra de Turno sem Lançamento x Possível Evento Externo/Interno
(coordenação, 02/11/2026):
  * ausência sem justificativa = "Turno sem Lançamento" (desconta pontos);
  * ANTES de descontar: cronograma (chuva, treinamento, atestado, férias, folga, reunião);
  * 20+ agentes sem lançamento no mesmo turno => possível evento (sem desconto);
  * toda a equipe (agentes ativos) sem lançamento no turno => possível evento;
  * detecções novas entram como "pendente" (não perdoam sozinhas).
Uso: python3 scripts/test_turno_evento.py
"""
import json
import os
import sys
import tempfile
import types
from datetime import date, datetime

import pandas as pd

try:  # usa o selenium de verdade quando instalado; senão, stubs só pra permitir o import
    import selenium.webdriver.common.by  # noqa: F401
    import selenium.webdriver.chrome.options  # noqa: F401
    import selenium.webdriver.support.ui  # noqa: F401
except ImportError:
    for nome in ("selenium", "selenium.webdriver", "selenium.webdriver.common",
                 "selenium.webdriver.common.by", "selenium.webdriver.chrome",
                 "selenium.webdriver.chrome.options", "selenium.webdriver.support",
                 "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions"):
        sys.modules[nome] = types.ModuleType(nome)
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
    sys.modules["selenium.webdriver.support"].expected_conditions = sys.modules["selenium.webdriver.support.expected_conditions"]
os.environ.setdefault("EVISITA_CPF", "00000000000")
os.environ.setdefault("EVISITA_SENHA", "teste")
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(RAIZ)
import coletar_evisita as ce  # noqa: E402

ce.HOJE_OVERRIDE = date(2027, 1, 1)
FALHAS = []


def checar(nome, cond, detalhe=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {detalhe}" if detalhe and not cond else ""))
    if not cond:
        FALHAS.append(nome)


def d(s):
    return datetime.strptime(s, "%d/%m/%Y").date()


DIAS = ce._dias_uteis_no_intervalo(d("05/10/2026"), d("09/10/2026"))  # seg..sex, sem feriado
MANHA, TARDE = 9.0, 14.0


def montar(agentes):
    """agentes: [(id, nome, equipe, {(dia_fmt, 'Manhã'|'Tarde'), ...} em que NÃO houve visita)]"""
    linhas, resultados = [], []
    for id_ag, nome, equipe, ausentes in agentes:
        for dia in DIAS:
            f = dia.strftime("%d/%m/%Y")
            for turno, hora in (("Manhã", MANHA), ("Tarde", TARDE)):
                if (f, turno) not in ausentes:
                    linhas.append({"id_agente": id_ag, "dia": dia, "hora_chegada": hora})
    df = pd.DataFrame(linhas)
    for id_ag, nome, equipe, _ in agentes:
        resultados.append({"id_agente": id_ag, "nome_agente": nome, "equipe": equipe,
                           "df": df[df["id_agente"] == id_ag].reset_index(drop=True)})
    hist = {a[0]: d("01/06/2026") for a in agentes}
    return df, resultados, hist


def rodar(agentes, cron=None):
    df, res, hist = montar(agentes)
    return ce._preparar_ausencias(df, res, cron if cron is not None else [], primeira_visita=hist)


def classes(regs, id_ag=None, dia=None, turno=None):
    return {r["classificacao"] for r in regs
            if (id_ag is None or r["id_agente"] == id_ag) and (dia is None or r["dia_fmt"] == dia)
            and (turno is None or r["turno"] == turno)}


EV, TSL = ce.CLASSIF_POSSIVEL_EVENTO, ce.CLASSIF_TURNO_SEM_LANCAMENTO

# --- padrão: ausência individual = Turno sem Lançamento ----------------------
agentes = [(1, "A1", "Equipe 1", {("07/10/2026", "Manhã")}),
           (2, "A2", "Equipe 1", set()), (3, "A3", "Equipe 1", set())]
regs = rodar(agentes)
checar("Padrão — ausência individual é Turno sem Lançamento", classes(regs, 1) == {TSL}, str(classes(regs, 1)))
checar("Padrão — observação diz que desconta pontos", "Desconta pontos" in regs[0]["observacao"])

# --- 20+ agentes no mesmo turno (equipes diferentes, ninguém é a equipe toda) --
def montar_20(n_ausentes_por_equipe):
    ag = []
    for eq, base in (("Equipe 1", 100), ("Equipe 2", 200)):
        for i in range(12):
            aus = {("07/10/2026", "Manhã")} if i < n_ausentes_por_equipe else set()
            ag.append((base + i, f"{eq}-{i}", eq, aus))
    return ag
regs = rodar(montar_20(10))   # 10 + 10 = 20 agentes
checar("20 agentes sem lançamento no mesmo turno => Possível Evento", classes(regs) == {EV}, str(classes(regs)))
checar("Evento 20+ — observação explica o gatilho", "20 agentes" in regs[0]["observacao"] and "Sem desconto" in regs[0]["observacao"])
regs = rodar(montar_20(9)) + []  # 9 + 9 = 18
checar("18 agentes (menos de 20) => continua Turno sem Lançamento", classes(regs) == {TSL}, str(classes(regs)))
ag19 = montar_20(10)
ag19[0] = (ag19[0][0], ag19[0][1], ag19[0][2], set())  # tira 1 → 19 ausentes
checar("19 agentes => Turno sem Lançamento", classes(rodar(ag19)) == {TSL})

# --- equipe inteira sem lançamento no turno ------------------------------------
agentes = [(1, "C1", "Equipe 3", {("08/10/2026", "Tarde")}),
           (2, "C2", "Equipe 3", {("08/10/2026", "Tarde")}),
           (3, "C3", "Equipe 3", {("08/10/2026", "Tarde")}),
           (4, "D1", "Equipe 4", set()), (5, "D2", "Equipe 4", set())]
regs = rodar(agentes)
checar("Equipe inteira sem lançamento no turno => Possível Evento", classes(regs) == {EV}, str(classes(regs)))
checar("Equipe inteira — observação cita a equipe", "toda a equipe (3 de 3" in regs[0]["observacao"])
agentes[2] = (3, "C3", "Equipe 3", set())
checar("2 de 3 agentes da equipe => Turno sem Lançamento", classes(rodar(agentes)) == {TSL})

# --- antes de classificar, vale o cronograma (férias tira o agente dos 'ativos') -
agentes = [(1, "E1", "Equipe 1", {("09/10/2026", "Manhã")}),
           (2, "E2", "Equipe 1", {("09/10/2026", "Manhã")}),
           (3, "E3", "Equipe 1", {("09/10/2026", "Manhã")})]
cron = [{"alvo": "agente", "id_agente": 3, "motivo": "Férias", "inicio": "09/10/2026", "fim": "09/10/2026"}]
regs = rodar(agentes, cron)
checar("Cronograma — agente de férias não gera registro", classes(regs, 3) == set())
checar("Cronograma — os 2 agentes ativos sem lançamento = equipe toda => Possível Evento", classes(regs) == {EV}, str(classes(regs)))
cron_chuva = [{"alvo": "todos", "motivo": "Chuva", "inicio": "09/10/2026", "fim": "09/10/2026"}]
checar("Cronograma — dia de chuva registrado: ninguém é descontado nem vira evento", rodar(agentes, cron_chuva) == [])
cron_trein = [{"alvo": "agente", "id_agente": 1, "motivo": "Reunião/Treinamento", "inicio": "09/10/2026", "fim": "09/10/2026"}]
regs = rodar([(1, "T1", "Equipe 1", {("09/10/2026", "Manhã")}), (2, "T2", "Equipe 1", set()), (3, "T3", "Equipe 1", set())], cron_trein)
checar("Cronograma — treinamento justifica o turno (sem registro)", classes(regs, 1) == set())

# --- data de corte opcional (não mexe em período anterior) ------------------------
ce.EVENTO_COLETIVO_A_PARTIR_DE = d("09/10/2026")
checar("Corte — dia anterior à data não vira evento", classes(rodar(montar_20(10))) == {TSL})
ce.EVENTO_COLETIVO_A_PARTIR_DE = d("07/10/2026")
checar("Corte — dia na data (ou depois) vira evento", classes(rodar(montar_20(10))) == {EV})
ce.EVENTO_COLETIVO_A_PARTIR_DE = None

# --- equipe sob demanda fica fora das duas regras -------------------------------
agentes = [(1, "B1", "Equipe Bloqueio", {("07/10/2026", "Manhã")}),
           (2, "B2", "Equipe Bloqueio", {("07/10/2026", "Manhã")})]
regs = rodar(agentes)
checar("Equipe sob demanda (Bloqueio) não vira evento", classes(regs) <= {TSL}, str(classes(regs)))

# --- ranking: evento não desconta e reduz os dias esperados ---------------------
if os.path.exists("data/semanas/326.xlsx"):
    df_total, resultados, _ = ce._montar_df_total_e_resultados([326])
    res = max(resultados, key=lambda r: r["resumo"]["dias_trabalhados"])
    ce.HOJE_OVERRIDE = date(2027, 1, 1)
    base = dict(id_agente=res["id_agente"], nome_agente=res["nome_agente"], equipe=res["equipe"],
                dia_semana="", observacao="x", _fill="E8E8E8")
    regs_tsl = [dict(base, dia_fmt=f"0{i}/09/2026", turno="Manhã", classificacao=TSL) for i in (1, 2, 3)]
    regs_ev = [dict(r, classificacao=EV) for r in regs_tsl]
    argumentos = (date(2026, 9, 30), None, date(2026, 9, 1))
    p_tsl, _ = ce._preparar_ranking(resultados, regs_tsl, *argumentos)
    p_ev, _ = ce._preparar_ranking(resultados, regs_ev, *argumentos)
    li = lambda p: next(x for x in p if x["nome_agente"] == res["nome_agente"])
    checar("Ranking — 3 turnos sem lançamento descontam (turnos_sem_trabalhar = 3)", li(p_tsl)["turnos_sem_trabalhar"] == 3, str(li(p_tsl)["turnos_sem_trabalhar"]))
    checar("Ranking — os mesmos 3 turnos como Possível Evento não descontam", li(p_ev)["turnos_sem_trabalhar"] == 0)
    checar("Ranking — evento não rebaixa a pontuação", li(p_ev)["pontos"] >= li(p_tsl)["pontos"], f'{li(p_ev)["pontos"]} x {li(p_tsl)["pontos"]}')
else:
    print("sem cache data/semanas/326.xlsx — teste de ranking pulado")

# --- detecção nova entra como pendente (não perdoa sozinha) -----------------------
def evento_ferias():
    return {"tipo": "possiveis_ferias", "id_agente": 999, "nome_agente": "Zé", "equipe": "Equipe 1",
            "inicio": "05/10/2026", "fim": "16/10/2026", "duracao": 10, "agentes_envolvidos": [999], "nomes_envolvidos": ["Zé"]}


def evento_chuva():
    return {"tipo": "paralisacao_coletiva", "equipe": "Equipe 1", "agentes_envolvidos": [1, 2], "nomes_envolvidos": ["a", "b"],
            "inicio": "07/10/2026", "fim": "07/10/2026", "duracao": 1}


def detectar(flag_ferias, flag_chuva):
    antes = (ce.CONFIRMAR_FERIAS_AUTOMATICAMENTE, ce.CONFIRMAR_CHUVA_AUTOMATICAMENTE)
    ce.CONFIRMAR_FERIAS_AUTOMATICAMENTE, ce.CONFIRMAR_CHUVA_AUTOMATICAMENTE = flag_ferias, flag_chuva
    try:
        caminho = os.path.join(tempfile.mkdtemp(), "det.json")
        return ce.atualizar_deteccoes_pendentes([evento_ferias(), evento_chuva()], caminho=caminho)
    finally:
        ce.CONFIRMAR_FERIAS_AUTOMATICAMENTE, ce.CONFIRMAR_CHUVA_AUTOMATICAMENTE = antes


fin = detectar(False, False)
fer = next(e for e in fin if e["tipo"] == "possiveis_ferias")
chu = next(e for e in fin if e["tipo"] == "paralisacao_coletiva")
checar("Padrão — férias detectada entra como pendente", fer["status"] == "pendente" and not fer["confirmado_automaticamente"], str(fer["status"]))
checar("Padrão — paralisação coletiva entra como pendente (sem categoria Chuva)", chu["status"] == "pendente" and chu["categoria_coletiva"] is None, str(chu))
efetivo = ce._cronograma_efetivo(fin)
checar("Pendente não entra no cronograma efetivo (continua contando)", not any(e.get("id_agente") == 999 for e in efetivo) and
       not any(e.get("alvo") == "equipe" and e.get("inicio") == "07/10/2026" for e in efetivo))
fin_auto = detectar(True, True)
checar("Modo automático (opcional) segue confirmando", all(e["status"] == "confirmada" for e in fin_auto))

# --- Patricia (ID 3177): treinamento registrado no cronograma ------------------------
ids = {e.get("id_agente"): e for e in ce.CRONOGRAMA_AUSENCIAS if e.get("id_agente") == 3177}
motivo = ce._obter_motivo_cronograma(3177, "Equipe 3", date(2026, 10, 22), ce.CRONOGRAMA_AUSENCIAS, turno="Manhã")
checar("Patricia (3177) — treinamento cobre 22/10 no cronograma", bool(motivo) and "Treinamento" in motivo, str(motivo))
checar("Patricia — treinamento não cobre outra agente", not ce._obter_motivo_cronograma(3128, "Equipe 3", date(2026, 10, 22), ce.CRONOGRAMA_AUSENCIAS, turno="Manhã"))

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam: {FALHAS}")
    sys.exit(1)
print("✅ Todos os testes de turno/evento passaram.")
