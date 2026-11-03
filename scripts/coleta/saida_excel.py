# -*- coding: utf-8 -*-
"""Saída: CSVs e salvar_excel_consolidado.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import os
import csv
import re
import unicodedata
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from .parametros import (
    ARQUIVO_CONSOLIDADO,
    HORA_ALMOCO_FIM_MIN,
    HORA_ALMOCO_INICIO_MIN,
    HORA_EXPEDIENTE_MANHA_FIM,
    HORA_EXPEDIENTE_MANHA_INICIO,
    HORA_EXPEDIENTE_TARDE_FIM,
    HORA_EXPEDIENTE_TARDE_INICIO,
    TETO_DURACAO_MEDIA_MIN,
)
from .pontos import PONTOS_INICIAIS
from .auxiliares import _fmt_hora_min
from .colunas import (
    COLS_ACIMA_TETO_MEDIA,
    COLS_ALMOCO,
    COLS_AREA,
    COLS_AUSENCIAS,
    COLS_CRONOGRAMA,
    COLS_DUPLICADAS,
    COLS_FORA_EXPEDIENTE,
    COLS_NEGATIVAS,
    COLS_PENDENCIAS_RESUMO,
    COLS_PONTO_ESTRATEGICO,
    COLS_RANKING,
    COLS_RANKING_DETALHE,
    COLS_RECUSADOS_DETALHE,
    COLS_RESUMO,
    COLS_SUSPEITAS,
)
from .estilo_excel import _adicionar_legenda, _escrever, _estilizar
from .abas import (
    _formatar_campos_resumo,
    _preparar_acima_teto_media,
    _preparar_almoco,
    _preparar_area,
    _preparar_duplicadas,
    _preparar_fora_expediente,
    _preparar_negativas,
    _preparar_resumo,
    _preparar_suspeitas,
)
from .ausencias_ranking import (
    _preparar_ausencias,
    _preparar_cronograma,
    _preparar_pendencias_resumo,
    _preparar_ranking,
    _preparar_recusados_detalhe,
)

log = logging.getLogger("evisita")


def _slugify_nome_arquivo(nome):
    """Converte o título de uma aba (com espaços/acentos) num nome de arquivo seguro."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    limpo = re.sub(r"[^\w\s-]", "", sem_acento).strip().replace(" ", "_")
    return limpo or "aba"


def exportar_todas_abas_csv(wb, pasta_saida):
    """
    Exporta CADA aba do workbook como um arquivo .csv separado (com os
    mesmos valores exibidos no Excel), já que um único CSV não suporta
    múltiplas abas. Os arquivos ficam em <pasta_saida>/csv/.
    """
    pasta_csv = os.path.join(pasta_saida, "csv")
    os.makedirs(pasta_csv, exist_ok=True)
    arquivos_gerados = []

    for ws in wb.worksheets:
        nome_arquivo = _slugify_nome_arquivo(ws.title) + ".csv"
        caminho_csv = os.path.join(pasta_csv, nome_arquivo)
        try:
            with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f:
                escritor = csv.writer(f, delimiter=";")
                for row in ws.iter_rows(values_only=True):
                    escritor.writerow(["" if v is None else v for v in row])
            arquivos_gerados.append(caminho_csv)
        except OSError as e:
            log.warning("Não foi possível exportar a aba '%s' para CSV: %s", ws.title, e)

    log.info("✅ %s abas exportadas em CSV, em: %s", len(arquivos_gerados), pasta_csv)
    return pasta_csv, arquivos_gerados


def salvar_excel_consolidado(resultados, df_total, pasta_saida, semanas_ponto_estrategico=None,
                              semanas_tratamento=None, lista_cronograma=None):
    os.makedirs(pasta_saida, exist_ok=True)
    caminho = os.path.join(pasta_saida, ARQUIVO_CONSOLIDADO)
    log.info("💾 Salvando %s", caminho)

    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("Resumo Geral")
    for col, (titulo, _) in enumerate(COLS_RESUMO, 1):
        ws.cell(row=2, column=col, value=titulo)
    registros_resumo = [_preparar_resumo(r) for r in resultados]
    linha_final = _escrever(ws, 3, registros_resumo, COLS_RESUMO)
    ultima_linha_dados = linha_final - 1
    _estilizar(ws, 2, titulo="RESUMO CONSOLIDADO — TODOS OS AGENTES", ultima_linha_dados=ultima_linha_dados)
    _adicionar_legenda(ws, linha_final + 2)

    ws_a = wb.create_sheet("Por Área")
    for col, (titulo, _) in enumerate(COLS_AREA, 1):
        ws_a.cell(row=2, column=col, value=titulo)
    regs = []
    for res in resultados:
        regs.extend(_preparar_area(df_total[df_total["id_agente"] == res["id_agente"]], res))
    linha_final_a = _escrever(ws_a, 3, regs, COLS_AREA)
    ultima_linha_dados_a = linha_final_a - 1
    _estilizar(ws_a, 2, cor_cab="1F3864", titulo="ANÁLISE POR ÁREA", ultima_linha_dados=ultima_linha_dados_a)
    _adicionar_legenda(ws_a, linha_final_a + 2)

    ws_d = wb.create_sheet("Visitas Duplicadas")
    for col, (titulo, _) in enumerate(COLS_DUPLICADAS, 1):
        ws_d.cell(row=2, column=col, value=titulo)
    regs_dup = _preparar_duplicadas(df_total)
    linha_final_d = _escrever(ws_d, 3, regs_dup, COLS_DUPLICADAS)
    ultima_linha_dados_d = linha_final_d - 1
    _estilizar(ws_d, 2, cor_cab="8C3B00",
               titulo=f"VISITAS DUPLICADAS ({len(regs_dup)} registros) — CONFIRME E EXCLUA NO SISTEMA",
               ultima_linha_dados=ultima_linha_dados_d)

    ws_s = wb.create_sheet("Visitas Suspeitas")
    for col, (titulo, _) in enumerate(COLS_SUSPEITAS, 1):
        ws_s.cell(row=2, column=col, value=titulo)
    regs_susp = _preparar_suspeitas(df_total)
    linha_final_s = _escrever(ws_s, 3, regs_susp, COLS_SUSPEITAS)
    ultima_linha_dados_s = linha_final_s - 1
    _estilizar(ws_s, 2, cor_cab="7A4B00",
               titulo=f"VISITAS EM SEQUÊNCIA SUSPEITA ({len(regs_susp)} registros) — "
                      f"CHEGADA NO MESMO MINUTO DA VISITA ANTERIOR",
               ultima_linha_dados=ultima_linha_dados_s)
    _adicionar_legenda(ws_s, linha_final_s + 2)

    ws_n = wb.create_sheet("Visitas Negativas")
    for col, (titulo, _) in enumerate(COLS_NEGATIVAS, 1):
        ws_n.cell(row=2, column=col, value=titulo)
    regs_neg = _preparar_negativas(df_total)
    linha_final_n = _escrever(ws_n, 3, regs_neg, COLS_NEGATIVAS)
    ultima_linha_dados_n = linha_final_n - 1
    _estilizar(ws_n, 2, cor_cab="595959",
               titulo=f"VISITAS COM DURAÇÃO NEGATIVA ({len(regs_neg)} registros) — "
                      f"PROVÁVEL BUG DO SISTEMA, EXCLUÍDAS DA MÉDIA/MEDIANA",
               ultima_linha_dados=ultima_linha_dados_n)
    _adicionar_legenda(ws_n, linha_final_n + 2)

    ws_teto = wb.create_sheet(f"Visitas Acima de {TETO_DURACAO_MEDIA_MIN}min")
    for col, (titulo, _) in enumerate(COLS_ACIMA_TETO_MEDIA, 1):
        ws_teto.cell(row=2, column=col, value=titulo)
    regs_teto = _preparar_acima_teto_media(df_total)
    linha_final_teto = _escrever(ws_teto, 3, regs_teto, COLS_ACIMA_TETO_MEDIA)
    ultima_linha_dados_teto = linha_final_teto - 1
    _estilizar(ws_teto, 2, cor_cab="4A5568",
               titulo=f"VISITAS COM DURAÇÃO ACIMA DE {TETO_DURACAO_MEDIA_MIN}MIN ({len(regs_teto)} registros) — "
                      f"AUDITORIA DE POSSÍVEL MANIPULAÇÃO DE HORÁRIO (LANÇAMENTO PELO COMPUTADOR); "
                      f"NO CÁLCULO DE MÉDIA/MEDIANA ENTRAM COMO {TETO_DURACAO_MEDIA_MIN}MIN",
               ultima_linha_dados=ultima_linha_dados_teto)

    ws_fe = wb.create_sheet("Fora do Expediente")
    for col, (titulo, _) in enumerate(COLS_FORA_EXPEDIENTE, 1):
        ws_fe.cell(row=2, column=col, value=titulo)
    regs_fe = _preparar_fora_expediente(df_total)
    linha_final_fe = _escrever(ws_fe, 3, regs_fe, COLS_FORA_EXPEDIENTE)
    ultima_linha_dados_fe = linha_final_fe - 1
    _estilizar(ws_fe, 2, cor_cab="8C1F1F",
               titulo=f"VISITAS FORA DO EXPEDIENTE / FIM DE SEMANA ({len(regs_fe)} registros) — "
                      f"HORÁRIO OFICIAL: {HORA_EXPEDIENTE_MANHA_INICIO}h-{HORA_EXPEDIENTE_MANHA_FIM}h "
                      f"E {HORA_EXPEDIENTE_TARDE_INICIO}h-{HORA_EXPEDIENTE_TARDE_FIM}h, DIAS ÚTEIS",
               ultima_linha_dados=ultima_linha_dados_fe)

    ws_al = wb.create_sheet("Visitas no Almoço")
    for col, (titulo, _) in enumerate(COLS_ALMOCO, 1):
        ws_al.cell(row=2, column=col, value=titulo)
    regs_al = _preparar_almoco(df_total)
    linha_final_al = _escrever(ws_al, 3, regs_al, COLS_ALMOCO)
    ultima_linha_dados_al = linha_final_al - 1
    _estilizar(ws_al, 2, cor_cab="1F6F5C",
               titulo=f"VISITAS NO HORÁRIO DE ALMOÇO ({len(regs_al)} registros) — "
                      f"{_fmt_hora_min(HORA_ALMOCO_INICIO_MIN)} ÀS {_fmt_hora_min(HORA_ALMOCO_FIM_MIN)} "
                      f"(TOLERÂNCIA DE 15MIN JÁ APLICADA)",
               ultima_linha_dados=ultima_linha_dados_al)

    ws_aus = wb.create_sheet("Ausências")
    for col, (titulo, _) in enumerate(COLS_AUSENCIAS, 1):
        ws_aus.cell(row=2, column=col, value=titulo)
    regs_aus = _preparar_ausencias(df_total, resultados, lista_cronograma)
    linha_final_aus = _escrever(ws_aus, 3, regs_aus, COLS_AUSENCIAS)
    ultima_linha_dados_aus = linha_final_aus - 1
    _estilizar(ws_aus, 2, cor_cab="4A4A4A",
               titulo=f"POSSÍVEIS AUSÊNCIAS POR DIA/TURNO ({len(regs_aus)} registros) — "
                      f"CONFIRMAR COM A ESCALA (FOLGA/ATESTADO/FALTA)",
               ultima_linha_dados=ultima_linha_dados_aus)

    ws_cron = wb.create_sheet("Cronograma")
    for col, (titulo, _) in enumerate(COLS_CRONOGRAMA, 1):
        ws_cron.cell(row=2, column=col, value=titulo)
    periodo_dias = df_total["dia"] if "dia" in df_total.columns and not df_total.empty else None
    data_min = periodo_dias.min() if periodo_dias is not None and not periodo_dias.empty else None
    data_max = periodo_dias.max() if periodo_dias is not None and not periodo_dias.empty else None
    regs_cron = _preparar_cronograma(resultados, data_min, data_max, lista_cronograma)
    linha_final_cron = _escrever(ws_cron, 3, regs_cron, COLS_CRONOGRAMA)
    ultima_linha_dados_cron = linha_final_cron - 1
    _estilizar(ws_cron, 2, cor_cab="2E5C8A",
               titulo=f"CRONOGRAMA — CHUVA/FOLGA/ATESTADO/REUNIÃO/FÉRIAS ({len(regs_cron)} registros) — "
                      f"EXCLUÍDOS DA ABA 'AUSÊNCIAS'. Edite em data/cronograma_ausencias.json "
                      f"(use cronograma_editor.html).",
               ultima_linha_dados=ultima_linha_dados_cron)

    ws_pend = wb.create_sheet("Recusados e Pendências")
    for col, (titulo, _) in enumerate(COLS_PENDENCIAS_RESUMO, 1):
        ws_pend.cell(row=2, column=col, value=titulo)
    regs_pend = _preparar_pendencias_resumo(resultados)
    linha_final_pend = _escrever(ws_pend, 3, regs_pend, COLS_PENDENCIAS_RESUMO)
    _estilizar(ws_pend, 2, cor_cab="7A1F1F",
               titulo="RESUMO DE PENDÊNCIA POR AGENTE (com Total Geral) — "
                      "% Pendência = (Fechados + Recusados) / (Abertos+Fechados+Recusados)")

    linha_detalhe_inicio = linha_final_pend + 2
    ws_pend.cell(row=linha_detalhe_inicio, column=1,
                  value=f"DETALHE — IMÓVEIS COM VISITA RECUSADA PELO MORADOR")
    ws_pend.cell(row=linha_detalhe_inicio, column=1).font = Font(bold=True, size=11, color="FFFFFF")
    ws_pend.cell(row=linha_detalhe_inicio, column=1).fill = PatternFill("solid", fgColor="7A1F1F")
    ws_pend.merge_cells(start_row=linha_detalhe_inicio, start_column=1,
                          end_row=linha_detalhe_inicio, end_column=len(COLS_RECUSADOS_DETALHE))
    for col, (titulo, _) in enumerate(COLS_RECUSADOS_DETALHE, 1):
        cell = ws_pend.cell(row=linha_detalhe_inicio + 1, column=col, value=titulo)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="A34A4A")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    regs_recusados = _preparar_recusados_detalhe(resultados)
    linha_final_recusados = _escrever(ws_pend, linha_detalhe_inicio + 2, regs_recusados, COLS_RECUSADOS_DETALHE)

    # Sem autofiltro aqui: são duas tabelas com colunas diferentes empilhadas
    # na mesma aba, então um filtro único não faria sentido. Só recalcula a
    # largura das colunas considerando todo o conteúdo já escrito.
    _estilizar(ws_pend, 2)

    if semanas_ponto_estrategico:
        ws_pe = wb.create_sheet("Ponto Estratégico")
        for col, (titulo, _) in enumerate(COLS_PONTO_ESTRATEGICO, 1):
            ws_pe.cell(row=2, column=col, value=titulo)
        regs_pe = _preparar_ponto_estrategico(semanas_ponto_estrategico)
        linha_final_pe = _escrever(ws_pe, 3, regs_pe, COLS_PONTO_ESTRATEGICO)
        ultima_linha_dados_pe = linha_final_pe - 1
        _estilizar(ws_pe, 2, cor_cab="4A2E6B",
                   titulo=f"PONTO ESTRATÉGICO — RESULTADOS POR SEMANA ({len(regs_pe)} linhas)",
                   ultima_linha_dados=ultima_linha_dados_pe)
        _adicionar_legenda(ws_pe, linha_final_pe + 2)

    # Resumo Semanal (tratamento) — mesma métrica do Resumo Geral, só que
    # quebrada por semana em vez de somada no período inteiro. Alimenta o
    # filtro "por semana" do dashboard (aba Resumo/Agentes). Só existe
    # quando o período consolidado cobre mais de uma semana — com uma
    # semana só ela seria idêntica ao Resumo Geral.
    if semanas_tratamento:
        ws_rs = wb.create_sheet("Resumo Semanal")
        for col, (titulo, _) in enumerate(COLS_PONTO_ESTRATEGICO, 1):
            ws_rs.cell(row=2, column=col, value=titulo)
        regs_rs = _preparar_ponto_estrategico(semanas_tratamento)
        linha_final_rs = _escrever(ws_rs, 3, regs_rs, COLS_PONTO_ESTRATEGICO)
        ultima_linha_dados_rs = linha_final_rs - 1
        _estilizar(ws_rs, 2, cor_cab="0F5132",
                   titulo=f"RESUMO GERAL — QUEBRADO POR SEMANA ({len(regs_rs)} linhas)",
                   ultima_linha_dados=ultima_linha_dados_rs)
        _adicionar_legenda(ws_rs, linha_final_rs + 2)

    # --- Ranking / Pontuação ---
    data_max_periodo = df_total["dia"].max() if not df_total.empty else None
    data_min_periodo = df_total["dia"].min() if not df_total.empty else None
    ranking_principal, ranking_detalhe = _preparar_ranking(
        resultados, regs_aus, data_max_periodo, lista_cronograma, data_min_periodo)

    ws_rk = wb.create_sheet("Ranking")
    for col, (titulo, _) in enumerate(COLS_RANKING, 1):
        ws_rk.cell(row=2, column=col, value=titulo)
    linha_final_rk = _escrever(ws_rk, 3, ranking_principal, COLS_RANKING)
    ultima_linha_dados_rk = linha_final_rk - 1
    _estilizar(ws_rk, 2, cor_cab="1A1A2E",
               titulo=f"RANKING DOS AGENTES — TODOS COMEÇAM COM {PONTOS_INICIAIS} PONTOS",
               ultima_linha_dados=ultima_linha_dados_rk)

    linha_detalhe_rk_inicio = linha_final_rk + 2
    ws_rk.cell(row=linha_detalhe_rk_inicio, column=1,
                value="DETALHAMENTO — TODOS OS CRITÉRIOS APLICADOS POR AGENTE")
    ws_rk.cell(row=linha_detalhe_rk_inicio, column=1).font = Font(bold=True, size=11, color="FFFFFF")
    ws_rk.cell(row=linha_detalhe_rk_inicio, column=1).fill = PatternFill("solid", fgColor="1A1A2E")
    ws_rk.merge_cells(start_row=linha_detalhe_rk_inicio, start_column=1,
                        end_row=linha_detalhe_rk_inicio, end_column=len(COLS_RANKING_DETALHE))
    for col, (titulo, _) in enumerate(COLS_RANKING_DETALHE, 1):
        cell = ws_rk.cell(row=linha_detalhe_rk_inicio + 1, column=col, value=titulo)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="2E4057")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    _escrever(ws_rk, linha_detalhe_rk_inicio + 2, ranking_detalhe, COLS_RANKING_DETALHE)

    # Sem autofiltro: duas tabelas com colunas diferentes empilhadas na mesma aba.
    _estilizar(ws_rk, 2)

    wb.save(caminho)
    log.info("✅ Consolidado salvo!")

    # Exporta TODAS as abas também em CSV (arquivo idêntico ao Excel, só que
    # em CSV — como CSV não suporta múltiplas abas, gera um .csv por aba).
    exportar_todas_abas_csv(wb, pasta_saida)

    return caminho


def _preparar_ponto_estrategico(semanas_todos_agentes):
    registros = []
    for item in semanas_todos_agentes:
        r, classif, fill = _formatar_campos_resumo(item["resumo"])
        registros.append({
            **r,
            "nome_agente": item["nome_agente"],
            "equipe": item["equipe"],
            "semana": item["semana"],
            "periodo_semana": item["periodo_semana"],
            "classificacao": classif,
            "_fill": fill,
        })
    registros.sort(key=lambda x: (x["nome_agente"], x["semana"]))
    return registros
