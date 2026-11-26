#!/usr/bin/env python3
"""Gera a seção «FORMA» (silhueta FUT da cartinha) no fim de assets/carta.css.

Silhueta 272x392 TRAÇADA da imagem de referência do cliente (cartas FUT): cume central, ombros inclinados até y≈46, laterais retas e base afunilada em arco. SEGS é o perfil simétrico (poligonal) extraído do contorno.
A MESMA definição (SEGS) e a mesma amostragem existem em assets/carta.js (FORMA_SEGS / formaPts) para o PNG em canvas;
test_album confere os marcadores. Uso: python3 scripts/gerar_forma_carta.py  (reescreve a seção em carta.css) · --check só verifica."""
import re, sys, os, math

W, H = 272, 392
# (tipo, pontos...) : 'M' início, 'L' reta, 'C' cúbica (2 controles + destino). Sentido horário (y para baixo).
SEGS = [("M", 179.9, 0.0), ("L", 186.1, 1.2), ("L", 202.7, 7.1), ("L", 244.9, 28.5), ("L", 253.4, 32.1), ("L", 268.9, 36.8), ("L", 271.2, 38.0), ("L", 272.0, 39.2), ("L", 271.7, 340.9), ("L", 269.9, 348.0), ("L", 266.5, 354.0), ("L", 260.5, 359.9), ("L", 252.1, 364.7), ("L", 248.6, 365.9), ("L", 235.9, 368.2), ("L", 190.7, 374.2), ("L", 171.7, 377.7), ("L", 150.9, 383.7), ("L", 140.4, 388.4), ("L", 136.0, 392.0), ("L", 131.6, 388.4), ("L", 121.1, 383.7), ("L", 100.3, 377.7), ("L", 81.3, 374.2), ("L", 36.1, 368.2), ("L", 23.4, 365.9), ("L", 19.9, 364.7), ("L", 11.5, 359.9), ("L", 5.5, 354.0), ("L", 2.1, 348.0), ("L", 0.3, 340.9), ("L", 0.0, 39.2), ("L", 0.8, 38.0), ("L", 3.1, 36.8), ("L", 18.6, 32.1), ("L", 27.1, 28.5), ("L", 69.3, 7.1), ("L", 85.9, 1.2), ("L", 92.1, 0.0), ("L", 179.9, 0.0)]
PASSOS = 10  # amostras por curva
BW = {"t-ferro": 3.5, "t-aco": 3.5, "t-bronze": 4, "t-prata": 5, "t-ouro": 7, "t-platina": 8, "t-elite": 8, "b-100": 8}
CORES = {"t-ferro": "107,114,128", "t-aco": "46,125,140", "t-bronze": "201,139,94", "t-prata": "198,204,212", "t-ouro": "224,182,79", "t-platina": "0,217,232", "t-elite": "168,85,247", "b-100": "255,212,71"}
MARCA_I, MARCA_F = "/* ===== FORMA «FUT» (início) ===== */", "/* ===== FORMA «FUT» (fim) ===== */"


def amostrar():
    pts, cur = [], None
    for s in SEGS:
        if s[0] == "M": cur = (s[1], s[2]); pts.append(cur)
        elif s[0] == "L": cur = (s[1], s[2]); pts.append(cur)
        else:
            x0, y0 = cur; x1, y1, x2, y2, x3, y3 = s[1:]
            for i in range(1, PASSOS + 1):
                t = i / PASSOS; u = 1 - t
                pts.append((u**3*x0 + 3*u*u*t*x1 + 3*u*t*t*x2 + t**3*x3, u**3*y0 + 3*u*u*t*y1 + 3*u*t*t*y2 + t**3*y3))
            cur = (x3, y3)
    if pts[0] == pts[-1]: pts.pop()
    return pts


def recuar(pts, d):
    if not d: return pts
    n, out = len(pts), []
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        def nor(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]; l = math.hypot(dx, dy) or 1
            return (-dy / l, dx / l)
        n1, n2 = nor(a, b), nor(b, c)
        mx, my = n1[0] + n2[0], n1[1] + n2[1]; ml = math.hypot(mx, my) or 1
        mx, my = mx / ml, my / ml
        cos = max(0.5, mx * n1[0] + my * n1[1])
        out.append((b[0] + mx * d / cos, b[1] + my * d / cos))
    return out


def f(v): return ("%.2f" % v).rstrip("0").rstrip(".")
def caminho(pts): return "M" + " L".join("%s %s" % (f(x), f(y)) for x, y in pts) + " Z"


def gerar():
    base = amostrar()
    L = [MARCA_I, "/* GERADO por scripts/gerar_forma_carta.py — não edite à mão. Silhueta FUT: ressalto central no topo, ombros curvos, base arredondada. Mesma geometria de FORMA_SEGS/formaPts em carta.js (PNG). */", "",
         ".c-conj .carta.carta { clip-path: path(\"%s\"); border-radius: 0; box-shadow: none; }" % caminho(base), "",
         ".c-conj .carta.carta > .c-borda { padding: 0 !important; border-radius: 0; box-shadow: none !important; -webkit-mask: none !important; mask: none !important; }",
         ".c-conj .carta.carta > .c-borda::before { display: none; }", ""]
    for cls, bw in BW.items():
        L.append(".c-conj .carta.%s > .c-borda { clip-path: path(evenodd, \"%s %s\"); }" % (cls, caminho(base), caminho(recuar(base, bw))))
    L += ["", "/* Brilho externo por nível: o recorte corta o box-shadow, então ele vira drop-shadow no conjunto .c-conj */"]
    for cls, rgb in CORES.items():
        forte = cls in ("t-ouro", "t-platina", "t-elite", "b-100")
        a = ".55" if cls == "b-100" else ".42" if forte else ".28" if cls != "t-ferro" else "0"
        L.append(".c-conj.c-conj:has(> .carta.%s) { filter: drop-shadow(0 0 %spx rgba(%s, %s)) drop-shadow(0 14px 16px rgba(0, 0, 0, .38)); }" % (cls, "16" if forte else "10", rgb, a))
    L.append(MARCA_F)
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "carta.css")
    s = open(dest, encoding="utf-8").read()
    padrao = re.compile(re.escape(MARCA_I) + r".*?" + re.escape(MARCA_F) + r"\n", re.S)
    novo = gerar()
    if "--check" in sys.argv:
        m = padrao.search(s); ok = bool(m) and m.group(0) == novo
        print("OK" if ok else "DESATUALIZADO: rode python3 scripts/gerar_forma_carta.py"); sys.exit(0 if ok else 1)
    if padrao.search(s): s = padrao.sub(lambda m: novo, s)
    else:
        i = s.index("/* ===== FORMA «BRASÃO»")
        s = s[:i] + novo
    open(dest, "w", encoding="utf-8").write(s)
    print("seção FORMA atualizada em", dest)
