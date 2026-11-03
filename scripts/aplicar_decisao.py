"""Aplica UMA decisão vinda da página validar.html (via Worker → repository_dispatch).

Entrada: variável de ambiente DECISAO com um JSON:
  {"acao": ..., "quem": "Nome da coordenação", "id_agente": 85,
   "inicio": "dd/mm/aaaa", "fim": "dd/mm/aaaa", "tipo": ..., "turno": "Manhã"|"Tarde"}

Ações:
  ferias_confirmar  marca as férias detectadas como validadas por <quem>
  ferias_nao        "não é férias": os dias viram FALTA (cancelar)
  ferias_ajustar    novo período final das férias (máx. 30 dias)
  lancar            tipo = ferias | ausencia_justificada | folga | meia_folga |
                           meia_ausencia_justificada   (as "meia_*" exigem turno)
  remover           desfaz um lançamento do cronograma (mesmos campos de "lancar")
  ajuste            ajuste manual de pontos: id_agente, data, pontos (±20), motivo (3–80 letras)
  ajuste_remover    desfaz um ajuste (mesmos campos)
  parada            equipe parada: alvo "equipe"|"todos", equipe, motivo, inicio, fim, turno (opcional)
  parada_remover    desfaz uma parada (mesmos campos)
  fechar_mes        arquiva o mês (mes = "Outubro/2026"); reabrir_mes exige confirmacao = nome do mês

Repositório PÚBLICO: o atestado é sempre gravado como "Ausência justificada"
(nunca "Atestado", CID ou diagnóstico).
Saída: mensagem (comentário/log); código 0 = ok, 1 = recusado (nada gravado).
"""
import json, os, re, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import lancar_ausencia as lau
import meses_arquivados as mesarq
import semanas_evisita as sem

CAMINHO_CRONOGRAMA = "data/cronograma_ausencias.json"
CAMINHO_NOMES = "data/agentes_nomes.json"
CAMINHO_DETECCOES = lau.CAMINHO_DETECCOES

TIPOS_CRONOGRAMA = {
    "ausencia_justificada": ("Ausência justificada", False),
    "folga": ("Folga", False),
    "meia_folga": ("Meia folga", True),
    "meia_ausencia_justificada": ("Meia ausência justificada", True),
}
TURNOS = ("Manhã", "Tarde")
LIMITE_DIAS_CRONOGRAMA = 60
CAMINHO_AJUSTES = "data/ajustes_ranking.json"
LIMITE_AJUSTE_PONTOS = 20.0
PARADAS = ("Chuva", "Reunião/Treinamento", "Levantamento de Índice", "Instalação de Ovitrampa",
           "Recolha de Ovitrampa", "Recuperação de Casas")
LIMITE_DIAS_PARADA = 30
# O motivo do ajuste aparece no Extrato PÚBLICO: nada de dado de saúde.
_PROIBIDO_NO_MOTIVO = re.compile(r"atestad|\bcid\b|doen[çc]|diagn[óo]s|m[ée]dic|sa[úu]de|laudo|cirurgi|depress|ansied", re.I)


def _ler(caminho, padrao):
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _gravar(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _datas(dec):
    try:
        ini = datetime.strptime(str(dec.get("inicio", "")), "%d/%m/%Y").date()
        fim = datetime.strptime(str(dec.get("fim", "")), "%d/%m/%Y").date()
    except ValueError:
        return None, None, "Datas inválidas. Use o formato dd/mm/aaaa."
    if fim < ini:
        return None, None, "O último dia não pode ser antes do primeiro dia."
    return ini, fim, None


def _entrada_cronograma(dec, nomes):
    """Valida e monta a entrada do cronograma. Devolve (entrada, erro)."""
    tipo = dec.get("tipo")
    if tipo not in TIPOS_CRONOGRAMA:
        return None, f"Tipo de lançamento desconhecido: {tipo!r}."
    motivo, exige_turno = TIPOS_CRONOGRAMA[tipo]
    ini, fim, erro = _datas(dec)
    if erro:
        return None, erro
    if (fim - ini).days + 1 > LIMITE_DIAS_CRONOGRAMA:
        return None, f"Período maior que {LIMITE_DIAS_CRONOGRAMA} dias — confira as datas."
    entrada = {"alvo": "agente", "id_agente": int(dec["id_agente"]), "motivo": motivo,
               "inicio": ini.strftime("%d/%m/%Y"), "fim": fim.strftime("%d/%m/%Y")}
    if exige_turno:
        if dec.get("turno") not in TURNOS:
            return None, "Escolha o turno (Manhã ou Tarde) para meia folga / meia ausência."
        entrada["turno"] = dec["turno"]
    return entrada, None


def _motivo_ajuste(txt):
    """Limpa e valida o motivo do ajuste. Devolve (motivo, erro)."""
    m = re.sub(r"[\x00-\x1f<>]", " ", str(txt or ""))
    m = re.sub(r"\s+", " ", m).strip()
    if len(m) < 3:
        return None, "Escreva o motivo (pelo menos 3 letras)."
    if len(m) > 80:
        return None, "Motivo muito longo (máximo 80 letras)."
    if _PROIBIDO_NO_MOTIVO.search(m):
        return None, "O motivo aparece publicamente no Extrato: não escreva dados de saúde nem atestado."
    return m, None


def _mes_arquivado_da_data(d, arquivados=None):
    h = sem.html_id_da_data(d)
    for ini, fim, nome in (arquivados if arquivados is not None else mesarq.carregar()):
        if ini <= h <= fim:
            return nome
    return None


def _aplicar_ajuste(dec, nomes, caminho_ajustes, quem, remover):
    try:
        id_ag = int(dec.get("id_agente"))
        d = datetime.strptime(str(dec.get("data", "")), "%d/%m/%Y").date()
        pontos = round(float(dec.get("pontos")), 2)
    except (TypeError, ValueError):
        return False, "❌ Ajuste inválido: confira agente, data e pontos."
    if str(id_ag) not in nomes:
        return False, "❌ Agente não reconhecido."
    nome = nomes[str(id_ag)].get("nome", "")
    if pontos == 0 or abs(pontos) > LIMITE_AJUSTE_PONTOS:
        return False, f"❌ Os pontos devem ser diferentes de zero e no máximo ±{LIMITE_AJUSTE_PONTOS:g}."
    motivo, erro = _motivo_ajuste(dec.get("motivo"))
    if erro:
        return False, f"❌ {erro}"
    arq = _mes_arquivado_da_data(d)
    if arq:
        return False, f"❌ {arq} está fechado. Reabra o mês antes de ajustar pontos nele."
    lista = _ler(caminho_ajustes, [])
    chave = lambda a: (int(a["id_agente"]), a["data"], round(float(a["pontos"]), 2), a["motivo"])
    alvo = (id_ag, d.strftime("%d/%m/%Y"), pontos, motivo)
    achados = [a for a in lista if chave(a) == alvo]
    sinal = f"{pontos:+g}".replace(".", ",")
    if remover:
        if not achados:
            return False, "❌ Não encontrei esse ajuste para desfazer."
        lista.remove(achados[0])
        _gravar(caminho_ajustes, lista)
        return True, f"✅ Ajuste desfeito: **{nome}**, {alvo[1]}, {sinal} pontos (por {quem})."
    if achados:
        return True, f"ℹ️ Esse ajuste de **{nome}** já existia."
    lista.append({"id_agente": id_ag, "data": alvo[1], "pontos": pontos, "motivo": motivo, "por": quem})
    _gravar(caminho_ajustes, lista)
    return True, f"✅ Ajuste lançado: **{nome}**, {alvo[1]}, {sinal} pontos — {motivo} (por {quem})."


def _aplicar_parada(dec, nomes, caminho_cron, quem, remover):
    ini, fim, erro = _datas(dec)
    if erro:
        return False, f"❌ {erro}"
    if (fim - ini).days + 1 > LIMITE_DIAS_PARADA:
        return False, f"❌ Parada maior que {LIMITE_DIAS_PARADA} dias — confira as datas."
    motivo = dec.get("motivo")
    if motivo not in PARADAS:
        return False, f"❌ Motivo de parada desconhecido: {motivo!r}."
    alvo = dec.get("alvo")
    entrada = {"alvo": alvo, "motivo": motivo, "inicio": ini.strftime("%d/%m/%Y"), "fim": fim.strftime("%d/%m/%Y")}
    if alvo == "equipe":
        equipes = {a.get("equipe") for a in nomes.values()}
        if dec.get("equipe") not in equipes:
            return False, "❌ Equipe não reconhecida."
        entrada = {"alvo": "equipe", "equipe": dec["equipe"], **{k: entrada[k] for k in ("motivo", "inicio", "fim")}}
    elif alvo != "todos":
        return False, "❌ Escolha uma equipe ou todas."
    if dec.get("turno"):
        if dec["turno"] not in TURNOS:
            return False, "❌ Turno inválido (Manhã ou Tarde)."
        entrada["turno"] = dec["turno"]
    quem_alvo = entrada.get("equipe", "todas as equipes")
    quando = f"{entrada['inicio']} a {entrada['fim']}" + (f", {entrada['turno']}" if entrada.get("turno") else "")
    if not remover:
        arq = _mes_arquivado_da_data(ini)
        arq2 = _mes_arquivado_da_data(fim)
        if arq or arq2:
            return False, f"❌ {arq or arq2} está fechado. Reabra o mês antes de lançar parada nele."
    cron = _ler(caminho_cron, [])
    if remover:
        if entrada not in cron:
            return False, "❌ Não encontrei essa parada para remover."
        cron.remove(entrada)
        _gravar(caminho_cron, cron)
        return True, f"✅ Parada removida: {motivo}, {quem_alvo}, {quando} (por {quem})."
    if entrada in cron:
        return True, f"ℹ️ Essa parada de {quem_alvo} já existia."
    cron.append(entrada)
    _gravar(caminho_cron, cron)
    return True, f"✅ Parada lançada: {motivo}, {quem_alvo}, {quando} (por {quem})."


def aplicar(dec, caminho_cron=CAMINHO_CRONOGRAMA, caminho_nomes=CAMINHO_NOMES, caminho_det=CAMINHO_DETECCOES,
            caminho_ajustes=CAMINHO_AJUSTES):
    nomes = _ler(caminho_nomes, {})
    quem0 = str(dec.get("quem") or "coordenação")[:60]
    acao0 = dec.get("acao")
    if acao0 in ("parada", "parada_remover"):
        return _aplicar_parada(dec, nomes, caminho_cron, quem0, acao0 == "parada_remover")
    if acao0 in ("ajuste", "ajuste_remover"):
        return _aplicar_ajuste(dec, nomes, caminho_ajustes, quem0, acao0 == "ajuste_remover")
    if acao0 in ("fechar_mes", "reabrir_mes"):
        import fechar_mes as fm
        mes = str(dec.get("mes", ""))[:30]
        if acao0 == "fechar_mes":
            return fm.fechar(mes)
        return fm.reabrir(mes, dec.get("confirmacao", ""))
    try:
        id_ag = int(dec.get("id_agente"))
    except (TypeError, ValueError):
        return False, "❌ Agente inválido."
    if str(id_ag) not in nomes:
        return False, "❌ Agente não reconhecido."
    dec = dict(dec, id_agente=id_ag)
    ag = nomes[str(id_ag)]
    nome, equipe = ag.get("nome", ""), ag.get("equipe", "")
    quem = str(dec.get("quem") or "coordenação")[:60]
    acao = dec.get("acao")

    if acao in ("ferias_confirmar", "ferias_nao", "ferias_ajustar") or (acao == "lancar" and dec.get("tipo") == "ferias"):
        ini, fim, erro = _datas(dec)
        if erro:
            return False, f"❌ {erro}"
        lista = _ler(caminho_det, [])
        if acao == "ferias_confirmar":
            tocadas = [e for e in lista if e.get("tipo") == "possiveis_ferias" and e.get("id_agente") == id_ag
                       and e.get("status") == "confirmada"
                       and lau._d(e["inicio"]) <= fim and ini <= lau._d(e["fim"])]
            if not tocadas:
                return False, "❌ Não encontrei férias confirmadas desse agente nesse período."
            for e in tocadas:
                e["validada_por"] = quem
                e["validada_em"] = datetime.now().strftime("%d/%m/%Y %H:%M")
                e.pop("revisao_classificacao_necessaria", None)
                e.pop("nota_revisao_classificacao", None)
            ok, msg = True, f"✅ Férias de **{nome}** validadas por {quem}."
        else:
            req = {"id_agente": id_ag, "ini": ini, "fim": fim,
                   "acao": lau.ACAO_CANCELAR if acao == "ferias_nao" else lau.ACAO_DEFINIR}
            if req["acao"] == lau.ACAO_DEFINIR and (fim - ini).days + 1 > lau.LIMITE_FERIAS_DIAS:
                return False, ("❌ Férias têm no máximo 30 dias corridos. Lance até 30 dias; "
                               "o que passar disso conta como falta.")
            ok, msg = lau.aplicar_ferias(lista, req, (nome, equipe), quem=quem)
        if ok:
            _gravar(caminho_det, lista)
        return ok, msg

    if acao in ("lancar", "remover"):
        entrada, erro = _entrada_cronograma(dec, nomes)
        if erro:
            return False, f"❌ {erro}"
        cron = _ler(caminho_cron, [])
        if acao == "lancar":
            if entrada in cron:
                return True, f"ℹ️ Esse lançamento de **{nome}** já existia."
            cron.append(entrada)
            _gravar(caminho_cron, cron)
            alvo = entrada["motivo"] + (f" ({entrada['turno']})" if entrada.get("turno") else "")
            return True, f"✅ {alvo} lançada: **{nome}**, {entrada['inicio']} a {entrada['fim']} (por {quem})."
        if entrada not in cron:
            return False, "❌ Não encontrei esse lançamento para remover."
        cron.remove(entrada)
        _gravar(caminho_cron, cron)
        return True, f"✅ Lançamento removido: **{nome}**, {entrada['inicio']} a {entrada['fim']} (por {quem})."

    return False, f"❌ Ação desconhecida: {acao!r}."


if __name__ == "__main__":
    try:
        dec = json.loads(os.environ.get("DECISAO", "{}"))
        if not isinstance(dec, dict):
            raise ValueError("não é objeto")
    except (json.JSONDecodeError, ValueError):
        print("❌ Decisão ilegível.")
        sys.exit(1)
    ok, msg = aplicar(dec)
    print(msg)
    sys.exit(0 if ok else 1)
