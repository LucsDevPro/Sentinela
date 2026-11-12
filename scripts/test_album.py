# -*- coding: utf-8 -*-
"""Testes estáticos do álbum: estrutura, 'Como é calculado' (gerado) e proteção dos efeitos das cartas.
Os efeitos em si (inclinação, brilho) precisam de navegador e se conferem no álbum."""
import json
import os
import re
import sys

os.environ.setdefault("EVISITA_CPF", "x")
os.environ.setdefault("EVISITA_SENHA", "x")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import coletar_evisita as C
import gerar_transparencia as T

falhas = []


def checar(nome, ok, extra=""):
    print(("[OK  ] " if ok else "[FALHA] ") + nome + ("" if ok else f"  -> {extra}"))
    if not ok:
        falhas.append(nome)


def ler(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as f:
        return f.read()


album = ler("album.html")
checar("album.html só tem estrutura: sem <style> nem <script> embutidos", "<style" not in album and not re.search(r"<script>\s*\S", album))
for ref in re.findall(r'(?:src|href)="(assets/[^"?#]+)"', album):
    checar(f"arquivo referenciado existe: {ref}", os.path.exists(os.path.join(RAIZ, ref)) or ref.endswith(("como_calcula.js", "agentes_dados.js", "fotos.js")), "não existe")
for i in ("abaCartas", "abaCalc", "painelCartas", "painelCalc", "podio", "album"):
    checar(f"album.html tem #{i}", f'id="{i}"' in album)
checar("álbum e agente carregam carta_fx.js", "assets/carta_fx.js" in album and "assets/carta_fx.js" in ler("agente.html"))
checar("o ícone do livro (aba) está no sprite", 'symbol id="i-book"' in album)

# --- "Como é calculado" (conteúdo gerado das constantes reais)
corpo = T.corpo_html()
secoes = re.findall(r"<h2>(\d+)\. ", corpo)
checar("seções numeradas em sequência, de 1 a 9", secoes == [str(i) for i in range(1, 10)], str(secoes))
checar("explica a regra dos turnos usando o limite REAL do código", f"<b>{C.LIMITE_AGENTES_EVENTO_TURNO} ou mais agentes</b>" in corpo)
checar("explica a ordem: chuva automática (limite) -> equipe inteira -> falta", corpo.index("classificado automaticamente como <b>chuva</b>") < corpo.index("possível chuva isolada ou reunião da equipe") < corpo.index("Caso contrário, é falta"))
frag = T.fragmento_js()
m = re.match(r"window\.COMO_CALCULA = (\{.*\});\n$", frag, re.S)
checar("assets/como_calcula.js é uma atribuição JS válida com o HTML", bool(m) and json.loads(m.group(1))["html"] == corpo)
checar("o arquivo gerado no repositório está em dia (rode gerar_transparencia.py)", ler("assets/como_calcula.js") == frag)
red = T.gerar()
checar("transparencia.html só redireciona para a aba do álbum", "album.html#como-calcula" in red and "<h2>" not in red)

# --- cartas: marcação e proteções dos efeitos
cj = ler("assets/carta.js")
checar("carta.js gera as camadas de brilho e faíscas e o --v dos atributos", "c-brilho" in cj and "c-glitter" in cj and "--v:" in cj)
css = ler("assets/carta.css")
bloco = css[css.index("EFEITOS VIVOS"):]
checar("efeitos animados só dentro de prefers-reduced-motion: no-preference", bloco.count("@media (prefers-reduced-motion: no-preference)") == 1 and "animation:" not in bloco[:bloco.index("@media (prefers-reduced-motion: no-preference)")].replace("animation: none", "").split("@keyframes")[0])
checar("há versão para menos movimento", "@media (prefers-reduced-motion: reduce)" in bloco)
checar("efeitos não vão para o papel", "@media print" in bloco and ".c-brilho" in bloco[bloco.index("@media print"):])
fx = ler("assets/carta_fx.js")
checar("carta_fx.js respeita prefers-reduced-motion e só anima o que está visível", "prefers-reduced-motion" in fx and "IntersectionObserver" in fx and "'vivo'" in fx)


# --- mês selecionado no álbum deve abrir a evolução naquele mês (não o mais recente)
aj = ler("assets/album.js")
checar("album.js passa &mes= na URL ao abrir agente.html",
       "agente.html" in aj and "&mes=" in aj and "encodeURIComponent(mes)" in aj)
ej = ler("assets/agente.js")
checar("agente.js lê o parâmetro mes da URL", "get('mes')" in ej or 'get("mes")' in ej)
checar("agente.js filtra o histórico até o mês escolhido",
       "todosMeses" in ej and "slice(0, idxRef" in ej)
checar("agente.js sem mes continua usando o mês mais recente",
       "todosMeses.length - 1" in ej and "mesParam" in ej)
# Setembro no álbum → evolução de setembro mesmo com dados posteriores: o link carrega mes=
checar("o link do álbum inclui o mês filtrado (não só id/nome)",
       "encodeURIComponent(mes)" in aj)
# O popup "Ver evolução do agente" (carta.js) também leva o mês da cartinha (u.mes), senão agente.js abre no mais recente
cj = ler("assets/carta.js")
checar("carta.js: o link do popup inclui o mês da cartinha (&mes=u.mes)",
       "agente.html?id=" in cj and "'&mes=' + encodeURIComponent(u.mes)" in cj)
# Formato da borda: escudo de cantos cortados (clip-path) no CSS e o mesmo polígono no PNG
cc = ler("assets/carta.css")
checar("carta.css: o cartão e o anel da borda usam clip-path em polígono (cantos cortados)",
       cc.count("clip-path: polygon(") >= 3 and "18px 18px 40px 40px" not in cc)
checar("carta.js: o PNG desenha o mesmo polígono (FORMA), sem as elipses do canto arredondado",
       "var FORMA = [[20, 0], [252, 0], [272, 20], [272, 366], [242, 392], [30, 392], [0, 366], [0, 20]]" in cj and "ctx.ellipse(x + w - a" not in cj)
# Clique na cartinha abre a evolução do agente; "Melhor do ano" = média de todos os meses
aj2 = ler("assets/album.js")
checar("carta.js: clicar na cartinha abre a evolução do agente (link do álbum ou agente.html?id=&mes=)",
       "return;   // no álbum a cartinha é um link" in cj and "location.href = 'agente.html?id='" in cj)
checar("album.js: opção 'Melhor do ano' ordena pela média das notas de todos os meses",
       "const ANO = 'Melhor do ano'" in aj2 and "notas.reduce((t, n) => t + n, 0) / notas.length" in aj2 and "q.u.pontos - p.u.pontos" in aj2)
checar("album.js: 'Melhor do ano' exige no mínimo 2 meses", "const MIN_MESES_ANO = 2" in aj2 and "ms.length < MIN_MESES_ANO" in aj2)
checar("album.js: no 'Melhor do ano' o link do agente não leva ?mes= (abre no mês mais recente)", "(doAno ? '' : '&mes=' + encodeURIComponent(mes))" in aj2)
# Tela de reunião: panorama de visitas; cabeçalhos alinhados; home no mês mais recente
pj = ler("assets/projecao.js"); ga = ler("scripts/gerar_agentes.py")
checar("projecao.js: tem o panorama geral, o mês a mês e o panorama de cada mês",
       "'pano-total'" in pj and "'pano-evolucao'" in pj and "'pm-'+m+'-1'" in pj and "'pm-'+m+'-2'" in pj)
checar("gerar_agentes.py: grava os totais de visitas por mês (panorama)", "def ler_panorama" in ga and '"panorama": panorama' in ga)
checar("cabeçalho das páginas secundárias tem a mesma largura do conteúdo (álbum 1240, demais 860)",
       "header.topo .marca{max-width:1240px" in ler("assets/album.css") and "header.topo .marca{max-width:860px" in ler("assets/agente.css") and "header.topo .marca{max-width:860px" in ler("assets/comparar.css"))
checar("moldura premium: peças fora do contorno (conjunto .c-conj, camadas atrás e na frente) na tela e no PNG",
       ".c-conj" in cc and ".c-orna-atras" in cc and ".c-orna-frente" in cc and "function ornSVG" in cj and "function ornCanvas" in cj and "ornCanvas(ctx, borda0, 'atras'" in cj and "ornCanvas(ctx, borda0, 'frente'" in cj)
checar("moldura premium: louros no Ouro, cristais e asas na Destaque/Lendária, aletas na Prata, coroa e gema", all(x in cj for x in ("lado = 0; lado < 2", "b-top' || borda === 'b-100", "borda === 'b-80'", "coroa: true", "gema: true")))
checar("álbum: o conjunto (e não só o cartão) ocupa a vaga, para as peças acompanharem escala e inclinação", ".slot .c-conj" in ler("assets/album.css") and "c-conj" in ler("assets/carta_fx.js"))
# Dashboard: evento do LIRAa, alertas em uma linha, Ausências em painéis, gráfico só mensal, críticos com detalhes
import json as _json
crono = _json.loads(ler("data/cronograma_ausencias.json"))
checar("cronograma: levantamento de índice (LIRAa) de 04/11 a 09/11/2026 para todos, sem falta",
       any(c.get("alvo") == "todos" and c.get("motivo") == "Levantamento de Índice" and c.get("inicio") == "04/11/2026" and c.get("fim") == "09/11/2026" for c in crono))
st = ler("scripts/style.css")
checar("alertas: cartões sempre em uma única linha (grid-auto-flow: column) e rolagem só em tela estreita",
       ".alert-grid { display: grid; grid-auto-flow: column;" in st and "@media (max-width: 860px) { .alert-grid" in st)
au = ler("scripts/templates/sections/ausencias.html")
checar("Ausências: seções viram painéis recolhíveis padronizados (só o gráfico abre por padrão)",
       au.count('<details class="painel"') >= 5 and '<details class="painel" open>' in au and ".painel > summary" in st)
cj2 = ler("scripts/templates/charts.js"); eq = ler("scripts/templates/sections/equipes.html")
checar("equipes: nota média por equipe só do mês completo (sem a visão semana a semana)",
       "mês completo" in eq and "C.semanas.map" not in cj2 and "C.equipes[eq][C.equipes[eq].length - 1]" in cj2)
vg = ler("scripts/templates/sections/visao_geral.html")
checar("visão geral: todos os agentes críticos aparecem, cada um com detalhes (details.critico-item)",
       '<details class="critico-item">' in vg and "Mostrando os 5 piores" not in vg and "criticos=records(crit_sorted, RESUMO_COLS)" in ler("scripts/generate_dashboard.py"))
# Lendária «Icon Mármore + Ouro»: tela, peças da moldura e PNG no mesmo visual
checar("Lendária em mármore e ouro no CSS (fundo claro, texto escuro, filete dourado)", "Icon Mármore + Ouro" in cc and "--tx: #1A1408" in cc)
checar("PNG e peças da moldura da Lendária seguem o ouro (sem o azul antigo)",
       "'b-100': ['#FFFBE6', '#F0C830', '#8A6010']" in cj and "rgba(61,155,255" not in cj and "rgba(89,184,255" not in cj and "'#8FD8FF'" not in cj)

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes do álbum passaram.")
