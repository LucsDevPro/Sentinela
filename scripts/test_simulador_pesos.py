# -*- coding: utf-8 -*-
"""O simulador de pesos tem de bater com o cálculo REAL: nota simulada (dados do simulador + pesos novos, na
mesma fórmula da página `pesos.js`) == nota que o ranking calcula de verdade com esses pesos."""
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MES = "Outubro/2026"
FALHAS = []


def check(cond, msg):
    print(("[OK  ] " if cond else "[FAIL] ") + msg)
    if not cond:
        FALHAS.append(msg)


if not os.path.exists(os.path.join(RAIZ, "data", "semanas", "327.xlsx")):
    print("sem cache de teste — pulado")
    sys.exit(0)


def gerar(pesos_arquivo=None):
    destino = tempfile.NamedTemporaryFile(suffix=".js", delete=False).name
    env = dict(os.environ, EVISITA_CPF="0", EVISITA_SENHA="0")
    env["SENTINELA_PESOS"] = pesos_arquivo or "padrao"
    r = subprocess.run([sys.executable, "scripts/gerar_simulador_pesos.py", destino, "--meses", MES],
                       cwd=RAIZ, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-800:], r.stderr[-800:])
        return None
    txt = open(destino, encoding="utf-8").read()
    return json.loads(txt[txt.index("=") + 1:].strip().rstrip(";"))


def simular(ag, atuais, novos):
    """Mesma conta de assets/pesos.js."""
    n = ag["bruta"] + sum(ag["inc"][k] * (novos[k] - atuais[k]) for k in novos)
    if ag["maximo"] is not None:
        n = min(n, ag["maximo"])
    if ag["minimo"] is not None:
        n = max(n, ag["minimo"])
    return round(n, 2)


base = gerar()
check(base is not None and len(base["meses"]) == 1 and base["meses"][0]["agentes"], f"simulador gera {MES} com agentes")
if base:
    atuais = {k: v["valor"] for k, v in base["pesos"].items()}
    novos = dict(atuais, PONTOS_PERDA_FORA_EXPEDIENTE=2, PONTOS_GANHO_DIA_COM_META=3, PONTOS_PERDA_TURNO_SEM_LANCAMENTO=0.5,
                 PONTOS_PERDA_VISITA_ALMOCO=1, PONTOS_GANHO_SEM_AUSENCIA=8, PONTOS_PERDA_VISITA_RAPIDA=0.6)
    ags = base["meses"][0]["agentes"]
    check(all(abs(simular(a, atuais, atuais) - a["pontos"]) < 0.011 for a in ags), "sem mudar peso, a simulação devolve a nota atual")
    arq = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"pesos": {k: {"valor": v} for k, v in novos.items()}}, arq)
    arq.close()
    real = gerar(arq.name)
    check(real is not None, "ranking real roda com os pesos novos")
    if real:
        reais = {a["id"]: a["pontos"] for a in real["meses"][0]["agentes"]}
        dif = [(a["nome"], simular(a, atuais, novos), reais[a["id"]]) for a in ags]
        pior = max(abs(s - r) for _, s, r in dif)
        check(pior <= 0.03, f"nota simulada == nota real com pesos novos (maior diferença {pior:.3f} em {len(dif)} agentes)")
        check(any(abs(simular(a, atuais, novos) - a["pontos"]) > 0.5 for a in ags), "os pesos de teste realmente mexem nas notas")

print()
if FALHAS:
    print(f"❌ {len(FALHAS)} teste(s) falharam.")
    sys.exit(1)
print("✅ Todos os testes do simulador de pesos passaram.")
