/* Abertura de pacote (tela de reunião, tecla P): um pacote fechado que se rasga no topo, solta as cartinhas dos agentes que tiraram 100
   girando, e depois revela uma a uma, DE TRÁS PRA FRENTE, até o 3º, o 2º e o 1º lugar, cada vez com mais efeito.
   Genérico: quem chama (projecao.js) entrega os itens já na ordem do ranking (melhor primeiro):
     { rank, rot, eq, nota, mk: () => html da cartinha, prep: (raiz) => ajustes (ex.: ocultar nome) }
   Entrada: Pacote.iniciar(el, itens, { mes }) → { passo(), fase(), ocupado() }.  Sem nada disso quando o sistema pede menos movimento (sem animação, só o resultado). */
(function () {
  'use strict';
  var REDUZ = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var NIVEL = { 1: ['#FFD25A', '#FFF6C8', '#F0B020', '#FF9A1F'], 2: ['#E6EEF9', '#9FB6D6', '#FFFFFF', '#6CC4F2'], 3: ['#E8A060', '#FFD0A0', '#B8662A', '#FFE9CF'], 0: ['#FFD25A', '#FFF3B0', '#6CC4F2'] };
  var FAIXA = { 1: ['🥇', 'CAMPEÃO · 1º LUGAR'], 2: ['🥈', '2º LUGAR'], 3: ['🥉', '3º LUGAR'] };

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
    var N = itens.length, palco = div('pk-palco'), fase = 'fechado', ocupado = false, atual = -1, folga = 0;
    var ordem = itens.map(function (_, i) { return i; }).reverse();   // revela do último para o primeiro
    el.appendChild(palco);
    var W = palco.clientWidth || 1000, H = palco.clientHeight || 600;

    // ---- fileira de cartinhas (de costas) embaixo; linhas conforme a quantidade ----
    var linhas = N <= 9 ? 1 : N <= 20 ? 2 : 3, porLinha = Math.ceil(N / linhas);
    var eLin = Math.max(0.12, Math.min(0.32, ((H * 0.3) / linhas - 12) / 392, (W * 0.94 / porLinha - 10) / 272));
    var fileira = div('pk-fileira'); fileira.style.setProperty('--e', eLin.toFixed(3)); fileira.style.width = Math.min(W * 0.96, porLinha * (272 * eLin + 8) + 4) + 'px'; fileira.style.left = '50%'; fileira.style.right = 'auto'; fileira.style.transform = 'translateX(-50%)';
    var slots = itens.map(function (it, i) {
      var s = div('pk-slot'), g = div('pk-giro', '<div class="pk-f pk-a">' + VERSO + '</div><div class="pk-f pk-b">' + VERSO + '</div>');
      s.appendChild(g); s.setAttribute('data-pos', String(i)); fileira.appendChild(s); g.style.opacity = '0'; return { s: s, g: g };
    });
    var pw0, ph = Math.min(H * 0.66, W * 0.46 * 1.55), pw = ph * 0.62; pw0 = pw;
    var pacote = div('pk-pacote'); pacote.style.cssText = 'width:' + pw + 'px;height:' + ph + 'px;margin:' + (-ph / 2) + 'px 0 0 ' + (-pw / 2) + 'px;font-size:' + (pw / 11) + 'px';
    var arte = '<div class="pk-arte"><i class="pk-crimpe"></i><div class="pk-logo">SENTINELA</div><div class="pk-sub">CARTINHAS</div><div class="pk-mes">' + esc(cfg.mes || '') + '</div><div class="pk-num"><b>' + N + '</b><span>cartas 100</span></div><i class="pk-crimpe b"></i><i class="pk-holo"></i></div>';
    var yR = 14;
    pacote.innerHTML = '<div class="pk-corpo" style="clip-path:' + poli(zig(yR).concat([['100%', '100%'], ['0%', '100%']])) + '">' + arte + '</div>' +
      '<div class="pk-topo" style="clip-path:' + poli([['0%', '0%'], ['100%', '0%']].concat(zig(yR, true))) + '">' + arte + '</div><i class="pk-fenda" style="top:' + yR + '%"></i>';
    var dica = div('pk-dica', ''), contador = div('pk-cont', '');
    var raios = div('pk-raios'), fundo = div('pk-fundo');
    palco.appendChild(fundo); palco.appendChild(raios); palco.appendChild(pacote); palco.appendChild(fileira); palco.appendChild(dica); palco.appendChild(contador);
    function texto(d, c) { dica.textContent = d; contador.textContent = c || ''; }
    texto('Clique ou tecle Enter para abrir o pacote', N + ' cartinhas com nota 100');
    folga = fileira.offsetHeight + 34;

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
    function confete(n) { if (window.CartaFX && CartaFX.confete) CartaFX.confete(palco, n); }

    // ---- 1) abrir: o pacote treme, o topo é rasgado, a luz sai e as cartas voam girando até a fileira ----
    async function abrir() {
      ocupado = true; texto('', '');
      var topo = pacote.querySelector('.pk-topo'), corpo = pacote.querySelector('.pk-corpo'), fenda = pacote.querySelector('.pk-fenda');
      await anima(pacote, [{ transform: 'rotate(0)' }, { transform: 'rotate(-3deg) scale(1.01)' }, { transform: 'rotate(3deg) scale(1.02)' }, { transform: 'rotate(-4deg) scale(1.03)' }, { transform: 'rotate(4deg) scale(1.04)' }, { transform: 'rotate(0) scale(1.05)' }], 900, { easing: 'ease-in-out' }, { transform: 'scale(1.05)' });
      var pc = centro(pacote, palco); fenda.style.opacity = '1';
      flash('#FFF6D0', 0.9); treme(18);
      var rasga = anima(topo, [{ transform: 'none', opacity: 1 }, { transform: 'translate(10%,-22%) rotate(16deg)', opacity: 1, offset: 0.45 }, { transform: 'translate(46%,-120%) rotate(52deg)', opacity: 0 }], 900, { easing: 'cubic-bezier(.3,.1,.5,1)' }, { opacity: '0' });
      chuva(pacote, NIVEL[1], 46, ph * 0.9);
      await esp(250);
      // as cartas saem do rasgo girando (cada uma com um pequeno atraso) e pousam na fileira
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
      fase = 'pronto'; ocupado = false; atual = -1;
      texto('Enter / clique: revelar a próxima · R: recomeçar', 'Revelando de trás pra frente: ' + N + ' cartinhas');
    }

    // ---- 2) revelar uma: ela sai da fileira, gira até o centro, vira e aparece com efeitos proporcionais à posição ----
    var foco = null;
    function eBig() { return Math.max(0.5, Math.min(1.75, ((H - folga - 70) * 0.94) / 392, (W * 0.4) / 272)); }
    async function revelar() {
      ocupado = true; atual++;
      var idx = ordem[atual], it = itens[idx], sl = slots[idx], rk = it.rank, top = rk <= 3 ? rk : 0, cores = NIVEL[top];
      texto('', 'Revelando ' + (atual + 1) + ' de ' + N + ' · faltam ' + (N - atual - 1));
      palco.setAttribute('data-nv', top ? 'r' + top : 'n');
      var eb = eBig();
      foco = div('pk-foco'); foco.style.paddingBottom = folga + 'px'; foco.style.paddingTop = (top ? 70 : 36) + 'px';
      var gr = div('pk-grande'); gr.style.setProperty('--e', eb.toFixed(3));
      var info = div('pk-info', '<div class="pk-rank">' + rk + 'º</div><div class="pk-nome">' + esc(it.rot) + '</div><div class="pk-eq">' + esc(it.eq || '') + '</div><div class="pk-nota"><b>' + esc(it.nota) + '</b><span>nota do mês</span></div>');
      foco.appendChild(gr); foco.appendChild(info); palco.appendChild(foco);
      gr.style.opacity = '0'; info.style.opacity = '0';
      if (top) { var fx = div('pk-faixa r' + top, '<i>' + FAIXA[top][0] + '</i>' + FAIXA[top][1]); foco.appendChild(fx); fx.style.opacity = '0'; foco._fx = fx; }
      // voo: o verso sai do lugar da fileira e vai para o centro, girando; no 1º/2º/3º há suspense antes de virar
      var voo = div('pk-voo', VERSO); voo.style.cssText = 'width:' + (272 * eb) + 'px;height:' + (392 * eb) + 'px;--e:' + eb;
      palco.appendChild(voo);
      var a = centro(gr, palco), b = centro(sl.g, palco), k = b.w / (272 * eb);
      voo.style.left = (a.x - 136 * eb) + 'px'; voo.style.top = (a.y - 196 * eb) + 'px';
      sl.g.style.opacity = '0.12';
      var dx = b.x - a.x, dy = b.y - a.y;
      await anima(voo, [{ transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + k + ') rotateY(0deg)' }, { transform: 'translate(' + dx * 0.4 + 'px,' + (dy * 0.4 - 90) + 'px) scale(' + (k + (1 - k) * 0.6) + ') rotateY(540deg)', offset: 0.55 }, { transform: 'translate(0,0) scale(1) rotateY(1080deg)' }], top ? 1300 : 900, { easing: 'cubic-bezier(.3,.7,.3,1)' }, { transform: 'none' });
      if (top) {
        var gl = '0 0 ' + (40 + top * 10) + 'px ' + cores[0];
        await anima(voo, [{ transform: 'translate(0,0) scale(1)', filter: 'brightness(1)' }, { transform: 'translate(-10px,0) scale(1.03)', filter: 'brightness(1.3)' }, { transform: 'translate(10px,0) scale(1.06)', filter: 'brightness(1.6)' }, { transform: 'translate(-12px,0) scale(1.08)', filter: 'brightness(2)' }, { transform: 'translate(0,0) scale(1.1)', filter: 'brightness(2.6)' }], 1200 + (4 - top) * 300, { easing: 'ease-in' }, null);
        voo.style.boxShadow = gl;
        if (top === 1) { palco.classList.add('escuro'); await esp(350); }
      }
      await anima(voo, [{ transform: 'rotateY(0)' }, { transform: 'rotateY(90deg)' }], 160, { easing: 'ease-in' }, null);
      voo.remove();
      // a cartinha de verdade aparece (mesma conta da cartinha, o mesmo desenho) com clarão, ondas e partículas
      gr.innerHTML = it.mk(); var carta = gr.querySelector('.carta'), nb = gr.querySelector('.c-ovr b');
      if (carta) carta.setAttribute('data-visto', '1'); if (nb) nb.setAttribute('data-contou', '1');
      if (it.prep) it.prep(gr, it);
      gr.style.opacity = '1';
      flash(top === 1 ? '#FFF2B8' : top === 2 ? '#DDEBFF' : top === 3 ? '#FFD9B0' : '#FFFFFF', top ? 0.95 : 0.55);
      if (top) treme(top === 1 ? 34 : top === 2 ? 22 : 14);
      var n0 = top ? [0, 3, 3, 2][4 - top] : 1;
      onda(gr, cores[0], 0); if (top) { onda(gr, cores[1], 160); onda(gr, cores[0], 320); }
      if (top === 1) { onda(gr, cores[3], 480); onda(gr, '#fff', 640); }
      chuva(gr, cores, top === 1 ? 96 : top === 2 ? 64 : top === 3 ? 48 : 26, top ? 260 + (4 - top) * 40 : 190);
      if (top) { palco.classList.add('destaque'); confete(top === 1 ? 180 : top === 2 ? 110 : 70); }
      var vira = anima(gr, [{ transform: 'perspective(1000px) rotateY(-90deg) scale(.9)', filter: 'brightness(2.8)' }, { transform: 'perspective(1000px) rotateY(0) scale(1.06)', filter: 'brightness(1.7)', offset: 0.6 }, { transform: 'perspective(1000px) rotateY(0) scale(1)', filter: 'brightness(1)' }], 700, { easing: 'cubic-bezier(.2,.9,.3,1)' }, null);
      await esp(250);
      anima(info, [{ opacity: 0, transform: 'translateX(40px)' }, { opacity: 1, transform: 'none' }], 520, null, { opacity: '1' });
      if (foco._fx) anima(foco._fx, [{ opacity: 0, transform: 'translateX(-50%) scale(2.6)' }, { opacity: 1, transform: 'translateX(-50%) scale(1)', offset: 0.55 }, { opacity: 1, transform: 'translateX(-50%) scale(1.06)' }, { opacity: 1, transform: 'translateX(-50%) scale(1)' }], 900, { easing: 'cubic-bezier(.2,.9,.3,1.2)' }, { opacity: '1' });
      await vira;
      fase = atual >= N - 1 ? 'ultima' : 'revelada'; ocupado = false;
      texto(atual >= N - 1 ? 'Enter / clique: guardar e encerrar' : 'Enter / clique: próxima cartinha · R: recomeçar', 'Revelando ' + (atual + 1) + ' de ' + N);
    }

    // ---- 3) guardar: a carta grande volta para o lugar na fileira e vira de frente (fica à mostra) ----
    async function guardar() {
      ocupado = true; var idx = ordem[atual], it = itens[idx], sl = slots[idx], gr = foco.querySelector('.pk-grande');
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

    async function fim() {
      ocupado = true; fase = 'fim'; palco.setAttribute('data-nv', 'n');
      var t = div('pk-fim', 'Parabéns a todos que chegaram ao 100! 🎉'); palco.appendChild(t);
      anima(t, [{ opacity: 0, transform: 'translate(-50%,-30px) scale(.8)' }, { opacity: 1, transform: 'translate(-50%,0) scale(1)' }], 700, null, { opacity: '1' });
      flash('#FFF2B8', 0.5); confete(160); onda(t, NIVEL[1][0], 0);
      texto('R: ver de novo', N + ' cartinhas 100'); ocupado = false;
    }

    async function passo() {
      if (ocupado) return;
      if (fase === 'fechado') return abrir();
      if (fase === 'pronto') return revelar();
      if (fase === 'revelada') { await guardar(); return revelar(); }
      if (fase === 'ultima') { await guardar(); return fim(); }
    }
    palco.addEventListener('click', function () { passo(); });
    return { passo: passo, fase: function () { return fase; }, ocupado: function () { return ocupado; }, total: N };
  }
  window.Pacote = { iniciar: iniciar };
})();
