# -*- coding: utf-8 -*-
"""Funções auxiliares (nomes, turnos, motivo do cronograma) e argumentos da linha de comando.

Faz parte do pacote `scripts/coleta/` (antes tudo ficava em coletar_evisita.py).
"""
import logging
import argparse
import pandas as pd
from .parametros import (
    CRONOGRAMA_AUSENCIAS,
    ID_ANO,
    ID_CICLO,
    PASTA_SAIDA,
    PASTA_SEMANAS,
)

log = logging.getLogger("evisita")


                              # abaixo de 60 (< 60) -> 🔴 CRÍTICO

# ============================================================
# Fim dos parâmetros editáveis — o restante do código normalmente não
# precisa ser alterado.
# ============================================================

NOMES_DIA_SEMANA = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta",
                     4: "Sexta", 5: "Sábado", 6: "Domingo"}


def _fmt_hora_min(minutos_desde_meia_noite):
    """Formata minutos-desde-meia-noite como 'HHhMM' (ex.: 675 -> '11h15')."""
    h, m = divmod(minutos_desde_meia_noite, 60)
    return f"{h:02d}h{m:02d}"


# Preposições/conectivos que ficam em minúsculo em nomes próprios (exceto se
# forem a primeira palavra do nome).
_PREPOSICOES_NOME = {"de", "da", "do", "das", "dos", "e"}


def _formatar_nome_proprio(nome):
    """
    Formata nome em Title Case (primeira letra maiúscula de cada palavra),
    mantendo preposições comuns (de/da/do/das/dos/e) em minúsculo — exceto se
    forem a primeira palavra do nome. Ex.: 'ADRIANA DE JESUS SARAIVA' ->
    'Adriana de Jesus Saraiva'.
    """
    if not nome:
        return nome
    palavras = nome.strip().lower().split()
    if not palavras:
        return nome
    resultado = []
    for i, p in enumerate(palavras):
        if i > 0 and p in _PREPOSICOES_NOME:
            resultado.append(p)
        else:
            resultado.append(p[:1].upper() + p[1:])
    return " ".join(resultado)


def _entrada_vale_pro_turno(entrada, turno):
    """Entrada sem "turno" vale o dia inteiro (e só responde a consultas de
    dia inteiro e de qualquer turno). Entrada com "turno" (meia folga/meia
    ausência justificada) só vale pra consulta daquele turno."""
    t = entrada.get("turno")
    if not t:
        return True
    return turno is not None and str(t).strip().lower() == str(turno).strip().lower()


def _meios_turnos_no_dia(id_agente, equipe, dia_date, lista_cronograma=None):
    """Quantos TURNOS do dia estão justificados por entradas com "turno"
    (meia folga etc.) — 0, 1 ou 2. Usado pra descontar 0,5 dia esperado."""
    return sum(1 for t in ("Manhã", "Tarde")
               if _obter_motivo_cronograma(id_agente, equipe, dia_date, lista_cronograma, turno=t, so_turno=True))


def _obter_motivo_cronograma(id_agente, equipe, dia_date, lista_cronograma=None, turno=None, so_turno=False):
    """
    Verifica se (agente, equipe, dia) bate com alguma entrada da lista de
    cronograma (chuva, folga, atestado, reunião/treinamento, férias — alvo
    agente/equipe/todos). Se `lista_cronograma` não for passada, usa
    CRONOGRAMA_AUSENCIAS puro (sem as detecções automáticas confirmadas) —
    passe o resultado de _cronograma_efetivo() pra incluir elas também.
    dia_date é um objeto date. O intervalo início-fim é INCLUSIVO nas duas
    pontas. Retorna o motivo (string) se encontrado, senão None.
    """
    lista = lista_cronograma if lista_cronograma is not None else CRONOGRAMA_AUSENCIAS
    for entrada in lista:
        alvo = entrada.get("alvo", "agente")
        if alvo == "agente" and entrada.get("id_agente") != id_agente:
            continue
        if alvo == "equipe" and entrada.get("equipe") != equipe:
            continue
        # alvo == "todos": sempre bate, não precisa checar mais nada
        if not _entrada_vale_pro_turno(entrada, turno):
            continue
        if so_turno and not entrada.get("turno"):
            continue  # consulta só de meio-turno: ignora entradas de dia inteiro
        try:
            inicio = pd.to_datetime(entrada["inicio"], format="%d/%m/%Y").date()
            fim = pd.to_datetime(entrada["fim"], format="%d/%m/%Y").date()
        except (ValueError, KeyError):
            log.warning("Cronograma: entrada inválida (verifique o formato dd/mm/aaaa): %s", entrada)
            continue
        if inicio <= dia_date <= fim:
            return entrada.get("motivo", "Ausência programada")
    return None


def parse_args():
    """Permite sobrescrever ano/ciclo/pastas sem editar o código a cada rodada.

    --semana (HTML ID), se passado, força a coleta/recoleta de UMA semana
    específica em vez de deixar decidir_semanas_a_coletar() escolher
    automaticamente — útil pra reprocessar manualmente uma semana pontual.
    """
    p = argparse.ArgumentParser(description="Análise de tempo de visitas E-Visita")
    p.add_argument("--semana", type=int, default=None,
                    help="HTML ID de uma única semana a coletar/recoletar manualmente "
                         "(se omitido, o script decide sozinho quais semanas buscar)")
    p.add_argument("--id-ano", type=int, default=ID_ANO)
    p.add_argument("--id-ciclo", type=int, default=ID_CICLO)
    p.add_argument("--saida", type=str, default=PASTA_SAIDA)
    p.add_argument("--pasta-semanas", type=str, default=PASTA_SEMANAS)
    return p.parse_args()
