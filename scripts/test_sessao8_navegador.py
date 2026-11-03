# -*- coding: utf-8 -*-
"""Testes de NAVEGADOR da Sessão 8 (validar.html com Worker simulado). Só na máquina de desenvolvimento."""
import functools, http.server, json, os, shutil, sys, tempfile, threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS = []
def checar(nome, cond, det=""):
    print(f"[{'OK  ' if cond else 'FALHOU'}] {nome}" + (f" — {det}" if not cond and det else ""))
    if not cond: FALHAS.append(nome)

trab = tempfile.mkdtemp()
shutil.copytree(os.path.join(RAIZ, "data"), os.path.join(trab, "data"), ignore=shutil.ignore_patterns("csv", "semanas", "historico"))
os.makedirs(os.path.join(trab, "assets"))
for f in ("validar.html", "manifest.webmanifest", "sw.js"):
    shutil.copy(os.path.join(RAIZ, f), trab)
for f in ("icone-192.png", "icone-512.png"):
    shutil.copy(os.path.join(RAIZ, "assets", f), os.path.join(trab, "assets"))
json.dump({"url": "https://w.example"}, open(os.path.join(trab, "data/config_worker.json"), "w"))
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=trab))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}/"

from playwright.sync_api import sync_playwright
estado = {"acoes": [], "checklist_pronto": False}
CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}
def rota(route, request):
    if request.method == "OPTIONS":
        return route.fulfill(status=204, headers=CORS)
    caminho = request.url.split("w.example")[1].split("?")[0]
    if request.method == "POST":
        estado["acoes"].append(json.loads(request.post_data))
        return route.fulfill(status=200, content_type="application/json", headers=CORS, body='{"ok":true,"id":"x"}')
    if caminho == "/log":
        corpo = {"quem": "Maria", "log": []}
    elif caminho == "/checklist":
        ok = estado["checklist_pronto"]
        corpo = {"quem": "Maria", "mes": "Outubro/2026", "periodo": "28/09/2026 a 30/10/2026", "pronto": ok, "itens": [
            {"id": "semanas", "ok": True, "texto": "Todas as 4 semanas do mês foram coletadas."},
            {"id": "dias", "ok": ok, "texto": "Nenhum dia sem trabalho esperando classificação." if ok else "3 dia(s) sem trabalho ainda esperam classificação."}]}
    elif caminho == "/contestacoes":
        corpo = {"quem": "Maria", "itens": [{"codigo": "ABCD2345", "id_agente": 1088, "criterio": "Turno sem lançamento", "texto": "Estava em reunião.", "mes": "Outubro/2026", "status": "aberta"}]}
    else:
        corpo = {"quem": "Maria", "itens": [], "gerado_em": "x"}
    route.fulfill(status=200, content_type="application/json", headers=CORS, body=json.dumps(corpo))

with sync_playwright() as p:
    nav = p.chromium.launch(); ctx = nav.new_context(viewport={"width": 390, "height": 800}); pg = ctx.new_page()
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script("sessionStorage.setItem('pinSentinela','1234')")
    pg.route("https://w.example/**", rota)
    dialogos = []
    pg.on("dialog", lambda d: (dialogos.append(d.message), d.accept()))
    pg.goto(base + "validar.html"); pg.wait_for_selector("#app:not([hidden])")
    checar("abre logado e sem erro de script", not erros, str(erros))
    checar("tem manifesto de aplicativo e ícones", pg.evaluate("document.querySelector('link[rel=manifest]').getAttribute('href')") == "manifest.webmanifest")
    checar("sem rolagem horizontal da página (celular)", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    # ajuste de pontos
    pg.click("[data-aba=ajuste]")
    aid = pg.evaluate("[...document.querySelectorAll('#ajAg option')].find(o => o.value).value")
    pg.select_option("#ajAg", aid); pg.fill("#ajPts", "2"); pg.fill("#ajMot", "Instabilidade do e-Visita")
    pg.click("#ajBtn"); pg.wait_for_timeout(300)
    a = estado["acoes"][-1]
    checar("ajuste: pede confirmação com resumo", dialogos and "Instabilidade" in dialogos[-1] and "+2" in dialogos[-1], str(dialogos[-1:]))
    checar("ajuste enviado com os campos certos", a["acao"] == "ajuste" and a["pontos"] == 2 and a["pin"] == "1234" and a["id_agente"] == int(aid), str(a))
    n = len(estado["acoes"]); pg.fill("#ajPts", "50"); pg.fill("#ajMot", "teste"); pg.click("#ajBtn"); pg.wait_for_timeout(200)
    checar("ajuste fora do limite nem sai da página", len(estado["acoes"]) == n)

    # equipe parada
    pg.click("[data-aba=parada]"); pg.select_option("#pdMot", "Chuva"); pg.select_option("#pdAlvo", "Equipe 2"); pg.select_option("#pdTurno", "Tarde")
    pg.click("#pdBtn"); pg.wait_for_timeout(300); a = estado["acoes"][-1]
    checar("parada por equipe e turno enviada", a["acao"] == "parada" and a["alvo"] == "equipe" and a["equipe"] == "Equipe 2" and a["turno"] == "Tarde" and a["motivo"] == "Chuva", str(a))
    pg.select_option("#pdAlvo", "todos"); pg.select_option("#pdTurno", ""); pg.click("#pdBtn"); pg.wait_for_timeout(300); a = estado["acoes"][-1]
    checar("parada de todas as equipes, dia inteiro", a["alvo"] == "todos" and "equipe" not in a and "turno" not in a, str(a))

    # fechar mês
    pg.click("[data-aba=fechar]"); pg.wait_for_selector("#checklist p b")
    checar("checklist incompleto: botão desligado", pg.is_disabled("#fcBtn") and "❌" in pg.inner_text("#checklist"))
    estado["checklist_pronto"] = True; pg.click("[data-aba=ajuste]"); pg.click("[data-aba=fechar]"); pg.wait_for_function("!document.getElementById('fcBtn').disabled")
    n = len(estado["acoes"]); pg.click("#fcBtn"); pg.wait_for_timeout(300)
    checar("checklist completo: fecha o mês", estado["acoes"][-1]["acao"] == "fechar_mes" and estado["acoes"][-1]["mes"] == "Outubro/2026" and len(estado["acoes"]) == n + 1)
    n = len(estado["acoes"]); pg.fill("#raConf", "errado"); pg.click("#raBtn"); pg.wait_for_timeout(200)
    checar("reabrir exige digitar o nome do mês", len(estado["acoes"]) == n)
    mes_arq = pg.evaluate("document.getElementById('raMes').value")
    pg.fill("#raConf", mes_arq); pg.click("#raBtn"); pg.wait_for_timeout(300)
    checar("reabrir com nome certo envia a confirmação", estado["acoes"][-1]["acao"] == "reabrir_mes" and estado["acoes"][-1]["confirmacao"] == mes_arq)

    # contestações
    pg.click("[data-aba=contest]"); pg.wait_for_selector("#listaContest .card")
    checar("contestação aparece para a coordenação", "Estava em reunião" in pg.inner_text("#listaContest"))
    pg.click("#listaContest >> text=Recusar"); pg.fill("#listaContest input[maxlength='240']", "Reunião não consta na agenda."); pg.click("text=Confirmar: recusar"); pg.wait_for_timeout(300)
    a = estado["acoes"][-1]
    checar("recusar envia resposta curta", a["acao"] == "contestacao_responder" and a["decisao"] == "recusar" and a["codigo"] == "ABCD2345", str(a))

    # ajuda
    pg.click("[data-aba=ajuda]")
    checar("tela de ajuda existe", "Como usar esta página" in pg.inner_text("#aba-ajuda"))
    # service worker não pode guardar o Worker
    sw = open(os.path.join(trab, "sw.js"), encoding="utf-8").read()
    checar("service worker ignora outras origens e não-GET", "u.origin !== location.origin" in sw and 'method !== "GET"' in sw)
    nav.close()
srv.shutdown()
print()
if FALHAS:
    print(f"❌ {len(FALHAS)} falha(s): {FALHAS}"); sys.exit(1)
print("✅ Todos os testes de navegador da Sessão 8 passaram.")
