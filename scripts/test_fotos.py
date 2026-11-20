# -*- coding: utf-8 -*-
"""Testes da padronização de fotos (scripts/padronizar_foto.py) e dos arquivos de foto já publicados."""
import os, re, sys, tempfile, shutil
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
try:
    from PIL import Image
except ImportError:
    print("[PULOU] Pillow não instalado: pip install pillow"); sys.exit(0)
import padronizar_foto as P

falhas = []
def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok: falhas.append(nome)

# recorte: sempre quadrado no tamanho padrão, mesmo com foto retrato, paisagem ou com transparência
for nome, tam, modo in (("retrato", (600, 900), "RGB"), ("paisagem", (900, 500), "RGB"), ("quadrada", (480, 480), "RGB"), ("transparente", (300, 700), "RGBA")):
    im = Image.new(modo, tam, (10, 20, 30, 0) if modo == "RGBA" else (10, 20, 30))
    r = P.recortar(im)
    checar(f"recorte {nome}: {P.LADO}×{P.LADO} em RGB", r.size == (P.LADO, P.LADO) and r.mode == "RGB", f"{r.size} {r.mode}")
im = Image.new("RGBA", (300, 700), (0, 0, 0, 0))
checar("fundo transparente vira o cinza neutro (sem preto)", P.recortar(im).getpixel((3, 3)) == P.FUNDO)

# o rosto escolhido fica dentro do recorte: faixa clara no terço de cima só entra se o rosto estiver lá
foto = Image.new("RGB", (400, 1000), (0, 0, 0)); foto.paste((255, 255, 255), (0, 100, 400, 300))
alto = P.recortar(foto, (0.5, 0.2)); baixo = P.recortar(foto, (0.5, 0.9))
checar("--rosto muda o enquadramento (faixa clara só aparece com o rosto no alto)", alto.getpixel((240, 150))[0] > 200 and baixo.getpixel((240, 150))[0] < 50)

# registro em fotos.js, em cópia: inclui, atualiza e mantém comentário de linha
tmp = tempfile.mkdtemp()
try:
    os.makedirs(os.path.join(tmp, "assets"))
    open(os.path.join(tmp, "assets", "fotos.js"), "w", encoding="utf-8").write('window.AGENTES_FOTOS = {\n  "1936": "assets/fotos/1936.png"   // Fulano\n};\n')
    P.RAIZ = tmp
    P.inserir_no_fotos_js("85", "assets/fotos/85.jpg")
    P.inserir_no_fotos_js("85", "assets/fotos/85b.jpg")
    s = open(os.path.join(tmp, "assets", "fotos.js"), encoding="utf-8").read()
    checar("fotos.js: acrescenta o ID com vírgula antes do comentário e sem duplicar", '"1936": "assets/fotos/1936.png", // Fulano' in s and s.count('"85"') == 1 and "85b.jpg" in s, s)
    checar("fotos.js continua sendo JavaScript válido (chaves e vírgulas)", re.search(r'\{\s*("[^"]+":\s*"[^"]+",?\s*(//[^\n]*)?\s*)+\};', s) is not None, s)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# fotos já publicadas: quadradas e referenciadas por ID existente
js = open(os.path.join(RAIZ, "assets", "fotos.js"), encoding="utf-8").read()
for id_, caminho in re.findall(r'"(\d+)"\s*:\s*"([^"]+)"', js):
    f = os.path.join(RAIZ, caminho)
    ok = os.path.exists(f)
    if ok:
        w, h = Image.open(f).size
        checar(f"foto do agente {id_}: arquivo existe e é quadrado", w == h, f"{w}×{h}")
    else:
        checar(f"foto do agente {id_}: arquivo existe", False, caminho)

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}"); sys.exit(1)
print("✅ Todos os testes de fotos passaram.")
