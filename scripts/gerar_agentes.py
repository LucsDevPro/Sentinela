# -*- coding: utf-8 -*-
"""Gera assets/agentes_dados.js, que alimenta a página agente.html (evolução do agente).

Só dados PÚBLICOS que já aparecem no ranking/extrato: nota por mês e por semana, dias
trabalhados x esperados e os principais critérios que tiraram/deram pontos. Nada de saúde
(o motivo de ausência é só "Ausência justificada"). Equipe Bloqueio fica de fora, como no resto.
"""
import json, os, re, sys, unicodedata
from datetime import datetime, date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import meses_arquivados as mesarq  # noqa: E402

EQUIPE_BLOQUEIO = "Equipe Bloqueio"
LABEL_MES_RE = re.compile(r"^[^\W\d_]+/\d{4}$")


def _chave(nome):
    t = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def ler_planilha(caminho):
    """({agente: {equipe, pos, trab, esp, turnos_sem, pontos, cls}}, {agente: [(criterio, pontos)]})"""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        if "Ranking" not in wb.sheetnames:
            return {}, {}
        rank, det, modo = {}, {}, None
        for vals in wb["Ranking"].iter_rows(values_only=True):
            if not vals or vals[0] is None:
                if modo == "rank":
                    modo = None
                continue
            if vals[0] == "Posição":
                modo = "rank"; continue
            if vals[0] == "Agente" and len(vals) > 2 and vals[2] == "Critério":
                modo = "det"; continue
            if modo == "rank":
                try:
                    rank[str(vals[1]).strip()] = {"equipe": vals[2], "pos": int(vals[0]), "trab": vals[3], "esp": vals[4],
                                                  "turnos_sem": vals[5], "pontos": float(vals[6]), "cls": vals[7]}
                except (TypeError, ValueError):
                    continue
            elif modo == "det":
                try:
                    det.setdefault(str(vals[0]).strip(), []).append((str(vals[2]), float(vals[7])))
                except (TypeError, ValueError, IndexError):
                    continue
        return rank, det
    finally:
        wb.close()


_MESES_NUM = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
              "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def _d(txt):
    try:
        return datetime.strptime(str(txt).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _faixa_mes(label):
    """'Outubro/2026' -> (1/10/2026, 31/10/2026) ou None."""
    nome, _, ano = str(label).partition("/")
    n = _MESES_NUM.get(unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower())
    if not n or not ano.isdigit():
        return None
    ini = date(int(ano), n, 1)
    fim = (date(int(ano) + (n == 12), n % 12 + 1, 1)) - timedelta(days=1)
    return ini, fim


def _faixa_semana(mes, periodo):
    """('Outubro/2026', '04/10 a 10/10') -> (4/10/2026, 10/10/2026) ou None."""
    m = re.match(r"^\s*(\d{2})/(\d{2})\s*a\s*(\d{2})/(\d{2})\s*$", str(periodo or ""))
    fm = _faixa_mes(mes)
    if not m or not fm:
        return None
    ano = fm[0].year
    try:
        ini, fim = date(ano, int(m[2]), int(m[1])), date(ano, int(m[4]), int(m[3]))
    except ValueError:
        return None
    return ini, fim


def paradas_no_periodo(cron, equipe, faixa):
    """Paradas (já públicas no cronograma) que valem para a equipe e encostam no período: [{motivo, dias}]."""
    if not faixa:
        return []
    out = {}
    for c in cron:
        if c.get("alvo") == "equipe" and c.get("equipe") != equipe:
            continue
        if c.get("alvo") not in ("equipe", "todos"):
            continue
        a, b = _d(c.get("inicio")), _d(c.get("fim"))
        if not a or not b:
            continue
        ini, fim = max(a, faixa[0]), min(b, faixa[1])
        if ini <= fim:
            out[c.get("motivo", "Parada")] = out.get(c.get("motivo", "Parada"), 0) + (fim - ini).days + 1
    return [{"motivo": k, "dias": v} for k, v in out.items()]


def _num(x):
    try:
        return round(float(x), 1)
    except (TypeError, ValueError):
        return None


def gerar(raiz=ROOT):
    raiz = Path(raiz)
    man_p = raiz / "data" / "historico" / "manifest.json"
    try:
        man = json.loads(man_p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        man = []
    try:
        nomes = json.loads((raiz / "data" / "agentes_nomes.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        nomes = {}
    ids = {str(v.get("nome", "")).strip().lower(): k for k, v in nomes.items()}
    fechados = {n for _, _, n in mesarq.carregar(str(raiz / "data" / "meses_arquivados.json"))}
    meses_e = sorted((e for e in man if e.get("tipo") != "semana" and LABEL_MES_RE.match(str(e.get("label", "")))),
                     key=lambda e: e.get("semana_inicio", 0))
    sem_e = sorted((e for e in man if e.get("tipo") == "semana"), key=lambda e: (e.get("semana_inicio", 0)))
    agentes = {}
    try:
        cron = json.loads((raiz / "data" / "cronograma_ausencias.json").read_text(encoding="utf-8"))
        if not isinstance(cron, list):
            cron = []
    except (OSError, json.JSONDecodeError):
        cron = []

    def ficha(nome, equipe):
        k = ids.get(nome.strip().lower()) or _chave(nome)
        a = agentes.setdefault(k, {"nome": nome, "equipe": equipe, "meses": [], "semanas": []})
        a["equipe"] = equipe or a["equipe"]
        return a

    for e in meses_e:
        cam = raiz / "data" / "historico" / e["arquivo"]
        if not cam.exists():
            continue
        rank, det = ler_planilha(cam)
        for nome, r in rank.items():
            if r["equipe"] == EQUIPE_BLOQUEIO:
                continue
            itens = det.get(nome, [])
            perdas = sorted((x for x in itens if x[1] < 0), key=lambda x: x[1])[:3]
            ganhos = sorted((x for x in itens if x[1] > 0), key=lambda x: -x[1])[:3]
            ficha(nome, r["equipe"])["meses"].append({
                "mes": e["label"], "pontos": _num(r["pontos"]), "trab": _num(r["trab"]), "esp": _num(r["esp"]),
                "turnos_sem": _num(r["turnos_sem"]), "pos": r["pos"], "cls": r["cls"], "total": len(rank), "fechado": e["label"] in fechados,
                "perdas": [{"c": c, "p": round(p, 1)} for c, p in perdas],
                "ganhos": [{"c": c, "p": round(p, 1)} for c, p in ganhos],
                "paradas": paradas_no_periodo(cron, r["equipe"], _faixa_mes(e["label"]))})
    for e in sem_e:
        cam = raiz / "data" / "historico" / e["arquivo"]
        if not cam.exists():
            continue
        rank, _ = ler_planilha(cam)
        for nome, r in rank.items():
            if r["equipe"] == EQUIPE_BLOQUEIO:
                continue
            ficha(nome, r["equipe"])["semanas"].append({
                "mes": e.get("mes"), "n": e.get("numero_semana"), "periodo": e.get("periodo", ""), "parcial": bool(e.get("parcial")),
                "pontos": _num(r["pontos"]), "trab": _num(r["trab"]), "esp": _num(r["esp"]),
                "paradas": paradas_no_periodo(cron, r["equipe"], _faixa_semana(e.get("mes"), e.get("periodo")))})
    return {"gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"), "agentes": agentes}


def main():
    dados = gerar()
    destino = ROOT / "assets" / "agentes_dados.js"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("window.AGENTES_DADOS=" + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";", encoding="utf-8")
    print(f"✅ {destino.name}: {len(dados['agentes'])} agente(s).")


if __name__ == "__main__":
    main()
