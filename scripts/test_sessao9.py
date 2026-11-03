# -*- coding: utf-8 -*-
"""Testes (sem navegador) da Sessão 9: metas por equipe e dados da página do agente."""
import json, os, sys, tempfile, types

for nome in ("selenium", "selenium.webdriver", "selenium.webdriver.common", "selenium.webdriver.common.by",
             "selenium.webdriver.chrome", "selenium.webdriver.chrome.options", "selenium.webdriver.support",
             "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions"):
    sys.modules.setdefault(nome, types.ModuleType(nome))
sys.modules["selenium"].webdriver = sys.modules["selenium.webdriver"]
sys.modules["selenium.webdriver.common.by"].By = type("By", (), {})
sys.modules["selenium.webdriver.chrome.options"].Options = type("Options", (), {})
sys.modules["selenium.webdriver.support.ui"].WebDriverWait = type("WebDriverWait", (), {})
os.environ.setdefault("EVISITA_CPF", "0"); os.environ.setdefault("EVISITA_SENHA", "t")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402
import coletar_evisita as ce, gerar_agentes as ga  # noqa: E402

FALHAS = []
def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond: FALHAS.append(nome)

# ---- metas por equipe
tmp = tempfile.mkdtemp(); arq = os.path.join(tmp, "m.json")
json.dump({"Equipe 1": 25, "Equipe 2": "abc", "Equipe 3": 0, "Equipe 4": 15}, open(arq, "w"))
m = ce._carregar_metas_equipes(arq)
checar("metas válidas lidas; inválidas ignoradas", m == {"Equipe 1": 25, "Equipe 4": 15}, str(m))
checar("sem arquivo: nenhuma meta", ce._carregar_metas_equipes(os.path.join(tmp, "nao.json")) == {})
open(arq, "w").write("{quebrado")
checar("arquivo quebrado não derruba", ce._carregar_metas_equipes(arq) == {})

def df_agente(equipe, visitas_por_dia, dias=3):
    linhas = []
    for d in range(dias):
        for i in range(visitas_por_dia):
            linhas.append({"dia": pd.Timestamp(2026, 10, 5 + d).date(), "imovel": f"i{d}-{i}", "equipe": equipe})
    return pd.DataFrame(linhas)

def meta_batida(equipe, v):
    df = df_agente(equipe, v)
    por_dia = df.groupby("dia")["imovel"].count()
    return int((por_dia >= ce.meta_da_equipe(df["equipe"].iloc[0])).sum())

ce.METAS_EQUIPES.clear(); ce.METAS_EQUIPES.update({"Equipe 1": 25})
checar("meta da equipe 25: 22 visitas/dia não bate", meta_batida("Equipe 1", 22) == 0)
checar("outra equipe usa a meta padrão (20): 22 bate", meta_batida("Equipe 2", 22) == 3)
checar("meta da equipe 25: 26 visitas/dia bate", meta_batida("Equipe 1", 26) == 3)
ce.METAS_EQUIPES.clear()

# ---- dados da página do agente
raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = ga.gerar(raiz)
ag = d["agentes"]
checar("há agentes", len(ag) > 10, str(len(ag)))
checar("chave é o id do agente quando conhecido", any(k.isdigit() for k in ag))
um = next(v for v in ag.values() if len(v["meses"]) >= 3)
checar("série mensal em ordem cronológica", [m["mes"] for m in um["meses"]][:2] == ["Maio/2026", "Junho/2026"], str([m["mes"] for m in um["meses"]]))
checar("mês tem trabalhados/esperados/nota", all(m["pontos"] is not None and m["esp"] is not None for m in um["meses"]))
checar("semanas do mês aberto presentes", any(len(v["semanas"]) >= 2 for v in ag.values()))
checar("Equipe Bloqueio fora", not any(v["equipe"] == "Equipe Bloqueio" for v in ag.values()))
texto = json.dumps(d, ensure_ascii=False).lower()
checar("nenhum termo de saúde nos dados públicos", not any(t in texto for t in ("atestado", " cid", "diagnóstico", "laudo")))
checar("meses fechados marcados", any(m["fechado"] for v in ag.values() for m in v["meses"]))

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} falha(s): {FALHAS}"); sys.exit(1)
print("✅ Todos os testes da Sessão 9 (sem navegador) passaram.")
