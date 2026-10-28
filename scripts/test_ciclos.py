# -*- coding: utf-8 -*-
"""Testes da conferência de ciclos (validar_ciclos.py) e do resumo da coleta
no GitHub Actions. Sem rede. Uso: python3 scripts/test_ciclos.py"""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validar_ciclos as V  # noqa: E402
import coletar_evisita as C  # noqa: E402

FALHAS = []


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


erros, avisos = V.conferir(date(2026, 10, 26))
check(not erros and not avisos, "26/10/2026: Outubro e Novembro cadastrados — sem erro e sem aviso")
erros, avisos = V.conferir(date(2026, 11, 10))
check(not erros and any("Semana 335" in a for a in avisos), "10/11/2026: só avisa que Dezembro (semana 335) ainda não tem ciclo")
erros, avisos = V.conferir(date(2026, 11, 30))
check(any("Semana 335" in e for e in erros), "30/11/2026: semana 335 já começou sem ciclo — ERRO (falharia o workflow)")

# resumo da coleta no GitHub
with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tmp:
    caminho = tmp.name
os.environ["GITHUB_STEP_SUMMARY"] = caminho
C._resumo_github([327], [{"html_id": 327, "agentes_ausentes": [(1938, "Equipe 3", "falha ao coletar página 1")],
                          "agentes_incompletos": [("Fulano", "Equipe 1", [3])], "total_agentes": 40}])
texto = open(caminho, encoding="utf-8").read()
check("1938" in texto and "Fulano" in texto and "mantidos" in texto, "resumo do GitHub lista agente ausente, páginas faltando e aviso de dados mantidos")
open(caminho, "w").close()
C._resumo_github([327], [{"html_id": 327, "agentes_ausentes": [], "agentes_incompletos": [], "total_agentes": 40}])
check("íntegra" in open(caminho, encoding="utf-8").read(), "resumo do GitHub confirma coleta íntegra")
os.unlink(caminho)

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes de ciclos passaram.")
