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

## scripts/generate_dashboard.py (1496 linhas)

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
- L485 `agrupar_cronograma_por_dia(rows)` — Agrupa as linhas de build_cronograma_rows por DIA (ou por período, quando o l…
- L521 `build_kpi_geral(resumo)`
- L537 `_ler_tabela_rapida(path, aba, colunas)` — Primeira tabela de uma aba (modo somente-leitura, bem mais rápido que carregar
- L560 `_num(v)`
- L568 `_ler_presenca(path)` — {agente: (dias_trabalhados, dias_esperados)} da aba Ranking. Nos períodos
- L581 `_meses_historico()` — [(label, caminho)] dos meses fechados, do mais antigo pro mais recente.
- L599 `_presenca_da_pagina()` — Presença da página que está sendo gerada. Página de um mês (ou de uma semana):
- L621 `_preparar_custos(d, presenca)` — Acrescenta ao DataFrame (já com _hu/_ht/_hs/_dias/_vd) a presença e o custo r…
- L649 `_custos_base(resumo)`
- L664 `adicionar_custo_real(resumo)` — Põe a coluna CustoReal no resumo (usada pelo gráfico de custos).
- L675 `_custo_ritmo_agregado(d)` — Folha ÷ horas úteis do mês de todos juntos (só dias trabalhados). A média
- L683 `_custo_real_agregado(d)`
- L688 `_custo_visita_agregado(d)`
- L693 `build_kpi_custos(resumo)`
- L719 `_faixa_custo(v)`
- L725 `_faixa_presenca(pct)`
- L729 `build_custos_rows(resumo)` — Linhas da tabela de custos: as colunas da planilha + presença, aproveitamento,
- L760 `build_custos_equipes(resumo)` — Uma linha por equipe, com o mesmo cálculo dos números gerais.
- L779 `build_custos_mensais()` — Custo real da hora útil de cada agente MÊS A MÊS + média dos meses.
- L824 `build_ausencias_agg(aus)`
- L856 `build_team_cards(resumo, teams)`
- L882 `_classe_por_pontos(p)`
- L891 `_ler_ranking_rapido(path)` — Lê só a tabela principal da aba Ranking de uma planilha (modo
- L918 `_sparkline(valores, w, h)` — Mini-gráfico (SVG inline) da pontuação mês a mês, escala fixa 0–100 pra
- L933 `build_media_mensal()`
- L976 `_worker_url()`
- L982 `_mes_contestavel(ctx)` — Mês ("Outubro/2026") ao qual a página se refere, se estiver ABERTO (contestaç…
- L1011 `_ids_por_nome()`
- L1018 `build_extratos(ranking_rows, detalhe_rows, sem_normaliz)` — Dados do "Extrato por agente" (folha de uma página com a conta da
- L1043 `_periodo_label(periodos)`
- L1053 `build_kpi_ranking(ranking)`
- L1066 `build_chart_data(data)`
- L1119 `build_context(data)`
- L1213 `build_comparacao_semanal(nav, pagina_semana)` — Nota média de cada equipe, semana a semana, dentro do mês (só na página do MÊ…
- L1269 `carregar_periodos()` — Monta a lista de opções do seletor de período no cabeçalho:
- L1319 `carregar_nav_semanas()` — Barra "Semana 1 | Semana 2 | ... | Mês completo" do mês vigente.
- L1380 `enxugar_html(html)` — Reduz o tamanho da página sem mudar o que aparece: o HTML dos templates
- L1392 `periodo_em_andamento(semana_fim_html, hoje)` — Sexta-feira em que o período termina SE ele ainda está em andamento (hoje <= …
- L1401 `_selo_periodo(ctx)` — 'dd/mm' da sexta final quando a página é de um MÊS ainda em andamento; senão …
- L1415 `main()`

Constantes: ROOT@28, LAZY@29, DIAS_UTEIS_MES_REF@35, META_VISITAS_DIA_REF@36, TETO_VISITA_MIN@37, CUSTO_FAIXA_MEDIO@42, CUSTO_FAIXA_ALTO@43, HORAS_UTEIS_BAIXO@44, HORAS_UTEIS_ALTO@45, CUSTO_GRAFICO_MAX@46, OUTRAS_ATIVIDADES_PATH@47, SCRIPTS_DIR@88, CONFIG_HOME_PATH@98, ACUMULADO_XLSX@99, HOME_XLSX@116, XLSX_PATH@118, OUT_PATH@119, SALARIO_MENSAL@121, EVISITA_URL@122, DIA_ORDER@123, EQUIPE_BLOQUEIO@129, RESUMO_COLS@227, AREA_COLS@241, ALERT_COLS@248, AUSENCIA_COLS@255, PENDENCIA_COLS@259, PE_COLS@263, RESUMO_SEMANAL_COLS@272, RANKING_COLS@273, RANKING_DET_COLS@280, _NAO_PADRONIZAR_TEXTO@299, _DIAS_CURTOS@482, _PRESENCA_CACHE@596, TEAM_COLORS@854, LABEL_MES_RE@880, _BLOCOS_LITERAIS_RE@1376, _ESPACOS_RE@1378

## scripts/gerar_agentes.py (239 linhas)

- L20 `_chave(nome)`
- L25 `ler_planilha(caminho)` — ({agente: {equipe, pos, trab, esp, turnos_sem, pontos, cls}}, {agente: [(crit…
- L58 `ler_panorama(caminho)` — Totais do mês para a tela de reunião, somando os agentes das equipes avaliada…
- L103 `_d(txt)`
- L110 `_faixa_mes(label)` — 'Outubro/2026' -> (1/10/2026, 31/10/2026) ou None.
- L121 `_faixa_semana(mes, periodo)` — ('Outubro/2026', '04/10 a 10/10') -> (4/10/2026, 10/10/2026) ou None.
- L135 `paradas_no_periodo(cron, equipe, faixa)` — Paradas (já públicas no cronograma) que valem para a equipe e encostam no per…
- L154 `_num(x)`
- L161 `gerar(raiz)`
- L230 `main()`

Constantes: ROOT@12, EQUIPE_BLOQUEIO@16, LABEL_MES_RE@17, _MESES_NUM@99

## scripts/gerar_form_atestado.py (126 linhas)

- L9 `rotulo(id_agente, info)`
- L14 `gerar(caminho_nomes, saida)`
- L67 `gerar_ferias(caminho_nomes, saida)`

## scripts/gerar_transparencia.py (219 linhas)

- L24 `n(v, casas)` — Número em pt-BR (vírgula decimal), sem zeros inúteis.
- L30 `hhmm(t)`
- L34 `e(t)`
- L38 `tabela(linhas, cab)`
- L44 `exemplo()` — Agente FICTÍCIO calculado com as mesmas constantes do ranking.
- L67 `_txt_meta()` — "20 visitas" ou, se houver metas por equipe (data/metas_equipes.json), "20 vi…
- L74 `corpo_html()` — Conteúdo (HTML) do "Como é calculado", sem moldura de página.
- L188 `_data_recalculo()` — ' em dd/mm/aaaa' da última vez que um mês congelado foi refeito (manifest.jso…
- L198 `fragmento_js()` — assets/como_calcula.js: o HTML do conteúdo, como string JS (o álbum injeta na…
- L203 `gerar()` — transparencia.html: só redireciona para a aba "Como é calculado" do álbum.

Constantes: ROOT@21

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

## scripts/meses_arquivados.py (29 linhas)

- L13 `carregar(caminho)` — [(semana_ini, semana_fim, "Mês/Ano"), ...] ordenado.
- L26 `gravar(lista, caminho)`

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

## scripts/regenerar_mes.py (271 linhas)

- L45 `escolher_alvos(arg, arquivados, oficiais)` — [(semana_ini, semana_fim, "Mês/Ano")] a regenerar.
- L66 `semanas_faltando(alvo, em_cache)` — Semanas (HTML ID) do mês que NÃO estão no cache. Mês só pode ser refeito com …
- L73 `ler_ranking(caminho)` — {agente: (posição, dias trabalhados, dias esperados, turnos sem trabalhar, po…
- L92 `comparar_rankings(antigo, novo)` — Resumo do que mudou entre duas leituras de ler_ranking().
- L109 `tirar_do_manifest(manifest, alvos)` — Manifest sem as entradas (mês e visões semanais) das semanas dos alvos.
- L116 `congelar_no_manifest(manifest, alvos, hoje)` — Marca como congeladas ("manual") as entradas dos alvos, como o 'Fechar mês' f…
- L126 `podar_backups(pasta, stem, manter)` — Apaga os backups `<stem>_antes-da-regeneracao-*.xlsx` mais antigos, deixando …
- L138 `_sha(caminho)`
- L147 `_linha_resumo(nome, r)`
- L155 `main(argv)`

Constantes: AQUI@31, PASTA_SEMANAS@36, PASTA_HISTORICO@37, PASTA_BACKUP@38, BACKUPS_A_MANTER@39

## scripts/regerar_paginas.py (54 linhas)

- L19 `_rodar(args)`
- L28 `main(argv)`

Constantes: RAIZ@16

## scripts/resumo.py (182 linhas)

- L27 `_d(texto)`
- L34 `janela_do_mes(semana_ini, semana_fim)` — (primeiro dia, última sexta-feira) do período formado pelas semanas HTML ini.…
- L40 `filtrar_deteccoes(dets, janela, status, tipo)` — Detecções que tocam a janela (ini, fim), com o status e o tipo pedidos (None …
- L55 `contar_deteccoes(dets, janelas)` — {mes: {(tipo curto, status): n}} — um evento que toca 2 meses entra nos dois.
- L68 `linha_deteccao(e)`
- L79 `_json(caminho, padrao)`
- L87 `_meses()` — [(label, semana_ini, semana_fim, 'congelado'|'aberto')] em ordem cronológica.
- L95 `_arquivo_do_mes(label)`
- L105 `cmd_meses(_a)`
- L111 `cmd_deteccoes(a)`
- L130 `cmd_ranking(a)`
- L151 `cmd_cronograma(a)`
- L159 `cmd_manifest(_a)`
- L165 `main(argv)`

Constantes: AQUI@20, RAIZ@22, TIPOS@24

## scripts/rodar_testes.py (71 linhas)

- L24 `_resumo(saida)`
- L30 `main(argv)`

Constantes: RAIZ@18, TESTES@19, LIMITE_S@21

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

## scripts/versionar_assets.py (76 linhas)

- L22 `hash_arquivo(caminho)`
- L27 `versionar_html(caminho, gravar)`
- L45 `versionar_sw(gravar)`
- L67 `main()`

Constantes: RAIZ@18, REF@19

## scripts/xlsx_scan.py (82 linhas)

- L8 `scan_tables(ws, max_col)`
- L41 `tables_to_dfs(tables)`
- L54 `_abrir(path, mtime_ns, tamanho)`
- L69 `_fechar_planilhas()`
- L76 `get_tables(path, sheet_name)`
- L81 `get_table(path, sheet_name, index)`

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

## scripts/coleta/ausencias_ranking.py (674 linhas)

- L50 `_primeira_visita_historica(pasta)` — {id_agente: date da PRIMEIRA visita em TODO o cache de semanas}.
- L103 `_hoje_local()`
- L113 `_preparar_ausencias(df_total, resultados, lista_cronograma, )` — Para cada agente, dia útil e turno (Manhã 7h-11h / Tarde 13h-17h) dentro
- L279 `_preparar_cronograma(resultados, data_min, data_max, lista_cr)` — Lista, de forma unificada e ordenada por data, todo o cronograma de
- L353 `_preparar_pendencias_resumo(resultados)` — Resumo de pendência por agente (abertos/fechados/recusados/total/% pendência),
- L397 `_observacao_ranking(res, qtd_ausencias, dias_periodo, alvo_e)` — Texto da coluna Observação do ranking: avisa quando o agente parece ter
- L424 `_carregar_ajustes_ranking(caminho)` — Ajustes MANUAIS de pontuação, lançados pelo gestor em
- L468 `_ler_notas_ranking(caminho)` — {nome_agente: pontuação final} da tabela principal da aba Ranking de uma plan…
- L492 `_media_historica_por_agente(data_min, manifest, pasta)` — {nome_agente: média das notas dos meses anteriores ao período que começa em `…
- L519 `_preparar_ranking(resultados, regs_ausencias, data_max, li)` — Calcula a pontuação de cada agente (calcular_pontuacao) e monta:
- L656 `_preparar_recusados_detalhe(resultados)` — Lista individual de todos os imóveis com visita recusada pelo morador.

Constantes: _CACHE_PRIMEIRA_VISITA@47, HOJE_OVERRIDE@101, CAMINHO_AJUSTES_RANKING@422, CAMINHO_MANIFEST_HISTORICO@463, PASTA_HISTORICO@464, _RE_LABEL_MES@465

## scripts/coleta/auxiliares.py (128 linhas)

- L31 `_fmt_hora_min(minutos_desde_meia_noite)` — Formata minutos-desde-meia-noite como 'HHhMM' (ex.: 675 -> '11h15').
- L42 `_formatar_nome_proprio(nome)` — Formata nome em Title Case (primeira letra maiúscula de cada palavra),
- L63 `_entrada_vale_pro_turno(entrada, turno)` — Entrada sem "turno" vale o dia inteiro (e só responde a consultas de
- L73 `_meios_turnos_no_dia(id_agente, equipe, dia_date, lista_crono)` — Quantos TURNOS do dia estão justificados por entradas com "turno"
- L80 `_obter_motivo_cronograma(id_agente, equipe, dia_date, lista_crono)` — Verifica se (agente, equipe, dia) bate com alguma entrada da lista de
- L113 `parse_args()` — Permite sobrescrever ano/ciclo/pastas sem editar o código a cada rodada.

Constantes: NOMES_DIA_SEMANA@27, _PREPOSICOES_NOME@39

## scripts/coleta/cache_semanas.py (326 linhas)

- L53 `_caminho_semana(html_id, sufixo, pasta_semanas)`
- L69 `_ler_aba_visitas(caminho_xlsx)`
- L87 `_salvar_df_semana(df, caminho_xlsx)`
- L95 `_carregar_df_semana(caminho_xlsx)` — Recarrega uma planilha de semana cacheada, corrigindo os tipos que o
- L123 `_mesclar_com_cache_anterior(html_id, df_tratamento, pendencia_por_ag)` — Evita que uma recoleta PIOR apague dados bons que já estavam no cache.
- L179 `salvar_cache_semana(html_id, df_tratamento, pendencia_por_ag)` — Grava em disco tudo que foi coletado para UMA semana: a planilha de
- L202 `coletar_uma_semana(session, html_id, id_ano, id_ciclo)` — Coleta TODOS os agentes (tratamento + Ponto Estratégico, quando
- L309 `_salvar_agentes_nomes(resultados, caminho)` — Atualiza (MERGE — nunca apaga o que já tinha) o mapa ID -> Nome de

Constantes: _COLS_BOOL_SEMANA@43, _COLS_DATETIME_SEMANA@50, _CACHE_LEITURA@64, _CACHE_LEITURA_MAX@65, _LOCK_CACHE@66

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

## scripts/coleta/consolidacao.py (212 linhas)

- L19 `_montar_df_total_e_resultados(htmls)` — Carrega o cache de cada semana em `htmls` e monta df_total + resultados
- L95 `rodar_deteccao_completa(pasta_semanas)` — Roda a detecção de possíveis férias/paralisação coletiva em cima do
- L111 `agentes_do_periodo(htmls)` — Lista (id_agente, nome, equipe) de todo agente com pelo menos uma visita em `…
- L129 `consolidar_semanas(htmls, pasta_saida, lista_cronograma, ag)` — Carrega o cache de cada semana em `htmls`, junta tudo e recalcula os

## scripts/coleta/deteccao.py (771 linhas)

- L133 `_feriados_em_vigor()` — Feriados de FERIADOS_NACIONAIS que valem na contagem (>= FERIADOS_VALEM_A_PAR…
- L145 `_dias_uteis_no_intervalo(data_min, data_max, feriados)` — Lista, em ordem, todo dia ÚTIL (seg-sex, fora feriados) entre
- L157 `_dias_uteis_do_mes_civil(data_ref, feriados)` — Lista (não só a contagem) dos dias úteis do MÊS CIVIL INTEIRO (dia 1
- L170 `_dias_uteis_alvo_periodo(data_min, data_max, feriados)` — Devolve a lista de dias úteis que serve de ALVO ("1 mês de
- L207 `_dias_uteis_mes_civil(data_ref, feriados)` — Nº de dias úteis do MÊS CIVIL INTEIRO (dia 1 ao último dia) que contém
- L217 `_dias_paralisacao_coletiva_no_mes(id_agente, equipe, dias_do_mes, lista_cr)` — Quantos dias, dentre `dias_do_mes` (dias úteis do mês civil), foram
- L235 `_runs_consecutivos_uteis(dias_uteis, faltando_set)` — dias_uteis: lista ordenada de dias úteis do período. faltando_set:
- L254 `detectar_ausencias_e_paralisacoes(df_total, resultados)` — Ponto de entrada da detecção — roda em cima do df_total/resultados já
- L284 `_dividir_em_ocorrencias(ini, fim, limite_dias_corridos)` — Quebra [ini, fim] (datas) em pedaços de no máximo `limite_dias_corridos`
- L298 `_periodos_se_sobrepoem(a_ini, a_fim, b_ini, b_fim)` — True se [a_ini,a_fim] e [b_ini,b_fim] têm pelo menos 1 dia em comum —
- L307 `_detectar_ferias_individuais(df_total, resultados, data_max, equipes_)` — ETAPA 1 — Férias/Atestado, por agente (ver regras completas no
- L391 `_detectar_chuva_coletiva(df_total, resultados, data_max, equipes_)` — ETAPA 2 — Chuva, por equipe, dia a dia, só entre os agentes ATIVOS
- L442 `_periodos_se_tocam(ini1, fim1, ini2, fim2, tolerancia_dias)` — True se dois períodos [ini1,fim1] e [ini2,fim2] (objetos date) se
- L460 `atualizar_deteccoes_pendentes(eventos_detectados, caminho)` — Funde os eventos detectados agora com o que já existia no arquivo,
- L693 `_cronograma_efetivo(deteccoes)` — CRONOGRAMA_AUSENCIAS + as detecções com status "confirmada" (as
- L740 `_carregar_agentes_sem_abono(caminho)` — {id_agente: date_desde ou None}. Agentes listados NÃO ganham abono
- L767 `_agente_sem_abono_em(id_agente, dia, cfg)`

Constantes: LIMITE_DIAS_UTEIS_FERIAS@64, LIMITE_DIAS_CORRIDOS_OCORRENCIA@69, TOLERANCIA_DIAS_MESMO_EVENTO@82, EQUIPES_SEM_DETECCAO_AUTOMATICA@95, FERIADOS_NACIONAIS@102, FERIADOS_VALEM_A_PARTIR_DE@131, _FERIADOS_PADRAO@140, CATEGORIAS_PARALISACAO_COLETIVA@142, CAMINHO_AGENTES_SEM_ABONO@737

## scripts/coleta/estilo_excel.py (224 linhas)

- L21 `_estilizar(ws, linha_cab, cor_cab, titulo, ultima_l)`
- L62 `_adicionar_legenda(ws, linha_inicio)` — Adiciona bloco de legenda explicando a classificação por % de visitas rápidas…
- L205 `_escrever(ws, linha, registros, colunas)`

## scripts/coleta/execucao.py (175 linhas)

- L25 `coletar_semanas_blindado(semanas, id_ano, id_ciclo, abrir, coleta)` — Coleta várias semanas SEM que uma falha derrube as demais:
- L72 `_resumo_github(semanas, resumo_integridade, extras)` — Escreve o resultado da coleta no resumo da execução do GitHub Actions
- L111 `main()`

## scripts/coleta/historico.py (222 linhas)

- L32 `atualizar_historico_do_cache(pasta_semanas, pasta_historico, pasta_sa)` — Reconstrói as entradas AUTOMÁTICAS de data/historico/ a partir do cache

## scripts/coleta/parametros.py (586 linhas)

- L144 `_grupo_mes_oficial(html_id)` — Nome do mês oficial (tabela acima) pra essa semana, ou None se a
- L154 `_faixa_mes_oficial(nome)` — (semana_inicio, semana_fim) oficiais de um mês de MESES_OFICIAIS.
- L171 `semanas_ja_coletadas(pasta_semanas)` — HTML IDs de semanas que já têm cache salvo em disco, em ordem
- L185 `decidir_semanas_a_coletar(hoje, pasta_semanas)` — Decide quais semanas (HTML IDs) buscar nesta execução:
- L281 `ciclo_para_semana(semana, ciclos)` — Acha o id_ciclo pra uma semana específica, numa tabela de ciclos
- L308 `ciclo_tratamento_configurado(html_id)` — id_ciclo de Tratamento cadastrado EXPLICITAMENTE em CICLOS_TRATAMENTO
- L316 `ciclo_tratamento_para_semana(html_id, id_ciclo_padrao)` — Como ciclo_para_semana(), mas com fallback pro id_ciclo padrão em vez
- L336 `_ciclos_esperados(html_id)`
- L340 `_ler_ciclos_coletados(pasta_semanas)`
- L351 `_registrar_ciclos_coletados(html_id, pasta_semanas)`
- L400 `_carregar_metas_equipes(caminho)` — Meta diária de visitas POR EQUIPE (opcional): {"Equipe 1": 25}. Equipe que não
- L425 `meta_da_equipe(equipe)`
- L508 `_cache_nomes_agentes(caminho)` — Cache persistente ID -> {nome, equipe}, mantido em memória durante a
- L538 `_atualizar_cache_nomes_agentes(id_agente, nome, equipe, caminho)` — Grava (merge, nunca sobrescreve o arquivo inteiro) um nome de
- L557 `_motivo_neutro(motivo)` — Repositório público: só rótulos neutros. "Atestado" (entradas antigas)
- L569 `_carregar_cronograma_ausencias(caminho)`

Constantes: CPF@27, SENHA@28, ID_MUNICIPIO@38, ID_ATIVIDADE@39, ID_ANO@40, ID_CICLO@41, ID_TIPO_VISITA@42, ANCORA_DATA@47, ANCORA_ID@48, MESES_PT@49, PRIMEIRA_SEMANA_COLETA@61, GERAR_PAGINAS_SEMANAIS@71, PRIMEIRA_SEMANA_DETALHE_SEMANAL@72, PASTA_ARQUIVO_SEMANAL@73, MESES_OFICIAIS@90, PRIMEIRA_SEMANA_CICLO_EXPLICITO@105, PRIMEIRA_SEMANA_VISAO_SEMANAL@109, MESES_ARQUIVADOS@134, MESES_ADICIONAIS@141, PASTA_SEMANAS@168, ID_PENDENCIA_ABERTOS@236, ID_PENDENCIA_FECHADOS@237, ID_PENDENCIA_RECUSADOS@238, AGENTES_POR_EQUIPE@241, AGENTES_PONTO_ESTRATEGICO@255, ID_ATIVIDADE_PONTO_ESTRATEGICO@258, CICLOS_PONTO_ESTRATEGICO@273, CICLOS_TRATAMENTO@302, NOME_ARQUIVO_CICLOS_COLETADOS@334, MAX_WORKERS@367, DELAY_ENTRE_PAGINAS@368, TIMEOUT_CONEXAO@369, TIMEOUT_LEITURA@370, TIMEOUT_HTTP@371, BACKOFF_BASE_S@372, BACKOFF_MAX_S@373, BACKOFF_JITTER_S@374, PAGE_LOAD_TIMEOUT_S@375, ESPERA_ELEMENTO_S@376, TENTATIVAS_LOGIN@377, TENTATIVAS_SAUDE@378, MAX_SEMANAS_FALHAS_SEGUIDAS@379, ORCAMENTO_COLETA_MIN@380, TENTATIVAS_POR_PAGINA@381, TEMPO_MIN_VISITA_MIN@384, TEMPO_MAX_VISITA_MIN@385, TETO_DURACAO_MEDIA_MIN@396, META_VISITAS_DIA@397, METAS_EQUIPES@422, PCT_RAPIDAS_OK_ATE@429, PCT_RAPIDAS_ATENCAO_ATE@430, LIMIAR_SEQUENCIA_SUSPEITA_SEG@439, HORA_ALMOCO_INICIO_MIN@446, HORA_ALMOCO_FIM_MIN@447, HORA_EXPEDIENTE_MANHA_INICIO@452, HORA_EXPEDIENTE_MANHA_FIM@453, HORA_EXPEDIENTE_TARDE_INICIO@454, HORA_EXPEDIENTE_TARDE_FIM@455, SALARIO_MINIMO@458, SALARIO_AGENTE@459, DIAS_UTEIS_MES@460, PASTA_SAIDA@463, ARQUIVO_CONSOLIDADO@464, URL_LOGIN@467, URL_VISITAS@468, MOTIVOS_CRONOGRAMA@496, CAMINHO_CACHE_NOMES_AGENTES@504, CRONOGRAMA_AUSENCIAS@586

## scripts/coleta/pontos.py (157 linhas)

- L114 `_ranking_sem_normalizacao(data_min, data_max)` — True se o período que começa em `data_min` usa o ranking novo (sem

Constantes: COLETAR_FECHADOS_RECUSADOS@15, PONTOS_INICIAIS@23, NOTA_MINIMA@24, NOTA_MAXIMA@25, TETO_FATOR_NORMALIZACAO@29, RANKING_SEM_NORMALIZACAO_A_PARTIR_DE@40, BONUS_MIN_FRACAO_DIAS_ESPERADOS@46, PRESENCA_MINIMA_FRACAO@54, LIMITE_AGENTES_EVENTO_TURNO@80, CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE@84, MOTIVOS_EVENTO_COLETIVO@85, CONFIRMAR_FERIAS_AUTOMATICAMENTE@92, CONFIRMAR_CHUVA_AUTOMATICAMENTE@100, EVENTO_COLETIVO_A_PARTIR_DE@105, CLASSIF_TURNO_SEM_LANCAMENTO@106, CLASSIF_POSSIVEL_EVENTO@107, CLASSIF_CHUVA_AUTOMATICA@108, AVISO_AFASTAMENTO_FRACAO_MAX@110, AVISO_AFASTAMENTO_TURNOS_MIN@111, AVISO_AFASTAMENTO_PERIODO_MAX_DIAS@112, HORA_LIMITE_INICIO_MANHA@125, HORA_LIMITE_FIM_MANHA@126, HORA_LIMITE_INICIO_TARDE@127, HORA_LIMITE_FIM_TARDE@128, PONTOS_PERDA_INICIO_MANHA_ATRASADO@131, PONTOS_PERDA_FIM_MANHA_ANTECIPADO@132, PONTOS_PERDA_INICIO_TARDE_ATRASADO@133, PONTOS_PERDA_FIM_TARDE_ANTECIPADO@134, PONTOS_PERDA_TURNO_SEM_LANCAMENTO@135, PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO@138, PONTOS_PERDA_VISITA_RAPIDA@139, PONTOS_PERDA_VISITA_LONGA@140, PONTOS_PERDA_VISITA_DUPLICADA@141, PONTOS_PERDA_SEQUENCIA_SUSPEITA@142, PONTOS_PERDA_VISITA_NEGATIVA@143, PONTOS_PERDA_FORA_EXPEDIENTE@144, PONTOS_PERDA_VISITA_ALMOCO@145, PONTOS_PERDA_DIA_SEM_META@146, PONTOS_GANHO_DIA_COM_META@149, PONTOS_GANHO_SEM_VISITA_RAPIDA@150, PONTOS_GANHO_SEM_AUSENCIA@151, PONTOS_GANHO_PONTUALIDADE_PERFEITA@152, NOTA_FAIXA_EXCELENTE@155, NOTA_FAIXA_BOM@156, NOTA_FAIXA_ATENCAO@157

## scripts/coleta/processamento.py (154 linhas)

- L26 `processar(equipe, id_ag, session_base, cfg)`
- L105 `processar_ponto_estrategico(id_ag, session_base, cfg_pe)` — Coleta as visitas de Ponto Estratégico de um agente (URL/id_atividade

## scripts/coleta/saida_excel.py (341 linhas)

- L65 `_slugify_nome_arquivo(nome)` — Converte o título de uma aba (com espaços/acentos) num nome de arquivo seguro.
- L72 `exportar_todas_abas_csv(wb, pasta_saida)` — Exporta CADA aba do workbook como um arquivo .csv separado (com os
- L98 `salvar_excel_consolidado(resultados, df_total, pasta_saida, seman)`
- L327 `_preparar_ponto_estrategico(semanas_todos_agentes)`

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
