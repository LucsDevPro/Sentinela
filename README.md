# Dashboard de Monitoramento de Visitas — Ponta Porã (S E N T I N E L A - HUB)

Este repositório agora faz o processo **inteiro sozinho**: coleta os dados no
e-Visita, gera o `index.html` do dashboard e publica no GitHub Pages — tudo
automaticamente, segunda/terça/quinta de madrugada, sem precisar rodar nada na sua máquina nem
subir planilha manualmente.

Continua funcionando também o jeito antigo (subir uma `Analise_Consolidada.xlsx`
manualmente em `data/`) como alternativa/backup, caso a coleta automática
falhe ou você precise reprocessar um dado específico.

**Página inicial configurável + aba "Acumulado":** o `index.html` (home)
mostra o período definido em `data/config_home.json` — por padrão, Julho/2026
(`{"arquivo": "data/historico/semanas_313-317.xlsx", "label": "Julho/2026"}`).
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
  4. Reconstrói `data/historico/` a partir do cache — agrupado por mês até
     Julho/2026; a partir de Agosto/2026, cada semana fechada vira sua
     própria página (mais detalhe, e dá pra revisar a última semana isolada,
     sem misturar com o resto do mês). Ver `PRIMEIRA_SEMANA_DETALHE_SEMANAL`
     em `scripts/coletar_evisita.py` se quiser mudar esse ponto de corte.

Na primeira execução (`data/semanas/` vazio), o script coleta da semana
18/2026 (HTML 305, início de Maio) até a semana atual, uma planilha por
semana. O `data/semanas/` é commitado no repositório junto com o resto — é
ele que guarda "até onde já coletamos" de uma execução pra outra.

**Ciclos diferentes por semana:** o `id_ciclo` usado na consulta ao e-Visita
não é fixo — muda em pontos específicos do ano. Isso já está mapeado em
`CICLOS_TRATAMENTO`, em `scripts/coletar_evisita.py`:
```python
CICLOS_TRATAMENTO = [
    (305, 312, 162),  # semanas 305-312 (maio-junho/2026) usam id_ciclo 162
    # a partir da semana 313 em diante, usa o ID_CICLO padrão (163)
]
```
Se o site mudar de ciclo de novo no futuro, adicione uma nova linha aqui — o
formato é `(semana_inicio_html, semana_fim_html, id_ciclo)`.

Pra recoletar manualmente só uma semana específica (ex.: corrigir um dado):
```
python scripts/coletar_evisita.py --semana 305
```
(305 é o HTML ID da semana — ver `scripts/semanas_evisita.py` pra converter
entre HTML ID e "Semana do Ano".)

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

## Estrutura do repositório

```
.
├── data/
│   ├── Analise_Consolidada.xlsx      ← acumulado de tudo, gerado automaticamente pela coleta
│   ├── config_home.json              ← qual período aparece na home (edite com home_editor.html)
│   ├── cronograma_ausencias.json     ← chuva/folga/atestado/reunião/férias (edite com cronograma_editor.html)
│   ├── agentes_nomes.json            ← ID → nome de cada agente, salvo automaticamente pelo coletor
│   ├── semanas/                     ← cache de cada semana coletada (uma planilha por semana)
│   └── historico/                   ← planilhas + manifest.json de cada mês arquivado
├── index.html                       ← home (período de data/config_home.json)
├── acumulado.html                   ← soma de TODAS as semanas já coletadas
├── home_editor.html                 ← editor visual pra escolher o período da home (abra no navegador)
├── cronograma_editor.html           ← editor visual do cronograma (abra no navegador)
├── assets/
│   └── logo_ponta_pora.png
├── scripts/
│   ├── coletar_evisita.py           ← faz login e coleta os dados do e-Visita (novo)
│   ├── generate_dashboard.py        ← carrega a planilha e prepara os dados
│   ├── xlsx_scan.py                 ← separa tabelas empilhadas dentro de uma aba
│   ├── style.css
│   ├── bootstrap.js
│   ├── chart.umd.js
│   └── templates/                   ← todo o HTML do dashboard mora aqui
│       ├── base.html                ← estrutura geral da página
│       ├── macros.html              ← componentes reutilizáveis (kpi, gráfico, tabela de alerta)
│       ├── charts.js                ← instancia os gráficos Chart.js com os dados
│       └── sections/                ← um arquivo por aba
│           ├── visao_geral.html
│           ├── agentes.html
│           ├── equipes.html
│           ├── areas.html
│           ├── alertas.html
│           ├── ausencias.html
│           ├── pendencias.html
│           ├── ponto_estrategico.html
│           └── custos.html
├── .github/workflows/
│   └── update-dashboard.yml         ← coleta + gera + publica, tudo em um workflow
├── requirements.txt
└── index.html                       ← gerado automaticamente, não edite à mão
```

## Passo a passo — configurar pela primeira vez

### 1. Criar o repositório no GitHub
1. Entre em [github.com/new](https://github.com/new).
2. Dê um nome, ex.: `dashboard-visitas`.
3. Deixe **Public** (necessário para o GitHub Pages gratuito) ou **Private**
   se você tiver GitHub Pro/Team/Enterprise.
4. Não marque nenhuma opção de inicialização (README, .gitignore etc.) —
   vamos enviar os arquivos prontos.
5. Clique em **Create repository**.

### 2. Enviar estes arquivos para o repositório
A forma mais simples, sem instalar nada:
1. Na página do repositório recém-criado, clique em **uploading an existing file**.
2. Arraste **todas** as pastas e arquivos deste pacote (mantendo a estrutura
   de pastas: `data/`, `assets/`, `scripts/`, `.github/`, `requirements.txt`).
   O GitHub aceita arrastar pastas inteiras direto do seu computador.
3. Escreva uma mensagem de commit (ex.: "Primeira versão") e clique em
   **Commit changes**.

*(Se preferir usar Git pela linha de comando, veja a seção "Via linha de
comando" mais abaixo.)*

### 3. Cadastrar o CPF e a senha do e-Visita como Secrets

**Nunca coloque CPF/senha direto no código** — o repositório é público, então
qualquer texto commitado fica visível pra qualquer pessoa. O script já lê as
credenciais de variáveis de ambiente; no GitHub isso vem dos **Secrets**:

1. No repositório, vá em **Settings → Secrets and variables → Actions**.
2. Clique em **New repository secret**.
3. Crie um secret chamado `EVISITA_CPF` com o CPF de login.
4. Crie outro chamado `EVISITA_SENHA` com a senha.

> ⚠️ Se essa senha já foi compartilhada em algum chat, e-mail ou documento
> fora de um cofre de senhas, o ideal é trocá-la no e-Visita antes de seguir
> — trate-a como exposta.

### 4. Dar permissão de escrita para o workflow
1. No repositório, vá em **Settings → Actions → General**.
2. Em **Workflow permissions**, marque **Read and write permissions**.
3. Clique em **Save**.

*(Isso é necessário porque o workflow precisa commitar a planilha nova e o
`index.html` atualizado de volta no repositório.)*

### 5. Ativar o GitHub Pages
1. Vá em **Settings → Pages**.
2. Em **Source**, selecione **GitHub Actions** (não "Deploy from a branch").
3. Pronto — não precisa configurar mais nada aqui.

### 6. Rodar a primeira vez
1. Vá na aba **Actions** do repositório.
2. Clique no workflow **Coletar e Atualizar Dashboard** na lista à esquerda.
3. Clique em **Run workflow**. Deixe a opção "Coletar dados novos no e-Visita"
   marcada e confirme.
4. Aguarde — a coleta de todos os agentes pode levar alguns minutos (é a
   mesma coleta que já era feita, só que rodando no GitHub em vez da sua
   máquina). Quando os passos `build` e `deploy` ficarem verdes, vá em
   **Settings → Pages** — o link do seu dashboard vai aparecer no topo, algo
   como: `https://SEU-USUARIO.github.io/dashboard-visitas/`

## Como funciona dali pra frente

**Automático:** o workflow roda sozinho segunda, terça e quinta às 3h (horário de
Ponta Porã) — coleta no e-Visita, gera o `index.html` e publica. Você não
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

## Editar cronograma — chuva, folga, atestado, reunião/treinamento, férias (sem mexer em código)

Tudo isso fica num único arquivo, `data/cronograma_ausencias.json`. Durante
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

## Testar localmente antes de subir (opcional)

Se tiver Python instalado:

```bash
pip install -r requirements.txt

# Coleta (precisa das credenciais como variável de ambiente):
export EVISITA_CPF="seu-cpf"
export EVISITA_SENHA="sua-senha"
python scripts/coletar_evisita.py --saida data

# Geração do HTML:
python scripts/generate_dashboard.py
```

Isso gera o `index.html` na raiz do projeto — só abrir no navegador para
conferir antes de enviar para o GitHub.

## Via linha de comando (alternativa ao passo 2)

```bash
git init
git add .
git commit -m "Primeira versão"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/dashboard-visitas.git
git push -u origin main
```
