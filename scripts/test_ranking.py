# -*- coding: utf-8 -*-
"""
Testes do ranking SEM fator de normalização (Outubro/2026 em diante) e da
garantia de que os períodos anteriores NÃO mudaram.

Usa o cache real de uma semana (data/semanas/326.xlsx) como massa de teste,
passando datas de período fictícias pra _preparar_ranking — não faz nenhuma
requisição ao e-Visita. Uso: python3 scripts/test_ranking.py
"""
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
    print("data/semanas/326.xlsx não existe — testes de ranking pulados.")
    sys.exit(0)

_, resultados, _ = C._montar_df_total_e_resultados([326])
# o agente com MENOS dias trabalhados é o caso mais sensível ao fator
resultados = sorted(resultados, key=lambda r: r["resumo"]["dias_trabalhados"])
alvo = resultados[0]
outro = resultados[-1]
check(alvo["resumo"]["dias_trabalhados"] < outro["resumo"]["dias_trabalhados"] or len(resultados) == 1,
      "massa de teste tem agentes com dias trabalhados diferentes")

NOVO = (date(2026, 10, 5), date(2026, 10, 30))      # Outubro: ranking novo
ANTIGO = (date(2026, 9, 1), date(2026, 9, 30))       # Setembro: ranking antigo
FERIAS = [{"alvo": "agente", "id_agente": alvo["id_agente"], "inicio": "12/10/2026",
           "fim": "23/10/2026", "motivo": "Férias"}]
dias_ferias = len(C._dias_uteis_no_intervalo(date(2026, 10, 12), date(2026, 10, 23)))  # 12/10 é feriado


def rodar(periodo, cronograma):
    return C._preparar_ranking(resultados, [], periodo[1], cronograma, periodo[0])


def por_agente(principal):
    return {r["nome_agente"]: r for r in principal}


# --- Outubro: sem fator, peso efetivo = nominal -----------------------------
princ, det = rodar(NOVO, [])
check(all(d["fator_normalizacao"] == 1.0 and d["peso"] == d["peso_nominal"] for d in det),
      "Outubro: fator = 1,0 e peso efetivo = peso nominal em TODOS os critérios")
for r in princ:
    soma = C.PONTOS_INICIAIS + sum(d["pontos"] for d in det if d["nome_agente"] == r["nome_agente"])
    esperado = max(min(soma, C.NOTA_MAXIMA), C.NOTA_MINIMA)
    if abs(esperado - r["pontos"]) > 0.02:
        check(False, f"Outubro: pontos de {r['nome_agente']} = 100 + Σ(qtd × peso) ({esperado} ≠ {r['pontos']})")
        break
else:
    check(True, "Outubro: pontos = 100 + Σ(quantidade × peso nominal) para todos os agentes")
for d in det:
    if abs(d["qtd"] * d["peso_nominal"] * (-1 if d["pontos"] < 0 else 1) - d["pontos"]) > 0.011 and d["pontos"] != 0:
        check(False, f"Outubro: quantidade × peso = pontos ({d['motivo']}: {d['qtd']} × {d['peso_nominal']} ≠ {d['pontos']})")
        break
else:
    check(True, "Outubro: quantidade × peso = pontos aplicados em cada linha do detalhamento")

# --- Outubro: esperado = dias úteis do PRÓPRIO período (04/10 a 30/10) ---------
base_out = len(C._dias_uteis_no_intervalo(date(2026, 10, 4), date(2026, 10, 30)))
check(all(r["dias_uteis_esperados"] == base_out for r in princ),
      f"Outubro: dias úteis esperados = {base_out} (04/10 a 30/10 — sem 01 e 02/10, que são de Setembro, e sem o feriado de 12/10)")
check(base_out == 19, "Outubro/2026 tem 19 dias úteis esperados (20 dias úteis menos o feriado de 12/10)")

# --- Outubro: férias reduzem os dias esperados ------------------------------
princ_f, det_f = rodar(NOVO, FERIAS)
a, af = por_agente(princ), por_agente(princ_f)
nome = alvo["nome_agente"]
check(af[nome]["dias_uteis_esperados"] == a[nome]["dias_uteis_esperados"] - dias_ferias,
      f"Outubro: agente de férias ({dias_ferias} dias úteis) tem {dias_ferias} dia(s) úteis esperados a menos "
      f"({a[nome]['dias_uteis_esperados']} → {af[nome]['dias_uteis_esperados']})")
check(all(af[n]["dias_uteis_esperados"] == a[n]["dias_uteis_esperados"] for n in a if n != nome),
      "Outubro: férias de um agente não mexem nos dias esperados dos outros")
check(af[nome]["pontos"] == a[nome]["pontos"],
      "Outubro: férias só ajustam os dias esperados — pontuação do agente não muda por causa do fator")

# --- Setembro (e anteriores): método antigo preservado ----------------------
princ_a, det_a = rodar(ANTIGO, [])
princ_af, _ = rodar(ANTIGO, FERIAS)
check(any(abs(d["fator_normalizacao"] - 1.0) > 1e-9 for d in det_a),
      "Setembro: continua usando o fator de normalização")
check(por_agente(princ_a)[nome]["dias_uteis_esperados"] == por_agente(princ_af)[nome]["dias_uteis_esperados"]
      and por_agente(princ_a)[nome]["pontos"] == por_agente(princ_af)[nome]["pontos"],
      "Setembro: cálculo antigo inalterado (mesmos dias esperados e pontos)")

# --- Chave geral: desligar volta tudo ao método antigo ----------------------
guardado = C.RANKING_SEM_NORMALIZACAO_A_PARTIR_DE
C.RANKING_SEM_NORMALIZACAO_A_PARTIR_DE = None
_, det_off = rodar(NOVO, [])
C.RANKING_SEM_NORMALIZACAO_A_PARTIR_DE = guardado
check(any(abs(d["fator_normalizacao"] - 1.0) > 1e-9 for d in det_off),
      "RANKING_SEM_NORMALIZACAO_A_PARTIR_DE = None volta ao método antigo")


# --- Bônus proporcional (método novo) ----------------------------------------
import copy
def _agente_sintetico(dias_trab):
    r = copy.deepcopy(alvo)
    r["resumo"]["dias_trabalhados"] = dias_trab
    r["resumo"]["dias_atingiu_meta"] = min(dias_trab, r["resumo"].get("dias_atingiu_meta", 0))
    r["resumo"]["visitas_rapidas"] = 0
    r["resumo"]["total_visitas"] = max(r["resumo"].get("total_visitas", 1), 1)
    return r

def _bonus(det):
    return [d for d in det if d["motivo"].startswith("Bônus") and d["pontos"] > 0]

_, _, _, det_poucos = C.calcular_pontuacao(_agente_sintetico(4), 0, 20, normalizar_periodo=False)
_, _, _, det_muitos = C.calcular_pontuacao(_agente_sintetico(12), 0, 20, normalizar_periodo=False)
_, _, _, det_antigo = C.calcular_pontuacao(_agente_sintetico(4), 0, 20, normalizar_periodo=True)
check(not _bonus(det_poucos), "Bônus: 4 de 20 dias esperados (<50%) — nenhum bônus concedido")
check(any("Bônus não concedido" in d["motivo"] for d in det_poucos), "Bônus: detalhamento explica por que o bônus não veio")
check(len(_bonus(det_muitos)) >= 2, "Bônus: 12 de 20 dias esperados (>=50%) — bônus concedidos")
check(len(_bonus(det_antigo)) >= 2, "Método antigo: bônus continuam sem a regra de 50% (nada mudou nos meses anteriores)")

# --- Observação: possível afastamento não registrado --------------------------
dias_out = C._dias_uteis_no_intervalo(date(2026, 10, 4), date(2026, 10, 30))
sint = _agente_sintetico(6)
obs = C._observacao_ranking(sint, 8, dias_out, 20, True, [], date(2026, 10, 5), date(2026, 10, 30))
check("Possível afastamento" in obs and "6 de 20" in obs, "Observação: 6 de 20 dias e 8 turnos sem lançamento gera aviso")
check(C._observacao_ranking(_agente_sintetico(19), 8, dias_out, 20, True, [], date(2026, 10, 5), date(2026, 10, 30)) == "",
      "Observação: quem trabalhou quase tudo não recebe aviso")
check(C._observacao_ranking(sint, 1, dias_out, 20, True, [], date(2026, 10, 5), date(2026, 10, 30)) == "",
      "Observação: poucos turnos sem lançamento não geram aviso")
check(C._observacao_ranking(sint, 8, dias_out, 20, False, [], date(2026, 5, 4), date(2026, 10, 2)) == "",
      "Observação: não aparece em períodos longos (Acumulado)")

# --- Feriados nacionais: valem de Julho/2026 em diante ---------------------
check(date(2026, 5, 1).weekday() == 4 and len(C._dias_uteis_no_intervalo(date(2026, 5, 1), date(2026, 5, 1))) == 1,
      "Feriados: 01/05/2026 (antes de Julho) NÃO é descontado — meses anteriores inalterados")
check(len(C._dias_uteis_do_mes_civil(date(2026, 7, 1))) == 23 and len(C._dias_uteis_do_mes_civil(date(2026, 8, 1))) == 21,
      "Feriados: Julho (23) e Agosto (21) não têm feriado nacional — contagem igual à de antes")
for f in ("07/09/2026", "12/10/2026", "02/11/2026", "20/11/2026", "25/12/2026"):
    dia = date(int(f[6:]), int(f[3:5]), int(f[:2]))
    check(dia.weekday() < 5 and dia not in C._dias_uteis_no_intervalo(dia, dia),
          f"Feriado {f} sai dos dias úteis")
check(len(C._dias_uteis_do_mes_civil(date(2026, 9, 1))) == 21, "Setembro/2026 tem 21 dias úteis (22 menos 07/09)")
nov = len(C._dias_uteis_no_intervalo(date(2026, 11, 1), date(2026, 11, 28)))
check(nov == 18, f"Novembro/2026 (01/11 a 28/11): 20 dias úteis menos Finados (02/11) e Consciência Negra (20/11) = {nov}")

# --- Dias esperados de Setembro (período que atravessa a virada) --------------
set_civil = C._dias_uteis_do_mes_civil(date(2026, 9, 1))
check(C._dias_uteis_alvo_periodo(date(2026, 8, 31), date(2026, 10, 2)) == set_civil,
      f"Setembro (31/08 a 02/10): alvo = dias úteis de Setembro ({len(set_civil)}), não de Outubro")
check(C._dias_uteis_alvo_periodo(date(2026, 6, 29), date(2026, 7, 31)) == C._dias_uteis_do_mes_civil(date(2026, 7, 1)),
      "Julho (29/06 a 31/07): alvo continua sendo Julho")
check(C._dias_uteis_alvo_periodo(date(2026, 5, 4), date(2026, 10, 2)) == C._dias_uteis_do_mes_civil(date(2026, 10, 1)),
      "Acumulado: alvo continua o do mês do último dia (como sempre foi)")

# --- Ajustes manuais (data/ajustes_ranking.json) --------------------------------
_, _, _, det_sem = C.calcular_pontuacao(_agente_sintetico(4), 0, 20, normalizar_periodo=False)
p_sem = C.calcular_pontuacao(_agente_sintetico(4), 0, 20, normalizar_periodo=False)[0]
p_aj, _, _, det_aj = C.calcular_pontuacao(_agente_sintetico(4), 0, 20, normalizar_periodo=False,
                                           ajustes=[("falha do e-Visita", 2.0), ("lançamento duplicado", -1.5)])
check(abs((p_aj - p_sem) - 0.5) < 0.011 or p_sem >= 99.5,
      f"Ajuste manual: +2,0 e −1,5 mudam a pontuação em +0,5 ({p_sem} → {p_aj})")
linhas_aj = [d for d in det_aj if d["motivo"].startswith("Ajuste manual:")]
check(len(linhas_aj) == 2 and {d["pontos"] for d in linhas_aj} == {2.0, -1.5},
      "Ajuste manual: cada ajuste vira uma linha própria no Detalhamento/Extrato, com o motivo")
check(all(d["fator_normalizacao"] == 1.0 for d in linhas_aj), "Ajuste manual: nunca é normalizado")
ajuste = [{"id_agente": alvo["id_agente"], "data": date(2026, 10, 15), "pontos": -3.0, "motivo": "teste"}]
base_p, _ = C._preparar_ranking(resultados, [], NOVO[1], [], NOVO[0], ajustes=[])
com_p, com_d = C._preparar_ranking(resultados, [], NOVO[1], [], NOVO[0], ajustes=ajuste)
fora_p, _ = C._preparar_ranking(resultados, [], NOVO[1], [], NOVO[0],
                                ajustes=[{**ajuste[0], "data": date(2026, 9, 15)}])
nome = alvo["nome_agente"]
b, c, f = por_agente(base_p), por_agente(com_p), por_agente(fora_p)
check(c[nome]["pontos"] <= b[nome]["pontos"] and (c[nome]["pontos"] < b[nome]["pontos"] or b[nome]["pontos"] <= 3),
      "Ajuste manual no período: pontuação do agente muda")
check(all(c[n]["pontos"] == b[n]["pontos"] for n in b if n != nome), "Ajuste manual: outros agentes não mudam")
check(f[nome]["pontos"] == b[nome]["pontos"], "Ajuste manual com data fora do período não é aplicado")
check(any(d["nome_agente"] == nome and d["motivo"] == "Ajuste manual: teste" for d in com_d),
      "Ajuste manual aparece no detalhamento do agente")
import json, tempfile
with tempfile.TemporaryDirectory() as tmp:
    ok_f = os.path.join(tmp, "aj.json")
    with open(ok_f, "w", encoding="utf-8") as fh:
        json.dump([{"id_agente": 116, "data": "15/10/2026", "pontos": 2, "motivo": "ok"},
                   {"id_agente": "x", "data": "2026-10-15", "pontos": 2, "motivo": "data errada"},
                   {"id_agente": 5, "data": "16/10/2026", "pontos": 1}], fh)
    check(len(C._carregar_ajustes_ranking(ok_f)) == 1, "Ajustes inválidos (id, data ou motivo ruins) são ignorados; o válido fica")
import validar_json as VJ
check(len(VJ.validar_ajustes([{"id_agente": 1, "data": "31/12/2026", "pontos": -1, "motivo": "x"}])) == 0
      and len(VJ.validar_ajustes([{"id_agente": 1, "data": "2026-12-31", "pontos": -1, "motivo": "x"}])) == 1
      and len(VJ.validar_ajustes({"a": 1})) == 1, "validar_json barra ajuste com formato errado")

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes de ranking passaram.")
