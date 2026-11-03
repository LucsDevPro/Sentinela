# -*- coding: utf-8 -*-
"""Estilo do Excel: formatação, legenda e escrita das abas.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from .parametros import (
    DIAS_UTEIS_MES,
    HORA_ALMOCO_FIM_MIN,
    HORA_ALMOCO_INICIO_MIN,
    LIMIAR_SEQUENCIA_SUSPEITA_SEG,
    PCT_RAPIDAS_ATENCAO_ATE,
    PCT_RAPIDAS_OK_ATE,
    SALARIO_AGENTE,
    URL_VISITAS,
)
from .auxiliares import _fmt_hora_min


def _estilizar(ws, linha_cab: int, cor_cab="2E4057", titulo=None, ultima_linha_dados=None):
    lado = Side(style="thin")
    borda = Border(left=lado, right=lado, top=lado, bottom=lado)

    if titulo:
        n_cols = ws.max_column
        ws.merge_cells(f"A1:{get_column_letter(n_cols)}1")
        c = ws["A1"]
        c.value = titulo
        c.font = Font(bold=True, size=12, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1A1A2E")
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 26

    for cell in ws[linha_cab]:
        if cell.value is None:
            continue
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor=cor_cab)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[linha_cab].height = 28

    for row in ws.iter_rows():
        for cell in row:
            cell.border = borda

    # Autoajuste de largura: mede o maior conteúdo de cada coluna a partir da
    # linha 2 (pula a linha 1, que é o título mesclado e distorceria a coluna A).
    for col in range(1, ws.max_column + 1):
        larg = max(
            (len(str(row[0].value or "")) for row in ws.iter_rows(min_row=2, min_col=col, max_col=col)),
            default=8,
        )
        ws.column_dimensions[get_column_letter(col)].width = max(8, min(larg + 2, 45))

    # Autofiltro: da linha de cabeçalho até a última linha de dados
    if ultima_linha_dados and ultima_linha_dados >= linha_cab:
        n_cols = ws.max_column
        ws.auto_filter.ref = f"A{linha_cab}:{get_column_letter(n_cols)}{ultima_linha_dados}"


def _adicionar_legenda(ws, linha_inicio: int):
    """Adiciona bloco de legenda explicando a classificação por % de visitas rápidas e outros alertas."""
    itens = [
        ("🟢 NORMAL", "D6F5D6", f"% Rápidas até {PCT_RAPIDAS_OK_ATE}%"),
        ("🟡 ATENÇÃO", "FFF9B0", f"% Rápidas entre {PCT_RAPIDAS_OK_ATE + 1}% e {PCT_RAPIDAS_ATENCAO_ATE}%"),
        ("🔴 CRÍTICO", "FFB3B3", f"% Rápidas acima de {PCT_RAPIDAS_ATENCAO_ATE}%"),
    ]

    linha = linha_inicio
    cab = ws.cell(row=linha, column=1, value="LEGENDA — CLASSIFICAÇÃO (baseada em % de Visitas Rápidas)")
    cab.font = Font(bold=True, size=10, color="FFFFFF")
    cab.fill = PatternFill("solid", fgColor="2E4057")
    n_cols_legenda = 3
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    cab.alignment = Alignment(horizontal="left", vertical="center")
    linha += 1

    lado = Side(style="thin")
    borda = Border(left=lado, right=lado, top=lado, bottom=lado)
    for rotulo, cor, descricao in itens:
        c1 = ws.cell(row=linha, column=1, value=rotulo)
        c1.fill = PatternFill("solid", fgColor=cor)
        c1.font = Font(bold=True, size=10)
        c1.alignment = Alignment(horizontal="center", vertical="center")
        c1.border = borda

        c2 = ws.cell(row=linha, column=2, value=descricao)
        c2.alignment = Alignment(horizontal="left", vertical="center")
        c2.border = borda
        ws.merge_cells(start_row=linha, start_column=2, end_row=linha, end_column=n_cols_legenda)
        linha += 1

    linha += 1  # linha em branco

    # Explicação da Sequência Suspeita
    cab2 = ws.cell(row=linha, column=1, value="⚠️ SEQUÊNCIA SUSPEITA")
    cab2.font = Font(bold=True, size=10, color="FFFFFF")
    cab2.fill = PatternFill("solid", fgColor="7A4B00")
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    cab2.alignment = Alignment(horizontal="left", vertical="center")
    linha += 1

    desc = ws.cell(
        row=linha, column=1,
        value=("Duas ou mais visitas consecutivas do mesmo agente registradas no MESMO "
                "MINUTO de chegada são marcadas como suspeitas (o e-Visita não registra "
                "segundos, então o critério de negócio de "
                f"{LIMIAR_SEQUENCIA_SUSPEITA_SEG}s de diferença equivale, na prática, a "
                "'mesmo minuto') — sugere lançamento em lote no sistema, não visita real "
                "de campo. Colunas: 'Visitas em Sequência Suspeita' (total de visitas "
                "envolvidas) e 'Maior Sequência Suspeita' (maior número de visitas "
                "seguidas nessa condição). Na aba 'Visitas Suspeitas', a coluna "
                "'Diferença p/ Anterior (s)*' fica em branco quando o alerta da "
                "linha veio do par com a visita SEGUINTE (não da anterior).")
    )
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    desc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[linha].height = 45
    linha += 1

    linha += 1  # linha em branco

    # Explicação do Horário de Almoço
    cab3 = ws.cell(row=linha, column=1, value="🍽️ VISITAS NO HORÁRIO DE ALMOÇO")
    cab3.font = Font(bold=True, size=10, color="FFFFFF")
    cab3.fill = PatternFill("solid", fgColor="1F6F5C")
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    cab3.alignment = Alignment(horizontal="left", vertical="center")
    linha += 1

    desc3 = ws.cell(
        row=linha, column=1,
        value=(f"Coluna 'Visitas no Almoço ({_fmt_hora_min(HORA_ALMOCO_INICIO_MIN)}-"
                f"{_fmt_hora_min(HORA_ALMOCO_FIM_MIN)})' conta as visitas com chegada registrada "
                f"nesse intervalo — o horário oficial de almoço é {_fmt_hora_min(HORA_ALMOCO_INICIO_MIN)} "
                f"às {_fmt_hora_min(HORA_ALMOCO_FIM_MIN)}, JÁ COM 15 MINUTOS DE TOLERÂNCIA em cada "
                "borda (visitas entre 11h-11h15 ou 12h45-13h não são tratadas como violação, só como "
                "'fora do expediente' genérico) — use para checar se o agente está trabalhando no "
                "horário de almoço ou se há erro de lançamento. Essas visitas ficam de fora do cálculo "
                "de 'Início/Fim Manhã' e 'Início/Fim Tarde', que usam a primeira chegada e a última "
                "saída de cada dia (não a média de todos os horários), para refletir melhor o início "
                "e o fim reais do expediente.")
    )
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    desc3.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[linha].height = 70
    linha += 1

    linha += 1  # linha em branco

    # Explicação de Horas Trabalhadas / Horas Úteis / Custo da Hora Útil
    cab4 = ws.cell(row=linha, column=1, value="💰 HORAS TRABALHADAS, HORAS ÚTEIS E CUSTO DA HORA ÚTIL")
    cab4.font = Font(bold=True, size=10, color="FFFFFF")
    cab4.fill = PatternFill("solid", fgColor="4A6741")
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    cab4.alignment = Alignment(horizontal="left", vertical="center")
    linha += 1

    desc4 = ws.cell(
        row=linha, column=1,
        value=("'Horas Trabalhadas' = jornada total do dia (primeira chegada até a última "
                "saída), descontando a sobreposição com o horário de almoço — depois tira-se "
                "a média entre os dias/semanas trabalhados. 'Horas Úteis' = soma das durações "
                "de visita no dia (tempo realmente dentro de imóveis), sem contar deslocamento "
                "entre visitas. 'Custo Hora Útil' = salário mensal do agente "
                f"(R$ {SALARIO_AGENTE:.2f}".replace(".", ",") + f", equivalente a 3 salários "
                f"mínimos federais) dividido pelas horas úteis mensais estimadas (Média Horas "
                f"Úteis/Dia × {DIAS_UTEIS_MES} dias úteis/mês). Quanto menos tempo o agente "
                "passa efetivamente em visita por dia, mais caro fica o custo por hora útil.")
    )
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    desc4.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[linha].height = 60
    linha += 1

    linha += 1  # linha em branco

    # Nota sobre a aba de duplicadas
    nota = ws.cell(
        row=linha, column=1,
        value=("ℹ️ A lista detalhada de visitas duplicadas (com endereço) está na aba "
               "'Visitas Duplicadas' — use-a para localizar e excluir os registros repetidos.")
    )
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    nota.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    nota.font = Font(italic=True, size=9)
    linha += 1

    # Nota sobre a aba de negativas
    nota2 = ws.cell(
        row=linha, column=1,
        value=("ℹ️ Visitas com duração NEGATIVA (saída antes da chegada — provável bug do "
               "sistema) foram excluídas do cálculo de Média/Mediana e estão detalhadas na "
               "aba 'Visitas Negativas', para investigação junto ao suporte do e-Visita.")
    )
    ws.merge_cells(start_row=linha, start_column=1, end_row=linha, end_column=n_cols_legenda)
    nota2.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    nota2.font = Font(italic=True, size=9)
    linha += 1

    return linha


def _escrever(ws, linha, registros, colunas):
    for dado in registros:
        fill = dado.get("_fill", "")
        for col, (_, chave) in enumerate(colunas, 1):
            valor = dado.get(chave, "")
            if isinstance(valor, bool):
                valor = "Sim" if valor else "Não"
            if chave == "id_visita" and valor not in ("", None):
                valor = str(int(valor)) if isinstance(valor, float) else str(valor)
            cell = ws.cell(row=linha, column=col, value=valor)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if chave == "id_visita":
                cell.number_format = "@"  # texto — evita notação científica e erros de conversão
                if valor not in ("", None) and str(valor).isdigit():
                    cell.hyperlink = f"{URL_VISITAS}/{valor}/detalhes"
                    cell.font = Font(color="0563C1", underline="single")
            if fill:
                cell.fill = PatternFill("solid", fgColor=fill)
        linha += 1
    return linha
