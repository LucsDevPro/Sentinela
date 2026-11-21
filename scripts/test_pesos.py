# -*- coding: utf-8 -*-
"""Testes do arquivo de pesos da pontuação (data/pesos_pontuacao.json)."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("EVISITA_CPF", "0")
os.environ.setdefault("EVISITA_SENHA", "0")
from coleta import pontos as P  # noqa: E402

FALHAS = []
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


def escrever(d):
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(d, f)
    f.close()
    return f.name


def erro(d):
    try:
        P.carregar_pesos(escrever(d))
    except ValueError as e:
        return str(e)
    return None


oficial = json.load(open(os.path.join(RAIZ, "data", "pesos_pontuacao.json"), encoding="utf-8"))["pesos"]
nomes_codigo = {n for n in dir(P) if n.startswith(("PONTOS_PERDA_", "PONTOS_GANHO_"))}
check(set(oficial) == nomes_codigo, "o JSON cobre exatamente os PONTOS_PERDA_*/PONTOS_GANHO_* do código")
check(all(isinstance(v["valor"], (int, float)) and v["descricao"] and v["rotulo"] for v in oficial.values()), "todo peso tem valor numérico, rótulo e descrição")
check(P.carregar_pesos("padrao") == {}, "'padrao' devolve vazio (vale o padrão do código)")
check(P.carregar_pesos("/nao/existe.json") == {}, "sem arquivo: vale o padrão do código")
check(P.carregar_pesos(escrever({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": 2}}})) == {"PONTOS_PERDA_FORA_EXPEDIENTE": 2},
      "valor válido é lido")
check(P.carregar_pesos(escrever({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": 0.25}})) == {"PONTOS_PERDA_FORA_EXPEDIENTE": 0.25},
      "aceita também número direto (sem objeto)")
check("desconhecido" in (erro({"pesos": {"PONTOS_PERDA_INEXISTENTE": {"valor": 1}}}) or ""), "nome desconhecido é recusado")
check("desconhecido" in (erro({"pesos": {"META_VISITAS_DIA": {"valor": 1}}}) or ""), "constante que não é peso é recusada")
check("inválido" in (erro({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": -1}}}) or ""), "valor negativo é recusado")
check("inválido" in (erro({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": 999}}}) or ""), "valor acima do limite é recusado")
check("inválido" in (erro({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": "2"}}}) or ""), "texto no lugar de número é recusado")
check("inválido" in (erro({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": True}}}) or ""), "booleano é recusado")
check("inválido" in (erro({"sem_pesos": 1}) or ""), "arquivo sem a chave 'pesos' é recusado")

# o JSON realmente manda: um processo novo com SENTINELA_PESOS aplicado vê o valor trocado
arq = escrever({"pesos": {"PONTOS_PERDA_FORA_EXPEDIENTE": {"valor": 3.5}}})
env = dict(os.environ, SENTINELA_PESOS=arq)
r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'scripts'); import coletar_evisita as C; print(C.PONTOS_PERDA_FORA_EXPEDIENTE)"],
                   cwd=RAIZ, env=env, capture_output=True, text=True)
check(r.stdout.strip().endswith("3.5"), f"SENTINELA_PESOS troca o peso no cálculo (lido: {r.stdout.strip()[-6:]!r})")

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes de pesos passaram.")
