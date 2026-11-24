#!/usr/bin/env python3
"""Gera assets/carta_forma.css: a silhueta «Brasão» das cartinhas (ombros cortados + base em V suave).

A mesma geometria existe em assets/carta.js (FORMA_TOPO / FORMA_BASE, função formaPts) para o PNG em canvas.
Se mudar TOPO ou BASE aqui, mude lá também (test_album confere). `--check` só verifica se o CSS está em dia."""
import sys, os

W, H = 272, 392
TOPO = 30     # tamanho do corte dos ombros (px)
BASE = 26     # profundidade do V da base (px)
# espessura da moldura de cada nível (px) — igual a --bw dos temas em carta.css
BW = {"t-ferro": 3.5, "t-aco": 3.5, "t-bronze": 4, "t-prata": 5, "t-ouro": 7, "t-platina": 8, "t-elite": 8, "b-100": 8}


def base_pts():
    return [(TOPO, 0), (W - TOPO, 0), (W, TOPO), (W, H - BASE), (W / 2, H), (0, H - BASE), (0, TOPO)]


def deslocar(pts, d):
    """Recua o polígono convexo (sentido horário na tela) d px para dentro, encontrando as retas vizinhas."""
    n, retas = len(pts), []
    for i in range(n):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        l = (dx * dx + dy * dy) ** .5
        nx, ny = -dy / l, dx / l           # normal para dentro (horário, y para baixo)
        retas.append(((x1 + nx * d, y1 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (p, v), (q, u) = retas[i - 1], retas[i]
        den = v[0] * u[1] - v[1] * u[0]
        t = ((q[0] - p[0]) * u[1] - (q[1] - p[1]) * u[0]) / den
        out.append((p[0] + v[0] * t, p[1] + v[1] * t))
    return out


def f(v):
    return ("%.2f" % v).rstrip("0").rstrip(".")


def caminho(pts):
    return "M" + " L".join("%s %s" % (f(x), f(y)) for x, y in pts) + " Z"


def poligono_calc():
    def cx(x): return "%spx" % f(x) if x <= W / 2 else "calc(100%% - %spx)" % f(W - x)
    def cy(y): return "%spx" % f(y) if y <= H / 2 else "calc(100%% - %spx)" % f(H - y)
    return "polygon(" + ", ".join("%s %s" % (cx(x), cy(y)) for x, y in base_pts()) + ")"


def gerar():
    L = ["/* GERADO por scripts/gerar_forma_carta.py — não edite à mão. Silhueta «Brasão» das cartinhas (carregar DEPOIS de carta_raridade.css). */", ""]
    L += ["/* Recorte do cartão: o brilho externo sai do box-shadow (que o recorte cortaria) e vai para um drop-shadow no conjunto .c-conj */",
          ".c-conj .carta.carta { clip-path: %s; border-radius: 0; box-shadow: none; }" % poligono_calc(), ""]
    L += ["/* Anel da moldura: contorno externo + contorno recuado (evenodd). O mesmo recorte vale para o brilho diagonal (::after). */",
          ".c-conj .carta > .c-borda { padding: 0; border-radius: 0; box-shadow: none; -webkit-mask: none; mask: none; }",
          ".c-conj .carta > .c-borda::before { display: none; }", ""]
    for cls, bw in BW.items():
        d = bw
        sel = ".c-conj .carta.%s > .c-borda" % cls
        L.append("%s { clip-path: path(evenodd, \"%s %s\"); }" % (sel, caminho(base_pts()), caminho(deslocar(base_pts(), d))))
    L += ["", "/* Foto 12 px menor: sobe o rodapé para fora do V da base */", ".c-conj .carta.carta { --k-foto: 100px; }", "", "/* Sem asas laterais nem gema: a silhueta já tem o V na base. A coroa do TOP 3 continua (carta.js). */",
          ".c-conj .c-orna-atras { display: none; }", "",
          "/* Brilho externo por nível (cor = --raridade de carta_raridade.css) */"]
    CORES = {"t-ferro": "107,114,128", "t-aco": "46,125,140", "t-bronze": "201,139,94", "t-prata": "198,204,212", "t-ouro": "224,182,79", "t-platina": "0,217,232", "t-elite": "168,85,247", "b-100": "255,212,71"}
    for cls, rgb in CORES.items():
        forte = cls in ("t-ouro", "t-platina", "t-elite", "b-100")
        a = ".55" if cls == "b-100" else ".42" if forte else ".28" if cls != "t-ferro" else "0"
        L.append(".c-conj.c-conj:has(> .carta.%s) { filter: drop-shadow(0 0 %spx rgba(%s, %s)) drop-shadow(0 14px 16px rgba(0, 0, 0, .38)); }" % (cls, "16" if forte else "10", rgb, a))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "carta_forma.css")
    novo = gerar()
    if "--check" in sys.argv:
        atual = open(dest, encoding="utf-8").read() if os.path.exists(dest) else ""
        print("OK" if atual == novo else "DESATUALIZADO: rode python3 scripts/gerar_forma_carta.py")
        sys.exit(0 if atual == novo else 1)
    open(dest, "w", encoding="utf-8").write(novo)
    print("gerado", dest)
