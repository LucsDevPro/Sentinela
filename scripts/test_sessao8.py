# -*- coding: utf-8 -*-
"""Testes da Sessão 8: ajuste de pontos, equipe parada, fechar/reabrir mês."""
import json, os, shutil, sys, tempfile, types, datetime as _dt

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
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import coletar_evisita as ce, aplicar_decisao as ad, fechar_mes as fm, meses_arquivados as mesarq  # noqa: E402

FALHAS = []
def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond: FALHAS.append(nome)

NOMES = {"85": {"nome": "Adriano Teste", "equipe": "Equipe 1"}, "86": {"nome": "Bia Teste", "equipe": "Equipe 2"}}
pasta = tempfile.mkdtemp()
n, c, a = (os.path.join(pasta, x) for x in ("n.json", "c.json", "a.json"))
json.dump(NOMES, open(n, "w")); json.dump([], open(c, "w")); json.dump([], open(a, "w"))
det = os.path.join(pasta, "d.json"); json.dump([], open(det, "w"))
A = lambda **d: ad.aplicar(dict(quem="Maria", **d), c, n, det, a)
lerj = lambda p: json.load(open(p))
AJ = dict(acao="ajuste", id_agente=85, data="15/10/2026", pontos=2, motivo="Instabilidade do e-Visita")

# ---- ajuste de pontos
ok, msg = A(**AJ)
checar("ajuste válido grava com motivo e autor", ok and lerj(a)[0]["motivo"] == "Instabilidade do e-Visita" and lerj(a)[0]["por"] == "Maria", msg)
ok, _ = A(**AJ); checar("ajuste repetido não duplica", ok and len(lerj(a)) == 1)
ok, msg = A(**dict(AJ, pontos=25)); checar("ajuste acima do limite é recusado", not ok and len(lerj(a)) == 1, msg)
ok, msg = A(**dict(AJ, motivo="atestado")); checar("motivo com dado de saúde é recusado", not ok, msg)
ok, msg = A(**dict(AJ, data="15/08/2026")); checar("ajuste em mês fechado é recusado", not ok and "fechado" in msg, msg)
ok, msg = A(**dict(AJ, id_agente=999)); checar("agente desconhecido é recusado", not ok)
ok, _ = A(**dict(AJ, acao="ajuste_remover")); checar("ajuste é reversível", ok and lerj(a) == [])
ok, _ = A(**dict(AJ, acao="ajuste_remover")); checar("desfazer o que não existe é recusado", not ok)
# o ajuste aparece no Extrato como "Ajuste manual: motivo" e muda a nota
A(**AJ)
ajs = ce._carregar_ajustes_ranking(a)
checar("motor lê o ajuste gravado (extra 'por' é ignorado)", len(ajs) == 1 and ajs[0]["pontos"] == 2.0)

# ---- equipe parada
P = dict(acao="parada", alvo="equipe", equipe="Equipe 2", motivo="Chuva", inicio="20/10/2026", fim="20/10/2026")
ok, msg = A(**P); cr = lerj(c)
checar("parada por equipe grava alvo equipe", ok and cr == [{"alvo": "equipe", "equipe": "Equipe 2", "motivo": "Chuva", "inicio": "20/10/2026", "fim": "20/10/2026"}], str(cr))
ok, _ = A(**dict(P, alvo="todos", motivo="Reunião/Treinamento", turno="Tarde"))
checar("parada de todos só de um turno", ok and lerj(c)[-1].get("turno") == "Tarde" and lerj(c)[-1]["alvo"] == "todos")
fim_da_equipe = ce._cronograma_motivo(86, "Equipe 2", _dt.date(2026, 10, 20), lerj(c), "Manhã") if hasattr(ce, "_cronograma_motivo") else None
ok, msg = A(**dict(P, equipe="Equipe X")); checar("equipe inexistente é recusada", not ok, msg)
ok, msg = A(**dict(P, motivo="Folga")); checar("motivo fora da lista é recusado", not ok)
ok, msg = A(**dict(P, inicio="01/09/2026", fim="05/09/2026")); checar("parada em mês fechado é recusada", not ok and "fechado" in msg, msg)
ok, _ = A(**dict(P, acao="parada_remover")); checar("parada é reversível", ok and len(lerj(c)) == 1)

# ---- fechar mês (cópia do repositório)
trab = tempfile.mkdtemp()
for sub in ("data", "scripts"):
    shutil.copytree(os.path.join(RAIZ, sub), os.path.join(trab, sub), ignore=shutil.ignore_patterns("__pycache__", "csv"))
cwd = os.getcwd(); os.chdir(trab)
try:
    ce.HOJE_OVERRIDE = _dt.date(2026, 10, 20)
    r = fm.checar("Outubro/2026")
    checar("mês em andamento: checklist bloqueia", not r["pronto"] and any(i["id"] == "semanas" and i["ok"] is False for i in r["itens"]))
    ok, msg = fm.fechar("Outubro/2026", regenerar=False)
    checar("fechar mês incompleto é recusado e nada muda", not ok and not any(t[2] == "Outubro/2026" for t in mesarq.carregar()), msg)

    ce.HOJE_OVERRIDE = _dt.date(2026, 10, 31)
    dets = json.load(open("data/deteccoes_pendentes.json"))
    # os dados reais podem já estar todos validados; para o teste, tira a validação de uma férias de Outubro
    for e in dets:
        if e.get("tipo") == "possiveis_ferias" and e.get("status") == "confirmada" and e["fim"].endswith("/10/2026"):
            e.pop("validada_por", None); e.pop("validada_em", None); break
    json.dump(dets, open("data/deteccoes_pendentes.json", "w"), ensure_ascii=False)
    r = fm.checar("Outubro/2026")
    checar("férias detectadas esperando validação bloqueiam", any(i["id"] == "ferias" and i["ok"] is False for i in r["itens"]))
    for e in dets:
        e["validada_por"] = "Maria"
    json.dump(dets, open("data/deteccoes_pendentes.json", "w"))
    r = fm.checar("Outubro/2026")
    checar("checklist completo: pronto", r["pronto"], json.dumps(r["itens"], ensure_ascii=False))
    ferias_ant = dets
    pend = [{"tipo": "possiveis_ferias", "status": "confirmada", "id_agente": 85, "inicio": "05/10/2026", "fim": "10/10/2026"}]
    json.dump(ferias_ant + pend, open("data/deteccoes_pendentes.json", "w"))
    r = fm.checar("Outubro/2026")
    checar("férias sem validação bloqueiam o fechamento", not r["pronto"] and any(i["id"] == "ferias" and i["ok"] is False for i in r["itens"]))
    json.dump(ferias_ant, open("data/deteccoes_pendentes.json", "w"))

    # Setembro (congelado) deve ficar idêntico
    import hashlib
    h = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    set_antes = h("data/historico/semanas_322-326.xlsx")
    ok, msg = fm.fechar("Outubro/2026", regenerar=False)
    checar("fechar mês completo funciona", ok, msg)
    man = json.load(open("data/historico/manifest.json"))
    mes = [e for e in man if e["label"] == "Outubro/2026" and e.get("tipo") != "semana"][0]
    semanas = [e for e in man if e.get("tipo") == "semana"]
    checar("mês e semanas viram manual (congelados)", mes["origem"] == "manual" and semanas and all(e["origem"] == "manual" for e in semanas))
    checar("cópia de segurança criada", any("antes-de-fechar" in f for f in os.listdir("data/historico/backup_congelado")))
    checar("mês aparece em meses_arquivados.json", any(i["mes"] == "Outubro/2026" for i in json.load(open("data/meses_arquivados.json"))))
    checar("mês já fechado não pode ser fechado de novo", not fm.fechar("Outubro/2026", regenerar=False)[0])
    checar("meses antigos continuam iguais", h("data/historico/semanas_322-326.xlsx") == set_antes)
    ok, msg = A(**dict(AJ, data="15/10/2026")) if False else (None, None)
    ok, msg = ad.aplicar(dict(quem="Maria", **AJ), c, n, det, a)
    checar("com o mês fechado, ajuste nele é recusado", not ok and "fechado" in msg, msg)

    ok, msg = fm.reabrir("Outubro/2026", "", regenerar=False)
    checar("reabrir sem digitar o nome é recusado", not ok)
    ok, msg = fm.reabrir("Setembro/2026", "Setembro/2026", regenerar=False)
    checar("mês antigo não reabre pela página", not ok, msg)
    ok, msg = fm.reabrir("Outubro/2026", "outubro/2026", regenerar=False)
    man = json.load(open("data/historico/manifest.json"))
    checar("reabrir com confirmação funciona e volta a 'cache'", ok and all(e["origem"] == "cache" for e in man if e.get("label") == "Outubro/2026" or e.get("mes") == "Outubro/2026"), msg)
    checar("reabrir faz backup antes", any("antes-de-reabrir" in f for f in os.listdir("data/historico/backup_congelado")))
    checar("mês sai de meses_arquivados.json", not any(i["mes"] == "Outubro/2026" for i in json.load(open("data/meses_arquivados.json"))))
finally:
    os.chdir(cwd)

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} falha(s): {FALHAS}"); sys.exit(1)
print("✅ Todos os testes da Sessão 8 passaram.")
