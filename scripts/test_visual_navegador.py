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
for f in ("agente.html", "contestacao.html", "validar.html", "projecao.html"):
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
    checar("fundo claro por padrão", bg == "rgb(237, 241, 247)", bg)
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

    # ---- páginas estáticas no claro e no escuro
    for f in ("agente.html?nome=Gilmar%20Bitencourt%20Luiz", "validar.html", "contestacao.html", "transparencia.html"):
        e = []; q = ctx.new_page(); q.on("pageerror", lambda x: e.append(str(x)))
        q.evaluate("1"); q.goto(U + f); q.wait_for_timeout(700)
        q.evaluate("localStorage.removeItem('sentinelaTema')"); q.reload(); q.wait_for_timeout(500)
        b1 = q.evaluate("getComputedStyle(document.body).backgroundColor")
        q.click("[data-tema-btn]"); q.wait_for_timeout(300)
        b2 = q.evaluate("getComputedStyle(document.body).backgroundColor")
        q.evaluate("localStorage.removeItem('sentinelaTema')")
        checar(f"{f.split('?')[0]}: claro por padrão e escuro no botão", b1 != b2 and b1 in ("rgb(238, 242, 248)", "rgb(237, 241, 247)"), f"{b1} {b2}")
        sobra = q.evaluate("document.documentElement.scrollWidth > innerWidth + 1")
        checar(f"{f.split('?')[0]}: sem erro de script", not e, str(e))
        q.close()
    checar("página inicial sem erros de script", not erros, str(erros))
    nav.close()

print("\n" + ("TUDO CERTO" if not FALHAS else f"{len(FALHAS)} FALHA(S): {FALHAS}"))
sys.exit(1 if FALHAS else 0)
