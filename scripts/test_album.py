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
checar("explica a ordem: evento (limite) -> equipe inteira -> falta", corpo.index("evento externo ou interno") < corpo.index("chuva isolada ou reunião da equipe") < corpo.index("Caso contrário, é falta"))
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

print()
if falhas:
    print(f"❌ {len(falhas)} falha(s): {falhas}")
    sys.exit(1)
print("✅ Todos os testes do álbum passaram.")
