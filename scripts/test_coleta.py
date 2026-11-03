# -*- coding: utf-8 -*-
"""Testes da blindagem da coleta: timeouts, retry com backoff, e-Visita fora do
ar, semana com erro sem derrubar as outras, sessão caída, orçamento de tempo e
proteção do cache. Tudo com fakes — nenhuma requisição real."""
import os
import sys
import tempfile

os.environ.setdefault("EVISITA_CPF", "teste")
os.environ.setdefault("EVISITA_SENHA", "teste")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pandas as pd  # noqa: E402
import requests  # noqa: E402
import coletar_evisita as C  # noqa: E402

FALHAS = []


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


dormiu = []
_sleep_real = C.time.sleep
C.time.sleep = lambda s: dormiu.append(s)   # nenhum teste espera de verdade


class Resp:
    def __init__(self, texto="<html><body>ok</body></html>", status=200):
        self.text, self.status_code = texto, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    """Respostas roteirizadas: cada item é uma Resp ou uma exceção a levantar."""
    def __init__(self, roteiro):
        self.roteiro, self.chamadas = list(roteiro), []

    def get(self, url, timeout=None):
        self.chamadas.append(timeout)
        item = self.roteiro.pop(0) if self.roteiro else Resp()
        if isinstance(item, Exception):
            raise item
        return item


# --- Timeouts -----------------------------------------------------------------
check(isinstance(C.TIMEOUT_HTTP, tuple) and C.TIMEOUT_HTTP[0] < C.TIMEOUT_HTTP[1],
      "Timeout HTTP separado: conexão (curta) e leitura (longa)")

# --- Backoff exponencial com jitter ---------------------------------------------
esperas = [C._espera_backoff(t) for t in (1, 2, 3, 4, 5, 9)]
check(all(min(C.BACKOFF_MAX_S, C.BACKOFF_BASE_S * 2 ** (t - 1)) <= e <= min(C.BACKOFF_MAX_S, C.BACKOFF_BASE_S * 2 ** (t - 1)) + C.BACKOFF_JITTER_S
          for t, e in zip((1, 2, 3, 4, 5, 9), esperas)), "Backoff dobra a cada falha, com jitter de até 1s")
check(C._espera_backoff(20) <= C.BACKOFF_MAX_S + C.BACKOFF_JITTER_S, "Backoff tem teto")

# --- baixar_soup_com_retry: timeout, lentidão, queda ----------------------------
dormiu.clear()
s = FakeSession([requests.Timeout("lento"), requests.ConnectionError("caiu"), Resp()])
soup = C.baixar_soup_com_retry(s, "http://x", "teste", tentativas=3)
check(soup is not None and len(s.chamadas) == 3, "Dois timeouts/quedas e a 3ª tentativa funciona")
check(all(c == C.TIMEOUT_HTTP for c in s.chamadas), "Toda chamada usa o timeout (conexão, leitura)")
check(len(dormiu) == 2 and dormiu[1] > dormiu[0] - C.BACKOFF_JITTER_S, "Esperou entre as tentativas, com espera crescente")

s = FakeSession([requests.Timeout("a")] * 5)
try:
    C.baixar_soup_com_retry(s, "http://x", "teste", tentativas=3)
    check(False, "Esgotadas as tentativas deve levantar erro")
except requests.Timeout:
    check(len(s.chamadas) == 3, "Esgotadas as tentativas: levanta o erro (sem insistir para sempre)")

dormiu.clear()
s = FakeSession([Resp('<html><input name="cpf"></html>')])
try:
    C.baixar_soup_com_retry(s, "http://x", "teste", tentativas=3)
    check(False, "Tela de login deve levantar SessaoExpiradaError")
except C.SessaoExpiradaError:
    check(len(s.chamadas) == 1 and not dormiu, "Sessão expirada não é repetida em vão (levanta na hora)")

# --- e-Visita no ar? --------------------------------------------------------------
_get = requests.get
try:
    requests.get = lambda url, **kw: Resp(status=200)
    check(C.evisita_no_ar()[0] is True, "Saúde: página de login responde → no ar")
    requests.get = lambda url, **kw: Resp(status=503)
    ok, det = C.evisita_no_ar(tentativas=2)
    check(ok is False and "503" in det, "Saúde: HTTP 503 em todas as tentativas → fora do ar")
    n = {"i": 0}

    def get_instavel(url, **kw):
        n["i"] += 1
        if n["i"] < 3:
            raise requests.ConnectionError("fora")
        return Resp(status=302)
    requests.get = get_instavel
    check(C.evisita_no_ar(tentativas=3)[0] is True, "Saúde: volta no meio das tentativas → no ar")
    requests.get = lambda url, **kw: (_ for _ in ()).throw(requests.Timeout("lento"))
    check(C.evisita_no_ar(tentativas=2)[0] is False, "Saúde: timeout em todas as tentativas → fora do ar")
finally:
    requests.get = _get

# --- abrir_sessao: login com retry --------------------------------------------------
class FakeDriver:
    fechados = 0
    def quit(self):
        FakeDriver.fechados += 1
    def get_cookies(self):
        return []

_cd, _fl = C.criar_driver, C.fazer_login
tent = {"n": 0}
try:
    C.criar_driver = lambda: FakeDriver()
    def login_instavel(d):
        tent["n"] += 1
        if tent["n"] < 3:
            raise RuntimeError("login lento")
    C.fazer_login = login_instavel
    sess = C.abrir_sessao(tentativas=3)
    check(sess is not None and tent["n"] == 3 and FakeDriver.fechados == 3,
          "Login falha 2x e funciona na 3ª; o navegador é fechado em todas as tentativas")
    C.fazer_login = lambda d: (_ for _ in ()).throw(RuntimeError("sempre falha"))
    try:
        C.abrir_sessao(tentativas=2)
        check(False, "Login impossível deve levantar erro")
    except RuntimeError as e:
        check("2 tentativas" in str(e), "Login impossível: erro claro depois das tentativas")
finally:
    C.criar_driver, C.fazer_login = _cd, _fl


# --- coletar_semanas_blindado ---------------------------------------------------------
def r_ok(h, total=10):
    return {"html_id": h, "sessao_caiu": False, "agentes_ausentes": [], "agentes_incompletos": [], "total_agentes": total}


def r_tudo_falhou(h, total=10):
    return {"html_id": h, "sessao_caiu": False, "agentes_incompletos": [], "total_agentes": total,
            "agentes_ausentes": [(i, "Equipe", "falha") for i in range(total)]}


feitas = []
def coleta_com_erro(sessao, h, ano, ciclo):
    feitas.append(h)
    if h == 2:
        raise RuntimeError("estouro no meio da semana")
    return r_ok(h)

res = C.coletar_semanas_blindado([1, 2, 3], 2026, 164, abrir=lambda: "sessao", coletar=coleta_com_erro)
check(feitas == [1, 2, 3] and len(res) == 3, "Erro no meio da semana 2: semanas 1 e 3 continuam")
check(res[1].get("abortada") and "estouro" in res[1]["agentes_ausentes"][0][2], "Semana abortada vai para o resumo com o motivo")

# sessão cai: reabre e refaz uma vez
aberturas, chamadas = [], []
def abrir_contando():
    aberturas.append(1)
    return f"s{len(aberturas)}"
def coleta_sessao(sessao, h, ano, ciclo):
    chamadas.append(sessao)
    if len(chamadas) == 1:
        d = r_ok(h); d["sessao_caiu"] = True
        return d
    return r_ok(h)
res = C.coletar_semanas_blindado([5], 2026, 164, abrir=abrir_contando, coletar=coleta_sessao)
check(len(aberturas) == 2 and chamadas == ["s1", "s2"] and not res[0]["sessao_caiu"],
      "Sessão caída: abre sessão nova e refaz a semana uma vez")

# e-Visita caindo: para depois de N semanas seguidas falhando por inteiro
vistas = []
def coleta_morta(sessao, h, ano, ciclo):
    vistas.append(h)
    return r_tudo_falhou(h)
res = C.coletar_semanas_blindado([1, 2, 3, 4, 5], 2026, 164, abrir=lambda: "s", coletar=coleta_morta)
check(vistas == [1, 2] and len(res) == 5 and all(r.get("pulada") for r in res[2:]),
      f"{C.MAX_SEMANAS_FALHAS_SEGUIDAS} semanas seguidas falhando: para e deixa as outras para a próxima execução")
check(all("próxima execução" in r["agentes_ausentes"][0][2] for r in res[2:]), "Semanas puladas dizem que ficam para a próxima execução")

# uma semana ruim no meio zera a contagem (não é falha seguida)
def coleta_alternada(sessao, h, ano, ciclo):
    return r_tudo_falhou(h) if h in (1, 3) else r_ok(h)
res = C.coletar_semanas_blindado([1, 2, 3, 4], 2026, 164, abrir=lambda: "s", coletar=coleta_alternada)
check(not any(r.get("pulada") for r in res), "Falhas não consecutivas não interrompem a coleta")

# orçamento de tempo
relogio = {"t": 0.0}
def agora():
    return relogio["t"]
def coleta_lenta(sessao, h, ano, ciclo):
    relogio["t"] += (C.ORCAMENTO_COLETA_MIN * 60) / 2 + 60   # cada semana leva mais da metade do orçamento
    return r_ok(h)
res = C.coletar_semanas_blindado([1, 2, 3, 4], 2026, 164, abrir=lambda: "s", coletar=coleta_lenta, agora=agora)
check([bool(r.get("pulada")) for r in res] == [False, False, True, True] or [bool(r.get("pulada")) for r in res] == [False, False, False, True],
      "Orçamento de tempo estourado: não começa semana nova")

# falha ao abrir sessão: não derruba, vai pro resumo
def abrir_quebrado():
    raise RuntimeError("login impossível")
res = C.coletar_semanas_blindado([1, 2, 3], 2026, 164, abrir=abrir_quebrado, coletar=coleta_com_erro)
check(len(res) == 3 and all(r.get("abortada") or r.get("pulada") for r in res), "Login impossível: nenhuma exceção sobe, tudo vai para o resumo")

# --- Cache nunca piora ------------------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    pasta = os.path.join(tmp, "semanas")
    os.makedirs(pasta)
    _p, _caminho_orig = C.PASTA_SEMANAS, C._caminho_semana
    C.PASTA_SEMANAS = pasta
    C._caminho_semana = lambda h, suf="", pasta_semanas=pasta: os.path.join(pasta_semanas, f"{h}{suf}")
    try:
        def df(id_ag, n):
            return pd.DataFrame({"id_agente": [id_ag] * n, "nome_agente": [f"A{id_ag}"] * n, "equipe": ["E"] * n, "x": range(n)})
        anterior = pd.concat([df(1, 20), df(2, 12), df(3, 5)], ignore_index=True)
        C._salvar_df_semana(anterior, C._caminho_semana(330, ".xlsx"))
        # recoleta ruim: agente 1 sumiu (resposta vazia), agente 2 veio com 3 de 12, agente 3 completo (5)
        novo = pd.concat([df(2, 3), df(3, 5)], ignore_index=True)
        final, _ = C._mesclar_com_cache_anterior(330, novo, {}, ids_falha=[])
        cont = final["id_agente"].value_counts().to_dict()
        check(cont.get(1) == 20, "Agente que sumiu da recoleta mantém os dados antigos")
        check(cont.get(2) == 12, "Agente com menos da metade das visitas mantém os dados antigos")
        check(cont.get(3) == 5, "Agente normal é atualizado")
        # recoleta melhor: agente 2 com 14 (mais que antes) substitui
        novo2 = pd.concat([df(1, 20), df(2, 14), df(3, 5)], ignore_index=True)
        final2, _ = C._mesclar_com_cache_anterior(330, novo2, {}, ids_falha=[])
        check(final2["id_agente"].value_counts().to_dict().get(2) == 14, "Recoleta com mais dados substitui o antigo")
        # recoleta toda vazia não apaga o arquivo
        C.salvar_cache_semana(330, pd.DataFrame(), {}, None, ids_falha=[1, 2, 3])
        depois = C._carregar_df_semana(C._caminho_semana(330, ".xlsx"))
        check(len(depois) == len(anterior), "Recoleta totalmente vazia não apaga o cache da semana")
    finally:
        C.PASTA_SEMANAS, C._caminho_semana = _p, _caminho_orig

C.time.sleep = _sleep_real
print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes da coleta passaram.")
