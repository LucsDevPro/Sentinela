#!/usr/bin/env python3
"""Gera transparencia.html: explica em linguagem simples como o ranking é
calculado. Os números vêm DIRETO das constantes de scripts/coleta/ (via coletar_evisita.py) — se
um peso mudar no código, a página muda junto (nunca fica desatualizada).

Uso: python scripts/gerar_transparencia.py [saida.html]   (padrão: transparencia.html)"""
import html
import os
import sys
from pathlib import Path

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import coletar_evisita as C  # noqa: E402
import icones  # noqa: E402

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


def gerar():
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

    css = """
@font-face{font-family:"Barlow Semi Condensed";font-weight:700;src:url(assets/fonts/barlow-semi-condensed-latin-700-normal.woff2) format("woff2");font-display:swap}
@font-face{font-family:"Barlow Semi Condensed";font-weight:600;src:url(assets/fonts/barlow-semi-condensed-latin-600-normal.woff2) format("woff2");font-display:swap}
@font-face{font-family:"IBM Plex Sans";font-weight:400;src:url(assets/fonts/ibm-plex-sans-latin-400-normal.woff2) format("woff2");font-display:swap}
@font-face{font-family:"IBM Plex Sans";font-weight:600;src:url(assets/fonts/ibm-plex-sans-latin-600-normal.woff2) format("woff2");font-display:swap}
:root{--bg:#EEF2F8;--card:#FFFFFF;--tx:#12233B;--mut:#4A5D7C;--bd:#D5DEEA;--pri:#0F5FB0;--pos:#0B7A44;--neg:#B3261E;--soft:#F2F6FB;color-scheme:light}
:root[data-theme="dark"]{--bg:#071426;--card:#0C1F3A;--tx:#E6EDF7;--mut:#9DB2D0;--bd:#1D3C68;--pri:#6CC4F2;--pos:#5CE59A;--neg:#FF8478;--soft:#102848;color-scheme:dark}
*{box-sizing:border-box}html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 "IBM Plex Sans",system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header.topo{background:#050F20;border-bottom:1px solid var(--bd);position:relative;padding:12px 16px 15px}
header.topo::after{content:"";position:absolute;left:0;right:0;bottom:-1px;height:3px;background:linear-gradient(90deg,#F7B500 0 120px,#FF5143 120px 168px,#19B8A3 168px 196px,transparent 196px)}
header.topo .marca{display:flex;align-items:center;gap:12px;max-width:860px;margin:0 auto}
header.topo img{height:34px;background:#fff;padding:3px 8px;border-radius:4px}
header.topo b{white-space:nowrap;font-family:"Barlow Semi Condensed",system-ui,sans-serif;font-size:1.2rem;letter-spacing:.04em;color:#fff}
header.topo b i{font-style:normal;color:#2BA8E8;font-weight:600}
header.topo a{margin-left:auto;font-size:.85rem;white-space:nowrap;color:#9DD3F5}
header.topo{border-bottom-color:#1D3C68}
.tema-btn{background:transparent;border:1px solid #2C4F82;color:#DCE7F5;border-radius:6px;padding:6px 10px;font:inherit;font-size:.82rem;cursor:pointer;white-space:nowrap;margin-left:auto}.tema-btn + a{margin-left:0}.tema-btn:hover{border-color:#F7B500}
.ico{width:1.1em;height:1.1em;vertical-align:-.18em;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.ico-sol{display:none}:root[data-theme="dark"] .ico-sol{display:inline}:root[data-theme="dark"] .ico-lua{display:none}
@media (max-width:480px){.tema-btn .tema-txt{display:none}.tema-btn{padding:6px 8px}header.topo{padding-left:10px;padding-right:10px}header.topo .marca{gap:6px}header.topo img{height:22px;padding:2px 4px}header.topo b{font-size:.9rem;letter-spacing:.02em}header.topo a{font-size:.72rem}header.topo b i{display:none}}
@media (max-width:480px){header.topo .marca{gap:8px}header.topo img{height:26px;padding:2px 6px}header.topo b{font-size:1.02rem}header.topo a{font-size:.78rem}}
main{max-width:860px;margin:0 auto;padding:16px 16px 48px}
h1,h2{font-family:"Barlow Semi Condensed",system-ui,sans-serif;letter-spacing:.01em}
h1{font-size:1.9rem;margin:10px 0 6px;color:#fff}h2{font-size:1.4rem;margin:30px 0 8px;color:var(--pri)}
a{color:var(--pri)}.mut{color:var(--mut)}
.card{background:var(--card);border:1px solid var(--bd);border-radius:6px;padding:14px 16px;margin:12px 0}
.rolar{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{padding:7px 8px;border-bottom:1px solid var(--bd);text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600}
td:nth-child(n+2),th:nth-child(n+2){white-space:nowrap}
.pos{color:var(--pos);font-weight:600}.neg{color:var(--neg);font-weight:600}
.destaque{background:var(--soft);border-left:4px solid #F7B500;border-radius:4px;padding:10px 14px}
li{margin:4px 0}
:focus-visible{outline:2px solid #F7B500;outline-offset:2px}
@media print{header.topo,a.voltar{display:none}:root,:root[data-theme="dark"]{--bg:#fff;--card:#fff;--tx:#1b2a3a;--mut:#4a5b72;--bd:#d8dee6;--pri:#0b3a75;--pos:#17803d;--neg:#b3261e;--soft:#eef3f9}body{background:#fff}h1{color:#1b2a3a}}
"""
    corpo = f"""
<h1><svg class="ico" aria-hidden="true"><use href="#i-book"/></svg> Como a nota do ranking é calculada</h1>
<p class="mut">Esta página é gerada automaticamente a partir das regras que o sistema usa de verdade. Se uma regra mudar, esta página muda junto.</p>

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

<h2>3. O que tira pontos</h2>
{tabela([[e(a), f'−{n(b)}', e(c)] for a, b, c in perdas], ["Situação", "Pontos", "Quando"])}
<p class="mut">Visita no horário de almoço (11h15 às 12h45) <b>não tira ponto</b>: continua aparecendo nos alertas só para informar quem trabalhou nesse horário.</p>

<h2>4. O que dá pontos</h2>
{tabela([[e(a), f'+{n(b)}', e(c)] for a, b, c in ganhos], ["Situação", "Pontos", "Quando"])}
<p>Os <b>bônus únicos</b> só valem para quem trabalhou pelo menos <b>{bonus_min}%</b> dos dias esperados.</p>

<h2>5. Presença mínima</h2>
<p><b>Presença = dias trabalhados ÷ dias esperados.</b> Como os esperados já descontam férias, folgas e ausências justificadas, <b>quem está justificado não é prejudicado</b>.</p>
<p>Se a presença ficar abaixo de <b>{pres_min}%</b>, a nota é multiplicada por <b>presença ÷ {pres_min}%</b>. Exemplos: presença de 25% → nota × 0,5; presença de 10% → nota × 0,2; {pres_min}% ou mais → sem redução. O desconto aparece como uma linha própria no extrato.</p>

<h2>6. Exemplo passo a passo (agente fictício)</h2>
<div class="card">
<p>Num mês com <b>{ex['esperados_base']} dias úteis</b>, o agente <b>Exemplo</b> teve <b>{ex['folga']} dia de folga</b> lançada → <b>{ex['esperados']} dias esperados</b>. Trabalhou <b>{ex['trab']} dias</b> (presença de {ex['presenca']*100:.0f}%, acima do mínimo de {pres_min}%).</p>
{tabela(linhas_ex, ["Critério", "Quantidade", "Peso", "Pontos"])}
<p class="mut">Nenhum bônus foi concedido porque o agente teve visitas rápidas, turnos sem lançamento e atrasos.</p>
</div>

<h2>7. Faixas da nota</h2>
<ul>
<li>🟢 Excelente: {C.NOTA_FAIXA_EXCELENTE} ou mais</li>
<li>🟡 Bom: {C.NOTA_FAIXA_BOM} a {n(C.NOTA_FAIXA_EXCELENTE - 0.1)}</li>
<li>🟠 Atenção: {C.NOTA_FAIXA_ATENCAO} a {n(C.NOTA_FAIXA_BOM - 0.1)}</li>
<li>🔴 Crítico: abaixo de {C.NOTA_FAIXA_ATENCAO}</li>
</ul>

<h2>8. Detalhes importantes</h2>
<ul>
<li><b>Meses fechados não mudam sozinhos.</b> {congelados} foram recalculados em 30/10/2026 com estas regras e congelados de novo. No <b>Acumulado</b> (vários meses) o ranking é <b>só a média das notas mensais</b>: somar meses numa conta única distorceria a nota.</li>
<li><b>Equipes que trabalham sob demanda</b> ({e(sob_demanda)}) não têm dia esperado fixo: não recebem o desconto de dia inteiro nem a regra de presença mínima.</li>
<li><b>Visão semanal:</b> as páginas "Semana 1, 2…" usam exatamente as mesmas regras, aplicadas só àqueles dias.</li>
<li><b>Ajustes manuais</b> da coordenação aparecem no extrato como "Ajuste manual: motivo".</li>
<li><b>Privacidade:</b> o site é público. Ausências aparecem só como "Ausência justificada" — o sistema nunca guarda motivo de saúde, CID ou diagnóstico.</li>
<li>Cada agente pode ver a conta completa no <b>Extrato</b> (aba Ranking → botão do agente).</li>
</ul>
"""
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Como o ranking é calculado</title><script src="assets/tema.js"></script><style>{css}</style></head>
<body>{icones.sprite(['moon','sun','book'])}<header class=\"topo\"><div class=\"marca\"><img src=\"assets/logo_ponta_pora.png\" alt=\"Prefeitura Municipal de Ponta Porã\"><b>SENTINELA <i>transparência</i></b><button type=\"button\" class=\"tema-btn\" data-tema-btn title=\"Mudar para o tema escuro\"><svg class=\"ico ico-lua\" aria-hidden=\"true\"><use href=\"#i-moon\"/></svg><svg class=\"ico ico-sol\" aria-hidden=\"true\"><use href=\"#i-sun\"/></svg> <span class=\"tema-txt\">Tema escuro</span></button><a href=\"index.html\">← Dashboard</a></div></header><main>{corpo}</main></body></html>"""


if __name__ == "__main__":
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "transparencia.html"
    saida.write_text(gerar(), encoding="utf-8")
    print(f"OK: {saida} ({saida.stat().st_size:,} bytes)")
