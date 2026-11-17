# Registro de decisões (mais recente primeiro)

## 17/11/2026 — Resumo do mês em A4 (PDF para a ata)
- Nova página `resumo.html` (+ `assets/resumo.js/.css`, só estrutura no .html): pódio, números do mês (média com variação sobre o mês anterior, quantos tiraram 100, média do top 5, melhor equipe), top 5, média por equipe, lista de quem tirou 100 e linhas para anotações. Mesma ordem do álbum/reunião (nota bruta → média anterior → posição oficial → nome); tudo vem de `AGENTES_DADOS`, nada calculado à parte. `?mes=Novembro/2026` escolhe o mês (padrão: o mais recente).
- Sem biblioteca de PDF: a folha tem `@page A4` e o botão chama `window.print()` («Salvar como PDF»); sempre clara, cabe em 1 página (testado em modo de impressão). Mostra os nomes (é para a ata); o «Nomes: ocultos» não se aplica.
- Entradas: botão «Resumo do mês» no álbum (mês do filtro) e «📄 Resumo do mês (PDF para a ata)» na tela de fechamento da reunião.

## 16/11/2026 (9) — som mais limpo e com «sala»
- Queixa: som «feio». Causa provável: serras empilhadas e metais agudos (A5/F#5) davam chiado, e tudo soava seco. Agora: cadeia de saída com **reverberação sintética** (~2,4 s) + filtro passa-baixa 9,5 kHz + compressor (`limitador` em `som.js`, vale na reunião e no vídeo); metais com corpo triangular, vibrato leve e filtro mais fechado; coro com 2 vozes e passa-baixa; acordes finais em voicing aberto (sem metal agudo) com **sinos** no brilho. Medido offline (`Som.renderizar`): energia de agudos caiu ~15× nos sons de revelação, picos ≤ 0,85. Teste confere volume, ausência de estouro e cauda de sala. Sem ouvir não dá para garantir o gosto: ajuste fino é por `mol.gain` (reverb), `lp.frequency` (brilho) e `GANHO`.

## 16/11/2026 (8) — foto no vídeo do top 5
- O vídeo do top 5 não passava o `id` do agente à `Carta.png`, e é por ele que a foto (`AGENTES_FOTOS`) entra na carta; só o vídeo de 1 carta passava. `gerarTop` agora usa `id` de cada item (`projecao.js` envia `id:a.k`). Fotos novas: `assets/fotos/ID.png` + linha em `assets/fotos.js`; valem em PNG, vídeo de 1 carta e vídeo do top 5. Com «Nomes: ocultos» a foto continua saindo.

## 16/11/2026 (7) — fechamento do mês, vídeo do top 5, desempate, legenda e volume
- **Fechamento (pacote):** depois do 1º lugar abre a tela «Parabéns ao top 5»: pódio 2º·1º·3º com as cartas, números do mês (nota média de todos os agentes, quantos tiraram 100, média do top 5) e «Também tiraram 100» (nomes pequenos; com nomes ocultos só a contagem). Dados vêm de `slidesDoPacote` → `opts.fechamento`. É a tela da «foto» para o grupo.
- **Vídeo do top 5** (`CartaVideo.gerarTop/enviarTop`, ≈15 s): do 5º ao 1º, cada um com a própria revelação (`DUR_TOP`: 2,3·2,3·2,8·3,0·4,6 s), clarão rápido entre as cartas e a mesma trilha sonora. `gravarCenas` generaliza o gravador (1 carta = 1 cena). Botão na tela de fechamento.
- **Desempate:** `criterioDesempate` (projecao.js) compara com o vizinho de mesma nota exibida e diz o que decidiu, na ordem do ranking: nota bruta → média dos meses anteriores → posição oficial → ordem alfabética. Aparece na ficha (⚖) e na legenda; some da ficha se a cena for baixa demais.
- **Acessibilidade:** legenda em texto (`.pk-leg`, `aria-live`) descrevendo cada passo; som em 3 níveis (desligado → ligado → baixo; botão e tecla S; `Som.nivel`, guardado em `sentinela:som`).

## 16/11/2026 (6) — pacote só com o top 5, sem «Campeão»
- O pacote da reunião passa a ter só o **top 5** do mês (`PACOTE_TOP` em `projecao.js`), em vez de todas as notas 100; sem o seletor «pular até». A faixa do 1º diz só «1º LUGAR» (tela e vídeo), e o fim diz «Parabéns ao top 5 do mês!».

## 16/11/2026 (5) — trilha sonora em clima de abertura de campeonato
- `som.js` ganhou «orquestra» sintetizada: tímpanos (`timpano`, `rufar` que acelera), metais (`metal`), coro (`coro`) e prato. `bronze`/`prata`/`ouro`, `suspense` e `fanfarra` foram refeitos (subida de metais, pancada de tímpanos, acorde de Ré maior com coro e prato). Melodias originais, só o clima lembra estádio; não reproduz nenhum hino real. Compressor no fim da cadeia contra estouro. O vídeo usa os mesmos sons (sem a fanfarra extra, que passava dos 5 s).

## 16/11/2026 (4) — pacote sem sobreposição + animações no computador do serviço
- **Causa do «não anima / bagunçado» no serviço:** o computador pedia «reduzir movimento» (comum em Windows com efeitos desligados, área de trabalho remota). O `carta.css` tinha `@media (prefers-reduced-motion:reduce){.carta{transform:none!important}}`, que também apagava a **escala** `--s`: cartas do álbum, da fileira e a carta grande do pacote ficavam em tamanho cheio e se sobrepunham. Agora o modo reduzido mantém `transform:scale(var(--s,1))`.
- **Animações:** `Movimento` (em `carta_fx.js`) = sistema + escolha da pessoa (`localStorage sentinela:animacoes`). No pacote, botão «✨ Animações» (tecla **M**) e um aviso amarelo com «Ativar animações» quando o sistema pede menos movimento. Respeita o sistema por padrão; um clique liga e fica guardado. Animações contínuas do `pacote.css` usam a classe `.mov` no palco, não mais o media query.
- **Layout do pacote:** palco em coluna: `.pk-cabeca` (dica · controles · contador) / aviso / `.pk-cena` (pacote, carta grande, banner, ficha) / `.pk-fileira`. Cada bloco tem seu espaço; carta e fonte da ficha saem do tamanho real da cena (`.estreito` em tela estreita, palco com altura mínima no celular). Teste em 1920, 1366, 1024 e 390 px.
- Vídeo de 5 s não mudou.

## 16/11/2026 (3) — 1º lugar com muito mais destaque + áudio no vídeo
- **Pacote, 1º lugar:** suspense maior (≈2,7 s) com holofote dourado, tela escura, coração batendo (`batida`) e a tela tremendo; na revelação clarão branco + dourado, tremor forte, 8 ondas, 190 partículas, 14 raios + 4 raios que caem DIRETO na carta (`CartaFX.raios(..., {x, y, n})`), dois trovões e a fanfarra, coroa 👑 que cai e quica no topo da carta, faixa «CAMPEÃO · 1º LUGAR» com brilho correndo, raios do fundo mais rápidos e **tempestade contínua** (3 raios + trovão a cada 3 s) enquanto ela está na tela. A carta grande usa mais espaço (o 1º pode cobrir um pouco da fileira).
- **Vídeo:** o 1º ganha 14 raios, 7 ondas, 150 partículas, tremor, clarão duplo, holofote dourado e a faixa «CAMPEÃO» maior, pulsando e com brilho passando. Agora o vídeo tem **trilha sonora** (`Som.paraGravacao`): giro, suspense, batida da revelação, um trovão por raio e fanfarra no 1º; vale mesmo com o som da reunião desligado. Prefere MP4 com AAC (WhatsApp/iPhone); sem isso cai para o que o navegador gravar.

## 16/11/2026 (2) — raios e trovão no lugar do confete
- O confete saiu de tudo (álbum, pacote e vídeo). No lugar: **relâmpagos** irregulares com ramificações, clarão azulado e **trovão** (som `trovao`, quando o som está ligado). `CartaFX.raios(alvo, n, cor)` no palco/álbum; no vídeo são desenhados no canvas (3 traços: brilho largo, médio e núcleo branco). Quantidade cresce do 3º (4) ao 2º (6) e ao 1º (9); o final da revelação solta 8. Seguem as regras dos outros efeitos: nada com «reduzir movimento», nada no PNG nem na impressão.

## 16/11/2026 (1) — pacote: som, automático, pular, controle remoto; vídeo de 5 s da cartinha
- **Som** (`assets/som.js`): sintetizado com Web Audio (nenhum arquivo): rasgo, giro, suspense que sobe, «ding», acorde de bronze/prata/ouro e fanfarra final. Começa **desligado**; botão «Som» na barra do pacote ou tecla S; a escolha fica no aparelho (`sentinela:som`).
- **Automático** (botão/tecla A): revela sozinho, ~3,2 s por carta e ~7 s nas do pódio. **Pular até o 10º/5º** (select): as de trás abrem de uma vez e a revelação começa nesse lugar.
- **Controle remoto:** PageDown, ↓, → , Enter, espaço e «.» avançam; PageUp/↑/← não fazem nada; botão «Próxima ▶» (grande no toque). Clique no palco também avança.
- **Vídeo de 5 s** (`assets/video.js`, `CartaVideo`): usa a MESMA imagem do botão Baixar (`Carta.png` com `transparente:true`) e anima em volta num canvas 720×1280: pacote que gira, clarão, ondas, partículas, confete, brilho passando, estrelinhas, faixa «CAMPEÃO/2º/3º LUGAR», nome e rodapé. Efeitos crescem do 3º ao 1º; demais posições têm versão leve. Gravado em tempo real com MediaRecorder: **MP4/H.264** quando o navegador grava (é o que o WhatsApp aceita em qualquer aparelho), senão WebM com aviso. Botão «Vídeo» em cada cartinha do álbum e na ficha do pacote; janela de envio (compartilhar / baixar / abrir WhatsApp Web). A aba precisa ficar aberta durante os 5 s.
- Álbum: os 3 botões viram só ícone abaixo de 1500 px (não cabiam no cartão).

## 15/11/2026 (9) — reunião: «Abrir pacote» (tecla P, `#pacote`)
- Novo modo na tela de reunião (`assets/pacote.js/.css`, ligado em `projecao.js`): um pacote «SENTINELA» fechado; ao clicar/Enter o topo é rasgado (clarão), as cartinhas saem **girando** e pousam de costas numa fileira. Só entram **quem tirou 100** (nota arredondada ≥ 100; com menos de 3, o top 3 entra mesmo assim).
- Cada Enter/clique/→ revela uma, **de trás pra frente**: a carta voa da fileira ao centro, vira e aparece; o efeito cresce até o pódio — 3º (bronze), 2º (prata, ondas), 1º (ouro: suspense, tela escurecida, raios girando, tremor, ondas, confete, faixa «CAMPEÃO»). Depois cada uma volta à fileira, de frente. No fim: parabéns + confete. R recomeça, P/C/Painéis saem.
- Respeita «Nomes: ocultos» (Agente N, sem foto) pela mesma `anonCarta` do modo cartinhas; a tela **não** avança sozinha (slide `manual`); com «reduzir movimento» tudo acontece sem animação.
- Cada mês tem a sua apresentação: seletor «mês» no cabeçalho (aparece em Cartinhas e Pacote), mantém `?mes=` na URL e vale para os dois modos; meses com poucos 100 mostram ao menos o top 3.
- Cabeçalho da reunião responsivo: título à esquerda e comandos (`.ctl`) à direita, que quebram em outra linha quando não cabem (antes rolava para o lado e estourava até em 1920 px); fonte dos botões proporcional à largura; abaixo de 700 px os botões ficam só com ícone.
- Cartas reais só são montadas ao revelar (a fileira usa versos): leve mesmo com muitos 100.

## 15/11/2026 (8) — efeitos extras nas cartinhas
- Já existiam (carta_fx.js): inclinação 3D e brilho que seguem o ponteiro, entrada em cascata, nota contando, coroa/raios no pódio. Foram **somados**:
- **Revelação na tela de reunião** (`CartaFX.revelar`): a cartinha chega num pacote «SENTINELA» que treme, vira e solta partículas (mais para lendária/destaque/ouro). Dura ~1,3 s.
- **Aura por nível** atrás da cartinha (lendária dourada, destaque rosa/ciano, ouro discreta) e reflexo lento de metal em prata/bronze/aço; ferro fica sem efeito de propósito; selo «100» da ELITE pulsa.
- **Esqueleto da foto** (shimmer cinza) até a imagem carregar.
- **Álbum:** ao filtrar, as cartinhas que ficam deslizam até o novo lugar (WAAPI, propriedade `translate`) e não «entram» de novo; **confete** no pódio na primeira abertura de cada mês neste aparelho (localStorage).
- **Tema escuro:** auras e pódio com mais luz. Corrigido o pódio vazio que aparecia com filtro (`[hidden]` perdia para `display:flex`).
- Regras: tudo só sem «reduzir movimento»; aura, pacote, partículas, esqueleto e confete somem na captura do PNG (`.c-captura`) e na impressão; aura sem `filter: blur` (pesava em 100 cartas).
- Não feito de propósito: item 4 (tendência/mini gráfico na carta).

## 15/11/2026 (7) — álbum: baixar todas (.zip), contagem por equipe e filtros na URL
- Busca por nome e filtro de equipe **já existiam**; foram melhorados: equipes mostram quantas cartinhas têm («Equipe 3 (10)»), botão «Limpar filtros» e os filtros (`eq`, `nivel`, `q`, `mes`) vão para a URL, então o link filtrado pode ser enviado.
- «Baixar todas (N) .zip»: gera o PNG de cada cartinha filtrada com o mesmo `Carta.png` da cartinha (modo `rapido`: uma passada só, por lote) e empacota em `assets/zip.js` (ZIP sem compressão, PNG já é comprimido; nomes em UTF-8). Uma pasta por equipe, para a coordenação repassar. Com «Modo apresentação» os nomes saem do arquivo (`NN-agente-N.png`).
- Confirma antes de lotes com mais de 40 cartinhas (~1,3 s cada; mais lento no celular); mostra progresso e permite cancelar; falhas são listadas ao final.

## 15/11/2026 (6) — «Melhor do ano»: o detalhe abria o mês mais recente
- Bug: no álbum «Melhor do ano» o agente aparecia em 1º, mas o link (e o «Ver evolução» do popup) abria `agente.html` sem o mês certo e a página caía em novembro (4º). Agora o link leva `mes=Melhor do ano` e a página mostra a mesma cartinha e a mesma posição (ex.: «1º de 43»), com «Por que esta nota?» explicando a média de cada mês (e link para a conta de cada mês).
- A conta do ano passou a morar em `Carta.anual` (`carta.js`), usada pelo álbum e por `agente.js`: uma só fonte, para os dois nunca divergirem.

## 15/11/2026 (5) — álbum: botões só no hover; WhatsApp no computador mostra a cartinha pronta
- Baixar/WhatsApp ficam invisíveis e aparecem ao passar o mouse (ou foco por teclado) na cartinha; em telas de toque ficam sempre à vista.
- «WhatsApp» no computador só abria o site, sem a imagem (o WhatsApp Web não aceita imagem por link). Agora abre uma janela (`<dialog class="c-envio">`, `carta.js::painelEnvio`) com a imagem pronta e os caminhos que funcionam: **Copiar e abrir o WhatsApp Web** (cola com Ctrl+V), **arrastar** a imagem para a conversa, **Compartilhar…** (se o sistema permitir) e **Baixar**. No celular continua a lista de compartilhar com o arquivo.

## 15/11/2026 (4) — «Por que esta nota?» na página do agente
- `agente.html` ganhou, logo abaixo dos indicadores, a conta inteira do mês: 100 pontos iniciais → cada critério (qtd × peso = pontos, com saldo corrido e explicação em português) → ajuste de presença → nota final; resumo (descontos, bônus, presença), **turnos descontados por dia/turno**, **justificados** (chuva, cronograma) e **visitas em sequência suspeita**. Botão «Imprimir este detalhamento» (folha só com ele). Para quando o agente questionar a nota.
- Dados novos em `agentes_dados.js` (`gerar_agentes.py::ler_evidencias`, campo `ev` por mês): só o que já é público na planilha. **Sem** logradouro/número do imóvel (endereço de morador) e sem motivo de saúde (justificados mostram só o rótulo do cronograma, ex. «Chuva»).
- Testes: `test_sessao10.py` (evidências) e `test_visual_navegador.py` (bloco «agente»).

## 15/11/2026 (3) — nível ELITE: valorizar quem tirou 100 fora do pódio
- Antes só o top 3 com 100 se destacava (LENDÁRIA); os demais com 100 saíam iguais a quem tem 90-99 (OURO). Agora nota 100 fora do pódio = **ELITE**: cartão de ouro com halo dourado, brilho sempre aceso e selo «100» (`.n100`, `.c-selo100` em `carta.css`; regra em `carta.js::medidas`). 90-99 segue OURO; pódio segue LENDÁRIA/DESTAQUE. Filtro de nível do álbum ganhou «ELITE».

## 15/11/2026 (2) — moldura das cartinhas alinhada ao contorno
- Louros do Ouro: a haste agora é um caminho paralelo ao escudo (fundo reto → chanfro 30×26 → lateral), a ~8 px de fora, em vez de uma curva solta a 15 px. Aletas da Prata: uma peça por lado, colada na lateral reta (y 200→358), com pontas em 45° (antes eram dois degraus soltos). Coroa e gema seguem centradas em x=136. A mesma lista de peças alimenta a tela e o PNG de canvas (`ornPecas` em `carta.js`).

## 15/11/2026 — PNG da cartinha fiel, botões embaixo, WhatsApp Web
- Botões Baixar/WhatsApp ficam **embaixo** da cartinha (antes cobriam o cartão).
- O PNG agora é gerado do HTML da própria cartinha (`html-to-image`, MIT, em `assets/html-to-image.js`, carregada só no 1º uso), com animações paradas (`.c-captura`). Se falhar, cai no desenho antigo em canvas (`pngCanvas`). Ícones `<use>` são copiados para dentro do SVG antes da captura.
- WhatsApp: **computador** abre `web.whatsapp.com` (janela aberta no clique) e deixa a imagem copiada para colar (Ctrl+V); se a cópia não for permitida, baixa a imagem. **Celular** usa a lista de compartilhar com o arquivo. Não testado em iPhone/Safari real.

## 14/11/2026 (4) — álbum: compartilhar/imprimir cartinhas e modo reunião
- `album.html`: cada cartinha ganha botões **baixar imagem** e **WhatsApp** (reusam `Carta.enviar`, a mesma imagem de `agente.html`; respeitam «ocultar nomes/fotos»). Botão **Imprimir cartinhas** (A4, 3 por linha, fundo branco, só o que está filtrado na tela; usa `inline-block` porque o Chrome ignora «não quebrar» em grade).
- `projecao.html`: **modo cartinhas** (botão «Cartinhas» ou tecla C; `projecao.html?mes=Mês/AAAA#cartinhas`): uma cartinha grande por tela, do 1º para o último (Top 10/20/Todas), com o que mais deu e tirou pontos. Com nomes ocultos (padrão) o texto do nome, as iniciais e a foto são TROCADOS por «Agente N», não só borrados. Tecla N mostra os nomes.
- Teste: `test_visual_navegador.py` (blocos «álbum» e «reunião»).

## 14/11/2026 (3) — impressão no tema escuro e testes de navegador ajustados
- **Bug:** imprimindo com o tema escuro, o texto dos KPIs saía claro (regra do tema escuro em `ultra-enterprise.css` vencia a de impressão). Agora o `@media print` fica no FIM do arquivo e força texto escuro/fundo branco.
- `agente.css`: `.kpi{position:relative}` evita estouro horizontal no celular (o `::after` ancorava na página).
- `test_visual_navegador.py` copia `album.html` e aceita o fundo claro atual (`rgb(238,242,248)`); `test_sessao10_navegador.py` segue o álbum novo (mês/tema padrão, chips de nível, escala no hover).

## 14/11/2026 (2) — álbum de cartinhas remodelado, tema claro de verdade e semanas compactas
- **Bug do tema:** `album.html` nascia com visual noturno mesmo no tema claro (5 camadas de CSS empilhadas em `assets/album.css` + `ultra-enterprise.css` por cima; `--tx` ficava claro sobre fundo claro).
  `album.css` foi reescrito em UMA camada (claro por padrão, `[data-theme="dark"]` opcional, tudo por variável) e o `album.html` não carrega mais o `ultra-enterprise.css`.
- **Página remodelada:** título + subtítulo, abas com sublinhado amarelo (igual ao dashboard), filtros (Mês/Equipe/Nível/Buscar) e interruptores (apresentação, ocultar fotos) em um painel só, explicação recolhida em "Como ler o álbum",
  atalhos por nível com contagem (clicar preenche o filtro "Nível"; contam só o que passou por equipe e busca), pódio e grade. Cabeçalho segue azul-marinho nos dois temas, alinhado a 1240 px.
- **Celular:** grade de 2 colunas com a carta em escala 0,58 (0,62 de 400 a 480 px); a caixa `.c-conj` tem 272 px cheios mesmo reduzida por transform, então a grade corta o excesso lateral só em ≤ 480 px (`overflow-x: clip`).
- **Dashboard:** os botões das semanas (`.week-chip`) voltam ao tamanho compacto (não esticam para preencher a linha); a linha continua sem quebrar.
## 14/11/2026 — design: menu em linha única, gráficos institucionais e "Por Área" recolhida
- **Menu em uma linha, em qualquer resolução** (`style.css`, `ultra-enterprise.css`, `base.html`): as 11 abas ficam sempre em uma linha só; o tamanho da letra acompanha a largura da caixa (`cqw`, container query),
  então o menu encolhe junto com a tela. Abaixo de 1100 px somem os trechos opcionais (`.tab-opc`: "& Irregularidades", "& Produtividade", "(média dos meses)"); em telas muito estreitas o menu rola de lado, sem quebrar.
  Barra de botões do cabeçalho: os 4 botões dividem a largura e, abaixo de ~1260 px, viram só o ícone (o `title` mostra o nome). Mesma regra na navegação semanal, no comparar de meses, no editor de detecções e na tela de projeção.
- **Gráficos institucionais** (`assets/tema.js` → `window.SENT_GRAF`, `templates/charts.js`): cada série declara um **papel** (`serie1/serie2/serie3/neutro`) ou um estado (`bom/atencao/critico`) e a cor é escolhida pelo tema.
  Séries = azul, laranja e verde-água, validadas (daltonismo ΔE ≥ 9; visão normal ≥ 26) nos dois temas; estado usa a mesma régua dos emblemas. Barras finas (≤ 24 px) com ponta arredondada, grade discreta sem linha de eixo,
  legenda com marcador, tooltip escuro em pt-BR, valor escrito só onde ajuda e total no centro da rosca. Barras de uma única série nominal usam a mesma cor (a cor não repete o que o comprimento já diz).
  Borda de "respiro" entre segmentos precisa existir já na criação (o Chart.js não anima de indefinido para cor).
- **Aba "Por Área" recolhida:** uma linha por área; "ver mais" abre as estatísticas da área e a tabela dos agentes que trabalharam nela. Totais da área (`generate_dashboard.build_areas_agrupadas`): somas, % refeitos sobre os totais,
  tempo médio ponderado pelos imóveis abertos; a mediana fica só por agente (mediana de medianas não é mediana). Buscar um agente abre sozinha as áreas em que ele trabalhou. Faixas de alerta espelhadas de `parametros.py`; teste: `test_areas_agrupadas.py`.

## 13/11/2026 — paralisações coletivas validadas automaticamente
- **Pedido da coordenação:** todas as paralisações coletivas devem estar validadas, e as próximas também, sem passar por validação manual.
- **Detecção nova:** `CONFIRMAR_CHUVA_AUTOMATICAMENTE = True` (`coleta/pontos.py`): a paralisação coletiva (equipe inteira sem lançamento no dia) nasce `confirmada`
  como **Chuva**, com `confirmado_automaticamente`. Férias/atestado individuais continuam entrando `pendente` (`CONFIRMAR_FERIAS_AUTOMATICAMENTE = False`). Reverte a decisão de 02/11 só para paralisação coletiva.
- **As 31 pendentes** em `data/deteccoes_pendentes.json` (Julho 4, Agosto 4, Setembro 7, Outubro 11, Novembro 5) foram validadas como Chuva
  (`validada_por`/`decidido_via` = coordenação, 13/11/2026). Motivo trocável no `deteccao_editor.html` (Capacitação, Reunião...). As 2 férias pendentes não foram tocadas.
- **Bug corrigido (a validação baixava notas):** a contagem dos 23 da regra suprema (`ausencias_ranking.py`, `_preparar_ausencias`) só reconhecia o motivo `"Chuva"`; a paralisação
  confirmada entra no cronograma como `"Chuva (confirmada)"`, então saía da conta, turnos que eram Chuva caíam abaixo de 23 e viravam Turno sem Lançamento (desconto) e os dias esperados subiam.
  Agora o sufixo `(confirmada)`/`(automático)` é ignorado na comparação. Simulado com `regenerar_mes.py todos`: Julho–Setembro idênticos; Outubro 2 notas sobem (até +4,0), nenhuma desce.
- **Meses fechados:** a confirmação muda os cálculos de Julho a Outubro só quando o mês for regerado (`regenerar-mes.yml`, um mês por vez, em ordem). Só Outubro muda (2 agentes).
- Teste: `test_turno_evento.py` (padrão novo + modo manual).

## 11/11/2026 — efeito de raio premium e correção do cartão que crescia
- **Raio premium:** Lendária (raio dourado) e Destaque (magenta com ciano) disparam raios em rajadas, como trovoada: cada galho acende, apaga e acende de novo em tempos diferentes (ciclo de 5,6 s), com clarão suave sobre o cartão, faíscas piscando, arcos correndo pela moldura e o halo das peças de fora pulsando; no hover a tempestade acelera. Só com movimento permitido (`prefers-reduced-motion`); sem movimento, os raios ficam acesos e calmos. O PNG desenha o instante do golpe, com a paleta de cada nível (`raiosPNG`/`arcosPNG`).
- **Correção:** a regra `.carta > * { position: relative }` do refinamento premium tirava as camadas de raios e arcos do posicionamento absoluto: elas empurravam o rodapé (o cartão chegava a 1100 px na página do agente) e ficavam cortadas no álbum, por isso o raio não aparecia. Agora são absolutas de novo.
- **Compactação:** o conteúdo do cartão tinha ~470 px e o álbum/PNG têm 392 px fixos (rodapé cortado). Estatísticas, nome e foto ficaram menores; o rodapé inteiro cabe e sobram ~20 px. No primeiro mês de cada agente o texto é «1º mês» (antes «sem mês anterior», que estourava o rodapé em 7 cartinhas de Julho).

## 11/11/2026 — Lendária «Icon Mármore + Ouro» e álbum mais espaçado
- A Lendária (100 pontos, top 3) deixa a «tempestade azul» e passa a ser mármore branco com filetes dourados, texto escuro, brilho quente e raios suaves em ouro (opacidade .4). Destaque ganha brilho rosa/ciano e Ouro um halo dourado; no hover, números e foto da Lendária ganham brilho e a inclinação máxima sobe para 16° (Destaque e Lendária).
- Álbum: grade e pódio com mais respiro (cartas maiores e mais espaço entre elas).
- Para tela e PNG ficarem iguais, o desenho do PNG (`carta.js`) e as peças da moldura da Lendária (cristais, asas, gema) usam a mesma paleta branco-ouro do CSS.

## 10/11/2026 — moldura premium das cartinhas, publicação mais segura e Outubro fechado
- **Moldura premium (estilo FIFA Mobile):** além do escudo com bisel, brilhos e fio fino, as cartinhas ganham peças FORA do contorno: aletas de metal na Prata; ramos de louro, coroa grande e gema no Ouro; cristais nas laterais, asas nos cantos de cima, coroa e gema na Destaque e na Lendária. Ficam num conjunto `.c-conj` (camada atrás e camada na frente do cartão), porque o recorte em escudo cortaria qualquer peça que passasse do contorno. A mesma lista de peças (`ornPecas` em `assets/carta.js`) alimenta o SVG da tela e o PNG de download. As peças acompanham a inclinação e a escala (o `carta_fx.js` copia `--rx/--ry` para o conjunto; no álbum, a escala `--s` está no conjunto).
- **Publicação:** a etapa do GitHub Pages tem limite de 8 min e, se travar, o workflow espera 1 min e tenta de novo; se as duas falharem, abre uma issue de aviso. Para só republicar sem coletar: Actions → Run workflow, desmarcando a coleta.
- **Cache do navegador:** `scripts/versionar_assets.py` põe `?v=<hash>` em cada `assets/*.js|css` das páginas e renova o nome do cache do `sw.js` a cada publicação (passo «Versionar arquivos do site»).
- **Outubro/2026 fechado** (checklist liberado; o item «dias sem trabalho a classificar» é conferido na página `validar.html`). Pode ser reaberto com `fechar_mes.py reabrir`. Os testes que supunham Outubro aberto passaram a recriá-lo na cópia de teste.

## 10/11/2026 — LIRAa, painéis, gráfico mensal e críticos com detalhes
- **04/11 a 09/11/2026: levantamento de índice rápido (LIRAa)**, evento para todos os agentes. Registrado em `data/cronograma_ausencias.json` como «Levantamento de Índice» (alvo «todos»): ninguém recebe falta nem perde pontos nesses dias, e eles saem dos dias esperados. Vale na próxima coleta.
- «Alertas e Irregularidades»: os 8 cartões ficam sempre numa única linha (tamanhos se ajustam à largura; abaixo de 860 px a linha rola de lado).
- «Ausências»: tudo em painéis recolhíveis padronizados (Como ler, Férias/Atestado, Cronograma, Mapa de calor e agentes, Todos os registros); só o painel dos gráficos vem aberto. Ao imprimir, todos abrem.
- «Nota média por equipe»: saiu a visão semana a semana (cada semana recomeça de 100 e dava notas mais altas que a do mês). Fica só a nota do mês completo, que é a mesma das cartinhas; a tela de reunião seguiu a mesma regra.
- «Agentes em Situação Crítica»: mostra **todos** (não só 5); clicar em cada agente abre mais detalhes (dias, visitas/dia, mediana, alertas, fechados/recusados, % pendência, horas, custo).

## 09/11/2026 — tela de reunião com panorama, cabeçalhos alinhados e home em Novembro
- Tela de reunião: novas telas com o **panorama geral** (total de imóveis trabalhados, visitas, dias de trabalho e nota média, mês a mês) e, para cada mês, o **panorama de visitas** (visitas, imóveis, dias, visitas por dia, tempo médio, áreas, agentes, nota média) e uma tela de **equipes e níveis**. Os totais saem das planilhas mensais (`ler_panorama` em `scripts/gerar_agentes.py`, chave `panorama` de `assets/agentes_dados.js`), sem a equipe sob demanda (Bloqueio); a soma de «imóveis trabalhados» bate com o número do cabeçalho do início. Só o mês mais recente aparece como «em andamento».
- Cabeçalho das páginas secundárias (álbum, evolução, comparar, validar, contestação) agora tem a largura do conteúdo, com o logo na mesma coluna do texto e os botões juntos à direita.
- Início passa a ser **Novembro/2026** (`data/config_home.json`).

## 08/11/2026 — álbum: «Melhor do ano» e clique na cartinha abre a evolução
- Novo item no filtro de mês do álbum, «Melhor do ano»: ranking pela **média das notas de todas as cartinhas mensais** do agente (julho até o mês mais recente, inclusive o mês aberto). Desempate: mais meses, depois nome. ASS e TUR somam o período inteiro; CON usa os 3 últimos meses; EVO é a variação do último mês; POS é a posição na média.
- **Mínimo de 2 meses** (`MIN_MESES_ANO` em `assets/album.js`): quem tem só 1 cartinha mensal não aparece no «Melhor do ano». O rodapé da cartinha mostra quantos meses entraram na média.
- Clicar numa cartinha do álbum agora abre direto a evolução do agente (no mês da cartinha; em «Melhor do ano», no mês mais recente). O detalhamento por passar o mouse continua; na página do agente, clicar ainda fixa o detalhamento.

## 08/11/2026 — formato da borda da cartinha: escudo de cantos cortados
- A cartinha deixa de ter cantos arredondados e passa a ter o formato de escudo (cantos cortados em diagonal: 20 px em cima, 30 × 26 px embaixo), com o anel metálico acompanhando o formato, bisel de luz e sombra, brilhos nos cantos, fio fino interno, coroa (Ouro, Destaque, Lendária) e gema embaixo (Prata em diante), faixa de luz animada nos níveis altos; o PNG de download desenha o mesmo. Só muda o contorno: o interior, as cores por nível e a pontuação ficam iguais.
- O recorte (`clip-path`) corta o `box-shadow`; por isso o brilho externo da Lendária e do Destaque passou para o contêiner (`filter: drop-shadow`). As demais cartas ficam sem a sombra externa.
- `assets/carta.css` (polígono, anel, filete da Lendária) e `assets/carta.js` (`FORMA`/`pathCartao`, usado no PNG de download) têm que ficar iguais; `scripts/test_album.py` confere os dois.

## 08/11/2026 — ranking semanal inclui agente do mês que passou a semana sem lançar nada
- Antes, o ranking de cada semana só tinha quem teve ao menos 1 visita naquela semana: quem ficou a semana inteira sem lançar sumia e inflava a média da equipe (ex.: Equipe 3 na semana 1: 90,5 sem a Alana; 80,4 com ela).
- Agora a visão semanal inclui os agentes do mês sem nenhuma visita na semana, **só se** já trabalhavam antes do período, não são de equipe sob demanda (Bloqueio) e têm turno sem justificativa no cronograma. Quem está de férias/atestado/folga lançado não aparece.
- A pontuação segue a regra do mês: parte de 100, desconta os turnos sem lançamento e aplica a presença mínima (50%); com 0 dia trabalhado a nota é 0.
- Implementação: `agentes_do_periodo` e `agentes_extra` em `scripts/coleta/consolidacao.py`, `agentes_sem_visita` em `saida_excel.py`, `sem_visita_no_periodo` em `ausencias_ranking.py`. Testes: `scripts/test_turno_evento.py`.

## 08/11/2026 — regra suprema: 23+ agentes sem lançamento = CHUVA automática
- **23 ou mais agentes sem lançamento no mesmo dia e turno**, somando todas as equipes, são classificados automaticamente como **Chuva**. Não fica pendente e não exige validação manual; não há desconto de pontos.
- A regra é prioritária e não depende da data de corte da regra de equipe. A contagem considera o total de agentes sem lançamento, inclusive os já cobertos por chuva/reunião no cronograma; férias, folga e ausência individual justificada não entram.
- Com menos de 23, permanece a regra anterior: equipe inteira sem lançamento (2 ou mais agentes ativos) = "Possível Evento Externo ou Interno", sem desconto e sujeito à confirmação; caso contrário, "Turno sem Lançamento".
- Implementação: `scripts/coleta/pontos.py` (`LIMITE_AGENTES_EVENTO_TURNO`, `CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE`, `CLASSIF_CHUVA_AUTOMATICA`) e `scripts/coleta/ausencias_ranking.py` (`_preparar_ausencias`). Testes: `scripts/test_turno_evento.py`.

## 06/11/2026 — álbum vivo, "Como é calculado" dentro do álbum, cronograma por dia recolhido
- **"Como é calculado" virou a 2ª aba do álbum** (`album.html#como-calcula`). `gerar_transparencia.py` agora grava `assets/como_calcula.js` (o álbum carrega ao abrir a aba) e `transparencia.html` só redireciona
  (links antigos). O texto ganhou a seção **"3. Turno sem lançamento: falta ou evento?"** (ordem: cronograma → 22+ agentes = evento → equipe inteira = chuva isolada/reunião → falta) e a data de recálculo vem do `manifest.json`.
- **Cartinhas vivas** (`carta.css` seção "EFEITOS VIVOS" + `assets/carta_fx.js`; `carta.js` ganhou `.c-brilho`, `.c-glitter` e `--v` nos atributos): inclinação 3D e brilho holográfico que seguem o mouse, faixa de luz e faíscas nas cartas
  altas (OURO/DESTAQUE/LENDÁRIA), moldura que gira, flutuar no DESTAQUE/LENDÁRIA, entrada em cascata, nota que sobe contando e barras nos atributos. Só as cartas visíveis animam (`.vivo`, via IntersectionObserver);
  tudo respeita `prefers-reduced-motion`. O PNG para baixar não mudou. **Pódio** (top 3, só sem filtros) no topo do álbum; medalhas ouro/prata/bronze. CSS/JS do álbum saíram do HTML: `assets/album.css`, `assets/album.js`.
- **Cronograma por dia:** "Ocorrências no Cronograma (por equipe)" agora lista um `<details>` por dia (ou período), todos recolhidos, com Expandir/Recolher todos; imprime aberto. `agrupar_cronograma_por_dia` em `generate_dashboard.py`.

## 06/11/2026 — otimizações de leitura/geração (menos token, mais rápido)
- **Cache em memória da leitura das semanas** (`_ler_aba_visitas` em `coleta/cache_semanas.py`): guarda o `read_excel` CRU (as conversões, como `acima_teto_media`, rodam a cada
  chamada), chave = caminho + data de modificação + tamanho, devolve cópia, invalidado por `_salvar_df_semana`, seguro entre threads; `SENTINELA_SEM_CACHE_LEITURA=1` desliga.
  **Ganho medido (modesto): Acumulado 66 → 46 s, rodada do histórico 47 → 39 s, detecção sem ganho (lê cada semana uma vez); `regenerar_mes todos` ≈ 228 → 184 s (~20%).**
  Saída idêntica com e sem cache (152 mil células de 8 planilhas + `deteccoes_pendentes.json`). Próximo gargalo medido: `_primeira_visita_historica` reabre todas as semanas (~15 s por processo).
- **`scripts/rodar_testes.py`** (roda no Windows) passa a ser a ÚNICA lista de testes; `rodar_testes.sh` só chama ele. Teste novo: `test_cache_leitura.py`.
- **`scripts/xlsx_scan.py`** abre a planilha UMA vez, em `read_only`, e lê por `iter_rows` (antes: reabria a cada aba e criava um objeto por célula). Geração do dashboard 3 a 7× mais rápida
  (Outubro 7,9 s → 1,5 s; Acumulado 14,8 s → 2,2 s), **HTML e `partes/` idênticos byte a byte** (conferido em 3 planilhas e pelo `tools/comparar_saidas.py`). As planilhas abertas são fechadas ao sair do processo (`atexit`).
- **`CLAUDE.md` enxuto** (7,4 → ~5 KB) + **`.claude/rules/`** (coleta, dashboard, editores/Worker, workflows): carregam só quando se abre arquivos da área.
  `.claude/settings.json` bloqueia também `data/deteccoes_pendentes.json` e os `chart.umd.js` — para dados use `python3 scripts/resumo.py`.
- **`scripts/resumo.py`** (consultas curtas: meses, detecções, ranking com `--vs` backup, cronograma, manifest), **`scripts/regerar_paginas.py`** (todas as páginas numa chamada) e
  **`tools/comparar_saidas.py`** (rede de segurança para refatorar o gerador: as chamadas do CI em duas versões, saída idêntica). Testes: `test_resumo.py`.
- `docs/PROMPT_DIVISAO_DASHBOARD.md`: plano para dividir `generate_dashboard.py`. **Não executado de propósito** (60 funções pequenas; ganho pequeno para o risco).

## 05/11/2026 — Maio e Junho saem do programa; regras novas em todos os meses; cabeçalho compacto
- **Maio e Junho/2026 excluídos** (semanas 305–312): sem coleta (`PRIMEIRA_SEMANA_COLETA = 313`), sem página, fora do Acumulado e da média dos meses.
  Removidos: `data/semanas/305–312*`, `data/historico/semanas_305-308/309-312` (+ backups), `historico/` e `partes/` desses meses, 13 detecções e 35 itens de
  cronograma que terminavam antes de 28/06, e a produção de Maio/Junho em `data/outras_atividades.json`. O histórico do Git guarda tudo.
- **Julho, Agosto e Setembro reabertos e recalculados com as regras atuais**, depois congelados de novo. Estavam com as regras antigas. Depois do recálculo a nota sobe para 38 de 49 agentes (Julho), 36 de 42 (Agosto) e
  39 de 42 (Setembro); ninguém desce; média +6 a +8 pts (maior alta +18,5); a posição muda para 44, 34 e 32 agentes. Cópias antigas: `data/historico/backup_congelado/*_antes-das-regras-novas.xlsx`.
  (O registro de 02/11 dizendo que "Maio–Outubro foram regenerados" não era verdade para os meses congelados.)
- **Chuva confirmada automaticamente voltou a `pendente`** (41 paralisações coletivas de Julho em diante, antes da regra de 02/11 sem validação humana). Férias já
  validadas pela coordenação e decisões de `falta` ficaram como estavam. Atestado: todos os 98 lançamentos já são "Ausência justificada" (sem diagnóstico).
- **Cabeçalho da home refeito:** tudo na mesma linha e na mesma altura (36 px, `--hbtn-h`); os 4 botões de texto têm a mesma largura
  (`.hbtn` em `.hnav`) e tema/imprimir viraram quadrados só com o símbolo (`.hbtn-ico`); "Ocultar nomes" e "Animações" viraram `.hopt`;
  no celular os botões ficam em 2×2. Marcação em `scripts/templates/base.html`, estilo em `scripts/style.css`.
- **Pequenas melhorias (05/11/2026):** selo "período em andamento até dd/mm" no cabeçalho dos meses ainda abertos (`periodo_em_andamento` em
  `generate_dashboard.py`); título e explicação do painel de férias corrigidos ("no período", limite de 7 dias úteis, "(confirmada)");
  `regenerar_mes.py` mantém só os 3 backups mais recentes por mês. CI: `test_turno_evento.py` não rodava no CI (só no `rodar_testes.sh`) e o pip não usava cache.
- **Regra do turno sem lançamento, ordem de decisão (coordenação, 05/11/2026):** 1º **22 ou mais agentes** sem lançamento no mesmo turno = evento
  externo/interno (regra máxima; era 20); 2º abaixo disso, **toda a equipe** (agentes ativos, 2+) sem lançamento = chuva isolada ou reunião;
  3º senão, falta (desconta), salvo o que o cronograma cobre (atestado, folga, férias). Só a observação da aba Ausências mudou de texto
  (a classificação segue "Possível Evento Externo ou Interno"). Julho–Outubro recalculados. **Opção `CONTAR_COBERTOS_POR_EVENTO_NO_LIMITE`**
  (padrão False = como antes: só contam os não cobertos pelo cronograma): ligada, quem já está coberto por chuva/reunião também entra nos 22,
  e confirmar a chuva de uma equipe deixa de tirar o turno das outras do limite (sem ela, em Setembro, confirmar 7 paralisações como chuva
  faria 8 agentes perderem até 1,5 pt). Férias, folga e atestado nunca contam. Teste: `test_turno_evento.py`.
- **Workflow "Regenerar mês congelado"** (`regenerar-mes.yml` + `scripts/regenerar_mes.py`): refaz um mês antigo com as regras de hoje, com
  modo simulação e backup (ver OPERACAO.md). Reabre um mês por vez, em ordem: o desempate do ranking lê a média dos meses anteriores do
  `manifest.json`; as reaberturas de Julho–Setembro feitas no mesmo dia, todas de uma vez, deixaram Agosto e Setembro sem o desempate,
  e foram refeitas em ordem.

## 04/11/2026 — cartinha: nível e borda pela mesma nota arredondada; cartinha 100 redesenhada
- **Correção:** o nível (ouro/prata/bronze/destaque) usava a nota exata e a borda usava a arredondada — 89,6 aparecia como 90, com cartão prata e borda de ouro. Agora os dois usam a nota arredondada que está escrita no cartão (≥ 90 ouro, ≥ 75 prata, abaixo bronze; destaque = top 3 com 90–99). `assets/carta.js` (`medidas`). Teste ajustado em `scripts/test_sessao10_navegador.py`.
- **Medida CON (consistência) da cartinha:** passou a considerar só os TRÊS ÚLTIMOS meses do período mostrado (hoje, agosto a outubro): desvio-padrão dessas três notas, CON = 100 − 5 × desvio (máx. 99). Antes usava todos os meses, e um único mês fora da curva (ex.: Maio 0,0 do agente 1936) zerava o CON. Com só um mês, CON = 99. `medidas` em `assets/carta.js`.
- **Quem chega ao teto de 100 é ordenado pela nota bruta (100 + critérios, ex.: 110,6), só na cartinha e no álbum.** Desempate: média dos meses anteriores e depois a posição oficial. A nota mostrada continua limitada a 100 e o ranking oficial (dashboard, Excel, `_preparar_ranking`) não mudou. `Carta.bruta`/`Carta.posicao` em `assets/carta.js`; ordenação em `album.html`.
- **Escala única da cartinha (pela nota arredondada):** 100 LENDÁRIA (tempestade) · 90–99 OURO · 80–89 PRATA · 70–79 BRONZE · 60–69 AÇO · abaixo de 60 FERRO. Cor do cartão e borda seguem a mesma faixa; a borda engrossa com o nível (`--bw`). **Mudou:** prata passou de ≥ 75 para ≥ 80 e bronze de < 75 para 70–79 (aço e ferro são novos). Top 3 com 90–99 = cartão de ouro com borda holográfica (`b-top`, rótulo DESTAQUE); a de 100 é uma só, sem variação de top 3. Filtro "Nível" do álbum atualizado.
- **Cartinha 100** ("Tempestade"): fundo escuro com raios e faíscas na borda, só com a classe `b-100` (`assets/carta.css` e o desenho do PNG em `assets/carta.js`; os raios são gerados em `RAIOS/ARCOS/FAISCAS`).

Uma entrada por decisão: **data · decisão · por quê · onde está no código**. Acrescente sempre que uma regra mudar.

## 04/11/2026 — desempate por média, detalhamento na cartinha e opção de ocultar fotos
- **Desempate do ranking:** nota igual → fica na frente quem tem a maior **média dos meses anteriores** (a da tabela "Média Mensal por Agente", arredondada em 1 casa;
  o mês do próprio período não entra; sem histórico fica atrás; empate total mantém a ordem anterior). `coleta/ausencias_ranking.py` → `_media_historica_por_agente`
  + chave de ordenação em `_preparar_ranking`. Teste: `scripts/test_desempate.py`. O álbum (`album.html`) aplica a mesma regra no navegador.
- **Cartinha:** passar o mouse mostra o detalhamento (todos os critérios do mês, vindos de `detalhe` em `assets/agentes_dados.js`, gerado por `scripts/gerar_agentes.py`);
  clicar fixa (no celular, o toque). Borda por faixa de nota e cor do 100 = ouro de 90–99 (`assets/carta.css`); foto por ID em `assets/fotos.js`; checkbox "Ocultar fotos".

## 03/11/2026 — organização do repositório (branch `organizacao`)
- **README reduzido** (853 → ~60 linhas). Conteúdo movido sem remover informação: `docs/OPERACAO.md` (coleta, detecção de férias, cronograma, atestado/férias,
  meses congelados, planilhas antigas), `docs/INSTALACAO.md` (Secrets, Pages, Worker, teste local), `docs/REGRAS_DETALHADAS.md` (ranking normalizado, teto de
  20 min, regras de ausência) e o histórico de sessões no fim deste arquivo. `docs/REGRAS.md` ficou curto de propósito (é o que o `CLAUDE.md` manda ler).
- **Correções feitas no texto migrado:** cron (era "segunda/terça/quinta"; real: dom/seg/ter 07:00 UTC); férias disparam com 7 dias úteis
  (`LIMITE_DIAS_UTEIS_FERIAS`; o README falava em "mais de 5" e numa constante que não existe mais); detecções novas entram `pendente` (o README dizia
  "confirmado automaticamente"); nome do repositório (`dashboard-visitas` → `sentinelaprime`) e URLs; árvore de pastas completa.
- **Novos:** `.env.example`; `.gitignore` revisado (`.env`, `node_modules`, `.playwright`, `.wrangler`, temporários); `scripts/rodar_testes.sh` passou a incluir
  `sessao8/9/10` (o CI já rodava) e mostra a última linha de saída quando o teste não imprime ✅/❌.
- **`scripts/coletar_evisita.py` dividido** (4.953 linhas → fachada de ~70 linhas + pacote `scripts/coleta/` com 16 módulos em camadas; o maior tem 769 linhas).
  Cada nó (função/constante) foi copiado sem alteração: o AST dos 259 nós é idêntico ao original, nenhum nome ficou indefinido e as 164 constantes
  (inclusive as carregadas dos JSON) e 116 funções têm o mesmo valor/bytecode (única diferença: o compilador não otimiza chamada de método em nome importado).
  A fachada reexporta todos os nomes e repassa `C.X = valor` aos módulos que possuem `X` (os testes fazem isso com `HOJE_OVERRIDE`, `CONFIRMAR_*`, `PASTA_SEMANAS`...;
  sem esse repasse 4 testes falham — verificado). `python scripts/coletar_evisita.py ...` e `import coletar_evisita as C` seguem iguais; workflows não mudaram.
  Mudanças pontuais de lugar para evitar ciclos: `_classificar` → calculos; `_carregar_agentes_sem_abono`, `_agente_sem_abono_em`, `CAMINHO_AGENTES_SEM_ABONO` → deteccao;
  `_preparar_ponto_estrategico` → saida_excel. Agora só `coleta/sessao.py` importa `selenium`.
- Nada de regra de negócio, pontuação, workflow ou HTML da raiz foi alterado.

## 02/11/2026
- **Possível Evento vale para todos os períodos (Maio–Outubro)** (`EVENTO_COLETIVO_A_PARTIR_DE = None`). Reclassifica ~1.100 turnos
  (Maio 246, Junho 161, Julho 198, Agosto 143, Setembro 202, Outubro 157); média de pontos sobe de 6 a 8 por mês, ninguém desce.
  Para poupar o passado: `date(2026, 10, 4)`.
- **Turno sem Lançamento é o padrão; Possível Evento Externo/Interno** com 22+ agentes no mesmo turno (era 20; mudou em 05/11/2026) ou equipe inteira sem lançamento
  (sem desconto). Antes de descontar, confere cronograma. Por quê: coordenação quer verificar chuva/treinamento/atestado/férias/folga/reunião
  antes de punir. → `_preparar_ausencias`, `LIMITE_AGENTES_EVENTO_TURNO`. Teste: `test_turno_evento.py`.
- **Detecções novas de férias e paralisação entram `pendente`** (antes entravam confirmadas). Decisões antigas intactas.
  → `CONFIRMAR_FERIAS_AUTOMATICAMENTE`, `CONFIRMAR_CHUVA_AUTOMATICAMENTE`.
- **Agente 3177 — Patricia Lanjer de Souza Domingues, Equipe 3** (agente nova). Treinamento lançado no cronograma de 05/10 a 30/10/2026
  (`Reunião/Treinamento`). Se continuar em novembro, estender o período em `data/cronograma_ausencias.json`.
- **Alana (2951) e Teonilda (3035)** seguem como **falta** (decisão da coordenação): desconto mantido.
- **Painel de Custos remodelado:** custo no ritmo × custo real; dias esperados já sem férias/atestado/treinamento/paralisação;
  média geral = folha ÷ horas úteis; tabela de custo mensal por agente; legendas e faixas. → `generate_dashboard.py` (`build_kpi_custos` e afins).
- Seletor de meses no tema claro: cores próprias (antes se misturava ao cabeçalho). → `scripts/style.css` (`.period-select`).
- Ranking de todos os meses conferido: Maio–Outubro regenerados com o método novo; Acumulado segue no antigo.

## Pendente de decisão (02/11/2026)
- Dias de chuva da Ana Gabriela (28 e 29/10, 14/10 tarde, 30/10 manhã): não confirmados (só havia previsão, sem medição).
- Os 7 turnos de Outubro classificados como evento (06/10 M, 08/10 M, 13/10 M e T, 14/10 M, 15/10 M, 30/10 T) aguardam confirmação.

---

# Histórico de sessões (migrado do README em 03/11/2026, texto original)

Os itens abaixo descrevem o que foi feito em cada sessão (29/10 a 01/11/2026). Servem de consulta; as regras atuais estão em `docs/REGRAS.md`.

## Sessões 8 e 9 (31/10/2026) — coordenação e agentes

**Pré-requisito:** Cloudflare configurada (seção acima). Sem ela, `validar.html` avisa e o formulário de contestação não aparece.
Copie para o repositório: `.github/`, `partes/`, `assets/` (agora com `agentes_dados.js` e ícones), `worker/` (cole o novo `index.js` no Cloudflare e **publique**), e os arquivos novos `agente.html`, `contestacao.html`, `manifest.webmanifest`, `sw.js`, `data/meses_arquivados.json`, `data/metas_equipes.json`.

### `validar.html` — abas novas
- **Ajuste de pontos**: agente, dia, pontos (até ±20), motivo curto. Pede confirmação com resumo; aparece no Extrato como "Ajuste manual: motivo" (**público**: o sistema recusa motivo com palavras de saúde/atestado). Lista os ajustes lançados, cada um com **Desfazer**. Mês fechado não aceita ajuste.
- **Equipe parada**: chuva, reunião/treinamento/capacitação, levantamento de índice, ovitrampa, recuperação de casas; uma equipe ou todas; datas (até 30 dias); dia inteiro, manhã ou tarde. Grava no cronograma (substitui o `cronograma_editor.html`). Cada parada tem **Remover**.
- **Fechar mês**: lista de conferência automática (semanas coletadas e mês terminado; próximo mês e ciclo cadastrados; nenhuma férias esperando validação; nenhum dia sem classificação; cópia de segurança automática). O botão só liga com tudo ✅. Fechar congela o mês e as semanas dele. **Reabrir** exige digitar o nome do mês e faz cópia antes (em `data/historico/backup_congelado/`).
- **Contestações**: pedidos dos agentes; **Aceitar** (com pontos opcionais, que viram um ajuste) ou **Recusar**, sempre com resposta curta.
- **?**: ajuda com o que cada botão faz.
- **Aplicativo no celular**: "Adicionar à tela inicial" instala como "Sentinela — validação". O PIN só vale enquanto o app está aberto; o service worker guarda só a página e nunca o que vem do Worker.

### Para os agentes
- **`agente.html?id=…` / `?nome=…`**: nota por mês e por semana, dias trabalhados × esperados, o que mais tirou e deu pontos. Só dados públicos, sem saúde; respeita o modo apresentação. Há link 📈 no Ranking e no Extrato.
- **Extratos em lote** (aba Ranking): "Imprimir da equipe" e "Imprimir de todos do mês" — uma folha por agente, sem página em branco; use "Salvar como PDF" na impressão.
- **Contestação**: no Extrato (só mês aberto), "Algo errado? Peça uma revisão" → critério + uma frase → o agente recebe um **código** e consulta a resposta em `contestacao.html`. Tudo fica só no Worker (nada em arquivo público); limites: 4 pedidos/hora por rede, 3 por dia por agente, campo-isca anti-robô, sem links no texto.
- **Comparativo semanal por equipe** (aba Equipes do mês): nota média de cada equipe por semana; semana parcial em tom mais claro.
- **Metas por equipe** (opcional): `data/metas_equipes.json`, ex.: `{"Equipe 1": 25}`. Quem não aparece usa a meta padrão (20). Aparece em "Como o ranking é calculado". Hoje o arquivo está vazio.

### Testes
`python scripts/test_sessao8.py`, `python scripts/test_sessao9.py` e `node worker/test_worker.mjs` rodam no workflow. Os de navegador (`scripts/test_sessao8_navegador.py`, `scripts/test_sessao9_navegador.py`) exigem Playwright e rodam só no computador de desenvolvimento.

## Identidade visual "painel de monitoramento" (31/10/2026)

Todas as páginas (dashboard, histórico, semanas, acumulado, `validar.html`, `agente.html`, `contestacao.html`, transparência) usam o mesmo visual: fundo azul-marinho profundo com as cores do logo da prefeitura (amarelo, vermelho e verde-água) e a faixa do topo que repete o sublinhado do logo. Números e títulos em **Barlow Semi Condensed**, texto em **IBM Plex Sans** — as fontes ficam em `assets/fonts/` (sem internet externa; licença OFL) e são carregadas por `assets/fontes.css`.
- **Impressão continua em papel branco** (relatórios, extratos e lote).
- No celular o cabeçalho deixa de ficar fixo no topo e as abas rolam para o lado.
- Para ajustar cores: no dashboard, `scripts/style.css` (bloco `:root`); nas outras páginas, o bloco `:root` no começo de cada arquivo.
- Copie para o repositório também: `assets/fonts/`, `assets/fontes.css` e os ícones novos `assets/icone-*.png`.

## Novidades de 29–30/10/2026

**Visões semanais (mês vigente).** Outubro e Novembro/2026 (e os próximos meses) ganham uma barra
`Semana 1 | Semana 2 | … | Mês completo` no topo da página do mês. Cada semana é uma página completa, com as
**mesmas regras** do ranking aplicadas só àqueles dias (veja a aba Equipes para o desempenho por equipe).
A semana em andamento aparece como **parcial**. Quando o mês é arquivado (`MESES_ARQUIVADOS`), as semanas dele
congelam junto na execução seguinte. Meses anteriores a Outubro não ganham semanais
(`PRIMEIRA_SEMANA_VISAO_SEMANAL`). Teste: `python scripts/test_semanal.py`.

**Presença mínima (nota proporcional).** Presença = dias trabalhados ÷ dias esperados (os esperados já descontam férias,
folga e ausência justificada). Abaixo de 50% (`PRESENCA_MINIMA_FRACAO`) a nota é multiplicada por presença ÷ 50%.
Só vale de Outubro/2026 em diante e não vale para Equipe Bloqueio / Ponto Estratégico. Aparece como linha no Extrato.

**Rótulo neutro.** O repositório é público: "Atestado" passa a ser sempre "Ausência justificada" e a detecção
automática grava só "Férias". Entradas antigas são convertidas na leitura (`_motivo_neutro`).

**Dia em andamento.** O dia de hoje nunca gera ausência, e quem ainda não lançou nada hoje não "deve" o dia de hoje nos dias esperados.

**Setembro/2026 reaberto e arquivado de novo (29/10).** Foi refeito com as regras atuais (dias esperados corrigidos,
feriado de 07/09). A versão anterior está em `data/historico/backup_congelado/`. Julho e Agosto continuam congelados.

**Transparência e peso das páginas.** `transparencia.html` explica o cálculo e é gerada das constantes do código
(`python scripts/gerar_transparencia.py`); tem link no cabeçalho e no Extrato. As páginas ficaram bem mais leves:
o Chart.js é um arquivo compartilhado (`assets/chart.umd.js`) e as tabelas de alertas e os extratos ficam em
`partes/` e carregam só quando você abre a aba/extrato (funciona também com o arquivo aberto do disco).
Ao subir arquivos à mão, suba também as pastas `partes/` e `assets/`.

**Atualização de 30/10/2026 — meses antigos recalculados.** Maio a Setembro foram reabertos, recalculados com as regras novas
(sem fator de normalização, feriados em todos os meses, dia inteiro sem lançamento, presença mínima, sem abono) e arquivados de novo.
As planilhas anteriores estão em `data/historico/backup_congelado/`. O **Acumulado** continua no método antigo (período longo).
`data/agentes_sem_abono.json` agora inclui Alana (2951) e Teonilda (3035) desde 01/01/2026: férias viram falta; só ausência
justificada lançada pela coordenação abona. Para tirar alguém da lista, apague a entrada.

**Acumulado = só a média.** Na página Acumulado a aba Ranking passa a ser "Ranking (média dos meses)": a média simples das notas
mensais de cada agente (com a tendência e a evolução). O ranking detalhado e o Extrato ficam na página de cada mês.

## Blindagem da coleta (30/10/2026)
- **Timeouts:** toda chamada HTTP usa (conexão 15 s, leitura 60 s); o Selenium tem tempo máximo de carga de página (60 s) e de espera por elemento (30 s).
- **Novas tentativas:** espera crescente com jitter (1 s, 2 s, 4 s… até 30 s) nas páginas, no login (3 tentativas) e na verificação de saúde.
- **e-Visita fora do ar:** antes de coletar, o coletor testa a página de login. Se não responder, **pula a coleta e publica com os dados que já existem**; as semanas são tentadas de novo na próxima execução (aviso no resumo da execução).
- **Uma semana com problema não derruba as outras:** o erro vai para o resumo (GITHUB_STEP_SUMMARY) e a coleta segue. Sessão caída = abre sessão nova e refaz a semana uma vez. Duas semanas seguidas falhando por inteiro = para (site instável) e deixa o resto para a próxima execução.
- **Tempo:** o coletor não começa semana nova depois de 170 min; o passo tem teto de 240 min e o job de 330 min. Se estourar, o site é publicado com o que já foi salvo.
- **Cache nunca piora:** um agente que volta sem nenhuma visita, ou com menos da metade do que já estava salvo, mantém os dados antigos.
- Versões das ações do GitHub fixadas (checkout 4.2.2, setup-python 5.3.0, upload-pages-artifact 3.0.1, deploy-pages 4.0.5) e do `requirements.txt` já eram fixas.
- Teste: `python scripts/test_coleta.py`.

## Sessão 10 — visual claro, tela de reunião e exportação (01/11/2026)

- **Tema claro é o padrão.** Em todas as páginas há o botão "Tema escuro / Tema claro" no cabeçalho; a escolha fica salva só no navegador de quem clicou (`assets/tema.js`). A impressão e o PDF saem sempre em fundo branco.
- **Ícones próprios** (`scripts/icones.py`) no lugar dos emojis de enfeite. Os emojis de situação (🟢🟡🟠🔴 ✅ ❌ ⛔) continuam, porque fazem parte da informação.
- **Gráfico por equipe, semana a semana** com as cores do logo e o valor escrito em cada barra.
- **Animação de entrada nos números** (contagem até o valor, 0,6 s). Caixa "Animações" no cabeçalho desliga; respeita a opção "reduzir movimento" do aparelho.
- **Baixar o ranking**: na aba Ranking, botão "Planilha (CSV, abre no Excel)" (sem nomes se o Modo apresentação estiver ligado) e link para o .xlsx completo do período.
- **Tela de reunião** (`projecao.html`, botão "Tela de reunião" no cabeçalho): alterna sozinha entre resumo do mês, top 10, maior evolução, equipes semana a semana e média por mês. Teclas: espaço pausa, ← → trocam, F tela cheia, N mostra/oculta nomes. Nomes começam ocultos.
- Teste novo: `python3 scripts/test_visual_navegador.py` (só na máquina de desenvolvimento).
- **Arquivos novos para copiar ao repositório:** `assets/tema.js`, `projecao.html`, `scripts/icones.py` (e, como sempre, as pastas `.github`, `partes` e `assets`).

## Sessão 11 — comparar meses, cartão do agente e linha do tempo (01/11/2026)

- **Comparar mês com mês** (`comparar.html`, botão "Comparar meses" no cabeçalho): escolha dois meses e veja a média geral, quem subiu, quem caiu e quem ficou estável (até 0,5 ponto), agrupado por equipe, com quantas posições cada um ganhou ou perdeu. Abas "Quem subiu / Quem caiu". Avisa quando um dos meses ainda está aberto.
- **Cartão do agente em estilo carta de jogador (com o logo novo em tom sobre tom, `assets/logo_carta.png`)** (topo de `agente.html`): nota do mês em destaque, equipe, posição e seis medidas de 0 a 99 (ASS assiduidade, TUR turnos cobertos, CON consistência, EVO evolução, POS posição, MED média dos meses). Nível pela nota: ouro ≥ 90, prata ≥ 75, bronze abaixo; "destaque" para top 3 com nota ≥ 90. Sem foto (usa as iniciais) e sem marcas de terceiros. No Modo apresentação nome e iniciais ficam borrados. A explicação das medidas aparece ao lado do cartão.
- **Linha do tempo do agente** (`agente.html`): mês a mês (e semana a semana dentro do mês aberto) com um quadradinho por dia esperado — cheio = trabalhado, vazio = sem lançamento — e etiquetas das **paradas da equipe** (chuva, reunião, mutirão…), que não contam como falta. Fica de fora, de propósito, qualquer lista dia a dia de ausência por agente: isso é sensível e o repositório é público.
- `scripts/gerar_agentes.py` passou a gravar `paradas` (vindas de `data/cronograma_ausencias.json`) em cada mês e semana.
- Testes novos: `scripts/test_sessao10.py` (entra no workflow) e `scripts/test_sessao10_navegador.py` (só na máquina de desenvolvimento).
- **Copiar para o repositório:** `comparar.html`, `agente.html`, `scripts/` e `.github` (e as pastas `partes` e `assets`, como sempre).

### Álbum de cartinhas (`album.html`)
Todas as cartinhas dos agentes, da maior nota para a menor, com o número do lugar. Passar o mouse (ou tocar no celular) amplia a cartinha; clicar abre a evolução do agente. Filtros por mês, equipe, nível (destaque/ouro/prata/bronze) e busca por nome; respeita o Modo apresentação e o tema claro/escuro. Botão "Álbum de cartinhas" no cabeçalho do painel.
O desenho da cartinha agora vive em `assets/carta.css` e `assets/carta.js` (usados pelo álbum e pela página do agente) e o logo em `assets/logo_carta.png`.
**Copiar:** `album.html`, `agente.html`, `assets/` (carta.css, carta.js, logo_carta.png) e `scripts/`.

### Cartinha como imagem / WhatsApp (página do agente)
Dois botões ao lado da cartinha: **Baixar imagem** (PNG) e **Enviar pelo WhatsApp**. No celular abre a lista de compartilhamento já com a imagem anexada; no computador baixa a imagem e abre o WhatsApp com a frase pronta (basta anexar). No Modo apresentação a frase sai sem o nome e a imagem sai com o nome coberto por bolinhas. A imagem é desenhada no próprio navegador (`Carta.png` em `assets/carta.js`), então só funciona pelo endereço do site (não abrindo o arquivo direto do computador). Copiar: `agente.html` e `assets/carta.js`.
