#!/usr/bin/env bash
# Roda TODOS os testes Python do CI (+ o de turno/evento) e imprime uma linha por teste.
# O teste do Worker é à parte: node worker/test_worker.mjs. Os *_navegador.py exigem Playwright (só no computador de desenvolvimento).
# Uso:  ./scripts/rodar_testes.sh            (todos)
#       ./scripts/rodar_testes.sh ranking    (só os que tiverem "ranking" no nome)
# Precisa de: pip install -r requirements.txt   (os testes rodam da raiz do repositório)
cd "$(dirname "$0")/.." || exit 1
TESTES=(deteccao ranking ciclos atestado ausencia decisao regras semanal coleta sessao8 sessao9 sessao10 turno_evento)
FILTRO="${1:-}"
falhas=0; rodados=0
for t in "${TESTES[@]}"; do
  [[ -n "$FILTRO" && "$t" != *"$FILTRO"* ]] && continue
  arq="scripts/test_${t}.py"
  [[ -f "$arq" ]] || { printf "%-16s (arquivo não existe)\n" "$t"; continue; }
  inicio=$(date +%s)
  saida=$(timeout 280 python3 "$arq" 2>&1); codigo=$?
  seg=$(( $(date +%s) - inicio ))
  resumo=$(printf '%s\n' "$saida" | grep -E "^(✅|❌)" | tail -1)
  [[ -z "$resumo" ]] && resumo=$(printf '%s\n' "$saida" | grep -v '^$' | tail -1)
  if [[ $codigo -eq 0 ]]; then printf "✅ %-16s %3ss  %s\n" "$t" "$seg" "${resumo#✅ }"
  else printf "❌ %-16s %3ss  %s\n" "$t" "$seg" "${resumo:-falhou (veja: python3 $arq)}"; falhas=$((falhas+1)); fi
  rodados=$((rodados+1))
done
echo "----"
if [[ $falhas -eq 0 ]]; then echo "✅ $rodados teste(s) passaram."; else echo "❌ $falhas de $rodados teste(s) falharam."; exit 1; fi
