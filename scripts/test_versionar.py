# -*- coding: utf-8 -*-
"""Testa scripts/versionar_assets.py: coloca ?v=hash, troca o hash quando o arquivo muda e é idempotente."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import versionar_assets as V

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


with tempfile.TemporaryDirectory() as d:
    os.makedirs(os.path.join(d, "assets")); os.makedirs(os.path.join(d, "historico"))
    js = os.path.join(d, "assets", "a.js"); css = os.path.join(d, "assets", "b.css")
    open(js, "w").write("console.log(1)"); open(css, "w").write("body{}")
    raiz = os.path.join(d, "p.html"); sub = os.path.join(d, "historico", "h.html")
    open(raiz, "w", encoding="utf-8").write('<link rel="stylesheet" href="assets/b.css"><script src="assets/a.js"></script><script src="https://x.com/assets/z.js"></script>')
    open(sub, "w", encoding="utf-8").write('<script src="../assets/a.js?v=deadbeef"></script><img src="assets/x.png">')
    checar("a página da raiz ganha ?v=hash em .js e .css", V.versionar_html(raiz) and 'assets/a.js?v=' in open(raiz, encoding="utf-8").read() and 'assets/b.css?v=' in open(raiz, encoding="utf-8").read())
    checar("não mexe em endereço externo nem em imagem", "https://x.com/assets/z.js" in open(raiz, encoding="utf-8").read() and 'assets/x.png"' in open(sub, encoding="utf-8").read())
    checar("página de historico/ resolve ../assets e troca o hash antigo", V.versionar_html(sub) and "?v=deadbeef" not in open(sub, encoding="utf-8").read())
    antes = open(raiz, encoding="utf-8").read()
    checar("rodar de novo não muda nada (idempotente)", not V.versionar_html(raiz) and antes == open(raiz, encoding="utf-8").read())
    open(js, "w").write("console.log(2)")
    checar("mudou o arquivo, mudou o hash na página", V.versionar_html(raiz) and antes != open(raiz, encoding="utf-8").read())

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes do versionamento passaram.")
