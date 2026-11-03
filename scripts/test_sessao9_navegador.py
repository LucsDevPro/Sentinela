# -*- coding: utf-8 -*-
"""Testes de NAVEGADOR da Sessão 9 (precisa de playwright + chromium; roda só na máquina de
desenvolvimento, não no workflow): página do agente, lote de impressão, contestação, comparação semanal.
Uso: python3 scripts/test_sessao9_navegador.py"""
import json, os, re, shutil, subprocess, sys, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS = []
def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond: FALHAS.append(nome)

trab = tempfile.mkdtemp()
for sub in ("data", "scripts", "assets"):
    shutil.copytree(os.path.join(RAIZ, sub), os.path.join(trab, sub), ignore=shutil.ignore_patterns("__pycache__", "csv"))
for f in ("agente.html", "contestacao.html", "transparencia.html"):
    shutil.copy(os.path.join(RAIZ, f), trab)
os.makedirs(os.path.join(trab, "historico")); os.makedirs(os.path.join(trab, "partes"))
json.dump({"url": "https://w.example"}, open(os.path.join(trab, "data/config_worker.json"), "w"))
man = json.load(open(os.path.join(trab, "data/historico/manifest.json")))
for e in man:
    if e.get("tipo") == "semana" and e.get("numero_semana") == 4:
        e["parcial"] = True
json.dump(man, open(os.path.join(trab, "data/historico/manifest.json"), "w"), ensure_ascii=False)
env = dict(os.environ, EVISITA_CPF="0", EVISITA_SENHA="t")
for f in ("semanas_327-330", "semana_329"):
    subprocess.run([sys.executable, "scripts/generate_dashboard.py", f"data/historico/{f}.xlsx", f"historico/{f}.html"], cwd=trab, env=env, check=True, capture_output=True)
# mês arquivado (Setembro): sem contestação
subprocess.run([sys.executable, "scripts/generate_dashboard.py", "data/historico/semanas_322-326.xlsx", "historico/semanas_322-326.html"], cwd=trab, env=env, check=True, capture_output=True)
subprocess.run([sys.executable, "scripts/gerar_agentes.py"], cwd=trab, env=env, check=True, capture_output=True)

mes_html = open(os.path.join(trab, "historico/semanas_327-330.html"), encoding="utf-8").read()
checar("gráfico semanal por equipe aparece na página do mês", "chartTeamSemanal" in mes_html)
checar("semana parcial marcada nos dados do gráfico", '"parcial":true' in mes_html.replace(" ", ""))
checar("página de uma semana não tem o gráfico comparativo", "chartTeamSemanal" not in open(os.path.join(trab, "historico/semana_329.html"), encoding="utf-8").read())

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    nav = p.chromium.launch()
    # ---- página do agente
    pg = nav.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    url = lambda f, q="": "file://" + os.path.join(trab, f) + q
    ag = json.loads(open(os.path.join(trab, "assets/agentes_dados.js"), encoding="utf-8").read()[len("window.AGENTES_DADOS="):-1])["agentes"]
    k, a = next((k, v) for k, v in ag.items() if k.isdigit() and len(v["meses"]) >= 3 and v["semanas"])
    pg.goto(url("agente.html", f"?id={k}")); pg.wait_for_selector("#gMes")
    checar("agente por ?id= mostra nome e gráficos", a["nome"] in pg.inner_text("h1") and pg.locator("canvas").count() == 3, str(pg.locator("canvas").count()))
    pg.goto(url("agente.html", "?nome=" + a["nome"].upper())); pg.wait_for_selector("#gMes")
    checar("agente por ?nome= (sem diferença de maiúsculas)", a["nome"] in pg.inner_text("h1"))
    checar("mostra perdas e ganhos do mês", "O que mais tirou pontos" in pg.inner_text("main"))
    pg.check("#apres")
    checar("modo apresentação borra o nome", pg.evaluate("getComputedStyle(document.querySelector('.nome')).filter").startswith("blur"))
    pg.goto(url("agente.html", "?nome=Fulano Inexistente"))
    checar("agente inexistente: aviso e busca", "Não encontrei" in pg.inner_text("main") and pg.locator("#b").count() == 1)
    pg.goto(url("agente.html"))
    checar("sem parâmetro: lista para escolher", pg.locator("#lista a").count() > 10)
    # sem dados
    vazio = os.path.join(trab, "agente_vazio.html")
    open(vazio, "w", encoding="utf-8").write(open(os.path.join(trab, "agente.html"), encoding="utf-8").read().replace("assets/agentes_dados.js", "assets/nao_existe.js"))
    pg.goto("file://" + vazio + "?id=1")
    checar("sem dados: mensagem amigável, sem erro de script", "Ainda não há dados" in pg.inner_text("main") and not erros, str(erros))
    # agente sem mês
    sem_mes = os.path.join(trab, "assets/agentes_poucos.js")
    open(sem_mes, "w", encoding="utf-8").write('window.AGENTES_DADOS={"gerado_em":"x","agentes":{"9":{"nome":"Novo Agente","equipe":"Equipe 1","meses":[],"semanas":[]}}};')
    pg.goto("file://" + vazio.replace("agente_vazio", "agente_novo") if False else url("agente.html"))
    nov = os.path.join(trab, "agente_novo.html")
    open(nov, "w", encoding="utf-8").write(open(os.path.join(trab, "agente.html"), encoding="utf-8").read().replace("assets/agentes_dados.js", "assets/agentes_poucos.js"))
    pg.goto("file://" + nov + "?id=9")
    checar("agente sem mês registrado: aviso, sem quebrar", "ainda não tem mês" in pg.inner_text("main"))

    # ---- lote de impressão
    pg = nav.new_page(viewport={"width": 1200, "height": 900}); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(url("historico/semanas_327-330.html"))
    pg.evaluate("window.print = () => { window.__imprimiu = true; }")
    pg.evaluate("imprimirExtratosLote('Equipe 1')"); pg.wait_for_function("window.__imprimiu === true")
    n_eq = pg.locator("#extratosLote .ex-folha").count()
    esperado = pg.evaluate("Object.values(EXTRATOS.agentes).filter(a => a.equipe === 'Equipe 1').length")
    checar("lote da equipe: uma folha por agente da equipe", n_eq == esperado and n_eq > 3, f"{n_eq} x {esperado}")
    checar("lote não traz botão de contestar", pg.locator("#extratosLote .ex-contestar").count() == 0)
    pg.emulate_media(media="print")
    pdf = pg.pdf(prefer_css_page_size=True)
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    checar("PDF do lote: uma página por agente, sem página em branco", paginas == n_eq, f"{paginas} páginas x {n_eq} folhas")
    pg.emulate_media(media="screen")
    pg.evaluate("window.dispatchEvent(new Event('afterprint'))")
    checar("depois de imprimir, o lote é limpo da página", pg.locator("#extratosLote").count() == 0 and "print-lote" not in (pg.evaluate("document.body.className")))
    pg.evaluate("imprimirExtratosLote('')"); pg.wait_for_timeout(300)
    total = pg.evaluate("Object.keys(EXTRATOS.agentes).length")
    checar("lote de todos: uma folha por agente do mês", pg.locator("#extratosLote .ex-folha").count() == total)
    pg.evaluate("window.dispatchEvent(new Event('afterprint'))")
    checar("ranking tem link para a página do agente", pg.locator("#tableRanking a[href*='agente.html?nome=']").count() > 10)

    # ---- contestação
    pedidos = []
    def rota(route, request):
        if request.method == "POST":
            pedidos.append(json.loads(request.post_data))
            ok = len(pedidos) <= 1
            route.fulfill(status=200 if ok else 429, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps({"ok": True, "codigo": "ABCD2345"} if ok else {"erro": "Muitos pedidos seus em pouco tempo."}))
        else:
            route.fulfill(status=204, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "POST"})
    pg.route("https://w.example/**", rota)
    nome = pg.evaluate("Object.keys(EXTRATOS.agentes)[0]")
    pg.evaluate(f"abrirExtrato({json.dumps(nome)})"); pg.wait_for_selector("#ctTexto", state="attached")
    pg.locator(".ex-contestar summary").click()
    pg.fill("#ctTexto", "Estava em reunião na manhã do dia 14."); pg.evaluate("enviarContestacao(" + str(pg.evaluate(f"EXTRATOS.agentes[{json.dumps(nome)}].id_agente")) + ")")
    pg.wait_for_function("document.getElementById('ctMsg').textContent.includes('ABCD2345')")
    checar("contestação válida mostra o código", "ABCD2345" in pg.inner_text("#ctMsg"))
    checar("corpo enviado tem critério, texto, mês e id", pedidos and pedidos[0]["mes"] == "Outubro/2026" and pedidos[0]["id_agente"] and pedidos[0]["texto"].startswith("Estava"), str(pedidos[:1]))
    checar("honeypot vai vazio para gente de verdade", pedidos[0]["hp"] == "")
    pg.evaluate("enviarContestacao(" + str(pedidos[0]["id_agente"]) + ")"); pg.wait_for_function("document.getElementById('ctMsg').textContent.includes('❌')")
    checar("limite do servidor aparece como mensagem amigável", "Muitos pedidos" in pg.inner_text("#ctMsg"))
    pg.evaluate("fecharExtrato()")
    # Setembro (mês fechado): sem formulário
    pg2 = nav.new_page(); pg2.goto(url("historico/semanas_322-326.html"))
    nome2 = pg2.evaluate("carregarExtratos().then(() => Object.keys(EXTRATOS.agentes)[0])")
    pg2.evaluate(f"abrirExtrato({json.dumps(nome2)})"); pg2.wait_for_timeout(300)
    checar("mês fechado: sem formulário de contestação", pg2.locator(".ex-contestar").count() == 0)
    # página de consulta
    pg3 = nav.new_page()
    def rota2(route, request):
        if "contestacao?codigo=" in request.url:
            route.fulfill(status=200, content_type="application/json", headers={"Access-Control-Allow-Origin": "*"},
                          body=json.dumps({"codigo": "ABCD2345", "status": "aceita", "criterio": "Turno sem lançamento", "mes": "Outubro/2026", "resposta": "Procede, ajustado.", "respondida_em": "2026-10-31"}))
        else:
            route.continue_()
    pg3.route("https://w.example/**", rota2)
    import functools, http.server, threading
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=trab))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    pg3.goto(base + "contestacao.html?codigo=ABCD2345"); pg3.wait_for_function("document.getElementById('res').textContent.includes('Procede')")
    checar("agente consulta a resposta pelo código", "Pedido aceito" in pg3.inner_text("#res"))
    pg3.goto(base + "contestacao.html"); pg3.fill("#cod", "abc"); pg3.click("#ver")
    checar("código inválido é recusado antes de consultar", "8 letras" in pg3.inner_text("#res"))
    srv.shutdown()
    nav.close()

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} falha(s): {FALHAS}"); sys.exit(1)
print("✅ Todos os testes de navegador da Sessão 9 passaram.")
