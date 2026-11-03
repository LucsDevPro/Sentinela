# -*- coding: utf-8 -*-
"""Testes: presença mínima (nota proporcional), rótulo neutro nos dados
públicos e dia em andamento. Usa o cache real (data/semanas/326.xlsx)."""
import json
import os
import sys
from datetime import date

os.environ.setdefault("EVISITA_CPF", "teste")
os.environ.setdefault("EVISITA_SENHA", "teste")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import coletar_evisita as C  # noqa: E402

FALHAS = []


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


if not os.path.exists("data/semanas/326.xlsx"):
    print("sem cache de teste — pulado")
    sys.exit(0)

df_total, resultados, _ = C._montar_df_total_e_resultados([326])
res = max(resultados, key=lambda r: r["resumo"]["dias_trabalhados"])
d = res["resumo"]["dias_trabalhados"]

# --- Presença mínima ---------------------------------------------------------
p_base, _, _, _ = C.calcular_pontuacao(res, 0, d, normalizar_periodo=False)
p_ok, _, _, det_ok = C.calcular_pontuacao(res, 0, d, normalizar_periodo=False, aplicar_presenca_minima=True)
check(p_ok == p_base and not any("Presença" in x["motivo"] for x in det_ok),
      "Presença 100%: nota não muda e não aparece linha de presença")
p_meio, _, _, _ = C.calcular_pontuacao(res, 0, d * 2, normalizar_periodo=False, aplicar_presenca_minima=True)
p_meio0, _, _, _ = C.calcular_pontuacao(res, 0, d * 2, normalizar_periodo=False)
check(p_meio == p_meio0, "Presença exatamente no mínimo (50%): sem redução")
p_baixa, _, _, det_b = C.calcular_pontuacao(res, 0, d * 4, normalizar_periodo=False, aplicar_presenca_minima=True)
p_baixa0, _, _, _ = C.calcular_pontuacao(res, 0, d * 4, normalizar_periodo=False)
check(abs(p_baixa - round(min(p_baixa0, 100) * 0.5, 2)) < 0.02,
      f"Presença 25%: nota proporcional (×0,5): {p_baixa0} → {p_baixa}")
lin = [x for x in det_b if "Presença" in x["motivo"]]
check(len(lin) == 1 and lin[0]["pontos"] < 0 and "25%" in lin[0]["motivo"], "Presença baixa: linha explicativa no detalhamento")
p_ant, _, _, det_ant = C.calcular_pontuacao(res, 0, d * 4, normalizar_periodo=True, aplicar_presenca_minima=True)
check(not any("Presença" in x["motivo"] for x in det_ant), "Método antigo (meses até Setembro/Acumulado): presença mínima não se aplica")

# sob demanda não sofre; agente normal sofre (via _preparar_ranking)
C.HOJE_OVERRIDE = date(2027, 1, 1)
def rodar_equipe(nome_equipe):
    rs = [dict(r, equipe=nome_equipe) if r is res else r for r in resultados]
    # período de 4 semanas fictício: poucos dias trabalhados / muitos esperados
    princ, det = C._preparar_ranking(rs, [], date(2026, 10, 30), None, date(2026, 10, 4))
    return [x for x in det if x["nome_agente"] == res["nome_agente"] and "Presença" in x["motivo"]]
check(len(rodar_equipe(res["equipe"] if res["equipe"] not in C.EQUIPES_SEM_DETECCAO_AUTOMATICA else "Equipe 1")) >= 0, "ranking roda")
check(rodar_equipe("Equipe Bloqueio") == [], "Equipe sob demanda não recebe redução por presença")

# --- Rótulo neutro -------------------------------------------------------------
check(C._motivo_neutro("Atestado") == "Ausência justificada", "'Atestado' vira 'Ausência justificada'")
check(C._motivo_neutro("Férias/Atestado (automático)") == "Férias (automático)", "'Férias/Atestado' vira 'Férias'")
check(C._motivo_neutro("Meio atestado") == "Meia ausência justificada", "'Meio atestado' vira 'Meia ausência justificada'")
check(C._motivo_neutro("Folga") == "Folga", "Outros motivos não mudam")
for arq in ("data/deteccoes_pendentes.json", "data/cronograma_ausencias.json"):
    txt = open(arq, encoding="utf-8").read()
    check("Atestado" not in txt and "atestado" not in txt.lower().replace("ausência justificada", ""),
          f"{arq}: nenhuma menção a atestado")

# --- Dia em andamento ----------------------------------------------------------
dias_dados = sorted(set(df_total["dia"]))
ultimo = dias_dados[-1]
C.HOJE_OVERRIDE = date(2027, 1, 1)
todas = C._preparar_ausencias(df_total, resultados, [], primeira_visita={})
C.HOJE_OVERRIDE = ultimo
parciais = C._preparar_ausencias(df_total, resultados, [], primeira_visita={})
dia_ult = ultimo.strftime("%d/%m/%Y")
check(len(todas) >= len(parciais), "referência calculada")
check(all(r["dia_fmt"] != dia_ult for r in parciais), "Dia em andamento: nenhuma ausência gerada para hoje")
check(len(parciais) <= len(todas), "Sem o dia corrente nunca há mais ausências")
# dias esperados: quem não visitou hoje não deve o dia de hoje
sem_visita_hoje = [r for r in resultados if ultimo not in set(r["df"]["dia"])]
if sem_visita_hoje:
    ini = date(2026, 9, 27)
    C.HOJE_OVERRIDE = date(2027, 1, 1)
    # usa método novo fictício com período de outubro para ter o branch novo
    princ_a, _ = C._preparar_ranking(resultados, [], date(2026, 10, 9), None, date(2026, 10, 4))
    C.HOJE_OVERRIDE = date(2026, 10, 9)
    princ_b, _ = C._preparar_ranking(resultados, [], date(2026, 10, 9), None, date(2026, 10, 4))
    ea = {r["nome_agente"]: r["dias_uteis_esperados"] for r in princ_a}
    eb = {r["nome_agente"]: r["dias_uteis_esperados"] for r in princ_b}
    check(all(eb[n] == ea[n] - 1 for n in ea if ultimo.__class__ and n in eb and not any(
        date(2026, 10, 9) in set(x["df"]["dia"]) for x in resultados if x["nome_agente"] == n)),
        "Dia em andamento: quem ainda não visitou hoje tem 1 dia esperado a menos")
C.HOJE_OVERRIDE = None

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes de regras passaram.")
