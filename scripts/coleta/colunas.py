# -*- coding: utf-8 -*-
"""Listas de colunas (COLS_*) de cada aba da planilha consolidada.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""


# ============================================================
# PLANILHA
# ============================================================

COLS_RESUMO = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Classificação", "classificacao"),
    ("Imóveis Abertos", "total_visitas"),
    ("Dias Trabalhados", "dias_trabalhados"),
    ("Visitas/Dia", "visitas_por_dia"),
    ("Média (min)", "media_min"),
    ("Mediana (min)", "mediana_min"),
    ("Rápidas", "visitas_rapidas"),
    ("% Rápidas", "pct_rapidas"),
    ("Longas", "visitas_longas"),
    ("Negativas", "visitas_negativas"),
    ("Dias c/ Meta", "dias_atingiu_meta"),
    ("Visitas Duplicadas", "visitas_duplicadas"),
    ("Visitas em Sequência Suspeita", "visitas_seq_suspeita"),
    ("Visitas no Almoço (11h15-12h45)", "visitas_horario_almoco"),
    ("Fora do Expediente/Fim de Semana", "visitas_fora_expediente"),
    ("Imóveis Fechados", "imoveis_fechados"),
    ("Imóveis Recusados", "imoveis_recusados"),
    ("Total Geral (Abertos+Fechados+Recusados)", "total_geral_pendencia"),
    ("% Pendência", "pct_pendencia"),
    ("Média Horas Trabalhadas/Dia", "media_horas_trabalhadas_dia"),
    ("Média Horas Trabalhadas/Semana", "media_horas_trabalhadas_semana"),
    ("Média Horas Úteis/Dia", "media_horas_uteis_dia"),
    ("Custo Hora Útil (R$)", "custo_hora_util"),
    ("Média Início Manhã", "inicio_manhã"),
    ("Média Fim Manhã", "fim_manhã"),
    ("Média Início Tarde", "inicio_tarde"),
    ("Média Fim Tarde", "fim_tarde"),
]

COLS_RANKING = [
    ("Posição", "posicao"),
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Dias Trabalhados", "dias_trabalhados"),
    ("Dias Úteis Esperados no Mês", "dias_uteis_esperados"),
    ("Turnos Sem Trabalhar", "turnos_sem_trabalhar"),
    ("Pontuação Final", "pontos"),
    ("Classificação", "classificacao"),
    ("Observação", "observacao"),
]

COLS_RANKING_DETALHE = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Critério", "motivo"),
    ("Quantidade", "qtd"),
    ("Peso Nominal (tabela de critérios)", "peso_nominal"),
    ("Fator de Normalização", "fator_normalizacao"),
    ("Peso Efetivo (nominal × fator)", "peso"),
    ("Pontos Aplicados", "pontos"),
]

COLS_PONTO_ESTRATEGICO = [
    ("Semana", "semana"),
    ("Período", "periodo_semana"),
] + COLS_RESUMO

COLS_AREA = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Área", "area"),
    ("Qtd Imóveis Abertos", "qtd_visitas"),
    ("Tempo Médio (min)", "tempo_medio"),
    ("Mediana (min)", "tempo_mediana"),
    ("Qtd Quarteirões", "qtd_quarteiroes"),
    ("Quarteirões", "quarteiroes"),
    ("Rápidas", "rapidas"),
    ("% Rápidas", "pct_rapidas"),
    ("Qtd Fechados", "qtd_fechados"),
    ("Qtd Recusados", "qtd_recusados"),
    ("% Pendência", "pct_pendencia_area"),
    ("Alerta", "alerta"),
]

COLS_DUPLICADAS = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
    ("Motivo", "motivo_duplicacao"),
]

COLS_SUSPEITAS = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Cadeia", "grupo_sequencia_suspeita"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
    ("Diferença p/ Anterior (s)*", "diff_chegada_anterior_seg"),
]

COLS_NEGATIVAS = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
    ("Duração (min)", "duracao_min"),
    ("Observação", "observacao"),
]

COLS_ACIMA_TETO_MEDIA = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
    ("Duração (min)", "duracao_min"),
]

COLS_FORA_EXPEDIENTE = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Dia da Semana", "dia_semana"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
    ("Motivo", "motivo"),
]

COLS_ALMOCO = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
]

COLS_AUSENCIAS = [
    ("ID Agente", "id_agente"),
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Dia", "dia_fmt"),
    ("Dia da Semana", "dia_semana"),
    ("Turno", "turno"),
    ("Observação", "observacao"),
]

COLS_CRONOGRAMA = [
    ("Dia Início", "dia_inicio"),
    ("Dia Fim", "dia_fim"),
    ("Motivo", "motivo"),
    ("Quem", "alvo_fmt"),
]

COLS_PENDENCIAS_RESUMO = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("Imóveis Abertos", "abertos"),
    ("Imóveis Fechados", "fechados"),
    ("Imóveis Recusados", "recusados"),
    ("Total Geral", "total_geral"),
    ("% Pendência", "pct_pendencia"),
]

COLS_RECUSADOS_DETALHE = [
    ("Agente", "nome_agente"),
    ("Equipe", "equipe"),
    ("ID Visita", "id_visita"),
    ("Área", "area"),
    ("Quarteirão", "quarteirao"),
    ("Logradouro", "logradouro"),
    ("Imóvel", "imovel"),
    ("Data Chegada", "data_chegada"),
    ("Data Saída", "data_saida"),
]
