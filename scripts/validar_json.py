# -*- coding: utf-8 -*-
"""
Valida a sintaxe dos arquivos JSON que o sistema depende de encontrar
íntegros — em especial os que costumam ser editados na mão direto pelo
GitHub (deteccoes_pendentes.json, agentes_nomes.json,
cronograma_ausencias.json, config_home.json).

Um erro de digitação (vírgula sobrando/faltando) faz o código de leitura
desses arquivos cair no fallback silencioso — trata como se o arquivo
estivesse vazio, sem avisar claramente que uma correção manual ou um nome
de agente inteiro sumiu. Isso já aconteceu de verdade neste projeto.

Uso: python3 scripts/validar_json.py
Sai com código 1 (falha o workflow) se algum arquivo estiver quebrado.
Arquivo que não existe é ignorado (é opcional em muitos casos).
"""
import json
import sys

ARQUIVOS_CRITICOS = [
    "data/deteccoes_pendentes.json",
    "data/agentes_nomes.json",
    "data/cronograma_ausencias.json",
    "data/config_home.json",
    "data/outras_atividades.json",
    "data/ajustes_ranking.json",
]


def validar_ajustes(dados):
    """data/ajustes_ranking.json: lista de {"id_agente", "data" (dd/mm/aaaa),
    "pontos" (número), "motivo" (texto)} — erro de formato aqui faria o
    ajuste ser ignorado em silêncio, então barra antes da coleta."""
    from datetime import datetime
    if not isinstance(dados, list):
        return ["data/ajustes_ranking.json: o arquivo deve ser uma lista [ ... ]"]
    erros = []
    for i, it in enumerate(dados, 1):
        try:
            int(it["id_agente"]); float(it["pontos"])
            datetime.strptime(str(it["data"]), "%d/%m/%Y")
            if not str(it["motivo"]).strip():
                raise ValueError("motivo vazio")
        except (KeyError, TypeError, ValueError) as e:
            erros.append(f"data/ajustes_ranking.json: ajuste #{i} inválido ({e!r}) — use "
                         f'{{"id_agente": 116, "data": "15/10/2026", "pontos": 2.0, "motivo": "..."}}')
    return erros


def validar(arquivos=ARQUIVOS_CRITICOS):
    erros = []
    for caminho in arquivos:
        try:
            with open(caminho, encoding="utf-8") as f:
                dados = json.load(f)
            if caminho.endswith("ajustes_ranking.json"):
                erros.extend(validar_ajustes(dados))
        except FileNotFoundError:
            continue  # arquivo opcional, tudo bem não existir
        except json.JSONDecodeError as e:
            erros.append(f"{caminho}: {e}")
    return erros


if __name__ == "__main__":
    erros = validar()
    if erros:
        print("::error::Arquivo(s) JSON quebrado(s) — corrija antes de continuar:")
        for e in erros:
            print(f"::error::  {e}")
        sys.exit(1)
    print(f"✅ Todos os {len(ARQUIVOS_CRITICOS)} arquivos JSON críticos estão válidos (ou não existem, o que é ok).")
