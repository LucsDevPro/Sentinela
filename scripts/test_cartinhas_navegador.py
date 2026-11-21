# -*- coding: utf-8 -*-
"""SUÍTE DAS CARTINHAS (navegador). Cobre os 8 tiers e confere, sem travar valores de cor:
  1. estrutura e medidas de cada tier        4. HTML × PNG (exportação principal e plano B em canvas)
  2. cores, bordas, tipografia, efeitos      5. movimento reduzido
  3. tema claro/escuro da Sala               6. áudio, vídeo e animações (SÓ MEDE: não altera nada)
  7. página: carregamento sob demanda, estados (vazio), aviso de fotos, fonte da nota, folha de recorte (8 por A4)
Filosofia: os testes aceitam trocar cores, espessuras e fontes. Eles checam INVARIANTES (contraste mínimo, valores
válidos, HTML == PNG, mesmas faixas nos dois caminhos), e todos os limites ficam em CONFIG, logo abaixo.
Como acrescentar teste: docs/TESTES_CARTINHAS.md.

Uso:  python3 scripts/test_cartinhas_navegador.py            # tudo (≈40 s, grava 1 vídeo de 5 s)
      python3 scripts/test_cartinhas_navegador.py --rapido   # sem vídeo
      python3 scripts/test_cartinhas_navegador.py --top5     # também grava o vídeo do top 5 (≈15 s a mais)
      python3 scripts/test_cartinhas_navegador.py cores      # só os grupos cujo nome contém «cores»
Precisa de playwright + chromium (e ffmpeg/ffprobe para o vídeo; sem eles os testes de vídeo são pulados)."""
import base64, functools, http.server, io, json, os, re, shutil, subprocess, sys, tempfile, threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ───────────────────────── CONFIG: ajuste aqui quando o visual mudar de propósito ─────────────────────────
CONFIG = {
    "ADIAR_MIN": 12,               # a Sala adia o desenho das cartinhas depois da 12ª (ADIAR_APOS em album.js): precisa haver mais que isso para o teste fazer sentido
    "NOTA_PESO_MIN": 700,          # a nota tem peso próprio (hoje 800): nunca mais fraca que negrito
    "BANDA_MEDIDAS": 20,           # cada medida (ASS…MED) fica a até N pontos da nota (igual a BANDA em carta.js)
    "CONTRASTE_NOTA": 3.0,         # texto grande (a nota) sobre o fundo do cartão (WCAG: 3 para texto grande)
    "CONTRASTE_TEXTO": 4.5,        # nome, rodapé e chips sobre o fundo do cartão
    "CONTRASTE_BORDA_RELEVO": 1.1,  # a moldura precisa ter relevo: --b1 (sombra) e --b3 (brilho) não podem ser iguais
    "BORDA_PX": (2, 14),           # espessura permitida de --bw
    "RAIO_PX": (6, 28),            # raio permitido do cartão
    "FONTE_MIN_PX": 9,             # menor texto aceitável dentro do cartão
    "FAMILIAS": ("Barlow", "IBM Plex"),   # famílias esperadas nos textos do cartão (qualquer uma serve em cada elemento)
    "PNG_DIF_MEDIA": 26,           # PNG principal × HTML: diferença média por canal (0–255) na grade
    "PNG_CANVAS_DIF_MEDIA": 60,    # plano B (canvas) é «menos fiel»: tolerância maior, mas ainda confere cor e brilho gerais
    "PNG_GRADE": (8, 10),          # colunas × linhas da grade de comparação
    "AUDIO_PICO_MAX": 1.0,         # nenhum som passa de 0 dBFS
    "AUDIO_RMS_MIN": 1e-4,         # nenhum som é mudo
    "VIDEO_DUR": (4.6, 5.8),       # duração aceitável do vídeo de 5 s (s)
    "VIDEO_FPS_MIN": 5.0,          # taxa mínima de quadros medida (o ambiente de teste não tem GPU: só barra regressão grave)
    "VIDEO_AUDIO_DB_MIN": -45.0,   # o áudio do vídeo não pode ser praticamente mudo (pico, dBFS)
    "VIDEO_FADE_RATIO": 0.6,       # no último 0,15 s o pico precisa cair abaixo de N × o pico geral (fade no fim)
}
# Os 8 tiers. «caso» = (nota, posição no mês de 20 agentes). Se um tier novo surgir, acrescente aqui.
TIERS = [
    ("LENDÁRIA", "b-100", 105, 1), ("DESTAQUE", "t-destaque b-top", 96, 2), ("ELITE", "b-90 n100", 104, 8), ("OURO", "b-90", 93, 9),
    ("PRATA", "t-prata b-80", 85, 10), ("BRONZE", "t-bronze b-70", 75, 11), ("AÇO", "t-aco b-60", 65, 12), ("FERRO", "t-ferro b-0", 40, 19),
]
PREMIUM = {"b-100", "b-top", "b-90"}   # tiers com brilho e animação própria
ORNAMENTOS = {"b-100", "b-top", "b-90", "b-80"}   # tiers com peças de moldura (louros, coroa, aletas) = chaves de ORN_PAL em carta.js
# ───────────────────────────────────────────────────────────────────────────────────────────────────────────

FALHAS, PULADOS = [], []
ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
RAPIDO, TOP5 = "--rapido" in sys.argv, "--top5" in sys.argv


def quer(grupo):
    return not ARGS or any(a.lower() in grupo.lower() for a in ARGS)


def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond:
        FALHAS.append(nome)


def pular(nome, motivo):
    print(f"[PULOU] {nome} — {motivo}")
    PULADOS.append(nome)


def lum(rgb):
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    r, g, b = [f(v / 255) for v in rgb[:3]]
    return .2126 * r + .7152 * g + .0722 * b


def contraste(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def rgb_de(s):
    m = re.findall(r"[\d.]+", s or "")
    return [float(x) for x in m[:3]] if len(m) >= 3 else None


# ───────────────────────── servidor estático (só leitura) ─────────────────────────
h = functools.partial(type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=RAIZ)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = f"http://127.0.0.1:{srv.server_address[1]}/"

# JS auxiliar injetado nas páginas: monta o cartão sintético de cada tier num contêiner visível
JS_MONTA = """([P, pos, id, vivo]) => {
  if (!document.getElementById('t-iso')) { const st = document.createElement('style'); st.id = 't-iso'; document.querySelectorAll('body > *:not(.t-host)').forEach(e => e.setAttribute('data-t-oculto', '')); st.textContent = '[data-t-oculto]{display:none!important} html,body{background:transparent!important}'; document.head.appendChild(st); }
  const ms = [{mes:'Teste/2026',pontos:P-3,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]},
              {mes:'Teste/2026',pontos:P,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]}];
  document.querySelectorAll('.t-host').forEach(e => e.remove());
  const host = document.createElement('div'); host.className = 't-host c-captura';
  host.style.cssText = 'position:absolute;left:20px;top:20px;width:332px;display:flow-root;background:transparent;z-index:99';
  host.innerHTML = Carta.html({nome:'Teste Silva',equipe:'EQ 1'}, ms, id || 'x', !vivo);   // vivo=true: registra no Movimento (anima como no álbum)
  document.body.appendChild(host);
  return host.querySelector('.carta').className;
}"""
JS_AGENTE = "({nome:'Teste Silva',equipe:'EQ 1'})"


def ms_sint(P, pos):
    return [{"mes": "Teste/2026", "pontos": P - 3, "pos": pos, "total": 20, "trab": 90, "esp": 100, "turnos_sem": 2, "detalhe": []},
            {"mes": "Teste/2026", "pontos": P, "pos": pos, "total": 20, "trab": 90, "esp": 100, "turnos_sem": 2, "detalhe": []}]


from playwright.sync_api import sync_playwright

try:
    from PIL import Image
    import numpy as np
except Exception:   # sem Pillow/numpy não dá para comparar pixels
    Image = np = None

with sync_playwright() as p:
    nav = p.chromium.launch()

    def pagina(reduzido=False, bloquear_lib=False, w=1100, h=900, dsf=2):
        ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=dsf, reduced_motion="reduce" if reduzido else "no-preference")
        pg = ctx.new_page(); erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        if bloquear_lib:
            pg.route("**/assets/html-to-image.js", lambda r: r.abort())
        pg.goto(U + "album.html"); pg.wait_for_function("window.Carta && window.AGENTES_DADOS", timeout=10000)
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(600)
        pg.erros = erros
        return pg

    # ═════════════ 1. TIERS: estrutura e medidas ═════════════
    if quer("tiers") or quer("estrutura") or quer("medidas"):
        print("\n== 1. tiers: estrutura e medidas ==")
        pg = pagina()
        for nome, marcas, P, pos in TIERS:
            cls = pg.evaluate(JS_MONTA, [P, pos, "x"])
            ok = all(m in cls.split() for m in marcas.split())
            checar(f"{nome}: classes do tier ({marcas}) presentes", ok, cls)
            r = pg.evaluate("""() => { const c = document.querySelector('.t-host .carta'), rc = c.getBoundingClientRect();
              const rod = c.querySelector('.c-rodape').textContent, fora = [];
              c.querySelectorAll('.c-ovr, .c-nome, .c-rodape, .c-stats > div, .c-foto, .c-topo').forEach(e => { const x = e.getBoundingClientRect();
                if (x.left < rc.left - 1 || x.right > rc.right + 1 || x.top < rc.top - 1 || x.bottom > rc.bottom + 1) fora.push(e.className); });
              const med = Carta.medidas([{mes:'T',pontos:%s-3,pos:%d,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]},{mes:'T',pontos:%s,pos:%d,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]}], 'x');
              return { w: rc.width, h: rc.height, rod, fora, sc: c.scrollHeight - c.clientHeight, st: med.st, nota: Math.min(99, Math.round(%s)) }; }""" % (P, pos, P, pos, P))
            checar(f"{nome}: rodapé mostra o nome do tier", nome in r["rod"], r["rod"])
            checar(f"{nome}: nada do conteúdo passa da borda do cartão", not r["fora"] and r["sc"] <= 1, str(r["fora"]) + f" sobra={r['sc']}")
            checar(f"{nome}: seis medidas em 0–99 e a até {CONFIG['BANDA_MEDIDAS']} pontos da nota",
                   len(r["st"]) == 6 and all(0 <= v <= 99 and abs(v - r["nota"]) <= CONFIG["BANDA_MEDIDAS"] for _, v in r["st"]), str(r["st"]))
        checar("tiers: sem erro de script na página", not pg.erros, str(pg.erros))
        pg.context.close()

    # ═════════════ 2. CORES, BORDAS, TIPOGRAFIA, EFEITOS (invariantes, não valores) ═════════════
    if quer("cores") or quer("bordas") or quer("tipografia") or quer("efeitos"):
        print("\n== 2. cores, bordas, tipografia e efeitos ==")
        pg = pagina()
        raio_png = re.search(r"var FORMA_R = (\d+);", open(os.path.join(RAIZ, "assets/carta.js"), encoding="utf-8").read())
        for nome, marcas, P, pos in TIERS:
            pg.evaluate(JS_MONTA, [P, pos, "x"])
            r = pg.evaluate("""() => { const c = document.querySelector('.t-host .carta'), cs = getComputedStyle(c);
              const v = n => cs.getPropertyValue(n).trim();
              const norm = s => { const e = document.createElement('i'); e.style.color = s; document.body.appendChild(e); const o = getComputedStyle(e).color; e.remove(); return o; };
              // a nota usa texto vazado (gradiente com background-clip:text): a «cor» é a média das paradas do gradiente
              const grad = s => { const e = el(s); if (!e) return null; const k = getComputedStyle(e); if (k.color !== 'rgba(0, 0, 0, 0)') return k.color; const m = (k.backgroundImage.match(/rgb\\([^)]*\\)/g) || []).map(x => x.match(/[\\d.]+/g).slice(0, 3).map(Number)); if (!m.length) return null; const mm = [0, 1, 2].map(i => Math.round(m.reduce((a, b) => a + b[i], 0) / m.length)); return 'rgb(' + mm.join(',') + ')'; };
              const el = s => c.querySelector(s), cor = s => el(s) ? getComputedStyle(el(s)).color : null, fs = s => el(s) ? parseFloat(getComputedStyle(el(s)).fontSize) : null;
              const fam = s => el(s) ? getComputedStyle(el(s)).fontFamily : '';
              const brilho = !!c.querySelector('.c-brilho'), raios = !!c.querySelector('.c-estrelas'), conj = c.closest('.c-conj') || c.parentElement;
              return { c1: norm(v('--c1')), c2: norm(v('--c2')), b1: norm(v('--b1')), b2: norm(v('--b2')), b3: norm(v('--b3')), bw: parseFloat(v('--bw')), raio: parseFloat(getComputedStyle(c).borderTopLeftRadius),
                nota: grad('.c-ovr b'), nome: cor('.c-nome'), rod: cor('.c-rodape'), chip: cor('.c-stats b'),
                fNota: fs('.c-ovr b'), fNome: fs('.c-nome'), fRod: fs('.c-rodape'), fChip: fs('.c-stats b'), fChipSig: fs('.c-stats span'),
                famNota: fam('.c-ovr b'), famNome: fam('.c-nome'), famRod: fam('.c-rodape'),
                brilho, raios, louros: !!conj.querySelector('.c-orna-atras'), coroa: !!conj.querySelector('.c-orna-frente'),
                sombra: cs.boxShadow !== 'none' || cs.filter !== 'none' || getComputedStyle(conj).filter !== 'none',
                fontesOk: document.fonts.check('700 20px "Barlow Semi Condensed"') && document.fonts.check('600 14px "IBM Plex Sans"') }; }""")
            c1, c2 = rgb_de(r["c1"]), rgb_de(r["c2"])
            fundo = [(a + b) / 2 for a, b in zip(c1, c2)] if c1 and c2 else None
            checar(f"{nome}: cores do tier (--c1, --c2, --b1..b3) existem e são válidas", all(r[k] and rgb_de(r[k]) for k in ("c1", "c2", "b1", "b2", "b3")), str({k: r[k] for k in ("c1", "c2", "b1", "b2", "b3")}))
            if fundo:
                ct = {k: contraste(rgb_de(r[k]), fundo) for k in ("nota", "nome", "rod", "chip") if r[k] and rgb_de(r[k])}
                checar(f"{nome}: contraste da nota ≥ {CONFIG['CONTRASTE_NOTA']}", ct.get("nota", 0) >= CONFIG["CONTRASTE_NOTA"], f"{ct.get('nota', 0):.2f}")
                # (nome, rodapé e chips: medidos nos pixels logo abaixo; --c1/--c2 não representam fundos em degradê)
                # contraste REAL: cor do texto × cor mediana dos pixels atrás dele (pega fundos que não vêm de --c1/--c2, como o roxo do Destaque)
                ruim_px = {}
                for k, sel in (("nome", ".c-nome"), ("rod", ".c-rodape"), ("chip", ".c-stats b")):
                    if not (r[k] and rgb_de(r[k])): continue
                    try:
                        im = Image.open(io.BytesIO(pg.locator(f".t-host {sel}").first.screenshot(omit_background=False))).convert("RGB")
                    except Exception:
                        continue
                    med = [float(np.median(np.asarray(im)[:, :, i])) for i in range(3)]
                    cr = contraste(rgb_de(r[k]), med)
                    if cr < CONFIG["CONTRASTE_TEXTO"]: ruim_px[k] = round(cr, 2)
                checar(f"{nome}: contraste medido nos pixels (nome, rodapé, chips) ≥ {CONFIG['CONTRASTE_TEXTO']}", not ruim_px, str(ruim_px))
                var_b = contraste(rgb_de(r["b1"]), rgb_de(r["b3"]))
                checar(f"{nome}: a borda tem relevo (b1 × b3 com razão ≥ {CONFIG['CONTRASTE_BORDA_RELEVO']})", var_b >= CONFIG["CONTRASTE_BORDA_RELEVO"], f"{var_b:.2f}")
            checar(f"{nome}: espessura da borda (--bw) entre {CONFIG['BORDA_PX'][0]} e {CONFIG['BORDA_PX'][1]} px", CONFIG["BORDA_PX"][0] <= (r["bw"] or 0) <= CONFIG["BORDA_PX"][1], str(r["bw"]))
            checar(f"{nome}: raio do cartão entre {CONFIG['RAIO_PX'][0]} e {CONFIG['RAIO_PX'][1]} px", CONFIG["RAIO_PX"][0] <= r["raio"] <= CONFIG["RAIO_PX"][1], str(r["raio"]))
            if raio_png:
                checar(f"{nome}: raio do HTML igual ao raio desenhado no PNG (FORMA_R)", abs(r["raio"] - int(raio_png.group(1))) <= 1, f"css={r['raio']} png={raio_png.group(1)}")
            menores = {k: r[k] for k in ("fNome", "fRod", "fChip", "fChipSig") if r[k] is not None and r[k] < CONFIG["FONTE_MIN_PX"]}
            checar(f"{nome}: nenhum texto menor que {CONFIG['FONTE_MIN_PX']} px", not menores, str(menores))
            checar(f"{nome}: tipografia usa {' ou '.join(CONFIG['FAMILIAS'])} e as fontes estão carregadas",
                   r["fontesOk"] and all(any(f in r[k] for f in CONFIG["FAMILIAS"]) for k in ("famNota", "famNome", "famRod")), f"{r['famNota']} | {r['famNome']}")
            premium = any(m in PREMIUM for m in marcas.split()); orn = any(m in ORNAMENTOS for m in marcas.split())
            checar(f"{nome}: efeitos {'premium (brilho + sombra + moldura)' if premium else 'sem brilho premium'}",
                   (r["brilho"] and r["sombra"] and (r["louros"] or r["coroa"])) if premium else True, f"brilho={r['brilho']} sombra={r['sombra']} louros={r['louros']} coroa={r['coroa']}")
            checar(f"{nome}: peças de moldura {'presentes' if orn else 'ausentes'} (ORN_PAL)", (r["louros"] or r["coroa"]) == orn, f"louros={r['louros']} coroa={r['coroa']}")
            if "b-100" in marcas or "b-top" in marcas:
                checar(f"{nome}: raios/arcos (c-estrelas) presentes", r["raios"])
        # paletas do PNG em canvas cobrem os mesmos tiers do CSS (sem exigir valores)
        cj = open(os.path.join(RAIZ, "assets/carta.js"), encoding="utf-8").read()
        cc = open(os.path.join(RAIZ, "assets/carta.css"), encoding="utf-8").read()
        for chave in ("b-100", "b-top", "b-90", "b-80"):
            checar(f"paleta das peças de moldura ({chave}) existe em ORN_PAL e no CSS", re.search(r"'%s':\s*\[" % chave, cj) is not None and (".carta.%s" % chave) in cc)
        for t in ("t-prata", "t-bronze", "t-aco", "t-ferro"):
            checar(f"tier {t} tem regra no CSS", (".carta.%s" % t) in cc)
        pg.context.close()

    # ═════════════ 3. TEMA DA SALA (escuro por padrão; botão leva ao claro) ═════════════
    if quer("tema"):
        print("\n== 3. tema da Sala de Troféus ==")
        pg = pagina()
        t0 = pg.evaluate("document.documentElement.getAttribute('data-theme')")
        checar("Sala nasce escura (data-tema-padrao=dark)", t0 == "dark", str(t0))
        if pg.locator("[data-tema-btn]").count():
            pg.click("[data-tema-btn]"); pg.wait_for_timeout(300)
            checar("botão de tema leva ao claro", pg.evaluate("document.documentElement.getAttribute('data-theme')") == "light")
        pg.context.close()

    # ═════════════ 4. HTML × PNG ═════════════
    def grade(img, cols, linhas):
        a = np.asarray(img.convert("RGBA")).astype(float)
        al = a[..., 3:4] / 255.0
        rgb = a[..., :3] * al + 128 * (1 - al)     # compõe sobre cinza neutro
        H, W = rgb.shape[:2]
        return np.array([[rgb[int(j * H / linhas):int((j + 1) * H / linhas), int(i * W / cols):int((i + 1) * W / cols)].mean(axis=(0, 1)) for i in range(cols)] for j in range(linhas)]), (a[..., 3] > 12)

    if quer("png"):
        print("\n== 4. HTML × PNG ==")
        if Image is None:
            pular("HTML × PNG", "instale Pillow e numpy (pip install pillow numpy)")
        else:
            for variante, bloquear, tol in (("principal (html-to-image)", False, CONFIG["PNG_DIF_MEDIA"]), ("plano B (canvas)", True, CONFIG["PNG_CANVAS_DIF_MEDIA"])):
                pg = pagina(reduzido=True, bloquear_lib=bloquear)
                for nome, marcas, P, pos in TIERS:
                    pg.evaluate(JS_MONTA, [P, pos, "x"]); pg.wait_for_timeout(250)
                    shot = pg.locator(".t-host").screenshot(omit_background=True)
                    b64 = pg.evaluate("""async ([P, pos]) => { const ms = [{mes:'Teste/2026',pontos:P-3,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]},{mes:'Teste/2026',pontos:P,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]}];
                      const bl = await Carta.png({nome:'Teste Silva',equipe:'EQ 1'}, ms, {id:'x', transparente:true}); const u = new Uint8Array(await bl.arrayBuffer());
                      let s = ''; for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192)); return btoa(s); }""", [P, pos])
                    A, B = Image.open(io.BytesIO(shot)), Image.open(io.BytesIO(base64.b64decode(b64)))
                    # o plano B tem margem própria: compara só o miolo comum, redimensionando o PNG ao tamanho do HTML
                    B0 = B.resize(A.size); B = B0.copy()
                    B.putalpha(A.convert("RGBA").split()[3])   # compara só o que o HTML pinta (o plano B desenha fundo opaco)
                    ga, ma = grade(A, *CONFIG["PNG_GRADE"]); gb, _ = grade(B, *CONFIG["PNG_GRADE"]); _, mb = grade(B0, *CONFIG["PNG_GRADE"])
                    dif = float(np.abs(ga - gb).mean()); ba, bb = ga.mean(), gb.mean()
                    checar(f"{nome} [{variante}]: cores do PNG batem com o HTML (dif. média {dif:.1f} ≤ {tol})", dif <= tol, f"{dif:.1f}")
                    checar(f"{nome} [{variante}]: brilho geral parecido (|Δ| ≤ {tol/2:.0f})", abs(ba - bb) <= tol / 2, f"{ba:.0f} × {bb:.0f}")
                    # ornamentos (louros/coroa) fora do cartão: se o HTML tem, o PNG também precisa ter, e vice-versa
                    def margem(m):
                        w = m.shape[1]; return float(m[:, : int(w * 0.07)].mean() + m[:, int(w * 0.93):].mean())
                    ha, hb = margem(ma) > 0.05, margem(mb) > 0.05
                    if not bloquear and ("b-90" in marcas or "b-80" in marcas or "b-100" in marcas):   # plano B pinta fundo opaco: sem máscara para comparar
                        checar(f"{nome} [{variante}]: ornamentos laterais presentes em HTML e PNG", ha == hb, f"html={ha} png={hb}")
                pg.context.close()

    # ═════════════ 5. MOVIMENTO REDUZIDO ═════════════
    if quer("movimento") or quer("reduzido"):
        print("\n== 5. movimento reduzido ==")
        for reduzido in (False, True):
            pg = pagina(reduzido=reduzido)
            for nome, marcas, P, pos in TIERS:
                pg.evaluate(JS_MONTA, [P, pos, "x", True])
                pg.evaluate("document.querySelector('.t-host').classList.remove('c-captura')")   # .c-captura congela animações: aqui queremos o cartão como no álbum
                pg.wait_for_timeout(900)
                n = pg.evaluate("""() => { const h = document.querySelector('.t-host'); return h.getAnimations({subtree: true}).filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity && a.playState === 'running').length; }""")
                premium = any(m in PREMIUM for m in marcas.split())
                if reduzido:
                    checar(f"{nome}: com movimento reduzido nenhuma animação infinita roda", n == 0, f"{n} rodando")
                elif premium and ("b-100" in marcas or "b-top" in marcas):
                    checar(f"{nome}: com movimento normal a moldura anima (≥ 1 animação infinita)", n >= 1, f"{n}")
            mov = pg.evaluate("window.Movimento ? Movimento.reduz() : null")
            checar(f"Movimento.reduz() reflete a preferência do sistema ({'reduzido' if reduzido else 'normal'})", mov == reduzido, str(mov))
            pg.context.close()

    # ═════════════ 7. PÁGINA: desempenho, estados, fotos, impressão ═════════════
    if quer("pagina") or quer("desempenho") or quer("estados") or quer("recorte"):
        print("\n== 7. página da Sala ==")
        pg = pagina(w=1300, h=1000)
        n_slots = pg.evaluate("document.querySelectorAll('.slot').length")
        n_cartas = pg.evaluate("document.querySelectorAll('.slot .carta').length")
        n_adiados = pg.evaluate("document.querySelectorAll('.slot.adiado').length")
        checar("carregamento sob demanda: no início só parte das cartinhas vira cartão", n_slots > CONFIG["ADIAR_MIN"] and 0 < n_adiados < n_slots and n_cartas + n_adiados == n_slots, f"slots={n_slots} cartas={n_cartas} adiados={n_adiados}")
        checar("esqueleto no lugar de cada cartinha adiada (com texto para leitor de tela)", pg.evaluate("[...document.querySelectorAll('.slot.adiado')].every(e => e.querySelector('.slot-esq[aria-label]'))"))
        for _ in range(40):   # rolagem em passos, como a pessoa faz (um salto direto ao fim pula o meio, que só abre quando chegamos perto)
            pg.mouse.wheel(0, 700); pg.wait_for_timeout(120)
        pg.wait_for_timeout(1200)
        checar("rolando até o fim, todas viram cartão (nada fica preso no esqueleto)", pg.evaluate("document.querySelectorAll('.slot.adiado').length") == 0)
        checar("depois de rolar, nenhum esqueleto sobra e a contagem de cartões bate com a de slots", pg.evaluate("document.querySelectorAll('.slot .carta').length") == n_slots)
        pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(300)
        # animações: só as cartas que estão perto da tela ficam .vivo
        vivos = pg.evaluate("document.querySelectorAll('.carta.vivo').length")
        checar("animações pausam fora da tela (menos cartas .vivo do que cartas)", 0 < vivos < n_slots, f"vivo={vivos} de {n_slots}")
        # fonte da nota: algarismos tabulares e peso próprio
        f = pg.evaluate("(() => { const b = document.querySelector('.carta .c-ovr b'); const c = getComputedStyle(b); return [c.fontVariantNumeric, c.fontWeight, c.fontFamily]; })()")
        checar("nota com algarismos tabulares", "tabular-nums" in f[0], f[0])
        checar("nota com peso próprio (≥ 700) e família do sistema", int(f[1]) >= CONFIG["NOTA_PESO_MIN"] and any(x in f[2] for x in CONFIG["FAMILIAS"]) or "Barlow" in f[2], str(f))
        # aviso de fotos
        av = pg.evaluate("(() => { const e = document.getElementById('avisoFotos'); return [e.hidden, e.textContent]; })()")
        checar("aviso «faltam fotos» aparece e diz como completar", av[0] is False and "padronizar_foto" in av[1], str(av))
        # estado vazio com saída
        pg.fill("#fBusca", "zzzz-nao-existe"); pg.wait_for_timeout(400)
        checar("estado vazio: mensagem e botão «Limpar filtros»", pg.locator(".estado.vazio [data-limpar]").count() == 1)
        pg.click(".estado.vazio [data-limpar]"); pg.wait_for_timeout(500)
        checar("«Limpar filtros» do estado vazio traz as cartinhas de volta", pg.evaluate("document.querySelectorAll('.slot').length") == n_slots)
        # folha de recorte: 8 por A4, na CSS de impressão
        pg.evaluate("Preguica.tudo(); document.body.classList.add('imp-recorte')"); pg.emulate_media(media="print"); pg.wait_for_timeout(500)
        g = pg.evaluate("""(() => { const s = [...document.querySelectorAll('#album .slot, #podio:not([hidden]) .slot')]; const r = s[0].getBoundingClientRect(); const mm = 96 / 25.4;
          const mk = getComputedStyle(s[1], '::before').backgroundImage;
          const topos = [...new Set(s.slice(0, 12).map(e => Math.round(e.getBoundingClientRect().top)))];
          return { larg: r.width / mm, alt: r.height / mm, marcas: (mk.match(/linear-gradient/g) || []).length, linhas: topos.length }; })()""")
        checar("folha de recorte: cartinha de 63 mm de largura", abs(g["larg"] - 63) < 1.5, str(g))
        checar("folha de recorte: 8 marcas de corte por cartinha", g["marcas"] == 8, str(g))
        pg.emulate_media(media="screen")
        pg.context.close()

    # ═════════════ 6. ÁUDIO, VÍDEO E ANIMAÇÕES (só mede) ═════════════
    if quer("audio") or quer("video") or quer("animac"):
        print("\n== 6. áudio, vídeo e animações (somente leitura) ==")
        pg = pagina()
        sons = pg.evaluate("""async () => { const nomes = ['rasgar','giro','suspense','ding','bronze','prata','ouro','fanfarra','batida','trovao'], out = {};
          for (const n of nomes) { const b = await Som.renderizar(n, 1200, 4); if (!b) { out[n] = null; continue; }
            let pico = 0, soma = 0, nan = 0, N = 0; for (let c = 0; c < b.numberOfChannels; c++) { const d = b.getChannelData(c); for (let i = 0; i < d.length; i++) { const v = d[i]; if (v !== v) nan++; else { if (Math.abs(v) > pico) pico = Math.abs(v); soma += v * v; N++; } } }
            out[n] = { pico, rms: Math.sqrt(soma / Math.max(1, N)), nan, canais: b.numberOfChannels, dur: b.duration }; }
          return out; }""")
        for n, s in sons.items():
            if s is None:
                pular(f"som «{n}»", "OfflineAudioContext indisponível"); continue
            checar(f"som «{n}»: sem NaN, não é mudo (rms ≥ {CONFIG['AUDIO_RMS_MIN']}) e não passa de 0 dBFS", s["nan"] == 0 and s["rms"] >= CONFIG["AUDIO_RMS_MIN"] and s["pico"] <= CONFIG["AUDIO_PICO_MAX"], str(s))
        checar("áudio: Som.paraGravacao existe e devolve fluxo + fade", pg.evaluate("(()=>{const a=Som.paraGravacao&&Som.paraGravacao();if(!a)return false;const ok=!!a.stream&&typeof a.fade==='function'&&typeof a.tocar==='function';a.fechar();return ok})()"))
        # animações das cartas: só confirma que as APIs existem (não dispara nada)
        checar("animações: Movimento, CartaVideo e Carta expõem a API esperada", pg.evaluate("!!(window.Movimento&&Movimento.reduz&&window.CartaVideo&&CartaVideo.quadro&&CartaVideo.gerar&&CartaVideo.gerarTop&&window.Carta&&Carta.png)"))
        # quadro do vídeo: desenha sem erro em cada tier e produz pixels (não fica em branco)
        q = pg.evaluate("""async () => { const out = {}; const casos = %s;
          for (const [nome, P, pos] of casos) { const ms = [{mes:'Teste/2026',pontos:P-3,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]},{mes:'Teste/2026',pontos:P,pos:pos,total:20,trab:90,esp:100,turnos_sem:2,detalhe:[]}];
            try { const bl = await Carta.png({nome:'Teste Silva',equipe:'EQ 1'}, ms, {id:'x', transparente:true}), url = URL.createObjectURL(bl), img = new Image(); img.src = url; await img.decode();
              const lugar = pos <= 3 ? pos : 0, S = CartaVideo.preparar(img, {nome:'Teste Silva', lugar, pontos:P, mes:'Teste/2026', equipe:'EQ 1', pos, total:20});
              const c = document.createElement('canvas'); c.width = CartaVideo.W; c.height = CartaVideo.H; const x = c.getContext('2d'); let vis = 0;
              for (const t of [0.5, 1.4, 2.5, 4.5]) { CartaVideo.quadro(x, t, S); const d = x.getImageData(0, 0, c.width, c.height).data; let s = 0; for (let i = 0; i < d.length; i += 4 * 97) s += d[i] + d[i + 1] + d[i + 2]; vis += s > 0 ? 1 : 0; }
              out[nome] = vis; } catch (e) { out[nome] = 'erro ' + e.message; } }
          return out; }""" % json.dumps([[t[0], t[2], t[3]] for t in TIERS]))
        for nome, v in q.items():
            checar(f"vídeo: o quadro de «{nome}» desenha nos 4 instantes testados", v == 4, str(v))

        if RAPIDO:
            pular("gravação do vídeo", "--rapido")
        elif not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            pular("gravação do vídeo", "ffmpeg/ffprobe não encontrados")
        elif not pg.evaluate("CartaVideo.suportado()"):
            pular("gravação do vídeo", "MediaRecorder sem formato suportado neste navegador")
        else:
            def analisa(rotulo, b64, dur_ok):
                d = tempfile.mkdtemp(); f = os.path.join(d, "v.bin")
                open(f, "wb").write(base64.b64decode(b64))
                info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries", "stream=codec_type,width,height,nb_read_frames:format=duration", "-of", "json", f], capture_output=True, text=True).stdout or "{}")
                vs = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]; au = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
                dur = float(info.get("format", {}).get("duration", 0) or 0)
                checar(f"{rotulo}: tem faixa de vídeo 720×1280 e faixa de áudio", bool(vs) and bool(au) and (vs[0].get("width"), vs[0].get("height")) == (720, 1280), str(info.get("streams")))
                checar(f"{rotulo}: duração dentro do esperado {dur_ok}", dur_ok[0] <= dur <= dur_ok[1], f"{dur:.2f}s")
                if vs and dur:
                    fps = int(vs[0].get("nb_read_frames", 0) or 0) / dur
                    checar(f"{rotulo}: taxa de quadros ≥ {CONFIG['VIDEO_FPS_MIN']} fps (medida {fps:.1f}; sem GPU no teste)", fps >= CONFIG["VIDEO_FPS_MIN"], f"{fps:.1f}")
                if au and np is not None:
                    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"], capture_output=True).stdout
                    a = np.frombuffer(raw, dtype=np.float32)
                    if len(a):
                        pico = float(np.abs(a).max()); db = 20 * np.log10(max(pico, 1e-9)); fim = float(np.abs(a[-int(8000 * 0.15):]).max())
                        checar(f"{rotulo}: áudio audível (pico {db:.1f} dBFS ≥ {CONFIG['VIDEO_AUDIO_DB_MIN']})", db >= CONFIG["VIDEO_AUDIO_DB_MIN"], f"{db:.1f}")
                        checar(f"{rotulo}: fade no fim (último 0,15 s ≤ {CONFIG['VIDEO_FADE_RATIO']}× o pico)", fim <= CONFIG["VIDEO_FADE_RATIO"] * pico, f"fim={fim:.2f} pico={pico:.2f}")
                shutil.rmtree(d, ignore_errors=True)
            r = pg.evaluate("""async () => { const bl = await CartaVideo.gerar({nome:'Teste Silva',equipe:'EQ 1'}, %s, {lugar:1, id:'x'});
              const u = new Uint8Array(await bl.arrayBuffer()); let s = ''; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return s ? btoa(s) : ''; }""" % json.dumps(ms_sint(105, 1)))
            analisa("vídeo do 1º lugar (5 s)", r, CONFIG["VIDEO_DUR"])
            if TOP5:
                r5 = pg.evaluate("""async () => { const mk = (P, pos) => ({a: {nome:'Teste Silva',equipe:'EQ 1', k:'x'}, ms: %s.map(m => Object.assign({}, m, {pontos: m.pontos - (105 - P), pos})), lugar: pos, id:'x'});
                  const bl = await CartaVideo.gerarTop([mk(105,1), mk(104,2), mk(103,3), mk(102,4), mk(101,5)], {});
                  const u = new Uint8Array(await bl.arrayBuffer()); let s = ''; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }""" % json.dumps(ms_sint(105, 1)))
                total = 14.0
                analisa("vídeo do top 5 (≈14 s)", r5, (12.5, 16.5))
        checar("áudio/vídeo: sem erro de script na página", not pg.erros, str(pg.erros))
        pg.context.close()

    nav.close()

print()
if PULADOS:
    print(f"⚠ pulados: {len(PULADOS)} ({', '.join(PULADOS)})")
if FALHAS:
    print(f"❌ {len(FALHAS)} falha(s):"); [print("  -", f) for f in FALHAS]; sys.exit(1)
print("TUDO CERTO")
