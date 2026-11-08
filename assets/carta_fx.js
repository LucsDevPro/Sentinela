/* Efeitos vivos das cartas — liga o que o carta.css (seção "EFEITOS VIVOS") desenha.
   - inclinação 3D e brilho que seguem o ponteiro (só mouse/caneta; no toque, um clarão ao tocar);
   - .vivo só nas cartas que estão na tela (as animações param fora dela: poupa CPU/bateria);
   - entrada em cascata (.entra) e a nota subindo, contando, na primeira vez que a carta aparece;
   - sem nada disso quando o sistema pede menos movimento (prefers-reduced-motion).
   Funciona sozinho: observa o DOM e liga as cartas que aparecerem depois (filtros do álbum, agente.html). */
(function () {
  'use strict';
  var REDUZ = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var MAX = 13;                 // inclinação máxima (graus)
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
      if (REDUZ) return;
      if (!c.style.getPropertyValue('--atraso')) {        // cartas que aparecem juntas entram uma após a outra
        c.style.setProperty('--atraso', Math.min(fila * 55, 700) + 'ms');
        fila++; clearTimeout(filaT); filaT = setTimeout(function () { fila = 0; }, 150);
      }
      c.classList.add('entra');
      contar(c);
    });
  }

  function ligar(raiz) {
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
    var s = ativa.style;
    s.setProperty('--mx', (px * 100).toFixed(1) + '%');
    s.setProperty('--my', (py * 100).toFixed(1) + '%');
    s.setProperty('--ry', ((px - 0.5) * 2 * MAX).toFixed(2) + 'deg');
    s.setProperty('--rx', ((0.5 - py) * 2 * MAX).toFixed(2) + 'deg');
    s.setProperty('--brilho', '1');
  }

  function soltar(c) {
    if (!c) return;
    c.classList.remove('inclinando');
    c.style.removeProperty('--rx'); c.style.removeProperty('--ry'); c.style.removeProperty('--brilho');
  }

  document.addEventListener('pointermove', function (e) {
    if (REDUZ || e.pointerType === 'touch') return;
    var c = e.target && e.target.closest ? e.target.closest('.carta[data-fx]') : null;
    if (c !== ativa) { soltar(ativa); ativa = c; if (c) c.classList.add('inclinando'); }
    if (!c) return;
    ultimo = e;
    if (!raf) raf = requestAnimationFrame(aplicar);
  }, { passive: true });
  document.documentElement.addEventListener('pointerleave', function () { soltar(ativa); ativa = null; });

  document.addEventListener('pointerdown', function (e) {     // toque: um clarão rápido onde o dedo encostou
    if (REDUZ || e.pointerType !== 'touch') return;
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
  window.CartaFX = { ligar: ligar };
})();
