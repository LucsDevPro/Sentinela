# -*- coding: utf-8 -*-
"""Roda TODOS os testes Python do projeto e imprime UMA linha por teste (funciona no Windows, Linux e macOS).

  python scripts/rodar_testes.py             # todos
  python scripts/rodar_testes.py ranking     # só os que tiverem "ranking" no nome
  python scripts/rodar_testes.py -v          # mostra a saída completa dos que falharem

O teste do Worker é à parte: node worker/test_worker.mjs. Os *_navegador.py exigem Playwright (só no
computador de desenvolvimento). Precisa de: pip install -r requirements.txt. Roda da raiz do repositório.
Para registrar um teste novo, acrescente o nome (sem "test_" e sem ".py") em TESTES abaixo — esta é a ÚNICA
lista (o rodar_testes.sh só chama este arquivo) — e, se for para o CI, também no update-dashboard.yml.
"""
import os
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTES = ["deteccao", "desempate", "ranking", "ciclos", "atestado", "ausencia", "decisao", "regras", "semanal",
          "coleta", "sessao8", "sessao9", "sessao10", "turno_evento", "regenerar_mes", "resumo", "cache_leitura", "album", "versionar"]
LIMITE_S = 280


def _resumo(saida):
    linhas = [l for l in saida.splitlines() if l.strip()]
    marcadas = [l for l in linhas if l.startswith(("✅", "❌"))]
    return (marcadas or linhas or [""])[-1]


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    verboso = "-v" in args
    filtro = next((a for a in args if not a.startswith("-")), "")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    falhas = rodados = 0
    for t in TESTES:
        if filtro and filtro not in t:
            continue
        arq = os.path.join("scripts", f"test_{t}.py")
        if not os.path.exists(os.path.join(RAIZ, arq)):
            print(f"?  {t:16} (arquivo não existe)")
            continue
        ini = time.time()
        try:
            r = subprocess.run([sys.executable, arq], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, timeout=LIMITE_S)
            codigo, saida = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            codigo, saida = 124, f"❌ passou de {LIMITE_S}s"
        seg = int(time.time() - ini)
        resumo = _resumo(saida)
        if codigo == 0:
            print(f"✅ {t:16} {seg:3d}s  {resumo.lstrip('✅ ')}")
        else:
            falhas += 1
            print(f"❌ {t:16} {seg:3d}s  {resumo or 'falhou (rode: python ' + arq + ')'}")
            if verboso:
                print("\n".join("     " + l for l in saida.splitlines()[-40:]))
        rodados += 1
    print("----")
    if falhas == 0:
        print(f"✅ {rodados} teste(s) passaram.")
        return 0
    print(f"❌ {falhas} de {rodados} teste(s) falharam.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
