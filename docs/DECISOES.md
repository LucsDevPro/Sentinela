# Registro de decisões (mais recente primeiro)

## 06/11/2026 — otimizações de leitura/geração (menos token, mais rápido)
- **Cache em memória da leitura das semanas** (`_ler_aba_visitas` em `coleta/cache_semanas.py`): guarda o `read_excel` CRU (as conversões, como `acima_teto_media`, rodam a cada
  chamada), chave = caminho + data de modificação + tamanho, devolve cópia, invalidado por `_salvar_df_semana`, seguro entre threads; `SENTINELA_SEM_CACHE_LEITURA=1` desliga.
  **Ganho medido (modesto): Acumulado 66 → 46 s, rodada do histórico 47 → 39 s, detecção sem ganho (lê cada semana uma vez); `regenerar_mes todos` ≈ 228 → 184 s (~20%).**
  Saída idêntica com e sem cache (152 mil células de 8 planilhas + `deteccoes_pendentes.json`). Próximo gargalo medido: `_primeira_visita_historica` reabre todas as semanas (~15 s por processo).
- **`scripts/rodar_testes.py`** (roda no Windows) passa a ser a ÚNICA lista de testes; `rodar_testes.sh` só chama ele. Teste novo: `test_cache_leitura.py`.
- **`scripts/xlsx_scan.py`** abre a planilha UMA vez, em `read_only`, e lê por `iter_rows` (antes: reabria a cada aba e criava um objeto por célula). Geração do dashboard 3 a 7× mais rápida
  (Outubro 7,9 s → 1,5 s; Acumulado 14,8 s → 2,2 s), **HTML e `partes/` idênticos byte a byte** (conferido em 3 planilhas e pelo `tools/comparar_saidas.py`). As planilhas abertas são fechadas ao sair do processo (`atexit`).
- **`CLAUDE.md` enxuto** (7,4 → ~5 KB) + **`.claude/rules/`** (coleta, dashboard, editores/Worker, workflows): carregam só quando se abre arquivos da área.
  `.claude/settings.json` bloqueia também `data/deteccoes_pendentes.json` e os `chart.umd.js` — para dados use `python3 scripts/resumo.py`.
- **`scripts/resumo.py`** (consultas curtas: meses, detecções, ranking com `--vs` backup, cronograma, manifest), **`scripts/regerar_paginas.py`** (todas as páginas numa chamada) e
  **`tools/comparar_saidas.py`** (rede de segurança para refatorar o gerador: as chamadas do CI em duas versões, saída idêntica). Testes: `test_resumo.py`.
- `docs/PROMPT_DIVISAO_DASHBOARD.md`: plano para dividir `generate_dashboard.py`. **Não executado de propósito** (60 funções pequenas; ganho pequeno para o risco).

## 05/11/2026 — Maio e Junho saem do programa; regras novas em todos os meses; cabeçalho compacto
- **Maio e Junho/2026 excluídos** (semanas 305–312): sem coleta (`PRIMEIRA_SEMANA_COLETA = 313`), sem página, fora do Acumulado e da média dos meses.
  Removidos: `data/semanas/305–312*`, `data/historico/semanas_305-308/309-312` (+ backups), `historico/` e `partes/` desses meses, 13 detecções e 35 itens de
  cronograma que terminavam antes de 28/06, e a produção de Maio/Junho em `data/outras_atividades.json`. O histórico do Git guarda tudo.
- **Julho, Agosto e Setembro reabertos e recalculados com as regras atuais**, depois congelados de novo. Estavam com as regras antigas. Depois do recálculo a nota sobe para 38 de 49 agentes (Julho), 36 de 42 (Agosto) e
  39 de 42 (Setembro); ninguém desce; média +6 a +8 pts (maior alta +18,5); a posição muda para 44, 34 e 32 agentes. Cópias antigas: `data/historico/backup_congelado/*_antes-das-regras-novas.xlsx`.
  (O registro de 02/11 dizendo que "Maio–Outubro foram regenerados" não era verdade para os meses congelados.)
- **Chuva confirmada automaticamente voltou a `pendente`** (41 paralisações coletivas de Julho em diante, antes da regra de 02/11 sem validação humana). Férias já
  validadas pela coordenação e decisões de `falta` ficaram como estavam. Atestado: todos os 98 lançamentos já são "Ausência justificada" (sem diagnóstico).
- **Cabeçalho da home refeito:** tudo na mesma linha e na mesma altura (36 px, `--hbtn-h`); os 4 botões de texto têm a mesma largura
  (`.hbtn` em `.hnav`) e tema/imprimir viraram quadrados só com o símbolo (`.hbtn-ico`); "Ocultar nomes" e "Animações" viraram `.hopt`;
  no celular os botões ficam em 2×2. Marcação em `scripts/templates/base.html`, estilo em `scripts/style.css`.
- **Pequenas melhorias (05/11/2026):** selo "período em andamento até dd/mm" no cabeçalho dos meses ainda abertos (`periodo_em_andamento` em
  `generate_dashboard.py`); título e explicação do painel de férias corrigidos ("no período", limite de 7 dias úteis, "(confirmada)");
  `regenerar_mes.py` mantém só os 3 backups mais recentes por mês. CI: `test_turno_evento.py` não rodava no CI (só no `rodar_testes.sh`) e o pip não usava cache.
- **Regra do turno sem lançamento, ordem de decisão (coordenação, 05/11/2026):** 1º **22 ou mais agentes** sem lançamento no mesmo turno = evento
  externo/interno (regra máxima; era 20); 2º abaixo disso, **toda a equipe** (agentes ativos, 2+) sem lançamento = chuva isolada ou reunião;
  3º senão, falta (desconta), salvo o que o cronograma cobre (atestado, folga, férias). Só a observação da aba Ausências mudou de texto
  (a classificação segue "Possível Evento Externo ou Interno"). Julho–Outubro recalculados. **Opção `CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE`**
  (padrão False = como antes: só contam os não cobertos pelo cronograma): ligada, quem já está coberto por chuva/reunião também entra nos 22,
  e confirmar a chuva de uma equipe deixa de tirar o turno das outras do limite (sem ela, em Setembro, confirmar 7 paralisações como chuva
  faria 8 agentes perderem até 1,5 pt). Férias, folga e atestado nunca contam. Teste: `test_turno_evento.py`.
- **Workflow "Regenerar mês congelado"** (`regenerar-mes.yml` + `scripts/regenerar_mes.py`): refaz um mês antigo com as regras de hoje, com
  modo simulação e backup (ver OPERACAO.md). Reabre um mês por vez, em ordem: o desempate do ranking lê a média dos meses anteriores do
  `manifest.json`; as reaberturas de Julho–Setembro feitas no mesmo dia, todas de uma vez, deixaram Agosto e Setembro sem o desempate,
  e foram refeitas em ordem.

## 04/11/2026 — cartinha: nível e borda pela mesma nota arredondada; cartinha 100 redesenhada
- **Correção:** o nível (ouro/prata/bronze/destaque) usava a nota exata e a borda usava a arredondada — 89,6 aparecia como 90, com cartão prata e borda de ouro. Agora os dois usam a nota arredondada que está escrita no cartão (≥ 90 ouro, ≥ 75 prata, abaixo bronze; destaque = top 3 com 90–99). `assets/carta.js` (`medidas`). Teste ajustado em `scripts/test_sessao10_navegador.py`.
- **Medida CON (consistência) da cartinha:** passou a considerar só os TRÊS ÚLTIMOS meses do período mostrado (hoje, agosto a outubro): desvio-padrão dessas três notas, CON = 100 − 5 × desvio (máx. 99). Antes usava todos os meses, e um único mês fora da curva (ex.: Maio 0,0 do agente 1936) zerava o CON. Com só um mês, CON = 99. `medidas` em `assets/carta.js`.
- **Quem chega ao teto de 100 é ordenado pela nota bruta (100 + critérios, ex.: 110,6), só na cartinha e no álbum.** Desempate: média dos meses anteriores e depois a posição oficial. A nota mostrada continua limitada a 100 e o ranking oficial (dashboard, Excel, `_preparar_ranking`) não mudou. `Carta.bruta`/`Carta.posicao` em `assets/carta.js`; ordenação em `album.html`.
- **Escala única da cartinha (pela nota arredondada):** 100 LENDÁRIA (tempestade) · 90–99 OURO · 80–89 PRATA · 70–79 BRONZE · 60–69 AÇO · abaixo de 60 FERRO. Cor do cartão e borda seguem a mesma faixa; a borda engrossa com o nível (`--bw`). **Mudou:** prata passou de ≥ 75 para ≥ 80 e bronze de < 75 para 70–79 (aço e ferro são novos). Top 3 com 90–99 = cartão de ouro com borda holográfica (`b-top`, rótulo DESTAQUE); a de 100 é uma só, sem variação de top 3. Filtro "Nível" do álbum atualizado.
- **Cartinha 100** ("Tempestade"): fundo escuro com raios e faíscas na borda, só com a classe `b-100` (`assets/carta.css` e o desenho do PNG em `assets/carta.js`; os raios são gerados em `RAIOS/ARCOS/FAISCAS`).

Uma entrada por decisão: **data · decisão · por quê · onde está no código**. Acrescente sempre que uma regra mudar.

## 04/11/2026 — desempate por média, detalhamento na cartinha e opção de ocultar fotos
- **Desempate do ranking:** nota igual → fica na frente quem tem a maior **média dos meses anteriores** (a da tabela "Média Mensal por Agente", arredondada em 1 casa;
  o mês do próprio período não entra; sem histórico fica atrás; empate total mantém a ordem anterior). `coleta/ausencias_ranking.py` → `_media_historica_por_agente`
  + chave de ordenação em `_preparar_ranking`. Teste: `scripts/test_desempate.py`. O álbum (`album.html`) aplica a mesma regra no navegador.
- **Cartinha:** passar o mouse mostra o detalhamento (todos os critérios do mês, vindos de `detalhe` em `assets/agentes_dados.js`, gerado por `scripts/gerar_agentes.py`);
  clicar fixa (no celular, o toque). Borda por faixa de nota e cor do 100 = ouro de 90–99 (`assets/carta.css`); foto por ID em `assets/fotos.js`; checkbox "Ocultar fotos".

## 03/11/2026 — organização do repositório (branch `organizacao`)
- **README reduzido** (853 → ~60 linhas). Conteúdo movido sem remover informação: `docs/OPERACAO.md` (coleta, detecção de férias, cronograma, atestado/férias,
  meses congelados, planilhas antigas), `docs/INSTALACAO.md` (Secrets, Pages, Worker, teste local), `docs/REGRAS_DETALHADAS.md` (ranking normalizado, teto de
  20 min, regras de ausência) e o histórico de sessões no fim deste arquivo. `docs/REGRAS.md` ficou curto de propósito (é o que o `CLAUDE.md` manda ler).
- **Correções feitas no texto migrado:** cron (era "segunda/terça/quinta"; real: dom/seg/ter 07:00 UTC); férias disparam com 7 dias úteis
  (`LIMITE_DIAS_UTEIS_FERIAS`; o README falava em "mais de 5" e numa constante que não existe mais); detecções novas entram `pendente` (o README dizia
  "confirmado automaticamente"); nome do repositório (`dashboard-visitas` → `sentinelaprime`) e URLs; árvore de pastas completa.
- **Novos:** `.env.example`; `.gitignore` revisado (`.env`, `node_modules`, `.playwright`, `.wrangler`, temporários); `scripts/rodar_testes.sh` passou a incluir
  `sessao8/9/10` (o CI já rodava) e mostra a última linha de saída quando o teste não imprime ✅/❌.
- **`scripts/coletar_evisita.py` dividido** (4.953 linhas → fachada de ~70 linhas + pacote `scripts/coleta/` com 16 módulos em camadas; o maior tem 769 linhas).
  Cada nó (função/constante) foi copiado sem alteração: o AST dos 259 nós é idêntico ao original, nenhum nome ficou indefinido e as 164 constantes
  (inclusive as carregadas dos JSON) e 116 funções têm o mesmo valor/bytecode (única diferença: o compilador não otimiza chamada de método em nome importado).
  A fachada reexporta todos os nomes e repassa `C.X = valor` aos módulos que possuem `X` (os testes fazem isso com `HOJE_OVERRIDE`, `CONFIRMAR_*`, `PASTA_SEMANAS`...;
  sem esse repasse 4 testes falham — verificado). `python scripts/coletar_evisita.py ...` e `import coletar_evisita as C` seguem iguais; workflows não mudaram.
  Mudanças pontuais de lugar para evitar ciclos: `_classificar` → calculos; `_carregar_agentes_sem_abono`, `_agente_sem_abono_em`, `CAMINHO_AGENTES_SEM_ABONO` → deteccao;
  `_preparar_ponto_estrategico` → saida_excel. Agora só `coleta/sessao.py` importa `selenium`.
- Nada de regra de negócio, pontuação, workflow ou HTML da raiz foi alterado.

## 02/11/2026
- **Possível Evento vale para todos os períodos (Maio–Outubro)** (`EVENTO_COLETIVO_A_PARTIR_DE = None`). Reclassifica ~1.100 turnos
  (Maio 246, Junho 161, Julho 198, Agosto 143, Setembro 202, Outubro 157); média de pontos sobe de 6 a 8 por mês, ninguém desce.
  Para poupar o passado: `date(2026, 10, 4)`.
- **Turno sem Lançamento é o padrão; Possível Evento Externo/Interno** com 22+ agentes no mesmo turno (era 20; mudou em 05/11/2026) ou equipe inteira sem lançamento
  (sem desconto). Antes de descontar, confere cronograma. Por quê: coordenação quer verificar chuva/treinamento/atestado/férias/folga/reunião
  antes de punir. → `_preparar_ausencias`, `LIMITE_AGENTES_EVENTO_TURNO`. Teste: `test_turno_evento.py`.
- **Detecções novas de férias e paralisação entram `pendente`** (antes entravam confirmadas). Decisões antigas intactas.
  → `CONFIRMAR_FERIAS_AUTOMATICAMENTE`, `CONFIRMAR_CHUVA_AUTOMATICAMENTE`.
- **Agente 3177 — Patricia Lanjer de Souza Domingues, Equipe 3** (agente nova). Treinamento lançado no cronograma de 05/10 a 30/10/2026
  (`Reunião/Treinamento`). Se continuar em novembro, estender o período em `data/cronograma_ausencias.json`.
- **Alana (2951) e Teonilda (3035)** seguem como **falta** (decisão da coordenação): desconto mantido.
- **Painel de Custos remodelado:** custo no ritmo × custo real; dias esperados já sem férias/atestado/treinamento/paralisação;
  média geral = folha ÷ horas úteis; tabela de custo mensal por agente; legendas e faixas. → `generate_dashboard.py` (`build_kpi_custos` e afins).
- Seletor de meses no tema claro: cores próprias (antes se misturava ao cabeçalho). → `scripts/style.css` (`.period-select`).
- Ranking de todos os meses conferido: Maio–Outubro regenerados com o método novo; Acumulado segue no antigo.

## Pendente de decisão (02/11/2026)
- Dias de chuva da Ana Gabriela (28 e 29/10, 14/10 tarde, 30/10 manhã): não confirmados (só havia previsão, sem medição).
- Os 7 turnos de Outubro classificados como evento (06/10 M, 08/10 M, 13/10 M e T, 14/10 M, 15/10 M, 30/10 T) aguardam confirmação.

---

# Histórico de sessões (migrado do README em 03/11/2026, texto original)

Os itens abaixo descrevem o que foi feito em cada sessão (29/10 a 01/11/2026). Servem de consulta; as regras atuais estão em `docs/REGRAS.md`.

## Sessões 8 e 9 (31/10/2026) — coordenação e agentes

**Pré-requisito:** Cloudflare configurada (seção acima). Sem ela, `validar.html` avisa e o formulário de contestação não aparece.
Copie para o repositório: `.github/`, `partes/`, `assets/` (agora com `agentes_dados.js` e ícones), `worker/` (cole o novo `index.js` no Cloudflare e **publique**), e os arquivos novos `agente.html`, `contestacao.html`, `manifest.webmanifest`, `sw.js`, `data/meses_arquivados.json`, `data/metas_equipes.json`.

### `validar.html` — abas novas
- **Ajuste de pontos**: agente, dia, pontos (até ±20), motivo curto. Pede confirmação com resumo; aparece no Extrato como "Ajuste manual: motivo" (**público**: o sistema recusa motivo com palavras de saúde/atestado). Lista os ajustes lançados, cada um com **Desfazer**. Mês fechado não aceita ajuste.
- **Equipe parada**: chuva, reunião/treinamento/capacitação, levantamento de índice, ovitrampa, recuperação de casas; uma equipe ou todas; datas (até 30 dias); dia inteiro, manhã ou tarde. Grava no cronograma (substitui o `cronograma_editor.html`). Cada parada tem **Remover**.
- **Fechar mês**: lista de conferência automática (semanas coletadas e mês terminado; próximo mês e ciclo cadastrados; nenhuma férias esperando validação; nenhum dia sem classificação; cópia de segurança automática). O botão só liga com tudo ✅. Fechar congela o mês e as semanas dele. **Reabrir** exige digitar o nome do mês e faz cópia antes (em `data/historico/backup_congelado/`).
- **Contestações**: pedidos dos agentes; **Aceitar** (com pontos opcionais, que viram um ajuste) ou **Recusar**, sempre com resposta curta.
- **?**: ajuda com o que cada botão faz.
- **Aplicativo no celular**: "Adicionar à tela inicial" instala como "Sentinela — validação". O PIN só vale enquanto o app está aberto; o service worker guarda só a página e nunca o que vem do Worker.

### Para os agentes
- **`agente.html?id=…` / `?nome=…`**: nota por mês e por semana, dias trabalhados × esperados, o que mais tirou e deu pontos. Só dados públicos, sem saúde; respeita o modo apresentação. Há link 📈 no Ranking e no Extrato.
- **Extratos em lote** (aba Ranking): "Imprimir da equipe" e "Imprimir de todos do mês" — uma folha por agente, sem página em branco; use "Salvar como PDF" na impressão.
- **Contestação**: no Extrato (só mês aberto), "Algo errado? Peça uma revisão" → critério + uma frase → o agente recebe um **código** e consulta a resposta em `contestacao.html`. Tudo fica só no Worker (nada em arquivo público); limites: 4 pedidos/hora por rede, 3 por dia por agente, campo-isca anti-robô, sem links no texto.
- **Comparativo semanal por equipe** (aba Equipes do mês): nota média de cada equipe por semana; semana parcial em tom mais claro.
- **Metas por equipe** (opcional): `data/metas_equipes.json`, ex.: `{"Equipe 1": 25}`. Quem não aparece usa a meta padrão (20). Aparece em "Como o ranking é calculado". Hoje o arquivo está vazio.

### Testes
`python scripts/test_sessao8.py`, `python scripts/test_sessao9.py` e `node worker/test_worker.mjs` rodam no workflow. Os de navegador (`scripts/test_sessao8_navegador.py`, `scripts/test_sessao9_navegador.py`) exigem Playwright e rodam só no computador de desenvolvimento.

## Identidade visual "painel de monitoramento" (31/10/2026)

Todas as páginas (dashboard, histórico, semanas, acumulado, `validar.html`, `agente.html`, `contestacao.html`, transparência) usam o mesmo visual: fundo azul-marinho profundo com as cores do logo da prefeitura (amarelo, vermelho e verde-água) e a faixa do topo que repete o sublinhado do logo. Números e títulos em **Barlow Semi Condensed**, texto em **IBM Plex Sans** — as fontes ficam em `assets/fonts/` (sem internet externa; licença OFL) e são carregadas por `assets/fontes.css`.
- **Impressão continua em papel branco** (relatórios, extratos e lote).
- No celular o cabeçalho deixa de ficar fixo no topo e as abas rolam para o lado.
- Para ajustar cores: no dashboard, `scripts/style.css` (bloco `:root`); nas outras páginas, o bloco `:root` no começo de cada arquivo.
- Copie para o repositório também: `assets/fonts/`, `assets/fontes.css` e os ícones novos `assets/icone-*.png`.

## Novidades de 29–30/10/2026

**Visões semanais (mês vigente).** Outubro e Novembro/2026 (e os próximos meses) ganham uma barra
`Semana 1 | Semana 2 | … | Mês completo` no topo da página do mês. Cada semana é uma página completa, com as
**mesmas regras** do ranking aplicadas só àqueles dias (veja a aba Equipes para o desempenho por equipe).
A semana em andamento aparece como **parcial**. Quando o mês é arquivado (`MESES_ARQUIVADOS`), as semanas dele
congelam junto na execução seguinte. Meses anteriores a Outubro não ganham semanais
(`PRIMEIRA_SEMANA_VISAO_SEMANAL`). Teste: `python scripts/test_semanal.py`.

**Presença mínima (nota proporcional).** Presença = dias trabalhados ÷ dias esperados (os esperados já descontam férias,
folga e ausência justificada). Abaixo de 50% (`PRESENCA_MINIMA_FRACAO`) a nota é multiplicada por presença ÷ 50%.
Só vale de Outubro/2026 em diante e não vale para Equipe Bloqueio / Ponto Estratégico. Aparece como linha no Extrato.

**Rótulo neutro.** O repositório é público: "Atestado" passa a ser sempre "Ausência justificada" e a detecção
automática grava só "Férias". Entradas antigas são convertidas na leitura (`_motivo_neutro`).

**Dia em andamento.** O dia de hoje nunca gera ausência, e quem ainda não lançou nada hoje não "deve" o dia de hoje nos dias esperados.

**Setembro/2026 reaberto e arquivado de novo (29/10).** Foi refeito com as regras atuais (dias esperados corrigidos,
feriado de 07/09). A versão anterior está em `data/historico/backup_congelado/`. Julho e Agosto continuam congelados.

**Transparência e peso das páginas.** `transparencia.html` explica o cálculo e é gerada das constantes do código
(`python scripts/gerar_transparencia.py`); tem link no cabeçalho e no Extrato. As páginas ficaram bem mais leves:
o Chart.js é um arquivo compartilhado (`assets/chart.umd.js`) e as tabelas de alertas e os extratos ficam em
`partes/` e carregam só quando você abre a aba/extrato (funciona também com o arquivo aberto do disco).
Ao subir arquivos à mão, suba também as pastas `partes/` e `assets/`.

**Atualização de 30/10/2026 — meses antigos recalculados.** Maio a Setembro foram reabertos, recalculados com as regras novas
(sem fator de normalização, feriados em todos os meses, dia inteiro sem lançamento, presença mínima, sem abono) e arquivados de novo.
As planilhas anteriores estão em `data/historico/backup_congelado/`. O **Acumulado** continua no método antigo (período longo).
`data/agentes_sem_abono.json` agora inclui Alana (2951) e Teonilda (3035) desde 01/01/2026: férias viram falta; só ausência
justificada lançada pela coordenação abona. Para tirar alguém da lista, apague a entrada.

**Acumulado = só a média.** Na página Acumulado a aba Ranking passa a ser "Ranking (média dos meses)": a média simples das notas
mensais de cada agente (com a tendência e a evolução). O ranking detalhado e o Extrato ficam na página de cada mês.

## Blindagem da coleta (30/10/2026)
- **Timeouts:** toda chamada HTTP usa (conexão 15 s, leitura 60 s); o Selenium tem tempo máximo de carga de página (60 s) e de espera por elemento (30 s).
- **Novas tentativas:** espera crescente com jitter (1 s, 2 s, 4 s… até 30 s) nas páginas, no login (3 tentativas) e na verificação de saúde.
- **e-Visita fora do ar:** antes de coletar, o coletor testa a página de login. Se não responder, **pula a coleta e publica com os dados que já existem**; as semanas são tentadas de novo na próxima execução (aviso no resumo da execução).
- **Uma semana com problema não derruba as outras:** o erro vai para o resumo (GITHUB_STEP_SUMMARY) e a coleta segue. Sessão caída = abre sessão nova e refaz a semana uma vez. Duas semanas seguidas falhando por inteiro = para (site instável) e deixa o resto para a próxima execução.
- **Tempo:** o coletor não começa semana nova depois de 170 min; o passo tem teto de 240 min e o job de 330 min. Se estourar, o site é publicado com o que já foi salvo.
- **Cache nunca piora:** um agente que volta sem nenhuma visita, ou com menos da metade do que já estava salvo, mantém os dados antigos.
- Versões das ações do GitHub fixadas (checkout 4.2.2, setup-python 5.3.0, upload-pages-artifact 3.0.1, deploy-pages 4.0.5) e do `requirements.txt` já eram fixas.
- Teste: `python scripts/test_coleta.py`.

## Sessão 10 — visual claro, tela de reunião e exportação (01/11/2026)

- **Tema claro é o padrão.** Em todas as páginas há o botão "Tema escuro / Tema claro" no cabeçalho; a escolha fica salva só no navegador de quem clicou (`assets/tema.js`). A impressão e o PDF saem sempre em fundo branco.
- **Ícones próprios** (`scripts/icones.py`) no lugar dos emojis de enfeite. Os emojis de situação (🟢🟡🟠🔴 ✅ ❌ ⛔) continuam, porque fazem parte da informação.
- **Gráfico por equipe, semana a semana** com as cores do logo e o valor escrito em cada barra.
- **Animação de entrada nos números** (contagem até o valor, 0,6 s). Caixa "Animações" no cabeçalho desliga; respeita a opção "reduzir movimento" do aparelho.
- **Baixar o ranking**: na aba Ranking, botão "Planilha (CSV, abre no Excel)" (sem nomes se o Modo apresentação estiver ligado) e link para o .xlsx completo do período.
- **Tela de reunião** (`projecao.html`, botão "Tela de reunião" no cabeçalho): alterna sozinha entre resumo do mês, top 10, maior evolução, equipes semana a semana e média por mês. Teclas: espaço pausa, ← → trocam, F tela cheia, N mostra/oculta nomes. Nomes começam ocultos.
- Teste novo: `python3 scripts/test_visual_navegador.py` (só na máquina de desenvolvimento).
- **Arquivos novos para copiar ao repositório:** `assets/tema.js`, `projecao.html`, `scripts/icones.py` (e, como sempre, as pastas `.github`, `partes` e `assets`).

## Sessão 11 — comparar meses, cartão do agente e linha do tempo (01/11/2026)

- **Comparar mês com mês** (`comparar.html`, botão "Comparar meses" no cabeçalho): escolha dois meses e veja a média geral, quem subiu, quem caiu e quem ficou estável (até 0,5 ponto), agrupado por equipe, com quantas posições cada um ganhou ou perdeu. Abas "Quem subiu / Quem caiu". Avisa quando um dos meses ainda está aberto.
- **Cartão do agente em estilo carta de jogador (com o logo novo em tom sobre tom, `assets/logo_carta.png`)** (topo de `agente.html`): nota do mês em destaque, equipe, posição e seis medidas de 0 a 99 (ASS assiduidade, TUR turnos cobertos, CON consistência, EVO evolução, POS posição, MED média dos meses). Nível pela nota: ouro ≥ 90, prata ≥ 75, bronze abaixo; "destaque" para top 3 com nota ≥ 90. Sem foto (usa as iniciais) e sem marcas de terceiros. No Modo apresentação nome e iniciais ficam borrados. A explicação das medidas aparece ao lado do cartão.
- **Linha do tempo do agente** (`agente.html`): mês a mês (e semana a semana dentro do mês aberto) com um quadradinho por dia esperado — cheio = trabalhado, vazio = sem lançamento — e etiquetas das **paradas da equipe** (chuva, reunião, mutirão…), que não contam como falta. Fica de fora, de propósito, qualquer lista dia a dia de ausência por agente: isso é sensível e o repositório é público.
- `scripts/gerar_agentes.py` passou a gravar `paradas` (vindas de `data/cronograma_ausencias.json`) em cada mês e semana.
- Testes novos: `scripts/test_sessao10.py` (entra no workflow) e `scripts/test_sessao10_navegador.py` (só na máquina de desenvolvimento).
- **Copiar para o repositório:** `comparar.html`, `agente.html`, `scripts/` e `.github` (e as pastas `partes` e `assets`, como sempre).

### Álbum de cartinhas (`album.html`)
Todas as cartinhas dos agentes, da maior nota para a menor, com o número do lugar. Passar o mouse (ou tocar no celular) amplia a cartinha; clicar abre a evolução do agente. Filtros por mês, equipe, nível (destaque/ouro/prata/bronze) e busca por nome; respeita o Modo apresentação e o tema claro/escuro. Botão "Álbum de cartinhas" no cabeçalho do painel.
O desenho da cartinha agora vive em `assets/carta.css` e `assets/carta.js` (usados pelo álbum e pela página do agente) e o logo em `assets/logo_carta.png`.
**Copiar:** `album.html`, `agente.html`, `assets/` (carta.css, carta.js, logo_carta.png) e `scripts/`.

### Cartinha como imagem / WhatsApp (página do agente)
Dois botões ao lado da cartinha: **Baixar imagem** (PNG) e **Enviar pelo WhatsApp**. No celular abre a lista de compartilhamento já com a imagem anexada; no computador baixa a imagem e abre o WhatsApp com a frase pronta (basta anexar). No Modo apresentação a frase sai sem o nome e a imagem sai com o nome coberto por bolinhas. A imagem é desenhada no próprio navegador (`Carta.png` em `assets/carta.js`), então só funciona pelo endereço do site (não abrindo o arquivo direto do computador). Copiar: `agente.html` e `assets/carta.js`.
