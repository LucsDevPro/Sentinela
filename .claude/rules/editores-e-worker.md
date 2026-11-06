---
paths:
  - worker/**
  - "*.html"
  - assets/**
  - sw.js
  - scripts/aplicar_decisao.py
  - scripts/lancar_*.py
  - .github/ISSUE_TEMPLATE/**
---
# Editores da coordenação, Worker e formulários

- O Worker (`worker/index.js`) é a única porta de entrada das decisões da coordenação: editor `.html` → Worker → `repository_dispatch` → `aplicar_decisao.py` / `lancar_*.py` → `data/*.json`.
- Mudou o Worker → `node worker/test_worker.mjs`.
- Atestado e férias usam issue forms (`.github/ISSUE_TEMPLATE/`) + `lancar_*.py`; nunca grave CID ou diagnóstico.
- Páginas da raiz: `.html` só com estrutura, código em `assets/<nome>.js/.css`. `index`, `acumulado` e `transparencia` são gerados: não edite.
- Mudou `assets/validar.*` ou renomeou arquivo → atualize `ARQUIVOS` e suba o `CASCA` em `sw.js`.
