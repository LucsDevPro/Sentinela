#!/usr/bin/env python3
"""Gera o "Como a nota do ranking é calculada": explica em linguagem simples as regras do ranking. Os números vêm
DIRETO das constantes de scripts/coleta/ (via coletar_evisita.py) — se um peso mudar no código, o texto muda junto.

O conteúdo vive DENTRO do álbum (album.html, aba "Como é calculado"): este script grava assets/como_calcula.js
(window.COMO_CALCULA = {html}), que o álbum carrega quando a aba é aberta (funciona também com file://).
transparencia.html passa a ser só um redirecionamento para album.html#como-calcula (links e favoritos antigos).

Uso: python scripts/gerar_transparencia.py [redirecionamento.html]   (padrão: transparencia.html)"""
import html
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coletar_evisita as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def n(v, casas=1):
    """Número em pt-BR (vírgula decimal), sem zeros inúteis."""
    t = f"{v:.{casas}f}".rstrip("0").rstrip(".") if casas else f"{v:.0f}"
    return t.replace(".", ",") or "0"


def hhmm(t):
    return f"{t[0]:02d}h{t[1]:02d}"


def e(t):
    return html.escape(str(t))


def tabela(linhas, cab):
    th = "".join(f"<th>{e(c)}</th>" for c in cab)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in l) + "</tr>" for l in linhas)
    return f'<div class="rolar"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def exemplo():
    """Agente FICTÍCIO calculado com as mesmas constantes do ranking."""
    esperados_base, folga = 21, 1
    esperados = esperados_base - folga
    trab, meta = 17, 9
    sem_meta = trab - meta
    atraso, turnos_sem, dias_inteiros, rapidas, dupl = 2, 3, 1, 8, 2
    itens = [
        ("Pontos iniciais", None, None, float(C.PONTOS_INICIAIS)),
        ("Dias com a meta diária batida", meta, C.PONTOS_GANHO_DIA_COM_META, meta * C.PONTOS_GANHO_DIA_COM_META),
        ("Dias trabalhados sem bater a meta", sem_meta, C.PONTOS_PERDA_DIA_SEM_META, -sem_meta * C.PONTOS_PERDA_DIA_SEM_META),
        ("Início da manhã atrasado", atraso, C.PONTOS_PERDA_INICIO_MANHA_ATRASADO, -atraso * C.PONTOS_PERDA_INICIO_MANHA_ATRASADO),
        ("Turnos sem lançamento", turnos_sem, C.PONTOS_PERDA_TURNO_SEM_LANCAMENTO, -turnos_sem * C.PONTOS_PERDA_TURNO_SEM_LANCAMENTO),
        ("Dia inteiro sem lançamento (extra)", dias_inteiros, C.PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO, -dias_inteiros * C.PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO),
        ("Visitas rápidas", rapidas, C.PONTOS_PERDA_VISITA_RAPIDA, -rapidas * C.PONTOS_PERDA_VISITA_RAPIDA),
        ("Visitas duplicadas", dupl, C.PONTOS_PERDA_VISITA_DUPLICADA, -dupl * C.PONTOS_PERDA_VISITA_DUPLICADA),
    ]
    total = sum(i[3] for i in itens)
    final = max(C.NOTA_MINIMA, min(C.NOTA_MAXIMA, total))
    return dict(esperados_base=esperados_base, folga=folga, esperados=esperados, trab=trab, itens=itens,
                total=total, final=final, presenca=trab / esperados)


def _txt_meta():
    """"20 visitas" ou, se houver metas por equipe (data/metas_equipes.json), "20 visitas; Equipe 1: 25"."""
    base = f"{C.META_VISITAS_DIA} visitas"
    extras = [f"{eq}: {v}" for eq, v in sorted(C.METAS_EQUIPES.items()) if v != C.META_VISITAS_DIA]
    return base + (" — metas diferentes: " + "; ".join(extras) if extras else "")


def corpo_html():
    """Conteúdo (HTML) do "Como é calculado", sem moldura de página."""
    perdas = [
        (f"Início da manhã depois das {hhmm(C.HORA_LIMITE_INICIO_MANHA)}", C.PONTOS_PERDA_INICIO_MANHA_ATRASADO, "por dia"),
        (f"Fim da manhã antes das {hhmm(C.HORA_LIMITE_FIM_MANHA)}", C.PONTOS_PERDA_FIM_MANHA_ANTECIPADO, "por dia"),
        (f"Início da tarde depois das {hhmm(C.HORA_LIMITE_INICIO_TARDE)}", C.PONTOS_PERDA_INICIO_TARDE_ATRASADO, "por dia"),
        (f"Fim da tarde antes das {hhmm(C.HORA_LIMITE_FIM_TARDE)}", C.PONTOS_PERDA_FIM_TARDE_ANTECIPADO, "por dia"),
        ("Turno sem lançamento (que não é feriado, chuva, reunião, férias, folga ou ausência justificada)", C.PONTOS_PERDA_TURNO_SEM_LANCAMENTO, "por turno"),
        ("Dia inteiro sem lançamento (os 2 turnos) — desconto EXTRA, somado ao dos dois turnos", C.PONTOS_PERDA_DIA_INTEIRO_SEM_LANCAMENTO, "por dia"),
        (f"Visita rápida (menos de {C.TEMPO_MIN_VISITA_MIN} min)", C.PONTOS_PERDA_VISITA_RAPIDA, "por visita"),
        ("Visita duplicada", C.PONTOS_PERDA_VISITA_DUPLICADA, "por visita"),
        ("Visita em sequência suspeita (lançamento em lote)", C.PONTOS_PERDA_SEQUENCIA_SUSPEITA, "por visita"),
        ("Visita fora do expediente ou em fim de semana", C.PONTOS_PERDA_FORA_EXPEDIENTE, "por visita"),
        ("Visita no horário de almoço", C.PONTOS_PERDA_VISITA_ALMOCO, "por visita"),
        (f"Dia trabalhado sem bater a meta diária de visitas ({_txt_meta()})", C.PONTOS_PERDA_DIA_SEM_META, "por dia"),
    ]
    perdas = [p for p in perdas if p[1]]
    ganhos = [
        (f"Dia com a meta diária de visitas batida ({_txt_meta()})", C.PONTOS_GANHO_DIA_COM_META, "por dia"),
        ("Bônus: nenhuma visita rápida no período", C.PONTOS_GANHO_SEM_VISITA_RAPIDA, "uma vez"),
        ("Bônus: nenhum turno sem lançamento no período", C.PONTOS_GANHO_SEM_AUSENCIA, "uma vez"),
        ("Bônus: pontualidade perfeita no período", C.PONTOS_GANHO_PONTUALIDADE_PERFEITA, "uma vez"),
    ]
    ini_novo = C.RANKING_SEM_NORMALIZACAO_A_PARTIR_DE
    feriados = ", ".join(f[:5] for f in C._feriados_em_vigor() if f.endswith("/2026"))
    ex = exemplo()
    pres_min = int(C.PRESENCA_MINIMA_FRACAO * 100)
    bonus_min = int(C.BONUS_MIN_FRACAO_DIAS_ESPERADOS * 100)
    nomes_cong = [l.split("/")[0] for _, _, l in C.MESES_ARQUIVADOS]
    congelados = (nomes_cong[0] + " a " + nomes_cong[-1]) if len(nomes_cong) > 1 else (nomes_cong[0] if nomes_cong else "Nenhum mês")
    sob_demanda = ", ".join(C.EQUIPES_SEM_DETECCAO_AUTOMATICA)
    data_recalculo = _data_recalculo()

    linhas_ex = []
    for nome, qtd, peso, pts in ex["itens"]:
        if qtd is None:
            linhas_ex.append([e(nome), "", "", f"<b>{n(pts)}</b>"])
        else:
            sinal = "+" if pts > 0 else "−"
            linhas_ex.append([e(nome), n(qtd, 0), n(peso), f'<span class="{"pos" if pts > 0 else "neg"}">{sinal}{n(abs(pts))}</span>'])
    linhas_ex.append(["<b>Soma</b>", "", "", f"<b>{n(ex['total'])}</b>"])
    if ex["total"] != ex["final"]:
        linhas_ex.append([f"Limite da nota (entre {C.NOTA_MINIMA} e {C.NOTA_MAXIMA})", "", "", f"<b>{n(ex['final'])}</b>"])
    linhas_ex.append(["<b>Nota final</b>", "", "", f"<b>{n(ex['final'])}</b>"])

    corpo = f"""
<p class="mut">Este texto é gerado automaticamente a partir das regras que o sistema usa de verdade. Se uma regra mudar, ele muda junto.</p>

<h2>1. A ideia em uma frase</h2>
<div class="destaque">Todo agente começa com <b>{C.PONTOS_INICIAIS} pontos</b>. Ganha pontos por dias bons, perde pontos por falhas, e a nota final fica sempre entre <b>{C.NOTA_MINIMA} e {C.NOTA_MAXIMA}</b>.
Em todos os meses <b>não existe fator de normalização</b>: o mesmo peso vale para todos, e a conta é simplesmente quantidade × peso.</div>

<h2>2. Dias esperados</h2>
<p>É quanto o agente <i>deveria</i> ter trabalhado no período. Conta-se assim:</p>
<ul>
<li>Dias úteis do período (segunda a sexta).</li>
<li>Menos os <b>feriados nacionais</b> ({e(feriados)}).</li>
<li>Menos os dias <b>justificados</b> em que o agente não trabalhou: <b>férias</b>, <b>folga</b>, <b>ausência justificada</b>, chuva, reunião/treinamento e outras paradas da equipe.</li>
<li><b>Meia folga</b> ou <b>meia ausência justificada</b> desconta <b>0,5 dia</b> (só aquele turno).</li>
<li><b>Férias valem no máximo {C.LIMITE_DIAS_CORRIDOS_OCORRENCIA} dias corridos</b>. O que passar disso conta como falta.</li>
<li>O <b>dia de hoje</b> (em andamento) não é cobrado de quem ainda não lançou nenhuma visita.</li>
</ul>
<p class="mut">Dia sem lançamento e sem nenhuma justificativa registrada <b>não sai</b> dos dias esperados: conta como falta.</p>

<h2>3. Turno sem lançamento: falta ou evento?</h2>
<p>Quando um agente fica um turno inteiro sem lançar nenhuma visita, o sistema decide <b>nesta ordem</b> (a primeira que se aplicar vale):</p>
<ol>
<li><b>Já está justificado no cronograma</b> (atestado, férias, folga, chuva, reunião…): não conta como falta.</li>
<li><b>{C.LIMITE_AGENTES_EVENTO_TURNO} ou mais agentes</b>, de qualquer equipe, sem lançamento no mesmo dia e turno: é classificado automaticamente como <b>chuva</b>, sem precisar de validação manual. É a regra suprema: <b>não desconta pontos</b>. A contagem inclui quem já estava coberto por chuva ou reunião no cronograma; férias, folga e atestado não entram.</li>
<li><b>Menos que isso, mas a equipe inteira parou</b> (todos os agentes ativos da equipe, pelo menos 2): é tratado como <b>possível chuva isolada ou reunião da equipe</b>. Também <b>não desconta</b>; a coordenação confirma o motivo no cronograma.</li>
<li><b>Caso contrário, é falta</b> e desconta pontos (veja a tabela abaixo).</li>
</ol>
<p class="mut">Quem decide o motivo real de um evento é a coordenação, no cronograma. Agentes de equipes que trabalham sob demanda ({e(sob_demanda)}) não entram nessas duas regras coletivas.</p>

<h2>4. O que tira pontos</h2>
{tabela([[e(a), f'−{n(b)}', e(c)] for a, b, c in perdas], ["Situação", "Pontos", "Quando"])}
<p class="mut">Visita no horário de almoço (11h15 às 12h45) <b>não tira ponto</b>: continua aparecendo nos alertas só para informar quem trabalhou nesse horário.</p>

<h2>5. O que dá pontos</h2>
{tabela([[e(a), f'+{n(b)}', e(c)] for a, b, c in ganhos], ["Situação", "Pontos", "Quando"])}
<p>Os <b>bônus únicos</b> só valem para quem trabalhou pelo menos <b>{bonus_min}%</b> dos dias esperados.</p>

<h2>6. Presença mínima</h2>
<p><b>Presença = dias trabalhados ÷ dias esperados.</b> Como os esperados já descontam férias, folgas e ausências justificadas, <b>quem está justificado não é prejudicado</b>.</p>
<p>Se a presença ficar abaixo de <b>{pres_min}%</b>, a nota é multiplicada por <b>presença ÷ {pres_min}%</b>. Exemplos: presença de 25% → nota × 0,5; presença de 10% → nota × 0,2; {pres_min}% ou mais → sem redução. O desconto aparece como uma linha própria no extrato.</p>

<h2>7. Exemplo passo a passo (agente fictício)</h2>
<div class="card">
<p>Num mês com <b>{ex['esperados_base']} dias úteis</b>, o agente <b>Exemplo</b> teve <b>{ex['folga']} dia de folga</b> lançada → <b>{ex['esperados']} dias esperados</b>. Trabalhou <b>{ex['trab']} dias</b> (presença de {ex['presenca']*100:.0f}%, acima do mínimo de {pres_min}%).</p>
{tabela(linhas_ex, ["Critério", "Quantidade", "Peso", "Pontos"])}
<p class="mut">Nenhum bônus foi concedido porque o agente teve visitas rápidas, turnos sem lançamento e atrasos.</p>
</div>

<h2>8. Faixas da nota</h2>
<ul>
<li>🟢 Excelente: {C.NOTA_FAIXA_EXCELENTE} ou mais</li>
<li>🟡 Bom: {C.NOTA_FAIXA_BOM} a {n(C.NOTA_FAIXA_EXCELENTE - 0.1)}</li>
<li>🟠 Atenção: {C.NOTA_FAIXA_ATENCAO} a {n(C.NOTA_FAIXA_BOM - 0.1)}</li>
<li>🔴 Crítico: abaixo de {C.NOTA_FAIXA_ATENCAO}</li>
</ul>

<h2>9. Detalhes importantes</h2>
<ul>
<li><b>Meses fechados não mudam sozinhos.</b> {congelados} foram recalculados{data_recalculo} com estas regras e congelados de novo. No <b>Acumulado</b> (vários meses) o ranking é <b>só a média das notas mensais</b>: somar meses numa conta única distorceria a nota.</li>
<li><b>Equipes que trabalham sob demanda</b> ({e(sob_demanda)}) não têm dia esperado fixo: não recebem o desconto de dia inteiro nem a regra de presença mínima.</li>
<li><b>Visão semanal:</b> as páginas "Semana 1, 2…" usam exatamente as mesmas regras, aplicadas só àqueles dias.</li>
<li><b>Ajustes manuais</b> da coordenação aparecem no extrato como "Ajuste manual: motivo".</li>
<li><b>Privacidade:</b> o site é público. Ausências aparecem só como "Ausência justificada" — o sistema nunca guarda motivo de saúde, CID ou diagnóstico.</li>
<li>Cada agente pode ver a conta completa no <b>Extrato</b> (aba Ranking → botão do agente).</li>
</ul>
"""
    return corpo


def _data_recalculo():
    """' em dd/mm/aaaa' da última vez que um mês congelado foi refeito (manifest.json); '' se não houver."""
    try:
        man = json.loads((ROOT / "data" / "historico" / "manifest.json").read_text(encoding="utf-8"))
        datas = [e["reaberto_em"] for e in man if e.get("reaberto_em")]
        return " em " + max(datas, key=lambda d: (d[6:10], d[3:5], d[0:2])) if datas else ""
    except Exception:
        return ""


def fragmento_js():
    """assets/como_calcula.js: o HTML do conteúdo, como string JS (o álbum injeta na aba "Como é calculado")."""
    return "window.COMO_CALCULA = " + json.dumps({"html": corpo_html()}, ensure_ascii=False) + ";\n"


def gerar():
    """transparencia.html: só redireciona para a aba "Como é calculado" do álbum."""
    return """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Como o ranking é calculado</title>
<meta http-equiv="refresh" content="0; url=album.html#como-calcula">
<script>location.replace("album.html#como-calcula");</script></head>
<body><p>O "Como é calculado" agora fica dentro do álbum. <a href="album.html#como-calcula">Abrir</a>.</p></body></html>
"""


if __name__ == "__main__":
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "transparencia.html"
    saida.write_text(gerar(), encoding="utf-8")
    frag = ROOT / "assets" / "como_calcula.js"
    frag.write_text(fragmento_js(), encoding="utf-8")
    print(f"OK: {saida} (redirecionamento) e {frag} ({frag.stat().st_size:,} bytes)")
