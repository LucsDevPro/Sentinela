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
    Path(hist, "semana_330.xlsx").write_bytes(b"x")
    antigo = [
        {"arquivo": "semanas_322-326.xlsx", "label": "Setembro/2026", "origem": "manual"},
        {"arquivo": "semana_324.xlsx", "tipo": "semana", "mes": "Setembro/2026", "origem": "cache", "semana_inicio": 324, "parcial": True},
        {"arquivo": "semana_330.xlsx", "tipo": "semana", "mes": "Outubro/2026", "origem": "cache", "semana_inicio": 330, "parcial": True},
    ]
    json.dump(antigo, open(os.path.join(hist, "manifest.json"), "w"))
    C.atualizar_historico_do_cache(pasta_semanas=os.path.join(tmp, "vazio"), pasta_historico=hist,
                                   pasta_saida_tmp=os.path.join(tmp, "t"))
    novo = {e["arquivo"]: e for e in json.load(open(os.path.join(hist, "manifest.json")))}
    check(novo["semana_324.xlsx"]["origem"] == "manual" and novo["semana_324.xlsx"]["parcial"] is False,
          "Semana de mês arquivado (Setembro) é congelada: origem manual, sem 'parcial'")
    check("semana_330.xlsx" not in novo, "Semana de mês aberto sem cache não vira manual")

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

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes semanais passaram.")
