---
paths:
  - scripts/generate_dashboard.py
  - scripts/xlsx_scan.py
  - scripts/templates/**
  - scripts/style.css
  - scripts/bootstrap.js
  - tools/shot.py
---
# Geração do dashboard

- Mexa em `scripts/templates/` ou na lógica de `generate_dashboard.py`, nunca nos HTML gerados.
- Funções que montam dados começam com `build_`.
- Planilhas: leia sempre por `xlsx_scan.get_tables` (abre a planilha uma vez, em `read_only`). Não use `openpyxl.load_workbook` sem `read_only=True` nem `ws.cell(r, c)` em laço: foi o que deixava a geração 4 a 6× mais lenta.
- Depois de mudança visual ou de dados: gere `_teste.html`, confira (`python3 tools/shot.py _teste.html custos` mostra claro/escuro e erros de JS; precisa de Playwright) e **apague** `_teste.html` e `partes/_teste*`.
- Compatível com o service worker: `sw.js` guarda `validar.js/.css` na casca offline; se renomear, atualize `ARQUIVOS` e suba o `CASCA`.
