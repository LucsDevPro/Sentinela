# -*- coding: utf-8 -*-
"""Regenera um mês CONGELADO (arquivado) com o código e as regras de hoje e congela de novo.

Serve para corrigir um problema que afeta meses antigos (um rótulo, uma regra nova, um bug de
cálculo): os meses arquivados nunca são recalculados sozinhos, então é preciso reabrir, refazer
a planilha a partir do cache (data/semanas/) e fechar de novo.

  python scripts/regenerar_mes.py "Setembro/2026"      # um mês
  python scripts/regenerar_mes.py todos                # todos os meses congelados
  python scripts/regenerar_mes.py "Setembro/2026" --sem-acumulado   # não refaz o Analise_Consolidada

O que faz, em ordem:
  1. confere que o mês existe, está congelado e que TODAS as semanas dele estão em data/semanas/;
  2. guarda a planilha antiga em data/historico/backup_congelado/<arquivo>_antes-da-regeneracao-<data>.xlsx
     (ficam só os 3 mais recentes por mês; backups com outros nomes não são tocados);
  3. refaz a detecção e o histórico, tratando o mês como aberto — UM MÊS POR VEZ, em ordem cronológica
     (o desempate do ranking usa a média dos meses anteriores, que precisam estar no manifest); depois o Acumulado;
  4. congela o mês de novo (origem "manual" no manifest.json; data/meses_arquivados.json não muda);
  5. confere que os OUTROS meses congelados não mudaram e mostra o que mudou nas notas.

Não coleta nada no e-Visita. As páginas HTML são geradas pelo workflow update-dashboard
(`rodar_coleta=false`), que o workflow "Regenerar mês congelado" aciona no fim.
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ.setdefault("EVISITA_CPF", "x")      # o pacote exige as variáveis, mas aqui não há login
os.environ.setdefault("EVISITA_SENHA", "x")

PASTA_SEMANAS = "data/semanas"
PASTA_HISTORICO = "data/historico"
PASTA_BACKUP = os.path.join(PASTA_HISTORICO, "backup_congelado")
BACKUPS_A_MANTER = 3   # por mês, só dos feitos por este script


# ---------------------------------------------------------------------------
# Funções puras (testadas em test_regenerar_mes.py)
# ---------------------------------------------------------------------------
def escolher_alvos(arg, arquivados, oficiais):
    """[(semana_ini, semana_fim, "Mês/Ano")] a regenerar.

    arg: "todos" ou o nome de um mês congelado (sem diferenciar maiúsculas/minúsculas).
    Levanta ValueError com mensagem clara se o mês não existir ou não estiver congelado."""
    arquivados = sorted(arquivados)
    if not arquivados:
        raise ValueError("Não há nenhum mês congelado (data/meses_arquivados.json está vazio).")
    pedido = (arg or "").strip()
    if pedido.lower() == "todos":
        return list(arquivados)
    for item in arquivados:
        if item[2].lower() == pedido.lower():
            return [item]
    if any(o[2].lower() == pedido.lower() for o in oficiais):
        raise ValueError(f"'{pedido}' é o mês vigente (não está congelado): ele já é refeito a cada execução "
                         "do workflow 'Coletar e Atualizar Dashboard'.")
    validos = ", ".join(a[2] for a in arquivados)
    raise ValueError(f"Mês '{pedido}' não encontrado entre os congelados. Opções: {validos} (ou 'todos').")


def semanas_faltando(alvo, em_cache):
    """Semanas (HTML ID) do mês que NÃO estão no cache. Mês só pode ser refeito com todas elas."""
    ini, fim, _ = alvo
    tem = set(em_cache)
    return [h for h in range(ini, fim + 1) if h not in tem]


def ler_ranking(caminho):
    """{agente: (posição, dias trabalhados, dias esperados, turnos sem trabalhar, pontuação)} da aba Ranking."""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    try:
        linhas = list(wb["Ranking"].iter_rows(values_only=True))
    finally:
        wb.close()
    cab = next((i for i, r in enumerate(linhas) if r and r[0] == "Posição"), None)
    if cab is None:
        return {}
    saida = {}
    for r in linhas[cab + 1:]:
        if r[0] is None or r[1] is None:
            break
        saida[r[1]] = (r[0], r[3], r[4], r[5], r[6])
    return saida


def comparar_rankings(antigo, novo):
    """Resumo do que mudou entre duas leituras de ler_ranking()."""
    comuns = [k for k in antigo if k in novo]
    difs = [(novo[k][4] or 0) - (antigo[k][4] or 0) for k in comuns]
    return {
        "agentes": len(comuns),
        "sobem": sum(1 for d in difs if d >= 0.05),
        "descem": sum(1 for d in difs if d <= -0.05),
        "iguais": sum(1 for d in difs if abs(d) < 0.05),
        "maior_alta": max(difs) if difs else 0.0,
        "maior_queda": min(difs) if difs else 0.0,
        "media": (sum(difs) / len(difs)) if difs else 0.0,
        "posicao_mudou": sum(1 for k in comuns if antigo[k][0] != novo[k][0]),
        "identico": bool(comuns) and all(antigo[k] == novo[k] for k in comuns) and set(antigo) == set(novo),
    }


def tirar_do_manifest(manifest, alvos):
    """Manifest sem as entradas (mês e visões semanais) das semanas dos alvos."""
    def dentro(e):
        return any(ini <= (e.get("semana_inicio") or -1) <= fim for ini, fim, _ in alvos)
    return [e for e in manifest if not dentro(e)]


def congelar_no_manifest(manifest, alvos, hoje):
    """Marca como congeladas ("manual") as entradas dos alvos, como o 'Fechar mês' faz."""
    for e in manifest:
        if any(ini <= (e.get("semana_inicio") or -1) <= fim for ini, fim, _ in alvos):
            e["origem"] = "manual"
            e["parcial"] = False
            e["reaberto_em"] = hoje
    return manifest


def podar_backups(pasta, stem, manter=3):
    """Apaga os backups `<stem>_antes-da-regeneracao-*.xlsx` mais antigos, deixando os `manter` mais recentes
    (o carimbo AAAAMMDD-HHMM no nome ordena cronologicamente). Backups com outros nomes nunca são tocados.
    Devolve os nomes apagados."""
    prefixo = f"{stem}_antes-da-regeneracao-"
    nomes = sorted(n for n in os.listdir(pasta) if n.startswith(prefixo) and n.endswith(".xlsx"))
    apagar = nomes[:-manter] if manter > 0 else nomes
    for n in apagar:
        os.remove(os.path.join(pasta, n))
    return apagar


def _sha(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


# ---------------------------------------------------------------------------
def _linha_resumo(nome, r):
    if r is None:
        return f"| {nome} | (sem planilha antiga para comparar) | | | | | |"
    ident = "**idêntico**" if r["identico"] else ""
    return (f"| {nome} | {r['agentes']} | {r['sobem']} sobem · {r['descem']} descem · {r['iguais']} iguais | "
            f"{r['maior_alta']:+.1f} / {r['maior_queda']:+.1f} | {r['media']:+.2f} | {r['posicao_mudou']} | {ident} |")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sem_acumulado = "--sem-acumulado" in argv
    argv = [a for a in argv if not a.startswith("--")]
    if len(argv) != 1:
        print(__doc__)
        return 2

    import coletar_evisita as C
    import coleta.historico as H
    import coleta.parametros as P

    arquivados = list(P.MESES_ARQUIVADOS)
    oficiais = list(P.MESES_OFICIAIS)
    try:
        alvos = escolher_alvos(argv[0], arquivados, oficiais)
    except ValueError as e:
        print(f"::error title=Mês inválido::{e}")
        return 2

    em_cache = C.semanas_ja_coletadas(PASTA_SEMANAS)
    for alvo in alvos:
        falta = semanas_faltando(alvo, em_cache)
        if falta:
            print(f"::error title=Faltam semanas no cache::{alvo[2]}: semanas {falta} não estão em {PASTA_SEMANAS}/. "
                  "O mês não pode ser refeito sem todas elas (recolete as semanas antes).")
            return 2

    carimbo = datetime.now().strftime("%Y%m%d-%H%M")
    hoje = datetime.now().strftime("%d/%m/%Y")
    manifest_path = os.path.join(PASTA_HISTORICO, "manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))

    def arquivo_do_mes(alvo):
        for e in manifest:
            if e.get("label") == alvo[2] and e.get("tipo") != "semana":
                return e["arquivo"]
        return f"semanas_{alvo[0]}-{alvo[1]}.xlsx"

    # 1) cópia de segurança + leitura do ranking antigo + impressão digital dos OUTROS meses congelados
    antigos, arquivos = {}, {}
    os.makedirs(PASTA_BACKUP, exist_ok=True)
    for alvo in alvos:
        arq = arquivo_do_mes(alvo)
        arquivos[alvo[2]] = arq
        caminho = os.path.join(PASTA_HISTORICO, arq)
        if os.path.exists(caminho):
            antigos[alvo[2]] = ler_ranking(caminho)
            destino = os.path.join(PASTA_BACKUP, f"{os.path.splitext(arq)[0]}_antes-da-regeneracao-{carimbo}.xlsx")
            shutil.copy2(caminho, destino)
            print(f"💾 backup: {destino}")
            for velho in podar_backups(PASTA_BACKUP, os.path.splitext(arq)[0], BACKUPS_A_MANTER):
                print(f"🧹 backup antigo removido (ficam os {BACKUPS_A_MANTER} mais recentes): {velho}")
    nomes_alvo = {a[2] for a in alvos}
    outros = {}
    for e in manifest:
        if e.get("origem") == "manual" and e.get("label") not in nomes_alvo and e.get("mes") not in nomes_alvo:
            c = os.path.join(PASTA_HISTORICO, e["arquivo"])
            if os.path.exists(c):
                outros[e["arquivo"]] = _sha(c)

    # 2-4) UM MÊS POR VEZ, em ordem cronológica. O desempate do ranking lê a média dos meses anteriores
    # do manifest.json em disco; se vários meses saíssem do manifest juntos, os posteriores seriam
    # calculados sem o desempate (e as posições de quem empata na nota ficariam erradas).
    lista = C.rodar_deteccao_completa(PASTA_SEMANAS)
    for alvo in sorted(alvos):
        # trata só este alvo como mês ABERTO durante a rodada (nada é gravado em parametros/JSON de meses)
        P.MESES_ARQUIVADOS = [m for m in arquivados if m != alvo]
        H.MESES_ARQUIVADOS = P.MESES_ARQUIVADOS
        P.MESES_OFICIAIS = sorted(set(oficiais) | {alvo})
        atual = json.load(open(manifest_path, encoding="utf-8"))
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(tirar_do_manifest(atual, [alvo]), f, ensure_ascii=False, indent=2)
        C.atualizar_historico_do_cache(pasta_semanas=PASTA_SEMANAS, lista_cronograma=lista)
        # congela de novo (como o 'Fechar mês' faz)
        novo_manifest = json.load(open(manifest_path, encoding="utf-8"))
        congelar_no_manifest(novo_manifest, [alvo], hoje)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(novo_manifest, f, ensure_ascii=False, indent=2)
    if not sem_acumulado:
        C.consolidar_semanas(em_cache, "data", lista)

    # 5) conferências e resumo
    erros = []
    for arq, sha in outros.items():
        c = os.path.join(PASTA_HISTORICO, arq)
        if not os.path.exists(c) or _sha(c) != sha:
            erros.append(f"o mês congelado '{arq}' foi alterado, mas não era para ser")
    linhas = ["## Regeneração de mês congelado", "",
              "| Mês | Agentes | Notas | Maior alta / queda | Média | Posição mudou | |",
              "|---|---|---|---|---|---|---|"]
    for alvo in alvos:
        c = os.path.join(PASTA_HISTORICO, arquivos[alvo[2]])
        if not os.path.exists(c):
            erros.append(f"a planilha de {alvo[2]} não foi gerada")
            continue
        r = comparar_rankings(antigos[alvo[2]], ler_ranking(c)) if alvo[2] in antigos else None
        linhas.append(_linha_resumo(alvo[2], r))
    linhas += ["", f"Outros meses congelados conferidos (intactos): **{len(outros)}**.",
               f"Planilhas antigas guardadas em `{PASTA_BACKUP}/` (sufixo `_antes-da-regeneracao-{carimbo}`)."]
    if erros:
        linhas += ["", "### ❌ Problemas"] + [f"- {e}" for e in erros]
    texto = "\n".join(linhas)
    print(texto)
    destino_resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino_resumo:
        with open(destino_resumo, "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    if erros:
        for e in erros:
            print(f"::error title=Regeneração incompleta::{e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
