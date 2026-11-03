# -*- coding: utf-8 -*-
"""Sessão HTTP/Selenium no e-Visita: login, retry, download e extração das visitas.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import re
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .parametros import (
    BACKOFF_BASE_S,
    BACKOFF_JITTER_S,
    BACKOFF_MAX_S,
    CPF,
    DELAY_ENTRE_PAGINAS,
    ESPERA_ELEMENTO_S,
    ID_ATIVIDADE,
    ID_MUNICIPIO,
    ID_PENDENCIA_ABERTOS,
    ID_TIPO_VISITA,
    MAX_WORKERS,
    PAGE_LOAD_TIMEOUT_S,
    SENHA,
    TENTATIVAS_LOGIN,
    TENTATIVAS_POR_PAGINA,
    TENTATIVAS_SAUDE,
    TIMEOUT_CONEXAO,
    TIMEOUT_HTTP,
    URL_LOGIN,
    URL_VISITAS,
    _atualizar_cache_nomes_agentes,
    _cache_nomes_agentes,
)
from .auxiliares import _formatar_nome_proprio

log = logging.getLogger("evisita")


# ============================================================
# LOGIN E SESSÃO
# ============================================================

def _espera_backoff(tentativa):
    """Espera exponencial com jitter antes da próxima tentativa (tentativa = 1, 2, 3...
    é a que ACABOU de falhar): 1s, 2s, 4s... até BACKOFF_MAX_S, mais 0–1s aleatório."""
    base = min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2 ** (tentativa - 1)))
    return base + random.uniform(0, BACKOFF_JITTER_S)


def criar_driver():
    opts = Options()
    # Headless: o runner do GitHub Actions não tem tela. Localmente também
    # funciona normalmente em modo headless, então não precisa de flag extra.
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT_S)
    driver.set_script_timeout(PAGE_LOAD_TIMEOUT_S)
    return driver


def fazer_login(driver):
    log.info("🔐 Realizando login...")
    driver.get(URL_LOGIN)
    wait = WebDriverWait(driver, ESPERA_ELEMENTO_S)
    wait.until(EC.presence_of_element_located((By.NAME, "cpf"))).send_keys(CPF)
    wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(SENHA)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    if "login" in driver.current_url.lower():
        raise RuntimeError("Login falhou — verifique CPF/senha.")
    log.info("✅ Login OK")


def _aplicar_retry(session):
    retry = Retry(total=4, connect=3, read=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504],
                  respect_retry_after_header=True)
    adapter = HTTPAdapter(pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS, max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def criar_session(driver):
    s = requests.Session()
    for c in driver.get_cookies():
        s.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
    return _aplicar_retry(s)


def abrir_sessao(tentativas=TENTATIVAS_LOGIN):
    """Abre o navegador, faz login e devolve uma requests.Session pronta.
    Tenta de novo (com espera crescente) se o site estiver lento ou o login
    falhar — e SEMPRE fecha o navegador, mesmo com erro."""
    ultimo = None
    for t in range(1, tentativas + 1):
        driver = None
        try:
            driver = criar_driver()
            fazer_login(driver)
            return criar_session(driver)
        except Exception as e:
            ultimo = e
            log.warning("⚠️ Login/sessão: tentativa %s/%s falhou: %s", t, tentativas, e)
            if t < tentativas:
                time.sleep(_espera_backoff(t))
        finally:
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
    raise RuntimeError(f"Não foi possível abrir sessão no e-Visita após {tentativas} tentativas: {ultimo}")


def evisita_no_ar(tentativas=TENTATIVAS_SAUDE):
    """Verificação de saúde ANTES de coletar: a página de login responde?
    Devolve (True/False, detalhe). Qualquer resposta HTTP < 500 conta como "no ar"."""
    ultimo = "sem resposta"
    for t in range(1, tentativas + 1):
        try:
            r = requests.get(URL_LOGIN, timeout=(TIMEOUT_CONEXAO, 30), allow_redirects=True)
            if r.status_code < 500:
                return True, f"HTTP {r.status_code}"
            ultimo = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            ultimo = f"{type(e).__name__}: {e}"
        if t < tentativas:
            time.sleep(_espera_backoff(t))
    return False, ultimo


def clonar_session(base):
    s = requests.Session()
    for c in base.cookies:
        s.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    s.headers.update(dict(base.headers))
    return _aplicar_retry(s)


# ============================================================
# COLETA
# ============================================================

class SessaoExpiradaError(RuntimeError):
    """Levantada quando a página retornada é a tela de login (sessão caiu)."""


def montar_url(id_agente: int, pagina: int, cfg: dict, id_pendencia: int = None,
                id_atividade: int = None, tem_foto: str = None) -> str:
    params = {
        "municipio": ID_MUNICIPIO, "id_ano": cfg["id_ano"], "id_ciclo": cfg["id_ciclo"],
        "semana_inicio": cfg["semana_inicio"], "semana_fim": cfg["semana_fim"],
        "id_atividade": id_atividade if id_atividade is not None else ID_ATIVIDADE,
        "id_tipo_visita": ID_TIPO_VISITA,
        "id_pendencia": id_pendencia if id_pendencia is not None else ID_PENDENCIA_ABERTOS,
        "id_agente": id_agente,
        "acao": "filtrar", "page": pagina,
    }
    if tem_foto is not None:
        params["tem_foto"] = tem_foto
    return requests.Request("GET", URL_VISITAS, params=params).prepare().url


def obter_total_paginas(soup):
    pag = soup.find("ul", class_="pagination")
    if not pag:
        return 1
    nums = []
    for a in pag.find_all("a", class_="page-link"):
        href = a.get("href", "")
        if "page=" in href:
            try:
                nums.append(int(href.split("page=")[-1].split("&")[0]))
            except ValueError:
                log.debug("Não foi possível extrair número de página de href=%s", href)
    return max(nums, default=1)


def _extrair_nome_agente_da_pagina(soup, id_agente):
    """
    (Fallback) Extrai o nome do agente a partir do <select> de filtro presente
    na página de listagem de visitas. Só funciona se o HTML BRUTO (sem JS)
    já vier com a <option> do agente preenchida — o que pode não ser o caso
    se o site carregar essa opção via AJAX (ver extrair_nome_agente).
    """
    select = soup.find("select", id="id_agente") or soup.find("select", attrs={"name": "id_agente"})

    if select is None:
        log.debug("_extrair_nome_agente_da_pagina: <select id/name='id_agente'> não encontrado (agente %s)", id_agente)
        return None

    opt = select.find("option", attrs={"value": str(id_agente)})
    if opt is None:
        opt = next((o for o in select.find_all("option") if "selected" in o.attrs), None)

    if opt is None:
        return None

    nome = opt.get_text(strip=True)
    if not nome or nome.lower() == "selecione":
        return None
    return nome


def _obter_nome_agente_via_api(session, id_agente):
    """
    Busca o nome do agente diretamente no endpoint 'getedit' usado pelo
    JavaScript da página (select2) para popular o campo com o valor
    pré-selecionado — ex.: .../sis_usuario/getedit/672.

    Esse endpoint é chamado via AJAX pelo navegador, então o nome do agente
    normalmente NÃO aparece no HTML bruto que o requests.get() baixa (só
    depois que o JS roda no navegador). Por isso buscamos direto na fonte.

    ATENÇÃO: o formato exato da resposta desse endpoint (JSON vs HTML) não
    pôde ser confirmado sem acesso direto ao sistema — a função tenta os
    formatos mais comuns. Se não funcionar na prática, ative logging DEBUG
    e envie a resposta bruta para ajuste fino.
    """
    url = f"{URL_LOGIN}/sis_usuario/getedit/{id_agente}"
    try:
        resp = session.get(url, timeout=TIMEOUT_HTTP)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.debug("getedit falhou para sis_usuario/%s: %s", id_agente, e)
        return None

    texto_bruto = resp.text.strip()

    # 1) Tenta JSON (formato mais comum para endpoints "getedit" desse tipo de sistema)
    try:
        data = resp.json()
    except ValueError:
        data = None

    if isinstance(data, dict):
        candidato = data.get("data") if isinstance(data.get("data"), dict) else data
        for chave in ("nome", "nome_usuario", "usuario", "descricao", "label", "text"):
            valor = candidato.get(chave) if isinstance(candidato, dict) else None
            if valor:
                return str(valor).strip()
        log.debug("getedit sis_usuario/%s respondeu JSON mas sem campo de nome reconhecido: %s",
                   id_agente, list(data.keys()))

    # 2) Tenta como HTML/texto simples (resposta curta = provavelmente só o nome,
    #    ou um <input value="..."> preenchido para o formulário de edição)
    if texto_bruto and "<html" not in texto_bruto.lower():
        soup_resp = BeautifulSoup(texto_bruto, "html.parser")
        input_nome = soup_resp.find("input", attrs={"name": re.compile("nome", re.I)})
        if input_nome and input_nome.get("value"):
            return input_nome["value"].strip()

        texto_limpo = soup_resp.get_text(strip=True)
        if texto_limpo and len(texto_limpo) < 100:
            return texto_limpo

    log.debug("getedit sis_usuario/%s: não foi possível extrair nome da resposta (%d caracteres)",
               id_agente, len(texto_bruto))
    return None


def extrair_nome_agente(session, soup, id_agente):
    """
    Tenta obter o nome do agente, nessa ordem:
      1) Endpoint getedit (fonte real usada pelo JS do site — mais confiável)
      2) Parsing do <select> da página de listagem (fallback, caso o site mude)
      3) Cache persistente (data/agentes_nomes.json) — nome já resolvido de
         verdade numa coleta anterior. É o que evita o "Agente_3035" quando
         o agente simplesmente não teve nenhum lançamento NESSA semana — a
         página de "sem resultados" do e-Visita costuma não trazer nem o
         <select> nem responder certo no getedit, mas o nome dele já é
         conhecido de outra semana, não precisa desistir.
      4) Nome genérico 'Agente_{id}' (última opção, sinaliza problema no log)
    Sempre que um nome de verdade é obtido (passo 1 ou 2), grava no cache
    na hora — assim ele já fica disponível pro passo 3 de qualquer outro
    agente/semana dentro da MESMA rodada, e de qualquer rodada futura.
    """
    nome = _obter_nome_agente_via_api(session, id_agente)
    if nome:
        nome = _formatar_nome_proprio(nome)
        _atualizar_cache_nomes_agentes(id_agente, nome)
        return nome

    nome = _extrair_nome_agente_da_pagina(soup, id_agente)
    if nome:
        nome = _formatar_nome_proprio(nome)
        _atualizar_cache_nomes_agentes(id_agente, nome)
        return nome

    nome_cache = _cache_nomes_agentes().get(str(id_agente), {}).get("nome")
    if nome_cache:
        log.info("ℹ️ Agente %s sem lançamento/nome resolvível nessa semana — "
                  "usando nome já conhecido do cache: %s", id_agente, nome_cache)
        return nome_cache

    log.warning("Não foi possível obter o nome do agente %s (nem via API, nem via página, nem via cache) — "
                 "usando nome genérico. Ative logging DEBUG para investigar.", id_agente)
    return f"Agente_{id_agente}"


def extrair_visitas(soup):
    tabela = soup.find("table", class_="table")
    if not tabela or not tabela.find("tbody"):
        return []
    visitas = []
    for tr in tabela.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 9:
            continue
        link = tr.select_one("a[href*='/detalhes']")
        id_visita = None
        if link:
            m = re.search(r"/sis_visita/(\d+)/detalhes", link.get("href", "") or "")
            if m:
                id_visita = int(m.group(1))
        visitas.append({
            "id_visita": id_visita,
            "regiao": tds[0].get_text(strip=True),
            "area": tds[1].get_text(strip=True),
            "quarteirao": tds[2].get_text(strip=True),
            "logradouro": tds[3].get_text(strip=True),
            "imovel": tds[4].get_text(strip=True),
            "atividade": tds[5].get_text(strip=True),
            "tipo_visita": tds[6].get_text(strip=True),
            "data_chegada": tds[7].get_text(strip=True),
            "data_saida": tds[8].get_text(strip=True),
        })
    return visitas


def _parece_tela_login(soup):
    return soup.find("input", {"name": "cpf"}) is not None


def baixar_soup(session, url):
    resp = session.get(url, timeout=TIMEOUT_HTTP)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    if _parece_tela_login(soup):
        raise SessaoExpiradaError(f"Sessão expirada ao acessar: {url}")
    return soup


def baixar_soup_com_retry(session, url, descricao="", tentativas=TENTATIVAS_POR_PAGINA):
    """
    Camada de retry em nível de APLICAÇÃO sobre baixar_soup — além do retry
    HTTP automático (urllib3, para 429/500/502/503/504), tenta de novo aqui
    para cobrir timeouts, erros de conexão e outras falhas que o retry HTTP
    não pega. Propaga SessaoExpiradaError imediatamente (não adianta insistir
    sem sessão válida).
    """
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return baixar_soup(session, url)
        except SessaoExpiradaError:
            raise
        except Exception as e:
            ultimo_erro = e
            if tentativa < tentativas:
                espera = _espera_backoff(tentativa)  # exponencial com jitter: ~1s, 2s, 4s...
                log.warning("Tentativa %s/%s falhou (%s): %s — tentando de novo em %.1fs",
                             tentativa, tentativas, descricao, e, espera)
                time.sleep(espera)
    raise ultimo_erro


def coletar_visitas_agente(session, id_agente, cfg, id_pendencia=None, obter_nome=True,
                            id_atividade=None, tem_foto=None):
    id_pendencia = id_pendencia if id_pendencia is not None else ID_PENDENCIA_ABERTOS
    log.info("  → Agente %s (pendência=%s)", id_agente, id_pendencia)
    soup_p1 = baixar_soup_com_retry(
        session, montar_url(id_agente, 1, cfg, id_pendencia, id_atividade, tem_foto),
        descricao=f"agente {id_agente} pend={id_pendencia} pág 1")
    total_pags = obter_total_paginas(soup_p1)
    todas = extrair_visitas(soup_p1)
    paginas_falhas = []

    for pag in range(2, total_pags + 1):
        try:
            soup = baixar_soup_com_retry(
                session, montar_url(id_agente, pag, cfg, id_pendencia, id_atividade, tem_foto),
                descricao=f"agente {id_agente} pend={id_pendencia} pág {pag}")
            novas = extrair_visitas(soup)
            todas.extend(novas)
            log.info("    pág %s/%s → %s visitas", pag, total_pags, len(novas))
            time.sleep(DELAY_ENTRE_PAGINAS)
        except SessaoExpiradaError:
            raise  # propaga: não adianta continuar coletando sem sessão válida
        except Exception as e:
            log.error("❌ Página %s do agente %s (pend=%s) falhou mesmo após %s tentativas: %s — "
                        "DADOS DESSA PÁGINA FICARÃO FALTANDO", pag, id_agente, id_pendencia, TENTATIVAS_POR_PAGINA, e)
            paginas_falhas.append(pag)

    nome = extrair_nome_agente(session, soup_p1, id_agente) if obter_nome else None
    por_id = {v["id_visita"]: v for v in todas if v["id_visita"]}
    finais = list(por_id.values()) + [v for v in todas if not v["id_visita"]]

    if paginas_falhas:
        log.error("⚠️ Agente %s (pend=%s): coleta INCOMPLETA — %s de %s páginas falharam (%s)",
                    id_agente, id_pendencia, len(paginas_falhas), total_pags, paginas_falhas)
    log.info("    ✅ Agente %s (pend=%s): %s visitas", id_agente, id_pendencia, len(finais))
    return nome, finais, paginas_falhas
