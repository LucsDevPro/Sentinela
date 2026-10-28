"""Lê o corpo de uma issue criada pelo formulário "Lançar atestado" e
acrescenta o registro em data/cronograma_ausencias.json.

Uso (no workflow): ISSUE_BODY="..." python scripts/lancar_atestado.py
Saída: imprime a mensagem pro comentário; código 0 = lançado ou já existia,
1 = dados inválidos (nada é gravado).
"""
import json, os, re, sys
from datetime import datetime

CAMINHO = "data/cronograma_ausencias.json"
NOMES = "data/agentes_nomes.json"

def _data(txt):
    try:
        return datetime.strptime(txt.strip(), "%d/%m/%Y")
    except ValueError:
        return None

def parse_corpo(corpo):
    """{'### Título': 'valor'} do formato que o GitHub gera para issue forms."""
    campos, atual = {}, None
    for linha in (corpo or "").replace("\r", "").split("\n"):
        if linha.startswith("### "):
            atual = linha[4:].strip()
            campos[atual] = ""
        elif atual is not None:
            campos[atual] += linha + "\n"
    return {k: v.strip() for k, v in campos.items()}

def montar_registro(corpo, nomes):
    c = parse_corpo(corpo)
    ag = next((v for k, v in c.items() if k.startswith("Agente")), "")
    ini = next((v for k, v in c.items() if k.startswith("Primeiro dia")), "")
    fim = next((v for k, v in c.items() if k.startswith("Último dia")), "")
    m = re.search(r"\(ID (\d+)\)\s*$", ag)
    if not m or m.group(1) not in nomes:
        return None, "Agente não reconhecido. Use o formulário e escolha o nome na lista."
    di, df = _data(ini), _data(fim)
    if not di or not df:
        return None, "Datas inválidas. Use o formato dd/mm/aaaa (ex.: 27/10/2026)."
    if df < di:
        return None, "O último dia não pode ser antes do primeiro dia."
    if (df - di).days > 60:
        return None, "Período maior que 60 dias — confira as datas."
    reg = {"alvo": "agente", "id_agente": int(m.group(1)), "motivo": "Atestado",
           "inicio": di.strftime("%d/%m/%Y"), "fim": df.strftime("%d/%m/%Y")}
    return reg, nomes[m.group(1)].get("nome", "")

def lancar(corpo, caminho=CAMINHO, caminho_nomes=NOMES):
    with open(caminho_nomes, encoding="utf-8") as f:
        nomes = json.load(f)
    reg, info = montar_registro(corpo, nomes)
    if reg is None:
        return False, f"❌ Não lancei: {info}"
    lista = []
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            lista = json.load(f)
    if reg in lista:
        return True, f"ℹ️ Esse atestado de **{info}** ({reg['inicio']} a {reg['fim']}) já estava lançado."
    lista.append(reg)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return True, (f"✅ Atestado lançado: **{info}**, {reg['inicio']} a {reg['fim']}. "
                  "Os dias saem de \"Turno sem lançamento\" e dos dias esperados, sem desconto de pontos. "
                  "O dashboard está sendo atualizado.")

if __name__ == "__main__":
    ok, msg = lancar(os.environ.get("ISSUE_BODY", ""))
    print(msg)
    sys.exit(0 if ok else 1)
