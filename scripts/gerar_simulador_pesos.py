#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera assets/simulador_pesos.js: os dados que a página `pesos.html` usa para simular, SEM gravar nada, o que
aconteceria com a nota e a posição de cada agente em cada mês se os pesos da pontuação mudassem.

Para cada mês (MESES_OFICIAIS + arquivados) refaz o ranking a partir das semanas em cache — o mesmo caminho do
histórico (`consolidar_semanas`), numa pasta temporária — e guarda, por agente, a nota e a inclinação de cada peso
(ver `_inclinacoes_pesos`). Nada de data/ nem do manifest é alterado.

Uso: python3 scripts/gerar_simulador_pesos.py [destino.js] [--meses "Outubro/2026"]   (padrão: assets/simulador_pesos.js)
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("EVISITA_CPF", "0")
os.environ.setdefault("EVISITA_SENHA", "0")
import coletar_evisita as C  # noqa: E402
import coleta.ausencias_ranking as AR  # noqa: E402
import coleta.parametros as P  # noqa: E402
import coleta.pontos as PT  # noqa: E402

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DESTINO_PADRAO = os.path.join(RAIZ, "assets", "simulador_pesos.js")


def meses():
    """[(semana_inicio, semana_fim, rótulo)] em ordem cronológica: arquivados + oficiais."""
    todos = {(m[0], m[1], m[2]) for m in list(P.MESES_ARQUIVADOS) + list(P.MESES_OFICIAIS)}
    return sorted(todos)


ARQUIVOS_PROTEGIDOS = ["data/deteccoes_pendentes.json", "data/agentes_nomes.json"]   # o pipeline regrava (carimbo de data); aqui nada deve mudar


def calcular(filtro=None):
    guardados = {}
    for c in ARQUIVOS_PROTEGIDOS:
        caminho = os.path.join(RAIZ, c)
        if os.path.exists(caminho):
            guardados[caminho] = open(caminho, "rb").read()
    try:
        return _calcular(filtro)
    finally:
        for caminho, conteudo in guardados.items():
            if open(caminho, "rb").read() != conteudo:
                open(caminho, "wb").write(conteudo)


def _calcular(filtro=None):
    em_cache = set(C.semanas_ja_coletadas(P.PASTA_SEMANAS))
    lista = C.rodar_deteccao_completa(P.PASTA_SEMANAS)
    saida = []
    tmp = tempfile.mkdtemp(prefix="sim_pesos_")
    try:
        for ini, fim, label in meses():
            if filtro and label not in filtro:
                continue
            semanas = sorted(h for h in em_cache if ini <= h <= fim)
            if not semanas:
                continue
            AR.COLETOR_SIMULACAO = []
            try:
                C.consolidar_semanas(semanas, tmp, lista)
                agentes = list(AR.COLETOR_SIMULACAO)
            finally:
                AR.COLETOR_SIMULACAO = None
            saida.append({"label": label, "semanas": [semanas[0], semanas[-1]], "agentes": agentes})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return saida


def montar(meses_calculados):
    pesos = json.load(open(os.path.join(RAIZ, "data", "pesos_pontuacao.json"), encoding="utf-8"))["pesos"]
    atuais = {n: getattr(PT, n) for n in pesos}   # o que o cálculo usou de fato (JSON já aplicado)
    return {
        "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "pesos": {n: dict(v, valor=atuais[n]) for n, v in pesos.items()},
        "limite_max": PT.PESOS_LIMITE_MAX,
        "meses": meses_calculados,
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    filtro = None
    if "--meses" in argv:   # só para testes/depuração: --meses "Outubro/2026,Novembro/2026"
        i = argv.index("--meses")
        filtro = set(argv[i + 1].split(","))
        del argv[i:i + 2]
    destino = argv[0] if argv else DESTINO_PADRAO
    dados = montar(calcular(filtro))
    with open(destino, "w", encoding="utf-8") as f:
        f.write("window.SIMULADOR_PESOS = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"OK: {destino} ({os.path.getsize(destino) // 1024} KB, {len(dados['meses'])} meses)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
