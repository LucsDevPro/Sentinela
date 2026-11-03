# Mapa do código (gerado por `scripts/gerar_mapa.py` — não edite à mão)

Formato: `L<linha> função(args) — resumo`. Constantes ficam no fim de cada arquivo (`NOME@linha`).
Use `grep -n "def nome" arquivo` ou `sed -n 'A,Bp'` pra ler só o trecho.

## scripts/aplicar_decisao.py (283 linhas)

- L53 `_ler(caminho, padrao)`
- L60 `_gravar(caminho, dados)`
- L66 `_datas(dec)`
- L77 `_entrada_cronograma(dec, nomes)` — Valida e monta a entrada do cronograma. Devolve (entrada, erro).
- L97 `_motivo_ajuste(txt)` — Limpa e valida o motivo do ajuste. Devolve (motivo, erro).
- L110 `_mes_arquivado_da_data(d, arquivados)`
- L118 `_aplicar_ajuste(dec, nomes, caminho_ajustes, quem, remov)`
- L154 `_aplicar_parada(dec, nomes, caminho_cron, quem, remover)`
- L197 `aplicar(dec, caminho_cron, caminho_nomes, caminh)`

Constantes: CAMINHO_CRONOGRAMA@32, CAMINHO_NOMES@33, CAMINHO_DETECCOES@34, TIPOS_CRONOGRAMA@36, TURNOS@42, LIMITE_DIAS_CRONOGRAMA@43, CAMINHO_AJUSTES@44, LIMITE_AJUSTE_PONTOS@45, PARADAS@46, LIMITE_DIAS_PARADA@48, _PROIBIDO_NO_MOTIVO@50

## scripts/coletar_evisita.py (73 linhas)

- L58 `class _Fachada` — Atribuir `C.X = valor` também atualiza X em cada módulo do pacote que o possu…

Constantes: _MODULOS@50

## scripts/fechar_mes.py (195 linhas)

- L28 `_ce()`
- L33 `_ler(caminho, padrao)`
- L41 `_gravar(caminho, dados)`
- L47 `_faixa(mes)`
- L55 `_intervalo_datas(ini, fim)`
- L60 `checar(mes, hoje, pasta_semanas, arquivados)` — Checklist do mês. Cada item: {id, ok (True/False/None=confirmado pelo Worker)…
- L114 `_backup(arquivo, sufixo)`
- L124 `fechar(mes, regenerar, hoje, pasta_semanas)` — Devolve (ok, mensagem).
- L155 `reabrir(mes, confirmacao, regenerar)`

Constantes: PASTA_HISTORICO@23, PASTA_BACKUP@24, CAMINHO_DETECCOES@25

## scripts/generate_dashboard.py (1403 linhas)

- L50 `carregar_outras_atividades()` — Lê data/outras_atividades.json (equipes/atividades fora do e-Visita,
- L102 `resolver_home_xlsx()`
- L131 `sem_bloqueio(df)`
- L136 `somente_bloqueio(df)`
- L143 `br(v, decimals)` — Formata número no padrão pt-BR. Tolerante a valor ausente/indefinido
- L156 `class_key(text)`
- L164 `badge(text)`
- L169 `row_class(text)`
- L173 `rank_class_key(text)` — Classificação do ranking tem 4 faixas (Excelente/Bom/Atenção/Crítico),
- L185 `rank_badge(text)`
- L189 `id_link(v)`
- L197 `parse_custo(v)`
- L206 `parse_br_date(s)`
- L212 `n(v)` — Converte numpy/pandas scalar para tipo nativo Python (uso em dados p/ JSON).
- L289 `cap_first(v)` — Primeira letra maiúscula, sem mexer no resto do texto (não usa
- L301 `ranking_sem_nan(rows)` — Célula vazia da coluna Observação chega como NaN (que o Jinja trataria
- L310 `records(df, colmap)`
- L322 `primeira_tabela(path, aba, subset)` — Lê a primeira tabela de uma aba com segurança: se a aba não existir
- L341 `load_all(path)`
- L431 `compute_all_absent(ausencias, resumo)` — Turnos em que TODA UMA EQUIPE ficou sem nenhuma visita registrada
- L444 `build_cronograma_rows(cronograma, all_absent)` — Junta o cronograma manual (data/cronograma_ausencias.json — chuva,
- L482 `build_kpi_geral(resumo)`
- L498 `_ler_tabela_rapida(path, aba, colunas)` — Primeira tabela de uma aba (modo somente-leitura, bem mais rápido que carregar
- L521 `_num(v)`
- L529 `_ler_presenca(path)` — {agente: (dias_trabalhados, dias_esperados)} da aba Ranking. Nos períodos
- L542 `_meses_historico()` — [(label, caminho)] dos meses fechados, do mais antigo pro mais recente.
- L560 `_presenca_da_pagina()` — Presença da página que está sendo gerada. Página de um mês (ou de uma semana):
- L582 `_preparar_custos(d, presenca)` — Acrescenta ao DataFrame (já com _hu/_ht/_hs/_dias/_vd) a presença e o custo r…
- L610 `_custos_base(resumo)`
- L625 `adicionar_custo_real(resumo)` — Põe a coluna CustoReal no resumo (usada pelo gráfico de custos).
- L636 `_custo_ritmo_agregado(d)` — Folha ÷ horas úteis do mês de todos juntos (só dias trabalhados). A média
- L644 `_custo_real_agregado(d)`
- L649 `_custo_visita_agregado(d)`
- L654 `build_kpi_custos(resumo)`
- L680 `_faixa_custo(v)`
- L686 `_faixa_presenca(pct)`
- L690 `build_custos_rows(resumo)` — Linhas da tabela de custos: as colunas da planilha + presença, aproveitamento,
- L721 `build_custos_equipes(resumo)` — Uma linha por equipe, com o mesmo cálculo dos números gerais.
- L740 `build_custos_mensais()` — Custo real da hora útil de cada agente MÊS A MÊS + média dos meses.
- L785 `build_ausencias_agg(aus)`
- L817 `build_team_cards(resumo, teams)`
- L843 `_classe_por_pontos(p)`
- L852 `_ler_ranking_rapido(path)` — Lê só a tabela principal da aba Ranking de uma planilha (modo
- L879 `_sparkline(valores, w, h)` — Mini-gráfico (SVG inline) da pontuação mês a mês, escala fixa 0–100 pra
- L894 `build_media_mensal()`
- L937 `_worker_url()`
- L943 `_mes_contestavel(ctx)` — Mês ("Outubro/2026") ao qual a página se refere, se estiver ABERTO (contestaç…
- L972 `_ids_por_nome()`
- L979 `build_extratos(ranking_rows, detalhe_rows, sem_normaliz)` — Dados do "Extrato por agente" (folha de uma página com a conta da
- L1004 `_periodo_label(periodos)`
- L1014 `build_kpi_ranking(ranking)`
- L1027 `build_chart_data(data)`
- L1080 `build_context(data)`
- L1173 `build_comparacao_semanal(nav, pagina_semana)` — Nota média de cada equipe, semana a semana, dentro do mês (só na página do MÊ…
- L1205 `carregar_periodos()` — Monta a lista de opções do seletor de período no cabeçalho:
- L1255 `carregar_nav_semanas()` — Barra "Semana 1 | Semana 2 | ... | Mês completo" do mês vigente.
- L1316 `enxugar_html(html)` — Reduz o tamanho da página sem mudar o que aparece: o HTML dos templates
- L1328 `main()`

Constantes: ROOT@28, LAZY@29, DIAS_UTEIS_MES_REF@35, META_VISITAS_DIA_REF@36, TETO_VISITA_MIN@37, CUSTO_FAIXA_MEDIO@42, CUSTO_FAIXA_ALTO@43, HORAS_UTEIS_BAIXO@44, HORAS_UTEIS_ALTO@45, CUSTO_GRAFICO_MAX@46, OUTRAS_ATIVIDADES_PATH@47, SCRIPTS_DIR@88, CONFIG_HOME_PATH@98, ACUMULADO_XLSX@99, HOME_XLSX@116, XLSX_PATH@118, OUT_PATH@119, SALARIO_MENSAL@121, EVISITA_URL@122, DIA_ORDER@123, EQUIPE_BLOQUEIO@129, RESUMO_COLS@227, AREA_COLS@241, ALERT_COLS@248, AUSENCIA_COLS@255, PENDENCIA_COLS@259, PE_COLS@263, RESUMO_SEMANAL_COLS@272, RANKING_COLS@273, RANKING_DET_COLS@280, _NAO_PADRONIZAR_TEXTO@299, _PRESENCA_CACHE@557, TEAM_COLORS@815, LABEL_MES_RE@841, _BLOCOS_LITERAIS_RE@1312, _ESPACOS_RE@1314

## scripts/gerar_agentes.py (191 linhas)

- L20 `_chave(nome)`
- L25 `ler_planilha(caminho)` — ({agente: {equipe, pos, trab, esp, turnos_sem, pontos, cls}}, {agente: [(crit…
- L62 `_d(txt)`
- L69 `_faixa_mes(label)` — 'Outubro/2026' -> (1/10/2026, 31/10/2026) ou None.
- L80 `_faixa_semana(mes, periodo)` — ('Outubro/2026', '04/10 a 10/10') -> (4/10/2026, 10/10/2026) ou None.
- L94 `paradas_no_periodo(cron, equipe, faixa)` — Paradas (já públicas no cronograma) que valem para a equipe e encostam no per…
- L113 `_num(x)`
- L120 `gerar(raiz)`
- L182 `main()`

Constantes: ROOT@12, EQUIPE_BLOQUEIO@16, LABEL_MES_RE@17, _MESES_NUM@58

## scripts/gerar_form_atestado.py (126 linhas)

- L9 `rotulo(id_agente, info)`
- L14 `gerar(caminho_nomes, saida)`
- L67 `gerar_ferias(caminho_nomes, saida)`

## scripts/gerar_transparencia.py (216 linhas)

- L21 `n(v, casas)` — Número em pt-BR (vírgula decimal), sem zeros inúteis.
- L27 `hhmm(t)`
- L31 `e(t)`
- L35 `tabela(linhas, cab)`
- L41 `exemplo()` — Agente FICTÍCIO calculado com as mesmas constantes do ranking.
- L64 `_txt_meta()` — "20 visitas" ou, se houver metas por equipe (data/metas_equipes.json), "20 vi…
- L71 `gerar()`

Constantes: ROOT@18

## scripts/icones.py (100 linhas)

- L73 `ico(nome, extra)`
- L77 `sprite(nomes)`
- L83 `_sem_emoji(txt)`
- L87 `_troca(m)`
- L92 `iconizar(html)`

Constantes: ICONES@12, MAPA@56, SO_REMOVER@63, _EMOJIS@65, _RX_EMOJI@66, _RX_BLOCOS@67, _RX_OPTION@68, _RX_TITLE@69, _RX_ATTR@70

## scripts/lancar_atestado.py (73 linhas)

- L14 `_data(txt)`
- L20 `parse_corpo(corpo)` — {'### Título': 'valor'} do formato que o GitHub gera para issue forms.
- L31 `montar_registro(corpo, nomes)`
- L50 `lancar(corpo, caminho, caminho_nomes)`

Constantes: CAMINHO@11, NOMES@12

## scripts/lancar_ausencia.py (159 linhas)

- L28 `_d(txt)`
- L32 `_f(d)`
- L36 `_dias_uteis(ini, fim)`
- L44 `_entrada(base, id_agente, ini, fim, status, motiv)`
- L56 `parse_ferias(corpo, nomes)`
- L82 `aplicar_ferias(lista, req, info_agente, quem)` — Altera `lista` (deteccoes) in-place. Devolve a mensagem de resultado.
- L131 `processar(corpo, labels, caminho_cron, caminho_nom)`

Constantes: CAMINHO_DETECCOES@22, LIMITE_FERIAS_DIAS@23, ACAO_DEFINIR@24, ACAO_CANCELAR@25

## scripts/meses_arquivados.py (30 linhas)

- L14 `carregar(caminho)` — [(semana_ini, semana_fim, "Mês/Ano"), ...] ordenado.
- L27 `gravar(lista, caminho)`

Constantes: CAMINHO@7, EMBUTIDOS@8

## scripts/publicar_sugestoes.py (155 linhas)

- L23 `_d(txt)`
- L27 `_planilhas_abertas()`
- L51 `ler_ausencias(arquivos)` — [(id_agente, nome, equipe, date, turno)] das abas 'Ausências'.
- L70 `_proximo_util(d)`
- L77 `montar_sugestoes(linhas)` — Agrupa dias úteis consecutivos de cada agente em períodos sugeridos.
- L99 `_item(id_ag, a, grupo)`
- L117 `montar_checklist()` — Checklist do mês aberto mais antigo (só contagens, nada sensível). None se fa…
- L131 `publicar(itens, url, token, checklist)`

Constantes: CONFIG_HOME@18, EQUIPES_SOB_DEMANDA@20

## scripts/semanas_evisita.py (145 linhas)

- L56 `_offset(ano)`
- L67 `semana_para_html(semana_ano, ano)` — Semana do Ano -> HTML ID (para montar a URL de consulta).
- L72 `html_para_semana(html_id, ano)` — HTML ID -> Semana do Ano (para exibir ao usuário).
- L77 `data_inicio_semana_html(html_id)` — Data (domingo) em que a semana daquele HTML ID começa.
- L82 `data_fim_semana_html(html_id)` — Data (sábado) em que a semana daquele HTML ID termina.
- L87 `html_id_da_data(dia)` — Dado um dia qualquer, devolve o HTML ID da semana do site que contém
- L93 `semana_atual_html(hoje)` — HTML ID da semana do site que contém hoje (ou a data passada).
- L98 `ano_da_semana_html(html_id)` — Ano civil predominante da semana (baseado na data de início).
- L103 `rotulo_semana_html(html_id)` — Rótulo amigável pra exibir uma semana ao usuário, ex.:
- L113 `nome_periodo(html_id_inicio, html_id_fim)` — Rótulo amigável pro seletor de período do dashboard: nome do mês em
- L132 `mes_da_semana_html(html_id)` — (ano, mês) predominante de uma semana — usado para agrupar semanas em

Constantes: OFFSETS_VALIDADOS@42, ANCORA_DATA@49, ANCORA_HTML_ID@50, MESES_PT@52

## scripts/validar_ciclos.py (81 linhas)

- L32 `conferir(hoje)` — Devolve (erros, avisos) — listas de mensagens.
- L51 `main()`

Constantes: SEMANAS_A_FRENTE_AVISO@29

## scripts/validar_json.py (96 linhas)

- L33 `validar_ajustes(dados)` — data/ajustes_ranking.json: lista de {"id_agente", "data" (dd/mm/aaaa),
- L53 `validar_sem_abono(dados)` — data/agentes_sem_abono.json: {"2951": {"desde": "dd/mm/aaaa" (opcional), "mot…
- L72 `validar(arquivos)`

Constantes: ARQUIVOS_CRITICOS@20

## scripts/xlsx_scan.py (50 linhas)

- L4 `scan_tables(ws, max_col)`
- L33 `tables_to_dfs(tables)`
- L45 `get_tables(path, sheet_name)`
- L49 `get_table(path, sheet_name, index)`

## scripts/coleta/abas.py (295 linhas)

- L17 `_formatar_campos_resumo(resumo_dict)` — Formata os campos calculados de um dicionário 'resumo' (vindo de
- L42 `_preparar_resumo(res)`
- L53 `_preparar_area(df_ag, res)`
- L69 `_preparar_duplicadas(df_total)` — Monta a lista de visitas duplicadas com endereço completo, para facilitar
- L112 `_preparar_suspeitas(df_total)` — Monta a lista de visitas marcadas como 'sequência suspeita' (chegadas no
- L152 `_preparar_negativas(df_total)` — Monta a lista de visitas com duração NEGATIVA (data de saída registrada
- L186 `_preparar_acima_teto_media(df_total)` — Monta a lista de visitas com duração acima de TETO_DURACAO_MEDIA_MIN
- L220 `_motivo_fora_expediente(row)`
- L234 `_preparar_fora_expediente(df_total)` — Monta a lista de visitas registradas fora do horário oficial de serviço
- L270 `_preparar_almoco(df_total)` — Lista apenas as visitas registradas no horário de almoço (11h15-12h45, com to…

## scripts/coleta/ausencias_ranking.py (574 linhas)

- L47 `_primeira_visita_historica(pasta)` — {id_agente: date da PRIMEIRA visita em TODO o cache de semanas}.
- L100 `_hoje_local()`
- L110 `_preparar_ausencias(df_total, resultados, lista_cronograma, )` — Para cada agente, dia útil e turno (Manhã 7h-11h / Tarde 13h-17h) dentro
- L245 `_preparar_cronograma(resultados, data_min, data_max, lista_cr)` — Lista, de forma unificada e ordenada por data, todo o cronograma de
- L319 `_preparar_pendencias_resumo(resultados)` — Resumo de pendência por agente (abertos/fechados/recusados/total/% pendência),
- L363 `_observacao_ranking(res, qtd_ausencias, dias_periodo, alvo_e)` — Texto da coluna Observação do ranking: avisa quando o agente parece ter
- L390 `_carregar_ajustes_ranking(caminho)` — Ajustes MANUAIS de pontuação, lançados pelo gestor em
- L423 `_preparar_ranking(resultados, regs_ausencias, data_max, li)` — Calcula a pontuação de cada agente (calcular_pontuacao) e monta:
- L556 `_preparar_recusados_detalhe(resultados)` — Lista individual de todos os imóveis com visita recusada pelo morador.

Constantes: _CACHE_PRIMEIRA_VISITA@44, HOJE_OVERRIDE@98, CAMINHO_AJUSTES_RANKING@388

## scripts/coleta/auxiliares.py (128 linhas)

- L31 `_fmt_hora_min(minutos_desde_meia_noite)` — Formata minutos-desde-meia-noite como 'HHhMM' (ex.: 675 -> '11h15').
- L42 `_formatar_nome_proprio(nome)` — Formata nome em Title Case (primeira letra maiúscula de cada palavra),
- L63 `_entrada_vale_pro_turno(entrada, turno)` — Entrada sem "turno" vale o dia inteiro (e só responde a consultas de
- L73 `_meios_turnos_no_dia(id_agente, equipe, dia_date, lista_crono)` — Quantos TURNOS do dia estão justificados por entradas com "turno"
- L80 `_obter_motivo_cronograma(id_agente, equipe, dia_date, lista_crono)` — Verifica se (agente, equipe, dia) bate com alguma entrada da lista de
- L113 `parse_args()` — Permite sobrescrever ano/ciclo/pastas sem editar o código a cada rodada.

Constantes: NOMES_DIA_SEMANA@27, _PREPOSICOES_NOME@39

## scripts/coleta/cache_semanas.py (293 linhas)

- L52 `_caminho_semana(html_id, sufixo, pasta_semanas)`
- L57 `_salvar_df_semana(df, caminho_xlsx)`
- L62 `_carregar_df_semana(caminho_xlsx)` — Recarrega uma planilha de semana cacheada, corrigindo os tipos que o
- L90 `_mesclar_com_cache_anterior(html_id, df_tratamento, pendencia_por_ag)` — Evita que uma recoleta PIOR apague dados bons que já estavam no cache.
- L146 `salvar_cache_semana(html_id, df_tratamento, pendencia_por_ag)` — Grava em disco tudo que foi coletado para UMA semana: a planilha de
- L169 `coletar_uma_semana(session, html_id, id_ano, id_ciclo)` — Coleta TODOS os agentes (tratamento + Ponto Estratégico, quando
- L276 `_salvar_agentes_nomes(resultados, caminho)` — Atualiza (MERGE — nunca apaga o que já tinha) o mapa ID -> Nome de

Constantes: _COLS_BOOL_SEMANA@42, _COLS_DATETIME_SEMANA@49

## scripts/coleta/calculos.py (626 linhas)

- L69 `calcular_tempos(visitas, nome, id_agente, equipe, semana)` — `semana_html_id`: quando a coleta já é feita semana a semana (o caso
- L172 `_media_horario(series_dt)` — Calcula o horário médio (datetime.time) de uma série de timestamps.
- L189 `_maior_sequencia_consecutiva(pares_suspeitos)` — Recebe a lista de pares (visita[i] vs visita[i-1]) marcados como suspeitos
- L202 `_fmt_hhmm_tupla(t)` — Formata tupla (hora, minuto) como 'HHhMM' (ex.: (8, 30) -> '08h30').
- L207 `_avaliar_pontualidade_diaria(df)` — Para cada dia trabalhado, verifica se o início/fim de cada turno
- L248 `_classificar_pontuacao(pontos)`
- L258 `br_num(v)` — Número em texto pt-BR sem zeros inúteis (3 → '3', 2.5 → '2,5').
- L263 `calcular_pontuacao(res, qtd_ausencias, alvo_dias_mes, norma)` — Calcula a pontuação final de um agente a partir de PONTOS_INICIAIS,
- L446 `_horas_trabalhadas_diarias(df)` — Para cada dia trabalhado, calcula:
- L497 `resumo_agente(df)`
- L579 `resumo_por_area(df, fechados_por_area, recusados_por_are)`
- L615 `_classificar(pct_rapidas)` — Classificação baseada no % DE VISITAS RÁPIDAS (< TEMPO_MIN_VISITA_MIN):

## scripts/coleta/colunas.py (206 linhas)


Constantes: COLS_RESUMO@12, COLS_RANKING@44, COLS_RANKING_DETALHE@56, COLS_PONTO_ESTRATEGICO@67, COLS_AREA@72, COLS_DUPLICADAS@89, COLS_SUSPEITAS@102, COLS_NEGATIVAS@116, COLS_ACIMA_TETO_MEDIA@130, COLS_FORA_EXPEDIENTE@143, COLS_ALMOCO@157, COLS_AUSENCIAS@169, COLS_CRONOGRAMA@179, COLS_PENDENCIAS_RESUMO@186, COLS_RECUSADOS_DETALHE@196

## scripts/coleta/consolidacao.py (177 linhas)

- L19 `_montar_df_total_e_resultados(htmls)` — Carrega o cache de cada semana em `htmls` e monta df_total + resultados
- L95 `rodar_deteccao_completa(pasta_semanas)` — Roda a detecção de possíveis férias/paralisação coletiva em cima do
- L111 `consolidar_semanas(htmls, pasta_saida, lista_cronograma)` — Carrega o cache de cada semana em `htmls`, junta tudo e recalcula os

## scripts/coleta/deteccao.py (768 linhas)

- L132 `_feriados_em_vigor()` — Feriados de FERIADOS_NACIONAIS que valem na contagem (>= FERIADOS_VALEM_A_PAR…
- L144 `_dias_uteis_no_intervalo(data_min, data_max, feriados)` — Lista, em ordem, todo dia ÚTIL (seg-sex, fora feriados) entre
- L156 `_dias_uteis_do_mes_civil(data_ref, feriados)` — Lista (não só a contagem) dos dias úteis do MÊS CIVIL INTEIRO (dia 1
- L169 `_dias_uteis_alvo_periodo(data_min, data_max, feriados)` — Devolve a lista de dias úteis que serve de ALVO ("1 mês de
- L206 `_dias_uteis_mes_civil(data_ref, feriados)` — Nº de dias úteis do MÊS CIVIL INTEIRO (dia 1 ao último dia) que contém
- L216 `_dias_paralisacao_coletiva_no_mes(id_agente, equipe, dias_do_mes, lista_cr)` — Quantos dias, dentre `dias_do_mes` (dias úteis do mês civil), foram
- L234 `_runs_consecutivos_uteis(dias_uteis, faltando_set)` — dias_uteis: lista ordenada de dias úteis do período. faltando_set:
- L253 `detectar_ausencias_e_paralisacoes(df_total, resultados)` — Ponto de entrada da detecção — roda em cima do df_total/resultados já
- L283 `_dividir_em_ocorrencias(ini, fim, limite_dias_corridos)` — Quebra [ini, fim] (datas) em pedaços de no máximo `limite_dias_corridos`
- L297 `_periodos_se_sobrepoem(a_ini, a_fim, b_ini, b_fim)` — True se [a_ini,a_fim] e [b_ini,b_fim] têm pelo menos 1 dia em comum —
- L306 `_detectar_ferias_individuais(df_total, resultados, data_max, equipes_)` — ETAPA 1 — Férias/Atestado, por agente (ver regras completas no
- L390 `_detectar_chuva_coletiva(df_total, resultados, data_max, equipes_)` — ETAPA 2 — Chuva, por equipe, dia a dia, só entre os agentes ATIVOS
- L441 `_periodos_se_tocam(ini1, fim1, ini2, fim2, tolerancia_dias)` — True se dois períodos [ini1,fim1] e [ini2,fim2] (objetos date) se
- L459 `atualizar_deteccoes_pendentes(eventos_detectados, caminho)` — Funde os eventos detectados agora com o que já existia no arquivo,
- L692 `_cronograma_efetivo(deteccoes)` — CRONOGRAMA_AUSENCIAS + as detecções com status "confirmada" (as
- L737 `_carregar_agentes_sem_abono(caminho)` — {id_agente: date_desde ou None}. Agentes listados NÃO ganham abono
- L764 `_agente_sem_abono_em(id_agente, dia, cfg)`

Constantes: LIMITE_DIAS_UTEIS_FERIAS@63, LIMITE_DIAS_CORRIDOS_OCORRENCIA@68, TOLERANCIA_DIAS_MESMO_EVENTO@81, EQUIPES_SEM_DETECCAO_AUTOMATICA@94, FERIADOS_NACIONAIS@101, FERIADOS_VALEM_A_PARTIR_DE@130, _FERIADOS_PADRAO@139, CATEGORIAS_PARALISACAO_COLETIVA@141, CAMINHO_AGENTES_SEM_ABONO@734

## scripts/coleta/estilo_excel.py (224 linhas)

- L21 `_estilizar(ws, linha_cab, cor_cab, titulo, ultima_l)`
- L62 `_adicionar_legenda(ws, linha_inicio)` — Adiciona bloco de legenda explicando a classificação por % de visitas rápidas…
- L205 `_escrever(ws, linha, registros, colunas)`

## scripts/coleta/execucao.py (175 linhas)

- L25 `coletar_semanas_blindado(semanas, id_ano, id_ciclo, abrir, coleta)` — Coleta várias semanas SEM que uma falha derrube as demais:
- L72 `_resumo_github(semanas, resumo_integridade, extras)` — Escreve o resultado da coleta no resumo da execução do GitHub Actions
- L111 `main()`

## scripts/coleta/historico.py (220 linhas)

- L32 `atualizar_historico_do_cache(pasta_semanas, pasta_historico, pasta_sa)` — Reconstrói as entradas AUTOMÁTICAS de data/historico/ a partir do cache

## scripts/coleta/parametros.py (584 linhas)

- L141 `_grupo_mes_oficial(html_id)` — Nome do mês oficial (tabela acima) pra essa semana, ou None se a
- L151 `_faixa_mes_oficial(nome)` — (semana_inicio, semana_fim) oficiais de um mês de MESES_OFICIAIS.
- L168 `semanas_ja_coletadas(pasta_semanas)` — HTML IDs de semanas que já têm cache salvo em disco, em ordem
- L182 `decidir_semanas_a_coletar(hoje, pasta_semanas)` — Decide quais semanas (HTML IDs) buscar nesta execução:
- L278 `ciclo_para_semana(semana, ciclos)` — Acha o id_ciclo pra uma semana específica, numa tabela de ciclos
- L306 `ciclo_tratamento_configurado(html_id)` — id_ciclo de Tratamento cadastrado EXPLICITAMENTE em CICLOS_TRATAMENTO
- L314 `ciclo_tratamento_para_semana(html_id, id_ciclo_padrao)` — Como ciclo_para_semana(), mas com fallback pro id_ciclo padrão em vez
- L334 `_ciclos_esperados(html_id)`
- L338 `_ler_ciclos_coletados(pasta_semanas)`
- L349 `_registrar_ciclos_coletados(html_id, pasta_semanas)`
- L398 `_carregar_metas_equipes(caminho)` — Meta diária de visitas POR EQUIPE (opcional): {"Equipe 1": 25}. Equipe que não
- L423 `meta_da_equipe(equipe)`
- L506 `_cache_nomes_agentes(caminho)` — Cache persistente ID -> {nome, equipe}, mantido em memória durante a
- L536 `_atualizar_cache_nomes_agentes(id_agente, nome, equipe, caminho)` — Grava (merge, nunca sobrescreve o arquivo inteiro) um nome de
- L555 `_motivo_neutro(motivo)` — Repositório público: só rótulos neutros. "Atestado" (entradas antigas)
- L567 `_carregar_cronograma_ausencias(caminho)`

Constantes: CPF@27, SENHA@28, ID_MUNICIPIO@38, ID_ATIVIDADE@39, ID_ANO@40, ID_CICLO@41, ID_TIPO_VISITA@42, ANCORA_DATA@47, ANCORA_ID@48, MESES_PT@49, PRIMEIRA_SEMANA_COLETA@59, GERAR_PAGINAS_SEMANAIS@69, PRIMEIRA_SEMANA_DETALHE_SEMANAL@70, PASTA_ARQUIVO_SEMANAL@71, MESES_OFICIAIS@88, PRIMEIRA_SEMANA_CICLO_EXPLICITO@102, PRIMEIRA_SEMANA_VISAO_SEMANAL@106, MESES_ARQUIVADOS@131, MESES_ADICIONAIS@138, PASTA_SEMANAS@165, ID_PENDENCIA_ABERTOS@233, ID_PENDENCIA_FECHADOS@234, ID_PENDENCIA_RECUSADOS@235, AGENTES_POR_EQUIPE@238, AGENTES_PONTO_ESTRATEGICO@252, ID_ATIVIDADE_PONTO_ESTRATEGICO@255, CICLOS_PONTO_ESTRATEGICO@270, CICLOS_TRATAMENTO@299, NOME_ARQUIVO_CICLOS_COLETADOS@332, MAX_WORKERS@365, DELAY_ENTRE_PAGINAS@366, TIMEOUT_CONEXAO@367, TIMEOUT_LEITURA@368, TIMEOUT_HTTP@369, BACKOFF_BASE_S@370, BACKOFF_MAX_S@371, BACKOFF_JITTER_S@372, PAGE_LOAD_TIMEOUT_S@373, ESPERA_ELEMENTO_S@374, TENTATIVAS_LOGIN@375, TENTATIVAS_SAUDE@376, MAX_SEMANAS_FALHAS_SEGUIDAS@377, ORCAMENTO_COLETA_MIN@378, TENTATIVAS_POR_PAGINA@379, TEMPO_MIN_VISITA_MIN@382, TEMPO_MAX_VISITA_MIN@383, TETO_DURACAO_MEDIA_MIN@394, META_VISITAS_DIA@395, METAS_EQUIPES@420, PCT_RAPIDAS_OK_ATE@427, PCT_RAPIDAS_ATENCAO_ATE@428, LIMIAR_SEQUENCIA_SUSPEITA_SEG@437, HORA_ALMOCO_INICIO_MIN@444, HORA_ALMOCO_FIM_MIN@445, HORA_EXPEDIENTE_MANHA_INICIO@450, HORA_EXPEDIENTE_MANHA_FIM@451, HORA_EXPEDIENTE_TARDE_INICIO@452, HORA_EXPEDIENTE_TARDE_FIM@453, SALARIO_MINIMO@456, SALARIO_AGENTE@457, DIAS_UTEIS_MES@458, PASTA_SAIDA@461, ARQUIVO_CONSOLIDADO@462, URL_LOGIN@465, URL_VISITAS@466, MOTIVOS_CRONOGRAMA@494, CAMINHO_CACHE_NOMES_AGENTES@502, CRONOGRAMA_AUSENCIAS@584

## scripts/coleta/pontos.py (136 linhas)

- L93 `_ranking_sem_normalizacao(data_min, data_max)` — True se o período que começa em `data_min` usa o ranking novo (sem

Constantes: COLETAR_FECHADOS_RECUSADOS@15, PONTOS_INICIAIS@23, NOTA_MINIMA@24, NOTA_MAXIMA@25, TETO_FATOR_NORMALIZACAO@29, RANKING_SEM_NORMALIZACAO_A_PARTIR_DE@38, BONUS_MIN_FRACAO_DIAS_ESPERADOS@44, PRESENCA_MINIMA_FRACAO@52, LIMITE_AGENTES_EVENTO_TURNO@72, CONFIRMAR_FERIAS_AUTOMATICAMENTE@79, CONFIRMAR_CHUVA_AUTOMATICAMENTE@80, EVENTO_COLETIVO_A_PARTIR_DE@85, CLASSIF_TURNO_SEM_LANCAMENTO@86, CLASSIF_POSSIVEL_EVENTO@87, AVISO_AFASTAMENTO_FRACAO_MAX@89, AVISO_AFASTAMENTO_TURNOS_MIN@90, AVISO_AFASTAMENTO_PERIODO_MAX_DIAS@91, HORA_LIMITE_INICIO_MANHA@104, HORA_LIMITE_FIM_MANHA@105, HORA_LIMITE_INICIO_TARDE@106, HORA_LIMITE_FIM_TARDE@107, PONTOS_PERDA_INICIO_MANHA_ATRASADO@110, PONTOS_PERDA_FIM_MANHA_ANTECIPADO@111, PONTOS_PERDA_INICIO_TARDE_ATRASADO@112, PONTOS_PERDA_FIM_TARDE_ANTECIPADO@113, PONTOS_PERDA_TURNO_SEM_LANCAMENTO@114, PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO@117, PONTOS_PERDA_VISITA_RAPIDA@118, PONTOS_PERDA_VISITA_LONGA@119, PONTOS_PERDA_VISITA_DUPLICADA@120, PONTOS_PERDA_SEQUENCIA_SUSPEITA@121, PONTOS_PERDA_VISITA_NEGATIVA@122, PONTOS_PERDA_FORA_EXPEDIENTE@123, PONTOS_PERDA_VISITA_ALMOCO@124, PONTOS_PERDA_DIA_SEM_META@125, PONTOS_GANHO_DIA_COM_META@128, PONTOS_GANHO_SEM_VISITA_RAPIDA@129, PONTOS_GANHO_SEM_AUSENCIA@130, PONTOS_GANHO_PONTUALIDADE_PERFEITA@131, NOTA_FAIXA_EXCELENTE@134, NOTA_FAIXA_BOM@135, NOTA_FAIXA_ATENCAO@136

## scripts/coleta/processamento.py (154 linhas)

- L26 `processar(equipe, id_ag, session_base, cfg)`
- L105 `processar_ponto_estrategico(id_ag, session_base, cfg_pe)` — Coleta as visitas de Ponto Estratégico de um agente (URL/id_atividade

## scripts/coleta/saida_excel.py (337 linhas)

- L65 `_slugify_nome_arquivo(nome)` — Converte o título de uma aba (com espaços/acentos) num nome de arquivo seguro.
- L72 `exportar_todas_abas_csv(wb, pasta_saida)` — Exporta CADA aba do workbook como um arquivo .csv separado (com os
- L98 `salvar_excel_consolidado(resultados, df_total, pasta_saida, seman)`
- L323 `_preparar_ponto_estrategico(semanas_todos_agentes)`

## scripts/coleta/sessao.py (416 linhas)

- L52 `_espera_backoff(tentativa)` — Espera exponencial com jitter antes da próxima tentativa (tentativa = 1, 2, 3…
- L59 `criar_driver()`
- L74 `fazer_login(driver)`
- L87 `_aplicar_retry(session)`
- L96 `criar_session(driver)`
- L103 `abrir_sessao(tentativas)` — Abre o navegador, faz login e devolve uma requests.Session pronta.
- L128 `evisita_no_ar(tentativas)` — Verificação de saúde ANTES de coletar: a página de login responde?
- L145 `clonar_session(base)`
- L157 `class SessaoExpiradaError` — Levantada quando a página retornada é a tela de login (sessão caiu).
- L161 `montar_url(id_agente, pagina, cfg, id_pendencia, id)`
- L177 `obter_total_paginas(soup)`
- L192 `_extrair_nome_agente_da_pagina(soup, id_agente)` — (Fallback) Extrai o nome do agente a partir do <select> de filtro presente
- L218 `_obter_nome_agente_via_api(session, id_agente)` — Busca o nome do agente diretamente no endpoint 'getedit' usado pelo
- L275 `extrair_nome_agente(session, soup, id_agente)` — Tenta obter o nome do agente, nessa ordem:
- L314 `extrair_visitas(soup)`
- L344 `_parece_tela_login(soup)`
- L348 `baixar_soup(session, url)`
- L357 `baixar_soup_com_retry(session, url, descricao, tentativas)` — Camada de retry em nível de APLICAÇÃO sobre baixar_soup — além do retry
- L381 `coletar_visitas_agente(session, id_agente, cfg, id_pendencia, o)`
