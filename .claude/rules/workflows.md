---
paths:
  - .github/workflows/**
---
# Workflows

- Alterar `.github/workflows/*` exige token com permissão "Workflows".
- O job `build` tem fila (`concurrency: coleta-<ref>`): a coleta leva ~1 h e uma segunda execução simultânea refaria o backfill.
- `rodar_testes.sh` e o passo de testes do CI precisam cobrir os mesmos testes.
