# -*- coding: utf-8 -*-
"""Testes da aba "Por Área" (uma linha recolhida por área): generate_dashboard.build_areas_agrupadas."""
import os
import re
import sys

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import generate_dashboard as GD

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


def lin(area, agente, abertos, rapidas, fechados, recusados, tempo, quart, equipe="Equipe 1"):
    return {"area": area, "agente": agente, "equipe": equipe, "abertos": abertos, "rapidas": rapidas, "fechados": fechados,
            "recusados": recusados, "tempo_medio": tempo, "quarteiroes_lista": quart, "alerta": "x"}


REGS = [
    lin("435 - JARDIM PRIMOR", "Ana", 60, 6, 10, 0, 4.0, "Q10, Q2"),
    lin("435 - JARDIM PRIMOR", "Bia", 40, 8, 20, 10, 6.0, "Q2, Q1"),
    lin("400 - CENTRO", "Caio", 10, 5, 0, 0, 3.0, "Q7"),
    lin("410 - VILA", "Dani", 0, 0, 0, 0, float("nan"), float("nan")),   # linha vazia da planilha (NaN) não pode quebrar
]
G = {g["area"]: g for g in GD.build_areas_agrupadas(REGS)}
j = G["435 - JARDIM PRIMOR"]

checar("uma linha por área", len(G) == 3, len(G))
checar("soma imóveis abertos", j["abertos"] == 100, j["abertos"])
checar("soma rápidas, fechados e recusados", (j["rapidas"], j["fechados"], j["recusados"]) == (14, 30, 10), (j["rapidas"], j["fechados"], j["recusados"]))
checar("% rápidas refeito sobre o total (14/100), não média de %", abs(j["pct_rapidas"] - 14.0) < 1e-9, j["pct_rapidas"])
checar("% pendência refeito sobre o total (40/140)", abs(j["pct_pendencia"] - 40 / 140 * 100) < 1e-9, j["pct_pendencia"])
checar("tempo médio ponderado pelos imóveis abertos ((60*4+40*6)/100)", abs(j["tempo_medio"] - 4.8) < 1e-9, j["tempo_medio"])
checar("quarteirões sem repetir e em ordem natural", j["quarteiroes_lista"] == "Q1, Q2, Q10" and j["qtd_quarteiroes"] == 3, j["quarteiroes_lista"])
checar("agentes da área do que mais abriu para o que menos abriu", [a["agente"] for a in j["agentes"]] == ["Ana", "Bia"], [a["agente"] for a in j["agentes"]])
checar("conta de agentes", j["n_agentes"] == 2, j["n_agentes"])
checar("alerta reclassificado pelo total: 14% = ATENÇÃO", "ATENÇÃO" in j["alerta"], j["alerta"])
checar("área com 50% de rápidas = CRÍTICO", "CRÍTICO" in G["400 - CENTRO"]["alerta"], G["400 - CENTRO"]["alerta"])
v = G["410 - VILA"]
checar("área vazia (NaN) não quebra: zeros e NORMAL", (v["abertos"], v["pct_rapidas"], v["tempo_medio"], v["qtd_quarteiroes"]) == (0, 0, 0, 0) and "NORMAL" in v["alerta"], v)
checar("áreas do maior para o menor % de rápidas", [g["area"] for g in GD.build_areas_agrupadas(REGS)][:2] == ["400 - CENTRO", "435 - JARDIM PRIMOR"])

# as faixas do gerador precisam ser as mesmas da regra oficial (o gerador não importa o pacote `coleta`)
fonte = open(os.path.join(AQUI, "coleta", "parametros.py"), encoding="utf-8").read()
ok_ate = re.search(r"^PCT_RAPIDAS_OK_ATE\s*=\s*(\d+)", fonte, re.M)
atencao_ate = re.search(r"^PCT_RAPIDAS_ATENCAO_ATE\s*=\s*(\d+)", fonte, re.M)
checar("faixas iguais às de coleta/parametros.py",
       bool(ok_ate and atencao_ate) and (int(ok_ate.group(1)), int(atencao_ate.group(1))) == (GD.PCT_RAPIDAS_OK_ATE, GD.PCT_RAPIDAS_ATENCAO_ATE),
       (ok_ate and ok_ate.group(1), atencao_ate and atencao_ate.group(1), GD.PCT_RAPIDAS_OK_ATE, GD.PCT_RAPIDAS_ATENCAO_ATE))

if falhas:
    print(f"\n❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("\nTodos os testes de áreas agrupadas passaram.")
