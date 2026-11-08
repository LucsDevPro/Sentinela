# Sentinela Prime — Dashboard de Monitoramento de Visitas (Ponta Porã/MS)

Dashboard estático que acompanha as visitas dos agentes de campo registradas no e-Visita: ranking de desempenho,
ausências e férias, custos e produtividade, pontos estratégicos e extrato por agente. O repositório faz tudo sozinho:
coleta os dados, gera as páginas e publica no **GitHub Pages**.

> Guia para o Claude Code (e para quem for mexer no código): comece por **[`CLAUDE.md`](CLAUDE.md)**.

## Tecnologias
- **Python 3.11**: `pandas`, `openpyxl`, `Jinja2` (geração das páginas), `selenium`, `requests`, `beautifulsoup4` (coleta). Versões fixas em `requirements.txt`.
- **HTML/CSS/JS** sem framework (Chart.js incluído em `assets/`); páginas instaláveis como app (`sw.js`, `manifest.webmanifest`).
- **GitHub Actions** (coleta, geração, deploy) e **Cloudflare Worker** (`worker/`, PIN da coordenação, decisões e contestações).

## Como funciona
1. O workflow `update-dashboard.yml` roda **domingo, segunda e terça às 07:00 UTC** (03:00 em Ponta Porã) ou pelo botão *Run workflow*.
2. `scripts/coletar_evisita.py` (código em `scripts/coleta/`) coleta cada semana do e-Visita (cache em `data/semanas/`) e consolida em `data/Analise_Consolidada.xlsx` e em uma planilha por mês (`data/historico/`).
3. `scripts/generate_dashboard.py` + `scripts/templates/` (Jinja2) geram `index.html`, `acumulado.html`, `historico/` e `partes/`.
4. O GitHub Pages publica. A coordenação valida férias, ausências e ajustes por `validar.html` → Worker → `repository_dispatch` → workflow.

## Instalação e execução local
```bash
pip install -r requirements.txt
cp .env.example .env && set -a && source .env && set +a   # só para a coleta (preencha antes); NUNCA commite o .env
python3 scripts/generate_dashboard.py data/historico/semanas_327-330.xlsx _teste.html   # gera uma página de teste
```
A coleta real (`python3 scripts/coletar_evisita.py --saida data`) acessa o e-Visita com `EVISITA_CPF` e `EVISITA_SENHA`.
Depois de testar, apague `_teste.html` e `partes/_teste*`. Configuração completa (Secrets, Pages, Worker): [`docs/INSTALACAO.md`](docs/INSTALACAO.md).

## Testes
```bash
./scripts/rodar_testes.sh        # testes Python do CI, uma linha por teste (~30 s)
node worker/test_worker.mjs      # testes do Worker
```
Os testes `*_navegador.py` e `tools/shot.py` usam Playwright e rodam só no computador de desenvolvimento.

## Estrutura principal
| Pasta / arquivo | Para quê |
|---|---|
| `*.html` na raiz | Páginas publicadas (**não mover**); `index`, `acumulado` e `transparencia` (só um redirecionamento para `album.html#como-calcula`) são gerados; o texto "Como é calculado" vive na aba do álbum |
| `scripts/` | Coleta, regras, geração, testes (`coletar_evisita.py` é a fachada; o código está em `scripts/coleta/`) e `templates/` |
| `data/` | Planilhas, cache por semana e JSONs de configuração (cronograma, ausências, metas) |
| `worker/` | Cloudflare Worker (validação pela coordenação) |
| `docs/` | Regras, decisões, mapa do código e manuais |
| `.github/` | Workflows e formulários de atestado/férias |

## Documentação
- [`CLAUDE.md`](CLAUDE.md): visão rápida, onde mexer, convenções e armadilhas.
- [`docs/REGRAS.md`](docs/REGRAS.md): pontuação, ausências, férias, custos (valores atuais).
- [`docs/DECISOES.md`](docs/DECISOES.md): o que foi decidido e quando, mais o histórico das sessões.
- [`docs/OPERACAO.md`](docs/OPERACAO.md): detecção de férias, cronograma, atestado, meses congelados, planilhas antigas.
- [`docs/INSTALACAO.md`](docs/INSTALACAO.md): configuração inicial, Secrets, Worker, teste local.
- [`docs/REGRAS_DETALHADAS.md`](docs/REGRAS_DETALHADAS.md): explicações longas das regras de ranking e ausência.
- [`docs/MAPA.md`](docs/MAPA.md): índice função → linha (gerado por `scripts/gerar_mapa.py`).

## Cuidados
- **Repositório público:** nunca grave senha, token, CID ou diagnóstico. Atestado é sempre "Ausência justificada".
- Não edite à mão os arquivos gerados (lista em `CLAUDE.md`); o workflow os recria.
