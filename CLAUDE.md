# Sentinela Prime — guia rápido para o Claude

Leia ESTE arquivo primeiro. Depois, só se precisar: `docs/REGRAS.md` (regras de negócio), `docs/DECISOES.md` (decisões por data; o fim do arquivo é um
histórico longo de sessões, leia só o topo) e `docs/MAPA.md` (índice função → linha; os maiores arquivos têm 600 a 1.400 linhas, **não leia inteiros**: use `grep -n` / `sed -n 'A,Bp'`).
Manuais longos (não leia por padrão): `docs/OPERACAO.md`, `docs/INSTALACAO.md`, `docs/REGRAS_DETALHADAS.md`; o `README.md` é só um resumo.

## O que é
Dashboard de monitoramento das visitas dos agentes de campo (e-Visita) de Ponta Porã/MS. Idioma: **português do Brasil**
(código, commits, textos). Publicado como site estático no GitHub Pages.

## Fluxo (GitHub Actions `update-dashboard.yml`: dom/seg/ter 07:00 UTC + botão "Run workflow")
```
e-Visita ──Selenium──▶ data/semanas/NNN.xlsx (cache por semana)
   scripts/coletar_evisita.py ─▶ data/Analise_Consolidada.xlsx (acumulado) + data/historico/semanas_AAA-BBB.xlsx (1 por mês)
   scripts/generate_dashboard.py + scripts/templates/ (Jinja2) ─▶ index.html, acumulado.html, historico/*.html, partes/
Editores (validar/deteccao/cronograma/home .html) ─▶ Worker Cloudflare (worker/index.js) ─▶ repository_dispatch
   ─▶ scripts/aplicar_decisao.py / lancar_ausencia.py / lancar_atestado.py ─▶ data/*.json
```

## Onde fica cada coisa
| Quero mexer em… | Arquivo (função/constante) |
|---|---|
| Pontuação e pesos (PONTOS_*) | `scripts/coleta/pontos.py` (constantes) e `scripts/coleta/calculos.py` → `calcular_pontuacao` |
| Turno sem lançamento / Possível Evento | `coleta/ausencias_ranking.py` → `_preparar_ausencias`; `coleta/pontos.py` → `LIMITE_AGENTES_EVENTO_TURNO`, `EVENTO_COLETIVO_A_PARTIR_DE` |
| Ranking e dias esperados | `coleta/ausencias_ranking.py` → `_preparar_ranking`; `coleta/pontos.py` → `RANKING_SEM_NORMALIZACAO_A_PARTIR_DE` |
| Detecção automática férias/chuva | `coleta/deteccao.py` → `detectar_ausencias_e_paralisacoes`, `atualizar_deteccoes_pendentes`; `CONFIRMAR_*_AUTOMATICAMENTE` em `coleta/pontos.py` |
| Cronograma (justificativas) | `data/cronograma_ausencias.json`, `_obter_motivo_cronograma` (`coleta/auxiliares.py`), `MOTIVOS_CRONOGRAMA` (`coleta/parametros.py`) |
| Agentes, equipes, ciclos, meses | `AGENTES_POR_EQUIPE`, `CICLOS_TRATAMENTO`, `MESES_OFICIAIS` (`coleta/parametros.py`); nomes em `data/agentes_nomes.json` (automático); depois rode `python3 scripts/gerar_form_atestado.py` |
| Painel Custos & Produtividade | `scripts/generate_dashboard.py` (`build_kpi_custos`, `build_custos_*`) + `scripts/templates/sections/custos.html` |
| Visual (CSS / JS) do dashboard gerado | `scripts/style.css`, `scripts/bootstrap.js`, `scripts/templates/charts.js` |
| Páginas editáveis da raiz (`validar`, `deteccao_editor`, `cronograma_editor`, `home_editor`, `agente`, `comparar`, `projecao`) | o `.html` só tem a estrutura; o código fica em `assets/<nome>.js` e `assets/<nome>.css` (o `sw.js` guarda `validar.js/.css` na casca offline: se renomear, atualize `ARQUIVOS` e suba o `CASCA`) |
| Abas do dashboard | `scripts/templates/sections/*.html` (uma por aba), `base.html` |
| Meses fechados/abertos | `data/meses_arquivados.json`, `data/historico/manifest.json`, `scripts/fechar_mes.py` |
| Refazer um mês congelado (corrigir meses antigos) | workflow `regenerar-mes.yml` → `scripts/regenerar_mes.py` (um mês por vez, cronológico; guarda backup) |

## Coletor (`scripts/coletar_evisita.py` é só a fachada; o código está em `scripts/coleta/`)
Camadas (cada módulo só importa dos anteriores): `parametros` → `pontos` → `auxiliares` → `deteccao` → `sessao` (Selenium/HTTP) → `calculos` → `colunas`
→ `estilo_excel` → `abas` → `ausencias_ranking` → `saida_excel` → `processamento` → `cache_semanas` → `consolidacao` → `historico` → `execucao` (`main`).
`import coletar_evisita as C` continua valendo para tudo (`C.calcular_pontuacao`, `C.CPF`...). Achar uma função: `grep -n "def nome" scripts/coleta/*.py` ou `docs/MAPA.md`.

## Comandos
```bash
./scripts/rodar_testes.sh                 # 13 testes Python do CI, uma linha cada (~30 s). Rode antes de todo commit.
node worker/test_worker.mjs               # testes do Worker (também no CI)
python3 scripts/generate_dashboard.py data/historico/semanas_327-330.xlsx _teste.html   # página de teste (Outubro)
python3 tools/shot.py _teste.html custos  # screenshot claro/escuro + erros de JS (precisa playwright)
python3 scripts/gerar_mapa.py             # atualiza docs/MAPA.md depois de mexer em funções
```
Depois de gerar `_teste.html`, **apague** `_teste.html` e `partes/_teste*` (não commitar).

## Convenções
- **Nunca edite à mão** arquivos gerados: `index.html`, `acumulado.html`, `transparencia.html`, `historico/*.html`, `partes/*`,
  `assets/agentes_dados.js`, `data/Analise_Consolidada.xlsx`, `data/historico/*.xlsx`, `data/semanas/*`, `data/csv/*`.
  Mudou o código/template → o workflow regenera. O bot faz commits "Atualiza coleta e dashboard automaticamente": sempre `git pull --rebase` antes de push.
- Agente é identificado por **ID**, nunca por nome, em qualquer lógica (nomes podem repetir).
- Regra nova → constante com nome claro + comentário do porquê + teste em `scripts/test_*.py` + linha em `docs/DECISOES.md`.
- Dados públicos: nunca gravar CID/diagnóstico (atestado = "Ausência justificada").
- Variáveis de ambiente: modelo em `.env.example` (`.env` é ignorado pelo Git; o coletor lê do ambiente, sem python-dotenv).
- Token do GitHub: usar só em URL temporária de push (`https://x-access-token:TOKEN@github.com/...`), nunca gravar no remote. Alterar `.github/workflows/*` exige permissão "Workflows" no token.

## Armadilhas conhecidas
- Mês ≠ mês civil: Outubro = semanas 327–330 (a semana de 04/10 abre o mês; 01–02/10 ainda são da semana 326/Setembro).
  Julho 313–317 · Agosto 318–321 · Setembro 322–326 · Outubro 327–330.
- Ranking sem normalização: vale para todo período de até 45 dias (todos os meses); o Acumulado (>45 dias) segue no método antigo. Detecção de férias dispara com `LIMITE_DIAS_UTEIS_FERIAS = 7` dias úteis e as detecções novas de férias/chuva entram **pendentes** (`CONFIRMAR_*_AUTOMATICAMENTE = False` em `coleta/pontos.py`); os comentários do código já descrevem isso.
- Os testes `scripts/test_*.py` importam `coletar_evisita`, que importa `coleta/sessao.py` (único módulo com `selenium`): sem `pip install -r requirements.txt` quase todos falham no import.
- Atribuir `C.X = valor` na fachada (como os testes fazem) repassa o valor aos módulos que possuem `X`; em código novo, prefira passar parâmetro a mudar variável de módulo.
- Equipes sob demanda (`EQUIPES_SEM_DETECCAO_AUTOMATICA`: Bloqueio, Ponto Estratégico) ficam fora das regras de evento; a Equipe Bloqueio também fica fora do painel de custos.
- Nas planilhas, a 1ª tabela de cada aba termina na primeira linha em branco (as legendas vêm depois): leia só até aí.
- Arquivos grandes: `.claude/settings.json` bloqueia a leitura dos gerados (`index.html`, `acumulado.html`, `historico/`, `partes/`, `data/semanas|csv|historico`, `data/*.xlsx`, fotos). Para dados, use `python3`/`jq` filtrando; `data/deteccoes_pendentes.json` tem ~2,4 mil linhas, não leia inteiro.
