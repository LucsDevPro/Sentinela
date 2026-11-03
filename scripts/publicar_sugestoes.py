"""Monta as SUGESTÕES de classificação dos dias sem trabalho e envia ao Worker.

Lê a aba "Ausências" das planilhas dos meses abertos (data/config_home.json +
mês seguinte, se existir) — já exclui fins de semana, feriados, paradas
coletivas, férias detectadas e tudo que o cronograma explica — e agrupa os dias
consecutivos de cada agente em períodos.

PRIVACIDADE (repositório público): esta lista NÃO é gravada no repositório. Ela
vai direto ao Worker (POST /publicar-sugestoes, protegido por token) e só a
coordenação, com PIN, consegue ler.

Variáveis de ambiente: SENTINELA_WORKER_URL e SENTINELA_PUBLISH_TOKEN. Sem elas,
o script só informa que pulou (não é erro).
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta

CONFIG_HOME = "data/config_home.json"
# Equipes sob demanda não têm dia esperado fixo: não geram sugestão de falta.
EQUIPES_SOB_DEMANDA = {"equipe bloqueio", "ponto estratégico"}


def _d(txt):
    return datetime.strptime(txt, "%d/%m/%Y").date()


def _planilhas_abertas():
    arquivos = []
    try:
        with open(CONFIG_HOME, encoding="utf-8") as f:
            home = json.load(f).get("arquivo")
        if home and os.path.exists(home):
            arquivos.append(home)
    except (OSError, json.JSONDecodeError):
        pass
    try:
        with open("data/historico/manifest.json", encoding="utf-8") as f:
            man = json.load(f)
        itens = man if isinstance(man, list) else man.get("meses", man.get("entradas", []))
        for e in itens:
            arq = e.get("arquivo")
            if arq and e.get("origem") == "cache" and e.get("tipo") != "semana":
                caminho = arq if arq.startswith("data/") else os.path.join("data/historico", arq)
                if os.path.exists(caminho) and caminho not in arquivos:
                    arquivos.append(caminho)
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return arquivos


def ler_ausencias(arquivos):
    """[(id_agente, nome, equipe, date, turno)] das abas 'Ausências'."""
    import openpyxl
    linhas = set()
    for caminho in arquivos:
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        if "Ausências" not in wb.sheetnames:
            continue
        for r in wb["Ausências"].iter_rows(min_row=3, values_only=True):
            if not r or r[0] is None or not r[3] or r[5] not in ("Manhã", "Tarde"):
                continue
            try:
                linhas.add((int(r[0]), str(r[1]), str(r[2]), _d(str(r[3])), r[5]))
            except (ValueError, TypeError):
                continue
        wb.close()
    return sorted(linhas, key=lambda t: (t[1], t[3], t[4]))


def _proximo_util(d):
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def montar_sugestoes(linhas):
    """Agrupa dias úteis consecutivos de cada agente em períodos sugeridos."""
    por_agente = {}
    for id_ag, nome, equipe, dia, turno in linhas:
        if equipe.strip().lower() in EQUIPES_SOB_DEMANDA:
            continue
        a = por_agente.setdefault(id_ag, {"nome": nome, "equipe": equipe, "dias": {}})
        a["dias"].setdefault(dia, set()).add(turno)
    itens = []
    for id_ag, a in por_agente.items():
        dias = sorted(a["dias"])
        grupo = []
        for dia in dias + [None]:
            if grupo and (dia is None or dia != _proximo_util(grupo[-1])):
                itens.append(_item(id_ag, a, grupo))
                grupo = []
            if dia is not None:
                grupo.append(dia)
    itens.sort(key=lambda i: (i["nome"], _d(i["inicio"])))
    return itens


def _item(id_ag, a, grupo):
    dias = [{"dia": d.strftime("%d/%m/%Y"),
             "turnos": [t for t in ("Manhã", "Tarde") if t in a["dias"][d]]} for d in grupo]
    n = len(grupo)
    inteiros = sum(1 for d in dias if len(d["turnos"]) == 2)
    if inteiros == 0 and n <= 2:
        t = dias[0]["turnos"][0]
        sug = f"Só o turno da {t.lower()}: provável meia folga ou meia ausência justificada"
    elif n <= 2:
        sug = "1 a 2 dias isolados: provável folga ou ausência justificada"
    elif n < 7:
        sug = "Vários dias seguidos: possível ausência justificada ou falta"
    else:
        sug = "7 ou mais dias úteis seguidos: provável férias (confira a aba Férias)"
    return {"id_agente": id_ag, "nome": a["nome"], "equipe": a["equipe"],
            "inicio": dias[0]["dia"], "fim": dias[-1]["dia"], "dias": dias, "sugestao": sug}


def montar_checklist():
    """Checklist do mês aberto mais antigo (só contagens, nada sensível). None se falhar."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import fechar_mes as fm, meses_arquivados as mesarq
        ce = fm._ce()
        fechados = {n for _, _, n in mesarq.carregar()}
        alvo = next((n for _, _, n in sorted(ce.MESES_OFICIAIS) if n not in fechados), None)
        return fm.checar(alvo) if alvo else None
    except Exception as e:
        print(f"ℹ️ Checklist de fechamento não gerado ({e}).")
        return None


def publicar(itens, url, token, checklist=None):
    dados = {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "itens": itens}
    if checklist and not checklist.get("erro"):
        dados["checklist"] = checklist
    corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + "/publicar-sugestoes", data=corpo, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


if __name__ == "__main__":
    url = os.environ.get("SENTINELA_WORKER_URL", "").strip()
    token = os.environ.get("SENTINELA_PUBLISH_TOKEN", "").strip()
    if not url or not token:
        print("ℹ️ Worker não configurado (SENTINELA_WORKER_URL/SENTINELA_PUBLISH_TOKEN) — sugestões não enviadas.")
        sys.exit(0)
    try:
        itens = montar_sugestoes(ler_ausencias(_planilhas_abertas()))
        status = publicar(itens, url, token, montar_checklist())
        print(f"✅ {len(itens)} sugestão(ões) enviada(s) ao Worker (HTTP {status}).")
    except Exception as e:  # nunca derruba o workflow por causa disso
        print(f"⚠️ Não consegui enviar as sugestões ({e}) — segue sem elas.")
    sys.exit(0)
