# -*- coding: utf-8 -*-
"""Consultas prontas e COMPACTAS sobre os dados do Sentinela (para não ler JSON/planilha inteiros).

  python scripts/resumo.py meses                              # meses (aberto/congelado) e suas semanas
  python scripts/resumo.py deteccoes                          # contagem por mês x tipo x status
  python scripts/resumo.py deteccoes --mes Setembro/2026 --status pendente [--tipo ferias|coletiva]
  python scripts/resumo.py ranking Setembro/2026 [--top 10]  # ranking do mês (posição, agente, pontos)
  python scripts/resumo.py ranking Setembro/2026 --vs data/historico/backup_congelado/X.xlsx   # o que mudou
  python scripts/resumo.py cronograma --agente 85             # lançamentos do cronograma de um agente (ID)
  python scripts/resumo.py manifest                           # arquivos do histórico e se estão congelados

Só lê; nunca grava. A saída é curta de propósito.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
RAIZ = os.path.dirname(AQUI)

TIPOS = {"ferias": "possiveis_ferias", "coletiva": "paralisacao_coletiva"}


def _d(texto):
    return datetime.strptime(texto, "%d/%m/%Y").date()


# ---------------------------------------------------------------------------
# Funções puras (testadas em test_resumo.py)
# ---------------------------------------------------------------------------
def janela_do_mes(semana_ini, semana_fim):
    """(primeiro dia, última sexta-feira) do período formado pelas semanas HTML ini..fim."""
    import semanas_evisita as S
    return S.data_inicio_semana_html(semana_ini), S.data_fim_semana_html(semana_fim) - timedelta(days=1)


def filtrar_deteccoes(dets, janela=None, status=None, tipo=None):
    """Detecções que tocam a janela (ini, fim), com o status e o tipo pedidos (None = qualquer)."""
    tipo_real = TIPOS.get(tipo, tipo)
    saida = []
    for e in dets:
        if status and e.get("status") != status:
            continue
        if tipo_real and e.get("tipo") != tipo_real:
            continue
        if janela and not (_d(e["inicio"]) <= janela[1] and _d(e["fim"]) >= janela[0]):
            continue
        saida.append(e)
    return sorted(saida, key=lambda e: (_d(e["inicio"]), e.get("equipe") or "", e.get("nome_agente") or ""))


def contar_deteccoes(dets, janelas):
    """{mes: {(tipo curto, status): n}} — um evento que toca 2 meses entra nos dois."""
    curto = {v: k for k, v in TIPOS.items()}
    saida = {}
    for mes, janela in janelas:
        c = {}
        for e in filtrar_deteccoes(dets, janela=janela):
            k = (curto.get(e.get("tipo"), e.get("tipo")), e.get("status"))
            c[k] = c.get(k, 0) + 1
        saida[mes] = c
    return saida


def linha_deteccao(e):
    quem = e.get("nome_agente") or e.get("equipe") or "?"
    if e.get("tipo") == "paralisacao_coletiva":
        quem = f"equipe {e.get('equipe')}"
    curto = {v: k for k, v in TIPOS.items()}.get(e.get("tipo"), e.get("tipo", ""))
    return f"{e['inicio']}–{e['fim']} | {curto:8} | {e.get('status',''):10} | {quem} | {e.get('motivo') or ''}"


# ---------------------------------------------------------------------------
# Acesso aos dados
# ---------------------------------------------------------------------------
def _json(caminho, padrao=None):
    c = os.path.join(RAIZ, caminho)
    if not os.path.exists(c):
        return padrao
    with open(c, encoding="utf-8") as f:
        return json.load(f)


def _meses():
    """[(label, semana_ini, semana_fim, 'congelado'|'aberto')] em ordem cronológica."""
    import coleta.parametros as P
    arq = {m[2] for m in P.MESES_ARQUIVADOS}
    todos = {m[2]: m for m in list(P.MESES_OFICIAIS) + list(P.MESES_ARQUIVADOS)}
    return [(m[2], m[0], m[1], "congelado" if m[2] in arq else "aberto") for m in sorted(todos.values())]


def _arquivo_do_mes(label):
    for e in _json("data/historico/manifest.json", []):
        if e.get("label") == label and e.get("tipo") != "semana":
            return os.path.join("data/historico", e["arquivo"])
    return None


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------
def cmd_meses(_a):
    for label, ini, fim, estado in _meses():
        j = janela_do_mes(ini, fim)
        print(f"{label:15} semanas {ini}-{fim} | {j[0].strftime('%d/%m')} a {j[1].strftime('%d/%m')} | {estado}")


def cmd_deteccoes(a):
    dets = _json("data/deteccoes_pendentes.json", [])
    meses = {m[0]: m for m in _meses()}
    if not (a.mes or a.status or a.tipo):
        print(f"{len(dets)} detecções no total. Por mês (evento que toca 2 meses conta nos dois):")
        for mes, c in contar_deteccoes(dets, [(m[0], janela_do_mes(m[1], m[2])) for m in meses.values()]).items():
            print(f"  {mes:15} " + ", ".join(f"{k[0]} {k[1]}: {n}" for k, n in sorted(c.items())))
        return
    janela = None
    if a.mes:
        if a.mes not in meses:
            sys.exit(f"Mês '{a.mes}' desconhecido. Opções: {', '.join(meses)}")
        janela = janela_do_mes(meses[a.mes][1], meses[a.mes][2])
    achados = filtrar_deteccoes(dets, janela, a.status, a.tipo)
    print(f"{len(achados)} detecção(ões):")
    for e in achados:
        print("  " + linha_deteccao(e))


def cmd_ranking(a):
    import regenerar_mes as R
    arq = _arquivo_do_mes(a.mes)
    if not arq:
        sys.exit(f"Sem planilha para '{a.mes}' no manifest (veja: resumo.py meses).")
    novo = R.ler_ranking(os.path.join(RAIZ, arq))
    if a.vs:
        antigo = R.ler_ranking(a.vs)
        r = R.comparar_rankings(antigo, novo)
        print(f"{a.mes}: {r['agentes']} agentes | sobem {r['sobem']}, descem {r['descem']}, iguais {r['iguais']} | "
              f"maior alta {r['maior_alta']:+.1f} / queda {r['maior_queda']:+.1f} | média {r['media']:+.2f} | "
              f"posição mudou em {r['posicao_mudou']}" + (" | IDÊNTICO" if r["identico"] else ""))
        mud = sorted(((novo[k][4] or 0) - (antigo[k][4] or 0), k) for k in novo if k in antigo)
        for d, k in [x for x in mud if abs(x[0]) >= 0.05][:a.top]:
            print(f"  {d:+6.1f}  {k}  (pos {antigo[k][0]}→{novo[k][0]}, pts {antigo[k][4]:.1f}→{novo[k][4]:.1f})")
        return
    print(f"{a.mes} ({arq}) — {len(novo)} agentes")
    for k, v in sorted(novo.items(), key=lambda kv: kv[1][0])[:a.top]:
        print(f"  {v[0]:>3}  {v[4]:6.1f}  {k}  (trab {v[1]}, esp {v[2]}, turnos s/ trab {v[3]})")


def cmd_cronograma(a):
    cr = _json("data/cronograma_ausencias.json", [])
    achados = [e for e in cr if a.agente is None or str(e.get("id_agente")) == str(a.agente)]
    print(f"{len(achados)} lançamento(s):")
    for e in sorted(achados, key=lambda e: _d(e["inicio"])):
        print(f"  {e['inicio']}–{e['fim']} | {e.get('alvo','agente'):7} | {e.get('motivo')} | id {e.get('id_agente', '-')}")


def cmd_manifest(_a):
    for e in _json("data/historico/manifest.json", []):
        print(f"{e['arquivo']:28} {e.get('origem','?'):7} {e.get('label') or e.get('mes') or ''}"
              + (f" (reaberto {e['reaberto_em']})" if e.get("reaberto_em") else ""))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("meses").set_defaults(f=cmd_meses)
    d = sub.add_parser("deteccoes"); d.set_defaults(f=cmd_deteccoes)
    d.add_argument("--mes"); d.add_argument("--status", choices=["pendente", "confirmada", "falta"]); d.add_argument("--tipo", choices=list(TIPOS))
    r = sub.add_parser("ranking"); r.set_defaults(f=cmd_ranking)
    r.add_argument("mes"); r.add_argument("--top", type=int, default=10); r.add_argument("--vs")
    c = sub.add_parser("cronograma"); c.set_defaults(f=cmd_cronograma); c.add_argument("--agente")
    sub.add_parser("manifest").set_defaults(f=cmd_manifest)
    a = p.parse_args(argv)
    os.environ.setdefault("EVISITA_CPF", "x"); os.environ.setdefault("EVISITA_SENHA", "x")
    os.chdir(RAIZ)
    a.f(a)


if __name__ == "__main__":
    main()
