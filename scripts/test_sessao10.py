# -*- coding: utf-8 -*-
"""Testes da Sessão 10 (sem navegador): paradas na linha do tempo do agente, dados públicos, ícones novos."""
import json, os, sys, tempfile, shutil
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import gerar_agentes as G
import icones
from datetime import date
FALHAS = []
def checar(n, c, d=""):
    print(f"[{'OK  ' if c else 'FALHOU'}] {n}" + (f" — {d}" if not c and d else ""))
    if not c: FALHAS.append(n)

cron = [{"alvo": "todos", "motivo": "Recuperação de Casas", "inicio": "28/07/2026", "fim": "31/07/2026"},
        {"alvo": "equipe", "equipe": "Equipe 1", "motivo": "Chuva", "inicio": "05/10/2026", "fim": "06/10/2026"},
        {"alvo": "equipe", "equipe": "Equipe 2", "motivo": "Reunião", "inicio": "05/10/2026", "fim": "05/10/2026"},
        {"alvo": "agente", "motivo": "Qualquer", "inicio": "01/10/2026", "fim": "30/10/2026"},
        {"alvo": "todos", "motivo": "Data ruim", "inicio": "xx", "fim": "yy"}]
checar("faixa do mês", G._faixa_mes("Outubro/2026") == (date(2026, 10, 1), date(2026, 10, 31)))
checar("faixa de dezembro vira o ano", G._faixa_mes("Dezembro/2026") == (date(2026, 12, 1), date(2026, 12, 31)))
checar("mês com acento/ç (Março)", G._faixa_mes("Março/2026") == (date(2026, 3, 1), date(2026, 3, 31)))
checar("faixa da semana", G._faixa_semana("Outubro/2026", "04/10 a 10/10") == (date(2026, 10, 4), date(2026, 10, 10)))
checar("faixa inválida vira None", G._faixa_semana("Outubro/2026", "???") is None and G._faixa_mes("Lixo") is None)
p1 = G.paradas_no_periodo(cron, "Equipe 1", G._faixa_mes("Outubro/2026"))
checar("equipe 1 vê só a própria parada e ignora alvo desconhecido/datas ruins", p1 == [{"motivo": "Chuva", "dias": 2}], str(p1))
checar("parada de 'todos' vale para qualquer equipe", G.paradas_no_periodo(cron, "Equipe 9", G._faixa_mes("Julho/2026")) == [{"motivo": "Recuperação de Casas", "dias": 4}])
checar("parada que começa antes do período conta só os dias dentro", G.paradas_no_periodo([{"alvo": "todos", "motivo": "X", "inicio": "28/09/2026", "fim": "02/10/2026"}], "E", G._faixa_mes("Outubro/2026")) == [{"motivo": "X", "dias": 2}])
checar("período sem parada devolve lista vazia", G.paradas_no_periodo(cron, "Equipe 1", G._faixa_mes("Maio/2026")) == [])
checar("sem faixa devolve vazio", G.paradas_no_periodo(cron, "Equipe 1", None) == [])

d = G.gerar()
a = next(iter(d["agentes"].values()))
checar("cada mês e cada semana trazem 'paradas'", all("paradas" in m for m in a["meses"]) and all("paradas" in s for s in a["semanas"]))
txt = json.dumps(d, ensure_ascii=False).lower()
checar("dados públicos sem palavras de saúde", not any(w in txt for w in ("atestado", "cid", "diagnóstico", "diagnostico", "doença", "doenca", "médico", "medico")))
for n in ("compare", "arrow-up", "arrow-down", "minus", "timeline", "cone"):
    checar(f"ícone '{n}' existe", n in icones.ICONES)
checar("🔁 vira ícone de comparar", "#i-compare" in icones.iconizar("<b>🔁 Comparar</b>"))
print("\n" + ("TUDO CERTO" if not FALHAS else f"{len(FALHAS)} FALHA(S): {FALHAS}"))
sys.exit(1 if FALHAS else 0)
