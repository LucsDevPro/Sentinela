# -*- coding: utf-8 -*-
"""Testes de NAVEGADOR da Sessão 10: comparar meses, cartão do agente, linha do tempo.
Precisa de playwright + chromium (só na máquina de desenvolvimento). Uso: python3 scripts/test_sessao10_navegador.py"""
import functools, http.server, json, os, re, shutil, subprocess, sys, tempfile, threading
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS = []
def checar(n, c, d=""):
    print(f"[{'OK  ' if c else 'FALHOU'}] {n}" + (f" — {d}" if not c and d else ""))
    if not c: FALHAS.append(n)

trab = tempfile.mkdtemp()
for sub in ("data", "scripts", "assets"):
    shutil.copytree(os.path.join(RAIZ, sub), os.path.join(trab, sub), ignore=shutil.ignore_patterns("__pycache__", "csv"))
for f in ("agente.html", "comparar.html", "album.html"):
    shutil.copy(os.path.join(RAIZ, f), trab)
subprocess.run([sys.executable, "scripts/gerar_agentes.py"], cwd=trab, check=True, capture_output=True)
txt = open(os.path.join(trab, "assets/agentes_dados.js"), encoding="utf-8").read()
D = json.loads(txt[len("window.AGENTES_DADOS="):-1])["agentes"]
# um agente com mais de um mês e outro que pegou a parada de julho
alvo_k, alvo = next((k, a) for k, a in D.items() if len(a["meses"]) >= 3)
com_parada = next((a for a in D.values() if any(m["paradas"] for m in a["meses"])), None)

h = functools.partial(type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=trab)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h); U = f"http://127.0.0.1:{srv.server_address[1]}/"
threading.Thread(target=srv.serve_forever, daemon=True).start()
q = "?id=" + alvo_k if alvo_k.isdigit() else "?nome=" + alvo["nome"].replace(" ", "%20")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    nav = p.chromium.launch(); ctx = nav.new_context(viewport={"width": 1100, "height": 900}); pg = ctx.new_page()
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    # ---------- cartão + linha do tempo
    pg.goto(U + "agente.html" + q); pg.wait_for_timeout(900)
    ult = alvo["meses"][-1]
    checar("cartão aparece", pg.locator(".carta").count() == 1)
    checar("nota grande do cartão = nota do mês arredondada", pg.inner_text(".c-ovr b").strip() == str(round(ult["pontos"])), pg.inner_text(".c-ovr b"))
    vals = [int(x) for x in pg.eval_on_selector_all(".c-stats b", "e=>e.map(x=>x.textContent)")]
    checar("seis medidas entre 0 e 99", len(vals) == 6 and all(0 <= v <= 99 for v in vals), str(vals))
    ass = round(ult["trab"] / ult["esp"] * 100) if ult["esp"] else 0
    checar("ASS = dias trabalhados ÷ esperados", vals[0] == min(99, ass), f"{vals[0]} x {ass}")
    cls = pg.get_attribute(".carta", "class")
    esperado = "t-destaque" if (ult["pos"] <= 3 and ult["pontos"] >= 90) else "" if ult["pontos"] >= 90 else "t-prata" if ult["pontos"] >= 75 else "t-bronze"
    checar("nível do cartão segue a nota", (esperado in cls) if esperado else not re.search(r"t-(prata|bronze|destaque)", cls), cls)
    checar("tem texto alternativo", "Cartão de" in pg.get_attribute(".carta", "aria-label"))
    n_li = pg.locator(".tl > li").count()
    checar("linha do tempo tem um item por mês", n_li == len(alvo["meses"]), f"{n_li} x {len(alvo['meses'])}")
    primeiro = pg.locator(".tl > li").first
    checar("mês mais recente aparece primeiro", ult["mes"] in primeiro.inner_text())
    on = primeiro.locator(".lin").first.locator(".qd i.on").count(); tot = primeiro.locator(".lin").first.locator(".qd i").count()
    checar("quadradinhos = dias trabalhados / esperados", on == round(ult["trab"]) and tot == max(round(ult["esp"]), round(ult["trab"])), f"{on}/{tot}")
    checar("semanas aparecem dentro do mês aberto", primeiro.locator("ul li").count() == len([s for s in alvo["semanas"] if s["mes"] == ult["mes"]]))
    if com_parada:
        pg.goto(U + "agente.html?nome=" + com_parada["nome"].replace(" ", "%20")); pg.wait_for_timeout(700)
        checar("parada da equipe aparece como etiqueta (e não como falta)", pg.locator(".chip.par").count() >= 1 and "não conta como falta" in pg.inner_text(".tl-leg"))
    pg.goto(U + "agente.html" + q); pg.wait_for_timeout(500)
    pg.check("#apres")
    checar("modo apresentação borra nome e iniciais do cartão", pg.evaluate("getComputedStyle(document.querySelector('.c-nome')).filter") != "none" and pg.evaluate("getComputedStyle(document.querySelector('.c-foto .nome')).filter") != "none")
    pg.click("[data-tema-btn]"); pg.wait_for_timeout(600)
    checar("cartão continua legível no tema escuro", pg.locator(".carta").count() == 1 and pg.locator(".tl > li").count() == n_li)
    pg.evaluate("localStorage.removeItem('sentinelaTema')")
    m = ctx.new_page(); m.set_viewport_size({"width": 360, "height": 800}); m.goto(U + "agente.html" + q); m.wait_for_timeout(700)
    checar("agente: sem rolagem lateral no celular", m.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), str(m.evaluate("document.documentElement.scrollWidth")))
    m.close()

    # ---------- comparar meses
    c = ctx.new_page(); ec = []; c.on("pageerror", lambda e: ec.append(str(e)))
    c.goto(U + "comparar.html"); c.wait_for_timeout(900)
    linhas = c.locator("table.cmp tr:has(td a)").count()
    s, cai = int(c.inner_text("#nSobe")), int(c.inner_text("#nCai"))
    checar("há linhas de comparação", linhas > 0, str(linhas))
    checar("subiram + caíram ≤ total comparado", s + cai <= linhas, f"{s}+{cai} x {linhas}")
    c.click("button[data-f='sobe']"); c.wait_for_timeout(300)
    ls = c.locator("table.cmp tr:has(td a)"); ok = all("up" in (ls.nth(i).locator(".dl").get_attribute("class") or "") for i in range(ls.count()))
    checar("'Quem subiu' lista só quem subiu", ls.count() == s and ok, f"{ls.count()} x {s}")
    c.click("button[data-f='cai']"); c.wait_for_timeout(300)
    ls = c.locator("table.cmp tr:has(td a)")
    checar("'Quem caiu' lista só quem caiu", ls.count() == cai and all("down" in (ls.nth(i).locator(".dl").get_attribute("class") or "") for i in range(ls.count())))
    c.click("button[data-f='todos']")
    meses = c.eval_on_selector_all("#sDe option", "o=>o.map(x=>x.value)")
    c.select_option("#sDe", meses[0]); c.select_option("#sPara", meses[1]); c.wait_for_timeout(300)
    checar("troca de meses refaz a comparação", "→" in c.inner_text(".kpis") and meses[0] in c.inner_text("#res"))
    c.select_option("#sDe", meses[-2]); c.select_option("#sPara", meses[-1]); c.wait_for_timeout(300)
    mes_aberto = [mm for a in D.values() for mm in a["meses"] if mm["mes"] == meses[-1] and not mm["fechado"]]
    checar("aviso de mês aberto aparece quando o mês não está fechado", (c.locator("#avAberto").count() == 1) == bool(mes_aberto))
    c.check("#apres")
    checar("modo apresentação borra nomes na comparação", c.evaluate("getComputedStyle(document.querySelector('table.cmp a.nome')).filter") != "none")
    checar("gráfico por equipe desenhado", c.evaluate("document.getElementById('gEq').width") > 0)
    c.set_viewport_size({"width": 360, "height": 800}); c.wait_for_timeout(400)
    checar("comparar: sem rolagem lateral no celular", c.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), str(c.evaluate("document.documentElement.scrollWidth")))
    checar("comparar sem erros de script", not ec, str(ec))
    # menos de dois meses
    um = open(os.path.join(trab, "comparar.html"), encoding="utf-8").read().replace('<script src="assets/agentes_dados.js"></script>', '<script>window.AGENTES_DADOS={agentes:{a:{nome:"A",equipe:"E",meses:[{mes:"Maio/2026",pontos:90,pos:1,total:1}]}}}</script>')
    open(os.path.join(trab, "comparar_um.html"), "w", encoding="utf-8").write(um)
    e = ctx.new_page(); ee = []; e.on("pageerror", lambda x: ee.append(str(x))); e.goto(U + "comparar_um.html"); e.wait_for_timeout(500)
    checar("com um mês só, mostra aviso amigável", "pelo menos dois meses" in e.inner_text("#conteudo") and not ee)
    checar("agente sem erros de script", not erros, str(erros))

    # ---------- álbum
    al = ctx.new_page(); ea = []; al.on("pageerror", lambda e: ea.append(str(e)))
    al.goto(U + "album.html"); al.wait_for_timeout(900)
    mes = al.input_value("#fMes")
    do_mes = sorted([m for a in D.values() for m in a["meses"] if m["mes"] == mes and m["pontos"] is not None], key=lambda m: -m["pontos"])
    checar("álbum tem uma cartinha por agente do mês", al.locator(".slot").count() == len(do_mes), f"{al.locator('.slot').count()} x {len(do_mes)}")
    notas = [int(x) for x in al.eval_on_selector_all(".slot .c-ovr b", "e=>e.map(x=>x.textContent)")]
    checar("cartinhas ordenadas da maior nota para a menor", notas == sorted(notas, reverse=True), str(notas[:8]))
    checar("primeira cartinha é o 1º lugar", al.inner_text(".slot .n").strip() == "1º")
    pequena = al.evaluate("document.querySelector('.slot .carta').getBoundingClientRect().width")
    al.hover(".slot:nth-child(3)"); al.wait_for_timeout(450)
    grande = al.evaluate("document.querySelector('.slot:nth-child(3) .carta').getBoundingClientRect().width")
    checar("passar o mouse amplia a cartinha", grande > pequena * 1.3, f"{pequena:.0f} -> {grande:.0f}")
    al.mouse.move(0, 0); al.wait_for_timeout(400)
    checar("ao tirar o mouse volta ao tamanho do álbum", abs(al.evaluate("document.querySelector('.slot:nth-child(3) .carta').getBoundingClientRect().width") - pequena) < 2)
    al.keyboard.press("Tab")
    eq1 = al.eval_on_selector_all("#fEq option", "o=>o.map(x=>x.value)")[1]
    al.select_option("#fEq", eq1); al.wait_for_timeout(250)
    checar("filtro por equipe", all(eq1.replace("Equipe ", "EQ ") in t for t in al.eval_on_selector_all(".slot .c-pos", "e=>e.map(x=>x.textContent)")) and al.locator(".slot").count() > 0)
    al.select_option("#fEq", ""); al.fill("#fBusca", alvo["nome"].split()[0][:4]); al.wait_for_timeout(250)
    checar("busca por nome", al.locator(".slot").count() >= 1 and al.locator(".slot").count() < len(do_mes))
    al.fill("#fBusca", "zzzzzz"); al.wait_for_timeout(200)
    checar("sem resultado mostra aviso", "Nenhuma cartinha" in al.inner_text("#resumo"))
    al.fill("#fBusca", ""); al.select_option("#fNivel", "OURO"); al.wait_for_timeout(250)
    checar("filtro por nível", all("OURO" in t for t in al.eval_on_selector_all(".slot .c-rodape span:first-child", "e=>e.map(x=>x.textContent)")))
    al.select_option("#fNivel", ""); al.check("#apres")
    checar("modo apresentação borra nomes do álbum", al.evaluate("getComputedStyle(document.querySelector('.slot .c-nome')).filter") != "none")
    checar("clique na cartinha leva para a página do agente", "agente.html" in al.get_attribute(".slot", "href"))
    al.set_viewport_size({"width": 360, "height": 800}); al.wait_for_timeout(300)
    checar("álbum: sem rolagem lateral no celular", al.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), str(al.evaluate("document.documentElement.scrollWidth")))
    checar("álbum sem erros de script", not ea, str(ea))
    vazio = open(os.path.join(trab, "album.html"), encoding="utf-8").read().replace('<script src="assets/agentes_dados.js"></script>', '<script>window.AGENTES_DADOS={agentes:{}}</script>')
    open(os.path.join(trab, "album_vazio.html"), "w", encoding="utf-8").write(vazio)
    av = ctx.new_page(); eav = []; av.on("pageerror", lambda e: eav.append(str(e))); av.goto(U + "album_vazio.html"); av.wait_for_timeout(500)
    checar("álbum sem dados mostra aviso", "Ainda não há cartinhas" in av.inner_text("main") and not eav, str(eav))
    # ---------- imagem da cartinha / WhatsApp
    im = ctx.new_page(); ei = []; im.on("pageerror", lambda e: ei.append(str(e))); im.goto(U + "agente.html" + q); im.wait_for_timeout(700)
    with im.expect_download() as dl:
        im.click("#bBaixar")
    arq = dl.value.path(); bruto = open(arq, "rb").read()
    import struct
    checar("baixa um PNG de verdade", bruto[:8] == b"\x89PNG\r\n\x1a\n" and len(bruto) > 20000, str(len(bruto)))
    larg, alt = struct.unpack(">II", bruto[16:24])
    checar("imagem tem proporção de cartinha", 600 <= larg <= 700 and 1.3 < alt / larg < 1.5, f"{larg}x{alt}")
    checar("nome do arquivo identifica a cartinha", dl.value.suggested_filename.startswith("cartinha-") and dl.value.suggested_filename.endswith(".png"), dl.value.suggested_filename)
    checar("mostra aviso depois de baixar", "baixada" in im.inner_text("#msgImg"))
    px = im.evaluate("""async () => { const bl = await Carta.png(Object.values(AGENTES_DADOS.agentes)[0], Object.values(AGENTES_DADOS.agentes)[0].meses);
      const bm = await createImageBitmap(bl), c = document.createElement('canvas'); c.width = bm.width; c.height = bm.height; const x = c.getContext('2d'); x.drawImage(bm, 0, 0);
      const g = (a, b) => Array.from(x.getImageData(a, b, 1, 1).data); return { canto: g(3, 3), centro: g(Math.round(bm.width * .5), Math.round(bm.height * .5)), n: g(Math.round(bm.width * .5), Math.round(bm.height * .5) - 120) }; }""")
    checar("fora da carta o fundo é claro; dentro, a cor da carta", px["canto"][0] > 220 and px["centro"][2] < 200, str(px))
    im.evaluate("""() => { window.__chamadas = []; Object.defineProperty(navigator, 'canShare', { value: () => true, configurable: true });
      Object.defineProperty(navigator, 'share', { value: async d => { window.__chamadas.push({ n: d.files.length, tipo: d.files[0].type, nome: d.files[0].name, texto: d.text }); }, configurable: true }); }""")
    im.click("#bZap"); im.wait_for_timeout(1500)
    ch = im.evaluate("window.__chamadas")
    checar("WhatsApp: compartilha o arquivo PNG pelo celular", len(ch) == 1 and ch[0]["n"] == 1 and ch[0]["tipo"] == "image/png", str(ch))
    checar("texto do envio traz nome, nota e mês", alvo["nome"] in ch[0]["texto"] and "nota" in ch[0]["texto"] and ult["mes"] in ch[0]["texto"], ch[0]["texto"])
    im.check("#apres"); im.click("#bZap"); im.wait_for_timeout(1500)
    ch = im.evaluate("window.__chamadas")
    checar("modo apresentação: texto do envio não leva o nome", len(ch) == 2 and alvo["nome"] not in ch[1]["texto"], str(ch[-1]))
    im.evaluate("() => { Object.defineProperty(navigator, 'canShare', { value: undefined, configurable: true }); }")
    im.uncheck("#apres")
    ctx.route("https://wa.me/**", lambda r: r.fulfill(status=200, content_type="text/html", body="ok"))
    with im.expect_popup() as pop:
        with im.expect_download() as dl2:
            im.click("#bZap")
    pop.value.wait_for_load_state()
    checar("computador: baixa a imagem e abre o WhatsApp com o texto", "wa.me" in pop.value.url and "text=" in pop.value.url and dl2.value.suggested_filename.endswith(".png"), pop.value.url[:60])
    checar("imagem: sem erros de script", not ei, str(ei))
    cr = ctx.new_page(); cr.goto(U + "agente.html" + q); cr.wait_for_timeout(500)
    checar("logo do cartão carrega (máscara)", cr.evaluate("getComputedStyle(document.querySelector('.c-logo i')).webkitMaskImage || getComputedStyle(document.querySelector('.c-logo i')).maskImage").find("logo_carta.png") > 0)
    nav.close()
print("\n" + ("TUDO CERTO" if not FALHAS else f"{len(FALHAS)} FALHA(S): {FALHAS}"))
sys.exit(1 if FALHAS else 0)
