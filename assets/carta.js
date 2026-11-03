/* Cartão do agente (estilo carta de jogador). Usado em agente.html e album.html.
   Carta.html(agente, mesesAteOMesEscolhido) -> HTML do cartão ('' se não houver nota). */
(function () {
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); };
  var f1 = function (n) { return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); };
  var SV = function (n) { return '<svg class="ico" aria-hidden="true"><use href="#i-' + n + '"/></svg>'; };
  var NOMES = { ASS: 'Assiduidade', TUR: 'Turnos cobertos', CON: 'Consistência', EVO: 'Evolução', POS: 'Posição', MED: 'Média dos meses' };
  function medidas(ms) {
    var u = ms[ms.length - 1]; if (!u || u.pontos == null) return null;
    var ant = ms.length > 1 ? ms[ms.length - 2] : null;
    var cl = function (v) { return Math.max(0, Math.min(99, Math.round(v))); };
    var notas = ms.map(function (m) { return m.pontos; }).filter(function (v) { return v != null; });
    var media = notas.reduce(function (t, v) { return t + v; }, 0) / notas.length;
    var dp = notas.length > 1 ? Math.sqrt(notas.reduce(function (t, v) { return t + Math.pow(v - media, 2); }, 0) / notas.length) : 0;
    var delta = ant && ant.pontos != null ? u.pontos - ant.pontos : null;
    var st = [['ASS', u.esp ? cl(u.trab / u.esp * 100) : 0], ['TUR', u.esp ? cl(100 - (u.turnos_sem || 0) / (u.esp * 2) * 100) : 0],
      ['CON', cl(100 - 5 * dp)], ['EVO', delta == null ? 50 : cl(50 + 5 * delta)],
      ['POS', u.total > 1 ? cl((u.total - u.pos) / (u.total - 1) * 100) : 99], ['MED', cl(media)]];
    var tier = (u.pos <= 3 && u.pontos >= 90) ? ['t-destaque', 'DESTAQUE'] : u.pontos >= 90 ? ['', 'OURO'] : u.pontos >= 75 ? ['t-prata', 'PRATA'] : ['t-bronze', 'BRONZE'];
    return { u: u, delta: delta, st: st, tier: tier };
  }
  function html(a, ms) {
    var m = medidas(ms); if (!m) return '';
    var u = m.u, delta = m.delta, st = m.st, tier = m.tier;
    var partes = String(a.nome).trim().split(/\s+/), curto = partes.length > 1 ? partes[0] + ' ' + partes[partes.length - 1] : partes[0];
    var ini = (partes[0][0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
    var eq = String(a.equipe).replace(/^Equipe\s*/i, 'EQ ');
    var tend = delta == null ? SV('minus') + ' sem mês anterior' : delta > 0.05 ? SV('arrow-up') + ' +' + f1(delta) + ' pts' : delta < -0.05 ? SV('arrow-down') + ' ' + f1(delta) + ' pts' : SV('minus') + ' estável';
    return '<div class="carta ' + tier[0] + '" role="img" aria-label="Cartão de ' + esc(a.nome) + ': nota ' + f1(u.pontos) + ', nível ' + tier[1] + '">' +
      '<div class="c-topo"><div class="c-ovr"><b' + (Math.round(u.pontos) >= 100 ? ' class="tres"' : '') + '>' + Math.round(u.pontos) + '</b><span>NOTA</span></div>' +
      '<div class="c-pos">' + esc(eq) + '<small>' + u.pos + 'º de ' + u.total + '</small></div><div class="c-logo" aria-hidden="true"><i></i></div></div>' +
      '<div class="c-foto"><span class="nome">' + esc(ini) + '</span></div>' +
      '<div class="c-nome nome"' + (curto.length > 20 ? ' style="font-size:1.05rem"' : curto.length > 15 ? ' style="font-size:1.2rem"' : '') + '>' + esc(curto) + '</div>' +
      '<div class="c-stats">' + st.map(function (x) { return '<div><b>' + x[1] + '</b><span>' + x[0] + '</span></div>'; }).join('') + '</div>' +
      '<div class="c-rodape"><span>' + esc(u.mes) + ' · ' + tier[1] + '</span><span>' + tend + '</span></div></div>';
  }

  /* ---- Imagem do cartão (PNG) para baixar ou mandar pelo WhatsApp ---- */
  var LOGO = { '': ['#A87612', '#7A520A', '#5C3C05'], 't-prata': ['#6F7F96', '#4C5B70', '#37455A'], 't-bronze': ['#8A4E22', '#63350F', '#4A2609'], 't-destaque': ['#FBE08A', '#F7B500', '#C58F00'] };
  var ICONES = { 'arrow-up': 'M12 19V5M6 11l6-6 6 6', 'arrow-down': 'M12 5v14M6 13l6 6 6-6', 'minus': 'M5 12h14' };
  function carregar(src) { return new Promise(function (ok, erro) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = erro; i.src = src; }); }
  function gradCss(ctx, ang, x, y, w, h, c1, c2) {
    var a = ang * Math.PI / 180, dx = Math.sin(a), dy = -Math.cos(a), L = Math.abs(w * dx) + Math.abs(h * dy), cx = x + w / 2, cy = y + h / 2;
    var g = ctx.createLinearGradient(cx - dx * L / 2, cy - dy * L / 2, cx + dx * L / 2, cy + dy * L / 2); g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
  }
  function pathCartao(ctx, x, y, w, h, S) {
    ctx.beginPath(); ctx.moveTo(x + 22 * S, y);
    ctx.lineTo(x + w - 22 * S, y); ctx.ellipse(x + w - 22 * S, y + 22 * S, 22 * S, 22 * S, 0, 1.5 * Math.PI, 2 * Math.PI);
    ctx.lineTo(x + w, y + h - 34 * S); ctx.ellipse(x + w - 46 * S, y + h - 34 * S, 46 * S, 34 * S, 0, 0, .5 * Math.PI);
    ctx.lineTo(x + 46 * S, y + h); ctx.ellipse(x + 46 * S, y + h - 34 * S, 46 * S, 34 * S, 0, .5 * Math.PI, Math.PI);
    ctx.lineTo(x, y + 22 * S); ctx.ellipse(x + 22 * S, y + 22 * S, 22 * S, 22 * S, 0, Math.PI, 1.5 * Math.PI); ctx.closePath();
  }
  function texto(ctx, txt, x, y, ls) { // letra a letra, para respeitar o espaçamento entre letras em qualquer navegador
    if (!ls) { ctx.fillText(txt, x, y); return; }
    for (var i = 0; i < txt.length; i++) { ctx.fillText(txt[i], x, y); x += ctx.measureText(txt[i]).width + ls; }
  }
  function png(a, ms, opcoes) {
    opcoes = opcoes || {};
    var S = 2, M = 20, host = document.createElement('div'), html0 = html(a, ms);
    if (!html0) return Promise.reject(new Error('sem nota'));
    host.style.cssText = 'position:fixed;left:-9999px;top:0;width:272px;pointer-events:none'; host.innerHTML = html0; document.body.appendChild(host);
    var card = host.firstElementChild, tier = (card.className.match(/t-\w+/) || [''])[0];
    var oculta = !!opcoes.ocultarNomes;
    var pronto = Promise.all([document.fonts ? document.fonts.ready : 0, document.fonts ? document.fonts.load('700 20px "Barlow Semi Condensed"') : 0, document.fonts ? document.fonts.load('600 14px "IBM Plex Sans"') : 0, carregar('assets/logo_carta.png')]);
    return pronto.then(function (r) {
      var logo = r[3], cr = card.getBoundingClientRect(), W = cr.width * S, H = cr.height * S;
      var cv = document.createElement('canvas'); cv.width = Math.round(W + 2 * M * S); cv.height = Math.round(H + 2 * M * S);
      var ctx = cv.getContext('2d'), cs = getComputedStyle(card), c1 = cs.getPropertyValue('--c1').trim(), c2 = cs.getPropertyValue('--c2').trim(), ln = cs.getPropertyValue('--ln').trim();
      var X = M * S, Y = M * S;
      ctx.fillStyle = '#EEF2F8'; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.30)'; ctx.shadowBlur = 28 * S; ctx.shadowOffsetY = 10 * S; pathCartao(ctx, X, Y, W, H, S); ctx.fillStyle = c2; ctx.fill(); ctx.restore();
      pathCartao(ctx, X, Y, W, H, S); ctx.save(); ctx.clip();
      ctx.fillStyle = gradCss(ctx, 155, X, Y, W, H, c1, c2); ctx.fillRect(X, Y, W, H);
      // listras
      ctx.save(); ctx.translate(X + W / 2, Y + H / 2); ctx.rotate((115 - 90) * Math.PI / 180);
      ctx.fillStyle = tier === 't-destaque' ? 'rgba(25,184,163,.16)' : 'rgba(255,255,255,.14)';
      for (var k = -Math.ceil(W + H); k < W + H; k += 34 * S) ctx.fillRect(k, -(W + H), 14 * S, 2 * (W + H));
      ctx.restore();
      // brilho
      var gx = X + (-0.30 * W) + 0.45 * W, gy = Y + (-0.40 * H) + 0.45 * H, rr = Math.min(.9 * W, .9 * H) / 2;
      var rg = ctx.createRadialGradient(gx, gy, 0, gx, gy, rr); rg.addColorStop(0, 'rgba(255,255,255,.55)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = rg; ctx.fillRect(X, Y, W, H);
      ctx.restore();
      var rel = function (e) { var b = e.getBoundingClientRect(); return { x: X + (b.left - cr.left) * S, y: Y + (b.top - cr.top) * S, w: b.width * S, h: b.height * S }; };
      // foto (círculo)
      var f = card.querySelector('.c-foto'), fr = rel(f), fs = getComputedStyle(f), bw = parseFloat(fs.borderTopWidth) * S;
      ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, fr.w / 2 - bw / 2, 0, 2 * Math.PI); ctx.fillStyle = fs.backgroundColor; ctx.fill(); ctx.lineWidth = bw; ctx.strokeStyle = ln; ctx.stroke();
      // linhas (bordas) do cartão
      [['.c-pos', 'top'], ['.c-nome', 'bottom'], ['.c-stats', 'bottom']].forEach(function (p) {
        var e = card.querySelector(p[0]), r0 = rel(e), w0 = parseFloat(getComputedStyle(e)['border' + (p[1] === 'top' ? 'Top' : 'Bottom') + 'Width']) * S;
        ctx.fillStyle = ln; ctx.fillRect(r0.x, p[1] === 'top' ? r0.y : r0.y + r0.h - w0, r0.w, w0);
      });
      var rod = card.querySelector('.c-rodape'), rr0 = rel(rod); ctx.fillStyle = 'rgba(0,0,0,0)';
      // textos
      var tw = document.createTreeWalker(card, NodeFilter.SHOW_TEXT), n;
      ctx.textBaseline = 'middle';
      while ((n = tw.nextNode())) {
        var t = n.nodeValue.replace(/\s+/g, ' ').trim(); if (!t) continue;
        var pe = n.parentElement, ps = getComputedStyle(pe);
        if (ps.textTransform === 'uppercase') t = t.toUpperCase();
        if (oculta && pe.closest('.nome')) t = t.replace(/[^\s]/g, '•');
        var rg2 = document.createRange(); rg2.selectNodeContents(n); var b = rg2.getBoundingClientRect();
        ctx.font = ps.fontWeight + ' ' + (parseFloat(ps.fontSize) * S) + 'px ' + ps.fontFamily;
        ctx.fillStyle = ps.color; ctx.globalAlpha = parseFloat(ps.opacity);
        var ls = ps.letterSpacing === 'normal' ? 0 : parseFloat(ps.letterSpacing) * S;
        texto(ctx, t, X + (b.left - cr.left) * S, Y + (b.top - cr.top + b.height / 2) * S, ls); ctx.globalAlpha = 1;
      }
      // setas
      card.querySelectorAll('svg.ico').forEach(function (sv) {
        var u = sv.querySelector('use'), id = u ? (u.getAttribute('href') || '').replace('#i-', '') : '', d = ICONES[id]; if (!d) return;
        var q = rel(sv); ctx.save(); ctx.translate(q.x, q.y); ctx.scale(q.w / 24, q.h / 24); ctx.strokeStyle = getComputedStyle(sv).color; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.stroke(new Path2D(d)); ctx.restore();
      });
      // logo tom sobre tom, com relevo
      var lr = rel(card.querySelector('.c-logo')), esc0 = Math.min(lr.w / logo.width, lr.h / logo.height), lw = logo.width * esc0, lh = logo.height * esc0;
      var of = document.createElement('canvas'); of.width = Math.ceil(lw); of.height = Math.ceil(lh); var oc = of.getContext('2d');
      oc.drawImage(logo, 0, 0, lw, lh); oc.globalCompositeOperation = 'source-in';
      var cl = LOGO[tier] || LOGO[''], lg = oc.createLinearGradient(0, 0, lw * .35, lh); lg.addColorStop(0, cl[0]); lg.addColorStop(.55, cl[1]); lg.addColorStop(1, cl[2]); oc.fillStyle = lg; oc.fillRect(0, 0, lw, lh);
      var lx = lr.x + (lr.w - lw) / 2, ly = lr.y + (lr.h - lh) / 2;
      ctx.save(); ctx.shadowColor = 'rgba(255,255,255,.55)'; ctx.shadowOffsetY = 1 * S; ctx.drawImage(of, lx, ly); ctx.restore();
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.28)'; ctx.shadowOffsetY = -1 * S; ctx.drawImage(of, lx, ly); ctx.restore();
      // borda interna clara
      ctx.save(); pathCartao(ctx, X + S, Y + S, W - 2 * S, H - 2 * S, S); ctx.lineWidth = 2 * S; ctx.strokeStyle = tier === 't-destaque' ? '#F7B500' : 'rgba(255,255,255,.35)'; ctx.stroke(); ctx.restore();
      return new Promise(function (ok, erro) { try { cv.toBlob(function (bl) { bl ? ok(bl) : erro(new Error('falha ao gerar a imagem')); }, 'image/png'); } catch (e) { erro(e); } });
    }).then(function (bl) { host.remove(); return bl; }, function (e) { host.remove(); throw e; });
  }
  function nomeArquivo(a, ms) {
    var u = ms[ms.length - 1], t = String(a.nome).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return 'cartinha-' + t + '-' + String(u.mes).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.png';
  }
  /* modo: 'baixar' | 'whatsapp'. Devolve uma frase para mostrar à pessoa. */
  function enviar(a, ms, modo, opcoes) {
    opcoes = opcoes || {};
    var u = ms[ms.length - 1], nome = opcoes.ocultarNomes ? 'Minha cartinha' : 'Cartinha de ' + a.nome;
    var texto = nome + ' — nota ' + f1(u.pontos) + ' em ' + u.mes + ' (Sentinela, Prefeitura de Ponta Porã)';
    return png(a, ms, opcoes).then(function (bl) {
      var arq = new File([bl], nomeArquivo(a, ms), { type: 'image/png' });
      var baixar = function () { var l = document.createElement('a'); l.href = URL.createObjectURL(bl); l.download = arq.name; document.body.appendChild(l); l.click(); setTimeout(function () { URL.revokeObjectURL(l.href); l.remove(); }, 800); };
      if (modo === 'baixar') { baixar(); return 'Imagem baixada. Procure em “Downloads”.'; }
      if (navigator.canShare && navigator.canShare({ files: [arq] }) && navigator.share) {
        return navigator.share({ files: [arq], title: nome, text: texto }).then(function () { return 'Pronto! Escolha o WhatsApp na lista que abriu.'; },
          function (e) { return e && e.name === 'AbortError' ? 'Envio cancelado.' : (baixar(), 'Não consegui abrir o compartilhamento; a imagem foi baixada. Anexe no WhatsApp.'); });
      }
      baixar(); window.open('https://wa.me/?text=' + encodeURIComponent(texto), '_blank', 'noopener');
      return 'Baixei a imagem e abri o WhatsApp. Anexe a imagem na conversa (clipe ou +).';
    });
  }
  window.Carta = { html: html, medidas: medidas, NOMES: NOMES, png: png, enviar: enviar, nomeArquivo: nomeArquivo };
})();
