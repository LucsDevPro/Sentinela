# -*- coding: utf-8 -*-
"""Testes das funções puras de scripts/regenerar_mes.py (não roda a regeneração inteira)."""
import os
import sys

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regenerar_mes as R

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


ARQ = [(313, 317, "Julho/2026"), (318, 321, "Agosto/2026"), (322, 326, "Setembro/2026")]
OFI = [(327, 330, "Outubro/2026"), (331, 335, "Novembro/2026")]

# --- escolher_alvos
checar("um mês congelado (ignora maiúsculas)", R.escolher_alvos("setembro/2026", ARQ, OFI) == [ARQ[2]])
checar("'todos' devolve todos os congelados", R.escolher_alvos("todos", ARQ, OFI) == ARQ)
checar("espaços em volta são ignorados", R.escolher_alvos("  Julho/2026 ", ARQ, OFI) == [ARQ[0]])
for arg, trecho, nome in [("Outubro/2026", "vigente", "mês vigente é recusado com explicação"),
                          ("Maio/2026", "Opções", "mês desconhecido lista as opções"),
                          ("", "Opções", "texto vazio é recusado")]:
    try:
        R.escolher_alvos(arg, ARQ, OFI)
        checar(nome, False, "não levantou erro")
    except ValueError as e:
        checar(nome, trecho in str(e), str(e))
try:
    R.escolher_alvos("todos", [], OFI)
    checar("sem nenhum congelado é recusado", False)
except ValueError:
    checar("sem nenhum congelado é recusado", True)

# --- semanas_faltando
checar("cache completo -> nada falta", R.semanas_faltando(ARQ[1], [318, 319, 320, 321, 400]) == [])
checar("aponta as semanas que faltam", R.semanas_faltando(ARQ[1], [318, 320]) == [319, 321])

# --- comparar_rankings  (posição, dias trab., dias esperados, turnos s/ trabalhar, pontos)
ant = {"A": (1, 20, 20, 0, 80.0), "B": (2, 18, 20, 2, 70.0), "C": (3, 15, 20, 5, 60.0)}
checar("rankings iguais -> idêntico", R.comparar_rankings(ant, dict(ant))["identico"] is True)
novo = {"A": (2, 20, 20, 0, 80.0), "B": (1, 18, 20, 2, 78.5), "C": (3, 15, 20, 5, 58.0)}
r = R.comparar_rankings(ant, novo)
checar("conta quem sobe e quem desce", (r["sobem"], r["descem"], r["iguais"]) == (1, 1, 1), str(r))
checar("maior alta, maior queda e média", (round(r["maior_alta"], 1), round(r["maior_queda"], 1), round(r["media"], 2)) == (8.5, -2.0, 2.17), str(r))
checar("conta mudança de posição", r["posicao_mudou"] == 2 and r["identico"] is False, str(r))
checar("agente que saiu/entrou deixa de ser idêntico", R.comparar_rankings(ant, {"A": ant["A"]})["identico"] is False)
checar("sem agentes em comum não quebra", R.comparar_rankings({}, {})["agentes"] == 0)

# --- manifest
MAN = [
    {"arquivo": "semanas_313-317.xlsx", "label": "Julho/2026", "origem": "manual", "semana_inicio": 313, "semana_fim": 317},
    {"arquivo": "semanas_327-330.xlsx", "label": "Outubro/2026", "origem": "cache", "semana_inicio": 327, "semana_fim": 330},
    {"arquivo": "semana_327.xlsx", "tipo": "semana", "origem": "cache", "semana_inicio": 327, "semana_fim": 327},
]
sem = R.tirar_do_manifest(MAN, [ARQ[0]])
checar("tira só o mês alvo do manifest", [e["arquivo"] for e in sem] == ["semanas_327-330.xlsx", "semana_327.xlsx"])
checar("não altera a lista original", len(MAN) == 3)
tirou_semanal = R.tirar_do_manifest(MAN, [OFI[0]])
checar("tirar um mês também leva as visões semanais dele", [e["arquivo"] for e in tirou_semanal] == ["semanas_313-317.xlsx"])
cong = R.congelar_no_manifest([dict(e, origem="cache") for e in MAN], [OFI[0]], "05/11/2026")
checar("congelar marca manual, não parcial e data", [(e["origem"], e.get("parcial"), e.get("reaberto_em")) for e in cong][1:] == [("manual", False, "05/11/2026")] * 2, str(cong))
checar("congelar não toca nos outros meses", cong[0]["origem"] == "cache" and "reaberto_em" not in cong[0])

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes de regenerar_mes passaram.")
