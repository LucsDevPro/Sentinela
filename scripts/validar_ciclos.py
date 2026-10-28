# -*- coding: utf-8 -*-
"""
Confere se TODA semana já iniciada tem o id_ciclo cadastrado (Tratamento e
Ponto Estratégico) em scripts/coletar_evisita.py — evita repetir o problema de
Outubro/2026, em que o mês virou e ninguém cadastrou o ciclo novo: a coleta
usou o ciclo antigo, voltou vazia e ninguém percebeu.

 - ERRO  (sai com código 1): semana já iniciada (até a semana atual) sem ciclo
   de Tratamento, sem ciclo de P.E. (quando há agente de P.E.) ou fora de
   MESES_OFICIAIS (a página do mês não seria montada direito).
 - AVISO (não falha): alguma das próximas semanas ainda sem ciclo — é só um
   lembrete pra cadastrar assim que o e-Visita abrir o ciclo novo.

No GitHub Actions escreve o resultado no resumo da execução
($GITHUB_STEP_SUMMARY) e emite anotações ::error::/::warning::.

Uso: python3 scripts/validar_ciclos.py [--hoje AAAA-MM-DD]
"""
import argparse
import os
import sys
from datetime import date, datetime

os.environ.setdefault("EVISITA_CPF", "validacao")     # só pra poder importar o módulo
os.environ.setdefault("EVISITA_SENHA", "validacao")   # (nenhuma requisição é feita)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coletar_evisita as C  # noqa: E402

SEMANAS_A_FRENTE_AVISO = 3


def conferir(hoje=None):
    """Devolve (erros, avisos) — listas de mensagens."""
    atual = C.semana_atual(hoje)
    erros, avisos = [], []
    for h in range(C.PRIMEIRA_SEMANA_CICLO_EXPLICITO, atual + SEMANAS_A_FRENTE_AVISO + 1):
        problemas = []
        if C.ciclo_tratamento_configurado(h) is None:
            problemas.append("sem id_ciclo de Tratamento em CICLOS_TRATAMENTO")
        if C.AGENTES_PONTO_ESTRATEGICO and C.ciclo_para_semana(h) is None:
            problemas.append("sem id_ciclo de Ponto Estratégico em CICLOS_PONTO_ESTRATEGICO")
        if C._grupo_mes_oficial(h) is None:
            problemas.append("fora de MESES_OFICIAIS (não entra em nenhuma página mensal)")
        if not problemas:
            continue
        msg = f"Semana {h} ({C.sem.rotulo_semana_html(h)}): " + "; ".join(problemas)
        (erros if h <= atual else avisos).append(msg)
    return erros, avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hoje", default=None, help="AAAA-MM-DD (padrão: hoje)")
    args = ap.parse_args()
    hoje = datetime.strptime(args.hoje, "%Y-%m-%d").date() if args.hoje else None
    erros, avisos = conferir(hoje)

    linhas = ["## 🔎 Conferência de ciclos do e-Visita", ""]
    if not erros and not avisos:
        linhas.append("✅ Todas as semanas até agora (e as próximas) têm ciclo cadastrado.")
    for e in erros:
        linhas.append(f"- ❌ {e}")
        print(f"::error title=Ciclo do e-Visita não cadastrado::{e}")
    for a in avisos:
        linhas.append(f"- ⚠️ {a} (cadastre quando o e-Visita abrir o ciclo novo)")
        print(f"::warning title=Próximo ciclo ainda não cadastrado::{a}")
    if erros:
        linhas += ["", "**Como corrigir:** copie o `id_ciclo` e as semanas da URL da consulta no e-Visita e "
                       "cadastre uma linha em `MESES_OFICIAIS`, `CICLOS_TRATAMENTO` e "
                       "`CICLOS_PONTO_ESTRATEGICO` (scripts/coletar_evisita.py). Passo a passo no README, "
                       "seção \"Novo mês\"."]
    print("\n".join(linhas))
    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n\n")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
