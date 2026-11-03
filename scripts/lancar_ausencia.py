"""Processa issues do GitHub que lançam/ajustam/cancelam ausências.

Formulários (labels):
  atestado -> data/cronograma_ausencias.json   (reaproveita lancar_atestado.py)
  ferias   -> data/deteccoes_pendentes.json    (férias detectadas ou manuais)
      "Definir/ajustar férias": o período informado vira o período FINAL das
          férias do agente (ajustado à mão, a detecção automática não mexe mais).
          Se já havia férias detectadas tocando o período, elas são ajustadas;
          senão uma nova entrada manual é criada. Máximo 30 dias corridos.
      "Cancelar férias": os dias do período informado deixam de ser férias e
          passam a contar como FALTA (o que sobrar fora do período continua férias).

Uso (workflow): ISSUE_BODY="..." ISSUE_LABELS="ferias" python scripts/lancar_ausencia.py
Saída: mensagem pro comentário; código 0 = ok, 1 = dados inválidos (nada gravado).
"""
import json, os, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import lancar_atestado as la

CAMINHO_DETECCOES = "data/deteccoes_pendentes.json"
LIMITE_FERIAS_DIAS = 30
ACAO_DEFINIR = "definir"
ACAO_CANCELAR = "cancelar"


def _d(txt):
    return datetime.strptime(txt, "%d/%m/%Y").date()


def _f(d):
    return d.strftime("%d/%m/%Y")


def _dias_uteis(ini, fim):
    n, d = 0, ini
    while d <= fim:
        n += d.weekday() < 5
        d += timedelta(days=1)
    return n


def _entrada(base, id_agente, ini, fim, status, motivo, quem):
    return {
        "tipo": "possiveis_ferias", "id_agente": id_agente,
        "nome_agente": base["nome_agente"], "equipe": base["equipe"],
        "inicio": _f(ini), "fim": _f(fim), "duracao": _dias_uteis(ini, fim),
        "status": status, "motivo": motivo, "confirmado_automaticamente": False,
        "ajustado_manual": True, "categoria_coletiva": None,
        "detectado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "decidido_via": quem,
    }


def parse_ferias(corpo, nomes):
    c = la.parse_corpo(corpo)
    ag = next((v for k, v in c.items() if k.startswith("Agente")), "")
    acao_txt = next((v for k, v in c.items() if k.startswith("O que fazer")), "")
    ini = next((v for k, v in c.items() if k.startswith("Primeiro dia")), "")
    fim = next((v for k, v in c.items() if k.startswith("Último dia")), "")
    import re
    m = re.search(r"\(ID (\d+)\)\s*$", ag)
    if not m or m.group(1) not in nomes:
        return None, "Agente não reconhecido. Use o formulário e escolha o nome na lista."
    acao = ACAO_CANCELAR if acao_txt.lower().startswith("cancelar") else ACAO_DEFINIR
    di, df = la._data(ini), la._data(fim)
    if not di or not df:
        return None, "Datas inválidas. Use o formato dd/mm/aaaa (ex.: 27/10/2026)."
    di, df = di.date(), df.date()
    if df < di:
        return None, "O último dia não pode ser antes do primeiro dia."
    dias = (df - di).days + 1
    if acao == ACAO_DEFINIR and dias > LIMITE_FERIAS_DIAS:
        return None, (f"Férias têm no máximo {LIMITE_FERIAS_DIAS} dias corridos (você informou {dias}). "
                      "Lance até 30 dias; o que passar disso conta como falta.")
    if dias > 366:
        return None, "Período maior que 1 ano — confira as datas."
    return {"id_agente": int(m.group(1)), "acao": acao, "ini": di, "fim": df}, nomes[m.group(1)].get("nome", "")


def aplicar_ferias(lista, req, info_agente, quem="issue"):
    """Altera `lista` (deteccoes) in-place. Devolve a mensagem de resultado."""
    id_ag, ini, fim = req["id_agente"], req["ini"], req["fim"]
    nome, equipe = info_agente
    ferias = [e for e in lista if e.get("tipo") == "possiveis_ferias" and e.get("id_agente") == id_ag]
    base = {"nome_agente": nome, "equipe": equipe}

    if req["acao"] == ACAO_CANCELAR:
        tocadas = [e for e in ferias if e.get("status") == "confirmada"
                   and _d(e["inicio"]) <= fim and ini <= _d(e["fim"])]
        if not tocadas:
            return False, "ℹ️ Não encontrei férias confirmadas desse agente nesse período — nada foi alterado."
        for e in tocadas:
            e_ini, e_fim = _d(e["inicio"]), _d(e["fim"])
            lista.remove(e)
            if e_ini < ini:      # sobra à esquerda continua férias
                lista.append(_entrada(e, id_ag, e_ini, ini - timedelta(days=1), "confirmada", "Férias", quem))
            if e_fim > fim:      # sobra à direita continua férias
                lista.append(_entrada(e, id_ag, fim + timedelta(days=1), e_fim, "confirmada", "Férias", quem))
            c_ini, c_fim = max(e_ini, ini), min(e_fim, fim)
            lista.append(_entrada(e, id_ag, c_ini, c_fim, "falta", "Falta (férias canceladas pela coordenação)", quem))
        return True, (f"✅ Férias canceladas de **{nome}** em {_f(ini)} a {_f(fim)}: "
                      "esses dias passam a contar como falta.")

    # definir/ajustar: o período informado é o FINAL das férias
    tocadas = [e for e in ferias if e.get("status") == "confirmada"
               and _d(e["inicio"]) <= fim + timedelta(days=1) and ini <= _d(e["fim"]) + timedelta(days=1)]
    alvo_antigo = None
    if tocadas:
        alvo_antigo = max(tocadas, key=lambda e: (min(fim, _d(e["fim"])) - max(ini, _d(e["inicio"]))).days)
        base = alvo_antigo
        lista.remove(alvo_antigo)
    # Dias do período que estavam como FALTA (ex.: excesso de 30 dias) passam a ser férias:
    # a falta é cortada e só sobra o que ficou fora do período.
    for f in [e for e in ferias if e.get("status") == "falta"
              and _d(e["inicio"]) <= fim and ini <= _d(e["fim"])]:
        f_ini, f_fim = _d(f["inicio"]), _d(f["fim"])
        lista.remove(f)
        if f_ini < ini:
            lista.append(_entrada(f, id_ag, f_ini, ini - timedelta(days=1), "falta", f.get("motivo", "Falta"), quem))
        if f_fim > fim:
            lista.append(_entrada(f, id_ag, fim + timedelta(days=1), f_fim, "falta", f.get("motivo", "Falta"), quem))
    lista.append(_entrada(base, id_ag, ini, fim, "confirmada", "Férias", quem))
    verbo = "ajustadas" if alvo_antigo else "lançadas"
    return True, (f"✅ Férias {verbo}: **{nome}**, {_f(ini)} a {_f(fim)}. "
                  "Os dias fora desse período contam normalmente (falta, se não houve trabalho). "
                  "O dashboard está sendo atualizado.")


def processar(corpo, labels, caminho_cron=la.CAMINHO, caminho_nomes=la.NOMES, caminho_det=CAMINHO_DETECCOES):
    # O tipo vem do próprio formulário (só o de férias tem "O que fazer"); não
    # depende de label, que o GitHub só aplica se ela já existir no repositório.
    labels = [l.strip().lower() for l in (labels or "").split(",") if l.strip()]
    eh_ferias = "ferias" in labels or "### O que fazer" in (corpo or "")
    if not eh_ferias:
        return la.lancar(corpo, caminho_cron, caminho_nomes)
    with open(caminho_nomes, encoding="utf-8") as f:
        nomes = json.load(f)
    req, info = parse_ferias(corpo, nomes)
    if req is None:
        return False, f"❌ Não lancei: {info}"
    lista = []
    if os.path.exists(caminho_det):
        with open(caminho_det, encoding="utf-8") as f:
            lista = json.load(f)
    ag = nomes[str(req["id_agente"])]
    ok, msg = aplicar_ferias(lista, req, (ag.get("nome", ""), ag.get("equipe", "")))
    if ok:
        with open(caminho_det, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return ok, msg


if __name__ == "__main__":
    ok, msg = processar(os.environ.get("ISSUE_BODY", ""), os.environ.get("ISSUE_LABELS", ""))
    print(msg)
    sys.exit(0 if ok else 1)
