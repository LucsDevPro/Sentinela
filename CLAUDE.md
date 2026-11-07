# Sentinela Prime — guia para o Claude

Leia ESTE arquivo primeiro; as regras de cada área carregam sozinhas de `.claude/rules/` quando você abre arquivos dela.
Só abra outros docs se precisar: `docs/REGRAS.md` (regras de negócio) · topo de `docs/DECISOES.md` (decisões por data; o fim é histórico longo) · `docs/MAPA.md` (função → linha).
Não leia por padrão: `docs/OPERACAO.md`, `INSTALACAO.md`, `REGRAS_DETALHADAS.md`. O `README.md` é só resumo.

## O que é
Dashboard das visitas dos agentes de campo (e-Visita) de Ponta Porã/MS, site estático no GitHub Pages. Idioma de código, commits e textos: **português do Brasil**.

## Fluxo (workflow `update-dashboard.yml`: dom/seg/ter 07:00 UTC + "Run workflow")
```
e-Visita ─Selenium▶ data/semanas/NNN.xlsx ─▶ data/Analise_Consolidada.xlsx + data/historico/semanas_AAA-BBB.xlsx
generate_dashboard.py + scripts/templates/ (Jinja2) ─▶ index.html, acumulado.html, historico/, partes/
Editores .html ─▶ Worker Cloudflare ─▶ repository_dispatch ─▶ scripts/aplicar_decisao|lancar_*.py ─▶ data/*.json
```

## Onde mexer
| Quero alterar… | Onde |
|---|---|
| Pontuação e pesos | `coleta/pontos.py` (constantes) + `coleta/calculos.py` → `calcular_pontuacao` |
| Turno sem lançamento / Evento | `coleta/ausencias_ranking.py` → `_preparar_ausencias`; constantes em `pontos.py` |
| Ranking e dias esperados | `coleta/ausencias_ranking.py` → `_preparar_ranking` |
| Detecção de férias/chuva | `coleta/deteccao.py`; `CONFIRMAR_*_AUTOMATICAMENTE` em `pontos.py` |
| Cronograma / justificativas | `data/cronograma_ausencias.json`, `coleta/auxiliares.py`, `MOTIVOS_CRONOGRAMA` (`parametros.py`) |
| Agentes, equipes, ciclos, meses | `coleta/parametros.py`; nomes em `data/agentes_nomes.json`; depois `python3 scripts/gerar_form_atestado.py` |
| Painel Custos | `generate_dashboard.py` (`build_kpi_custos`, `build_custos_*`) + `templates/sections/custos.html` |
| Visual / abas | `scripts/style.css`, `bootstrap.js`, `templates/charts.js`, `templates/sections/*.html`, `base.html` |
| Páginas editáveis da raiz | `.html` só tem estrutura; código em `assets/<nome>.js/.css` |
| Meses fechados | `data/meses_arquivados.json`, `data/historico/manifest.json`, `scripts/fechar_mes.py` |
| Refazer mês congelado | workflow `regenerar-mes.yml` → `scripts/regenerar_mes.py` (um mês por vez, em ordem) |

Achar função: `grep -n "def nome" scripts/coleta/*.py` ou `docs/MAPA.md`. Arquivos têm até 1.400 linhas: **não leia inteiros**, use `grep -n` / `sed -n 'A,Bp'`.

## Comandos
```
pip install -r requirements.txt          # obrigatório: quase todo teste importa selenium
python3 scripts/rodar_testes.py [filtro] [-v]   # testes Python (~20 s, roda no Windows). Antes de todo commit. (rodar_testes.sh só chama este)
node worker/test_worker.mjs              # testes do Worker
python3 scripts/generate_dashboard.py data/historico/semanas_327-330.xlsx _teste.html   # página de teste (~2 s)
python3 scripts/gerar_mapa.py            # atualiza docs/MAPA.md (--check só verifica)
python3 scripts/regerar_paginas.py       # regera TODAS as páginas a partir dos dados (~20 s); --so-home só o index
python3 scripts/resumo.py meses|deteccoes|ranking|cronograma|manifest   # consultas curtas: use em vez de ler JSON/xlsx
python3 scripts/regenerar_mes.py "Setembro/2026"   # refaz um mês congelado (ou `todos`); veja docs/OPERACAO.md
python3 tools/comparar_saidas.py         # refatorou o gerador? exige saída idêntica à do HEAD (--autoteste prova que pega erro)
```
Depois de gerar `_teste.html`, **apague** `_teste.html` e `partes/_teste*`.

## Regras que valem sempre
- **Nunca edite à mão** os gerados: `index.html`, `acumulado.html`, `transparencia.html`, `historico/*`, `partes/*`, `assets/agentes_dados.js`, `data/Analise_Consolidada.xlsx`, `data/historico/*.xlsx`, `data/semanas/*`, `data/csv/*`. Mudou código/template → o workflow regenera.
- Agente = sempre por **ID**, nunca por nome.
- Regra nova = constante com nome claro + comentário do porquê + teste em `scripts/test_*.py` + linha em `docs/DECISOES.md`.
- Repositório público: nunca gravar senha, token, CID ou diagnóstico (atestado = "Ausência justificada"). `.env` fora do Git (modelo: `.env.example`).
- O bot também commita ("Atualiza coleta e dashboard automaticamente"): sempre `git pull --rebase` antes de push.
- Token do GitHub só em URL temporária de push, nunca no remote.

## Armadilhas
- Mês ≠ mês civil: Outubro = semanas 327–330 (a semana de 04/10 abre o mês).
- Detecções novas de férias/chuva entram **pendentes** (`CONFIRMAR_*_AUTOMATICAMENTE = False`).
- Leitura bloqueada em `.claude/settings.json` (gerados e `deteccoes_pendentes.json`). Para dados, use `python3`/`jq` filtrando.
