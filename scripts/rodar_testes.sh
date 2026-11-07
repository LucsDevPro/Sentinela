#!/usr/bin/env bash
# Atalho: a lista de testes e a lógica ficam em scripts/rodar_testes.py (funciona também no Windows/PowerShell).
cd "$(dirname "$0")/.." || exit 1
exec python3 scripts/rodar_testes.py "$@"
