# Prompt: dividir `scripts/generate_dashboard.py` sem quebrar nada

> Cole tudo abaixo da linha no Claude Code, na raiz do repositório. Foi escrito a partir de uma análise do código real (60 funções, 36 globais, 1.427 linhas) e de uma rede de testes que já existe em `tools/comparar_saidas.py`.

---

## Objetivo
Dividir `scripts/generate_dashboard.py` em um pacote `scripts/dashboard/`, **sem mudar nenhum byte da saída** (`index.html`, `acumulado.html`, `historico/*.html`, `partes/*`). Isto é uma refatoração pura: **proibido** corrigir bug, renomear função, "melhorar" lógica ou mexer em template, CSS ou JS.

## Regra de ouro
Mover = recortar e colar a função **inteira, sem alterar o corpo**. As únicas edições permitidas dentro de uma função movida são o qualificador de nomes de configuração (`XLSX_PATH` → `cfg.XLSX_PATH`) e os imports no topo do módulo novo.

## Passo 0 — Rede de segurança (obrigatório antes de mexer em código)
1. `git checkout -b refator-dashboard` e `pip install -r requirements.txt pyflakes`.
2. `./scripts/rodar_testes.sh` → **15 de 15 verdes** (anote). Se algum falhar, PARE.
3. `python3 tools/comparar_saidas.py` → **"SAÍDA IDÊNTICA"** contra `HEAD` (confirma a linha de base; ~30 s).
4. `python3 -m pyflakes scripts/generate_dashboard.py` → sem saída (linha de base limpa).
5. `python3 tools/comparar_saidas.py --autoteste` → "Autoteste passou" (prova que o comparador pega erro).

## Portão de cada etapa (rode ao FIM DE CADA ETAPA, antes do commit)
```
python3 -m pyflakes scripts/generate_dashboard.py scripts/dashboard/   # zero avisos (pega NameError em ramos raros)
./scripts/rodar_testes.sh                                              # 15 de 15
python3 tools/comparar_saidas.py                                       # SAÍDA IDÊNTICA (compara com o HEAD anterior)
```
Um commit por etapa, mensagem `refator(dashboard): <etapa>`. Se o portão falhar: **não avance e não "conserte por cima"**; `git checkout -- .` e refaça a etapa. Por que pyflakes: a matriz de saída exercita só ~88% das linhas; os 12% restantes são tratamento de erro e casos raros, onde um import esquecido só estoura em produção.

## Estrutura final e dono de cada nome
`scripts/dashboard/__init__.py` fica **vazio** (sem imports, para não criar efeito colateral de ordem).

| Módulo | Conteúdo exato |
|---|---|
| `config.py` | `ROOT`, `SCRIPTS_DIR`, `LAZY`, `DIAS_UTEIS_MES_REF`, `META_VISITAS_DIA_REF`, `TETO_VISITA_MIN`, `CUSTO_FAIXA_MEDIO`, `CUSTO_FAIXA_ALTO`, `HORAS_UTEIS_BAIXO`, `HORAS_UTEIS_ALTO`, `CUSTO_GRAFICO_MAX`, `OUTRAS_ATIVIDADES_PATH`, `CONFIG_HOME_PATH`, `ACUMULADO_XLSX`, `resolver_home_xlsx`, `HOME_XLSX`, `XLSX_PATH`, `OUT_PATH`, `SALARIO_MENSAL`, `EVISITA_URL`, `DIA_ORDER`, `EQUIPE_BLOQUEIO`, `TEAM_COLORS`, `LABEL_MES_RE` — **na mesma ordem e com os mesmos comentários** |
| `colunas.py` | `RESUMO_COLS`, `AREA_COLS`, `ALERT_COLS`, `AUSENCIA_COLS`, `PENDENCIA_COLS`, `PE_COLS`, `RESUMO_SEMANAL_COLS`, `RANKING_COLS`, `RANKING_DET_COLS`, `_NAO_PADRONIZAR_TEXTO` |
| `formatters.py` | `br`, `class_key`, `badge`, `row_class`, `rank_class_key`, `rank_badge`, `id_link`, `parse_custo`, `parse_br_date`, `n`, `cap_first`, `ranking_sem_nan`, `records`, `sem_bloqueio`, `somente_bloqueio`, `_classe_por_pontos`, `_sparkline`, `enxugar_html`, `_BLOCOS_LITERAIS_RE`, `_ESPACOS_RE` |
| `leitura_rapida.py` | `_ler_tabela_rapida`, `_num`, `_ler_presenca`, `_ler_ranking_rapido`, `_meses_historico` |
| `custos.py` | `_PRESENCA_CACHE`, `_presenca_da_pagina`, `_preparar_custos`, `_custos_base`, `adicionar_custo_real`, `_custo_ritmo_agregado`, `_custo_real_agregado`, `_custo_visita_agregado`, `_faixa_custo`, `_faixa_presenca`, `build_kpi_custos`, `build_custos_rows`, `build_custos_equipes`, `build_custos_mensais`, `carregar_outras_atividades` |
| `ranking.py` | `build_kpi_ranking`, `build_extratos`, `build_media_mensal`, `_ids_por_nome`, `_periodo_label`, `_worker_url`, `_mes_contestavel` |
| `context.py` | `build_context`, `build_cronograma_rows`, `build_kpi_geral`, `build_ausencias_agg`, `build_team_cards`, `build_chart_data`, `compute_all_absent` |
| `navegacao.py` | `carregar_periodos`, `carregar_nav_semanas`, `periodo_em_andamento`, `_selo_periodo`, `build_comparacao_semanal` |
| `loaders.py` | `primeira_tabela`, `load_all` |
| `generate_dashboard.py` | só os imports, a fachada (abaixo) e `main()` + `if __name__ == "__main__"` |

Ordem de import, da base para o topo (verificada sem ciclos): `colunas → config → formatters → leitura_rapida → custos → ranking → context → navegacao → loaders → generate_dashboard`. **Nenhum módulo importa de um que vem depois dele nessa lista.** `_ler_*` NÃO vão para `loaders` e `_presenca_da_pagina` fica em `custos`: o desenho "loaders + custos" cria o ciclo `loaders ↔ custos` (`load_all` chama `adicionar_custo_real`, e `custos` lê as planilhas).

## Armadilhas que você DEVE tratar (cada uma já causaria bug silencioso)
1. **Configuração mutável.** `XLSX_PATH`, `OUT_PATH`, `ROOT`, `CONFIG_HOME_PATH` e `SALARIO_MENSAL` são lidos em vários módulos, e `scripts/test_semanal.py` (linhas 62–84) faz `G.OUT_PATH = …`, `G.ROOT, G.CONFIG_HOME_PATH = …`. Regra: em todo módulo novo use `from dashboard import config as cfg` e leia `cfg.OUT_PATH` **no momento da chamada**. **Proibido** `from dashboard.config import OUT_PATH` (congela o valor e o teste passaria a testar nada, ou pior, passaria sem testar).
2. **Fachada que repassa atribuições.** Em `generate_dashboard.py`, reexporte todos os nomes movidos (`from dashboard.custos import …` explícito, sem `*`) e copie o padrão `_Fachada` de `scripts/coletar_evisita.py` (linhas 40–70): `G.X = valor` deve atualizar `X` em `config` (e em qualquer módulo do pacote que o possua). `G.sem_evisita` também precisa continuar existindo (o teste usa). Quem importa `generate_dashboard as G` não pode notar diferença.
3. **`ROOT`/`SCRIPTS_DIR` dependem de `__file__`.** Em `scripts/dashboard/config.py` o `parent` muda de nível: `ROOT = Path(__file__).resolve().parent.parent.parent` e `SCRIPTS_DIR = Path(__file__).resolve().parent.parent`. Se errar um nível, o gerador lê `data/` e `templates/` do lugar errado.
4. **`sys.argv` é lido na importação.** `XLSX_PATH`/`OUT_PATH` vêm de `sys.argv[1]`/`[2]` ao importar `config`; `resolver_home_xlsx()` também roda na importação e **imprime avisos**. Mantenha exatamente esse comportamento (config importado uma única vez, na mesma ordem de efeitos). Não mova isso para dentro de `main()`.
5. **`sys.path`.** `generate_dashboard.py` insere `scripts/` no `sys.path` antes de importar `xlsx_scan`, `semanas_evisita`, `icones`. Os módulos do pacote que usam `xlsx_scan`/`semanas_evisita`/`icones` importam por nome absoluto (`from xlsx_scan import get_tables`), que funciona porque `scripts/` já está no path; não use `from ..xlsx_scan`.
6. **Estado global.** `_PRESENCA_CACHE` (chave `str(cfg.XLSX_PATH)`) fica **só** em `custos.py`; nunca duplique.
7. **Datas.** `datetime.now(...)` aparece em `build_context` e `_selo_periodo`. Não troque por parâmetro nem congele; o comparador já normaliza o horário.
8. **Jinja.** O `Environment` e `env.filters.update(br=…, badge=…, id_link=…, class_key=…, row_class=…, rank_badge=…)` ficam em `main()`; os seis filtros vêm de `formatters`. `FileSystemLoader(str(cfg.SCRIPTS_DIR / "templates"))`.
9. **`gerar_mapa.py` só varre `scripts/*.py` e `scripts/coleta/`** (linha 43). Acrescente `scripts/dashboard/*.py`, rode `python3 scripts/gerar_mapa.py` e confirme que `--check` passa; sem isso, `docs/MAPA.md` perde essas funções.
10. **Docs e regras que citam o arquivo antigo:** `CLAUDE.md` (linha "Painel Custos"), `docs/REGRAS.md` (seção Custos), `.claude/rules/dashboard.md` (acrescentar `scripts/dashboard/**` em `paths:`), `README.md`. Atualize só a localização; registre uma linha em `docs/DECISOES.md`.

## Etapas (nesta ordem; cada uma passa no portão e vira um commit)
1. `dashboard/__init__.py` (vazio), `config.py`, `colunas.py`. `generate_dashboard.py` passa a importar de lá e a fachada já nasce aqui (com `config`). **Teste obrigatório desta etapa:** `python3 scripts/test_semanal.py` verde (prova que `G.OUT_PATH = …` ainda chega às funções).
2. `formatters.py`.
3. `leitura_rapida.py`.
4. `custos.py`.
5. `ranking.py`.
6. `context.py`.
7. `navegacao.py`.
8. `loaders.py`; `generate_dashboard.py` fica só com fachada e `main()`.
9. `gerar_mapa.py` + docs + `.claude/rules/dashboard.md`.

## Verificações finais (todas devem passar)
- `python3 tools/comparar_saidas.py --base <commit-antes-da-etapa-1> --testes` → idêntico e 15/15.
- `python3 -m pyflakes scripts/` sem avisos novos.
- Cada módulo importa **sozinho** (um processo por módulo), sem `ImportError`:
  `for m in config colunas formatters leitura_rapida custos ranking context navegacao loaders; do python3 -c "import sys; sys.path.insert(0,'scripts'); import dashboard.$m" || echo FALHOU $m; done`
- `wc -l`: nenhum módulo novo passa de ~450 linhas e `generate_dashboard.py` fica abaixo de ~150.
- `git diff --stat` contra a base: nenhuma mudança em `index.html`, `acumulado.html`, `historico/`, `partes/`, `data/`, `scripts/templates/`, `style.css`, `bootstrap.js`.

## Se algo divergir
Pare e relate: etapa, chamada que falhou, trecho do diff. Não ajuste o comparador, não aumente tolerâncias, não normalize mais nada para "passar".
