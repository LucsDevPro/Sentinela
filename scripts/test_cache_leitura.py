# -*- coding: utf-8 -*-
"""Testes do cache em memória da leitura das semanas (coleta/cache_semanas.py: _ler_aba_visitas)."""
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import coletar_evisita as C
import coleta.cache_semanas as CS

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


# conta quantas leituras reais (pd.read_excel) acontecem
leituras = []
_orig = pd.read_excel


def _contador(*a, **k):
    leituras.append(a[0])
    return _orig(*a, **k)


pd.read_excel = _contador


def df_base(valores):
    return pd.DataFrame({"agente": ["A", "B", "C"], "duracao_min": valores, "dia": ["2026-10-05"] * 3})


with tempfile.TemporaryDirectory() as tmp:
    a = os.path.join(tmp, "327.xlsx")
    CS._CACHE_LEITURA.clear()
    CS._salvar_df_semana(df_base([5, 12, 30]), a)

    # --- 1. a 2ª leitura da mesma semana não relê o arquivo
    leituras.clear()
    d1 = C._carregar_df_semana(a)
    d2 = C._carregar_df_semana(a)
    checar("1ª leitura lê o arquivo; a 2ª vem do cache", len(leituras) == 1, str(len(leituras)))
    checar("o conteúdo é o mesmo", d1.equals(d2) and list(d1["agente"]) == ["A", "B", "C"])

    # --- 2. devolve CÓPIA: alterar o resultado não contamina as próximas leituras
    d1["agente"] = "ALTERADO"
    d1.loc[0, "duracao_min"] = 999
    d3 = C._carregar_df_semana(a)
    checar("alterar o DataFrame devolvido não contamina o cache", list(d3["agente"]) == ["A", "B", "C"] and d3.loc[0, "duracao_min"] == 5, str(d3.to_dict("list")))

    # --- 3. a conversão com a constante do momento continua valendo (cache guarda o dado CRU)
    teto_orig = CS.TETO_DURACAO_MEDIA_MIN
    try:
        CS.TETO_DURACAO_MEDIA_MIN = 10
        acima10 = list(C._carregar_df_semana(a)["acima_teto_media"])
        CS.TETO_DURACAO_MEDIA_MIN = 20
        acima20 = list(C._carregar_df_semana(a)["acima_teto_media"])
    finally:
        CS.TETO_DURACAO_MEDIA_MIN = teto_orig
    checar("mudar TETO_DURACAO_MEDIA_MIN muda 'acima_teto_media' sem reler o arquivo",
           acima10 == [False, True, True] and acima20 == [False, False, True] and len(leituras) == 1, f"{acima10} {acima20} leituras={len(leituras)}")

    # --- 4. se o arquivo muda, relê (data de modificação/tamanho na chave)
    time.sleep(0.01)
    df_base([1, 2, 3, ][:3]).assign(extra=[7, 8, 9]).to_excel(a, sheet_name="visitas", index=False)   # grava por fora, sem passar por _salvar_df_semana
    d4 = C._carregar_df_semana(a)
    checar("arquivo alterado por fora é relido", "extra" in d4.columns and len(leituras) == 2, str(list(d4.columns)))

    # --- 5. _salvar_df_semana invalida
    CS._salvar_df_semana(df_base([40, 41, 42]), a)
    d5 = C._carregar_df_semana(a)
    checar("regravar com _salvar_df_semana invalida o cache", list(d5["duracao_min"]) == [40, 41, 42] and "extra" not in d5.columns, str(d5.to_dict("list")))

    # --- 6. arquivo inexistente: vazio e sem leitura
    n = len(leituras)
    checar("arquivo inexistente devolve DataFrame vazio sem ler", C._carregar_df_semana(os.path.join(tmp, "nao_existe.xlsx")).empty and len(leituras) == n)

    # --- 7. limite de tamanho
    max_orig = CS._CACHE_LEITURA_MAX
    try:
        CS._CACHE_LEITURA_MAX = 2
        CS._CACHE_LEITURA.clear()
        for i in range(4):
            p = os.path.join(tmp, f"s{i}.xlsx")
            CS._salvar_df_semana(df_base([i, i, i]), p)
            C._carregar_df_semana(p)
        checar("o cache respeita o tamanho máximo", len(CS._CACHE_LEITURA) <= 2, str(len(CS._CACHE_LEITURA)))
        n = len(leituras)
        C._carregar_df_semana(os.path.join(tmp, "s3.xlsx"))
        checar("a semana mais recente continua em cache", len(leituras) == n)
    finally:
        CS._CACHE_LEITURA_MAX = max_orig

    # --- 8. desligar por variável de ambiente
    CS._CACHE_LEITURA.clear()
    os.environ["SENTINELA_SEM_CACHE_LEITURA"] = "1"
    try:
        n = len(leituras)
        C._carregar_df_semana(a)
        C._carregar_df_semana(a)
        checar("SENTINELA_SEM_CACHE_LEITURA=1 lê o arquivo toda vez", len(leituras) - n == 2 and not CS._CACHE_LEITURA)
    finally:
        del os.environ["SENTINELA_SEM_CACHE_LEITURA"]

    # --- 9. várias threads lendo as mesmas semanas (a coleta faz isso) não quebram nada
    CS._CACHE_LEITURA.clear()
    arqs = []
    for i in range(6):
        p = os.path.join(tmp, f"t{i}.xlsx")
        CS._salvar_df_semana(df_base([i, i + 1, i + 2]), p)
        arqs.append(p)
    try:
        with ThreadPoolExecutor(max_workers=8) as ex:
            res = list(ex.map(lambda p: list(C._carregar_df_semana(p)["duracao_min"]), arqs * 8))
        ok = all(r == [i % 6, i % 6 + 1, i % 6 + 2] for i, r in enumerate(res))
        checar("leituras concorrentes devolvem os dados certos, sem erro", ok)
    except Exception as e:  # noqa: BLE001
        checar("leituras concorrentes devolvem os dados certos, sem erro", False, repr(e))

pd.read_excel = _orig
print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes do cache de leitura passaram.")
