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
]


def validar(arquivos=ARQUIVOS_CRITICOS):
    erros = []
    for caminho in arquivos:
        try:
            with open(caminho, encoding="utf-8") as f:
                json.load(f)
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
