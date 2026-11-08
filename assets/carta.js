/* Cartão do agente (estilo carta de jogador). Usado em agente.html e album.html.
   Carta.html(agente, mesesAteOMesEscolhido) -> HTML do cartão ('' se não houver nota). */
(function () {
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); };
  var CID = 0, REG = {};
  var f1 = function (n) { return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); };
  var SV = function (n) { return '<svg class="ico" aria-hidden="true"><use href="#i-' + n + '"/></svg>'; };
  var NOMES = { ASS: 'Assiduidade', TUR: 'Turnos cobertos', CON: 'Consistência', EVO: 'Evolução', POS: 'Posição', MED: 'Média dos meses' };
  /* Nota "bruta": a nota oficial é limitada a 100, mas 100 + critérios pode passar (ex.: 110,6). Só vale para quem chegou ao teto; os demais usam a nota oficial.
     Entre quem está no teto, o ranking do cartão e do álbum ordena pela bruta (depois a média dos meses anteriores, depois a posição oficial). */
  var r1 = function (n) { return Math.round(n * 10) / 10; };
  function bruta(u) {
    if (!u || u.pontos == null) return null;
    if (u.pontos < 99.95 || !u.detalhe || !u.detalhe.length) return u.pontos;
    return Math.max(100, r1(100 + u.detalhe.reduce(function (t, x) { return t + x[3]; }, 0)));
  }
  var POSMES = {};
  function mapaPos(mes) {
    if (POSMES[mes]) return POSMES[mes];
    var ag = (window.AGENTES_DADOS && window.AGENTES_DADOS.agentes) || {}, L = [];
    Object.keys(ag).forEach(function (k) {
      var ms = ag[k].meses || [], i = -1; ms.forEach(function (m, j) { if (m.mes === mes) i = j; });
      if (i < 0 || ms[i].pontos == null) return;
      var v = ms.slice(0, i).map(function (m) { return m.pontos; }).filter(function (n) { return n != null; });
      L.push({ k: k, b: bruta(ms[i]), h: v.length ? r1(v.reduce(function (t, n) { return t + n; }, 0) / v.length) : -1, p: ms[i].pos, n: String(ag[k].nome) });
    });
    L.sort(function (x, y) { return y.b - x.b || y.h - x.h || x.p - y.p || x.n.localeCompare(y.n, 'pt-BR'); });
    var mp = {}; L.forEach(function (l, i) { mp[l.k] = i + 1; }); return (POSMES[mes] = mp);
  }
  function posicao(u, id) { // posição mostrada: só muda para quem está no teto de 100
    if (id == null || !u || u.pontos == null || u.pontos < 99.95) return u ? u.pos : null;
    return mapaPos(u.mes)[String(id)] || u.pos;
  }
  function medidas(ms, id) {
    var u = ms[ms.length - 1]; if (!u || u.pontos == null) return null;
    var ant = ms.length > 1 ? ms[ms.length - 2] : null;
    var cl = function (v) { return Math.max(0, Math.min(99, Math.round(v))); };
    var notas = ms.map(function (m) { return m.pontos; }).filter(function (v) { return v != null; });
    var media = notas.reduce(function (t, v) { return t + v; }, 0) / notas.length;
    // Consistência: desvio-padrão das notas dos TRÊS ÚLTIMOS meses do período mostrado (hoje, agosto a outubro; acompanha o mês escolhido). Quanto menor a variação, maior o CON (máx. 99).
    var rec = notas.slice(-3), mrec = rec.reduce(function (t, v) { return t + v; }, 0) / rec.length;
    var dp = rec.length > 1 ? Math.sqrt(rec.reduce(function (t, v) { return t + Math.pow(v - mrec, 2); }, 0) / rec.length) : 0;
    var delta = ant && ant.pontos != null ? u.pontos - ant.pontos : null;
    var st = [['ASS', u.esp ? cl(u.trab / u.esp * 100) : 0], ['TUR', u.esp ? cl(100 - (u.turnos_sem || 0) / (u.esp * 2) * 100) : 0],
      ['CON', cl(100 - 5 * dp)], ['EVO', delta == null ? 50 : cl(50 + 5 * delta)],
      ['POS', u.total > 1 ? cl((u.total - posicao(u, id)) / (u.total - 1) * 100) : 99], ['MED', cl(media)]];
    // Escala única, pela nota ARREDONDADA (a que aparece no cartão): a cor do cartão e a borda seguem a mesma faixa.
    // LENDÁRIA (tempestade) = só o TOP 3 com nota 100 | 90-99 e demais 100 = OURO | 80-89 PRATA | 70-79 BRONZE | 60-69 AÇO | abaixo de 60 FERRO.
    // Top 3 do mês com 90-99 (quando há menos de 3 agentes com 100) ganha o cartão de ouro com borda holográfica ("DESTAQUE").
    // A posição vem de posicao() (para quem está no teto, ordenada pela nota bruta).
    var r = Math.round(u.pontos), pos3 = posicao(u, id) <= 3, lend = r >= 100 && pos3, top3 = r >= 90 && r < 100 && pos3;
    var tier = lend ? ['', 'LENDÁRIA'] : top3 ? ['', 'DESTAQUE'] : r >= 90 ? ['', 'OURO'] : r >= 80 ? ['t-prata', 'PRATA'] : r >= 70 ? ['t-bronze', 'BRONZE'] : r >= 60 ? ['t-aco', 'AÇO'] : ['t-ferro', 'FERRO'];
    var borda = lend ? 'b-100' : top3 ? 'b-top' : r >= 90 ? 'b-90' : r >= 80 ? 'b-80' : r >= 70 ? 'b-70' : r >= 60 ? 'b-60' : 'b-0';
    return { u: u, delta: delta, st: st, tier: tier, borda: borda };
  }
  /* Cartinha 100: estrelas [x, y, raio] no espaço 272x392 do cartão (usadas no HTML e no PNG) */
  var ESTRELA = 'M0-1Q.15-.15 1 0Q.15.15 0 1Q-.15.15-1 0Q-.15-.15 0-1Z';
  /* Cartinha 100 ("Tempestade"): raios gerados uma vez (sempre iguais) no espaço 272x392 do cartão; servem ao HTML (SVG) e ao PNG (canvas).
     RAIOS = descargas no fundo, saindo da foto e pelas laterais; ARCOS = faíscas em zigue-zague correndo pela borda; FAISCAS = pontinhos de luz. */
  var RAIOS = [], ARCOS = [], FAISCAS = []; // RAIOS = [caminho, espessura relativa]
  (function () {
    var sd = 23; function q() { sd = (sd * 16807) % 2147483647; return sd / 2147483647; }
    function pts(x1, y1, x2, y2, disp, n) {
      var p = [[x1, y1], [x2, y2]];
      for (var k = 0; k < n; k++) { var np = [p[0]]; for (var i = 0; i < p.length - 1; i++) { var a = p[i], b = p[i + 1], dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1, o = (q() - .5) * disp; np.push([(a[0] + b[0]) / 2 - dy / l * o, (a[1] + b[1]) / 2 + dx / l * o], b); } p = np; disp /= 2; }
      return p;
    }
    var d = function (p) { return 'M' + p.map(function (v) { return v[0].toFixed(1) + ' ' + v[1].toFixed(1); }).join('L'); };
    // descarga com ramificações recursivas: cada galho sai de um ponto do tronco, mais curto e mais fino
    function raio(x1, y1, x2, y2, disp, w, prof) {
      var p = pts(x1, y1, x2, y2, disp, 5); RAIOS.push([d(p), w]);
      if (prof <= 0) return;
      var ang = Math.atan2(y2 - y1, x2 - x1), len = Math.hypot(x2 - x1, y2 - y1);
      [.3, .55, .78].forEach(function (f) {
        if (q() < .25) return;
        var m = p[Math.floor(p.length * f)], u = ang + (q() < .5 ? -1 : 1) * (.5 + q() * .5), L = len * (.28 + q() * .22);
        raio(m[0], m[1], m[0] + Math.cos(u) * L, m[1] + Math.sin(u) * L, L * .35, w * .55, prof - 1);
      });
    }
    var CX = 136, CY = 158, R0 = 63;
    // [ângulo (0 = leste, sentido horário), raio final]: troncos saindo da foto, evitando a região dos textos
    [[188, 124], [160, 116], [212, 104], [352, 124], [18, 116], [328, 104], [262, 100], [296, 104], [238, 96]].forEach(function (a) {
      var t = a[0] * Math.PI / 180; raio(CX + Math.cos(t) * R0, CY + Math.sin(t) * R0, CX + Math.cos(t) * a[1], CY + Math.sin(t) * a[1], 20, 1, 2);
    });
    raio(19, 22, 26, 206, 16, .8, 1); raio(253, 122, 249, 262, 16, .8, 1); // descargas rente às laterais
    function zig(x1, y1, x2, y2, amp) { var n = Math.round(Math.hypot(x2 - x1, y2 - y1) / 7), p = []; for (var i = 0; i <= n; i++) { var t = i / n, o = i === 0 || i === n ? 0 : (i % 2 ? 1 : -1) * amp * (.5 + q() * .8); p.push(x1 === x2 ? [x1 + o, y1 + (y2 - y1) * t] : [x1 + (x2 - x1) * t, y1 + o]); } return d(p); }
    ARCOS.push(zig(60, 5.5, 132, 5.5, 3.2), zig(266.5, 140, 266.5, 232, 3.2), zig(88, 386.5, 204, 386.5, 3.2), zig(5.5, 248, 5.5, 338, 3.2), zig(5.5, 80, 5.5, 130, 3.2));
    for (var i = 0; i < 36; i++) FAISCAS.push([16 + q() * 240, 16 + q() * 360, .5 + q() * .9, .35 + q() * .55]);
  })();
  function html(a, ms, id, semRegistro) {
    var m = medidas(ms, id); if (!m) return '';
    var u = m.u, pos = posicao(u, id), delta = m.delta, st = m.st, tier = m.tier;
    var foto = id != null && window.AGENTES_FOTOS ? window.AGENTES_FOTOS[String(id)] : '';
    var cid = ''; if (!semRegistro) { cid = String(++CID); REG[cid] = { a: a, ms: ms, id: id }; }
    var partes = String(a.nome).trim().split(/\s+/), curto = partes.length > 1 ? partes[0] + ' ' + partes[partes.length - 1] : partes[0];
    var ini = (partes[0][0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
    var eq = String(a.equipe).replace(/^Equipe\s*/i, 'EQ ');
    var tend = delta == null ? SV('minus') + ' sem mês anterior' : delta > 0.05 ? SV('arrow-up') + ' +' + f1(delta) + ' pts' : delta < -0.05 ? SV('arrow-down') + ' ' + f1(delta) + ' pts' : SV('minus') + ' estável';
    var extra100 = m.borda !== 'b-100' ? '' : '<svg class="c-estrelas" viewBox="0 0 272 392" preserveAspectRatio="none" aria-hidden="true">' + RAIOS.map(function (r) { return '<g class="rai"><path class="rg" stroke-width="' + (8 * r[1]).toFixed(2) + '" d="' + r[0] + '"/><path class="ry" stroke-width="' + (2.8 * r[1]).toFixed(2) + '" d="' + r[0] + '"/><path class="rw" stroke-width="' + Math.max(.6, 1.2 * r[1]).toFixed(2) + '" d="' + r[0] + '"/></g>'; }).join('') + FAISCAS.map(function (f) { return '<circle cx="' + f[0].toFixed(1) + '" cy="' + f[1].toFixed(1) + '" r="' + f[2].toFixed(2) + '" fill="#CDEBFF" fill-opacity="' + f[3].toFixed(2) + '"/>'; }).join('') + '</svg><svg class="c-arcos" viewBox="0 0 272 392" preserveAspectRatio="none" aria-hidden="true">' + ARCOS.map(function (d) { return '<path class="ag" d="' + d + '"/><path class="aw" d="' + d + '"/>'; }).join('') + '</svg>';
    return '<div class="carta ' + tier[0] + ' ' + m.borda + '"' + (cid ? ' data-cid="' + cid + '"' : '') + ' role="img" aria-label="Cartão de ' + esc(a.nome) + ': nota ' + f1(u.pontos) + ', nível ' + tier[1] + '">' +
      '<div class="c-topo"><div class="c-ovr"><b' + (Math.round(u.pontos) >= 100 ? ' class="tres"' : '') + '>' + Math.round(u.pontos) + '</b><span>NOTA</span></div>' +
      '<div class="c-pos">' + esc(eq) + '<small>' + pos + 'º de ' + u.total + '</small></div><div class="c-logo" aria-hidden="true"><i></i></div></div>' +
      (foto ? '<div class="c-foto tem-foto"><span class="nome">' + esc(ini) + '</span><img src="' + esc(foto) + '" alt=""></div>' : '<div class="c-foto"><span class="nome">' + esc(ini) + '</span></div>') +
      '<div class="c-nome nome"' + (curto.length > 20 ? ' style="font-size:1.05rem"' : curto.length > 15 ? ' style="font-size:1.08rem"' : '') + '>' + esc(curto) + '</div>' +
      '<div class="c-stats">' + st.map(function (x) { return '<div style="--v:' + x[1] + '%"><b>' + x[1] + '</b><span>' + x[0] + '</span></div>'; }).join('') + '</div>' +
      '<div class="c-rodape"><span>' + esc(u.mes) + ' · ' + tier[1] + '</span><span>' + tend + '</span></div>' + extra100 + '<i class="c-brilho" aria-hidden="true"></i>' + (m.borda === 'b-90' || m.borda === 'b-top' || m.borda === 'b-100' ? '<i class="c-glitter" aria-hidden="true"></i>' : '') + '<i class="c-borda" aria-hidden="true"></i></div>';
  }

  /* ---- Imagem do cartão (PNG) para baixar ou mandar pelo WhatsApp ---- */
  var LOGO = { 'b-100': ['#FFF6C8', '#FFD84A', '#E09800'], '': ['#D4B040', '#9A7218', '#5C4208'], 't-prata': ['#C0CEDC', '#7A8FA8', '#3A4E66'], 't-bronze': ['#D08A48', '#9A521C', '#5C2E0A'], 't-aco': ['#8AA8A2', '#4E6E68', '#2A3E3A'], 't-ferro': ['#B0B0B0', '#686868', '#2E2E2E'], 't-destaque': ['#FFE8A0', '#F0B400', '#B07800'] };
  var ICONES = { 'arrow-up': 'M12 19V5M6 11l6-6 6 6', 'arrow-down': 'M12 5v14M6 13l6 6 6-6', 'minus': 'M5 12h14' };
  function carregar(src) { return new Promise(function (ok, erro) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = erro; i.src = src; }); }
  function gradCss(ctx, ang, x, y, w, h, c1, c2) {
    var a = ang * Math.PI / 180, dx = Math.sin(a), dy = -Math.cos(a), L = Math.abs(w * dx) + Math.abs(h * dy), cx = x + w / 2, cy = y + h / 2;
    var g = ctx.createLinearGradient(cx - dx * L / 2, cy - dy * L / 2, cx + dx * L / 2, cy + dy * L / 2); g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
  }
  var FORMA = [[20, 0], [252, 0], [272, 20], [272, 366], [242, 392], [30, 392], [0, 366], [0, 20]]; // escudo no espaço 272x392 (igual ao clip-path do CSS)
  function pathCartao(ctx, x, y, w, h, S, d, continuar) { // d = recuo (quem chama já passa o retângulo encolhido em d); continuar = não reiniciar o caminho
    d = d || 0; x -= d; y -= d; w += 2 * d; h += 2 * d; var n = FORMA.length;
    // cantos de baixo ancorados na base (altura fixa em px do cartão), como no CSS
    var P = FORMA.map(function (p) { return [p[0] === 272 ? w : (p[0] > 136 ? w - (272 - p[0]) * S : p[0] * S), p[1] > 196 ? h - (392 - p[1]) * S : p[1] * S]; });
    if (d) P = P.map(function (p, i) {
      var a = P[(i + n - 1) % n], c = P[(i + 1) % n];
      function nr(u, v) { var dx = v[0] - u[0], dy = v[1] - u[1], l = Math.hypot(dx, dy); return [-dy / l, dx / l]; }
      var n1 = nr(a, p), n2 = nr(p, c), k = 1 / (1 + n1[0] * n2[0] + n1[1] * n2[1]);
      return [p[0] + (n1[0] + n2[0]) * k * d, p[1] + (n1[1] + n2[1]) * k * d];
    });
    if (!continuar) ctx.beginPath(); ctx.moveTo(x + P[0][0], y + P[0][1]);
    for (var i = 1; i < n; i++) ctx.lineTo(x + P[i][0], y + P[i][1]);
    ctx.closePath();
  }
  function texto(ctx, txt, x, y, ls) { // letra a letra, para respeitar o espaçamento entre letras em qualquer navegador
    if (!ls) { ctx.fillText(txt, x, y); return; }
    for (var i = 0; i < txt.length; i++) { ctx.fillText(txt[i], x, y); x += ctx.measureText(txt[i]).width + ls; }
  }
  function png(a, ms, opcoes) {
    opcoes = opcoes || {};
    var S = 2, M = 20, host = document.createElement('div'), html0 = html(a, ms, opcoes.id, true);
    if (!html0) return Promise.reject(new Error('sem nota'));
    host.style.cssText = 'position:fixed;left:-9999px;top:0;width:272px;pointer-events:none'; host.innerHTML = html0; document.body.appendChild(host);
    var card = host.firstElementChild, tier = (card.className.match(/t-\w+/) || [''])[0];
    var oculta = !!opcoes.ocultarNomes, is100 = card.classList.contains('b-100');
    if (opcoes.ocultarFoto) { var im0 = card.querySelector('.c-foto img'); if (im0) im0.remove(); } // sem foto: ficam as iniciais
    var imgFoto = card.querySelector('.c-foto img'), pronto = Promise.all([document.fonts ? document.fonts.ready : 0, document.fonts ? document.fonts.load('700 20px "Barlow Semi Condensed"') : 0, document.fonts ? document.fonts.load('600 14px "IBM Plex Sans"') : 0, carregar('assets/logo_carta.png'), imgFoto && !opcoes.ocultarFoto ? carregar(imgFoto.getAttribute('src')).catch(function () { return null; }) : null]);
    return pronto.then(function (r) {
      var logo = r[3], cr = card.getBoundingClientRect(), W = cr.width * S, H = cr.height * S;
      var cv = document.createElement('canvas'); cv.width = Math.round(W + 2 * M * S); cv.height = Math.round(H + 2 * M * S);
      var ctx = cv.getContext('2d'), cs = getComputedStyle(card), c1 = cs.getPropertyValue('--c1').trim(), c2 = cs.getPropertyValue('--c2').trim(), ln = cs.getPropertyValue('--ln').trim();
      var X = M * S, Y = M * S;
      ctx.fillStyle = '#EEF2F8'; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.30)'; ctx.shadowBlur = 28 * S; ctx.shadowOffsetY = 10 * S; pathCartao(ctx, X, Y, W, H, S); ctx.fillStyle = c2; ctx.fill(); ctx.restore();
      pathCartao(ctx, X, Y, W, H, S); ctx.save(); ctx.clip();
      ctx.fillStyle = gradCss(ctx, 155, X, Y, W, H, c1, c2); ctx.fillRect(X, Y, W, H);
      var fr100 = is100 ? (function () { var b = card.querySelector('.c-foto').getBoundingClientRect(); return { cx: X + (b.left - cr.left + b.width / 2) * S, cy: Y + (b.top - cr.top + b.height / 2) * S }; })() : null;
      if (is100) {
        // clarão azul atrás da foto (radial-gradient do ::after do CSS)
        var cx0 = X + W * .5, cy0 = Y + H * .4, R0 = Math.max(Math.hypot(cx0 - X, cy0 - Y), Math.hypot(X + W - cx0, cy0 - Y), Math.hypot(cx0 - X, Y + H - cy0), Math.hypot(X + W - cx0, Y + H - cy0)) * .55, g0 = ctx.createRadialGradient(cx0, cy0, 0, cx0, cy0, R0);
        g0.addColorStop(0, 'rgba(120,190,255,.6)'); g0.addColorStop(1, 'rgba(60,130,255,0)'); ctx.fillStyle = g0; ctx.fillRect(X, Y, W, H);
        // raios: halo azul, miolo ciano e núcleo branco; a espessura de cada galho vem de r[1]
        ctx.save(); ctx.translate(X, Y); ctx.scale(W / 272, H / 392); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        RAIOS.forEach(function (r) {
          var pa = new Path2D(r[0]);
          ctx.save(); ctx.strokeStyle = 'rgba(61,155,255,.55)'; ctx.lineWidth = 8 * r[1]; ctx.shadowColor = '#3D9BFF'; ctx.shadowBlur = 12 * S; ctx.stroke(pa); ctx.restore();
          ctx.save(); ctx.strokeStyle = '#8FD8FF'; ctx.lineWidth = 2.8 * r[1]; ctx.shadowColor = '#59B8FF'; ctx.shadowBlur = 7 * S; ctx.stroke(pa); ctx.restore();
          ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = Math.max(.6, 1.2 * r[1]); ctx.stroke(pa);
        });
        FAISCAS.forEach(function (f) { ctx.globalAlpha = f[3]; ctx.fillStyle = '#CDEBFF'; ctx.beginPath(); ctx.arc(f[0], f[1], f[2], 0, 2 * Math.PI); ctx.fill(); });
        ctx.restore();
        // filete interno (::before do CSS: 13px para dentro)
        ctx.save(); pathCartao(ctx, X + 13 * S, Y + 13 * S, W - 26 * S, H - 26 * S, S, 13 * S); ctx.lineWidth = 1.5 * S; ctx.strokeStyle = '#DDF2FF'; ctx.shadowColor = '#59B8FF'; ctx.shadowBlur = 8 * S; ctx.stroke(); ctx.shadowBlur = 0; ctx.stroke(); ctx.restore();
      } else {
        // listras
        ctx.save(); ctx.translate(X + W / 2, Y + H / 2); ctx.rotate((115 - 90) * Math.PI / 180);
        ctx.fillStyle = tier === 't-destaque' ? 'rgba(25,184,163,.16)' : 'rgba(255,255,255,.14)';
        for (var k = -Math.ceil(W + H); k < W + H; k += 34 * S) ctx.fillRect(k, -(W + H), 14 * S, 2 * (W + H));
        ctx.restore();
        // brilho
        var gx = X + (-0.30 * W) + 0.45 * W, gy = Y + (-0.40 * H) + 0.45 * H, rr = Math.min(.9 * W, .9 * H) / 2;
        var rg = ctx.createRadialGradient(gx, gy, 0, gx, gy, rr); rg.addColorStop(0, 'rgba(255,255,255,.55)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = rg; ctx.fillRect(X, Y, W, H);
      }
      ctx.restore();
      var rel = function (e) { var b = e.getBoundingClientRect(); return { x: X + (b.left - cr.left) * S, y: Y + (b.top - cr.top) * S, w: b.width * S, h: b.height * S }; };
      // foto (círculo)
      var f = card.querySelector('.c-foto'), fr = rel(f), fs = getComputedStyle(f), bw = parseFloat(fs.borderTopWidth) * S;
      if (is100) { // anel dourado externo + brilho (box-shadow do CSS)
        ctx.save(); ctx.shadowColor = 'rgba(89,184,255,.85)'; ctx.shadowBlur = 24 * S; ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, fr.w / 2 + 2.5 * S, 0, 2 * Math.PI);
        ctx.lineWidth = 5 * S; ctx.strokeStyle = 'rgba(190,230,255,.95)'; ctx.stroke(); ctx.restore();
      }
      ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, fr.w / 2 - bw / 2, 0, 2 * Math.PI); ctx.fillStyle = fs.backgroundColor; ctx.fill();
      var ft = r[4];
      if (ft) { // foto recortada em círculo (object-fit: cover, ancorada em 50% 30%)
        var ds = fr.w - 2 * bw, k = Math.max(ds / ft.width, ds / ft.height), dw = ft.width * k, dh = ft.height * k;
        ctx.save(); ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, ds / 2, 0, 2 * Math.PI); ctx.clip();
        ctx.drawImage(ft, fr.x + bw - (dw - ds) * .5, fr.y + bw - (dh - ds) * .3, dw, dh); ctx.restore();
      }
      ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, fr.w / 2 - bw / 2, 0, 2 * Math.PI); ctx.lineWidth = bw; ctx.strokeStyle = ln; ctx.stroke();
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
        if (r[4] && pe.closest('.c-foto')) continue; // a foto cobre as iniciais
        if (ps.textTransform === 'uppercase') t = t.toUpperCase();
        if (oculta && pe.closest('.nome')) t = t.replace(/[^\s]/g, '•');
        var rg2 = document.createRange(); rg2.selectNodeContents(n); var b = rg2.getBoundingClientRect();
        ctx.font = ps.fontWeight + ' ' + (parseFloat(ps.fontSize) * S) + 'px ' + ps.fontFamily;
        ctx.fillStyle = ps.color; ctx.globalAlpha = parseFloat(ps.opacity); ctx.shadowColor = 'rgba(0,0,0,0)';
        if (is100 && pe.matches('.c-ovr b')) { // número com folha de ouro
          var og = ctx.createLinearGradient(0, Y + (b.top - cr.top) * S, 0, Y + (b.bottom - cr.top) * S); og.addColorStop(0, '#FFFFFF'); og.addColorStop(.55, '#FFE14D'); og.addColorStop(1, '#F5A300');
          ctx.fillStyle = og; ctx.shadowColor = 'rgba(61,155,255,.9)'; ctx.shadowBlur = 6 * S; ctx.shadowOffsetY = 0;
        }
        var ls = ps.letterSpacing === 'normal' ? 0 : parseFloat(ps.letterSpacing) * S;
        texto(ctx, t, X + (b.left - cr.left) * S, Y + (b.top - cr.top + b.height / 2) * S, ls); ctx.globalAlpha = 1; ctx.shadowColor = 'rgba(0,0,0,0)'; ctx.shadowOffsetY = 0; ctx.shadowBlur = 0;
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
      var cl = LOGO[is100 ? 'b-100' : tier] || LOGO[''], lg = oc.createLinearGradient(0, 0, lw * .35, lh); lg.addColorStop(0, cl[0]); lg.addColorStop(.55, cl[1]); lg.addColorStop(1, cl[2]); oc.fillStyle = lg; oc.fillRect(0, 0, lw, lh);
      var lx = lr.x + (lr.w - lw) / 2, ly = lr.y + (lr.h - lh) / 2;
      ctx.save(); ctx.shadowColor = 'rgba(255,255,255,.55)'; ctx.shadowOffsetY = 1 * S; ctx.drawImage(of, lx, ly); ctx.restore();
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.28)'; ctx.shadowOffsetY = -1 * S; ctx.drawImage(of, lx, ly); ctx.restore();
      // borda interna clara
      ctx.save(); pathCartao(ctx, X + S, Y + S, W - 2 * S, H - 2 * S, S); ctx.lineWidth = 2 * S; ctx.strokeStyle = tier === 't-destaque' ? '#F7B500' : 'rgba(255,255,255,.35)'; ctx.stroke(); ctx.restore();
      // borda por faixa de nota (anel com degradê, igual ao CSS .c-borda)
      var B = (parseFloat(cs.getPropertyValue('--bw')) || 5) * S, bc = [cs.getPropertyValue('--b1').trim(), cs.getPropertyValue('--b2').trim(), cs.getPropertyValue('--b3').trim()];
      var bg = gradCss(ctx, 135, X, Y, W, H, bc[0], bc[0]); bg.addColorStop(.25, bc[1]); bg.addColorStop(.5, bc[2]); bg.addColorStop(.75, bc[1]);
      ctx.save(); ctx.beginPath(); pathCartao(ctx, X, Y, W, H, S, 0, true); pathCartao(ctx, X + B, Y + B, W - 2 * B, H - 2 * B, S, B, true); ctx.fillStyle = bg; ctx.fill('evenodd'); ctx.restore();
      if (is100) { // faíscas correndo pela borda (por cima do anel)
        ctx.save(); ctx.translate(X, Y); ctx.scale(W / 272, H / 392); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        ARCOS.forEach(function (d) { var pa = new Path2D(d);
          ctx.save(); ctx.strokeStyle = 'rgba(120,205,255,.85)'; ctx.lineWidth = 3.4; ctx.shadowColor = '#59B8FF'; ctx.shadowBlur = 8 * S; ctx.stroke(pa); ctx.restore();
          ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 1; ctx.stroke(pa); });
        ctx.restore();
      }
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

  /* ---- Detalhamento ao passar o mouse / clicar na cartinha ----
     Mostra os critérios que formaram a nota do mês (mesma tabela "Detalhamento — Critérios Aplicados por Agente" do dashboard)
     e a média dos meses anteriores, que é o critério de desempate do ranking. */
  var fn = function (n) { return Number(n).toLocaleString('pt-BR', { maximumFractionDigits: 2 }); };
  var sg = function (n) { return (n > 0 ? '+' : n < 0 ? '−' : '') + f1(Math.abs(n)); };
  function detalheHtml(reg) {
    var a = reg.a, ms = reg.ms, u = ms[ms.length - 1], det = u.detalhe, linhas;
    if (det && det.length) { // [critério, quantidade, peso, pontos]: ganhos (maiores primeiro) e depois perdas (maiores primeiro)
      var ord = det.slice().sort(function (x, y) { return (y[3] > 0) - (x[3] > 0) || Math.abs(y[3]) - Math.abs(x[3]); });
      linhas = ord.map(function (x) { return '<tr><td>' + esc(x[0]) + '</td><td class="n">' + (x[1] == null ? '' : fn(x[1])) + '</td><td class="n">' + (x[2] == null ? '' : fn(x[2])) + '</td><td class="n ' + (x[3] < 0 ? 'neg' : 'pos') + '">' + sg(x[3]) + '</td></tr>'; }).join('');
    } else {
      linhas = (u.ganhos || []).concat(u.perdas || []).map(function (x) { return '<tr><td>' + esc(x.c) + '</td><td class="n"></td><td class="n"></td><td class="n ' + (x.p < 0 ? 'neg' : 'pos') + '">' + sg(x.p) + '</td></tr>'; }).join('');
    }
    var soma = det && det.length ? det.reduce(function (t, x) { return t + x[3]; }, 0) : null, nota = Math.round(u.pontos * 10) / 10;
    var total = soma == null ? null : 100 + soma;
    var obs = total == null ? '' : total > 100.05 ? ' <small>(a nota é limitada a 100)</small>' : (total < -0.05 ? ' <small>(a nota mínima é 0)</small>' : (Math.abs(total - nota) > 0.15 ? ' <small>(com ajustes do período, ex.: presença mínima)</small>' : ''));
    var ant = ms.slice(0, -1).map(function (m) { return m.pontos; }).filter(function (v) { return v != null; });
    var mh = ant.length ? ant.reduce(function (t, v) { return t + v; }, 0) / ant.length : null;
    var link = reg.id != null && !/agente\.html$/.test(location.pathname) ? '<a class="c-pop-link" href="agente.html?id=' + encodeURIComponent(reg.id) + '&mes=' + encodeURIComponent(u.mes) + '">Ver evolução do agente →</a>' : '';
    return '<div class="c-pop-topo"><div><b class="nome">' + esc(a.nome) + '</b><span>' + esc(u.mes) + ' · ' + posicao(u, reg.id) + 'º de ' + u.total + '</span></div><button type="button" data-fechar aria-label="Fechar">×</button></div>' +
      '<table><thead><tr><th>Critério</th><th class="n">Qtd</th><th class="n">Peso</th><th class="n">Pontos</th></tr></thead><tbody>' +
      '<tr class="base"><td>Pontos iniciais</td><td></td><td></td><td class="n">100,0</td></tr>' + linhas + '</tbody>' +
      '<tfoot>' + (total == null ? '' : '<tr><td colspan="3">Total (100 + critérios)</td><td class="n">' + f1(total) + '</td></tr>') +
      '<tr class="final"><td colspan="3">Nota final' + obs + '</td><td class="n">' + f1(u.pontos) + '</td></tr></tfoot></table>' +
      '<p class="c-pop-desempate">' + (mh == null ? 'Sem meses anteriores: não há média para desempate.' : 'Média dos meses anteriores: <b>' + f1(mh) + '</b> (usada no desempate quando duas notas são iguais).') + '</p>' + link;
  }
  var pop = null, atual = null, fixo = false, timer = 0;
  function elPop() {
    if (pop) return pop;
    pop = document.createElement('div'); pop.className = 'c-pop'; pop.hidden = true; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', 'Detalhamento da nota');
    pop.addEventListener('mouseenter', function () { clearTimeout(timer); });
    pop.addEventListener('mouseleave', function () { if (!fixo) agendar(); });
    pop.addEventListener('click', function (e) { if (e.target.closest('[data-fechar]')) fechar(); });
    document.body.appendChild(pop); return pop;
  }
  function fechar() { clearTimeout(timer); fixo = false; atual = null; if (pop) pop.hidden = true; }
  function agendar() { clearTimeout(timer); timer = setTimeout(function () { if (!fixo) fechar(); }, 220); }
  function abrir(card, travar) {
    var reg = REG[card.getAttribute('data-cid')]; if (!reg || !medidas(reg.ms)) return;
    var el = elPop(); clearTimeout(timer); atual = card; fixo = !!travar;
    el.innerHTML = detalheHtml(reg); el.hidden = false; el.classList.toggle('fixo', fixo);
    var estreito = window.innerWidth < 720; el.classList.toggle('folha', estreito);
    if (estreito) { el.style.left = el.style.top = ''; return; }
    var r = card.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight, x = r.right + 10;
    if (x + w > window.innerWidth - 8) x = r.left - w - 10;
    if (x < 8) x = Math.max(8, (window.innerWidth - w) / 2);
    el.style.left = Math.round(x) + 'px'; el.style.top = Math.round(Math.max(8, Math.min(r.top, window.innerHeight - h - 8))) + 'px';
  }
  var cartaDe = function (e) { var t = e.target; return t && t.closest ? t.closest('.carta[data-cid]') : null; };
  document.addEventListener('mouseover', function (e) { if (fixo) return; var c = cartaDe(e); if (c) { clearTimeout(timer); if (c !== atual) abrir(c, false); } });
  document.addEventListener('mouseout', function (e) { if (fixo) return; if (cartaDe(e) && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.c-pop'))) agendar(); });
  document.addEventListener('click', function (e) {
    var c = cartaDe(e);
    if (c) { e.preventDefault(); if (fixo && atual === c) fechar(); else abrir(c, true); }   // clicar na cartinha fixa o detalhamento (no celular, é o toque)
    else if (fixo && !(e.target.closest && e.target.closest('.c-pop'))) fechar();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fechar(); });
  window.addEventListener('scroll', function () { if (!fixo) fechar(); }, true);
  window.Carta = { html: html, medidas: medidas, bruta: bruta, posicao: posicao, NOMES: NOMES, png: png, enviar: enviar, nomeArquivo: nomeArquivo };
})();
