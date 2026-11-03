# -*- coding: utf-8 -*-
"""Gera docs/MAPA.md: índice de funções e constantes dos scripts (arquivo, linha, 1ª linha
da docstring). Serve pra ir direto ao trecho certo sem ler arquivos de milhares de linhas.

Uso:  python3 scripts/gerar_mapa.py          (reescreve docs/MAPA.md)
      python3 scripts/gerar_mapa.py --check  (falha se o mapa estiver desatualizado)
"""
import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "MAPA.md"
MAX_DOC = 78


def resumo_doc(no):
    doc = ast.get_docstring(no) or ""
    linha = next((l.strip() for l in doc.splitlines() if l.strip()), "")
    return (linha[:MAX_DOC - 1] + "…") if len(linha) > MAX_DOC else linha


def analisar(caminho):
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    funcs, consts = [], []
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = ", ".join(a.arg for a in no.args.args)[:40]
            funcs.append((no.lineno, f"{no.name}({args})", resumo_doc(no)))
        elif isinstance(no, ast.ClassDef):
            funcs.append((no.lineno, f"class {no.name}", resumo_doc(no)))
        elif isinstance(no, ast.Assign):
            for alvo in no.targets:
                if isinstance(alvo, ast.Name) and alvo.id.isupper() and len(alvo.id) > 2:
                    consts.append((no.lineno, alvo.id))
    return len(arvore.body), funcs, consts


def gerar():
    saida = ["# Mapa do código (gerado por `scripts/gerar_mapa.py` — não edite à mão)", "",
             "Formato: `L<linha> função(args) — resumo`. Constantes ficam no fim de cada arquivo (`NOME@linha`).",
             "Use `grep -n \"def nome\" arquivo` ou `sed -n 'A,Bp'` pra ler só o trecho.", ""]
    arquivos = sorted((RAIZ / "scripts").glob("*.py")) + sorted((RAIZ / "scripts" / "coleta").glob("*.py"))
    for caminho in arquivos:
        if caminho.name.startswith("test_") or caminho.name in ("gerar_mapa.py", "__init__.py"):
            continue
        _, funcs, consts = analisar(caminho)
        total = len(caminho.read_text(encoding="utf-8").splitlines())
        saida += [f"## {caminho.relative_to(RAIZ).as_posix()} ({total} linhas)", ""]
        for linha, assinatura, doc in funcs:
            saida.append(f"- L{linha} `{assinatura}`" + (f" — {doc}" if doc else ""))
        if consts:
            saida += ["", "Constantes: " + ", ".join(f"{n}@{l}" for l, n in consts)]
        saida.append("")
    return "\n".join(saida).rstrip() + "\n"


if __name__ == "__main__":
    novo = gerar()
    if "--check" in sys.argv:
        if not SAIDA.exists() or SAIDA.read_text(encoding="utf-8") != novo:
            print("docs/MAPA.md desatualizado — rode: python3 scripts/gerar_mapa.py")
            sys.exit(1)
        print("docs/MAPA.md está em dia.")
    else:
        SAIDA.write_text(novo, encoding="utf-8")
        print(f"OK: {SAIDA.relative_to(RAIZ)} ({len(novo.splitlines())} linhas, {len(novo)//1024} KB)")
