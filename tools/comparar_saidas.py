#!/usr/bin/env python3
"""Compara a SAÍDA do gerador do dashboard entre duas versões do código.

Serve de rede de segurança para refatorar `scripts/generate_dashboard.py` (ou qualquer
coisa que ele use): roda as MESMAS chamadas que o CI faz nas duas versões e exige
saída idêntica, byte a byte, fora o horário de geração.

Uso:
    python3 tools/comparar_saidas.py                       # HEAD  x  árvore de trabalho
    python3 tools/comparar_saidas.py --base main           # qualquer ref do Git como "antes"
    python3 tools/comparar_saidas.py --base-dir /caminho   # uma pasta já pronta como "antes"
    python3 tools/comparar_saidas.py --autoteste           # prova que o comparador pega erro
    python3 tools/comparar_saidas.py --testes              # também roda ./scripts/rodar_testes.sh no "depois"

Nada é escrito no repositório: as duas versões são copiadas para uma pasta temporária.
Só usa a biblioteca padrão (o gerador em si precisa de `pip install -r requirements.txt`).
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Horário de geração ("atualizado em 06/11/2026 01:31", data-print-date): muda a cada minuto.
RE_HORA = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")
IGNORAR_NA_COPIA = shutil.ignore_patterns(".git", "__pycache__", "node_modules", ".playwright", "_teste*")


def copiar_arvore(origem: Path, destino: Path):
    shutil.copytree(origem, destino, ignore=IGNORAR_NA_COPIA)


def exportar_ref(ref: str, destino: Path):
    destino.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(RAIZ), "archive", ref], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(destino)], input=tar, check=True)


def chamadas(arv: Path):
    """As mesmas invocações do workflow update-dashboard.yml (+ 3 casos de borda)."""
    cs = [dict(nome="home (sem argumentos)", args=[], saida="index.html")]
    cs.append(dict(nome="acumulado", args=["data/Analise_Consolidada.xlsx", "acumulado.html"], saida="acumulado.html"))
    for x in sorted((arv / "data" / "historico").glob("*.xlsx")):
        cs.append(dict(nome=f"historico/{x.stem}", args=[f"data/historico/{x.name}", f"historico/{x.stem}.html"],
                       saida=f"historico/{x.stem}.html"))
    # Borda 1: partes pesadas dentro do HTML (ramo LAZY desligado).
    cs.append(dict(nome="sem lazy (SENTINELA_SEM_LAZY=1)", args=["data/historico/semanas_327-330.xlsx", "_teste_semlazy.html"],
                   saida="_teste_semlazy.html", env={"SENTINELA_SEM_LAZY": "1"}))
    # Borda 2: planilha inexistente -> código de saída 1 e mensagem de erro.
    cs.append(dict(nome="erro: planilha inexistente", args=["data/nao_existe.xlsx", "_teste_erro.html"], saida=None))
    # Borda 3: config_home.json apontando para arquivo que sumiu -> aviso e cai no acumulado.
    cs.append(dict(nome="home com config quebrada", args=[], saida="index.html", antes=_quebrar_config_home))
    return cs


def _quebrar_config_home(arv: Path):
    (arv / "data" / "config_home.json").write_text(
        json.dumps({"arquivo": "data/historico/nao_existe.xlsx", "label": "x"}), encoding="utf-8")


def normalizar(texto: str, arv: Path) -> str:
    return RE_HORA.sub("<HORA>", texto.replace(str(arv), "<RAIZ>"))


def rodar_uma(arv: Path, c: dict):
    """Roda uma chamada numa cópia exclusiva da árvore (as chamadas não se atrapalham)."""
    with tempfile.TemporaryDirectory(prefix="cmp_run_") as tmp:
        w = Path(tmp) / "r"
        copiar_arvore(arv, w)
        if c.get("antes"):
            c["antes"](w)
        env = {**os.environ, **c.get("env", {})}
        p = subprocess.run([sys.executable, "scripts/generate_dashboard.py", *c["args"]], cwd=w, env=env,
                           capture_output=True, text=True)
        r = dict(rc=p.returncode, stdout=normalizar(p.stdout, w), stderr=normalizar(p.stderr, w), arquivos={})
        if c["saida"]:
            alvos = [c["saida"]]
            stem = Path(c["saida"]).stem
            alvos += [f"partes/{stem}.alertas.js", f"partes/{stem}.extratos.js"]
            for a in alvos:
                f = w / a
                r["arquivos"][a] = normalizar(f.read_text(encoding="utf-8"), w) if f.exists() else None
        # Traceback do Python traz caminhos/linhas que mudam de propósito numa refatoração: só o tipo importa.
        if p.returncode not in (0, 1):
            r["stderr_final"] = (p.stderr.strip().splitlines() or [""])[-1]
        return r


def superficie_api(arv: Path):
    """Nomes públicos de `import generate_dashboard` (os testes usam G.X) e assinaturas das funções."""
    cod = ("import inspect, json, sys; sys.argv=['x']; sys.path.insert(0,'scripts'); import generate_dashboard as G\n"
           "out={}\n"
           "for n in dir(G):\n"
           "    if n.startswith('__'): continue\n"
           "    v=getattr(G,n)\n"
           "    if inspect.isfunction(v):\n"
           "        try: out[n]='def'+str(inspect.signature(v))\n"
           "        except Exception: out[n]='def'\n"
           "    elif inspect.ismodule(v): out[n]='módulo'\n"
           "    else: out[n]=type(v).__name__\n"
           "print(json.dumps(out))")
    p = subprocess.run([sys.executable, "-c", cod], cwd=arv, capture_output=True, text=True)
    if p.returncode != 0:
        return None, p.stderr.strip().splitlines()[-1:]
    return json.loads(p.stdout.strip().splitlines()[-1]), None


def comparar(base: Path, novo: Path, verbose=True):
    cs = chamadas(base)
    with ThreadPoolExecutor(max_workers=4) as ex:
        fb = [ex.submit(rodar_uma, base, c) for c in cs]
        fn = [ex.submit(rodar_uma, novo, c) for c in cs]
        rb, rn = [f.result() for f in fb], [f.result() for f in fn]
    falhas = 0
    if verbose:
        print(f"{'chamada':38} {'rc':>6}  arquivos  resultado")
    for c, a, b in zip(cs, rb, rn):
        problemas = []
        if a["rc"] != b["rc"]:
            problemas.append(f"código de saída {a['rc']} -> {b['rc']}")
        if a["stdout"] != b["stdout"]:
            problemas.append("stdout difere")
        if a["rc"] == 1 and a["stderr"] != b["stderr"]:
            problemas.append("stderr difere")
        if a.get("stderr_final") != b.get("stderr_final"):
            problemas.append(f"erro inesperado: {b.get('stderr_final')!r}")
        for nome in sorted(set(a["arquivos"]) | set(b["arquivos"])):
            x, y = a["arquivos"].get(nome), b["arquivos"].get(nome)
            if x is None and y is None and a["rc"] != 0:
                continue
            if x != y:
                if x is None or y is None:
                    problemas.append(f"{nome}: {'sumiu' if y is None else 'apareceu'}")
                else:
                    d = next(difflib.unified_diff(x.splitlines(), y.splitlines(), lineterm="", n=0), "")
                    ln = [l for l in difflib.unified_diff(x.splitlines(), y.splitlines(), lineterm="", n=0)
                          if l[:1] in "+-" and l[:3] not in ("+++", "---")][:2]
                    problemas.append(f"{nome} difere (ex.: {' | '.join(s[:90] for s in ln)})")
        n_arq = len([k for k, v in b["arquivos"].items() if v is not None])
        if verbose:
            print(f"{c['nome']:38} {a['rc']:>2}->{b['rc']:<2}  {n_arq:>4}      {'✅ idêntico' if not problemas else '❌ ' + '; '.join(problemas)}")
        falhas += bool(problemas)
    # superfície de API
    sa, ea = superficie_api(base)
    sn, en = superficie_api(novo)
    if sa is None or sn is None:
        print("❌ API: não consegui importar generate_dashboard:", ea or en)
        falhas += 1
    else:
        sumiram = sorted(set(sa) - set(sn))
        mudaram = sorted(n for n in sa if n in sn and sa[n] != sn[n])
        if verbose:
            print(f"{'API: import generate_dashboard as G':38} {len(sa)}->{len(sn)} nomes  ",
                  "✅ nada sumiu" if not (sumiram or mudaram) else "")
        if sumiram:
            print("   ❌ sumiram de G:", ", ".join(sumiram)); falhas += 1
        if mudaram:
            print("   ❌ assinatura/tipo mudou:", ", ".join(f"{n} ({sa[n]} -> {sn[n]})" for n in mudaram)); falhas += 1
    return falhas, len(cs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="HEAD", help="ref do Git usada como 'antes' (padrão: HEAD)")
    ap.add_argument("--base-dir", help="pasta pronta usada como 'antes' (ignora --base)")
    ap.add_argument("--novo-dir", help="pasta usada como 'depois' (padrão: árvore de trabalho atual)")
    ap.add_argument("--autoteste", action="store_true", help="prova que o comparador detecta erros (null + 2 mutações)")
    ap.add_argument("--testes", action="store_true", help="roda ./scripts/rodar_testes.sh no 'depois'")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="cmp_") as tmp:
        tmp = Path(tmp)
        base = tmp / "antes"
        if a.base_dir:
            copiar_arvore(Path(a.base_dir), base)
        else:
            exportar_ref(a.base, base)
        novo = tmp / "depois"
        copiar_arvore(Path(a.novo_dir) if a.novo_dir else RAIZ, novo)

        if a.autoteste:
            return autoteste(base, tmp)

        falhas, n = comparar(base, novo)
        if a.testes:
            print("\n== testes Python do CI na versão 'depois' ==")
            r = subprocess.run(["bash", "scripts/rodar_testes.sh"], cwd=novo)
            falhas += r.returncode != 0
        print("\n" + ("✅ SAÍDA IDÊNTICA em todas as chamadas." if not falhas else f"❌ {falhas} divergência(s) — NÃO misture esta refatoração."))
        return 1 if falhas else 0


def autoteste(base: Path, tmp: Path):
    """1) cópia idêntica deve dar zero diferenças; 2) duas mutações devem ser pegas."""
    ok = True
    print("### Teste nulo: 'depois' = cópia idêntica do 'antes'")
    nulo = tmp / "nulo"; copiar_arvore(base, nulo)
    f, _ = comparar(base, nulo, verbose=False)
    print("   ", "✅ 0 diferenças (o comparador não inventa erro)" if f == 0 else f"❌ {f} diferença(s) falsa(s)")
    ok &= f == 0

    def mutar(nome, arquivo, de, para):
        nonlocal ok
        m = tmp / f"mut_{nome}"; copiar_arvore(base, m)
        p = m / arquivo
        t = p.read_text(encoding="utf-8")
        assert de in t, f"trecho não encontrado em {arquivo}: {de!r}"
        p.write_text(t.replace(de, para, 1), encoding="utf-8")
        f, _ = comparar(base, m, verbose=False)
        print(f"### Mutação '{nome}' ({arquivo}: {de!r} -> {para!r})")
        print("   ", f"✅ detectada ({f} divergência(s))" if f else "❌ NÃO detectada — o comparador está cego a isso")
        ok &= f > 0

    mutar("constante de custo", "scripts/generate_dashboard.py", "SALARIO_MENSAL = 4863.00", "SALARIO_MENSAL = 4864.00")
    mutar("função de formatação", "scripts/generate_dashboard.py", "def parse_br_date(", "def parse_br_date_ORIG(")
    mutar("template", "scripts/templates/base.html", "<header>", "<header data-x=\"1\">")
    print("\n" + ("✅ Autoteste passou." if ok else "❌ Autoteste falhou."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
