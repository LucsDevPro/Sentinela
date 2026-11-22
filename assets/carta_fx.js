/* Efeitos vivos das cartas — liga o que o carta.css (seção "EFEITOS VIVOS") desenha.
   - inclinação 3D e brilho que seguem o ponteiro (só mouse/caneta; no toque, um clarão ao tocar);
   - .vivo só nas cartas que estão na tela (as animações param fora dela: poupa CPU/bateria);
   - entrada em cascata (.entra) e a nota subindo, contando, na primeira vez que a carta aparece;
   - sem nada disso quando o sistema pede menos movimento (prefers-reduced-motion).
   Funciona sozinho: observa o DOM e liga as cartas que aparecerem depois (filtros do álbum, agente.html). */
(function () {
  'use strict';
  /* «Movimento»: o sistema pode pedir menos movimento (Windows: Efeitos de animação desligados; muito comum em área de trabalho remota
     e em computador de repartição). Na apresentação (pacote) a pessoa pode ligar as animações de propósito: fica guardado neste navegador. */
  var SIST = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches), PREF = 'sentinela:animacoes', forca = null;
  try { forca = localStorage.getItem(PREF); } catch (e) {}
  function reduz() { return forca === '1' ? false : forca === '0' ? true : SIST; }
  window.Movimento = {
    reduz: reduz, sistema: function () { return SIST; }, forcado: function () { return forca; },
    definir: function (v) { forca = v == null ? null : v ? '1' : '0'; try { if (forca == null) localStorage.removeItem(PREF); else localStorage.setItem(PREF, forca); } catch (e) {} document.documentElement.classList.toggle('mov-forcado', forca === '1'); }
  };
  if (forca === '1') document.documentElement.classList.add('mov-forcado');
  var MAX = 14;                 // inclinação máxima (graus)
  var io = null, fila = 0, filaT = 0, ativa = null, ultimo = null, raf = 0;

  function contar(carta) {
    var b = carta.querySelector('.c-ovr b');
    if (!b || b.getAttribute('data-contou')) return;
    b.setAttribute('data-contou', '1');
    var alvo = parseInt(b.textContent, 10);
    if (!isFinite(alvo) || alvo < 1) return;
    var atraso = parseFloat(carta.style.getPropertyValue('--atraso')) || 0, dur = 750, ini = null;
    b.textContent = '0';
    (function passo(t) {
      if (ini === null) ini = t + atraso;
      var p = Math.max(0, Math.min(1, (t - ini) / dur));
      b.textContent = String(Math.round(alvo * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(passo); else b.textContent = String(alvo);
    })(performance.now());
  }

  function aoVer(entradas) {
    entradas.forEach(function (en) {
      var c = en.target;
      if (!en.isIntersecting) { c.classList.remove('vivo'); return; }
      c.classList.add('vivo');
      if (c.getAttribute('data-visto')) return;
      c.setAttribute('data-visto', '1');
      if (reduz()) return;
      if (!c.style.getPropertyValue('--atraso')) {        // cartas que aparecem juntas entram uma após a outra
        c.style.setProperty('--atraso', Math.min(fila * 55, 700) + 'ms');
        fila++; clearTimeout(filaT); filaT = setTimeout(function () { fila = 0; }, 150);
      }
      c.classList.add('entra');
      contar(c);
    });
  }


  /* ---- esqueleto da foto: shimmer cinza até a imagem carregar ---- */
  function esqueleto(raiz) {
    Array.prototype.forEach.call((raiz || document).querySelectorAll('.c-foto.tem-foto:not([data-esq])'), function (f) {
      f.setAttribute('data-esq', '');
      var im = f.querySelector('img');
      if (!im || im.complete || reduz()) return;
      f.classList.add('carregando');
      var fim = function () { f.classList.remove('carregando'); };
      im.addEventListener('load', fim, { once: true }); im.addEventListener('error', fim, { once: true });
    });
  }

  /* ---- partículas (WAAPI: nada fica no DOM depois) ---- */
  var COR = { 'b-100': ['#FFD447', '#FFFBEA', '#D6A638'], 'b-90': ['#F2C94C', '#F8DE85'] };
  function particulas(ancora, borda, n) {
    var cores = COR[borda]; if (!cores || reduz() || !ancora.animate) return;
    var wrap = document.createElement('div'); wrap.className = 'c-particulas';
    for (var i = 0; i < n; i++) {
      var p = document.createElement('i'), ang = Math.random() * Math.PI * 2, d = 150 + Math.random() * 190;
      p.style.background = cores[i % cores.length]; wrap.appendChild(p);
      p.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: 'translate(' + Math.cos(ang) * d + 'px,' + Math.sin(ang) * d + 'px) scale(.2) rotate(' + (Math.random() * 540) + 'deg)', opacity: 0 }],
        { duration: 900 + Math.random() * 700, easing: 'cubic-bezier(.1,.7,.3,1)', fill: 'forwards' });
    }
    ancora.appendChild(wrap); setTimeout(function () { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, 1800);
  }
  /* raios: relâmpagos irregulares (com ramificações) caem do topo, com clarão azulado, em sequência; WAAPI, nada fica no DOM depois */
  function caminho(x0, y0, x1, y1, amp, seg) {
    var p = [[x0, y0]], i; for (i = 1; i < seg; i++) { var t = i / seg; p.push([x0 + (x1 - x0) * t + (Math.random() - 0.5) * amp, y0 + (y1 - y0) * t + (Math.random() - 0.5) * amp * 0.35]); }
    p.push([x1, y1]); return p;
  }
  function dpath(p) { return 'M' + p.map(function (q) { return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join(' L'); }
  function raios(alvo, n, cor, opt) {   // opt = {x, y, n}: os primeiros `opt.n` raios caem DIRETO naquele ponto (mais grossos)
    if (reduz() || !alvo || !alvo.animate) return;
    var w = alvo.clientWidth || 800, h = alvo.clientHeight || 600, cx = cor || '#9FD4FF', wrap = document.createElement('div'); wrap.className = 'c-raios';
    for (var i = 0; i < (n || 6); i++) {
      var forte = !!(opt && opt.x != null && i < (opt.n || 1)), x0 = forte ? opt.x + (Math.random() - 0.5) * 70 : w * (0.08 + Math.random() * 0.84), y1 = forte ? opt.y : h * (0.45 + Math.random() * 0.5), x1 = forte ? opt.x + (Math.random() - 0.5) * 24 : x0 + (Math.random() - 0.5) * w * 0.18, main = caminho(x0, -10, x1, y1, w * 0.07, 12), d = dpath(main), ramos = '';
      for (var r = 0; r < 3; r++) {
        var m = main[2 + Math.floor(Math.random() * 8)], dir = Math.random() < 0.5 ? -1 : 1;
        ramos += '<path class="r" d="' + dpath(caminho(m[0], m[1], m[0] + dir * (40 + Math.random() * 110), m[1] + 60 + Math.random() * 130, 26, 5)) + '"/>';
      }
      var sv = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); sv.setAttribute('class', 'c-raio' + (forte ? ' forte' : '')); sv.setAttribute('width', w); sv.setAttribute('height', h); sv.setAttribute('viewBox', '0 0 ' + w + ' ' + h); sv.style.setProperty('--rc', cx);
      sv.innerHTML = '<path class="g" d="' + d + '"/><path class="n" d="' + d + '"/>' + ramos;
      var fl = document.createElement('div'); fl.className = 'c-raio-flash'; wrap.appendChild(fl); wrap.appendChild(sv);
      var at = 120 + i * (1500 / (n || 6)) + Math.random() * 220;
      sv.animate([{ opacity: 0 }, { opacity: 1, offset: 0.1 }, { opacity: 0.25, offset: 0.25 }, { opacity: 1, offset: 0.4 }, { opacity: 0.5, offset: 0.65 }, { opacity: 0 }], { duration: 480, delay: at, fill: 'both' });
      fl.animate([{ opacity: 0 }, { opacity: 0.9, offset: 0.1 }, { opacity: 0.15, offset: 0.3 }, { opacity: 0.6, offset: 0.4 }, { opacity: 0 }], { duration: 480, delay: at, fill: 'both' });
    }
    alvo.appendChild(wrap); setTimeout(function () { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, 3200);
  }

  /* ---- revelação (modo reunião): a carta chega num pacote que treme, vira e solta um clarão ---- */
  function revelar(carta) {
    if (reduz() || !carta || !carta.animate) return;
    var conj = carta.closest('.c-conj') || carta, pai = conj.parentNode, borda = (carta.className.match(/b-(?:\d+|top)/) || [''])[0];
    var capa = document.createElement('div'); capa.className = 'c-pacote'; capa.innerHTML = '<div>SENTINELA<small>CARTINHA</small></div>';
    conj.classList.add('c-oculta'); conj.appendChild(capa);   // a capa mora dentro do conjunto: herda a escala e cobre só a carta
    var persp = 'perspective(900px) ';
    var treme = capa.animate([{ transform: persp + 'rotate(0)' }, { transform: persp + 'rotate(-2.5deg)' }, { transform: persp + 'rotate(2.5deg)' }, { transform: persp + 'rotate(-2deg)' }, { transform: persp + 'rotate(0)' }], { duration: 520, easing: 'ease-in-out' });
    treme.onfinish = function () {
      var vira = capa.animate([{ transform: persp + 'rotateY(0)' }, { transform: persp + 'rotateY(90deg)' }], { duration: 170, easing: 'ease-in', fill: 'forwards' });
      vira.onfinish = function () {
        if (capa.parentNode) capa.parentNode.removeChild(capa);
        conj.classList.remove('c-oculta');
        carta.animate([{ transform: persp + 'rotateY(-90deg)', filter: 'brightness(2.4)' }, { transform: persp + 'rotateY(0)', filter: 'brightness(1.6)', offset: .6 }, { transform: persp + 'rotateY(0)', filter: 'brightness(1)' }], { duration: 520, easing: 'cubic-bezier(.2,.9,.3,1)' });
        particulas(pai, borda, borda === 'b-100' ? 48 : borda === 'b-90' ? 22 : 14);
      };
    };
  }

  function ligar(raiz) {
    esqueleto(raiz);
    var lista = (raiz || document).querySelectorAll('.carta:not([data-fx])');
    Array.prototype.forEach.call(lista, function (c) {
      c.setAttribute('data-fx', '');
      if (io) io.observe(c); else c.classList.add('vivo');
    });
  }

  function aplicar() {
    raf = 0;
    if (!ativa || !ultimo) return;
    var ref = ativa.closest('.slot') || ativa.parentElement || ativa;   // medido no contêiner, que não gira (o cartão gira)
    var r = ref.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var px = Math.max(0, Math.min(1, (ultimo.clientX - r.left) / r.width));
    var py = Math.max(0, Math.min(1, (ultimo.clientY - r.top) / r.height));
    var max = ativa.classList.contains('b-100') ? 17 : (ativa.classList.contains('b-90') ? 15 : MAX);
    var s = ativa.style;
    s.setProperty('--mx', (px * 100).toFixed(1) + '%');
    s.setProperty('--my', (py * 100).toFixed(1) + '%');
    s.setProperty('--ry', ((px - 0.5) * 2 * max).toFixed(2) + 'deg');
    s.setProperty('--rx', ((0.5 - py) * 2 * max).toFixed(2) + 'deg');
    s.setProperty('--brilho', '1');
    var w = ativa.parentElement; if (w && w.classList.contains('c-conj')) { w.style.setProperty('--ry', s.getPropertyValue('--ry')); w.style.setProperty('--rx', s.getPropertyValue('--rx')); }   // as peças da moldura acompanham a inclinação
  }

  function soltar(c) {
    if (!c) return;
    c.classList.remove('inclinando');
    c.style.removeProperty('--rx'); c.style.removeProperty('--ry'); c.style.removeProperty('--brilho');
    var w = c.parentElement; if (w && w.classList.contains('c-conj')) { w.style.removeProperty('--rx'); w.style.removeProperty('--ry'); }
  }

  document.addEventListener('pointermove', function (e) {
    if (reduz() || e.pointerType === 'touch') return;
    var c = e.target && e.target.closest ? e.target.closest('.carta[data-fx]') : null;
    if (c !== ativa) { soltar(ativa); ativa = c; if (c) c.classList.add('inclinando'); }
    if (!c) return;
    ultimo = e;
    if (!raf) raf = requestAnimationFrame(aplicar);
  }, { passive: true });
  document.documentElement.addEventListener('pointerleave', function () { soltar(ativa); ativa = null; });

  document.addEventListener('pointerdown', function (e) {     // toque: um clarão rápido onde o dedo encostou
    if (reduz() || e.pointerType !== 'touch') return;
    var c = e.target && e.target.closest ? e.target.closest('.carta[data-fx]') : null;
    if (!c) return;
    var r = (c.closest('.slot') || c.parentElement || c).getBoundingClientRect();
    c.style.setProperty('--mx', (((e.clientX - r.left) / r.width) * 100).toFixed(1) + '%');
    c.style.setProperty('--my', (((e.clientY - r.top) / r.height) * 100).toFixed(1) + '%');
    c.style.setProperty('--brilho', '1');
    setTimeout(function () { c.style.removeProperty('--brilho'); }, 700);
  }, { passive: true });

  if ('IntersectionObserver' in window) io = new IntersectionObserver(aoVer, { threshold: 0.2 });
  ligar();
  var pendente = false;
  new MutationObserver(function () {
    if (pendente) return;
    pendente = true;
    requestAnimationFrame(function () { pendente = false; ligar(); });
  }).observe(document.documentElement, { childList: true, subtree: true });
  window.CartaFX = { ligar: ligar, revelar: revelar, raios: raios, reduz: SIST };
})();
