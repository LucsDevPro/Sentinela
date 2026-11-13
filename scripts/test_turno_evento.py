# -*- coding: utf-8 -*-
"""Testes da regra de Turno sem Lançamento x Possível Evento Externo/Interno
(coordenação, 02/11/2026; limite e ordem de decisão ajustados em 05/11 e 08/11/2026):
  * ausência sem justificativa = "Turno sem Lançamento" (desconta pontos);
  * ANTES de descontar: cronograma (chuva, treinamento, atestado, férias, folga, reunião);
  * LIMITE (23) ou mais agentes sem lançamento no mesmo turno => CHUVA automática (regra suprema, sem desconto);
  * abaixo do limite, toda a equipe (agentes ativos) sem lançamento => possível evento, sem desconto;
  * senão é Turno sem Lançamento (falta);
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


EV, TSL, CHUVA = ce.CLASSIF_POSSIVEL_EVENTO, ce.CLASSIF_TURNO_SEM_LANCAMENTO, ce.CLASSIF_CHUVA_AUTOMATICA

# --- padrão: ausência individual = Turno sem Lançamento ----------------------
agentes = [(1, "A1", "Equipe 1", {("07/10/2026", "Manhã")}),
           (2, "A2", "Equipe 1", set()), (3, "A3", "Equipe 1", set())]
regs = rodar(agentes)
checar("Padrão — ausência individual é Turno sem Lançamento", classes(regs, 1) == {TSL}, str(classes(regs, 1)))
checar("Padrão — observação diz que desconta pontos", "Desconta pontos" in regs[0]["observacao"])

# --- LIMITE (23) ou mais agentes no mesmo turno (equipes diferentes, ninguém é a equipe toda) --
LIM = ce.LIMITE_AGENTES_EVENTO_TURNO
checar("o limite geral é 23 (regra suprema da coordenação, 08/11/2026)", LIM == 23, str(LIM))


def montar_n(n_ausentes, cobertos_chuva=0):
    """2 equipes de 13 agentes; `n_ausentes` ausentes no turno (metade em cada), nunca a equipe toda
    (com 12 por equipe, 23 ausentes esvaziariam uma equipe inteira e acionariam a regra de equipe).
    `cobertos_chuva` dos ausentes ganham 'Chuva' no cronograma (devolve também a lista do cronograma)."""
    ag, cron, a_cobrir = [], [], cobertos_chuva
    metade = (n_ausentes // 2, n_ausentes - n_ausentes // 2)
    for (eq, base), n_eq in zip((("Equipe 1", 100), ("Equipe 2", 200)), metade):
        for i in range(13):
            aus = {("07/10/2026", "Manhã")} if i < n_eq else set()
            ag.append((base + i, f"{eq}-{i}", eq, aus))
            if aus and a_cobrir > 0:
                cron.append({"alvo": "agente", "id_agente": base + i, "motivo": "Chuva", "inicio": "07/10/2026", "fim": "07/10/2026"})
                a_cobrir -= 1
    return ag, cron


regs = rodar(montar_n(LIM)[0])
checar(f"{LIM} agentes sem lançamento no mesmo turno => CHUVA automática", classes(regs) == {CHUVA}, str(classes(regs)))
checar("CHUVA automática — observação informa regra suprema e dispensa validação",
       "confirmação automática" in regs[0]["observacao"] and "Sem desconto" in regs[0]["observacao"]
       and "sem necessidade de validação manual" in regs[0]["observacao"], regs[0]["observacao"])
checar(f"{LIM + 3} agentes (bem acima do limite) => CHUVA automática", classes(rodar(montar_n(LIM + 3)[0])) == {CHUVA})
checar(f"{LIM - 1} agentes (abaixo do limite, ninguém é a equipe toda) => Turno sem Lançamento (falta)", classes(rodar(montar_n(LIM - 1)[0])) == {TSL})
checar("22 agentes (abaixo do limite) => Turno sem Lançamento", classes(rodar(montar_n(22)[0])) == {TSL})

# --- a contagem total inclui quem já está coberto por chuva/reunião no cronograma ----
ag, cron = montar_n(LIM, cobertos_chuva=3)                        # 20 descobertos + 3 cobertos por chuva
checar("A contagem total inclui quem já está coberto por chuva no cronograma",
       ce.CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE is True)
regs = rodar(ag, cron)
checar("20 descobertos + 3 cobertos por chuva = 23 => CHUVA automática", classes(regs) == {CHUVA}, str(classes(regs)))
checar("  — a observação informa quantos já estavam cobertos", "3 já cobertos por chuva/reunião" in regs[0]["observacao"], regs[0]["observacao"])
ag_f = [x for x in ag]
cron_ferias = [dict(c, motivo="Férias") for c in cron]
checar("Férias (ausência individual) nunca contam no limite", classes(rodar(ag_f, cron_ferias)) == {TSL}, str(classes(rodar(ag_f, cron_ferias))))
# Paralisação coletiva VALIDADA entra no cronograma como "Chuva (confirmada)"/"Chuva (automático)":
# validar o evento não pode tirar esses agentes da conta dos 23 (senão o turno virava falta e descontava).
for sufixo in (" (confirmada)", " (automático)"):
    cron_suf = [dict(c, motivo="Chuva" + sufixo) for c in cron]
    regs_suf = rodar(ag, cron_suf)
    checar(f'Chuva "{sufixo.strip()}" também conta nos 23 (validar o evento não vira desconto)',
           classes(regs_suf) == {CHUVA}, str(classes(regs_suf)))
cron_equipe_conf = [{"alvo": "equipe", "equipe": "Equipe 2", "motivo": "Chuva (confirmada)", "inicio": "07/10/2026", "fim": "07/10/2026"}]
# Caso real (Outubro/2026): equipe inteira (13) coberta por paralisação validada + 10 de outra equipe sem lançamento = 23.
aus_dia = {("07/10/2026", "Manhã")}
ag_eq = [(100 + i, f"E1-{i}", "Equipe 1", aus_dia if i < 10 else set()) for i in range(13)] + \
        [(200 + i, f"E2-{i}", "Equipe 2", aus_dia) for i in range(13)]
regs_eq = rodar(ag_eq, cron_equipe_conf)
checar("Equipe inteira coberta por Chuva (confirmada) conta nos 23 e o resto vira CHUVA, não desconto",
       classes(regs_eq) == {CHUVA}, str(classes(regs_eq)))
ce.CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE = False
checar("Com a contagem total desligada, os mesmos 20 descobertos não atingem o limite",
       classes(rodar(ag, cron)) == {TSL}, str(classes(rodar(ag, cron))))
ce.CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE = True

# --- equipe inteira sem lançamento no turno ------------------------------------
agentes = [(1, "C1", "Equipe 3", {("08/10/2026", "Tarde")}),
           (2, "C2", "Equipe 3", {("08/10/2026", "Tarde")}),
           (3, "C3", "Equipe 3", {("08/10/2026", "Tarde")}),
           (4, "D1", "Equipe 4", set()), (5, "D2", "Equipe 4", set())]
regs = rodar(agentes)
checar("Equipe inteira sem lançamento no turno => Possível Evento", classes(regs) == {EV}, str(classes(regs)))
checar("Equipe inteira — observação cita a equipe e diz chuva isolada ou reunião", "toda a equipe (3 de 3" in regs[0]["observacao"] and "chuva isolada ou reunião" in regs[0]["observacao"], regs[0]["observacao"])
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

# --- data de corte opcional: só limita a regra de equipe, não a regra suprema -------
ce.EVENTO_COLETIVO_A_PARTIR_DE = d("09/10/2026")
checar("Corte — 23+ continua CHUVA automática mesmo antes da data de corte", classes(rodar(montar_n(LIM)[0])) == {CHUVA})
checar("Corte — equipe inteira antes da data de corte continua Turno sem Lançamento",
       classes(rodar([(1, "C1", "Equipe 3", {("08/10/2026", "Tarde")}), (2, "C2", "Equipe 3", {("08/10/2026", "Tarde")})])) == {TSL})
ce.EVENTO_COLETIVO_A_PARTIR_DE = d("07/10/2026")
checar("Corte — abaixo de 23, equipe inteira vira evento na data (ou depois)",
       classes(rodar([(1, "C1", "Equipe 3", {("08/10/2026", "Tarde")}), (2, "C2", "Equipe 3", {("08/10/2026", "Tarde")})])) == {EV})
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
    regs_chuva = [dict(r, classificacao=CHUVA) for r in regs_tsl]
    argumentos = (date(2026, 9, 30), None, date(2026, 9, 1))
    p_tsl, _ = ce._preparar_ranking(resultados, regs_tsl, *argumentos)
    p_ev, _ = ce._preparar_ranking(resultados, regs_ev, *argumentos)
    p_chuva, _ = ce._preparar_ranking(resultados, regs_chuva, *argumentos)
    li = lambda p: next(x for x in p if x["nome_agente"] == res["nome_agente"])
    checar("Ranking — 3 turnos sem lançamento descontam (turnos_sem_trabalhar = 3)", li(p_tsl)["turnos_sem_trabalhar"] == 3, str(li(p_tsl)["turnos_sem_trabalhar"]))
    checar("Ranking — os mesmos 3 turnos como Possível Evento não descontam", li(p_ev)["turnos_sem_trabalhar"] == 0)
    checar("Ranking — os mesmos 3 turnos como CHUVA automática não descontam",
           li(p_chuva)["turnos_sem_trabalhar"] == 0 and li(p_chuva)["pontos"] == li(p_ev)["pontos"] and li(p_chuva)["pontos"] >= li(p_tsl)["pontos"],
           f'{li(p_chuva)["turnos_sem_trabalhar"]} turnos, {li(p_chuva)["pontos"]} x {li(p_tsl)["pontos"]}')
    checar("Ranking — evento não rebaixa a pontuação", li(p_ev)["pontos"] >= li(p_tsl)["pontos"], f'{li(p_ev)["pontos"]} x {li(p_tsl)["pontos"]}')
else:
    print("sem cache data/semanas/326.xlsx — teste de ranking pulado")

# --- visão semanal: agente do mês SEM nenhuma visita na semana entra e é cobrado ----------------
agentes = [(1, "S1", "Equipe 1", set()), (2, "S2", "Equipe 1", set())]
df_s, res_s, hist_s = montar(agentes)
def vazio(id_, equipe, hist=d("01/06/2026")):
    hist_s[id_] = hist
    return {"ok": True, "id_agente": id_, "nome_agente": f"Z{id_}", "equipe": equipe, "resumo": {},
            "df": df_s.iloc[0:0].copy(), "sem_visita_no_periodo": True}
regs_v = ce._preparar_ausencias(df_s, res_s + [vazio(900, "Equipe 1")], [], primeira_visita=hist_s)
r900 = [r for r in regs_v if r["id_agente"] == 900]
checar("Sem visita na semana — o agente do mês é avaliado (turnos sem lançamento)", len(r900) > 0 and {r["classificacao"] for r in r900} <= {TSL, EV, CHUVA}, str(len(r900)))
checar("Sem visita na semana — sem a marca, o agente continua ignorado",
       not [r for r in ce._preparar_ausencias(df_s, res_s + [dict(vazio(901, "Equipe 1"), sem_visita_no_periodo=False)], [], primeira_visita=hist_s) if r["id_agente"] == 901])
checar("Sem visita na semana — equipe sob demanda (Bloqueio) nunca entra vazia",
       not [r for r in ce._preparar_ausencias(df_s, res_s + [vazio(902, "Equipe Bloqueio")], [], primeira_visita=hist_s) if r["id_agente"] == 902])
checar("Sem visita na semana — quem só começou depois do período não é cobrado",
       not [r for r in ce._preparar_ausencias(df_s, res_s + [vazio(903, "Equipe 1", hist=d("30/12/2026"))], [], primeira_visita=hist_s) if r["id_agente"] == 903])
cron_f = [{"alvo": "agente", "id_agente": 904, "motivo": "Férias", "inicio": "01/10/2026", "fim": "31/12/2026"}]
checar("Sem visita na semana — férias no cronograma: sem registro (não aparece no ranking)",
       not [r for r in ce._preparar_ausencias(df_s, res_s + [vazio(904, "Equipe 1")], cron_f, primeira_visita=hist_s) if r["id_agente"] == 904])

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


# Padrão atual (13/11/2026): paralisação coletiva nasce confirmada como Chuva (a coordenação quer
# todas validadas); férias/atestado individuais continuam entrando pendentes.
checar("Padrão — CONFIRMAR_CHUVA_AUTOMATICAMENTE ligado e CONFIRMAR_FERIAS_AUTOMATICAMENTE desligado",
       ce.CONFIRMAR_CHUVA_AUTOMATICAMENTE is True and ce.CONFIRMAR_FERIAS_AUTOMATICAMENTE is False)
fin_padrao = ce.atualizar_deteccoes_pendentes([evento_ferias(), evento_chuva()],
                                              caminho=os.path.join(tempfile.mkdtemp(), "det_padrao.json"))
fer_p = next(e for e in fin_padrao if e["tipo"] == "possiveis_ferias")
chu_p = next(e for e in fin_padrao if e["tipo"] == "paralisacao_coletiva")
checar("Padrão — paralisação coletiva nova já nasce confirmada como Chuva (sem validação manual)",
       chu_p["status"] == "confirmada" and chu_p["categoria_coletiva"] == "Chuva" and chu_p["confirmado_automaticamente"], str(chu_p))
checar("Padrão — férias individual continua entrando pendente", fer_p["status"] == "pendente" and not fer_p["confirmado_automaticamente"], str(fer_p["status"]))
efetivo_p = ce._cronograma_efetivo(fin_padrao)
checar("Padrão — paralisação confirmada entra no cronograma efetivo; férias pendente não",
       any(e.get("alvo") == "equipe" and e.get("inicio") == "07/10/2026" for e in efetivo_p)
       and not any(e.get("id_agente") == 999 for e in efetivo_p))

# Modo manual (flags desligadas): tudo entra pendente até a coordenação confirmar.
fin = detectar(False, False)
fer = next(e for e in fin if e["tipo"] == "possiveis_ferias")
chu = next(e for e in fin if e["tipo"] == "paralisacao_coletiva")
checar("Modo manual — férias detectada entra como pendente", fer["status"] == "pendente" and not fer["confirmado_automaticamente"], str(fer["status"]))
checar("Modo manual — paralisação coletiva entra como pendente (sem categoria Chuva)", chu["status"] == "pendente" and chu["categoria_coletiva"] is None, str(chu))
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
