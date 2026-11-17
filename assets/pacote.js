/* Abertura de pacote (tela de reunião, tecla P): um pacote fechado que se rasga no topo, solta as cartinhas dos agentes que tiraram 100
   girando, e depois revela uma a uma, DE TRÁS PRA FRENTE, até o 3º, o 2º e o 1º lugar, cada vez com mais efeito.
   Genérico: quem chama (projecao.js) entrega os itens já na ordem do ranking (melhor primeiro):
     { rank, rot, eq, nota, mk: () => html da cartinha, prep: (raiz) => ajustes (ex.: ocultar nome) }
   Entrada: Pacote.iniciar(el, itens, { mes }) → { passo(), fase(), ocupado() }.  Sem nada disso quando o sistema pede menos movimento (sem animação, só o resultado). */
(function () {
  'use strict';
  /* REDUZ = sem animação. Vem do sistema (prefers-reduced-motion) ou da escolha da pessoa no botão «Animações» (carta_fx.js → Movimento). */
  var REDUZ = false;
  function atualizaReduz() { REDUZ = window.Movimento ? Movimento.reduz() : !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); return REDUZ; }
  atualizaReduz();
  var NIVEL = { 1: ['#FFD25A', '#FFF6C8', '#F0B020', '#FF9A1F'], 2: ['#E6EEF9', '#9FB6D6', '#FFFFFF', '#6CC4F2'], 3: ['#E8A060', '#FFD0A0', '#B8662A', '#FFE9CF'], 0: ['#FFD25A', '#FFF3B0', '#6CC4F2'] };
  var FAIXA = { 1: ['🥇', '1º LUGAR'], 2: ['🥈', '2º LUGAR'], 3: ['🥉', '3º LUGAR'] };

  function div(cls, html) { var d = document.createElement('div'); d.className = cls; if (html != null) d.innerHTML = html; return d; }
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function esp(ms) { return new Promise(function (r) { setTimeout(r, REDUZ ? 0 : ms); }); }
  /* anima e, no fim, grava o estado final no style e solta a animação (sem deixar animação «presa» mandando no elemento) */
  function anima(el, kf, dur, opc, final) {
    if (!el) return Promise.resolve();
    if (REDUZ || !el.animate) { if (final) Object.keys(final).forEach(function (k) { el.style[k] = final[k]; }); return Promise.resolve(); }
    var o = { duration: dur, fill: 'both', easing: 'ease-out' }; if (opc) Object.keys(opc).forEach(function (k) { o[k] = opc[k]; });
    var a = el.animate(kf, o);
    return a.finished.then(function () { if (final) Object.keys(final).forEach(function (k) { el.style[k] = final[k]; }); a.cancel(); }, function () {});
  }
  function centro(el, ref) { var r = el.getBoundingClientRect(), p = ref.getBoundingClientRect(); return { x: r.left - p.left + r.width / 2, y: r.top - p.top + r.height / 2, w: r.width, h: r.height }; }
  function zig(y, inverso) {   // borda picotada do rasgo: a mesma linha serve ao corpo e ao topo, então as duas peças se encaixam
    var p = [], n = 26, i;
    for (i = 0; i <= n; i++) p.push([(i / n * 100).toFixed(2) + '%', (y + (i % 2 ? -1.1 : 0.9)).toFixed(2) + '%']);
    return inverso ? p.reverse() : p;
  }
  function poli(pts) { return 'polygon(' + pts.map(function (q) { return q[0] + ' ' + q[1]; }).join(',') + ')'; }
  var VERSO = '<div class="pk-esc"><div class="c-pacote pk-verso"><div>SENTINELA<small>CARTINHA</small></div></div></div>';

  function iniciar(el, itens, cfg) {
    cfg = cfg || {};
    var N = itens.length, palco = div('pk-palco'), fase = 'fechado', ocupado = false, atual = -1;
    atualizaReduz(); palco.classList.toggle('mov', !REDUZ);
    var ordem = itens.map(function (_, i) { return i; }).reverse();   // revela do último para o primeiro
    el.appendChild(palco);
    var W = palco.clientWidth || 1000, H = palco.clientHeight || 600;
    /* blocos em coluna: cabeça (dica · controles · contador) / cena (pacote e carta grande) / fileira. Nada fica um em cima do outro: cada bloco tem o seu espaço. */
    var cabeca = div('pk-cabeca'), cena = div('pk-cena');
    palco.appendChild(cabeca); palco.appendChild(cena);

    // ---- fileira de cartinhas (de costas) embaixo; linhas conforme a quantidade ----
    var linhas = N <= 9 ? 1 : N <= 20 ? 2 : 3, porLinha = Math.ceil(N / linhas);
    var eLin = Math.max(0.07, Math.min(0.32, ((H * 0.28) / linhas - 12) / 392, (W * 0.94 / porLinha - 9) / 272));
    var fileira = div('pk-fileira'); fileira.style.setProperty('--e', eLin.toFixed(3)); fileira.style.width = Math.min(W * 0.96, porLinha * (272 * eLin + 8) + 4) + 'px'; 
    var slots = itens.map(function (it, i) {
      var s = div('pk-slot'), g = div('pk-giro', '<div class="pk-f pk-a">' + VERSO + '</div><div class="pk-f pk-b">' + VERSO + '</div>');
      s.appendChild(g); s.setAttribute('data-pos', String(i)); fileira.appendChild(s); g.style.opacity = '0'; return { s: s, g: g };
    });
    palco.appendChild(fileira);
    var dica = div('pk-dica', ''), contador = div('pk-cont', ''), barra = div('pk-barra');
    cabeca.appendChild(dica); cabeca.appendChild(barra); cabeca.appendChild(contador);
    var CW = cena.clientWidth || W, CH = cena.clientHeight || H * 0.6;
    var ph = Math.max(120, Math.min(CH * 0.94, CW * 0.8 * 1.6)), pw = ph * 0.62;
    var pacote = div('pk-pacote'); pacote.style.cssText = 'width:' + pw + 'px;height:' + ph + 'px;margin:' + (-ph / 2) + 'px 0 0 ' + (-pw / 2) + 'px;font-size:' + (pw / 11) + 'px';
    var arte = '<div class="pk-arte"><i class="pk-crimpe"></i><div class="pk-logo">SENTINELA</div><div class="pk-sub">CARTINHAS</div><div class="pk-mes">' + esc(cfg.mes || '') + '</div><div class="pk-num"><b>' + N + '</b><span>cartas 100</span></div><i class="pk-crimpe b"></i><i class="pk-holo"></i></div>';
    var yR = 14;
    pacote.innerHTML = '<div class="pk-corpo" style="clip-path:' + poli(zig(yR).concat([['100%', '100%'], ['0%', '100%']])) + '">' + arte + '</div>' +
      '<div class="pk-topo" style="clip-path:' + poli([['0%', '0%'], ['100%', '0%']].concat(zig(yR, true))) + '">' + arte + '</div><i class="pk-fenda" style="top:' + yR + '%"></i>';
    var raios = div('pk-raios'), fundo = div('pk-fundo');
    palco.insertBefore(raios, palco.firstChild); palco.insertBefore(fundo, palco.firstChild); cena.appendChild(pacote);
    function texto(d, c) { dica.textContent = d; contador.textContent = c || ''; }
    texto('Clique ou tecle Enter para abrir o pacote', 'Top ' + N + ' do mês');

    // ---- barra de controles: som, automático, pular até o Nº e «Próxima» (toque / controle remoto) ----
    var auto = false, pularAte = 0, timer = null;
    // legenda em texto do que está acontecendo (também lida por leitor de tela): ajuda quem não ouve bem a sala ou o som
    var leg = div('pk-leg'); leg.setAttribute('role', 'status'); leg.setAttribute('aria-live', 'polite'); palco.insertBefore(leg, fileira);
    function legenda(t) { leg.textContent = t; }
    legenda('Pacote fechado. Aperte Enter ou clique para abrir.');
    var opts = '<option value="0">Revelar todas</option>' + [10, 5].filter(function (v) { return v < N; }).map(function (v) { return '<option value="' + v + '">Pular até o ' + v + 'º</option>'; }).join('');
    barra.innerHTML = '<button type="button" data-b="som" title="Som: desligado, ligado ou baixo (tecla S)"></button><button type="button" data-b="auto" title="Revela sozinho, uma por uma (tecla A)"></button><button type="button" data-b="anim" title="Liga/desliga as animações e efeitos (tecla M). Fica guardado neste navegador."></button>' +
      (N > 5 ? '<select data-b="pular" aria-label="Quantas revelar" title="Revelar só as melhores: as demais aparecem de uma vez">' + opts + '</select>' : '') +
      '<button type="button" data-b="prox" class="pk-prox" title="Próxima (Enter, espaço, PageDown ou clique no palco)">Próxima ▶</button>';
    var aviso = div('pk-aviso', '<span>As animações estão <b>desligadas</b> porque este computador pede «menos movimento» <small class="pk-aviso-det">(no Windows: Configurações › Acessibilidade › Efeitos visuais › Efeitos de animação)</small>. </span><button type="button" data-b="anim-on">Ativar animações</button>');
    palco.insertBefore(aviso, cena);
    aviso.addEventListener('click', function (e) { e.stopPropagation(); if (e.target.closest('button')) alternarAnim(); });
    function alternarAnim() {
      if (window.Movimento) Movimento.definir(REDUZ); atualizaReduz(); palco.classList.toggle('mov', !REDUZ); rotulos();
    }
    function rotulos() {
      barra.querySelector('[data-b=som]').textContent = (window.Som && Som.nivel() === 2) ? '🔉 Som baixo' : (window.Som && Som.ligado()) ? '🔊 Som ligado' : '🔇 Som desligado';
      barra.querySelector('[data-b=auto]').textContent = auto ? '⏸ Automático: ligado' : '▶ Automático: desligado';
      barra.querySelector('[data-b=anim]').textContent = REDUZ ? '✨ Animações: desligadas' : '✨ Animações: ligadas'; barra.querySelector('[data-b=anim]').classList.toggle('on', !REDUZ);
      aviso.hidden = !(REDUZ && window.Movimento && Movimento.sistema() && Movimento.forcado() == null);
      barra.querySelector('[data-b=auto]').classList.toggle('on', auto); barra.querySelector('[data-b=som]').classList.toggle('on', !!(window.Som && Som.ligado()));
    }
    function alternarSom() { if (window.Som) Som.ciclar(); rotulos(); }   // desligado → ligado → baixo
    function agendar(ms) { clearTimeout(timer); if (auto && fase !== 'fim') timer = setTimeout(function () { passo(); }, REDUZ ? 400 : ms); }
    function alternarAuto() { auto = !auto; rotulos(); clearTimeout(timer); if (auto && !ocupado) agendar(900); }
    barra.addEventListener('click', function (e) { e.stopPropagation(); var b = e.target.closest('button[data-b]'); if (!b) return; if (b.dataset.b === 'som') alternarSom(); else if (b.dataset.b === 'auto') alternarAuto(); else if (b.dataset.b === 'prox') passo(); else if (b.dataset.b === 'anim' || b.dataset.b === 'anim-on') alternarAnim(); });
    barra.addEventListener('change', function (e) { if (e.target.dataset.b === 'pular') pularAte = parseInt(e.target.value, 10) || 0; });
    rotulos();

    // ---- efeitos ----
    function flash(cor, op) { var f = div('pk-flash'); f.style.background = cor || '#fff'; palco.appendChild(f); return anima(f, [{ opacity: 0 }, { opacity: op || 0.85, offset: 0.25 }, { opacity: 0 }], 700, null, null).then(function () { f.remove(); }); }
    function onda(ancora, cor, atraso) {
      if (REDUZ) return; var o = div('pk-onda'); o.style.borderColor = cor; ancora.appendChild(o);
      anima(o, [{ transform: 'translate(-50%,-50%) scale(.2)', opacity: 0.95 }, { transform: 'translate(-50%,-50%) scale(5.2)', opacity: 0 }], 1100, { delay: atraso || 0, easing: 'cubic-bezier(.1,.7,.3,1)' }).then(function () { o.remove(); });
    }
    function chuva(ancora, cores, n, dist) {
      if (REDUZ) return; var w = div('c-particulas'); ancora.appendChild(w);
      for (var i = 0; i < n; i++) {
        var p = document.createElement('i'), a = Math.random() * 6.2832, d = dist * (0.45 + Math.random() * 0.75);
        p.style.background = cores[i % cores.length]; w.appendChild(p);
        anima(p, [{ transform: 'translate(0,0) scale(1.1)', opacity: 1 }, { transform: 'translate(' + Math.cos(a) * d + 'px,' + Math.sin(a) * d + 'px) scale(.2) rotate(' + (Math.random() * 600) + 'deg)', opacity: 0 }], 900 + Math.random() * 900, { easing: 'cubic-bezier(.1,.7,.3,1)' }, null);
      }
      setTimeout(function () { w.remove(); }, 2200);
    }
    function treme(forca) {
      if (REDUZ || !palco.animate) return; var k = []; for (var i = 0; i < 9; i++) k.push({ transform: 'translate(' + ((Math.random() - 0.5) * forca) + 'px,' + ((Math.random() - 0.5) * forca) + 'px)' }); k.push({ transform: 'none' });
      palco.animate(k, { duration: 520, easing: 'ease-out' });
    }
    function relampagos(n, cor) { if (window.CartaFX && CartaFX.raios) CartaFX.raios(palco, n, cor); }

    // ---- 1) abrir: o pacote treme, o topo é rasgado, a luz sai e as cartas voam girando até a fileira ----
    async function abrir() {
      ocupado = true; texto('', ''); legenda('Abrindo o pacote: ' + N + ' cartinhas saem voando.');
      var topo = pacote.querySelector('.pk-topo'), corpo = pacote.querySelector('.pk-corpo'), fenda = pacote.querySelector('.pk-fenda');
      await anima(pacote, [{ transform: 'rotate(0)' }, { transform: 'rotate(-3deg) scale(1.01)' }, { transform: 'rotate(3deg) scale(1.02)' }, { transform: 'rotate(-4deg) scale(1.03)' }, { transform: 'rotate(4deg) scale(1.04)' }, { transform: 'rotate(0) scale(1.05)' }], 900, { easing: 'ease-in-out' }, { transform: 'scale(1.05)' });
      var pc = centro(pacote, palco); fenda.style.opacity = '1';
      flash('#FFF6D0', 0.9); treme(18); if (window.Som) Som.tocar('rasgar');
      var rasga = anima(topo, [{ transform: 'none', opacity: 1 }, { transform: 'translate(10%,-22%) rotate(16deg)', opacity: 1, offset: 0.45 }, { transform: 'translate(46%,-120%) rotate(52deg)', opacity: 0 }], 900, { easing: 'cubic-bezier(.3,.1,.5,1)' }, { opacity: '0' });
      chuva(pacote, NIVEL[1], 46, ph * 0.9);
      await esp(250);
      // as cartas saem do rasgo girando (cada uma com um pequeno atraso) e pousam na fileira
      if (window.Som) Som.tocar('giro', 1500);
      var voos = slots.map(function (sl, i) {
        var c = centro(sl.g, palco), dx = pc.x - c.x, dy = pc.y - ph * 0.28 - c.y;
        return anima(sl.g, [
          { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + (pw * 0.6 / c.w) + ') rotateY(0deg)', opacity: 0 },
          { transform: 'translate(' + dx * 0.55 + 'px,' + (dy * 0.55 - H * 0.28) + 'px) scale(' + (pw * 0.55 / c.w) + ') rotateY(540deg)', opacity: 1, offset: 0.35 },
          { transform: 'translate(' + dx * 0.15 + 'px,' + (dy * 0.15 - 30) + 'px) scale(1.2) rotateY(900deg)', opacity: 1, offset: 0.78 },
          { transform: 'translate(0,0) scale(1) rotateY(1080deg)', opacity: 1 }], 1500, { delay: i * Math.min(110, 1400 / N), easing: 'cubic-bezier(.25,.8,.3,1)' }, { opacity: '1', transform: 'none' });
      });
      anima(corpo, [{ transform: 'none', opacity: 1 }, { transform: 'translateY(26%) scale(.96)', opacity: 0 }], 900, { delay: 500, easing: 'ease-in' }, { opacity: '0' });
      anima(raios, [{ opacity: 0 }, { opacity: 0.8 }], 800, { delay: 200 }, { opacity: '0.8' });
      await Promise.all(voos); pacote.style.display = 'none';
      anima(raios, [{ opacity: 0.8 }, { opacity: 0 }], 700, null, { opacity: '0' });
      fase = 'pronto'; ocupado = false; atual = -1; agendar(1500);
      texto('Enter / clique: revelar a próxima · R: recomeçar', 'Revelando de trás pra frente: ' + N + ' cartinhas'); legenda('Pacote aberto. Vamos revelar do ' + N + 'º ao 1º lugar.');
    }

    // ---- 2) revelar uma: ela sai da fileira, gira até o centro, vira e aparece com efeitos proporcionais à posição ----
    var foco = null, tempestade = null;
    async function revelar() {
      ocupado = true; atual++;
      var idx = ordem[atual], it = itens[idx], sl = slots[idx], rk = it.rank, top = rk <= 3 ? rk : 0, cores = NIVEL[top];
      texto('', 'Revelando ' + (atual + 1) + ' de ' + N + ' · faltam ' + (N - atual - 1));
      palco.setAttribute('data-nv', top ? 'r' + top : 'n');
      foco = div('pk-foco'); var gr = div('pk-grande'), linha = div('pk-linha');
      var info = div('pk-info', '<div class="pk-rank">' + rk + 'º</div><div class="pk-nome">' + esc(it.rot) + '</div><div class="pk-eq">' + esc(it.eq || '') + '</div><div class="pk-nota"><b>' + esc(it.nota) + '</b><span>nota do mês</span></div>' + (it.emp ? '<div class="pk-emp">⚖ ' + esc(it.emp) + '</div>' : '') + (cfg.video ? '<button type="button" class="pk-video">🎬 Vídeo de 5 s para o WhatsApp</button><div class="pk-vst" role="status" aria-live="polite"></div>' : ''));
      var bv = info.querySelector('.pk-video');
      if (bv) bv.addEventListener('click', function (e) { e.stopPropagation(); var st = info.querySelector('.pk-vst'); bv.disabled = true; st.textContent = 'Gerando o vídeo (5 s)…'; Promise.resolve(cfg.video(it)).then(function (m) { st.textContent = m || ''; }, function () { st.textContent = 'Não consegui gerar o vídeo neste navegador.'; }).then(function () { bv.disabled = false; }); });
      if (top) { var fx = div('pk-faixa r' + top, '<i>' + FAIXA[top][0] + '</i>' + FAIXA[top][1]); foco.appendChild(fx); fx.style.opacity = '0'; foco._fx = fx; }
      linha.appendChild(gr); linha.appendChild(info); foco.appendChild(linha); cena.appendChild(foco);
      gr.style.opacity = '0'; info.style.opacity = '0';
      // tamanhos tirados do espaço que sobrou de verdade (resolução, janela, fileira): carta e texto cabem sempre, sem passar dos controles
      var cw = cena.clientWidth, ch = cena.clientHeight, fh = foco._fx ? (Math.min(cw / 20, ch * 0.09, 54) | 0) : 0;
      if (foco._fx) { foco._fx.style.fontSize = Math.max(15, fh) + 'px'; }
      var lw = linha.clientWidth, lh = linha.clientHeight, estreito = lw < 640 || lw < lh * 0.95, extra = top === 1 ? 70 : 0;
      var eb = estreito ? Math.min(((lh * 0.6) - extra) / 392, (lw * 0.78) / 272, 1.3) : Math.min((lh * 0.96 - extra) / 392, (lw * 0.42) / 272, 1.75);
      eb = Math.max(0.3, eb); gr.style.setProperty('--e', eb.toFixed(3));
      foco.classList.toggle('estreito', estreito);
      info.style.fontSize = Math.max(11, Math.min(estreito ? lh * 0.4 / (it.emp ? 17 : 12) : lh / (it.emp ? 25 : 17), (estreito ? lw : lw - 272 * eb - 40) / 15, 26)).toFixed(1) + 'px';
      function cabe() { return info.scrollHeight <= lh + 1 && info.getBoundingClientRect().bottom <= linha.getBoundingClientRect().bottom + 1; }
      for (var fz = parseFloat(info.style.fontSize), g = 0; g < 14 && fz > 9 && !cabe(); g++) { fz -= 1; info.style.fontSize = fz + 'px'; }   // encolhe até caber na altura da cena
      var pe = info.querySelector('.pk-emp'); if (pe && !cabe()) pe.style.display = 'none';   // cena muito baixa: o desempate fica só na legenda
      // voo: o verso sai do lugar da fileira e vai para o centro, girando; no 1º/2º/3º há suspense antes de virar
      var voo = div('pk-voo', VERSO); voo.style.cssText = 'width:' + (272 * eb) + 'px;height:' + (392 * eb) + 'px;--e:' + eb;
      palco.appendChild(voo);
      var a = centro(gr, palco), b = centro(sl.g, palco), k = b.w / (272 * eb);
      voo.style.left = (a.x - 136 * eb) + 'px'; voo.style.top = (a.y - 196 * eb) + 'px';
      sl.g.style.opacity = '0.12'; if (window.Som) Som.tocar('giro', top ? 1300 : 900);
      var dx = b.x - a.x, dy = b.y - a.y;
      await anima(voo, [{ transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + k + ') rotateY(0deg)' }, { transform: 'translate(' + dx * 0.4 + 'px,' + (dy * 0.4 - 90) + 'px) scale(' + (k + (1 - k) * 0.6) + ') rotateY(540deg)', offset: 0.55 }, { transform: 'translate(0,0) scale(1) rotateY(1080deg)' }], top ? 1300 : 900, { easing: 'cubic-bezier(.3,.7,.3,1)' }, { transform: 'none' });
      if (top) {
        var gl = '0 0 ' + (40 + top * 10) + 'px ' + cores[0]; if (window.Som) Som.tocar('suspense', top === 1 ? 2600 : 1200 + (4 - top) * 300);
        if (top === 1) {   // suspense maior: holofote dourado, escuro, e o «coração» batendo com a tela tremendo
          palco.classList.add('escuro'); var hf = div('pk-holofote'); hf.style.left = (centro(gr, cena).x - 150 * eb) + 'px'; hf.style.width = (300 * eb) + 'px'; cena.appendChild(hf); anima(hf, [{ opacity: 0 }, { opacity: 1 }], 900, null, { opacity: '1' });
          [350, 950, 1550, 2050].forEach(function (ms) { setTimeout(function () { treme(10); if (window.Som) Som.tocar('batida'); }, ms); });
        }
        await anima(voo, [{ transform: 'translate(0,0) scale(1)', filter: 'brightness(1)' }, { transform: 'translate(-10px,0) scale(1.03)', filter: 'brightness(1.3)' }, { transform: 'translate(10px,0) scale(1.06)', filter: 'brightness(1.6)' }, { transform: 'translate(-12px,0) scale(1.08)', filter: 'brightness(2)' }, { transform: 'translate(0,0) scale(1.1)', filter: 'brightness(2.6)' }], top === 1 ? 2700 : 1200 + (4 - top) * 300, { easing: 'ease-in' }, null);
        voo.style.boxShadow = gl;
        if (top === 1) await esp(300);
      }
      await anima(voo, [{ transform: 'rotateY(0)' }, { transform: 'rotateY(90deg)' }], 160, { easing: 'ease-in' }, null);
      voo.remove();
      // a cartinha de verdade aparece (mesma conta da cartinha, o mesmo desenho) com clarão, ondas e partículas
      gr.innerHTML = it.mk(); var carta = gr.querySelector('.carta'), nb = gr.querySelector('.c-ovr b');
      if (carta) carta.setAttribute('data-visto', '1'); if (nb) nb.setAttribute('data-contou', '1');
      if (it.prep) it.prep(gr, it);
      gr.style.opacity = '1';
      if (window.Som) { Som.tocar(top ? ['', 'ouro', 'prata', 'bronze'][top] : 'ding'); if (top) Som.tocar('trovao'); if (top === 1) { setTimeout(function () { Som.tocar('trovao'); }, 450); setTimeout(function () { Som.tocar('fanfarra'); }, 900); } }
      flash(top === 1 ? '#FFFFFF' : top === 2 ? '#DDEBFF' : top === 3 ? '#FFD9B0' : '#FFFFFF', top ? 1 : 0.55);
      if (top === 1) setTimeout(function () { flash('#FFD25A', 0.85); }, 170);
      if (top) treme(top === 1 ? 70 : top === 2 ? 22 : 14);
      var n0 = top ? [0, 3, 3, 2][4 - top] : 1;
      onda(gr, cores[0], 0); if (top) { onda(gr, cores[1], 160); onda(gr, cores[0], 320); }
      if (top === 1) { onda(gr, cores[3], 480); onda(gr, '#fff', 640); for (var oi = 0; oi < 5; oi++) onda(gr, oi % 2 ? '#fff' : cores[0], 800 + oi * 220); }
      chuva(gr, cores, top === 1 ? 190 : top === 2 ? 64 : top === 3 ? 48 : 26, top === 1 ? 380 : top ? 260 + (4 - top) * 40 : 190);
      if (top === 1) {   // coroa que cai do alto e quica no topo da carta + tempestade que continua enquanto ela está na tela
        var co = div('pk-coroa', '👑'); co.style.fontSize = (88 * eb) + 'px'; gr.appendChild(co);
        anima(co, [{ transform: 'translate(-50%,-420px) scale(2.4) rotate(-25deg)', opacity: 0 }, { transform: 'translate(-50%,0) scale(1.1) rotate(4deg)', opacity: 1, offset: 0.55 }, { transform: 'translate(-50%,-26px) scale(1) rotate(-3deg)', offset: 0.75 }, { transform: 'translate(-50%,0) scale(1) rotate(0)' }], 1100, { delay: 250, easing: 'cubic-bezier(.3,.7,.4,1)' }, { opacity: '1', transform: 'translate(-50%,0)' });
        var cc = centro(gr, palco); if (window.CartaFX && CartaFX.raios) CartaFX.raios(palco, 4, '#FFFFFF', { x: cc.x, y: cc.y - 40 * eb, n: 4 });
        tempestade = setInterval(function () { relampagos(3, '#FFE08A'); if (window.Som) Som.tocar('trovao'); }, 3000);
      }
      if (top) { palco.classList.add('destaque'); relampagos(top === 1 ? 14 : top === 2 ? 6 : 4, top === 1 ? '#FFE08A' : top === 2 ? '#BFE0FF' : '#FFB070'); }
      var vira = anima(gr, [{ transform: 'perspective(1000px) rotateY(-90deg) scale(.9)', filter: 'brightness(2.8)' }, { transform: 'perspective(1000px) rotateY(0) scale(1.06)', filter: 'brightness(1.7)', offset: 0.6 }, { transform: 'perspective(1000px) rotateY(0) scale(1)', filter: 'brightness(1)' }], 700, { easing: 'cubic-bezier(.2,.9,.3,1)' }, null);
      await esp(250);
      anima(info, [{ opacity: 0, transform: 'translateX(40px)' }, { opacity: 1, transform: 'none' }], 520, null, { opacity: '1' });
      if (foco._fx) anima(foco._fx, [{ opacity: 0, transform: 'scale(2.6)' }, { opacity: 1, transform: 'scale(1)', offset: 0.55 }, { opacity: 1, transform: 'scale(1.06)' }, { opacity: 1, transform: 'scale(1)' }], 900, { easing: 'cubic-bezier(.2,.9,.3,1.2)' }, { opacity: '1' });
      await vira;
      fase = atual >= N - 1 ? 'ultima' : 'revelada'; ocupado = false;
      legenda(rk + 'º lugar revelado: ' + it.rot + ', ' + (it.eq || 'sem equipe') + ', nota ' + it.nota + '. ' + (it.emp || ''));
      texto(atual >= N - 1 ? 'Enter / clique: guardar e encerrar' : 'Enter / clique: próxima cartinha · R: recomeçar', 'Revelando ' + (atual + 1) + ' de ' + N);
      agendar(top ? 7000 : 3200);
    }

    // ---- 3) guardar: a carta grande volta para o lugar na fileira e vira de frente (fica à mostra) ----
    async function guardar() {
      ocupado = true; clearInterval(tempestade); var idx = ordem[atual], it = itens[idx], sl = slots[idx], gr = foco.querySelector('.pk-grande');
      var a = centro(gr, palco), b = centro(sl.g, palco), k = b.w / a.w;
      palco.classList.remove('destaque', 'escuro'); palco.setAttribute('data-nv', 'n');
      anima(foco.querySelector('.pk-info'), [{ opacity: 1 }, { opacity: 0 }], 300, null, { opacity: '0' });
      if (foco._fx) anima(foco._fx, [{ opacity: 1 }, { opacity: 0 }], 300, null, { opacity: '0' });
      await anima(gr, [{ transform: 'none', opacity: 1 }, { transform: 'translate(' + (b.x - a.x) + 'px,' + (b.y - a.y) + 'px) scale(' + k + ')', opacity: 0.2 }], 560, { easing: 'cubic-bezier(.5,0,.3,1)' }, null);
      foco.remove(); foco = null;
      var face = sl.g.querySelector('.pk-b'); face.className = 'pk-f pk-b pk-mini'; face.innerHTML = it.mk();
      var c = face.querySelector('.carta'), nb = face.querySelector('.c-ovr b'); if (c) c.setAttribute('data-visto', '1'); if (nb) nb.setAttribute('data-contou', '1');
      if (it.prep) it.prep(face, it);
      sl.g.style.opacity = '1';
      await anima(sl.g, [{ transform: 'rotateY(0)' }, { transform: 'rotateY(180deg)' }], 650, { easing: 'cubic-bezier(.3,.8,.3,1)' }, { transform: 'rotateY(180deg)' });
      sl.s.classList.add('aberta');
    }

    /* ---- 4) fechamento do mês: pódio (1º, 2º, 3º), números do mês e quem mais tirou 100. É a tela que serve de foto para o grupo ---- */
    async function fim() {
      ocupado = true; fase = 'fim'; palco.setAttribute('data-nv', 'n');
      var f = cfg.fechamento || {}, mesTxt = f.mes || cfg.mes || '';
      flash('#FFF2B8', 0.5); relampagos(8, '#FFE08A'); if (window.Som) { Som.tocar('fanfarra'); Som.tocar('trovao'); }
      Array.prototype.forEach.call(palco.querySelectorAll('.pk-holofote'), function (h) { h.remove(); });
      fileira.style.display = 'none';   // a cena ganha o espaço da fileira
      var tela = div('pk-final'), tit = div('pk-fim pk-f-tit', 'Parabéns ao top ' + N + (mesTxt ? ' de ' + esc(mesTxt) : ' do mês') + '! 🎉'), pod = div('pk-pod'), nums = div('pk-nums'), outros = div('pk-outros'), bts = div('pk-f-bt');
      var por = {}; itens.forEach(function (it) { por[it.rank] = it; });
      [2, 1, 3].forEach(function (r) {
        var it = por[r]; if (!it) return;
        var col = div('pk-pcol r' + r), cartaBox = div('pk-grande pk-pcard'), ped = div('pk-ped', '<b>' + r + 'º</b><span class="pk-pn">' + esc(it.rot) + '</span><span class="pk-pt">' + esc(it.nota) + ' · ' + esc(it.eq || '') + '</span>');
        cartaBox.innerHTML = it.mk(); var c = cartaBox.querySelector('.carta'), nb = cartaBox.querySelector('.c-ovr b'); if (c) c.setAttribute('data-visto', '1'); if (nb) nb.setAttribute('data-contou', '1'); if (it.prep) it.prep(cartaBox, it);
        col.appendChild(cartaBox); col.appendChild(ped); pod.appendChild(col);
      });
      function chip(rot, valor, sub) { return '<div class="pk-chip"><span>' + esc(rot) + '</span><b>' + esc(valor) + '</b>' + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</div>'; }
      nums.innerHTML = (f.media ? chip('Nota média do mês', f.media, f.total ? 'de ' + f.total + ' agentes' : '') : '') + (f.n100 != null ? chip('Tiraram 100', String(f.n100), f.total ? 'de ' + f.total + ' agentes' : '') : '') + (f.mediaTop ? chip('Média do top ' + N, f.mediaTop, 'os mais bem colocados') : '');
      if (f.outros) outros.innerHTML = '<b>Também tiraram 100:</b> ' + esc(f.outros); else outros.hidden = true;
      if (cfg.videoTop) {
        var bv = document.createElement('button'); bv.type = 'button'; bv.className = 'pk-video'; bv.textContent = '🎬 Vídeo do top ' + N + ' (15 s) para o WhatsApp'; var st = div('pk-vst'); st.setAttribute('role', 'status'); st.setAttribute('aria-live', 'polite');
        bv.addEventListener('click', function (e) { e.stopPropagation(); bv.disabled = true; st.textContent = 'Gerando o vídeo (≈15 s)…'; Promise.resolve(cfg.videoTop()).then(function (m) { st.textContent = m || ''; }, function () { st.textContent = 'Não consegui gerar o vídeo neste navegador.'; }).then(function () { bv.disabled = false; }); });
        bts.appendChild(bv); bts.appendChild(st);
      }
      if (f.resumoUrl) { var rs = document.createElement('a'); rs.className = 'pk-video'; rs.href = f.resumoUrl; rs.target = '_blank'; rs.rel = 'noopener'; rs.textContent = '📄 Resumo do mês (PDF para a ata)'; rs.addEventListener('click', function (e) { e.stopPropagation(); }); bts.insertBefore(rs, bts.firstChild); }
      tela.appendChild(tit); tela.appendChild(pod); tela.appendChild(nums); tela.appendChild(outros); tela.appendChild(bts); cena.appendChild(tela);
      // tamanhos: a carta do pódio cabe no que sobrou (largura de 3 colunas e altura da área do pódio)
      var cw = tela.clientWidth, fz = Math.max(11, Math.min(cw / 62, cena.clientHeight / 30, 21)); tela.style.fontSize = fz.toFixed(1) + 'px';
      var ph = pod.clientHeight, ped1 = 6 * fz, e = Math.max(0.25, Math.min((ph - ped1 - 10) / 392, (cw / 3 - 14) / 272, 1.15));
      pod.style.setProperty('--e', e.toFixed(3)); pod.style.setProperty('--ped1', ped1.toFixed(0) + 'px');
      if (!REDUZ) { anima(tit, [{ opacity: 0, transform: 'translateY(-24px) scale(.85)' }, { opacity: 1, transform: 'none' }], 700, null, { opacity: '1' }); Array.prototype.forEach.call(pod.children, function (c, i) { anima(c, [{ opacity: 0, transform: 'translateY(60px) scale(.8)' }, { opacity: 1, transform: 'none' }], 800, { delay: 250 + i * 220, easing: 'cubic-bezier(.2,.9,.3,1)' }, { opacity: '1' }); }); }
      legenda('Fechamento de ' + mesTxt + ': ' + [1, 2, 3].filter(function (r) { return por[r]; }).map(function (r) { return r + 'º ' + por[r].rot + ', nota ' + por[r].nota; }).join('; ') + (f.media ? '. Nota média do mês: ' + f.media : '') + (f.n100 != null ? '. Tiraram 100: ' + f.n100 : '') + '.');
      texto('R: ver de novo', 'Fechamento do mês'); ocupado = false;
    }

    function mostrarFace(sl, it) {   // abre a cartinha na fileira sem animação (usado em «Pular até o Nº»)
      var face = sl.g.querySelector('.pk-b'); face.className = 'pk-f pk-b pk-mini'; face.innerHTML = it.mk();
      var c = face.querySelector('.carta'), nb = face.querySelector('.c-ovr b'); if (c) c.setAttribute('data-visto', '1'); if (nb) nb.setAttribute('data-contou', '1');
      if (it.prep) it.prep(face, it); sl.g.style.opacity = '1'; sl.g.style.transform = 'rotateY(180deg)'; sl.s.classList.add('aberta');
    }
    function pularInicio() {
      if (!pularAte || atual !== -1) return;
      var k = 0; ordem.forEach(function (idx) { if (itens[idx].rank > pularAte) { mostrarFace(slots[idx], itens[idx]); k++; } });
      if (k < N) atual = k - 1;
    }
    async function passo() {
      if (window.Som) Som.preparar();
      clearTimeout(timer);
      if (ocupado) return;
      if (fase === 'fechado') return abrir();
      if (fase === 'pronto') { pularInicio(); return revelar(); }
      if (fase === 'revelada') { await guardar(); return revelar(); }
      if (fase === 'ultima') { await guardar(); return fim(); }
    }
    palco.addEventListener('click', function () { passo(); });
    return { passo: passo, alternarAnim: alternarAnim, alternarSom: alternarSom, alternarAuto: alternarAuto, auto: function () { return auto; }, fase: function () { return fase; }, ocupado: function () { return ocupado; }, total: N };
  }
  window.Pacote = { iniciar: iniciar };
})();
