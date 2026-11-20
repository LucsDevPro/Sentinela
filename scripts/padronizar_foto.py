#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Padroniza a foto de um agente para a cartinha: quadrada, 480×480, rosto no terço de cima, fundo neutro.

Uso:  python3 scripts/padronizar_foto.py ID caminho/da/foto.jpg [--rosto X Y]
  ID           id do agente (nunca o nome)
  --rosto X Y  ponto do rosto na foto original, de 0 a 1 (padrão: centro na horizontal e 35 % da altura)
Grava assets/fotos/ID.jpg (JPEG q90, sem transparência: PNG com fundo vazio vira cinza-azulado neutro) e atualiza assets/fotos.js.
Repositório público: use só foto autorizada, sem metadados (o EXIF é descartado ao regravar)."""
import argparse, os, re, sys
from PIL import Image, ImageOps

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LADO = 480                      # a cartinha mostra ~110 px; 480 cobre a exportação em 2× sem pesar
FUNDO = (226, 232, 240)         # cinza-azulado neutro (só aparece onde o original é transparente)
ROSTO_PADRAO = (0.5, 0.35)


def recortar(im, rosto=ROSTO_PADRAO):
    """Quadrado centrado no rosto, o maior possível dentro da imagem."""
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fundo = Image.new("RGB", im.size, FUNDO)
        fundo.paste(im, mask=im.split()[3])
        im = fundo
    else:
        im = im.convert("RGB")
    w, h = im.size
    lado = min(w, h)
    cx, cy = rosto[0] * w, rosto[1] * h
    x0 = int(min(max(cx - lado / 2, 0), w - lado))
    y0 = int(min(max(cy - lado / 2, 0), h - lado))
    return im.crop((x0, y0, x0 + lado, y0 + lado)).resize((LADO, LADO), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("id"); ap.add_argument("foto"); ap.add_argument("--rosto", nargs=2, type=float, metavar=("X", "Y"))
    a = ap.parse_args()
    if not re.fullmatch(r"\d+", a.id):
        sys.exit("O ID do agente é numérico (veja scripts/resumo.py ranking).")
    rosto = tuple(a.rosto) if a.rosto else ROSTO_PADRAO
    if not all(0 <= v <= 1 for v in rosto):
        sys.exit("--rosto X Y vai de 0 a 1.")
    img = recortar(Image.open(a.foto), rosto)
    os.makedirs(os.path.join(RAIZ, "assets", "fotos"), exist_ok=True)
    destino = os.path.join(RAIZ, "assets", "fotos", f"{a.id}.jpg")
    img.save(destino, "JPEG", quality=90, optimize=True)   # sem exif
    rel = f"assets/fotos/{a.id}.jpg"
    inserir_no_fotos_js(a.id, rel)
    print(f"✔ {rel} ({LADO}×{LADO}) e assets/fotos.js atualizados.")


def inserir_no_fotos_js(id_, rel):
    p = os.path.join(RAIZ, "assets", "fotos.js")
    s = open(p, encoding="utf-8").read()
    if re.search(rf'"{id_}"\s*:', s):
        s = re.sub(rf'"{id_}"\s*:\s*"[^"]*"', f'"{id_}": "{rel}"', s)
    else:
        m = re.search(r"window\.AGENTES_FOTOS\s*=\s*\{(.*?)\n\};", s, re.S)
        corpo = m.group(1)
        linhas = [l for l in corpo.split("\n") if l.strip()]
        if linhas:
            ult = linhas[-1]
            if not ult.rstrip().endswith(","):
                partes = ult.split("//", 1)
                ult_novo = partes[0].rstrip() + "," + ((" //" + partes[1]) if len(partes) > 1 else "")
                linhas[-1] = ult_novo
        linhas.append(f'  "{id_}": "{rel}"')
        s = s[:m.start(1)] + "\n" + "\n".join(linhas) + s[m.end(1):]
    open(p, "w", encoding="utf-8").write(s)


if __name__ == "__main__":
    main()
