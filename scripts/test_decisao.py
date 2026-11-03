# -*- coding: utf-8 -*-
"""Testes de scripts/aplicar_decisao.py (ações da página validar.html), do suporte a
meio turno no motor do ranking e das sugestões de classificação dos dias sem trabalho."""
import sys
import types
import json
from datetime import date, datetime

import pandas as pd

# --- stubs pros módulos de navegador, só pra permitir o import -------------
for nome in ("selenium", "selenium.webdriver", "selenium.webdriver.common",
             "selenium.webdriver.common.by", "selenium.webdriver.chrome",
             "selenium.webdriver.chrome.options", "selenium.webdriver.support",
             "selenium.webdriver.support.ui", "selenium.webdriver.support.expected_conditions"):
    mod = types.ModuleType(nome)
    sys.modules.setdefault(nome, mod)
sys.modules["selenium"].webdriver = sys.modules["selenium.webdriver"]
sys.modules["selenium.webdriver"].common = sys.modules["selenium.webdriver.common"]
sys.modules["selenium.webdriver"].chrome = sys.modules["selenium.webdriver.chrome"]
sys.modules["selenium.webdriver"].support = sys.modules["selenium.webdriver.support"]
sys.modules["selenium.webdriver.common"].by = sys.modules["selenium.webdriver.common.by"]
sys.modules["selenium.webdriver.common.by"].By = type("By", (), {})
sys.modules["selenium.webdriver.chrome"].options = sys.modules["selenium.webdriver.chrome.options"]
sys.modules["selenium.webdriver.chrome.options"].Options = type("Options", (), {})
sys.modules["selenium.webdriver.support"].ui = sys.modules["selenium.webdriver.support.ui"]
sys.modules["selenium.webdriver.support.ui"].WebDriverWait = type("WebDriverWait", (), {})
sys.modules["selenium.webdriver.support"].expected_conditions = sys.modules[
    "selenium.webdriver.support.expected_conditions"]

import os
os.environ.setdefault("EVISITA_CPF", "00000000000")
os.environ.setdefault("EVISITA_SENHA", "teste")

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import coletar_evisita as ce  # noqa: E402
import datetime as _dt  # noqa: E402
ce.HOJE_OVERRIDE = _dt.date(2027, 1, 1)  # hoje fixo nos testes

FALHAS = []


def checar(nome, condicao, detalhe=""):
    status = "OK  " if condicao else "FALHOU"
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


def d(s):
    return datetime.strptime(s, "%d/%m/%Y").date()


def montar_resultado(id_agente, nome, equipe, dias_com_visita):
    """Monta um item de `resultados` só com o necessário pras funções de
    detecção (id_agente/nome_agente/equipe/df, coluna 'dia')."""
    df = pd.DataFrame({"dia": sorted(dias_com_visita)}) if dias_com_visita else pd.DataFrame({"dia": []})
    return {"id_agente": id_agente, "nome_agente": nome, "equipe": equipe, "df": df}


def montar_df_total(resultados):
    linhas = []
    for r in resultados:
        for dia in r["df"]["dia"]:
            linhas.append({"id_agente": r["id_agente"], "dia": dia})
    return pd.DataFrame(linhas)


def dias_uteis_entre(ini, fim):
    return [dd for dd in ce._dias_uteis_no_intervalo(d(ini), d(fim))]



import tempfile
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import aplicar_decisao as ad  # noqa: E402
import publicar_sugestoes as ps  # noqa: E402
from datetime import time as _t  # noqa: E402

NOMES = {"85": {"nome": "Adriano Teste", "equipe": "Equipe 1"}, "86": {"nome": "Bia Teste", "equipe": "Equipe 2"}}


def ambiente(extra_det=()):
    pasta = tempfile.mkdtemp()
    nomes, cron, det = (os.path.join(pasta, n) for n in ("n.json", "c.json", "d.json"))
    json.dump(NOMES, open(nomes, "w")); json.dump([], open(cron, "w"))
    json.dump([{"tipo": "possiveis_ferias", "id_agente": 85, "nome_agente": "Adriano Teste", "equipe": "Equipe 1",
                "inicio": "28/09/2026", "fim": "27/10/2026", "duracao": 22, "status": "confirmada",
                "motivo": "Férias", "revisao_classificacao_necessaria": True,
                "nota_revisao_classificacao": "x"}] + list(extra_det), open(det, "w"))
    def A(**dec):
        return ad.aplicar(dec, cron, nomes, det)
    lerc = lambda: json.load(open(cron))
    lerd = lambda: json.load(open(det))
    return A, lerc, lerd


def base(**kw):
    d = {"quem": "Maria", "id_agente": 85, "inicio": "10/10/2026", "fim": "10/10/2026"}
    d.update(kw)
    return d


def teste_lancamentos():
    A, lerc, lerd = ambiente()
    ok, msg = A(**base(acao="lancar", tipo="ausencia_justificada"))
    checar("Lançar ausência justificada grava rótulo neutro", ok and lerc()[0]["motivo"] == "Ausência justificada", msg)
    checar("Nunca grava a palavra 'Atestado' nos dados públicos", "Atestado" not in json.dumps(lerc()))
    ok, msg = A(**base(acao="lancar", tipo="ausencia_justificada"))
    checar("Repetir não duplica", ok and len(lerc()) == 1, msg)
    ok, msg = A(**base(acao="lancar", tipo="folga", inicio="12/10/2026", fim="13/10/2026"))
    checar("Folga de 2 dias", ok and lerc()[1]["motivo"] == "Folga")
    ok, _ = A(**base(acao="lancar", tipo="meia_folga"))
    checar("Meia folga sem turno é recusada", not ok)
    ok, _ = A(**base(acao="lancar", tipo="meia_folga", turno="Manhã", inicio="14/10/2026", fim="14/10/2026"))
    checar("Meia folga com turno grava o turno", ok and lerc()[-1].get("turno") == "Manhã" and lerc()[-1]["motivo"] == "Meia folga")
    ok, _ = A(**base(acao="lancar", tipo="meia_ausencia_justificada", turno="Tarde", inicio="15/10/2026", fim="15/10/2026"))
    checar("Meia ausência justificada com turno", ok and lerc()[-1]["motivo"] == "Meia ausência justificada")
    antes = json.dumps(lerc())
    for nome, dec in [("tipo inválido", base(acao="lancar", tipo="xpto")),
                      ("agente inexistente", base(acao="lancar", tipo="folga", id_agente=999)),
                      ("data inválida", base(acao="lancar", tipo="folga", inicio="31/02/2026")),
                      ("fim antes do início", base(acao="lancar", tipo="folga", inicio="12/10/2026", fim="11/10/2026")),
                      ("período de 90 dias", base(acao="lancar", tipo="folga", inicio="01/07/2026", fim="30/09/2026")),
                      ("ação desconhecida", base(acao="apagar"))]:
        ok, _ = A(**dec)
        checar(f"Recusa: {nome}", (not ok) and json.dumps(lerc()) == antes)
    ok, _ = A(**base(acao="remover", tipo="folga", inicio="12/10/2026", fim="13/10/2026"))
    checar("Remover lançamento", ok and not any(e["motivo"] == "Folga" for e in lerc()))
    ok, _ = A(**base(acao="remover", tipo="folga", inicio="12/10/2026", fim="13/10/2026"))
    checar("Remover algo que não existe é recusado", not ok)


def teste_decisoes_de_ferias():
    A, lerc, lerd = ambiente()
    ok, _ = A(**base(acao="ferias_confirmar", inicio="01/10/2026", fim="05/10/2026"))
    e = lerd()[0]
    checar("Confirmar: marca quem validou e limpa o aviso de revisão",
           ok and e.get("validada_por") == "Maria" and "revisao_classificacao_necessaria" not in e, str(e))
    ok, msg = A(**base(acao="ferias_ajustar", inicio="28/09/2026", fim="30/10/2026"))
    checar("Ajustar acima de 30 dias é recusado", not ok, msg)
    ok, _ = A(**base(acao="ferias_ajustar", inicio="28/09/2026", fim="20/10/2026"))
    checar("Ajustar encurta e protege (ajustado_manual)", ok and lerd()[0]["fim"] == "20/10/2026" and lerd()[0].get("ajustado_manual"))
    ok, _ = A(**base(acao="ferias_nao", inicio="10/10/2026", fim="20/10/2026"))
    st = sorted((x["inicio"], x["fim"], x["status"]) for x in lerd())
    checar("'Não é férias' vira falta só nos dias indicados",
           ok and ("10/10/2026", "20/10/2026", "falta") in st and ("28/09/2026", "09/10/2026", "confirmada") in st, str(st))
    ok, _ = A(**base(acao="lancar", tipo="ferias", id_agente=86, inicio="01/11/2026", fim="20/11/2026"))
    checar("Lançar férias novas cria entrada manual", ok and any(x["id_agente"] == 86 and x["status"] == "confirmada" for x in lerd()))
    ok, _ = A(**base(acao="ferias_confirmar", inicio="01/03/2026", fim="05/03/2026"))
    checar("Confirmar período sem férias é recusado", not ok)
    # "Era férias": a falta de excesso vira férias só nos dias indicados
    A2, lerc2, lerd2 = ambiente(extra_det=[{
        "tipo": "possiveis_ferias", "id_agente": 85, "nome_agente": "Adriano Teste", "equipe": "Equipe 1",
        "inicio": "28/10/2026", "fim": "05/11/2026", "duracao": 7, "status": "falta",
        "motivo": "Falta (passou de 30 dias de férias)"}])
    ok, _ = A2(**base(acao="ferias_ajustar", inicio="28/10/2026", fim="30/10/2026"))
    st = sorted((x["inicio"], x["fim"], x["status"]) for x in lerd2())
    checar("Ajustar sobre uma falta transforma esses dias em férias e mantém o resto como falta",
           ok and ("28/10/2026", "30/10/2026", "confirmada") in st and ("31/10/2026", "05/11/2026", "falta") in st, str(st))


def teste_meio_turno_no_motor():
    cron = [{"alvo": "agente", "id_agente": 1, "motivo": "Meia folga", "turno": "Manhã",
             "inicio": "14/10/2026", "fim": "14/10/2026"},
            {"alvo": "agente", "id_agente": 1, "motivo": "Folga", "inicio": "15/10/2026", "fim": "15/10/2026"}]
    dia14, dia15, dia16 = d("14/10/2026"), d("15/10/2026"), d("16/10/2026")
    f = ce._obter_motivo_cronograma
    checar("Meia folga vale só no turno indicado", f(1, "E", dia14, cron, turno="Manhã") and not f(1, "E", dia14, cron, turno="Tarde"))
    checar("Meia folga não vale como dia inteiro", f(1, "E", dia14, cron) is None)
    checar("Folga de dia inteiro vale nos dois turnos", f(1, "E", dia15, cron, turno="Manhã") and f(1, "E", dia15, cron, turno="Tarde"))
    checar("Meios turnos do dia contados (0,5 dia esperado por turno)",
           ce._meios_turnos_no_dia(1, "E", dia14, cron) == 1 and ce._meios_turnos_no_dia(1, "E", dia15, cron) == 0
           and ce._meios_turnos_no_dia(1, "E", dia16, cron) == 0)
    # nas ausências: manhã justificada -> só a tarde aparece como sem lançamento
    linhas = [{"id_agente": 1, "dia": dia, "hora_chegada": h} for dia in (d("13/10/2026"), d("16/10/2026")) for h in (9.0, 14.0)]
    df = pd.DataFrame(linhas)
    res = [{"id_agente": 1, "nome_agente": "A", "equipe": "Equipe 1", "df": df}]
    regs = ce._preparar_ausencias(df, res, cron, primeira_visita={1: d("01/06/2026")})
    turnos14 = sorted(r["turno"] for r in regs if r["dia_fmt"] == "14/10/2026")
    checar("Ausências: com meia folga de manhã só a tarde fica sem lançamento", turnos14 == ["Tarde"], str(turnos14))
    checar("Ausências: dia com folga inteira não gera ausência", not any(r["dia_fmt"] == "15/10/2026" for r in regs))


def teste_sugestoes():
    D = d
    linhas = [
        (1, "Ana", "Equipe 1", D("06/10/2026"), "Manhã"),
        (1, "Ana", "Equipe 1", D("13/10/2026"), "Manhã"), (1, "Ana", "Equipe 1", D("13/10/2026"), "Tarde"),
        (1, "Ana", "Equipe 1", D("14/10/2026"), "Manhã"), (1, "Ana", "Equipe 1", D("14/10/2026"), "Tarde"),
        (2, "Beto", "Equipe 2", D("09/10/2026"), "Manhã"), (2, "Beto", "Equipe 2", D("09/10/2026"), "Tarde"),
        (2, "Beto", "Equipe 2", D("12/10/2026"), "Manhã"), (2, "Beto", "Equipe 2", D("12/10/2026"), "Tarde"),  # sex -> seg
        (3, "Caio", "Equipe Bloqueio", D("06/10/2026"), "Manhã"),
    ]
    itens = ps.montar_sugestoes(linhas)
    por = {(i["id_agente"], i["inicio"]): i for i in itens}
    checar("Sugestões: dias separados viram períodos separados", (1, "06/10/2026") in por and (1, "13/10/2026") in por, str(list(por)))
    checar("Sugestões: dias consecutivos agrupam", por[(1, "13/10/2026")]["fim"] == "14/10/2026")
    checar("Sugestões: sexta + segunda são consecutivos (fim de semana não quebra)",
           (2, "09/10/2026") in por and por[(2, "09/10/2026")]["fim"] == "12/10/2026")
    checar("Sugestões: só um turno sugere meia folga", "meia" in por[(1, "06/10/2026")]["sugestao"].lower())
    checar("Sugestões: equipe sob demanda (Bloqueio) fica de fora", not any(i["id_agente"] == 3 for i in itens))
    checar("Sugestões: nunca carrega CID/diagnóstico", "cid" not in json.dumps(itens).lower())


if __name__ == "__main__":
    teste_lancamentos()
    teste_decisoes_de_ferias()
    teste_meio_turno_no_motor()
    teste_sugestoes()
    print()
    if FALHAS:
        print(f"❌ {len(FALHAS)} teste(s) falharam: {FALHAS}")
        sys.exit(1)
    print("✅ Todos os testes de decisões passaram.")
