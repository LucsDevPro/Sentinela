# -*- coding: utf-8 -*-
"""Parâmetros editáveis: credenciais, filtros, equipes, ciclos, regras, cronograma.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import re
import json
from datetime import datetime
import meses_arquivados as mesarq
import semanas_evisita as sem

log = logging.getLogger("evisita")


# ============================================================
# ⚙️  PARÂMETROS EDITÁVEIS — ALTERE AQUI CONFORME A NECESSIDADE
# ============================================================
# Este é o ÚNICO bloco que você normalmente precisa mexer para ajustar o
# comportamento do script. Está organizado por assunto; cada grupo tem uma
# explicação rápida do que o parâmetro faz.

# --- 1) CREDENCIAIS DE LOGIN -----------------------------------------------
# Pode ser sobrescrito por variável de ambiente (EVISITA_CPF / EVISITA_SENHA)
# ou editado direto aqui embaixo (valor após a vírgula é o padrão).
CPF   = os.environ.get("EVISITA_CPF")
SENHA = os.environ.get("EVISITA_SENHA")

if not CPF or not SENHA:
    raise SystemExit(
        "❌ Defina as variáveis de ambiente EVISITA_CPF e EVISITA_SENHA antes de rodar "
        "(no GitHub Actions isso vem dos Secrets do repositório; localmente, exporte-as "
        "no terminal antes de chamar o script)."
    )

# --- 2) FILTRO DE COLETA (o que buscar no e-Visita) ------------------------
ID_MUNICIPIO   = 62       # 62 = Ponta Porã
ID_ATIVIDADE   = 4        # 4 = Tratamento
ID_ANO         = 14       # código interno do ano epidemiológico (não é o ano civil)
ID_CICLO       = 163      # código interno do ciclo (ex.: "Rotina - 4")
ID_TIPO_VISITA = 0        # 0 = ambos (normal + recuperação) | 1 = só normal | 2 = só recuperação

# --- Cálculo automático de semana -------------------------------------------
# A conversão HTML ID <-> Semana do Ano mora inteira em scripts/semanas_evisita.py
# (é usada tanto aqui quanto no gerador do dashboard). Aqui só reaproveitamos.
ANCORA_DATA = sem.ANCORA_DATA
ANCORA_ID   = sem.ANCORA_HTML_ID
MESES_PT    = sem.MESES_PT

semana_atual        = sem.semana_atual_html    # ID de semana do site que contém hoje
_data_inicio_semana  = sem.data_inicio_semana_html
nome_periodo         = sem.nome_periodo         # rótulo amigável (nome do mês) pro seletor de período

# Primeira semana buscada na coleta inicial (quando data/semanas/ está vazio)
# — HTML 313 = Semana 27/2026 (28/06/2026), início de Julho. Maio e Junho/2026
# (semanas 305–312) SAÍRAM do programa em 05/11/2026: não são coletados, não
# têm página nem entram no Acumulado nem na média dos meses. É INDEPENDENTE
# de ANCORA_ID/ANCORA_DATA acima (que servem só pra converter data <-> HTML
# ID em qualquer ano, não pra decidir de onde a coleta começa).
PRIMEIRA_SEMANA_COLETA = 313

# Páginas SEMANAIS soltas (uma página por semana, a partir da semana 318 =
# 02/08/2026) foram ARQUIVADAS: o histórico agora só tem páginas MENSAIS
# (ver MESES_OFICIAIS). As planilhas semanais antigas ficam preservadas em
# data/historico/arquivo_semanal/ (fora do menu), e o cache bruto de cada
# semana continua intacto em data/semanas/. Se algum dia quiser voltar a
# gerar uma página por semana, troque a flag abaixo para True — semanas que
# não pertencem a nenhum mês de MESES_OFICIAIS passam a virar página própria
# (comportamento antigo, a partir de PRIMEIRA_SEMANA_DETALHE_SEMANAL).
GERAR_PAGINAS_SEMANAIS = False
PRIMEIRA_SEMANA_DETALHE_SEMANAL = 318
PASTA_ARQUIVO_SEMANAL = "arquivo_semanal"   # dentro de data/historico/

# Limites REAIS de cada mês, confirmados direto pelos parâmetros da URL do
# e-Visita (semana_inicio/semana_fim/id_ciclo) — NÃO batem exatamente com o
# calendário civil (ex.: a semana 313 começa domingo 28/06, mas já pertence
# ao ciclo de Julho no site, não Junho; Setembro foi de 322 a 326 e terminou
# em 03/10). Por isso o agrupamento do histórico usa esta tabela em vez de
# inferir pela data de início da semana.
#
# O nome do arquivo de cada mês usa SEMPRE o intervalo oficial daqui (ex.:
# semanas_327-330.xlsx), mesmo que o mês ainda esteja incompleto — assim o
# nome não muda a cada semana que chega e o link da home
# (data/config_home.json) nunca quebra. O mês cresce sozinho conforme as
# semanas seguintes são coletadas.
#
# PARA ADICIONAR UM MÊS NOVO: acrescente uma linha aqui, uma em
# CICLOS_TRATAMENTO e uma em CICLOS_PONTO_ESTRATEGICO (mais abaixo).
MESES_OFICIAIS = [
    # Julho a Setembro/2026 foram ARQUIVADOS (ver MESES_ARQUIVADOS logo abaixo)
    # — saíram daqui de propósito, não é esquecimento (Maio e Junho saíram do
    # programa). Ciclos deles:
    #   Julho 163 (padrão) / PE 154 · Agosto 163 / PE 155 · Setembro 164 / PE 156
    (327, 330, "Outubro/2026"),   # Tratamento 164 / PE 157 (arquivar quando fechar, na semana 330)
    (331, 334, "Novembro/2026"),  # Tratamento 165 / PE 158
]

# A partir desta semana o id_ciclo de Tratamento NÃO pode mais cair no
# padrão (ID_CICLO=163) por esquecimento: se a semana não estiver em
# CICLOS_TRATAMENTO, ela é PULADA com erro claro (em vez de coletar com o
# ciclo errado e gravar um cache vazio, que foi o que aconteceu com
# Outubro). Também é a primeira semana cujo ciclo coletado é registrado em
# data/semanas/_ciclos_coletados.json e conferido a cada execução.
PRIMEIRA_SEMANA_CICLO_EXPLICITO = 327

# Visões semanais (Semana 1 | 2 | … | Mês completo) só para o mês vigente:
# Outubro/2026 (semana 327) em diante. Meses anteriores NÃO ganham semanais.
PRIMEIRA_SEMANA_VISAO_SEMANAL = 327

# Meses que já foram gerados e "fechados" — não são mais regenerados
# automaticamente a cada rodada (ver atualizar_historico_do_cache(), que
# preserva no manifest.json qualquer entrada com "origem": "manual" sem
# tocar nela). O arquivo .xlsx continua no repositório normalmente, do
# jeito que foi gerado da última vez, e continua acessível pelo
# home_editor.html/historico como qualquer outro mês.
#
# Isso existe por dois motivos: (1) performance — não tem por que
# reprocessar um mês que já fechou há tempos toda vez que o workflow roda,
# só cresce o tempo de execução à toa conforme o histórico cresce; (2)
# estabilidade — um mês fechado não deveria mudar de número sozinho por
# causa de uma correção de código futura (ex.: a correção de nome de agente
# ou a de duplicata de férias que fizemos), senão os números "oficiais" de
# um mês passado ficam instáveis, o que é ruim pra confiança/auditoria.
#
# Pra REABRIR um mês arquivado (só se precisar corrigir algo grave nele de
# verdade): tire a entrada correspondente de data/historico/manifest.json
# (ou troque "origem" de "manual" pra "cache") e rode
# `consolidar_semanas([...semanas do mês...], "data/historico", ...)` na
# mão uma vez — depois arquive de novo trocando "origem" de volta pra
# "manual". Não é algo pra acontecer sozinho numa rodada automática.
# A lista vive em data/meses_arquivados.json ("Fechar mês" na página validar.html grava lá);
# sem o arquivo, vale a lista embutida em scripts/meses_arquivados.py.
MESES_ARQUIVADOS = mesarq.carregar()

# Consolidados EXTRAS, além dos meses de MESES_OFICIAIS (ex.: um trimestre
# ou um intervalo qualquer somando várias semanas). Formato:
# (semana_inicio, semana_fim, "Label"). Hoje vazio: Agosto e Setembro, que
# viviam aqui, passaram para MESES_OFICIAIS (mesmos nomes de arquivo, então
# nada muda para quem já tinha esses links).
MESES_ADICIONAIS = []


def _grupo_mes_oficial(html_id):
    """Nome do mês oficial (tabela acima) pra essa semana, ou None se a
    semana não estiver cadastrada ali (cai no fallback de
    atualizar_historico_do_cache — semana individual ou calendário)."""
    for ini, fim, nome in MESES_OFICIAIS:
        if ini <= html_id <= fim:
            return nome
    return None


def _faixa_mes_oficial(nome):
    """(semana_inicio, semana_fim) oficiais de um mês de MESES_OFICIAIS."""
    for ini, fim, n in MESES_OFICIAIS:
        if n == nome:
            return ini, fim
    return None

# --- Coleta semana a semana --------------------------------------------------
# A partir de agora a coleta NÃO busca mais um intervalo de semanas de uma vez
# só. Cada semana (HTML ID) é buscada e cacheada SEPARADAMENTE em
# data/semanas/<html_id>.csv (+ _pe.csv pro Ponto Estratégico), e depois TODAS
# as semanas já cacheadas são consolidadas num único Analise_Consolidada.xlsx.
# Isso deixa cada execução mais rápida (só busca o que realmente mudou) e
# permite reprocessar uma semana específica sem tocar nas outras.
PASTA_SEMANAS = "data/semanas"


def semanas_ja_coletadas(pasta_semanas=PASTA_SEMANAS):
    """HTML IDs de semanas que já têm cache salvo em disco, em ordem
    crescente. Uma semana só conta como coletada se tiver o .csv principal
    (o de Ponto Estratégico é opcional — nem toda semana tem PE cadastrado)."""
    if not os.path.isdir(pasta_semanas):
        return []
    ids = []
    for f in os.listdir(pasta_semanas):
        m = re.fullmatch(r"(\d+)\.xlsx", f)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def decidir_semanas_a_coletar(hoje=None, pasta_semanas=PASTA_SEMANAS):
    """Decide quais semanas (HTML IDs) buscar nesta execução:

      - Primeira execução (nada cacheado ainda): busca da semana
        PRIMEIRA_SEMANA_COLETA (Julho/2026) até a semana atual — uma
        planilha por semana.
      - Execuções seguintes: sempre RECOLETA a última semana já salva (os
        dados do e-Visita ainda podem mudar) e, se já existir uma semana
        nova disponível no site, busca ela(s) também — sem pular nenhuma,
        mesmo que o workflow tenha ficado parado por mais de uma semana.

    Retorna a lista de HTML IDs a coletar, em ordem crescente."""
    atual = semana_atual(hoje)
    ja = semanas_ja_coletadas(pasta_semanas)
    if not ja:
        log.info("📦 Primeira execução detectada (nenhuma semana em %s) — "
                  "coletando da semana %s (HTML %s) até a atual (HTML %s).",
                  pasta_semanas, sem.html_para_semana(PRIMEIRA_SEMANA_COLETA), PRIMEIRA_SEMANA_COLETA, atual)
        return list(range(PRIMEIRA_SEMANA_COLETA, atual + 1))
    ultima = max(ja)
    fim = max(atual, ultima)
    semanas = set(range(ultima, fim + 1))

    # Reprocessamento seguro: qualquer semana >= PRIMEIRA_SEMANA_CICLO_EXPLICITO
    # (e já disponível, ou seja <= semana atual) cujo cache não foi coletado
    # com o ciclo configurado hoje entra de novo — cobre semanas que ficaram
    # sem coleta por falta de configuração (ex.: Outubro, 327-330), inclusive
    # buracos no meio (semana 328 falhou mas a 329 passou). Depois de coletada
    # com sucesso o ciclo fica registrado e ela deixa de ser reprocessada.
    registrados = _ler_ciclos_coletados(pasta_semanas)
    for h in range(PRIMEIRA_SEMANA_CICLO_EXPLICITO, atual + 1):
        if ciclo_tratamento_configurado(h) is None:
            log.error("❌ Semana %s (%s) NÃO tem id_ciclo de Tratamento em CICLOS_TRATAMENTO — "
                       "não será coletada. Cadastre o ciclo (ver README, 'Novo mês').",
                       h, sem.rotulo_semana_html(h))
            semanas.discard(h)
            continue
        reg = registrados.get(str(h), {})
        esperado = _ciclos_esperados(h)
        if (reg.get("tratamento"), reg.get("pe")) != (esperado["tratamento"], esperado["pe"]):
            if h not in semanas:
                log.info("🔁 Semana %s será reprocessada (ciclo registrado %s ≠ configurado %s).",
                          h, (reg.get("tratamento"), reg.get("pe")), (esperado["tratamento"], esperado["pe"]))
            semanas.add(h)
    return sorted(semanas)

# Valores de pendência do e-Visita. O relatório principal (tempos de visita,
# alertas, etc.) é sempre baseado nos ABERTOS (ID_PENDENCIA_ABERTOS) — são os
# imóveis com visita registrada e horário real, usados em toda a análise de
# tempo/qualidade. Fechados e Recusados só entram na contagem/percentual de
# pendência (ver seção 14).
ID_PENDENCIA_ABERTOS   = 1   # imóveis com pendência em aberto (dataset principal da análise)
ID_PENDENCIA_FECHADOS  = 2   # imóveis com o ciclo fechado/concluído
ID_PENDENCIA_RECUSADOS = 3   # imóveis onde o morador recusou a visita

# --- 3) EQUIPES E AGENTES (IDs do e-Visita, agrupados por equipe) ----------
AGENTES_POR_EQUIPE = {
    "Equipe 1":        [116, 73, 1935, 470, 672, 3037, 79, 85, 30, 3101],
    "Equipe 2":        [115, 125, 3035, 3127, 2030, 134, 99, 142, 465, 81, 151, 2917],
    "Equipe 3":        [113, 2951, 120, 1938, 2721, 3128, 3038, 2918, 1936, 3177],
    "Equipe 4":        [80, 124, 161, 1943, 2789, 1996, 157, 110, 149, 86, 1942],
    "Equipe Bloqueio": [162, 1088, 1934, 109, 155, 126, 476, 122, 2101],
}

# --- 3b) PONTO ESTRATÉGICO (equipe/URL separada, com id_atividade e
# ciclo/semana próprios — ex.: id_atividade=3, tem_foto=, ciclo/semana
# geralmente diferentes do restante) --------------------------------------
# Preencha aqui os IDs dos agentes de Ponto Estratégico (mesmo formato de
# AGENTES_POR_EQUIPE, mas sem separação por equipe — se precisar separar por
# equipe no futuro, é só adaptar para um dict como o de cima).
AGENTES_PONTO_ESTRATEGICO = [
    1031,
]
ID_ATIVIDADE_PONTO_ESTRATEGICO = 3   # 3 = Ponto Estratégico (vs 4 = Tratamento no restante)

# A Atividade 3 (Ponto Estratégico) tem ciclos MENORES e independentes da
# Atividade 4 — cada ciclo novo no site tem seu próprio ID. Cadastre aqui
# cada ciclo conhecido como (semana_inicio, semana_fim, id_ciclo):
#   - ciclo 1: semanas 313-317 (28/06 a 01/08/2026) -> id_ciclo 154
#   - ciclo 2: semanas 318-321 (02/08 a 29/08/2026) -> id_ciclo 155
#   - ciclo 3: semanas 322-326 (30/08 a 03/10/2026, Setembro) -> id_ciclo 156
# Quando um novo ciclo começar no site (semana 327 em diante), adicione uma
# nova linha aqui com o id_ciclo daquele ciclo. Enquanto uma semana cair fora
# de todas as faixas cadastradas (ou o id_ciclo estiver None), a coleta do
# Ponto Estratégico é pulada com um aviso claro em vez de mandar um id_ciclo
# errado pro site.
#   - ciclo 4: semanas 327-330 (04/10 a 31/10/2026, Outubro)  -> id_ciclo 157
#   - ciclo 5: semanas 331-334 (Novembro/2026)                 -> id_ciclo 158
CICLOS_PONTO_ESTRATEGICO = [
    (313, 317, 154),
    (318, 321, 155),
    (322, 326, 156),
    (327, 330, 157),
    (331, 334, 158),
]

def ciclo_para_semana(semana, ciclos=CICLOS_PONTO_ESTRATEGICO):
    """Acha o id_ciclo pra uma semana específica, numa tabela de ciclos
    (serve tanto pra CICLOS_PONTO_ESTRATEGICO quanto CICLOS_TRATAMENTO).
    Retorna None se a semana cair fora de todos os ciclos cadastrados
    (ciclo futuro ainda não adicionado à lista) ou se o ciclo encontrado
    ainda não tiver id_ciclo preenchido."""
    for ini, fim, id_ciclo in ciclos:
        if ini <= semana <= fim:
            return id_ciclo
    return None

# O id_ciclo da Atividade 4 (Tratamento) também muda ao longo do tempo — não
# é fixo como o ID_CICLO abaixo fazia parecer. Confirmado com a URL real do
# site: a partir da semana 313 (Julho/2026) vale o ID_CICLO "padrão" (163,
# definido mais abaixo) e muda de novo a partir da semana 322 (Setembro/2026),
# que usa id_ciclo 164. (Maio–Junho, semanas 305–312, ciclo 162, saíram do
# programa e não são mais coletados.) Faixas SEM entrada aqui
# caem no id_ciclo padrão automaticamente — só precisa cadastrar aqui os
# ciclos ANTIGOS/diferentes do padrão atual.
#   - semanas 327-330 (Outubro/2026)  -> id_ciclo 164
#   - semanas 331-334 (Novembro/2026) -> id_ciclo 165
CICLOS_TRATAMENTO = [
    (322, 326, 164),
    (327, 330, 164),
    (331, 334, 165),
]

def ciclo_tratamento_configurado(html_id):
    """id_ciclo de Tratamento cadastrado EXPLICITAMENTE em CICLOS_TRATAMENTO
    pra essa semana, ou None se não houver faixa que a cubra."""
    for ini, fim, id_ciclo in CICLOS_TRATAMENTO:
        if ini <= html_id <= fim:
            return id_ciclo
    return None

def ciclo_tratamento_para_semana(html_id, id_ciclo_padrao):
    """Como ciclo_para_semana(), mas com fallback pro id_ciclo padrão em vez
    de None — toda semana tem uma coleta de Tratamento a fazer. ATENÇÃO: a
    partir de PRIMEIRA_SEMANA_CICLO_EXPLICITO o fallback não é mais usado
    pela coleta (ver coletar_uma_semana): semana sem ciclo cadastrado é
    pulada com erro claro, porque o padrão (163) devolve dados vazios."""
    cadastrado = ciclo_tratamento_configurado(html_id)
    return cadastrado if cadastrado is not None else id_ciclo_padrao


# --- Registro do ciclo realmente usado em cada semana ------------------------
# data/semanas/_ciclos_coletados.json guarda, pra cada semana coletada COM
# SUCESSO a partir de PRIMEIRA_SEMANA_CICLO_EXPLICITO, quais id_ciclo foram
# usados ({"327": {"tratamento": 164, "pe": 157, "coletado_em": "..."}}).
# Serve pra decidir_semanas_a_coletar() reprocessar sozinha qualquer semana
# cujo ciclo registrado não bate com o configurado (ou que nunca foi coletada
# direito), sem precisar de flag manual — e parar de reprocessar assim que
# estiver certa (idempotente).
NOME_ARQUIVO_CICLOS_COLETADOS = "_ciclos_coletados.json"

def _ciclos_esperados(html_id):
    return {"tratamento": ciclo_tratamento_configurado(html_id),
            "pe": ciclo_para_semana(html_id)}

def _ler_ciclos_coletados(pasta_semanas):
    caminho = os.path.join(pasta_semanas, NOME_ARQUIVO_CICLOS_COLETADOS)
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}

def _registrar_ciclos_coletados(html_id, pasta_semanas=None):
    pasta_semanas = pasta_semanas or PASTA_SEMANAS
    dados = _ler_ciclos_coletados(pasta_semanas)
    registro = _ciclos_esperados(html_id)
    registro["coletado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    dados[str(html_id)] = registro
    os.makedirs(pasta_semanas, exist_ok=True)
    with open(os.path.join(pasta_semanas, NOME_ARQUIVO_CICLOS_COLETADOS), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, sort_keys=True)

# (o antigo "semana_inicio_ciclo_pe" não é mais necessário: como agora cada
# semana é coletada individualmente, não existe mais a ideia de "buscar o
# ciclo inteiro desde o início numa tacada só" — cada semana busca só ela
# mesma, e o id_ciclo certo é resolvido por ciclo_para_semana() na hora.)

# --- 4) PERFORMANCE DA COLETA -----------------------------------------------
MAX_WORKERS          = 3     # quantos agentes coletar em paralelo ao mesmo tempo
DELAY_ENTRE_PAGINAS   = 0.30  # segundos de pausa entre páginas de um mesmo agente (evita sobrecarregar o servidor)
TIMEOUT_CONEXAO       = 15    # segundos pra ABRIR a conexão (se o servidor não responde, falha rápido e tenta de novo)
TIMEOUT_LEITURA       = 60    # segundos esperando a resposta depois de conectado (servidor lento)
TIMEOUT_HTTP          = (TIMEOUT_CONEXAO, TIMEOUT_LEITURA)   # (conexão, leitura) — usado em TODA chamada HTTP
BACKOFF_BASE_S        = 1.0   # espera antes da 2ª tentativa; dobra a cada falha (1s, 2s, 4s, 8s...)
BACKOFF_MAX_S         = 30.0  # teto da espera entre tentativas
BACKOFF_JITTER_S      = 1.0   # soma de 0 a 1s aleatórios (evita todas as threads baterem juntas no servidor)
PAGE_LOAD_TIMEOUT_S   = 60    # Selenium: tempo máximo pra carregar uma página
ESPERA_ELEMENTO_S     = 30    # Selenium: tempo máximo esperando um elemento da tela de login
TENTATIVAS_LOGIN      = 3     # tentativas de login (navegador + sessão) antes de desistir
TENTATIVAS_SAUDE      = 3     # tentativas da verificação "o e-Visita está no ar?" antes de coletar
MAX_SEMANAS_FALHAS_SEGUIDAS = 2   # se N semanas seguidas falharem por inteiro, para de coletar (e-Visita fora do ar)
ORCAMENTO_COLETA_MIN  = 170   # não começa semana nova depois disso (o job tem timeout maior); o que faltou fica pra próxima execução
TENTATIVAS_POR_PAGINA = 3     # tentativas extras (nível aplicação) se uma página falhar, antes de desistir dela

# --- 5) REGRAS DE ALERTA DE TEMPO DE VISITA ---------------------------------
TEMPO_MIN_VISITA_MIN = 3     # visita com duração menor que isso (min) = "rápida" (alerta)
TEMPO_MAX_VISITA_MIN = 30    # visita com duração maior que isso (min) = "longa" (alerta)
# Alguns agentes lançam pelo computador e conseguem manipular o horário de
# saída, inflando a duração da visita registrada. Pra isso não distorcer a
# média/mediana de tempo por visita, qualquer visita acima disso entra no
# cálculo de média/mediana como se tivesse durado exatamente esse teto (não
# afeta a contagem de "longas" acima, nem a listagem de alerta — só a média).
# Ex. real que motivou subir o teto de 15 -> 20min: um lançamento do agente
# Gabriel de 2.888 minutos numa única visita — o lançamento em si continua
# intacto na planilha/aba de auditoria (ver _preparar_acima_teto_media), só
# o valor USADO nos cálculos (média, mediana, horas úteis, gráficos etc.)
# entra capado em TETO_DURACAO_MEDIA_MIN.
TETO_DURACAO_MEDIA_MIN = 20
META_VISITAS_DIA     = 20    # meta de visitas por dia, usada na coluna "Dias c/ Meta"


def _carregar_metas_equipes(caminho="data/metas_equipes.json"):
    """Meta diária de visitas POR EQUIPE (opcional): {"Equipe 1": 25}. Equipe que não
    estiver no arquivo usa META_VISITAS_DIA. Valores inválidos (não numéricos, <1 ou >200)
    são ignorados com aviso. Vale para o ranking (Dias c/ Meta) e aparece na transparência."""
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            bruto = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    metas = {}
    for equipe, v in (bruto.items() if isinstance(bruto, dict) else []):
        try:
            v = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= v <= 200:
            metas[str(equipe)] = v
    return metas


METAS_EQUIPES = _carregar_metas_equipes()


def meta_da_equipe(equipe):
    return METAS_EQUIPES.get(str(equipe), META_VISITAS_DIA)

# --- 6) CLASSIFICAÇÃO DO AGENTE (🟢🟡🔴), baseada em % de visitas rápidas --
PCT_RAPIDAS_OK_ATE       = 10   # até 10% de visitas rápidas      -> 🟢 NORMAL
PCT_RAPIDAS_ATENCAO_ATE  = 20   # de 11% a 20% de visitas rápidas -> 🟡 ATENÇÃO
                                  # acima de 20%                    -> 🔴 CRÍTICO

# --- 7) SEQUÊNCIA SUSPEITA (lançamento em lote) -----------------------------
# Visitas consecutivas do mesmo agente com chegada muito próxima no tempo.
# IMPORTANTE: o e-Visita só registra minutos (sem segundos), então na prática
# esse limiar só pega visitas cravadas no MESMO MINUTO — mantido em segundos
# como critério de negócio explícito e para caso o sistema passe a fornecer
# segundos no futuro.
LIMIAR_SEQUENCIA_SUSPEITA_SEG = 50

# --- 8) HORÁRIO DE ALMOÇO (com tolerância) ----------------------------------
# Horário efetivamente monitorado como "visita durante o almoço". Já vem com
# 15 minutos de tolerância em cada borda em relação ao intervalo cheio
# (11h-13h), para não pegar visitas que só terminaram/começaram um pouco
# antes/depois do horário oficial.
HORA_ALMOCO_INICIO_MIN = 11 * 60 + 15   # 11h15 em minutos desde a meia-noite
HORA_ALMOCO_FIM_MIN    = 12 * 60 + 45   # 12h45 em minutos desde a meia-noite

# --- 9) HORÁRIO OFICIAL DE EXPEDIENTE (dias úteis) --------------------------
# Qualquer visita fora desses intervalos — inclusive sábado/domingo — entra
# na aba "Fora do Expediente".
HORA_EXPEDIENTE_MANHA_INICIO = 7
HORA_EXPEDIENTE_MANHA_FIM    = 11
HORA_EXPEDIENTE_TARDE_INICIO = 13
HORA_EXPEDIENTE_TARDE_FIM    = 17

# --- 10) CUSTO / SALÁRIO ----------------------------------------------------
SALARIO_MINIMO = 1621.00
SALARIO_AGENTE = 3 * SALARIO_MINIMO   # agente ganha 3 salários mínimos federais
DIAS_UTEIS_MES = 22                    # usado para estimar horas úteis mensais e custo da hora útil

# --- 11) SAÍDA (onde salvar o Excel) ----------------------------------------
PASTA_SAIDA         = "output"
ARQUIVO_CONSOLIDADO = "Analise_Consolidada.xlsx"

# --- 12) URLs DO SISTEMA (só mexer se o endereço do e-Visita mudar) --------
URL_LOGIN   = "https://evisita.saude.ms.gov.br/endemias"
URL_VISITAS = "https://evisita.saude.ms.gov.br/endemias/sis_visita"

# --- 13) CRONOGRAMA / AUSÊNCIAS PROGRAMADAS ---------------------------------
# Chuva, folga, atestado, reunião/treinamento e férias — tudo num só lugar,
# editável em data/cronograma_ausencias.json (use o editor visual
# cronograma_editor.html pra gerar o conteúdo, sem precisar mexer em código).
#
# Esses dias/períodos são EXCLUÍDOS do cálculo da aba "Ausências" (não
# contam como possível falta a investigar, nem entram na pontuação do
# agente) e aparecem listados na aba "Cronograma" — em cima dos dias que o
# próprio programa já detecta automaticamente como "ninguém trabalhou"
# (fins de semana, feriados nacionais já fora do range de dias úteis).
#
# Cada entrada é um dicionário com:
#   "alvo"      -> "agente" | "equipe" | "todos"
#   "id_agente" -> obrigatório só quando alvo == "agente"
#   "equipe"    -> obrigatório só quando alvo == "equipe" (nome exato, deve
#                  bater com AGENTES_POR_EQUIPE)
#   "motivo"    -> um destes cinco, sempre: "Chuva", "Folga", "Atestado",
#                  "Reunião/Treinamento", "Férias"
#   "inicio"    -> data "dd/mm/aaaa" (obrigatório)
#   "fim"       -> data "dd/mm/aaaa" (obrigatório — pra um dia só, repete a
#                  mesma data em início e fim)
#   "turno"     -> opcional ("Manhã" ou "Tarde"): a entrada vale SÓ pra esse
#                  turno do dia (Meia folga / Meia ausência justificada).
#                  Sem "turno" a entrada vale o dia inteiro.
#   Rótulo público do atestado: "Ausência justificada" (repositório público —
#   nunca grave CID/diagnóstico). "Atestado" segue válido pra entradas antigas.
MOTIVOS_CRONOGRAMA = [
    "Chuva", "Folga", "Meia folga", "Ausência justificada", "Meia ausência justificada",
    "Atestado", "Reunião/Treinamento", "Férias",
    "Levantamento de Índice", "Instalação de Ovitrampa", "Recolha de Ovitrampa",
    "Recuperação de Casas",
]


CAMINHO_CACHE_NOMES_AGENTES = "data/agentes_nomes.json"
_cache_nomes_agentes_mem = {}  # caminho -> dict carregado (lazy) — ver _cache_nomes_agentes()


def _cache_nomes_agentes(caminho=CAMINHO_CACHE_NOMES_AGENTES):
    """Cache persistente ID -> {nome, equipe}, mantido em memória durante a
    execução pra não reabrir o arquivo a cada agente/semana. É a mesma
    lógica em dois sentidos:
      1) LEITURA — extrair_nome_agente() consulta esse cache como
         penúltimo recurso, ANTES de desistir e usar "Agente_{id}", pra
         quando a resolução ao vivo falhar numa semana específica (o caso
         mais comum: o agente não teve nenhum lançamento naquela semana, e
         a página de "sem resultados" do e-Visita não traz nem o
         <select>, nem o endpoint getedit responde direito).
      2) ESCRITA — toda vez que um nome de verdade É resolvido com sucesso
         (ao vivo, via API ou via página), ele é gravado aqui na hora — não
         só no fim da consolidação — pra já poder ser reaproveitado pelo
         PRÓXIMO agente/semana/pendência dentro da MESMA rodada, e por
         qualquer rodada futura, mesmo que esse agente não apareça de novo
         tão cedo.
    Nunca é apagado por uma rodada que não viu aquele agente — só é
    ATUALIZADO quando um nome de verdade (não genérico) é aprendido."""
    if caminho not in _cache_nomes_agentes_mem:
        cache = {}
        if os.path.exists(caminho):
            try:
                with open(caminho, encoding="utf-8") as f:
                    cache = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                log.warning("⚠️ Não deu pra ler %s (começando um cache de nomes vazio): %s", caminho, e)
        _cache_nomes_agentes_mem[caminho] = cache
    return _cache_nomes_agentes_mem[caminho]


def _atualizar_cache_nomes_agentes(id_agente, nome, equipe=None, caminho=CAMINHO_CACHE_NOMES_AGENTES):
    """Grava (merge, nunca sobrescreve o arquivo inteiro) um nome de
    verdade aprendido pra um agente. Nomes genéricos ("Agente_{id}") NUNCA
    são gravados aqui — só serviriam pra estragar um nome bom que já
    estava salvo de uma rodada anterior."""
    if not nome or str(nome).startswith("Agente_"):
        return
    cache = _cache_nomes_agentes(caminho)
    entrada = cache.get(str(id_agente), {})
    if entrada.get("nome") == nome and (equipe is None or entrada.get("equipe") == equipe):
        return  # já está assim, não precisa regravar o arquivo à toa
    cache[str(id_agente)] = {"nome": nome, "equipe": equipe if equipe is not None else entrada.get("equipe", "")}
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)
    except OSError as e:
        log.warning("⚠️ Não deu pra salvar %s: %s", caminho, e)


def _motivo_neutro(motivo):
    """Repositório público: só rótulos neutros. "Atestado" (entradas antigas)
    e "Férias/Atestado" (rótulo antigo das detecções) viram os neutros."""
    m = str(motivo or "")
    m = m.replace("Férias/Atestado", "Férias")
    if m == "Atestado":
        return "Ausência justificada"
    if m == "Meio atestado":
        return "Meia ausência justificada"
    return m


def _carregar_cronograma_ausencias(caminho="data/cronograma_ausencias.json"):
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        if not isinstance(dados, list):
            log.warning("⚠️ %s não é uma lista — ignorando cronograma/ausências programadas.", caminho)
            return []
        for e in dados:
            if isinstance(e, dict) and "motivo" in e:
                e["motivo"] = _motivo_neutro(e["motivo"])
        return dados
    except (json.JSONDecodeError, OSError) as e:
        log.warning("⚠️ Erro ao ler %s (%s) — ignorando cronograma/ausências programadas.", caminho, e)
        return []

CRONOGRAMA_AUSENCIAS = _carregar_cronograma_ausencias()
