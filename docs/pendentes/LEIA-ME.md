# Mudanças de workflow aguardando aplicação

Estes dois itens mexem em `.github/workflows/`, e o token usado pelo assistente não tem o escopo `workflow`
(o GitHub recusa o push). Aplique da sua máquina (onde o seu login tem permissão), na raiz do repositório:

```bash
git pull
git mv docs/pendentes/regenerar-mes.yml .github/workflows/regenerar-mes.yml
git apply docs/pendentes/ci-testes-e-cache.patch
git rm docs/pendentes/ci-testes-e-cache.patch docs/pendentes/LEIA-ME.md
git add -A && git commit -m "Aplica workflows pendentes (regenerar mês, CI, cache do pip, push só na main)"
git push
```

| Arquivo | O que faz |
|---|---|
| `regenerar-mes.yml` | Botão em Actions → *Regenerar mês congelado* (refaz um mês antigo com as regras de hoje; veja `docs/OPERACAO.md`). |
| `ci-testes-e-cache.patch` | CI passa a rodar `test_turno_evento.py` e `test_regenerar_mes.py`; cache do pip; `push` só na `main` (hoje qualquer branch dispara coleta/geração/deploy). |

Depois de aplicar, apague esta pasta (`docs/pendentes/`) e a nota em `docs/OPERACAO.md`.
