"""
Lógica de semanas do e-Visita
==============================
O e-Visita usa DOIS identificadores diferentes para representar uma mesma
semana:

  - HTML ID     -> usado exclusivamente nas CONSULTAS ao sistema
                   (parâmetros semana_inicio/semana_fim na URL).
  - Semana do Ano -> usada apenas para EXIBIÇÃO ao usuário (dashboard,
                   nomes de arquivo, logs, manifest).

Esses dois números NÃO são a mesma coisa e NÃO devem ser confundidos em
nenhum lugar do código. Este módulo é o único lugar que sabe converter um no
outro — todo o resto do projeto (coletor e gerador do dashboard) importa
daqui em vez de reimplementar a conta.

Regra validada para 2026 (com dados reais do e-Visita):

    HTML 288 = Semana 01
    ...
    HTML 318 = Semana 31
    ...
    HTML 339 = Semana 52

    html_id = semana_ano + 287
    semana_ano = html_id - 287

IMPORTANTE: esse deslocamento (287) só foi confirmado para 2026. Para
qualquer outro ano, o offset PRECISA ser validado contra o site antes de
aplicar a conversão — por isso todas as funções abaixo recebem `ano` como
parâmetro e travam (ValueError) se for um ano sem offset cadastrado, em vez
de silenciosamente devolver um número errado.
"""

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Offsets validados por ano (html_id = semana_ano + OFFSETS[ano]).
# Para adicionar suporte a um novo ano: confirme pelo menos um par
# (html_id, semana_ano) direto no site do e-Visita e cadastre o offset aqui.
# ---------------------------------------------------------------------------
OFFSETS_VALIDADOS = {
    2026: 287,
}

# Âncora usada para achar o HTML ID de uma DATA (não de uma semana_ano) —
# confirmado com dados reais: cada semana do site começa domingo e termina
# sábado; HTML 313 = domingo 28/06/2026.
ANCORA_DATA = date(2026, 6, 28)
ANCORA_HTML_ID = 313

MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
            "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _offset(ano: int) -> int:
    if ano not in OFFSETS_VALIDADOS:
        raise ValueError(
            f"Offset HTML<->Semana do Ano não validado para {ano}. "
            f"Confirme pelo menos um par (html_id, semana_ano) no site do "
            f"e-Visita para {ano} e cadastre o valor em OFFSETS_VALIDADOS "
            f"antes de converter semanas desse ano."
        )
    return OFFSETS_VALIDADOS[ano]


def semana_para_html(semana_ano: int, ano: int = 2026) -> int:
    """Semana do Ano -> HTML ID (para montar a URL de consulta)."""
    return semana_ano + _offset(ano)


def html_para_semana(html_id: int, ano: int = 2026) -> int:
    """HTML ID -> Semana do Ano (para exibir ao usuário)."""
    return html_id - _offset(ano)


def data_inicio_semana_html(html_id: int) -> date:
    """Data (domingo) em que a semana daquele HTML ID começa."""
    return ANCORA_DATA + timedelta(days=(html_id - ANCORA_HTML_ID) * 7)


def data_fim_semana_html(html_id: int) -> date:
    """Data (sábado) em que a semana daquele HTML ID termina."""
    return data_inicio_semana_html(html_id) + timedelta(days=6)


def html_id_da_data(dia: date) -> int:
    """Dado um dia qualquer, devolve o HTML ID da semana do site que contém
    esse dia (cada semana do site vai de domingo a sábado)."""
    return ANCORA_HTML_ID + (dia - ANCORA_DATA).days // 7


def semana_atual_html(hoje: date = None) -> int:
    """HTML ID da semana do site que contém hoje (ou a data passada)."""
    return html_id_da_data(hoje or date.today())


def ano_da_semana_html(html_id: int) -> int:
    """Ano civil predominante da semana (baseado na data de início)."""
    return data_inicio_semana_html(html_id).year


def rotulo_semana_html(html_id: int) -> str:
    """Rótulo amigável pra exibir uma semana ao usuário, ex.:
    'Semana 26/2026 (28/06 a 04/07)'."""
    ano = ano_da_semana_html(html_id)
    semana_ano = html_para_semana(html_id, ano)
    ini = data_inicio_semana_html(html_id)
    fim = data_fim_semana_html(html_id)
    return f"Semana {semana_ano:02d}/{ano} ({ini.strftime('%d/%m')} a {fim.strftime('%d/%m')})"


def nome_periodo(html_id_inicio: int, html_id_fim: int) -> str:
    """Rótulo amigável pro seletor de período do dashboard: nome do mês em
    que CAI A MAIORIA das semanas do intervalo (evita que uma semana de
    virada, tipo 28/06 a 04/07, vire 'Junho-Agosto' só por causa de 1 dia
    em cada ponta). Só usa 'Mês1-Mês2/ano' se o intervalo genuinamente
    cobrir vários meses quase por igual (mais de uma semana em cada um)."""
    from collections import Counter
    meses = [data_inicio_semana_html(h).month for h in range(html_id_inicio, html_id_fim + 1)]
    ano = data_inicio_semana_html(html_id_fim).year
    contagem = Counter(meses)
    if len(contagem) == 1:
        return f"{MESES_PT[meses[0] - 1]}/{ano}"
    mes_predominante, qtd = contagem.most_common(1)[0]
    if qtd / len(meses) >= 0.6:
        return f"{MESES_PT[mes_predominante - 1]}/{ano}"
    m_ini, m_fim = min(contagem), max(contagem)
    return f"{MESES_PT[m_ini - 1]}-{MESES_PT[m_fim - 1]}/{ano}"


def mes_da_semana_html(html_id: int) -> tuple:
    """(ano, mês) predominante de uma semana — usado para agrupar semanas em
    meses na hora de montar os arquivos de histórico."""
    d = data_inicio_semana_html(html_id)
    return (d.year, d.month)


if __name__ == "__main__":
    # Autoteste rápido com os exemplos dados como referência.
    assert semana_para_html(1, 2026) == 288, semana_para_html(1, 2026)
    assert html_para_semana(318, 2026) == 31, html_para_semana(318, 2026)
    assert html_para_semana(339, 2026) == 52, html_para_semana(339, 2026)
    assert html_para_semana(313, 2026) == 26, html_para_semana(313, 2026)
    print("OK — conversões batem com os exemplos validados para 2026.")
