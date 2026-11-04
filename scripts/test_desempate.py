# -*- coding: utf-8 -*-
"""Desempate do ranking pela média dos meses anteriores (coleta/ausencias_ranking._media_historica_por_agente)."""
import json, os, sys, tempfile
from datetime import date
os.environ.setdefault("EVISITA_CPF", "teste")
os.environ.setdefault("EVISITA_SENHA", "teste")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import openpyxl
import coletar_evisita as C  # noqa: F401  (carrega o pacote coleta)
from coleta import ausencias_ranking as R

falhas = []


def checar(nome, ok, extra=""):
    print(("✔ " if ok else "✘ ") + nome + (f"  [{extra}]" if extra and not ok else ""))
    if not ok:
        falhas.append(nome)


def planilha(caminho, notas):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Ranking"
    ws.cell(row=1, column=1, value="RANKING")
    for c, t in enumerate(["Posição", "Agente", "Equipe", "Dias Trabalhados", "Dias Úteis Esperados no Mês",
                           "Turnos Sem Trabalhar", "Pontuação Final", "Classificação"], 1):
        ws.cell(row=2, column=c, value=t)
    for i, (n, p) in enumerate(notas.items(), 1):
        for c, v in enumerate([i, n, "Equipe 1", 10, 10, 0, p, "x"], 1):
            ws.cell(row=2 + i, column=c, value=v)
    wb.save(caminho)


with tempfile.TemporaryDirectory() as d:
    planilha(os.path.join(d, "ago.xlsx"), {"Ana": 90.0, "Bia": 70.0, "Caio": 60.0})
    planilha(os.path.join(d, "set.xlsx"), {"Ana": 80.0, "Bia": 100.0})
    planilha(os.path.join(d, "out.xlsx"), {"Ana": 100.0, "Bia": 100.0, "Caio": 100.0})   # mês do próprio período: NÃO entra
    man = os.path.join(d, "manifest.json")
    with open(man, "w") as f:
        json.dump([{"arquivo": "ago.xlsx", "label": "Agosto/2026", "semana_inicio": 318, "semana_fim": 321},
                   {"arquivo": "set.xlsx", "label": "Setembro/2026", "semana_inicio": 322, "semana_fim": 326},
                   {"arquivo": "out.xlsx", "label": "Outubro/2026", "semana_inicio": 327, "semana_fim": 330},
                   {"arquivo": "s.xlsx", "label": "Semana 330", "tipo": "semana", "semana_inicio": 330, "semana_fim": 330}], f)
    m = R._media_historica_por_agente(date(2026, 10, 4), manifest=man, pasta=d)
    checar("média de Ana = (90+80)/2, sem contar Outubro", abs(m.get("Ana", 0) - 85) < 1e-9, str(m))
    checar("média de Bia = (70+100)/2", abs(m.get("Bia", 0) - 85) < 1e-9, str(m))
    checar("Caio só tem Agosto (60)", abs(m.get("Caio", 0) - 60) < 1e-9, str(m))
    m2 = R._media_historica_por_agente(date(2026, 9, 6), manifest=man, pasta=d)   # período de Setembro: só Agosto vale
    checar("para Setembro, só Agosto conta", abs(m2.get("Ana", 0) - 90) < 1e-9 and abs(m2.get("Bia", 0) - 70) < 1e-9, str(m2))
checar("sem data não quebra", R._media_historica_por_agente(None) == {})
checar("manifesto inexistente não quebra", R._media_historica_por_agente(date(2026, 10, 4), manifest="/nao/existe.json") == {})
print("❌ falhou: " + ", ".join(falhas) if falhas else "✅ desempate: tudo certo")
sys.exit(1 if falhas else 0)
