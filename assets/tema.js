/* Tema do Sentinela: claro por padrão, escuro opcional (botão no cabeçalho).
   Carregue este arquivo no <head>: ele aplica a escolha ANTES de pintar a página (sem piscar).
   A escolha fica só neste navegador (localStorage); se o navegador bloquear, vale o claro. */
(function () {
  var raiz = document.documentElement;
  function ler() { try { return localStorage.getItem('sentinelaTema'); } catch (e) { return null; } }
  function gravar(t) { try { localStorage.setItem('sentinelaTema', t); } catch (e) {} }
  /* Página que nasce escura (ex.: a Sala de Troféus) declara <html data-tema-padrao="dark">: sem escolha guardada vale o escuro, e o botão leva ao claro (data-theme="light"). */
  var padrao = raiz.getAttribute('data-tema-padrao') === 'dark' ? 'dark' : 'light', guardado = ler();
  var atual = guardado === 'dark' || guardado === 'light' ? guardado : padrao;
  function pintar() { if (atual === 'dark') raiz.setAttribute('data-theme', 'dark'); else if (padrao === 'dark') raiz.setAttribute('data-theme', 'light'); else raiz.removeAttribute('data-theme'); }
  pintar();

  function cor(nome, padrao) {
    var v = getComputedStyle(raiz).getPropertyValue(nome).trim();
    return v || padrao;
  }
  /* Faz os gráficos (Chart.js) acompanharem o tema, inclusive os que já estão na tela */
  window.aplicarTemaGraficos = function () {
    if (!window.Chart) return;
    if (window.SENT_GRAF) window.SENT_GRAF.padroes();
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
      if (window.SENT_GRAF) window.SENT_GRAF.retingir(ch);
      ch.update('none');
    });
  };
  window.alternarTema = function () {
    atual = atual === 'dark' ? 'light' : 'dark';
    pintar();
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

/* Gráficos institucionais (Chart.js): anatomia e cores compartilhadas por TODAS as páginas.
   - Cores por PAPEL, não por hex: o gráfico diz `papel: 'serie1'` (ou `papeis: ['bom','critico', ...]` uma por barra) e este módulo
     escolhe a cor certa para o tema e a refaz sozinho quando o tema muda. Séries = azul, laranja e verde-água, validadas com o
     validador da skill dataviz nos dois temas (separação para daltonismo ΔE ≥ 9, visão normal ≥ 26). Estado (normal/atenção/crítico)
     usa a MESMA régua das legendas e emblemas do site.
   - Anatomia: barras finas (≤ 24 px) com a ponta arredondada e a base reta, grade discreta sem linha de eixo, legenda com marcador,
     tooltip escuro com números em pt-BR, valores escritos só onde ajudam (plugin `valores`) e total no centro da rosca (plugin `centro`). */
(function () {
  var raiz = document.documentElement;
  function escuro() { return raiz.getAttribute('data-theme') === 'dark'; }
  function css(nome, padrao) { var v = getComputedStyle(raiz).getPropertyValue(nome).trim(); return v || padrao; }
  var SERIES = {
    claro:  { serie1: '#1c5cab', serie2: '#eb6834', serie3: '#1baf7a', neutro: '#8392a8' },
    escuro: { serie1: '#3987e5', serie2: '#d95926', serie3: '#199e70', neutro: '#7088ab' }
  };
  var ESTADO = { bom: '#12B76A', atencao: '#F2B01E', critico: '#E4572E' };
  var ESTADO_ROTULO = { bom: 'Normal', atencao: 'Atenção', critico: 'Crítico' };
  function cor(papel) { return ESTADO[papel] || (SERIES[escuro() ? 'escuro' : 'claro'])[papel] || papel; }
  function fmt(v, casas) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    var c = casas == null ? (Number.isInteger(Number(v)) ? 0 : 1) : casas;
    return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c });
  }
  function lum(hex) {
    var m = /^#?([0-9a-f]{6})/i.exec(hex || ''); if (!m) return 0.5;
    var n = parseInt(m[1], 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function textoSobre(fundo) {   // branco ou o azul-tinta, o que contrastar mais com o preenchimento
    var l = lum(fundo), ctBranco = 1.05 / (l + 0.05), ctTinta = (l + 0.05) / (lum('#12233B') + 0.05);
    return ctBranco >= ctTinta ? '#FFFFFF' : '#12233B';
  }

  /* Escreve o valor na ponta da barra ('ponta') ou dentro do segmento ('dentro', só se couber).
     Ligue por gráfico: options.plugins.valores = { ativo: true, casas: 0, posicao: 'ponta' | 'dentro', omitirZero: true }.
     O dataset pode trazer `casas`, `prefixo` e `sufixo` (ex.: sufixo: '%'), os mesmos usados no tooltip. */
  var pluginValores = {
    id: 'valores',
    afterDatasetsDraw: function (ch, args, o) {
      if (!o || !o.ativo) return;
      var ctx = ch.ctx, horiz = ch.options.indexAxis === 'y', tam = o.tamanho || 11;
      ctx.save(); ctx.font = '600 ' + tam + 'px "IBM Plex Sans", sans-serif';
      ch.data.datasets.forEach(function (ds, i) {
        var meta = ch.getDatasetMeta(i); if (meta.hidden) return;
        meta.data.forEach(function (el, j) {
          var v = ds.data[j]; if (v === null || v === undefined || (o.omitirZero && Number(v) === 0)) return;
          var txt = (ds.prefixo || '') + fmt(v, ds.casas != null ? ds.casas : o.casas) + (ds.sufixo || ''), w = ctx.measureText(txt).width;
          if (o.posicao === 'dentro') {
            var comp = horiz ? Math.abs(el.x - el.base) : Math.abs(el.y - el.base), larg = horiz ? el.height : el.width;
            if (comp < (horiz ? w + 12 : tam + 8) || larg < (horiz ? tam + 4 : w + 12)) return;   // não cabe: legenda e tooltip carregam o valor
            var fundo = Array.isArray(ds.backgroundColor) ? ds.backgroundColor[j] : ds.backgroundColor;
            ctx.fillStyle = textoSobre(typeof fundo === 'string' ? fundo : '#888888');
            ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
            ctx.fillText(txt, horiz ? (el.x + el.base) / 2 : el.x, horiz ? el.y : (el.y + el.base) / 2);
          } else {
            ctx.fillStyle = css('--text', '#12233B');
            if (horiz) { ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(txt, el.x + 6, el.y); }
            else { ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'; ctx.fillText(txt, el.x, el.y - 5); }
          }
        });
      });
      ctx.restore();
    }
  };
  /* Número grande no meio da rosca: options.plugins.centro = { valor: '42', rotulo: 'agentes' } */
  var pluginCentro = {
    id: 'centro',
    afterDraw: function (ch, args, o) {
      if (!o || o.valor == null) return;
      var a = ch.chartArea, ctx = ch.ctx, x = (a.left + a.right) / 2, y = (a.top + a.bottom) / 2, d = Math.min(a.right - a.left, a.bottom - a.top);
      ctx.save(); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = css('--h', '#0B2A52'); ctx.font = '700 ' + Math.round(d * 0.2) + 'px "Barlow Semi Condensed", "IBM Plex Sans", sans-serif';
      ctx.fillText(String(o.valor), x, y - d * 0.04);
      ctx.fillStyle = css('--text2', '#455879'); ctx.font = '500 ' + Math.max(10, Math.round(d * 0.065)) + 'px "IBM Plex Sans", sans-serif';
      ctx.fillText(o.rotulo || '', x, y + d * 0.11); ctx.restore();
    }
  };

  var registrado = false;
  function padroes() {
    if (!window.Chart) return;
    if (!registrado) { Chart.register(pluginValores, pluginCentro); registrado = true; }
    var D = Chart.defaults, txt = css('--text2', '#455879'), grade = css('--grid', 'rgba(69,88,121,0.16)');
    D.font.family = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
    D.color = txt; D.borderColor = grade;
    D.animation = (window.animacoesLigadas && !window.animacoesLigadas()) ? false : { duration: 550, easing: 'easeOutQuart' };
    var L = D.plugins.legend.labels;
    D.plugins.legend.position = 'bottom'; L.usePointStyle = true; L.pointStyle = 'rectRounded'; L.boxWidth = 9; L.boxHeight = 9; L.padding = 16; L.color = txt;
    var T = D.plugins.tooltip;
    T.backgroundColor = 'rgba(8,22,42,0.96)'; T.borderColor = 'rgba(255,255,255,0.14)'; T.borderWidth = 1; T.padding = 10; T.cornerRadius = 8; T.boxPadding = 5;
    T.titleColor = '#FFFFFF'; T.bodyColor = '#DCE7F5'; T.titleFont = { weight: '600', size: 12 }; T.bodyFont = { size: 12 }; T.titleMarginBottom = 6; T.usePointStyle = true;
    T.callbacks.label = function (c) {
      var ds = c.dataset, t = c.chart.config.type, v = (t === 'doughnut' || t === 'pie') ? c.parsed : (c.chart.options.indexAxis === 'y' ? c.parsed.x : c.parsed.y);
      var nome = (t === 'doughnut' || t === 'pie') ? c.label : ds.label, valor = (ds.prefixo || '') + fmt(v, ds.casas) + (ds.sufixo || '');
      return nome ? nome + ': ' + valor : valor;
    };
    T.callbacks.afterLabel = function (c) {
      var ds = c.dataset, t = c.chart.config.type;
      if ((t === 'doughnut' || t === 'pie') && c.dataset.data.length) {
        var tot = c.dataset.data.reduce(function (a, b) { return a + Number(b || 0); }, 0);
        return tot ? fmt(c.parsed / tot * 100, 1) + '% do total' : '';
      }
      if (ds.papeis && ds.papeis[c.dataIndex]) return 'Situação: ' + (ESTADO_ROTULO[ds.papeis[c.dataIndex]] || '');
    };
    ['category', 'linear', 'logarithmic'].forEach(function (tipo) {   // cada tipo de escala guarda os próprios padrões
      var E = D.scales[tipo]; if (!E) return;
      E.grid = E.grid || {}; E.border = E.border || {}; E.ticks = E.ticks || {};
      E.grid.drawTicks = false; E.grid.color = grade; E.border.display = false; E.ticks.padding = 6; E.ticks.color = txt;
    });
    D.scales.category.grid.display = false;
    D.scales.linear.ticks.callback = function (v) { return fmt(v); };
    var B = D.datasets.bar; B.maxBarThickness = 24; B.borderRadius = 4; B.borderSkipped = 'start'; B.categoryPercentage = 0.8; B.barPercentage = 0.88;
    var N = D.datasets.line; N.borderWidth = 2; N.tension = 0.25; N.pointRadius = 4; N.pointHoverRadius = 6; N.pointBorderWidth = 2; N.borderJoinStyle = 'round'; N.borderCapStyle = 'round';
  }
  /* Refaz as cores das séries com `papel`/`papeis` (troca de tema) e o "respiro" de 2 px entre segmentos/pontos */
  function superficie() { return css('--card', '#FFFFFF'); }
  function retingir(ch) {
    var sup = superficie();
    ch.data.datasets.forEach(function (ds) {
      var tipo = ds.type || ch.config.type;
      if (ds.papeis) ds.backgroundColor = ds.papeis.map(cor);
      else if (ds.papel) {
        var c = cor(ds.papel);
        if (tipo === 'line') { ds.borderColor = c; ds.backgroundColor = c; ds.pointBackgroundColor = c; ds.pointBorderColor = sup; }
        else ds.backgroundColor = c;
      }
      if (ds.respiro) { ds.borderColor = sup; ds.borderWidth = 2; }
    });
  }
  window.SENT_GRAF = { superficie: superficie, cor: cor, fmt: fmt, padroes: padroes, retingir: retingir, ESTADO: ESTADO, ESTADO_ROTULO: ESTADO_ROTULO, textoSobre: textoSobre };
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
