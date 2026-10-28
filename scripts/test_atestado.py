"""Testes do lançamento de atestado por issue (scripts/lancar_atestado.py)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import lancar_atestado as la

falhas = 0
def chk(nome, cond):
    global falhas
    print(("[OK  ] " if cond else "[FALHA] ") + nome)
    falhas += 0 if cond else 1

def corpo(ag="Fulano — Equipe 1 (ID 10)", ini="27/10/2026", fim="28/10/2026"):
    return (f"### Agente\n\n{ag}\n\n### Primeiro dia do atestado\n\n{ini}\n\n"
            f"### Último dia do atestado\n\n{fim}\n\n### Confirmação\n\n- [x] Não informei CID")

with tempfile.TemporaryDirectory() as d:
    nomes = os.path.join(d, "n.json"); cron = os.path.join(d, "c.json")
    json.dump({"10": {"nome": "Fulano", "equipe": "Equipe 1"}}, open(nomes, "w"))
    json.dump([{"alvo": "todos", "motivo": "Chuva", "inicio": "01/10/2026", "fim": "01/10/2026"}], open(cron, "w"))

    ok, msg = la.lancar(corpo(), cron, nomes)
    lista = json.load(open(cron))
    chk("lança atestado válido", ok and len(lista) == 2)
    chk("registro correto", lista[-1] == {"alvo": "agente", "id_agente": 10, "motivo": "Atestado",
                                          "inicio": "27/10/2026", "fim": "28/10/2026"})
    chk("preserva entradas antigas", lista[0]["motivo"] == "Chuva")
    ok, msg = la.lancar(corpo(), cron, nomes)
    chk("repetir não duplica", ok and len(json.load(open(cron))) == 2)
    for nome, c in [("agente fora da lista", corpo(ag="X (ID 999)")),
                    ("data inválida", corpo(ini="31/02/2026")),
                    ("fim antes do início", corpo(ini="28/10/2026", fim="27/10/2026")),
                    ("período absurdo", corpo(ini="01/01/2026", fim="31/12/2026")),
                    ("corpo vazio", "")]:
        antes = open(cron).read()
        ok, msg = la.lancar(c, cron, nomes)
        chk(f"recusa: {nome}", (not ok) and open(cron).read() == antes)

# formulário gerado bate com agentes_nomes.json
import gerar_form_atestado as g
with tempfile.TemporaryDirectory() as d:
    out = os.path.join(d, "a.yml")
    n = g.gerar("data/agentes_nomes.json", out)
    chk("formulário lista todos os agentes", n == len(json.load(open("data/agentes_nomes.json"))))
    chk("formulário sem CID/diagnóstico pedido", "CID" in open(out, encoding="utf-8").read())

print("\n✅ Todos os testes de atestado passaram." if not falhas else f"\n❌ {falhas} falha(s).")
sys.exit(1 if falhas else 0)
