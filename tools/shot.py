# -*- coding: utf-8 -*-
"""Tira screenshot de uma aba do dashboard (claro e/ou escuro) e mostra erros de JavaScript.

Uso:
  python3 tools/shot.py index.html custos                  # aba "custos", tema claro e escuro
  python3 tools/shot.py _teste.html ranking --tema claro --largura 400   # celular
  python3 tools/shot.py index.html custos --seletor "#tableCustosMensal"  # só um elemento

Saída: /tmp/shot_<aba>_<tema>.png (ou --saida). Requer: pip install playwright && playwright install chromium
"""
import argparse
import asyncio
from pathlib import Path


async def principal(a):
    from playwright.async_api import async_playwright
    caminho = Path(a.html).resolve()
    async with async_playwright() as p:
        nav = await p.chromium.launch()
        for tema in a.tema.split(","):
            pg = await nav.new_page(viewport={"width": a.largura, "height": 900})
            erros = []
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
            await pg.goto(f"file://{caminho}")
            await pg.evaluate(f"document.documentElement.setAttribute('data-theme','{'dark' if tema == 'escuro' else 'light'}')")
            if a.aba:
                await pg.click(f"button.nav-tab[data-section='{a.aba}']")
            await pg.wait_for_timeout(1500)
            alvo = await pg.query_selector(a.seletor or (f"#{a.aba}" if a.aba else "body"))
            saida = f"{a.saida}_{tema}.png" if a.saida else f"/tmp/shot_{a.aba or 'pagina'}_{tema}.png"
            await alvo.screenshot(path=saida)
            print(f"{tema}: {saida} | erros JS: {erros[:5] or 'nenhum'}")
        await nav.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("aba", nargs="?", default="", help="data-section da aba (ex.: custos, ranking)")
    ap.add_argument("--tema", default="claro,escuro")
    ap.add_argument("--largura", type=int, default=1400)
    ap.add_argument("--seletor", default="")
    ap.add_argument("--saida", default="", help="prefixo do arquivo de saída")
    asyncio.run(principal(ap.parse_args()))
