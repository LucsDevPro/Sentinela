# Testes das cartinhas (suíte de navegador)

Arquivo: `scripts/test_cartinhas_navegador.py`. Roda no Chromium (Playwright), serve `assets/` por um servidor local e **não escreve nada no repositório**.
Não está em `rodar_testes.py` (precisa de navegador); rode à mão ao mexer em cartinha, borda, cor, PNG, vídeo ou som.

```
python3 scripts/test_cartinhas_navegador.py            # tudo (~40 s; grava 1 vídeo de 5 s)
python3 scripts/test_cartinhas_navegador.py --rapido   # sem vídeo
python3 scripts/test_cartinhas_navegador.py --top5     # também o vídeo do Top 5
python3 scripts/test_cartinhas_navegador.py png        # só grupos cujo nome contém «png»
```
Requisitos: `pip install playwright pillow numpy` + chromium; `ffmpeg/ffprobe` para o vídeo (sem eles, o teste é PULADO, não falha).

## O que cobre (todos os 8 tiers: LENDÁRIA, ELITE, PLATINA, OURO, PRATA, BRONZE, AÇO, FERRO)
| Grupo | Verifica |
|---|---|
| `tiers` | classes, regra de CSS do tier, medidas coerentes com a nota (faixa de 20 pts, nota sem teto de 100) |
| `cores` | contraste (nota ≥ 3, textos ≥ 4,5), relevo da moldura, espessura/raio dentro de faixa, tamanho mínimo e família das fontes, efeitos e ornamentos por tier |
| `tema` | Sala nasce escura; botão leva ao claro |
| `png` | exportação principal (html-to-image) **e** plano B (canvas, forçado bloqueando a lib) × cartão HTML: cor média por grade, brilho geral, ornamentos laterais |
| `movimento` | com `prefers-reduced-motion: reduce` nenhuma animação infinita roda; no normal, as molduras premium animam |
| `pagina` | **carregamento sob demanda** (só parte vira cartão no início; rolando, todas abrem), animações só nas cartas perto da tela, nota com algarismos tabulares e peso próprio, aviso «faltam fotos», estado vazio com «Limpar filtros», **folha de recorte** (63 mm, 8 marcas de corte) |
| `audio` / `video` | **somente leitura**: cada som (pico ≤ 0 dBFS, não mudo), quadros de cada tier, vídeo de 5 s (duração, fps, áudio presente, fade no fim) |

## Fotos e folha de recorte (rotina)
- Foto nova: `python3 scripts/padronizar_foto.py ID foto.jpg [--rosto X Y]` (480×480, rosto no terço de cima, fundo neutro, sem EXIF) e já registra em `assets/fotos.js`. `scripts/test_fotos.py` confere o recorte, o registro e que toda foto publicada é quadrada.
- «Folha de recorte» (botão da Sala): A4 paisagem, 8 cartinhas de 63 mm por folha com marcas de corte. Sem ornamentos nem sombras pesadas (o PDF perdia a moldura com elas).
- Tokens do visual: bloco `:root{--k-…}` no topo de `assets/carta.css` (foto, espessuras por nível, fonte e peso da nota, auras). Trocar visual = mexer ali; a suíte segue valendo.

## Regra de ouro: trocar cor não pode quebrar teste
Os testes checam **invariantes** (contraste, validade, HTML == PNG), nunca um hex fixo. Mudou a paleta de propósito? Normalmente nada a fazer.
Se um limite ficar apertado demais, ajuste **só o `CONFIG`** (topo do arquivo), cada chave tem comentário. Não afrouxe para esconder um defeito real
(a suíte já pegou dois: raio negativo e fundo dourado no plano B do Destaque).
`scripts/test_album.py` segue a mesma ideia (`eh_cor`, regex de «3 cores válidas»).

## Auditoria não altera vídeo, áudio nem animação
O grupo 6 só mede: renderiza sons offscreen, grava o vídeo em página própria e analisa com ffprobe/ffmpeg. Nunca edite `video.js`, `som.js` ou animações
para «fazer o teste passar»; mudanças nesses recursos são feitas à parte e o teste só confere o resultado.

## Como acrescentar
1. **Tier novo**: acrescente uma linha em `TIERS` `(nome, "classes", nota, posição)`; se tiver ornamento ou for premium, inclua a classe em `PREMIUM` / `ORNAMENTOS`. Os grupos o cobrem sozinhos.
2. **Teste novo**: dentro do grupo `if quer("..."):` mais próximo, use `pg.evaluate(JS_MONTA, [nota, pos, "x", vivo])` (monta o cartão isolado; `vivo=True` registra no Movimento e anima) e chame `checar("descrição com o valor medido", condição, detalhe)`.
   Para ler estilo: `getComputedStyle(.carta)`; para comparar com PNG, reaproveite `grade()`.
3. **Limite novo**: crie a chave em `CONFIG` com comentário do porquê e use `CONFIG["..."]`; nunca número solto no teste.
4. **Grupo novo**: `if quer("nome"):` + `print("\n== N. título ==")`; atualize a docstring do topo e esta tabela.
5. Falha esperada por mudança de projeto? Ajuste o `CONFIG` e registre em `docs/DECISOES.md`.

Cuidados: `.c-captura` congela animações (use só para capturas); o 4º argumento `true` de `Carta.html` não registra no Movimento (sem animações infinitas); páginas editáveis não devem ser abertas por `file://`.
