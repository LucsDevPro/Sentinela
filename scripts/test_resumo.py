# -*- coding: utf-8 -*-
"""Testes das funções puras de scripts/resumo.py."""
import os
import sys
from datetime import date

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resumo as R

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


def ev(ini, fim, tipo, status, equipe="Equipe 1", nome="Fulano"):
    return {"inicio": ini, "fim": fim, "tipo": tipo, "status": status, "equipe": equipe, "nome_agente": nome, "motivo": ""}


DETS = [
    ev("10/09/2026", "20/09/2026", "possiveis_ferias", "confirmada"),
    ev("14/09/2026", "14/09/2026", "paralisacao_coletiva", "pendente", "Equipe 2"),
    ev("28/09/2026", "05/10/2026", "possiveis_ferias", "falta", nome="Beltrano"),     # atravessa Setembro -> Outubro
    ev("20/10/2026", "21/10/2026", "paralisacao_coletiva", "pendente", "Equipe 3"),
]
SET = (date(2026, 8, 30), date(2026, 10, 2))
OUT = (date(2026, 10, 4), date(2026, 10, 30))

# janela do mês = do 1º dia da primeira semana à SEXTA da última
j = R.janela_do_mes(327, 330)
checar("janela de Outubro: 04/10 a 30/10 (sexta)", j == (date(2026, 10, 4), date(2026, 10, 30)), str(j))

checar("sem filtro devolve tudo, em ordem cronológica", [e["inicio"] for e in R.filtrar_deteccoes(DETS)] == ["10/09/2026", "14/09/2026", "28/09/2026", "20/10/2026"])
checar("filtra por janela (Setembro)", len(R.filtrar_deteccoes(DETS, janela=SET)) == 3)
checar("evento que atravessa o mês aparece nos dois", any(e["nome_agente"] == "Beltrano" for e in R.filtrar_deteccoes(DETS, janela=OUT)))
checar("filtra por status", [e["status"] for e in R.filtrar_deteccoes(DETS, status="pendente")] == ["pendente", "pendente"])
checar("filtra por tipo curto (coletiva)", len(R.filtrar_deteccoes(DETS, tipo="coletiva")) == 2 and len(R.filtrar_deteccoes(DETS, tipo="ferias")) == 2)
checar("filtros combinados (Outubro + pendente + coletiva)", len(R.filtrar_deteccoes(DETS, OUT, "pendente", "coletiva")) == 1)
checar("nada encontrado -> lista vazia", R.filtrar_deteccoes(DETS, status="falta", tipo="coletiva") == [])

c = R.contar_deteccoes(DETS, [("Setembro/2026", SET), ("Outubro/2026", OUT)])
checar("contagem por mês e tipo/status", c["Setembro/2026"] == {("ferias", "confirmada"): 1, ("coletiva", "pendente"): 1, ("ferias", "falta"): 1}, str(c))
checar("contagem: o evento que atravessa conta nos dois meses", c["Outubro/2026"].get(("ferias", "falta")) == 1, str(c))

l = R.linha_deteccao(DETS[1])
checar("linha da paralisação mostra a equipe e o tipo curto", "equipe Equipe 2" in l and "coletiva" in l and "pendente" in l, l)
checar("linha de férias mostra o agente", "Fulano" in R.linha_deteccao(DETS[0]) and "ferias" in R.linha_deteccao(DETS[0]))

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes de resumo passaram.")
