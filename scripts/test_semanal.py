# -*- coding: utf-8 -*-
"""Testes das visões semanais do mês vigente (barra de navegação, semana
parcial e congelamento junto com o mês arquivado)."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("EVISITA_CPF", "teste")
os.environ.setdefault("EVISITA_SENHA", "teste")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.argv = ["x"]
import coletar_evisita as C  # noqa: E402
import generate_dashboard as G  # noqa: E402

FALHAS = []


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


# --- congelamento: semana de mês arquivado vira "manual" ------------------------
with tempfile.TemporaryDirectory() as tmp:
    hist = os.path.join(tmp, "historico")
    os.makedirs(hist)
    Path(hist, "semana_324.xlsx").write_bytes(b"x")
    Path(hist, "semana_331.xlsx").write_bytes(b"x")
    antigo = [
        {"arquivo": "semanas_322-326.xlsx", "label": "Setembro/2026", "origem": "manual"},
        {"arquivo": "semana_324.xlsx", "tipo": "semana", "mes": "Setembro/2026", "origem": "cache", "semana_inicio": 324, "parcial": True},
        {"arquivo": "semana_331.xlsx", "tipo": "semana", "mes": "Novembro/2026", "origem": "cache", "semana_inicio": 331, "parcial": True},
    ]
    json.dump(antigo, open(os.path.join(hist, "manifest.json"), "w"))
    C.atualizar_historico_do_cache(pasta_semanas=os.path.join(tmp, "vazio"), pasta_historico=hist,
                                   pasta_saida_tmp=os.path.join(tmp, "t"))
    novo = {e["arquivo"]: e for e in json.load(open(os.path.join(hist, "manifest.json")))}
    check(novo["semana_324.xlsx"]["origem"] == "manual" and novo["semana_324.xlsx"]["parcial"] is False,
          "Semana de mês arquivado (Setembro) é congelada: origem manual, sem 'parcial'")
    check("semana_331.xlsx" not in novo, "Semana de mês aberto sem cache não vira manual")

# --- barra de navegação ------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "data" / "historico").mkdir(parents=True)
    (root / "historico").mkdir()
    manifest = [
        {"arquivo": "semanas_322-326.xlsx", "label": "Setembro/2026", "origem": "manual"},
        {"arquivo": "semanas_327-330.xlsx", "label": "Outubro/2026", "origem": "cache"},
        {"arquivo": "semana_327.xlsx", "tipo": "semana", "mes": "Outubro/2026", "label": "Outubro/2026 · Semana 1",
         "numero_semana": 1, "periodo": "04/10 a 10/10", "parcial": False, "origem": "cache"},
        {"arquivo": "semana_328.xlsx", "tipo": "semana", "mes": "Outubro/2026", "label": "Outubro/2026 · Semana 2",
         "numero_semana": 2, "periodo": "11/10 a 17/10", "parcial": True, "origem": "cache"},
    ]
    (root / "data" / "historico" / "manifest.json").write_text(json.dumps(manifest))
    (root / "data" / "config_home.json").write_text(json.dumps({"arquivo": "data/historico/semanas_327-330.xlsx", "label": "Outubro/2026"}))
    (root / "index.html").write_text("x")
    G.ROOT, G.CONFIG_HOME_PATH = root, root / "data" / "config_home.json"

    G.OUT_PATH = root / "historico" / "semana_328.html"
    nav, pag = G.carregar_nav_semanas()
    check(nav and [i["label"] for i in nav["itens"]] == ["Semana 1", "Semana 2", "Mês completo"], "Barra: Semana 1 | Semana 2 | Mês completo")
    check(pag and pag["numero"] == 2 and pag["parcial"], "Página da semana 2: marcada como parcial")
    check([i["atual"] for i in nav["itens"]] == [False, True, False], "Barra marca a semana atual")
    check(nav["itens"][-1]["href"] == "semanas_327-330.html", "Semana → 'Mês completo' aponta para a página do mês")

    G.OUT_PATH = root / "index.html"
    nav, pag = G.carregar_nav_semanas()
    check(nav and pag is None and nav["itens"][-1]["atual"] and nav["itens"][-1]["href"] == "index.html",
          "Home (Outubro): barra aparece, 'Mês completo' é a própria home")
    check(nav["itens"][0]["href"] == "historico/semana_327.html", "Home: links das semanas relativos à raiz")

    G.OUT_PATH = root / "historico" / "semanas_322-326.html"
    nav, pag = G.carregar_nav_semanas()
    check(nav is None and pag is None, "Mês arquivado sem semanas: sem barra")

    G.OUT_PATH = root / "acumulado.html"
    check(G.carregar_nav_semanas() == (None, None), "Acumulado: sem barra")
    G.OUT_PATH = root / "historico" / "semana_328.html"
    check(all("Semana" not in p["label"] for p in G.carregar_periodos()), "Seletor de período não lista semanas")

# --- selo "período em andamento": sexta final do período, só enquanto hoje <= essa sexta
from datetime import date, timedelta  # noqa: E402
_fim = 330                                        # última semana oficial de Outubro/2026
_sexta = G.sem_evisita.data_fim_semana_html(_fim) - timedelta(days=1)
check(_sexta.weekday() == 4, f"a data final do período é uma sexta-feira ({_sexta})")
check(G.periodo_em_andamento(_fim, _sexta - timedelta(days=10)) == _sexta, "antes do fim: período em andamento, devolve a sexta final")
check(G.periodo_em_andamento(_fim, _sexta) == _sexta, "no próprio dia da sexta final ainda é 'em andamento'")
check(G.periodo_em_andamento(_fim, _sexta + timedelta(days=1)) is None, "depois da sexta final: período fechado, sem selo")
check(G.periodo_em_andamento(None, date(2026, 1, 1)) is None and G.periodo_em_andamento(0, date(2026, 1, 1)) is None, "sem semana_fim: sem selo")

# --- agrupar_cronograma_por_dia: cada dia vira um grupo, em ordem cronológica (não alfabética)
_rows = [
    dict(periodo="05/10/2026", motivo="Chuva", quem="Equipe 2", auto=False),
    dict(periodo="30/09/2026", motivo="Nenhum agente da equipe registrou visita neste turno", quem="Todos da Equipe 1 (9/9)", auto=True),
    dict(periodo="05/10/2026", motivo="Reunião/Treinamento", quem="Equipe 3", auto=False),
    dict(periodo="22/09/2026 a 25/09/2026", motivo="Férias", quem="Fulano", auto=False),
    dict(periodo="05/10/2026", motivo="Chuva", quem="Equipe 4", auto=False),
    dict(periodo="não é data", motivo="X", quem="Y", auto=False),
]
_g = G.agrupar_cronograma_por_dia(_rows)
check([x["titulo"] for x in _g][:3] == ["22/09/2026 a 25/09/2026", "Qua 30/09/2026", "Seg 05/10/2026"], f"grupos em ordem cronológica, com o dia da semana: {[x['titulo'] for x in _g]}")
check(_g[-1]["titulo"] == "não é data", "linha com data ilegível vai para o fim, sem quebrar")
_d5 = next(x for x in _g if x["titulo"].endswith("05/10/2026"))
check(_d5["n"] == 3 and _d5["motivos"] == ["Chuva", "Reunião/Treinamento"], f"mesmo dia agrupa as 3 linhas e não repete motivo: {_d5['motivos']}")
check(next(x for x in _g if x["titulo"].startswith("Qua"))["motivos"] == ["Equipe parada (auto)"] and next(x for x in _g if x["titulo"].startswith("Qua"))["auto_n"] == 1, "paralisação automática aparece como 'Equipe parada (auto)'")
check(G.agrupar_cronograma_por_dia([]) == [], "sem linhas -> sem grupos")
check(sum(x["n"] for x in _g) == len(_rows), "nenhuma linha se perde no agrupamento")

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes semanais passaram.")
