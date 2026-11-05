# -*- coding: utf-8 -*-
"""Ranking: constantes de pontos (perdas e ganhos) e do evento coletivo por turno.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
from datetime import date


# --- 14) COLETA DE PENDÊNCIA (fechados/recusados) ---------------------------
# Se True, o script faz coletas ADICIONAIS (uma para fechados, uma para
# recusados) além da coleta principal (abertos), para calcular o % de
# pendência e preencher a aba "Recusados e Pendências". Isso TRIPLICA o
# número de requisições feitas ao servidor — desligue (False) se quiser uma
# coleta mais rápida e não precisar dessas colunas/aba agora.
COLETAR_FECHADOS_RECUSADOS = True

# --- 15) RANKING / PONTUAÇÃO DOS AGENTES ------------------------------------
# Todo agente começa com PONTOS_INICIAIS. Cada critério abaixo desconta ou
# soma pontos conforme a quantidade de ocorrências no período analisado.
# Ajuste os pesos livremente — coloque 0 para desligar um critério sem
# precisar remover a linha.

PONTOS_INICIAIS = 100
NOTA_MINIMA = 0      # pontuação não cai abaixo disso (None = sem piso)
NOTA_MAXIMA = 100    # pontuação não passa disso (None = sem teto)
# Teto do fator de normalização "por mês" (ver calcular_pontuacao) — evita
# que quem trabalhou poucos dias no período (ex.: maioria de férias) tenha
# qualquer deslize nesses poucos dias amplificado de forma extrema.
TETO_FATOR_NORMALIZACAO = 2.0

# O ranking NÃO usa o fator de normalização: Peso Efetivo = Peso Nominal para
# todos os agentes, e "Dias Úteis Esperados" desconta os dias de férias/atestado/
# folga/paralisação de cada um. O critério é a PRIMEIRA data do período
# analisado: períodos que começam a partir desta data usam o método novo. Com
# 01/01/2026 isso vale para TODOS os meses (Julho/2026 em diante), mas só para
# períodos de até AVISO_AFASTAMENTO_PERIODO_MAX_DIAS (45) dias: o Acumulado
# (período longo) segue no método antigo, normalizado (ver
# _ranking_sem_normalizacao). Pra desligar a regra e voltar tudo ao método
# antigo, coloque None; pra poupar meses antigos, use a data de início desejada.
RANKING_SEM_NORMALIZACAO_A_PARTIR_DE = date(2026, 1, 1)

# Bônus únicos (sem visita rápida / sem ausência / pontualidade perfeita) só
# valem pra quem trabalhou pelo menos esta fração dos dias úteis ESPERADOS —
# senão quem trabalhou 2 dias levava os mesmos +13 pontos de quem trabalhou o
# mês inteiro. Só vale no método novo (Outubro/2026 em diante, ver acima).
BONUS_MIN_FRACAO_DIAS_ESPERADOS = 0.5

# Presença mínima (método novo): presença = dias trabalhados ÷ dias esperados
# (os esperados JÁ descontam férias/folga/ausência justificada lançadas, então
# quem está de férias ou com atestado lançado NÃO é penalizado aqui). Se a
# presença ficar abaixo deste limite, a nota (antes dos ajustes manuais) é
# multiplicada por presença ÷ limite (nota proporcional). Ex.: limite 50% e
# presença 25% → nota × 0,5. Não vale para as equipes sob demanda.
PRESENCA_MINIMA_FRACAO = 0.5

# Aviso "possível afastamento não registrado" na coluna Observação do ranking:
# o agente trabalhou menos que esta fração dos dias esperados E tem pelo menos
# este número de turnos sem lançamento. Provavelmente é férias/licença/atestado
# que falta lançar no cronograma — a gestão deve conferir antes de punir.
# --- Evento coletivo por TURNO (regra da coordenação, 02/11/2026) ---------
# Turno sem lançamento é a regra: toda ausência que o cronograma não explica
# (chuva, treinamento, atestado, férias, folga, reunião...) vira "Turno sem
# Lançamento" e desconta pontos. A EXCEÇÃO é o padrão coletivo: quando vários
# agentes ficam sem lançamento no mesmo turno, é muito mais provável um evento
# externo (chuva, falta de energia...) ou interno (reunião, capacitação) do
# que dezenas de faltas individuais coincidentes. Aí o turno é classificado
# automaticamente como "Possível Evento Externo ou Interno" — sem desconto —
# pra coordenação confirmar o motivo no cronograma. Dois gatilhos:
#   1) LIMITE_AGENTES_EVENTO_TURNO ou mais agentes (de qualquer equipe) sem
#      lançamento no MESMO dia e turno;
#   2) TODOS os agentes ativos de uma equipe (2 ou mais) sem lançamento no turno.
# "Ativo" = não coberto pelo cronograma naquele turno. Equipes sob demanda
# (EQUIPES_SEM_DETECCAO_AUTOMATICA, ex.: Bloqueio) não entram nas duas regras.
LIMITE_AGENTES_EVENTO_TURNO = 20
# Detecção automática (data/deteccoes_pendentes.json): a regra agora é "ausência
# sem lançamento = Turno sem Lançamento (desconta)" até alguém verificar. Por
# isso as detecções NOVAS entram como "pendente" (continuam contando como turno
# sem lançamento; o padrão coletivo cai na regra de Possível Evento acima) e só
# viram férias/chuva quando a coordenação confirmar. Decisões já tomadas
# (confirmada / falta) NÃO mudam. Ponha True pra voltar ao modo antigo.
CONFIRMAR_FERIAS_AUTOMATICAMENTE = False
CONFIRMAR_CHUVA_AUTOMATICAMENTE = False
# Data a partir da qual a regra de Possível Evento vale. Valor atual: None = vale
# pra TODOS os períodos (Julho/2026 em diante; Julho a Setembro reclassificam
# centenas de turnos e a média de pontos sobe 6 a 8 pontos por mês). Pra poupar os
# meses já fechados, use a data de início de Outubro (veja o comentário no fim da linha).
EVENTO_COLETIVO_A_PARTIR_DE = None   # vale para TODOS os períodos (Julho/2026 em diante); pra voltar a poupar os meses fechados: date(2026, 10, 4)
CLASSIF_TURNO_SEM_LANCAMENTO = "Turno sem Lançamento"
CLASSIF_POSSIVEL_EVENTO = "Possível Evento Externo ou Interno"

AVISO_AFASTAMENTO_FRACAO_MAX = 0.7
AVISO_AFASTAMENTO_TURNOS_MIN = 4
AVISO_AFASTAMENTO_PERIODO_MAX_DIAS = 45   # só em períodos de ~1 mês (não no Acumulado)

def _ranking_sem_normalizacao(data_min, data_max=None):
    """True se o período que começa em `data_min` usa o ranking novo (sem
    fator de normalização). Ver RANKING_SEM_NORMALIZACAO_A_PARTIR_DE."""
    if (data_min is not None and data_max is not None
            and (data_max - data_min).days > AVISO_AFASTAMENTO_PERIODO_MAX_DIAS):
        return False  # período longo (Acumulado): somar vários meses sem normalizar zeraria todo mundo
    return (RANKING_SEM_NORMALIZACAO_A_PARTIR_DE is not None and data_min is not None
            and data_min >= RANKING_SEM_NORMALIZACAO_A_PARTIR_DE)

# Horários de referência para os critérios de pontualidade por turno
# (avaliados DIA A DIA, não pela média do período).
HORA_LIMITE_INICIO_MANHA = (8, 30)    # início da manhã depois disso = atraso
HORA_LIMITE_FIM_MANHA    = (10, 0)    # fim da manhã antes disso = saiu cedo demais
HORA_LIMITE_INICIO_TARDE = (14, 30)   # início da tarde depois disso = atraso
HORA_LIMITE_FIM_TARDE    = (16, 0)    # fim da tarde antes disso = saiu cedo demais

# --- PERDAS (pontos perdidos por ocorrência) ---
PONTOS_PERDA_INICIO_MANHA_ATRASADO = 0.3   # por dia que começou a manhã após HORA_LIMITE_INICIO_MANHA
PONTOS_PERDA_FIM_MANHA_ANTECIPADO  = 0.3   # por dia que terminou a manhã antes de HORA_LIMITE_FIM_MANHA
PONTOS_PERDA_INICIO_TARDE_ATRASADO = 0.3   # por dia que começou a tarde após HORA_LIMITE_INICIO_TARDE
PONTOS_PERDA_FIM_TARDE_ANTECIPADO  = 0.3   # por dia que terminou a tarde antes de HORA_LIMITE_FIM_TARDE
PONTOS_PERDA_TURNO_SEM_LANCAMENTO  = 1.5   # por turno sem visita registrada (que não é chuva/reunião/férias)
# Só no método novo (Outubro/2026 em diante): dia em que os DOIS turnos ficaram
# sem lançamento perde isto A MAIS, além dos 2 turnos (1,5 + 1,5 + 1,0 = 4,0 no dia).
PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO = 1.0
PONTOS_PERDA_VISITA_RAPIDA         = 0.2   # por visita < TEMPO_MIN_VISITA_MIN
PONTOS_PERDA_VISITA_LONGA          = 0     # por visita > TEMPO_MAX_VISITA_MIN (desligado por padrão)
PONTOS_PERDA_VISITA_DUPLICADA      = 0.3   # por visita duplicada
PONTOS_PERDA_SEQUENCIA_SUSPEITA    = 1     # por visita envolvida em sequência suspeita (lançamento em lote)
PONTOS_PERDA_VISITA_NEGATIVA       = 0     # por visita com duração negativa (desligado — normalmente é bug do sistema, não culpa do agente)
PONTOS_PERDA_FORA_EXPEDIENTE       = 0.5   # por visita fora do expediente oficial / fim de semana
PONTOS_PERDA_VISITA_ALMOCO         = 0     # visita no almoço NÃO desconta ponto (só aparece como informação nos alertas)
PONTOS_PERDA_DIA_SEM_META          = 0.5   # por dia trabalhado que não bateu a meta diária de visitas

# --- GANHOS (pontos ganhos por ocorrência ou bônus único no período) ---
PONTOS_GANHO_DIA_COM_META          = 1     # por dia que bateu a meta diária de visitas
PONTOS_GANHO_SEM_VISITA_RAPIDA     = 5     # bônus único: ZERO visitas rápidas no período inteiro
PONTOS_GANHO_SEM_AUSENCIA          = 5     # bônus único: ZERO turnos sem lançamento no período inteiro
PONTOS_GANHO_PONTUALIDADE_PERFEITA = 3     # bônus único: ZERO violações de horário (início/fim) no período

# Faixas de classificação da pontuação final
NOTA_FAIXA_EXCELENTE = 90   # >= 90        -> 🟢 EXCELENTE
NOTA_FAIXA_BOM        = 75  # 75 a 89,9    -> 🟡 BOM
NOTA_FAIXA_ATENCAO    = 60  # 60 a 74,9    -> 🟠 ATENÇÃO
