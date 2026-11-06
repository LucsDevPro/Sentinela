# Operação do sistema

> Migrado do `README.md` em 03/11/2026 sem remover informação. Onde havia texto desatualizado ele foi corrigido
> (lista em `docs/DECISOES.md`, entrada de 03/11/2026). Em caso de dúvida valem `CLAUDE.md` e `docs/REGRAS.md`.
> Contém: funcionamento da coleta/dashboard, detecção de férias, cronograma, atestado/férias, meses congelados, planilhas antigas.

## Funcionamento da coleta e do dashboard (texto original da abertura do README)

Este repositório agora faz o processo **inteiro sozinho**: coleta os dados no
e-Visita, gera o `index.html` do dashboard e publica no GitHub Pages — tudo
automaticamente, domingo/segunda/terça de madrugada, sem precisar rodar nada na sua máquina nem
subir planilha manualmente.

Continua funcionando também o jeito antigo (subir uma `Analise_Consolidada.xlsx`
manualmente em `data/`) como alternativa/backup, caso a coleta automática
falhe ou você precise reprocessar um dado específico.

**Página inicial configurável + aba "Acumulado":** o `index.html` (home)
mostra o período definido em `data/config_home.json` — por padrão, Outubro/2026
(`{"arquivo": "data/historico/semanas_327-330.xlsx", "label": "Outubro/2026"}`).
Separado da home, `acumulado.html` sempre mostra a SOMA de TODAS as semanas
já coletadas até agora (não depende de configuração nenhuma, é sempre o
`data/Analise_Consolidada.xlsx` puro) — os dois aparecem lado a lado no
seletor de período do topo ("🏠 Início" e "📊 Acumulado"), junto com cada mês
arquivado em `historico/`.

Pra trocar qual período aparece na home, tem duas formas:
  - **Editor visual** (recomendado): abra **`home_editor.html`** no
    navegador, cole o conteúdo de `data/historico/manifest.json`, escolha o
    período no menu e copie o JSON gerado pra `data/config_home.json` no
    GitHub. Mesmo padrão do `cronograma_editor.html` — sem precisar mexer em
    código.
  - **Na mão**: edite `data/config_home.json` direto, com o caminho
    (relativo à raiz do repo) e o rótulo do arquivo que deve virar home.

Se `data/config_home.json` não existir ou apontar pra um arquivo que sumiu,
a home cai automaticamente pro acumulado, pra nunca gerar uma home quebrada.

**Coleta semana a semana:** a coleta não busca mais um intervalo de semanas
de uma vez só — cada semana do e-Visita (HTML ID) é buscada e cacheada
SEPARADAMENTE em `data/semanas/<html_id>.xlsx` (+ `_pe.xlsx` pro Ponto
Estratégico, `_pendencia.json` com os números de fechados/recusados). A cada
execução (agora domingo/segunda/terça às 3h):

  1. Recoleta a última semana já salva (os dados do e-Visita ainda podem mudar).
  2. Busca a(s) semana(s) nova(s), se já estiver(em) disponível(is) no site.
  3. Consolida TODO o cache disponível num único `data/Analise_Consolidada.xlsx`.
  4. Reconstrói `data/historico/` a partir do cache — **apenas páginas
     MENSAIS** (Julho, Agosto, Setembro, Outubro, Novembro...). As páginas
     semanais soltas (semanas 318-326) foram arquivadas em
     `data/historico/arquivo_semanal/` (fora do menu, dados preservados); o
     detalhe por semana continua disponível pelo filtro de semana dentro de
     cada página mensal. Pra voltar a gerar uma página por semana, troque
     `GERAR_PAGINAS_SEMANAIS` pra `True` em `scripts/coleta/parametros.py`.

Na primeira execução (`data/semanas/` vazio), o script coleta da semana
27/2026 (HTML 313, início de Julho) até a semana atual, uma planilha por
semana. Maio e Junho/2026 saíram do programa em 05/11/2026 (sem coleta, página, Acumulado ou média). O `data/semanas/` é commitado no repositório junto com o resto — é
ele que guarda "até onde já coletamos" de uma execução pra outra.

**Ciclos diferentes por semana:** o `id_ciclo` usado na consulta ao e-Visita
não é fixo — muda em pontos específicos do ano. Isso já está mapeado em
`CICLOS_TRATAMENTO`, em `scripts/coleta/parametros.py`:
```python
CICLOS_TRATAMENTO = [
    (322, 326, 164),  # semanas 322-326 (setembro/2026) usam id_ciclo 164
    (327, 330, 164),  # semanas 327-330 (outubro/2026)  usam id_ciclo 164
    (331, 334, 165),  # semanas 331-334 (novembro/2026) usam id_ciclo 165
    # faixas sem entrada aqui usam o ID_CICLO padrão (163)
]
```
Se o site mudar de ciclo de novo no futuro, adicione uma nova linha aqui — o
formato é `(semana_inicio_html, semana_fim_html, id_ciclo)`.

**Limites de mês (histórico):** os "meses" do histórico (Maio/2026,
Junho/2026 etc.) NÃO batem exatamente com o calendário civil — são os
limites reais confirmados na URL do e-Visita, cadastrados em
`MESES_OFICIAIS`, em `scripts/coleta/parametros.py`:
```python
MESES_OFICIAIS = [
    (313, 317, "Julho/2026"),
    (318, 321, "Agosto/2026"),
    (322, 326, "Setembro/2026"),
    (327, 330, "Outubro/2026"),
    (331, 334, "Novembro/2026"),
]
```
(Julho a Setembro ficam em `MESES_ARQUIVADOS`, congelados.) Agosto a Novembro/2026 também estão em `MESES_OFICIAIS` (o nome do arquivo usa
sempre a faixa oficial do mês, ex.: `semanas_327-330.xlsx`, mesmo com o mês
incompleto — assim o link da home nunca quebra). Ao cadastrar um mês
novo aqui, a próxima coleta já reagrupa e renomeia os arquivos certinho; planilhas
órfãs são apagadas, exceto as semanais (`semana_<N>.xlsx`), que vão para
`data/historico/arquivo_semanal/`.

**Novo mês (passo a passo):** quando o e-Visita abrir um ciclo novo, copie da
URL de cada consulta o `id_ciclo` e as semanas, e cadastre 3 linhas em
`scripts/coleta/parametros.py`: `MESES_OFICIAIS` (nome do mês),
`CICLOS_TRATAMENTO` (atividade 4) e `CICLOS_PONTO_ESTRATEGICO` (atividade 3).
Depois, se quiser, aponte a home em `data/config_home.json` (ou use o
`home_editor.html`). Já estão cadastrados: Outubro (Tratamento 164 / P.E. 157,
semanas 327-330) e Novembro (Tratamento 165 / P.E. 158, semanas 331-334).
Trava de segurança: a partir da semana 327, semana SEM ciclo de Tratamento
cadastrado não é coletada (erro claro no log) em vez de usar o ciclo padrão
(que devolve dados vazios).

**Reprocessamento automático e seguro:** a cada semana coletada com sucesso a
partir da 327, o ciclo usado fica registrado em
`data/semanas/_ciclos_coletados.json`. Toda execução reprocessa sozinha as
semanas disponíveis cujo registro não bate com o ciclo configurado (ou que
nunca foram coletadas direito) — foi assim que Outubro (327-330) é recuperado
na primeira execução depois desta mudança, e depois disso para de ser
reprocessado. A recoleta SUBSTITUI os dados da semana (nunca soma, então não
duplica) e nunca piora o cache: coleta vazia não apaga nada, e agente que
falhar ou vier com páginas faltando mantém os dados que já estavam salvos.

Pra recoletar manualmente só uma semana específica (ex.: corrigir um dado):
```
python scripts/coletar_evisita.py --semana 313
```
(313 é o HTML ID da semana — ver `scripts/semanas_evisita.py` pra converter
entre HTML ID e "Semana do Ano".)

**Ranking — sem fator de normalização a partir de Outubro/2026:** a regra
mora em `RANKING_SEM_NORMALIZACAO_A_PARTIR_DE` (`scripts/coleta/pontos.py`,
hoje `date(2026, 10, 4)` = início da semana 327). Períodos que COMEÇAM nessa
data ou depois (Outubro, Novembro...) usam o método novo: Peso Efetivo = Peso
Nominal para todos, pontos = 100 + Σ(quantidade × peso), e **Dias Úteis
Esperados** = dias úteis do próprio período − dias de férias/atestado/folga/
chuva/reunião do cronograma em que o agente não trabalhou. Períodos que
passam de 45 dias (o Acumulado) seguem como eram, com
fator de normalização. Pra desligar a regra nova, coloque `None`. Testes:
`python3 scripts/test_ranking.py`.

**Aba "Média Mensal":** tabela agente × mês com a pontuação final de cada
mês e a média simples delas (`build_media_mensal` em
`scripts/generate_dashboard.py`). Não recalcula nada: lê a aba Ranking já
pronta de cada mês de `data/historico/manifest.json` (só meses "Mês/Ano"),
então meses fechados nunca mudam, e um mês novo entra sozinho na coleta
seguinte.

**Feriados nacionais:** `FERIADOS_NACIONAIS` (em `scripts/coleta/deteccao.py`) traz os feriados nacionais de 2026 e 2027 (sem pontos facultativos como Carnaval e Corpus Christi; acrescente os estaduais/municipais que a equipe não trabalha). Só valem a partir de `FERIADOS_VALEM_A_PARTIR_DE` (01/07/2026): descontam os dias úteis de Julho em diante (Julho e Agosto não têm feriado nacional; Setembro 21, Outubro 19, Novembro 18) — no cálculo dos dias esperados e na detecção de férias. Meses anteriores (Maio–Junho) seguem como foram calculados. Pra valer desde sempre, coloque `None`.

**Ranking — regras do método novo (Outubro/2026 em diante):**
- **Bônus proporcionais:** os bônus únicos (+5 sem visita rápida, +5 sem turno sem lançamento, +3 pontualidade) só são concedidos a quem trabalhou pelo menos `BONUS_MIN_FRACAO_DIAS_ESPERADOS` (50%) dos dias esperados; o Detalhamento/Extrato explica quando o bônus não vem. Meses antigos mantêm a regra antiga.
- **Observação "possível afastamento não registrado":** aparece na tabela do Ranking pra quem trabalhou pouco (< 70% dos dias esperados) e tem muitos turnos sem lançamento (≥ 4) — é sinal de férias/licença/atestado que falta lançar em `data/cronograma_ausencias.json` (ou confirmar em `deteccao_editor.html`). Parâmetros `AVISO_AFASTAMENTO_*` em `coletar_evisita.py`. Só em períodos de ~1 mês (não no Acumulado).
- **Extrato por agente:** botão **🧾 Extrato** em cada linha do Ranking abre a folha com a conta completa (dias, bônus, perdas, limite 0–100), pronta pra imprimir ou salvar em PDF (1 página A4).
- **Dias esperados de períodos que atravessam a virada** (ex.: Setembro, 31/08 a 02/10) usam o mês que domina o período, não o do último dia.
- **Média Mensal** agora mostra a **tendência** (diferença do último mês pro anterior) e um mini-gráfico por agente; dá pra ordenar pela tendência.

**Conferência automática de ciclos:** `scripts/validar_ciclos.py` roda a cada execução do workflow. Semana já iniciada sem `id_ciclo` (Tratamento ou P.E.) ou fora de `MESES_OFICIAIS` → o passo final da execução FALHA (o GitHub avisa por e-mail) com o motivo no resumo da execução; ciclos das próximas semanas faltando viram só um aviso. A coleta também escreve no resumo da execução os agentes ausentes/páginas faltando. Testes: `python3 scripts/test_ciclos.py`.

**Impressão do relatório completo:** o botão "🖨️ Imprimir relatório completo do mês" imprime todas as abas (A4 paisagem), sem páginas em branco — a 1ª tabela de cada aba não quebra página, legendas recolhidas saem abertas e o estado é restaurado depois.

**Tamanho das páginas:** `enxugar_html()` (em `generate_dashboard.py`) colapsa a indentação do HTML fora de `<script>/<style>/<pre>`; as páginas ficaram ~45% menores (Acumulado 6,9 → 3,8 MB) sem mudar o que aparece.

**Semana do e-Visita vs. Semana do Ano:** o e-Visita usa dois números
diferentes pra semana — o HTML ID (só pra consultar o sistema) e a "Semana
do Ano" (só pra mostrar pro usuário). A conversão entre os dois
(`html_id = semana_ano + 287`, válida só pra 2026) mora inteira em
`scripts/semanas_evisita.py`. Se o offset mudar em outro ano, valide um par
(html_id, semana_ano) real no site e atualize `OFFSETS_VALIDADOS` nesse
arquivo — o script trava com um erro claro em vez de converter errado.

**Filtro por semana no dashboard:** a aba "Resumo Completo por Agente"
agora tem um seletor de semana (só aparece quando o período carregado cobre
mais de uma semana) — junto com os filtros de equipe/classificação/nome já
existentes. Selecionar uma semana troca os números da tabela pros daquela
semana específica, sem precisar trocar de página. A aba "Ponto Estratégico"
já tinha esse filtro por semana antes.


O gerador do HTML usa **Jinja2**: o `generate_dashboard.py` só carrega a
planilha e prepara os dados; todo o HTML fica separado em templates dentro de
`scripts/templates/`, um arquivo por aba do dashboard. Isso deixa o código
bem mais curto e fácil de mexer — pra ajustar o layout de uma aba, edita só
o `.html` dela, não precisa tocar no Python.


## Estrutura do repositório (completa, conferida em 03/11/2026)

```
.
├── CLAUDE.md  README.md  requirements.txt  .gitignore  .gitattributes  .env.example
├── *.html (raiz)        ← páginas publicadas pelo Pages; NÃO mover (URLs, sw.js, manifest, workflows)
│   ├── index.html · acumulado.html · transparencia.html   ← GERADOS (não editar à mão)
│   ├── validar.html · agente.html · album.html · comparar.html · contestacao.html · projecao.html · atestado.html
│   └── home_editor.html · cronograma_editor.html · deteccao_editor.html   ← editores (abrir no navegador)
├── sw.js · manifest.webmanifest   ← app instalável no celular (só guarda a "casca" de validar.html)
├── historico/            ← páginas HTML de cada mês/semana arquivados (GERADAS)
├── partes/               ← alertas e extratos carregados sob demanda (GERADAS, *.alertas.js / *.extratos.js)
├── assets/               ← logo, fontes (fonts/), carta.css/js, tema.js, chart.umd.js, ícones; agentes_dados.js é GERADO
├── data/
│   ├── Analise_Consolidada.xlsx     ← acumulado (gerado pela coleta)
│   ├── semanas/                     ← cache por semana (NNN.xlsx, NNN_pe.xlsx, NNN_pendencia.json, _ciclos_coletados.json)
│   ├── historico/                   ← planilhas mensais + manifest.json; arquivo_semanal/ e backup_congelado/
│   ├── csv/                         ← CSVs de cada aba (gerados)
│   ├── config_home.json · config_worker.json · meses_arquivados.json · metas_equipes.json · outras_atividades.json
│   ├── cronograma_ausencias.json · deteccoes_pendentes.json · agentes_nomes.json · agentes_sem_abono.json · ajustes_ranking.json
├── scripts/
│   ├── coletar_evisita.py (fachada) · coleta/ (16 módulos: parâmetros, regras, ranking, planilhas, cache) · generate_dashboard.py · gerar_agentes.py
│   ├── aplicar_decisao.py · lancar_ausencia.py · lancar_atestado.py · fechar_mes.py · publicar_sugestoes.py
│   ├── gerar_form_atestado.py · gerar_transparencia.py · gerar_mapa.py · icones.py · meses_arquivados.py
│   ├── semanas_evisita.py · validar_ciclos.py · validar_json.py · xlsx_scan.py · rodar_testes.sh · test_*.py
│   ├── style.css · bootstrap.js · chart.umd.js
│   └── templates/ (base.html, macros.html, charts.js, sections/*.html — um arquivo por aba)
├── worker/               ← Cloudflare Worker (index.js, wrangler.toml, test_worker.mjs)
├── tools/shot.py         ← screenshot claro/escuro + erros de JS (usa Playwright; só no computador de desenvolvimento)
├── registros/            ← planilha de férias/ausências lançadas em 01/11/2026 + LEIA-ME.txt (sem categorias, repositório público)
├── docs/                 ← REGRAS.md, DECISOES.md, MAPA.md (gerado), INSTALACAO.md, OPERACAO.md, REGRAS_DETALHADAS.md
└── .github/
    ├── workflows/        ← update-dashboard.yml (dom/seg/ter 07:00 UTC), aplicar-decisao.yml, lancar-atestado.yml
    └── ISSUE_TEMPLATE/   ← atestado.yml, ferias.yml (gerados por gerar_form_atestado.py), config.yml
```

## Como funciona dali pra frente

**Automático:** o workflow roda sozinho domingo, segunda e terça às 3h (horário de
Ponta Porã; `cron: "0 7 * * 0,1,2"` = 07:00 UTC) — coleta no e-Visita, gera o `index.html` e publica. Você não
precisa fazer nada.

Pra mudar o horário, edite a linha `cron` no topo de
`.github/workflows/update-dashboard.yml`. O formato é `minuto hora * * dias`
em **UTC** (Ponta Porã/MS está em UTC-4, então some 4 horas ao horário local
desejado para calcular o valor em UTC).

**Manual, sob demanda:** aba **Actions → Coletar e Atualizar Dashboard → Run
workflow**. Dá pra desmarcar "Coletar dados novos" se você só quer forçar
uma nova geração do HTML sem coletar de novo (por exemplo, depois de editar
um template).

**Fallback antigo (upload manual da planilha):** ainda funciona. Suba um
`Analise_Consolidada.xlsx` novo em `data/` pela interface do GitHub — isso
dispara o workflow, mas **sem** rodar a coleta automática (só regenera o
dashboard a partir do arquivo que você subiu).

Você pode acompanhar qualquer execução na aba **Actions** — uma bolinha
amarela girando indica que está processando; verde é sucesso; vermelho é
erro (clique no workflow pra ver o log; erros de coleta geralmente são login
que falhou ou o e-Visita fora do ar; erros de geração geralmente são aba ou
coluna da planilha renomeada).

## Detecção automática de possíveis férias e paralisação coletiva

**Cada agente é avaliado a partir da PRÓPRIA primeira visita, nunca da
data mínima do sistema inteiro.** Sem isso, um agente (ou equipe inteira)
que começou a trabalhar depois do início do período rastreado — ex.: uma
atividade sazonal — teria todo o tempo ANTES de existir contado como
"dias sem lançamento", gerando férias/paralisações falsas logo no início
do período de cada um (e, como vários agentes da mesma equipe têm essa
mesma falsa ausência se sobrepondo desde o mesmo dia, isso também inflava
paralisações coletivas em bolhas de meses de duração, juntando gente que
não tinha nada a ver uma com a outra). Testei com um cenário reproduzindo
exatamente esse padrão (equipe inteira começando 8 semanas depois do
início do período) e confirmei: zero eventos falsos, tanto individuais
quanto coletivos. **Essa mesma correção também estava faltando na aba
"Ausências" em si** (não só na detecção de férias) — corrigido junto.

**Agrupamento de paralisação coletiva por interseção real, não corrente:**
o agrupamento antigo juntava um agente ao grupo se ele se sobrepusesse com
QUALQUER outro membro já no grupo — isso forma uma CORRENTE (as férias de
A tocam nas de B, as de B tocam nas de C, e o grupo vira uma bolha de
meses mesmo que A e C nunca tivessem ficado ausentes ao mesmo tempo).
Corrigido pra exigir que o grupo inteiro tenha uma interseção real (pelo
menos um dia em comum entre TODOS os membros) — testei com o cenário
exato desse bug (A toca B, B toca C, A nunca toca C) e confirmei: A agora
aparece como férias individual separada, e só B+C (que realmente se
sobrepuseram) formam um evento coletivo pequeno e preciso.

**Exclusão individual completa, mesmo dentro de um grupo coletivo:** a
correção acima trouxe um efeito colateral que também corrigi — quando 2+
agentes formam um grupo, o período do EVENTO (pra rotular/exibir) é a
interseção (o dia em comum), mas cada agente é excluído dos cálculos pelo
período INDIVIDUAL completo dele, não só pela interseção. Sem isso, um
agente cuja férias de 20 dias só tocasse a de outro por 2 dias teria só
esses 2 dias excluídos — o resto ficaria contando como ausência normal por
engano (era a causa da maioria das férias automáticas não aparecerem
direito). Testei com esse cenário exato (agente com férias de 19 dias,
outro de 11 dias, se tocando só em 5) e confirmei: cada um agora tem o
período completo excluído.

**Equipes sem detecção automática:** cadastre em
`EQUIPES_SEM_DETECCAO_AUTOMATICA`, em `scripts/coleta/deteccao.py`, o nome
de equipes que não devem passar pela detecção — por padrão, "Equipe
Bloqueio" (time pequeno, dinâmica diferente do resto, com férias
cadastradas na mão em `data/cronograma_ausencias.json`).
```python
EQUIPES_SEM_DETECCAO_AUTOMATICA = ["Equipe Bloqueio"]
```

Além do cronograma manual (acima), o sistema também **detecta sozinho**
quando um agente fica muitos dias úteis seguidos sem lançar nenhuma visita
— sem precisar que ninguém cadastre nada primeiro.

Como funciona, por agente, contando só dias úteis (pula sábado, domingo e
os feriados cadastrados em `FERIADOS_NACIONAIS`, em `scripts/coleta/deteccao.py`):

| Dias seguidos sem lançamento | O que acontece |
|---|---|
| 1 a 4 dias úteis | Aparece como "possível ausência" na aba Ausências de sempre — informativo, nada muda nos cálculos |
| 5 e 6 dias úteis | Continua só monitorando — ainda nada muda |
| 7 dias úteis ou mais (`LIMITE_DIAS_UTEIS_FERIAS = 7`) | Vira candidato a Férias. **Desde 02/11/2026 a detecção nova entra `pendente`** (continua descontando como turno sem lançamento) até a coordenação confirmar em `validar.html`/`deteccao_editor.html`. Só depois de confirmada sai dos cálculos. Voltar ao modo antigo (confirmar sozinho): `CONFIRMAR_FERIAS_AUTOMATICAMENTE = True` |

**Antes de registrar férias individuais**, o sistema
verifica se **2 ou mais agentes da mesma equipe** pararam de lançar no
mesmo período — nesse caso, em vez de registrar como férias, vira
**"possível paralisação coletiva"** (🌧️ Chuva, 📚 Capacitação, 🏢
Reunião/atividade coletiva, 📋 Outra atividade coletiva), que **fica
pendente esperando você escolher o motivo** — o sistema não adivinha
sozinho nesse caso, porque o padrão sugere outra coisa (chuva, reunião
etc.), não o agente estar de férias.

**Se não for férias/atestado de verdade** (ex.: é uma falta mesmo, não
justificada), abra **`deteccao_editor.html`**, cole o conteúdo de
`data/deteccoes_pendentes.json`, encontre o evento e clique em **"🚫 Não é
férias — marcar como falta"**. A partir daí os dias voltam a contar
normalmente (aparecem na Ausências, pesam na pontuação) — documentado como
falta, não como uma detecção esquecida. Pra desfazer, é só clicar em
"✅ Voltar a Férias" de novo.

Pra paralisação coletiva, o fluxo continua igual: escolher o motivo e
clicar em confirmar (ou "🚫 Marcar como falta", se não for nada disso).

Depois de decidir algo no editor, copie o JSON gerado e cole em
`data/deteccoes_pendentes.json` no GitHub. A decisão fica salva pra sempre
— mesmo que o período se estenda (o agente continue sem lançar), a próxima
coleta só atualiza a data final do evento, sem te pedir pra decidir de novo.

Exemplo, exatamente como pedido:
```
Agente A: 20 dias úteis no período, 5 dias de férias confirmadas
→ ranking e todos os indicadores consideram 15 dias trabalhados, não 20
```
Isso já funciona assim por como o cálculo é feito desde sempre (médias e
ranking sempre dividiram pelos dias que o agente realmente trabalhou, nunca
por um total fixo de dias do mês) — a confirmação só evita que esses dias
apareçam como "ausência não explicada" pesando na pontuação.

Na aba **Ausências**, uma tabela "🌴 Quem está de Férias, Atestado ou
Afins" mostra de forma rápida quem tem um período confirmado agora, sem
precisar abrir o Cronograma inteiro pra procurar.

## Editar cronograma — chuva, reunião, índice, ovitrampa, recuperação de casas (sem mexer em código)

**Não cadastre férias/atestado individual aqui** — o sistema já detecta e
confirma isso sozinho (ver seção acima). Use `data/cronograma_ausencias.json`
só pra coisas que o sistema NÃO tem como adivinhar sozinho: chuva, reunião,
levantamento de índice, instalação/recolha de ovitrampa, recuperação de
casas — atividades coletivas ou específicas que não são "ausência", mas
também não têm como ser inferidas automaticamente. Durante
esses períodos, o(s) agente(s) afetado(s) não contam como possível ausência
a investigar (não pesa na pontuação) e o registro aparece listado na aba
"Cronograma" do dashboard — em cima dos dias que o próprio programa já
detecta sozinho (ninguém de nenhuma equipe trabalhou naquele turno).

Cada registro tem: **quem** é afetado (um agente específico, uma equipe
inteira, ou todos os agentes — útil pra chuva ou reunião geral), o
**motivo** (sempre um destes cinco: Chuva, Folga, Atestado,
Reunião/Treinamento, Férias) e o **período** (só o dia de entrada e o dia
de saída — pra um dia só, repete a mesma data nos dois campos).

Pra editar sem tocar em código: abra **`cronograma_editor.html`** (baixe do
repositório e abra no navegador, com dois cliques — não precisa de internet
nem instalar nada). Escolha quem é afetado, o motivo (menu fixo, sem digitar
nada errado) e o período, e um botão já monta o JSON certinho pra colar em
`data/cronograma_ausencias.json` no GitHub (abrir o arquivo → ✏️ ícone de
lápis → apagar tudo → colar → Commit changes). Se o arquivo já tiver
registros antigos, cole o conteúdo dele na caixa "Carregar o que já existe"
no topo do editor antes de adicionar/remover — assim você edita a lista em
vez de começar do zero toda vez.

**Nomes de verdade no menu, em vez de só o ID:** o coletor salva
automaticamente `data/agentes_nomes.json` (ID → nome + equipe) toda vez que
roda de verdade — é a única fonte confiável dos nomes, já que eles só
existem dentro do e-Visita (o `AGENTES_POR_EQUIPE` do script só tem os IDs).
Cole o conteúdo desse arquivo na caixa "Carregar nomes dos agentes" no topo
do `cronograma_editor.html` e o menu passa a mostrar "João da Silva —
Equipe 1" em vez de "ID 116 — Equipe 1". Antes da primeira coleta rodar,
esse arquivo ainda não existe — o menu simplesmente mostra os IDs até lá.

## Planilha antiga / fora do sistema de coleta (ex.: Jan-Maio, coletada com outros parâmetros)

Se você já tem uma planilha no mesmo formato do `Analise_Consolidada.xlsx`,
mas gerada por fora do fluxo normal (outro período, outros parâmetros — por
exemplo, Janeiro a Maio/2026, rodado manualmente antes de o sistema semanal
existir), dá pra deixá-la disponível pra consulta **sem que ela entre em
nenhum cálculo** (Acumulado, filtro de semana, custos, médias — nada). Ela
fica só como uma página fixa, separada.

Passo a passo:
1. Coloque o arquivo `.xlsx` dentro de `data/historico/` (ex.:
   `data/historico/jan_a_maio_2026.xlsx`).
2. Abra `data/historico/manifest.json` no GitHub e acrescente uma entrada
   com `"origem": "manual"` — é esse campo que protege a entrada de ser
   apagada na próxima coleta automática:
   ```json
   {
     "arquivo": "jan_a_maio_2026.xlsx",
     "label": "Janeiro a Maio/2026",
     "origem": "manual"
   }
   ```
3. Pronto — na próxima geração do dashboard, ela aparece no seletor de
   período ("📅 Janeiro a Maio/2026"), com sua própria página, sem afetar o
   Acumulado nem nada mais.

**Por que fica isolada automaticamente:** o Acumulado (`acumulado.html`) só
soma o que está no cache de semanas (`data/semanas/`) — nunca lê arquivos de
`data/historico/` diretamente. E a rotina que reconstrói o histórico a cada
coleta automática (`atualizar_historico_do_cache()`) **nunca toca** em
entradas marcadas `"origem": "manual"`, só nas que ela mesma gerou
(`"origem": "cache"`) — então sua planilha antiga nunca é sobrescrita nem
apagada, mesmo rodando a coleta automática infinitas vezes depois.

## Importante: não mude os nomes das abas/colunas da planilha

O script (`scripts/xlsx_scan.py` + `scripts/generate_dashboard.py`) espera
estas abas:

- `Resumo Geral` — Agente, Equipe, Classificação, Imóveis Abertos/Fechados/Recusados, Total Geral, % Pendência, horas, custo, etc.
- `Por Área` — mesma lógica de Abertos/Fechados/Recusados, por área/agente.
- `Visitas Duplicadas`, `Visitas Suspeitas`, `Visitas Negativas`, `Fora do Expediente`, `Visitas no Almoço` — alertas (agora com coluna `Região`).
- `Ausências`
- `Cronograma` — período, motivo (Chuva/Folga/Atestado/Reunião-Treinamento/Férias), quem foi afetado. Aparece como aviso no topo da Visão Geral.
- `Recusados e Pendências` — tem **duas tabelas na mesma aba** (resumo de pendência por agente + detalhe dos imóveis recusados). Vira a aba **Pendências** do dashboard.
- `Ponto Estratégico` — acompanhamento semanal de um agente/local especial. Vira a aba **Ponto Estratégico** do dashboard. Linhas com "Selecione" no campo Agente (placeholder de dropdown vazio) são ignoradas automaticamente.

Como a coleta agora é automática e gera a planilha com a mesma lógica de
sempre (`scripts/coletar_evisita.py` é o mesmo script de antes, só ajustado
pra rodar sem interface gráfica), isso não deve mudar no dia a dia. Vale só
se você decidir editar `coletar_evisita.py` e sem querer renomear uma coluna
ou aba de saída — a geração quebra com um erro do tipo
`KeyError: 'Nome da Coluna'`.

## Ajustes manuais de pontuação (`data/ajustes_ranking.json`)

Para dar ou tirar pontos de um agente com justificativa (aparece no Extrato e na
coluna de detalhes como "Ajuste manual: motivo"), adicione itens à lista:

```json
[
  {"id_agente": 116, "data": "15/10/2026", "pontos": 2.0, "motivo": "Ação extra autorizada pela coordenação"}
]
```

- `pontos` positivo soma, negativo desconta (sem fator de normalização).
- O ajuste só vale no mês cuja janela contém a `data`.
- Itens inválidos são ignorados com aviso no log; `validar_json.py` também aponta.
- **Só afeta meses regenerados** (Outubro/Novembro). Meses arquivados não são recalculados.

## Meses congelados (Julho a Setembro/2026)

Os meses fechados ficam em `data/meses_arquivados.json` (lido por `scripts/meses_arquivados.py`;
o botão **Fechar mês** da página `validar.html` grava ali) e marcados
`origem: "manual"` no `manifest.json`: o pipeline **não** recalcula nem reescreve
essas planilhas, então os números publicados não mudam.

- **05/11/2026:** Julho a Setembro foram reabertos, recalculados com as regras atuais e congelados de novo
  (a nota subiu 6 a 8 pts em média; planilhas antigas em `data/historico/backup_congelado/*_antes-das-regras-novas.xlsx`).
- **Corrigir um mês antigo (rótulo, regra nova, bug de cálculo): workflow "Regenerar mês congelado".**
  > ⚠️ **Pendente:** se a aba Actions ainda não mostra esse workflow, o arquivo ainda está em `docs/pendentes/` (o token do assistente
  > não tinha o escopo `workflow`). Instruções em `docs/pendentes/LEIA-ME.md`. O script local (`scripts/regenerar_mes.py`) já funciona.
  Aba Actions → *Regenerar mês congelado* → Run workflow → `mes` = `Setembro/2026` (ou `todos`).
  Desmarque **aplicar** para só simular: o resumo da execução mostra quantos agentes sobem/descem e
  quantas posições mudam, sem gravar nada. Com **aplicar**, ele guarda a planilha antiga em
  `data/historico/backup_congelado/*_antes-da-regeneracao-<data>.xlsx`, refaz o mês a partir do cache
  (`data/semanas/`, sem e-Visita), congela de novo, confere que os outros meses congelados ficaram
  intactos e aciona o `update-dashboard` (`rodar_coleta=false`) para gerar as páginas e publicar.
  Ficam só os 3 backups mais recentes de cada mês (`*_antes-da-regeneracao-*`); os de outros nomes não são apagados.
  Local: `python scripts/regenerar_mes.py "Setembro/2026"` (ou `todos`; `--sem-acumulado` pula o Analise_Consolidada).
  O mês só pode ser refeito se **todas** as semanas dele estiverem em `data/semanas/`.
  Ele reabre **um mês por vez, em ordem cronológica**, porque o desempate do ranking usa a média dos meses
  anteriores lida do `manifest.json`: sem isso, quem empata na nota ficaria na posição errada.
- Para reabrir um mês fechado pela página: aba **Fechar mês → Reabrir** (digite o nome do mês;
  cópia de segurança automática). Julho–Setembro seguem congelados; só o desenvolvedor reabre.
- **Depois da semana 330:** feche Outubro pela aba **Fechar mês** (ou `python scripts/fechar_mes.py fechar "Outubro/2026"`).

---

## Lançar atestado pelo GitHub (formulário pré-preenchido)

**Jeito mais fácil:** abra `atestado.html` no site publicado
(`https://lucsdevpro.github.io/sentinelaprime/atestado.html`), escolha o agente e as
datas (já vêm com hoje) e clique em **Abrir formulário já preenchido**. O GitHub abre com
tudo preenchido; basta clicar em *Submit new issue*.

Também dá para ir em **Issues → New issue → Lançar atestado**.

O que acontece depois (`.github/workflows/lancar-atestado.yml`):
1. Confere agente e datas. Se algo estiver errado, comenta na issue e **não grava nada**.
2. Acrescenta `{"alvo":"agente","id_agente":N,"motivo":"Atestado",...}` em
   `data/cronograma_ausencias.json` (repetir o mesmo pedido não duplica).
3. Faz o commit, dispara a atualização do site (sem recoletar no e-Visita), comenta e fecha a issue.

Regras e cuidados:
- Só dono, membros e colaboradores do repositório conseguem lançar (outras issues são ignoradas).
- O formulário **não pede CID nem diagnóstico**; só ficam datas e o rótulo "Atestado".
  Se o repositório for público, o nome do agente fica visível na issue — prefira repositório privado.
- Atestado lançado tira os dias de "Turno sem lançamento" e dos dias esperados: **não desconta ponto**.
- Entrou ou saiu agente? Rode `python scripts/gerar_form_atestado.py` e envie o
  `.github/ISSUE_TEMPLATE/atestado.yml` atualizado.
- Para desfazer um lançamento errado, remova a linha em `data/cronograma_ausencias.json`
  (ou use o `cronograma_editor.html`).

---

### Lançar, ajustar ou cancelar férias (formulário no GitHub)

Em `atestado.html` escolha **Férias — definir ou ajustar** ou **Férias — cancelar** (ou vá em
Issues → New issue → "Férias (definir, ajustar ou cancelar)"). O workflow `lancar-atestado.yml`:

- **Definir/ajustar:** o período informado vira o período final das férias (máx. 30 dias). Se já havia férias
  detectadas tocando o período, são ajustadas; senão cria uma nova. O ajuste fica protegido
  (`ajustado_manual`): a detecção automática não estica nem encolhe mais.
- **Cancelar:** os dias informados viram **falta**; o que sobrar fora do período continua como férias.
- O tipo é reconhecido pelo próprio formulário (não depende de labels existirem no repositório).
- Entrada de férias ajustada à mão sempre vence a detecção; dias fora dela, sem trabalho, contam como falta.
- Entrou/saiu agente? Rode `python scripts/gerar_form_atestado.py` e envie os dois `.yml` de `.github/ISSUE_TEMPLATE/`.

### Cuidado ao copiar para o GitHub

`.github` é pasta oculta. Os arquivos devem ficar exatamente em `.github/workflows/*.yml` e
`.github/ISSUE_TEMPLATE/*.yml`. Cópias em `.github/workflows/workflows/` ou
`.github/workflows/ISSUE_TEMPLATE/` **não funcionam** (apague).

