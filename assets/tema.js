/* Tema do Sentinela: claro por padrão, escuro opcional (botão no cabeçalho).
   Carregue este arquivo no <head>: ele aplica a escolha ANTES de pintar a página (sem piscar).
   A escolha fica só neste navegador (localStorage); se o navegador bloquear, vale o claro. */
(function () {
  var raiz = document.documentElement;
  function ler() { try { return localStorage.getItem('sentinelaTema'); } catch (e) { return null; } }
  function gravar(t) { try { localStorage.setItem('sentinelaTema', t); } catch (e) {} }
  var atual = ler() === 'dark' ? 'dark' : 'light';
  if (atual === 'dark') raiz.setAttribute('data-theme', 'dark'); else raiz.removeAttribute('data-theme');

  function cor(nome, padrao) {
    var v = getComputedStyle(raiz).getPropertyValue(nome).trim();
    return v || padrao;
  }
  /* Faz os gráficos (Chart.js) acompanharem o tema, inclusive os que já estão na tela */
  window.aplicarTemaGraficos = function () {
    if (!window.Chart) return;
    var txt = cor('--text2', '#46597A'), grade = cor('--grid', 'rgba(70,89,122,0.16)');
    Chart.defaults.color = txt; Chart.defaults.borderColor = grade;
    var lista = Chart.instances ? Object.values(Chart.instances) : [];
    lista.forEach(function (ch) {
      var o = (ch.config && ch.config.options) || {};
      o.plugins = o.plugins || {}; o.plugins.legend = o.plugins.legend || {}; o.plugins.legend.labels = o.plugins.legend.labels || {}; o.plugins.legend.labels.color = txt;
      var escalas = o.scales || {};
      if (ch.scales) Object.keys(ch.scales).forEach(function (k) { if (!escalas[k]) escalas[k] = {}; }); o.scales = escalas;
      Object.values(escalas).forEach(function (s) {
        s.ticks = s.ticks || {}; s.ticks.color = txt;
        s.grid = s.grid || {}; s.grid.color = grade;
        if (s.title) s.title.color = txt;
      });
      ch.update('none');
    });
  };
  window.alternarTema = function () {
    atual = atual === 'dark' ? 'light' : 'dark';
    if (atual === 'dark') raiz.setAttribute('data-theme', 'dark'); else raiz.removeAttribute('data-theme');
    gravar(atual);
    rotular();
    window.aplicarTemaGraficos();
    document.dispatchEvent(new CustomEvent('sentinela:tema', { detail: atual }));
  };
  window.temaAtual = function () { return atual; };
  function rotular() {
    document.querySelectorAll('[data-tema-btn]').forEach(function (b) {
      b.setAttribute('aria-pressed', atual === 'dark' ? 'true' : 'false');
      b.setAttribute('title', atual === 'dark' ? 'Mudar para o tema claro' : 'Mudar para o tema escuro');
      b.setAttribute('aria-label', b.getAttribute('title'));
      var t = b.querySelector('.tema-txt'); if (t) t.textContent = atual === 'dark' ? 'Tema claro' : 'Tema escuro';
    });
  }
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-tema-btn]').forEach(function (b) { b.addEventListener('click', window.alternarTema); });
    rotular();
  });
})();

/* Animação de entrada dos números (um único efeito: contagem de 0 até o valor, ~0,6 s).
   Liga/desliga pela caixa "Animações" (fica salvo neste navegador). Respeita "reduzir movimento" do sistema. */
(function () {
  function ler() { try { return localStorage.getItem('sentinelaAnim'); } catch (e) { return null; } }
  function gravar(v) { try { localStorage.setItem('sentinelaAnim', v); } catch (e) {} }
  var reduz = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.animacoesLigadas = function () { return !reduz && ler() !== 'off'; };
  var RX = /^(-?\d{1,3}(?:\.\d{3})*|-?\d+)(,\d+)?(%?)$/;
  function contar(el) {
    var orig = el.textContent.trim(), m = RX.exec(orig);
    if (!m) return;
    var inteiro = parseInt(m[1].replace(/\./g, ''), 10), dec = m[2] ? m[2].length - 1 : 0;
    var alvo = parseFloat(m[1].replace(/\./g, '') + (m[2] ? '.' + m[2].slice(1) : ''));
    if (!isFinite(alvo) || alvo === 0) return;
    var t0 = null, dur = 600;
    function fmt(v) {
      var s = v.toFixed(dec).split('.');
      s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      return s.join(',') + m[3];
    }
    function passo(t) {
      if (t0 === null) t0 = t;
      var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = p >= 1 ? orig : fmt(alvo * e);
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }
  window.animarNumeros = function (raiz) {
    if (!window.animacoesLigadas()) return;
    (raiz || document).querySelectorAll('.kpi-value, .ac-val, .ts-val').forEach(function (el) {
      if (el.offsetParent !== null) contar(el);
    });
  };
  document.addEventListener('DOMContentLoaded', function () {
    var cx = document.getElementById('toggleAnimacoes');
    if (cx) {
      cx.checked = window.animacoesLigadas();
      if (reduz) { cx.disabled = true; cx.parentNode.title = 'Seu sistema está configurado para reduzir movimento'; }
      cx.addEventListener('change', function () { gravar(cx.checked ? 'on' : 'off'); if (cx.checked) window.animarNumeros(); });
    }
    window.addEventListener('load', function () { window.animarNumeros(); });
    document.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('.nav-tab')) setTimeout(function () { window.animarNumeros(document.querySelector('.section.active, section.active') || document); }, 30);
    });
  });
})();
