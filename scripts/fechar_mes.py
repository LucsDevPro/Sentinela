# -*- coding: utf-8 -*-
"""Fechar / reabrir um mês pela página validar.html.

  python scripts/fechar_mes.py checar [Mês/Ano]      -> JSON com o checklist (não grava nada)
  python scripts/fechar_mes.py fechar "Outubro/2026"
  python scripts/fechar_mes.py reabrir "Outubro/2026"

"Fechar" = arquivar: faz cópia de segurança da planilha, grava o mês em
data/meses_arquivados.json, marca o mês e as visões semanais dele como
"manual" no manifest (congelados). O mês seguinte já está em MESES_OFICIAIS e
passa a ser o mês vigente. "Reabrir" desfaz isso (cópia de segurança antes) e
só vale pra meses de MESES_OFICIAIS (os de Maio–Setembro seguem congelados).
Nada de dado sensível: o checklist só tem contagens.
"""
import json, os, shutil, sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
import meses_arquivados as mesarq  # noqa: E402

PASTA_HISTORICO = "data/historico"
PASTA_BACKUP = "data/historico/backup_congelado"
CAMINHO_DETECCOES = "data/deteccoes_pendentes.json"


def _ce():
    import coletar_evisita as ce
    return ce


def _ler(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return padrao


def _gravar(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _faixa(mes):
    ce = _ce()
    for ini, fim, nome in ce.MESES_OFICIAIS:
        if nome == mes:
            return ini, fim
    return None


def _intervalo_datas(ini, fim):
    import semanas_evisita as sem
    return sem.data_inicio_semana_html(ini), sem.data_fim_semana_html(fim) - timedelta(days=1)


def checar(mes, hoje=None, pasta_semanas="data/semanas", arquivados=None):
    """Checklist do mês. Cada item: {id, ok (True/False/None=confirmado pelo Worker), texto}."""
    ce = _ce()
    hoje = hoje or ce._hoje_local()
    arquivados = arquivados if arquivados is not None else mesarq.carregar()
    faixa = _faixa(mes)
    if faixa is None:
        return {"mes": mes, "pronto": False, "itens": [], "erro": "Esse mês não está cadastrado como mês aberto."}
    if any(n == mes for _, _, n in arquivados):
        return {"mes": mes, "pronto": False, "itens": [], "erro": "Esse mês já está fechado."}
    ini, fim = faixa
    d_ini, d_fim = _intervalo_datas(ini, fim)
    itens = []

    faltam = [h for h in range(ini, fim + 1) if not os.path.exists(os.path.join(pasta_semanas, f"{h}.xlsx"))]
    terminou = hoje > d_fim
    if faltam:
        itens.append({"id": "semanas", "ok": False, "texto": f"Faltam {len(faltam)} semana(s) coletada(s) do mês."})
    elif not terminou:
        itens.append({"id": "semanas", "ok": False,
                      "texto": f"O mês só termina em {d_fim.strftime('%d/%m/%Y')}: ainda faltam dias para coletar."})
    else:
        itens.append({"id": "semanas", "ok": True, "texto": f"Todas as {fim - ini + 1} semanas do mês foram coletadas."})

    seguinte = next((n for i, _, n in sorted(ce.MESES_OFICIAIS) if i > fim), None)
    prox_ini = next((i for i, _, n in ce.MESES_OFICIAIS if n == seguinte), None)
    if seguinte and ce.ciclo_tratamento_configurado(prox_ini) is not None:
        itens.append({"id": "proximo", "ok": True, "texto": f"O próximo mês ({seguinte}) está cadastrado."})
    else:
        itens.append({"id": "proximo", "ok": False,
                      "texto": "O próximo mês (e o número do ciclo dele) ainda não foi cadastrado no sistema."})

    pend = 0
    for e in _ler(CAMINHO_DETECCOES, []):
        if e.get("tipo") != "possiveis_ferias" or e.get("status") != "confirmada" or e.get("validada_por"):
            continue
        try:
            a = datetime.strptime(e["inicio"], "%d/%m/%Y").date()
            b = datetime.strptime(e["fim"], "%d/%m/%Y").date()
        except (KeyError, ValueError):
            continue
        if a <= d_fim and d_ini <= b:
            pend += 1
    itens.append({"id": "ferias", "ok": pend == 0,
                  "texto": "Nenhuma férias esperando validação." if pend == 0
                  else f"{pend} férias do mês ainda esperam validação."})

    itens.append({"id": "dias", "ok": None, "texto": "Nenhum dia sem trabalho esperando classificação (conferido pela página)."})
    itens.append({"id": "backup", "ok": True, "texto": "Cópia de segurança: feita automaticamente na hora de fechar."})
    pronto = all(i["ok"] in (True, None) for i in itens)
    return {"mes": mes, "pronto": pronto, "itens": itens,
            "periodo": f"{d_ini.strftime('%d/%m/%Y')} a {d_fim.strftime('%d/%m/%Y')}"}


def _backup(arquivo, sufixo):
    origem = os.path.join(PASTA_HISTORICO, arquivo)
    if not os.path.exists(origem):
        return None
    os.makedirs(PASTA_BACKUP, exist_ok=True)
    nome = f"{os.path.splitext(arquivo)[0]}_{sufixo}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.xlsx"
    shutil.copy2(origem, os.path.join(PASTA_BACKUP, nome))
    return nome


def fechar(mes, regenerar=True, hoje=None, pasta_semanas="data/semanas"):
    """Devolve (ok, mensagem)."""
    r = checar(mes, hoje=hoje, pasta_semanas=pasta_semanas)
    if r.get("erro"):
        return False, f"❌ {r['erro']}"
    bloqueios = [i["texto"] for i in r["itens"] if i["ok"] is False]
    if bloqueios:
        return False, "❌ Ainda não dá para fechar " + mes + ": " + " ".join(bloqueios)
    ce = _ce()
    ini, fim = _faixa(mes)
    if regenerar:   # garante que a planilha congelada é a versão mais recente do cache
        ce.atualizar_historico_do_cache()
    manifest = _ler(os.path.join(PASTA_HISTORICO, "manifest.json"), [])
    entrada = next((e for e in manifest if e.get("label") == mes and e.get("tipo") != "semana"), None)
    if not entrada or not os.path.exists(os.path.join(PASTA_HISTORICO, entrada["arquivo"])):
        return False, f"❌ Não achei a planilha de {mes} no histórico. Rode a coleta antes de fechar."
    _backup(entrada["arquivo"], "antes-de-fechar")
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    for e in manifest:
        if e is entrada or (e.get("tipo") == "semana" and e.get("mes") == mes):
            e["origem"] = "manual"
            e["fechado_em"] = agora
            if e.get("tipo") == "semana":
                e["parcial"] = False
    _gravar(os.path.join(PASTA_HISTORICO, "manifest.json"), manifest)
    lista = mesarq.carregar()
    lista.append((ini, fim, mes))
    mesarq.gravar(lista)
    return True, f"✅ {mes} fechado e congelado. Cópia de segurança guardada. O mês seguinte passa a ser o mês aberto."


def reabrir(mes, confirmacao, regenerar=True):
    if str(confirmacao).strip().lower() != mes.strip().lower():
        return False, "❌ Para reabrir, digite o nome do mês exatamente (ex.: Outubro/2026)."
    if _faixa(mes) is None:
        return False, f"❌ {mes} não pode ser reaberto por aqui (é um mês antigo congelado). Peça ao desenvolvedor."
    lista = mesarq.carregar()
    if not any(n == mes for _, _, n in lista):
        return False, f"❌ {mes} não está fechado."
    manifest = _ler(os.path.join(PASTA_HISTORICO, "manifest.json"), [])
    for e in manifest:
        if e.get("label") == mes and e.get("tipo") != "semana":
            _backup(e["arquivo"], "antes-de-reabrir")
    for e in manifest:
        if (e.get("label") == mes and e.get("tipo") != "semana") or (e.get("tipo") == "semana" and e.get("mes") == mes):
            e["origem"] = "cache"
            e.pop("fechado_em", None)
            e["reaberto_em"] = datetime.now().strftime("%d/%m/%Y")
    _gravar(os.path.join(PASTA_HISTORICO, "manifest.json"), manifest)
    mesarq.gravar([t for t in lista if t[2] != mes])
    if regenerar:
        # a lista já mudou no disco; recarrega a constante antes de regenerar
        ce = _ce()
        ce.MESES_ARQUIVADOS[:] = mesarq.carregar()
        ce.atualizar_historico_do_cache()
    return True, f"✅ {mes} reaberto (cópia de segurança feita). A próxima coleta volta a recalcular este mês."


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "checar"
    mes = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "checar":
        ce = _ce()
        alvo = mes or next((n for _, _, n in ce.MESES_OFICIAIS if not any(n == a for _, _, a in mesarq.carregar())), None)
        print(json.dumps(checar(alvo), ensure_ascii=False))
    elif cmd in ("fechar", "reabrir") and mes:
        ok, msg = fechar(mes) if cmd == "fechar" else reabrir(mes, mes)
        print(msg)
        sys.exit(0 if ok else 1)
    else:
        print("Uso: fechar_mes.py checar|fechar|reabrir [Mês/Ano]")
        sys.exit(2)
