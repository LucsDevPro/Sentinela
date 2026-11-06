# -*- coding: utf-8 -*-
"""Regera TODAS as páginas HTML a partir dos dados já existentes (sem coleta, sem e-Visita).

  python scripts/regerar_paginas.py            # index, acumulado, transparência, agentes e historico/*.html
  python scripts/regerar_paginas.py --so-home  # só o index.html

Mesma sequência do workflow update-dashboard (passos de geração). Use depois de mudar template, CSS ou regra
de cálculo, para conferir o resultado completo antes do commit. Apaga páginas órfãs de historico/ (sem .xlsx).
"""
import os
import shutil
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rodar(args):
    t = time.time()
    r = subprocess.run([sys.executable, *args], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"❌ {' '.join(args)}\n{(r.stderr or r.stdout)[-1500:]}")
        sys.exit(r.returncode)
    print(f"✓ {' '.join(args[1:]) or args[0]}  ({time.time() - t:.1f}s)")


def main(argv=None):
    so_home = "--so-home" in (argv if argv is not None else sys.argv[1:])
    gd = os.path.join("scripts", "generate_dashboard.py")
    if not so_home:   # na geração completa as partes de TODAS as páginas são recriadas; em --so-home só a do index
        shutil.rmtree(os.path.join(RAIZ, "partes"), ignore_errors=True)
    _rodar([gd])
    if so_home:
        return 0
    _rodar([gd, "data/Analise_Consolidada.xlsx", "acumulado.html"])
    _rodar([os.path.join("scripts", "gerar_transparencia.py")])
    _rodar([os.path.join("scripts", "gerar_agentes.py")])
    pasta_h = os.path.join(RAIZ, "historico")
    os.makedirs(pasta_h, exist_ok=True)
    for f in sorted(os.listdir(pasta_h)):
        if f.endswith(".html") and not os.path.exists(os.path.join(RAIZ, "data", "historico", f[:-5] + ".xlsx")):
            os.remove(os.path.join(pasta_h, f))
            print(f"🧹 página órfã removida: historico/{f}")
    pasta_x = os.path.join(RAIZ, "data", "historico")
    for x in sorted(os.listdir(pasta_x)):
        if x.endswith(".xlsx"):
            _rodar([gd, f"data/historico/{x}", f"historico/{x[:-5]}.html"])
    print("✅ páginas regeneradas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
