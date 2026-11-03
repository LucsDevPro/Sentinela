# -*- coding: utf-8 -*-
"""Lista de meses ARQUIVADOS (congelados). Fica em data/meses_arquivados.json
pra que "Fechar mês" (página validar.html) possa arquivar um mês sem mexer em código.
Sem o arquivo (ou ilegível), vale a lista embutida abaixo."""
import json, os

CAMINHO = "data/meses_arquivados.json"
EMBUTIDOS = [
    (305, 308, "Maio/2026"), (309, 312, "Junho/2026"), (313, 317, "Julho/2026"),
    (318, 321, "Agosto/2026"), (322, 326, "Setembro/2026"),
]


def carregar(caminho=CAMINHO):
    """[(semana_ini, semana_fim, "Mês/Ano"), ...] ordenado."""
    if not os.path.exists(caminho):
        return list(EMBUTIDOS)
    try:
        with open(caminho, encoding="utf-8") as f:
            itens = json.load(f)
        lista = [(int(i["inicio"]), int(i["fim"]), str(i["mes"])) for i in itens]
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError):
        return list(EMBUTIDOS)
    return sorted(lista)


def gravar(lista, caminho=CAMINHO):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump([{"inicio": a, "fim": b, "mes": m} for a, b, m in sorted(lista)], f, ensure_ascii=False, indent=2)
        f.write("\n")
