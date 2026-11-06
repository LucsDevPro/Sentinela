---
paths:
  - scripts/coleta/**
  - scripts/coletar_evisita.py
  - scripts/test_*.py
  - scripts/rodar_testes.sh
---
# Coleta e testes

- Camadas (cada módulo só importa dos anteriores, sem import cíclico): `parametros → pontos → auxiliares → deteccao → sessao (Selenium/HTTP) → calculos → colunas → estilo_excel → abas → ausencias_ranking → saida_excel → processamento → cache_semanas → consolidacao → historico → execucao (main)`.
- `coletar_evisita.py` é só fachada: `import coletar_evisita as C` vale para tudo (`C.calcular_pontuacao`, `C.CPF`…). Atribuir `C.X = valor` (como os testes fazem) repassa o valor aos módulos que têm `X`; em código novo, prefira passar parâmetro.
- Só `coleta/sessao.py` importa `selenium`; sem `pip install -r requirements.txt` quase todos os testes falham no import.
- Constantes de regra ficam em `pontos.py` ou `parametros.py`, com comentário do **porquê**.
- Mudou pontuação, ausência, detecção ou ranking → exige teste em `scripts/test_*.py` e linha em `docs/DECISOES.md`.
- Novo teste: acrescente o nome em `TESTES` de `rodar_testes.sh` (e no CI, se ele ainda listar os testes à mão).
- Ranking sem normalização vale para períodos de até 45 dias (todos os meses); o Acumulado (> 45 dias) segue o método antigo. Férias disparam com `LIMITE_DIAS_UTEIS_FERIAS = 7`.
- Equipes sob demanda (`EQUIPES_SEM_DETECCAO_AUTOMATICA`: Bloqueio, Ponto Estratégico) ficam fora das regras de evento; a Equipe Bloqueio também fica fora do painel de custos.
- Nas planilhas, a 1ª tabela de cada aba termina na primeira linha em branco (as legendas vêm depois). Leia planilhas só por `scripts/xlsx_scan.py` (`get_tables`).
- Alterou função pública → `python3 scripts/gerar_mapa.py`.
