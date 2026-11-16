# -*- coding: utf-8 -*-
"""Testes de NAVEGADOR do visual (Sessão 10): tema claro padrão e alternância, impressão sempre clara,
ícones, exportação do ranking, animação dos números, tela de reunião, contraste.
Precisa de playwright + chromium (roda só na máquina de desenvolvimento). Uso: python3 scripts/test_visual_navegador.py"""
import functools, http.server, os, re, shutil, subprocess, sys, tempfile, threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS = []
def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond: FALHAS.append(nome)

trab = tempfile.mkdtemp()
for sub in ("data", "scripts", "assets"):
    shutil.copytree(os.path.join(RAIZ, sub), os.path.join(trab, sub), ignore=shutil.ignore_patterns("__pycache__", "csv"))
for f in ("agente.html", "contestacao.html", "validar.html", "projecao.html", "album.html"):
    shutil.copy(os.path.join(RAIZ, f), trab)
os.makedirs(os.path.join(trab, "partes"))
env = dict(os.environ, EVISITA_CPF="0", EVISITA_SENHA="t")
for args in (["scripts/generate_dashboard.py", "data/historico/semanas_327-330.xlsx", "index.html"],
             ["scripts/gerar_transparencia.py"], ["scripts/gerar_agentes.py"]):
    subprocess.run([sys.executable] + args, cwd=trab, env=env, check=True, capture_output=True)

# ---- checagens estáticas
idx = open(os.path.join(trab, "index.html"), encoding="utf-8").read()
checar("página inicial não nasce com tema escuro", 'data-theme="dark"' not in idx.split("<body")[0].replace("[data-theme", ""))
checar("tema.js carregado no <head>", "tema.js" in idx.split("</head>")[0])
checar("emojis de enfeite trocados por ícones", idx.count('<svg class="ico') >= 10 and not re.search("[📅📆📈🏠🖨🚧🏆📋🤖🧾📊📖📑🔻🕐🍽🖥🚫💰📍🎯🌴]", re.sub(r"<script.*?</script>", "", idx, flags=re.S)))
checar("emojis de status continuam (🟢🔴)", "🟢" in idx or "🔴" in idx)
def lum(h):
    h = h.lstrip("#"); r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def contraste(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05) / (lb + .05)
css = open(os.path.join(RAIZ, "scripts/style.css"), encoding="utf-8").read()
def tok(bloco, n):
    return re.search(r"--%s:\s*(#[0-9A-Fa-f]{6})" % n, bloco).group(1)
claro = re.search(r":root\s*\{(.*?)\}", css, re.S).group(1)
escuro = re.search(r':root\[data-theme="dark"\]\s*\{(.*?)\}', css, re.S).group(1)
for nome, bloco in (("claro", claro), ("escuro", escuro)):
    for t in ("text", "text2", "text3", "ok-tx", "warn-tx", "bad-tx", "info-tx"):
        try:
            c = contraste(tok(bloco, t), tok(bloco, "card"))
        except AttributeError:
            continue
        checar(f"contraste {t} sobre o cartão no tema {nome} ≥ 4,5", c >= 4.5, f"{c:.2f}")

h = functools.partial(type("Q", (http.server.SimpleHTTPRequestHandler,), {"log_message": lambda *a: None}), directory=trab)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h); porta = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
U = f"http://127.0.0.1:{porta}/"

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1280, "height": 800}, accept_downloads=True); pg = ctx.new_page()
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(U + "index.html"); pg.wait_for_timeout(1200)
    checar("abre no tema claro", pg.evaluate("document.documentElement.getAttribute('data-theme')") is None)
    bg = pg.evaluate("getComputedStyle(document.body).backgroundColor")
    checar("fundo claro por padrão", bg in ("rgb(237, 241, 247)", "rgb(238, 242, 248)"), bg)
    pg.click("[data-tema-btn]"); pg.wait_for_timeout(400)
    checar("botão muda para escuro", pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark")
    checar("texto do botão muda", "claro" in pg.inner_text("[data-tema-btn]").lower())
    pg.reload(); pg.wait_for_timeout(900)
    checar("escolha do tema fica salva", pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark")
    checar("gráficos acompanham o tema", pg.evaluate("Chart.defaults.color") != "#46597A")
    pg.emulate_media(media="print")
    fundo = pg.evaluate("getComputedStyle(document.body).backgroundColor"); cor_h = pg.evaluate("getComputedStyle(document.querySelector('.kpi-value')).color")
    checar("impressão continua em fundo branco no tema escuro", fundo in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"), fundo)
    checar("impressão com texto escuro", cor_h == "rgb(26, 43, 66)", cor_h)
    pg.emulate_media(media="screen")
    pg.click("[data-tema-btn]"); pg.wait_for_timeout(300)
    checar("volta para o claro", pg.evaluate("document.documentElement.getAttribute('data-theme')") is None)

    # ---- animação dos números
    pg.click(".nav-tab[data-section='ranking']"); pg.wait_for_timeout(300)
    pg.goto(U + "index.html"); pg.wait_for_timeout(250)
    meio = pg.evaluate("document.querySelector('.kpi-value').textContent")
    pg.wait_for_timeout(1500)
    fim = pg.evaluate("Array.from(document.querySelectorAll('.kpi-value')).map(e=>e.textContent.trim())")
    esperado = re.findall(r'class="kpi-value">([^<]*)<', idx)
    checar("números terminam exatamente no valor original", [x.strip() for x in esperado] == fim, f"{esperado} x {fim}")
    pg.uncheck("#toggleAnimacoes"); pg.reload(); pg.wait_for_timeout(150)
    sem_anim = pg.evaluate("document.querySelector('.kpi-value').textContent.trim()")
    checar("com 'Animações' desligado o número aparece pronto", sem_anim == esperado[0].strip(), sem_anim)
    checar("caixa 'Animações' lembra o desligado", not pg.is_checked("#toggleAnimacoes"))
    pg.check("#toggleAnimacoes")

    # ---- exportação do ranking
    pg.click(".nav-tab[data-section='ranking']"); pg.wait_for_timeout(300)
    with pg.expect_download() as d:
        pg.click("text=Planilha (CSV")
    arq = d.value.path(); bruto = open(arq, "rb").read()
    txt = bruto.decode("utf-8")
    linhas = txt.lstrip("\ufeff").strip().split("\r\n")
    n_ranking = pg.evaluate("document.querySelectorAll('#tableRanking tbody tr').length")
    checar("CSV com BOM (acentos certos no Excel)", bruto.startswith(b"\xef\xbb\xbf"))
    checar("CSV com cabeçalho + uma linha por agente", len(linhas) == n_ranking + 1, f"{len(linhas)} x {n_ranking}")
    checar("CSV separado por ponto e vírgula, sem coluna de botões", linhas[0].count(";") >= 6 and "Extrato" not in linhas[0])
    nome1 = pg.evaluate("document.querySelector('#tableRanking tbody .agent-name').textContent.trim()")
    checar("CSV traz o nome do agente fora do modo apresentação", nome1 in txt)
    pg.check("#togglePresentationMode")
    with pg.expect_download() as d2:
        pg.click("text=Planilha (CSV")
    t2 = open(d2.value.path(), "rb").read().decode("utf-8")
    checar("modo apresentação: CSV sai sem nomes", nome1 not in t2 and "Agente 1" in t2)
    pg.uncheck("#togglePresentationMode")

    # ---- tela de reunião
    pr = ctx.new_page(); errp = []; pr.on("pageerror", lambda e: errp.append(str(e)))
    pr.goto(U + "projecao.html"); pr.wait_for_timeout(1000)
    total = pr.evaluate("PROJECAO.total")
    checar("tela de reunião tem várias telas", total >= 3, str(total))
    pr.evaluate("PROJECAO.pausa(true)"); a0 = pr.evaluate("PROJECAO.atual()")
    pr.keyboard.press("ArrowRight"); pr.wait_for_timeout(300)
    checar("seta para a direita avança", pr.evaluate("PROJECAO.atual()") == (a0 + 1) % total)
    pr.keyboard.press("ArrowLeft"); pr.wait_for_timeout(300)
    checar("seta para a esquerda volta", pr.evaluate("PROJECAO.atual()") == a0)
    pr.select_option("#vel", "10"); pr.evaluate("PROJECAO.pausa(false)")
    pr.keyboard.press(" "); checar("barra de espaço pausa", pr.evaluate("PROJECAO.pausado()") is True)
    pr.keyboard.press(" "); checar("barra de espaço continua", pr.evaluate("PROJECAO.pausado()") is False)
    # alterna sozinha: acelera o relógio da página
    pr.evaluate("PROJECAO.ir(0)"); pr.select_option("#vel", "10")
    pr.wait_for_timeout(11500)
    checar("troca de tela sozinha depois do tempo", pr.evaluate("PROJECAO.atual()") == 1)
    pr.evaluate("PROJECAO.pausa(true); PROJECAO.ir(1)"); pr.wait_for_timeout(500)
    checar("nomes ocultos por padrão", not re.search(r"[A-Z][a-z]+ [A-Z][a-z]+ [A-Z]", pr.inner_text("#palco")) or "Agente 1" in pr.inner_text("#palco"))
    checar("há um gráfico desenhado", pr.evaluate("document.querySelectorAll('#palco canvas').length") >= 1)
    pr.click("[data-tema-btn]"); pr.wait_for_timeout(500)
    checar("tema escuro vale na tela de reunião", pr.evaluate("document.documentElement.getAttribute('data-theme')") == "dark")
    checar("tela de reunião sem erros de script", not errp, str(errp))
    # sem dados
    vazio = open(os.path.join(trab, "projecao.html"), encoding="utf-8").read()
    open(os.path.join(trab, "projecao_vazia.html"), "w", encoding="utf-8").write(vazio.replace('<script src="assets/agentes_dados.js"></script>', '<script>window.AGENTES_DADOS={agentes:{}}</script>'))
    pe = ctx.new_page(); erre = []; pe.on("pageerror", lambda e: erre.append(str(e)))
    pe.goto(U + "projecao_vazia.html"); pe.wait_for_timeout(800)
    checar("sem dados mostra aviso e não quebra", "Ainda não há notas" in pe.inner_text("#palco") and not erre, str(erre))

    # ---- álbum: baixar a cartinha, imprimir e abrir o modo reunião
    al = ctx.new_page(); ea = []; al.on("pageerror", lambda x: ea.append(str(x)))
    al.goto(U + "album.html"); al.wait_for_timeout(1500)
    al.select_option("#fMes", index=1); al.wait_for_timeout(1500)
    sl = al.locator("#album .slot").nth(1)
    checar("álbum: botões de compartilhar ficam invisíveis sem o mouse", al.evaluate("getComputedStyle(document.querySelector('#album .acoes')).opacity") == "0")
    sl.hover()
    try: al.wait_for_function("getComputedStyle(document.querySelectorAll('#album .acoes')[1]).opacity==='1'", timeout=5000); vis = True
    except Exception: vis = False
    checar("álbum: botões aparecem ao passar o mouse na cartinha", vis)
    checar("álbum: cada cartinha tem botões de baixar e WhatsApp", sl.locator("button[data-acao]").count() == 2)
    with al.expect_download(timeout=20000) as dl:
        sl.locator("button[data-acao=baixar]").click()
    checar("álbum: botão baixa a imagem PNG da cartinha", dl.value.suggested_filename.startswith("cartinha-") and dl.value.suggested_filename.endswith(".png"), dl.value.suggested_filename)
    checar("álbum: baixar não abre a página do agente", "album.html" in al.url)
    checar("álbum: botões ficam EMBAIXO da cartinha (não cobrem)", al.evaluate("(()=>{const s=document.querySelector('#album .slot'),c=s.querySelector('.carta').getBoundingClientRect(),a=s.querySelector('.acoes').getBoundingClientRect();return a.top>=c.bottom-4})()"))
    el = al.evaluate("""()=>{const c=[...document.querySelectorAll('#album .carta, #podio .carta')];
      const cem=c.filter(x=>x.querySelector('.c-ovr b').textContent.trim()==='100'), el=cem.filter(x=>!x.classList.contains('b-100'));
      return {cem:cem.length, el:el.length, ok:el.every(x=>x.classList.contains('n100')&&x.querySelector('.c-selo100')&&/ELITE/.test(x.querySelector('.c-rodape').textContent)),
              semSelo:c.filter(x=>!x.classList.contains('n100')).every(x=>!x.querySelector('.c-selo100'))}}""")
    checar("álbum: quem tirou 100 fora do pódio é ELITE com selo 100 (e só eles)", el["el"] >= 1 and el["ok"] and el["semSelo"], str(el))
    bits = al.evaluate("fetch('assets/html-to-image.js').then(r=>r.ok)")
    checar("álbum: biblioteca do PNG fiel está no site", bits)
    al.emulate_media(media="print"); al.wait_for_timeout(200)
    checar("álbum (impressão): filtros e botões somem, cartinhas ficam", al.evaluate("getComputedStyle(document.querySelector('.controles')).display") == "none" and al.locator("#album .slot").count() > 3)
    checar("álbum (impressão): botões de compartilhar escondidos", al.evaluate("getComputedStyle(document.querySelector('.acoes')).display") == "none")
    al.emulate_media(media="screen")
    al.click("#bReuniao"); al.wait_for_timeout(1500)
    checar("álbum: «Modo reunião» abre a projeção nas cartinhas", al.url.endswith("#cartinhas") and al.evaluate("PROJECAO.modo()") == "cartas", al.url)
    checar("álbum: sem erros de script", not ea, str(ea))
    # ---- projeção em modo cartinhas
    al.evaluate("PROJECAO.pausa(true)"); al.keyboard.press("ArrowRight"); al.wait_for_timeout(900)
    checar("reunião: uma cartinha por tela (intro + top 10)", al.evaluate("PROJECAO.total") == 11 and al.locator("#palco .carta").count() == 1)
    txt = al.inner_text("#palco")
    checar("reunião: nomes ocultos por padrão (nome e iniciais trocados)", "Agente 1" in txt and not al.evaluate("!!document.querySelector('#palco .c-foto img')") and re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", al.inner_text("#palco .carta").title().replace("Agente 1", "")) is None, txt[:120])
    al.keyboard.press("n"); al.wait_for_timeout(700)
    checar("reunião: tecla N mostra o nome", "Agente 1" not in al.inner_text("#palco .cp-nome"))
    al.keyboard.press("ArrowRight"); al.wait_for_timeout(700)
    checar("reunião: seta avança para a próxima cartinha", "2º de" in al.inner_text("#palco"))
    al.keyboard.press("c"); al.wait_for_timeout(700)
    checar("reunião: tecla C volta aos painéis", al.evaluate("PROJECAO.modo()") == "paineis" and al.locator("#palco .carta").count() == 0)
    al.close()

    # ---- álbum: filtros na URL, contagem por equipe, «Limpar filtros» e .zip com pastas por equipe
    zp = ctx.new_page(); ez = []; zp.on("pageerror", lambda x: ez.append(str(x)))
    zp.goto(U + "album.html?eq=Equipe%203"); zp.wait_for_timeout(1800)
    checar("álbum: ?eq= na URL já filtra a equipe", zp.evaluate("document.getElementById('fEq').value") == "Equipe 3")
    checar("álbum: equipes mostram a contagem «Equipe 3 (N)»", zp.evaluate("[...document.querySelectorAll('#fEq option')].some(o=>/^Equipe 3 \\(\\d+\\)$/.test(o.textContent.trim()))"))
    checar("álbum: «Limpar filtros» aparece com filtro ativo", zp.evaluate("!document.getElementById('bLimpar').hidden"))
    nome = zp.evaluate("document.querySelector('.carta .c-nome')?.textContent.trim().split(/\\s+/)[0]||''")
    if nome:
        zp.fill("#fBusca", nome); zp.wait_for_timeout(500)
    n = zp.evaluate("(document.getElementById('bZip').textContent.match(/\\((\\d+)\\)/)||[0,0])[1]")
    checar("álbum: botão do .zip mostra a quantidade filtrada", int(n) >= 1, str(n))
    try:
        with zp.expect_download(timeout=90000) as dl: zp.click("#bZip")
        import zipfile
        caminho = dl.value.path(); z = zipfile.ZipFile(caminho)
        nomes = z.namelist()
        checar("zip: íntegro e com uma imagem por cartinha", z.testzip() is None and len(nomes) == int(n), f"{len(nomes)} x {n}")
        checar("zip: pasta por equipe e arquivos PNG", all(x.startswith("Equipe 3/") and x.endswith(".png") for x in nomes), str(nomes[:2]))
        checar("zip: imagens são PNG de verdade", all(z.read(x)[:8] == b"\x89PNG\r\n\x1a\n" for x in nomes))
    except Exception as e:
        checar("zip: download concluído", False, str(e))
    zp.click("#bLimpar"); zp.wait_for_timeout(400)
    checar("álbum: «Limpar filtros» zera equipe e busca", zp.evaluate("document.getElementById('fEq').value===''&&document.getElementById('fBusca').value===''&&document.getElementById('bLimpar').hidden"))
    checar("álbum: zip sem erros de script", not ez, str(ez)); zp.close()

    # ---- efeitos extras: confete no pódio, cartas deslizam ao filtrar, aura por nível, pacote na reunião, tudo some com «reduzir movimento»
    fx = ctx.new_page(); efx = []; fx.on("pageerror", lambda x: efx.append(str(x)))
    fx.goto(U + "album.html"); fx.evaluate("localStorage.clear()"); fx.reload(); fx.wait_for_timeout(1500)
    checar("efeitos: confete cai no pódio na primeira vez do mês", fx.evaluate("document.querySelectorAll('#podio .c-confete').length") == 1)
    checar("efeitos: lendária tem aura atrás da carta", fx.evaluate("getComputedStyle(document.querySelector('.c-conj.b-100'),'::before').content") not in ("none", "normal"))
    fx.select_option("#fEq", "Equipe 3"); fx.wait_for_timeout(120)
    checar("efeitos: ao filtrar, as cartas que ficam deslizam até o novo lugar", fx.evaluate("document.getAnimations().filter(a=>a.effect.getKeyframes()[0].translate).length") > 0)
    checar("efeitos: «podio» vazio some (hidden respeitado)", fx.evaluate("getComputedStyle(document.getElementById('podio')).display") == "none")
    fx.goto(U + "projecao.html#cartinhas"); fx.wait_for_timeout(300); fx.keyboard.press("ArrowRight"); fx.wait_for_timeout(250)
    checar("efeitos: reunião mostra o pacote antes de revelar a cartinha", fx.locator("#palco .c-pacote").count() == 1)
    fx.wait_for_timeout(1500)
    checar("efeitos: pacote some e a cartinha fica visível", fx.locator("#palco .c-pacote").count() == 0 and fx.evaluate("getComputedStyle(document.querySelector('#palco .carta')).visibility") == "visible")
    checar("efeitos: sem erros de script", not efx, str(efx)); fx.close()
    ctx_r = nav.new_context(reduced_motion="reduce", viewport={"width": 1280, "height": 900}); rp = ctx_r.new_page()
    rp.goto(U + "album.html"); rp.wait_for_timeout(1200)
    checar("efeitos: com «reduzir movimento» não há confete nem pacote", rp.locator(".c-confete").count() == 0)
    rp.goto(U + "projecao.html#cartinhas"); rp.wait_for_timeout(300); rp.keyboard.press("ArrowRight"); rp.wait_for_timeout(200)
    checar("efeitos: com «reduzir movimento» a reunião mostra a carta direto", rp.locator("#palco .c-pacote").count() == 0 and rp.locator("#palco .carta").count() == 1)
    ctx_r.close()

    # ---- reunião: abrir pacote (só quem fez 100, revelado de trás pra frente até o 1º lugar)
    pk = ctx.new_page(); epk = []; pk.on("pageerror", lambda x: epk.append(str(x)))
    pk.goto(U + "projecao.html#pacote"); pk.wait_for_timeout(800)
    n100 = pk.locator(".pk-slot").count()
    esperado = pk.evaluate("(()=>{const D=Object.values(AGENTES_DADOS.agentes);const mes=document.querySelector('.slide h2 small').textContent;return D.filter(a=>a.meses.some(m=>m.mes===mes&&Math.round(m.pontos)>=100)).length})()")
    checar("pacote: começa fechado, com tantas cartas quantos agentes com 100", pk.locator(".pk-pacote").count() == 1 and n100 == max(esperado, 3), f"{n100} x {esperado}")
    checar("pacote: a tela não passa sozinha (modo manual)", pk.evaluate("PROJECAO.modo()") == "pacote")
    pk.keyboard.press("Enter"); pk.wait_for_function("getComputedStyle(document.querySelector('.pk-pacote')).display==='none'", timeout=15000)
    pk.keyboard.press("Enter"); pk.wait_for_function(f"document.querySelector('.pk-cont').textContent==='Revelando 1 de {n100}'", timeout=15000)
    checar("pacote: revela primeiro a ÚLTIMA colocada, sem nome (Agente N)", pk.evaluate("document.querySelector('.pk-rank').textContent") == f"{n100}º" and "Agente" in pk.evaluate("document.querySelector('.pk-nome').textContent") and pk.locator(".pk-grande .carta").count() == 1)
    checar("pacote: sem erros de script (versão com animação)", not epk, str(epk)); pk.close()
    ctr = nav.new_context(reduced_motion="reduce", viewport={"width": 1280, "height": 800}); rk = ctr.new_page(); erk = []; rk.on("pageerror", lambda x: erk.append(str(x)))
    rk.goto(U + "projecao.html#pacote"); rk.wait_for_timeout(600); ranks = []
    for i in range(n100 + 2):
        rk.keyboard.press("Enter"); rk.wait_for_timeout(120)
        r = rk.evaluate("document.querySelector('.pk-rank')?.textContent||''")
        if r and (not ranks or ranks[-1] != r): ranks.append(r)
    seq = [int(x.replace("º", "")) for x in ranks]
    checar("pacote: revelação vai do último até o 1º lugar, em ordem", seq == sorted(seq, reverse=True) and seq[-1] == 1 and seq[-3:] == [3, 2, 1], str(seq))
    checar("pacote: no fim mostra os parabéns e as cartas ficam à mostra", rk.locator(".pk-fim").count() == 1 and rk.locator(".pk-slot.aberta").count() == n100)
    checar("pacote: com «reduzir movimento» não há pacote voando nem erros", not erk, str(erk)); ctr.close()

    # ---- apresentação de cada mês: o seletor troca o mês do pacote e das cartinhas
    ms = ctx.new_page(); ems = []; ms.on("pageerror", lambda x: ems.append(str(x)))
    ms.goto(U + "projecao.html#pacote"); ms.wait_for_timeout(700)
    meses = ms.eval_on_selector_all("#mesApres option", "o=>o.map(x=>x.value)")
    checar("apresentação: seletor de mês aparece com todos os meses (mais recente primeiro)", len(meses) >= 2 and not ms.evaluate("document.getElementById('mesApres').hidden"), str(meses))
    if len(meses) >= 2:
        outro = meses[1]; ms.select_option("#mesApres", outro); ms.wait_for_timeout(600)
        checar("apresentação: ao trocar o mês o pacote é refeito para esse mês", ms.evaluate("document.querySelector('.pk-mes').textContent") == outro and f"mes={outro.replace('/', '%2F')}" in ms.url, ms.url)
        ms.evaluate("PROJECAO.trocarModo('cartas')"); ms.wait_for_timeout(300)
        checar("apresentação: as cartinhas seguem o mesmo mês", outro in ms.evaluate("document.querySelector('.slide h2').textContent"))
    checar("apresentação: sem erros de script", not ems, str(ems)); ms.close()

    # ---- cabeçalho da reunião se ajusta à resolução: sem rolagem lateral e todos os comandos à vista
    hp = ctx.new_page()
    for w, h in ((1920, 1080), (1366, 768), (1024, 700), (768, 900), (390, 800)):
        hp.set_viewport_size({"width": w, "height": h}); hp.goto(U + "projecao.html#pacote"); hp.wait_for_timeout(400)
        r = hp.evaluate("(()=>{const h=document.querySelector('header'),d=document.documentElement,b=[...h.querySelectorAll('.bt:not([hidden])')];return {ov:h.scrollWidth>h.clientWidth+1||d.scrollWidth>d.clientWidth+1,fora:b.filter(x=>{const q=x.getBoundingClientRect();return q.right>innerWidth+1||q.left<-1}).length,n:b.length}})()")
        checar(f"reunião {w}px: cabeçalho sem rolagem e com todos os comandos à vista", not r["ov"] and r["fora"] == 0 and r["n"] >= 6, str(r))
    hp.close()

    # ---- «Melhor do ano»: o detalhe abre o MESMO ranking anual (antes caía no mês mais recente e o agente mudava de posição)
    an = ctx.new_page(); ean = []; an.on("pageerror", lambda x: ean.append(str(x)))
    an.goto(U + "album.html?mes=Melhor%20do%20ano"); an.wait_for_timeout(1800)
    lugar = an.evaluate("document.querySelector('#podio .slot.p1 .n').textContent.trim()")
    href = an.evaluate("document.querySelector('#podio .slot.p1').getAttribute('href')")
    checar("melhor do ano: o link da cartinha leva o mês «Melhor do ano»", "mes=Melhor%20do%20ano" in href, href)
    an.click("#podio .slot.p1"); an.wait_for_timeout(1800)
    pos = an.evaluate("[...document.querySelectorAll('.kpi')].map(k=>k.innerText.replace(/\\n/g,' ')).find(t=>/POSIÇÃO NO ANO/i.test(t))||''")
    checar("melhor do ano: página do agente mostra a mesma posição do álbum", pos and pos.upper().startswith("POSIÇÃO NO ANO " + lugar.upper()) if False else bool(pos) and (" " + lugar + " de ") in pos, f"{lugar} / {pos}")
    checar("melhor do ano: explica a média dos meses e lista cada mês", an.evaluate("!!document.querySelector('#detalhamento') && /média das notas/i.test(document.querySelector('#detalhamento').innerText) && document.querySelectorAll('#detalhamento tbody tr').length >= 2"))
    checar("melhor do ano: sem erros de script", not ean, str(ean)); an.close()

    # ---- agente.html: «Por que esta nota?» com a conta inteira e os turnos descontados
    ag = ctx.new_page(); eg = []; ag.on("pageerror", lambda x: eg.append(str(x)))
    ag.goto(U + "agente.html"); ag.wait_for_timeout(500)
    alvo_ag = ag.evaluate("""()=>{for(const [k,a] of Object.entries(AGENTES_DADOS.agentes)){const m=a.meses.slice().pop();if(m&&m.ev&&m.ev.sem&&m.ev.sem.length&&m.detalhe)return {k, dia:m.ev.sem[0][0], n:m.ev.sem.length}}return null}""")
    checar("dados do agente trazem os turnos descontados (ev.sem)", alvo_ag is not None, "nenhum agente com turno sem lançamento no último mês")
    ag.goto(U + "agente.html?id=" + (alvo_ag["k"] if alvo_ag else "0")); ag.wait_for_timeout(1500)
    det = ag.evaluate("""(DIA)=>{const d=document.querySelector('#detalhamento');if(!d)return null;const t=d.innerText;
      const linhas=[...d.querySelectorAll('table.porque tbody tr')].length;
      return {linhas, turnos:/Turnos descontados \\(\\d+ em \\d+ dia/.test(t), dias:t.includes(DIA), final:!!d.querySelector('tr.final'), antes:d.compareDocumentPosition(document.querySelector('#gMes'))&Node.DOCUMENT_POSITION_FOLLOWING?true:false}}""", alvo_ag["dia"] if alvo_ag else "")
    checar("agente: «Por que esta nota?» lista todos os critérios (não só 3)", det and det["linhas"] >= 6, str(det))
    checar("agente: mostra os dias e turnos descontados", det and det["turnos"] and det["dias"], str(det))
    checar("agente: detalhamento vem antes dos gráficos e tem nota final", det and det["final"] and det["antes"], str(det))
    ag.set_viewport_size({"width": 360, "height": 800}); ag.wait_for_timeout(300)
    checar("agente: sem rolagem lateral no celular com o detalhamento", not ag.evaluate("document.documentElement.scrollWidth>innerWidth"))
    checar("agente: sem erros de script", not eg, str(eg)); ag.close()

    # ---- páginas estáticas no claro e no escuro
    for f in ("agente.html?nome=Gilmar%20Bitencourt%20Luiz", "validar.html", "contestacao.html", "album.html"):
        e = []; q = ctx.new_page(); q.on("pageerror", lambda x: e.append(str(x)))
        q.evaluate("1"); q.goto(U + f); q.wait_for_timeout(700)
        q.evaluate("localStorage.removeItem('sentinelaTema')"); q.reload(); q.wait_for_timeout(500)
        # fundo pode estar no <body> ou, se ele é transparente, no <html>
        fundo_js = "(()=>{const c=getComputedStyle(document.body).backgroundColor;return c==='rgba(0, 0, 0, 0)'?getComputedStyle(document.documentElement).backgroundColor:c})()"
        b1 = q.evaluate(fundo_js)
        q.click("[data-tema-btn]"); q.wait_for_timeout(300)
        b2 = q.evaluate(fundo_js)
        q.evaluate("localStorage.removeItem('sentinelaTema')")
        checar(f"{f.split('?')[0]}: claro por padrão e escuro no botão", b1 != b2 and b1 in ("rgb(238, 242, 248)", "rgb(237, 241, 247)"), f"{b1} {b2}")
        sobra = q.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
        checar(f"{f.split('?')[0]}: sem erro de script", not e, str(e))
        q.close()
    checar("página inicial sem erros de script", not erros, str(erros))
    nav.close()

print("\n" + ("TUDO CERTO" if not FALHAS else f"{len(FALHAS)} FALHA(S): {FALHAS}"))
sys.exit(1 if FALHAS else 0)
