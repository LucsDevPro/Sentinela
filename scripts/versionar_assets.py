# -*- coding: utf-8 -*-
"""Renova o cache do navegador: coloca ?v=<hash do conteúdo> em cada assets/*.js|css citado pelas páginas.

O GitHub Pages deixa o navegador guardar cada arquivo por até 10 min; sem versão na URL, quem abre o site logo depois de
uma atualização pode ver o JS/CSS antigo com a página nova. Com ?v=hash a URL muda sempre que o arquivo muda (e só então).
Também troca o nome do cache do service worker (sw.js) por um hash dos arquivos que ele guarda.

  python scripts/versionar_assets.py            -> altera as páginas .html da raiz e de historico/ e o sw.js
  python scripts/versionar_assets.py --checar   -> só informa o que mudaria (sem gravar)
Rodar duas vezes seguidas não muda nada (idempotente).
"""
import glob
import hashlib
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = re.compile(r'''((?:src|href)=["'])((?:\./|\.\./)?assets/[A-Za-z0-9_./-]+\.(?:js|css))(?:\?v=[^"']*)?(["'])''')


def hash_arquivo(caminho):
    with open(caminho, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def versionar_html(caminho, gravar=True):
    base = os.path.dirname(caminho)
    with open(caminho, encoding="utf-8") as f:
        texto = f.read()

    def troca(m):
        alvo = os.path.normpath(os.path.join(base, m.group(2)))
        if not os.path.exists(alvo):
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}?v={hash_arquivo(alvo)}{m.group(3)}"

    novo = REF.sub(troca, texto)
    if novo != texto and gravar:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(novo)
    return novo != texto


def versionar_sw(gravar=True):
    sw = os.path.join(RAIZ, "sw.js")
    if not os.path.exists(sw):
        return False
    with open(sw, encoding="utf-8") as f:
        texto = f.read()
    m = re.search(r'const ARQUIVOS = \[(.*?)\];', texto, re.S)
    if not m:
        return False
    nomes = re.findall(r'"([^"]+)"', m.group(1))
    h = hashlib.sha1()
    for n in nomes:
        p = os.path.join(RAIZ, n)
        if os.path.exists(p):
            h.update(hash_arquivo(p).encode())
    novo = re.sub(r'const CASCA = "[^"]*";', f'const CASCA = "sentinela-casca-{h.hexdigest()[:8]}";', texto, count=1)
    if novo != texto and gravar:
        with open(sw, "w", encoding="utf-8") as f:
            f.write(novo)
    return novo != texto


def main():
    gravar = "--checar" not in sys.argv
    paginas = sorted(glob.glob(os.path.join(RAIZ, "*.html")) + glob.glob(os.path.join(RAIZ, "historico", "*.html")))
    mudou = [os.path.relpath(p, RAIZ) for p in paginas if versionar_html(p, gravar)]
    sw = versionar_sw(gravar)
    print(f"{'Versionadas' if gravar else 'Mudariam'}: {len(mudou)} página(s)" + (" + sw.js" if sw else ""))


if __name__ == "__main__":
    main()
