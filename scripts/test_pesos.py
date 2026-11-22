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

# --- ação pesos_aplicar (aplicar_decisao.py): grava pesos + histórico, recusa o inválido ---
import shutil  # noqa: E402
import aplicar_decisao as AD  # noqa: E402

check(AD.PESOS_LIMITE_MAX == P.PESOS_LIMITE_MAX, "limite do aplicar_decisao == limite do cálculo")
tmp = tempfile.mkdtemp()
arq_p, arq_h = os.path.join(tmp, "pesos.json"), os.path.join(tmp, "hist.json")
shutil.copy(os.path.join(RAIZ, "data", "pesos_pontuacao.json"), arq_p)
json.dump([], open(arq_h, "w"))


def A(**dec):
    return AD.aplicar(dict({"acao": "pesos_aplicar", "quem": "Maria", "motivo": "Teste de equilíbrio"}, **dec),
                      caminho_pesos=arq_p, caminho_pesos_hist=arq_h)


def valor(n):
    return json.load(open(arq_p, encoding="utf-8"))["pesos"][n]["valor"]


antes = valor("PONTOS_PERDA_FORA_EXPEDIENTE")
ok, msg = A(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 1.25, "PONTOS_GANHO_DIA_COM_META": 2})
check(ok and valor("PONTOS_PERDA_FORA_EXPEDIENTE") == 1.25 and valor("PONTOS_GANHO_DIA_COM_META") == 2, "pesos válidos são gravados")
hist = json.load(open(arq_h, encoding="utf-8"))
check(len(hist) == 1 and hist[0]["quem"] == "Maria" and len(hist[0]["mudancas"]) == 2 and hist[0]["mudancas"][0]["antes"] is not None,
      "histórico registra quem, motivo e antes→depois")
check(hist[0]["snapshot"]["PONTOS_PERDA_FORA_EXPEDIENTE"] == 1.25 and len(hist[0]["snapshot"]) == 18, "histórico guarda snapshot completo")
check(P.carregar_pesos(arq_p)["PONTOS_PERDA_FORA_EXPEDIENTE"] == 1.25, "arquivo gravado é aceito pelo carregador do cálculo")
ok2, msg2 = A(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 1.25})
check(ok2 and "nada mudou" in msg2 and len(json.load(open(arq_h, encoding="utf-8"))) == 1, "mesmo valor: nada muda e não entra no histórico")
for rotulo, dec in {"nome desconhecido": dict(pesos={"PONTOS_PERDA_X": 1}), "negativo": dict(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": -1}),
                    "acima do limite": dict(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 51}), "texto": dict(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": "2"}),
                    "sem pesos": dict(pesos={}), "motivo curto": dict(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 2}, motivo="a"),
                    "motivo com saúde": dict(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 2}, motivo="por causa do atestado")}.items():
    ok3, _ = A(**dec)
    check(not ok3 and valor("PONTOS_PERDA_FORA_EXPEDIENTE") == 1.25, f"recusa: {rotulo} (nada é gravado)")
ok4, _ = A(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 1.25, "PONTOS_PERDA_VISITA_RAPIDA": 9, "PONTOS_GANHO_DIA_COM_META": 99})
check(not ok4 and valor("PONTOS_PERDA_VISITA_RAPIDA") != 9, "um valor inválido no conjunto derruba o conjunto todo")
for _ in range(AD.PESOS_HISTORICO_MAX + 5):
    A(pesos={"PONTOS_PERDA_FORA_EXPEDIENTE": 3 if valor("PONTOS_PERDA_FORA_EXPEDIENTE") != 3 else 4})
check(len(json.load(open(arq_h, encoding="utf-8"))) == AD.PESOS_HISTORICO_MAX, "histórico guarda só as versões mais recentes")
# restaurar = reenviar o snapshot de uma versão antiga
snap = hist[0]["snapshot"]
ok5, _ = A(pesos=snap, motivo="Restaurar versão antiga")
check(ok5 and valor("PONTOS_PERDA_FORA_EXPEDIENTE") == 1.25, "restaurar uma versão antiga (enviando o snapshot) funciona")
shutil.rmtree(tmp, ignore_errors=True)

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes de pesos passaram.")
