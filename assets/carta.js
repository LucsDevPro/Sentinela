/* Cartão do agente (estilo carta de jogador). Usado em agente.html e album.html.
   Carta.html(agente, mesesAteOMesEscolhido) -> HTML do cartão ('' se não houver nota). */
(function () {
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); };
  var CID = 0, REG = {};
  var f1 = function (n) { return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); };
  var SV = function (n) { return '<svg class="ico" aria-hidden="true"><use href="#i-' + n + '"/></svg>'; };
  var NOMES = { ASS: 'Assiduidade', TUR: 'Turnos cobertos', CON: 'Consistência', EVO: 'Evolução', POS: 'Posição', MED: 'Média dos meses' };
  /* Nota "bruta": até 18/11/2026 a nota oficial era limitada a 100 (meses congelados antes disso ainda trazem 100); aqui se recalcula 100 + critérios (ex.: 110,6) para quem está em 100. Sem teto, a nota oficial já é a real.
     Entre quem está no teto, o ranking do cartão e do álbum ordena pela bruta (depois a média dos meses anteriores, depois a posição oficial). */
  var r1 = function (n) { return Math.round(n * 10) / 10; };
  function bruta(u) {
    if (!u || u.pontos == null) return null;
    if (u.pontos > 100.05) return u.pontos;   // sem teto (desde 19/11/2026): a nota oficial já é a real
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
  /* Posição pela NOTA exibida (empatados na mesma nota dividem o lugar): é a que alimenta a medida POS. Quem tem 100 não pode aparecer com POS baixo só porque
     perdeu o desempate (a nota bruta) para outro 100. A posição mostrada no cartão e o ranking continuam sendo os de posicao(). */
  var POSNOTA = {};
  function posPorNota(u, id) {
    if (id == null || !u || u.mes === 'Média') return u ? u.pos : null;
    if (!POSNOTA[u.mes]) {
      var ag = (window.AGENTES_DADOS && window.AGENTES_DADOS.agentes) || {}, N = {}, mp = {};
      Object.keys(ag).forEach(function (k) { (ag[k].meses || []).forEach(function (m) { if (m.mes === u.mes && m.pontos != null) N[k] = r1(m.pontos); }); });
      Object.keys(N).forEach(function (k) { mp[k] = 1 + Object.keys(N).filter(function (o) { return N[o] > N[k]; }).length; });
      POSNOTA[u.mes] = mp;
    }
    return POSNOTA[u.mes][String(id)] || u.pos;
  }
  function posicao(u, id) { // posição mostrada: só muda para quem está no teto de 100
    if (id == null || !u || u.pontos == null || u.pontos < 99.95) return u ? u.pos : null;
    return mapaPos(u.mes)[String(id)] || u.pos;
  }
  var BANDA = 20;   // distância máxima entre a nota e cada medida do cartão
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
    /* COERÊNCIA COM A NOTA: as seis medidas nunca ficam mais de BANDA pontos longe da nota do cartão (um 100 não tem medida 50; um 40 não tem medida 95).
       Antes disso as definições já acompanham a nota: EVO parte da nota (não de 50) e POS usa o lugar pela nota (empate em 100 = mesmo lugar). */
    var nr = cl(u.pontos), gb = function (v) { return Math.max(Math.max(0, nr - BANDA), Math.min(Math.min(99, nr + BANDA), v)); };
    var st = [['ASS', u.esp ? cl(u.trab / u.esp * 100) : 0], ['TUR', u.esp ? cl(100 - (u.turnos_sem || 0) / (u.esp * 2) * 100) : 0],
      ['CON', u.con != null ? u.con : cl(100 - 5 * dp)], ['EVO', u.evo != null ? u.evo : delta == null ? cl(u.pontos) : cl(u.pontos + 5 * delta)],
      ['POS', u.total > 1 ? cl((u.total - posPorNota(u, id)) / (u.total - 1) * 100) : 99], ['MED', cl(media)]].map(function (x) { return [x[0], gb(x[1])]; });
    // Escala única, pela nota ARREDONDADA (a que aparece no cartão): a cor do cartão e a borda seguem a mesma faixa.
    // LENDÁRIA (tempestade) = só o TOP 3 com nota ≥ 100 | demais ≥ 100 = ELITE (ouro + brilho) | 90-99 = OURO | 80-89 PRATA | 70-79 BRONZE | 60-69 AÇO | abaixo de 60 FERRO.
    // Top 3 do mês com 90-99 (quando há menos de 3 agentes com 100 ou mais) ganha o cartão roxo com borda holográfica ("DESTAQUE").
    // A posição vem de posicao() (para quem está no teto, ordenada pela nota bruta).
    var r = Math.round(u.pontos), pos3 = posicao(u, id) <= 3, lend = r >= 100 && pos3, top3 = r >= 90 && r < 100 && pos3;
    var elite = r >= 100 && !pos3;   // tirou 100 mas ficou fora do pódio: não pode parecer um 90 qualquer
    var tier = lend ? ['', 'LENDÁRIA'] : top3 ? ['', 'DESTAQUE'] : elite ? ['', 'ELITE'] : r >= 90 ? ['', 'OURO'] : r >= 80 ? ['t-prata', 'PRATA'] : r >= 70 ? ['t-bronze', 'BRONZE'] : r >= 60 ? ['t-aco', 'AÇO'] : ['t-ferro', 'FERRO'];
    var borda = lend ? 'b-100' : top3 ? 'b-top' : r >= 90 ? 'b-90' : r >= 80 ? 'b-80' : r >= 70 ? 'b-70' : r >= 60 ? 'b-60' : 'b-0';
    return { u: u, delta: delta, st: st, tier: tier, borda: borda, elite: elite };
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
    var tend = delta == null ? SV('minus') + ' 1º mês' : delta > 0.05 ? SV('arrow-up') + ' +' + f1(delta) + ' pts' : delta < -0.05 ? SV('arrow-down') + ' ' + f1(delta) + ' pts' : SV('minus') + ' estável';
    var extra100 = (m.borda !== 'b-100' && m.borda !== 'b-top') ? '' : '<svg class="c-estrelas" viewBox="0 0 272 392" preserveAspectRatio="none" aria-hidden="true">' + RAIOS.map(function (r) { return '<g class="rai"><path class="rg" stroke-width="' + (8 * r[1]).toFixed(2) + '" d="' + r[0] + '"/><path class="ry" stroke-width="' + (2.8 * r[1]).toFixed(2) + '" d="' + r[0] + '"/><path class="rw" stroke-width="' + Math.max(.6, 1.2 * r[1]).toFixed(2) + '" d="' + r[0] + '"/></g>'; }).join('') + FAISCAS.map(function (f) { return '<circle cx="' + f[0].toFixed(1) + '" cy="' + f[1].toFixed(1) + '" r="' + f[2].toFixed(2) + '" fill="#CDEBFF" fill-opacity="' + f[3].toFixed(2) + '"/>'; }).join('') + '</svg><svg class="c-arcos" viewBox="0 0 272 392" preserveAspectRatio="none" aria-hidden="true">' + ARCOS.map(function (d) { return '<path class="ag" d="' + d + '"/><path class="aw" d="' + d + '"/>'; }).join('') + '</svg><i class=\"c-flash\" aria-hidden=\"true\"></i>';
    return '<div class="c-conj ' + m.borda + (m.elite ? ' n100' : '') + '">' + ornSVG(m.borda, 'atras') + '<div class="carta ' + tier[0] + ' ' + m.borda + (m.elite ? ' n100' : '') + '"' + (cid ? ' data-cid="' + cid + '"' : '') + ' role="img" aria-label="Cartão de ' + esc(a.nome) + ': nota ' + f1(u.pontos) + ', nível ' + tier[1] + '">' +
      '<div class="c-topo"><div class="c-ovr"><b' + (Math.round(u.pontos) >= 100 ? ' class="tres"' : '') + '>' + Math.round(u.pontos) + '</b><span>NOTA</span></div>' +
      '<div class="c-pos"><small>' + pos + 'º · ' + u.total + '</small><span>' + esc(eq) + '</span></div><div class="c-logo" aria-hidden="true"><i></i></div></div>' +
      (foto ? '<div class="c-foto tem-foto"><span class="nome">' + esc(ini) + '</span><img src="' + esc(foto) + '" alt=""></div>' : '<div class="c-foto"><span class="nome">' + esc(ini) + '</span></div>') +
      '<div class="c-nome nome"' + (curto.length > 22 ? ' style="font-size:1.05rem"' : curto.length > 17 ? ' style="font-size:1.14rem"' : '') + '>' + esc(curto) + '</div>' +
      '<div class="c-stats">' + st.map(function (x) { return '<div class="c-chip" style="--v:' + x[1] + '%"><b>' + x[1] + '</b><span>' + x[0] + '</span></div>'; }).join('') + '</div>' +
      '<div class="c-rodape"><span>' + esc(u.mes) + ' · ' + tier[1] + '</span><span>' + tend + '</span></div>' + extra100 + '<i class="c-brilho" aria-hidden="true"></i>' + (m.borda === 'b-90' || m.borda === 'b-top' || m.borda === 'b-100' ? '<i class="c-glitter" aria-hidden="true"></i>' : '') + '<i class="c-borda" aria-hidden="true"></i></div>' + ornSVG(m.borda, 'frente') + '</div>';
  }

  /* ---- Imagem do cartão (PNG) para baixar ou mandar pelo WhatsApp ---- */
  var LOGO = { 'b-100': ['#FFF6C8', '#E8B820', '#A07010'], '': ['#D4B040', '#9A7218', '#5C4208'], 't-prata': ['#C0CEDC', '#7A8FA8', '#3A4E66'], 't-bronze': ['#D08A48', '#9A521C', '#5C2E0A'], 't-aco': ['#8AA8A2', '#4E6E68', '#2A3E3A'], 't-ferro': ['#B0B0B0', '#686868', '#2E2E2E'], 't-destaque': ['#FFE0F0', '#FF6BCB', '#9B2BC7'] };
  var ICONES = { 'arrow-up': 'M12 19V5M6 11l6-6 6 6', 'arrow-down': 'M12 5v14M6 13l6 6 6-6', 'minus': 'M5 12h14' };
  function carregar(src) { return new Promise(function (ok, erro) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = erro; i.src = src; }); }
  function gradCss(ctx, ang, x, y, w, h, c1, c2) {
    var a = ang * Math.PI / 180, dx = Math.sin(a), dy = -Math.cos(a), L = Math.abs(w * dx) + Math.abs(h * dy), cx = x + w / 2, cy = y + h / 2;
    var g = ctx.createLinearGradient(cx - dx * L / 2, cy - dy * L / 2, cx + dx * L / 2, cy + dy * L / 2); g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
  }
  /* Retângulo arredondado 272×392 (raio 18) — alinhado ao CSS; mais estável no PNG/vídeo que o escudo. */
  var FORMA_R = 18;
  /* ---------- Moldura premium (louros, aletas, cristais, coroa e gema) ----------
     As peças ficam FORA do contorno da cartinha (no espaço 272x392 do cartão, com 20-26 px de folga), por isso vão num conjunto
     .c-conj: uma camada atrás do cartão e outra na frente. A mesma lista de peças alimenta o SVG da tela e o canvas do PNG. */
  var ORN_PAL = { 'b-80': ['#F4F8FF', '#9AA8BD', '#59667A'], 'b-90': ['#FFF3B0', '#F2B81C', '#8A5A00'], 'b-top': ['#FFE5F6', '#FF5BC8', '#6B2BD9'], 'b-100': ['#FFFBE6', '#F0C830', '#8A6010'] };
  function ornPecas(borda) {
    var atras = [], frente = [], n, i, lado, t;
    function espelha(pts) { return pts.map(function (q) { return [272 - q[0], q[1]]; }); }
    if (borda === 'b-80') { // prata: uma aleta de cada lado, colada na lateral reta do escudo (x=0, y 202→356) e com as pontas em 45°
      var f = [[0, 200], [-12, 214], [-12, 344], [0, 358]]; atras.push({ t: 'poly', pts: f }, { t: 'poly', pts: espelha(f) });
    }
    if (borda === 'b-90') { // ouro: dois ramos de louro que ACOMPANHAM o contorno do cartão arredondado (a ~11 px de fora; canto = arco de raio 29 centrado em (18,374)), da gema até a altura do ombro
      /* haste = caminho paralelo à borda: fundo reto → canto em arco → lateral reta. Folhas amostradas por distância ao longo dela. */
      var haste = [[112, 403], [60, 403], [30, 403], [18, 403], [7.0, 401.0], [-2.5, 394.5], [-9.1, 385.2], [-11, 374], [-11, 300], [-11, 230], [-11, 176]], seg = [], tot = 0;
      for (i = 1; i < haste.length; i++) { var sl = Math.hypot(haste[i][0] - haste[i - 1][0], haste[i][1] - haste[i - 1][1]); seg.push(sl); tot += sl; }
      n = 17;
      for (lado = 0; lado < 2; lado++) {
        for (i = 0; i < n; i++) {
          var d = tot * (0.03 + 0.94 * i / (n - 1)), k = 0; while (k < seg.length - 1 && d > seg[k]) { d -= seg[k]; k++; }
          var u = seg[k] ? d / seg[k] : 0, ax = haste[k][0], ay = haste[k][1], bx = haste[k + 1][0], by = haste[k + 1][1];
          var x = ax + (bx - ax) * u, y = ay + (by - ay) * u, ang = Math.atan2(by - ay, bx - ax), dir = i % 2 ? 1 : -1;
          var cx = x + Math.cos(ang + dir * Math.PI / 2) * 3.2, cy = y + Math.sin(ang + dir * Math.PI / 2) * 3.2;
          if (lado) cx = 272 - cx;
          atras.push({ t: 'leaf', cx: cx, cy: cy, rx: 14 - i * 0.3, ry: 5.2, rot: lado ? Math.PI - (ang + dir * 0.7) : ang + dir * 0.7 });
        }
      }
    }
    /* Top 3: sem asas nem cristais laterais (poluíam o visual). Só coroa + gema. */
    if (borda === 'b-90' || borda === 'b-top' || borda === 'b-100') { // coroa grande saindo pelo alto
      frente.push({ t: 'poly', pts: [[104, 9], [108, -11], [122, -1], [136, -22], [150, -1], [164, -11], [168, 9]], coroa: true });
    }
    if (ORN_PAL[borda]) frente.push({ t: 'poly', pts: [[116, 383], [156, 383], [147, 396], [136, 411], [125, 396]], gema: true }); // gema embaixo
    return { atras: atras, frente: frente, pal: ORN_PAL[borda] };
  }
  function ornSVG(borda, camada) {
    var o = ornPecas(borda), pecas = o[camada]; if (!pecas.length) return '';
    var pal = o.pal, id = 'og-' + borda + '-' + camada, f2 = function (v) { return (Math.round(v * 10) / 10); };
    var corpo = pecas.map(function (q) {
      var fill = q.coroa ? '#FFD54A' : 'url(#' + id + ')', st = q.coroa ? '#6B4200' : pal[2], sw = q.coroa ? 1.4 : 0.9;
      if (q.t === 'leaf') return '<ellipse cx="' + f2(q.cx) + '" cy="' + f2(q.cy) + '" rx="' + f2(q.rx) + '" ry="' + f2(q.ry) + '" transform="rotate(' + f2(q.rot * 180 / Math.PI) + ' ' + f2(q.cx) + ' ' + f2(q.cy) + ')" fill="' + fill + '" stroke="' + st + '" stroke-width="' + sw + '"/>';
      return '<polygon points="' + q.pts.map(function (z) { return f2(z[0]) + ',' + f2(z[1]); }).join(' ') + '" fill="' + fill + '" stroke="' + st + '" stroke-width="' + sw + '" stroke-linejoin="round"' + (q.coroa ? ' class="c-orna-coroa"' : '') + '/>';
    }).join('');
    return '<svg class="c-orna c-orna-' + camada + '" viewBox="-30 -26 332 444" aria-hidden="true"><defs><linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + pal[0] + '"/><stop offset=".5" stop-color="' + pal[1] + '"/><stop offset="1" stop-color="' + pal[2] + '"/></linearGradient></defs>' + corpo + '</svg>';
  }
  function ornCanvas(ctx, borda, camada, X, Y, S) {
    var o = ornPecas(borda), pecas = o[camada], pal = o.pal; if (!pecas.length) return;
    pecas.forEach(function (q) {
      var yMin = 1e9, yMax = -1e9;
      (q.t === 'leaf' ? [[0, q.cy - q.rx], [0, q.cy + q.rx]] : q.pts).forEach(function (z) { yMin = Math.min(yMin, z[1]); yMax = Math.max(yMax, z[1]); });
      var g = ctx.createLinearGradient(0, Y + yMin * S, 0, Y + yMax * S); g.addColorStop(0, pal[0]); g.addColorStop(.5, pal[1]); g.addColorStop(1, pal[2]);
      ctx.save(); ctx.fillStyle = q.coroa ? '#FFD54A' : g; ctx.strokeStyle = q.coroa ? '#6B4200' : pal[2]; ctx.lineWidth = (q.coroa ? 1.4 : 0.9) * S; ctx.lineJoin = 'round';
      if (q.coroa || q.gema) { ctx.shadowColor = q.coroa ? 'rgba(255,236,160,.9)' : pal[1]; ctx.shadowBlur = 6 * S; }
      ctx.beginPath();
      if (q.t === 'leaf') ctx.ellipse(X + q.cx * S, Y + q.cy * S, q.rx * S, q.ry * S, q.rot, 0, 2 * Math.PI);
      else { q.pts.forEach(function (z, k) { if (k) ctx.lineTo(X + z[0] * S, Y + z[1] * S); else ctx.moveTo(X + z[0] * S, Y + z[1] * S); }); ctx.closePath(); }
      ctx.fill(); ctx.shadowBlur = 0; ctx.stroke(); ctx.restore();
    });
  }
  /* Raios no PNG: o instante do golpe (tudo aceso), com a paleta de cada nível. A espessura de cada galho vem de r[1]. */
  var PRAIO = {
    'b-100': { a: .95, halo: 'rgba(255,196,60,.55)', haloSh: '#FFC43C', miolo: '#D79A12', mioloSh: '#FFC846', fil: '#FFFBE8', fais: '#FFD25A', arco: 'rgba(255,190,50,.7)', arcoSh: '#FFBE32', arcoFil: '#FFF6D0' },
    'b-top': { a: .95, halo: 'rgba(255,70,190,.5)', haloSh: '#FF46BE', miolo: '#FF63CE', mioloSh: '#40E0FF', fil: '#E9FBFF', fais: '#8FEFFF', arco: 'rgba(64,224,255,.75)', arcoSh: '#40E0FF', arcoFil: '#FFFFFF' }
  };
  function raiosPNG(ctx, X, Y, W, H, S, P) {
    ctx.save(); ctx.globalAlpha = P.a; ctx.translate(X, Y); ctx.scale(W / 272, H / 392); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    RAIOS.forEach(function (r) {
      var pa = new Path2D(r[0]);
      ctx.save(); ctx.strokeStyle = P.halo; ctx.lineWidth = 8 * r[1]; ctx.shadowColor = P.haloSh; ctx.shadowBlur = 12 * S; ctx.stroke(pa); ctx.restore();
      ctx.save(); ctx.strokeStyle = P.miolo; ctx.lineWidth = 2.8 * r[1]; ctx.shadowColor = P.mioloSh; ctx.shadowBlur = 8 * S; ctx.stroke(pa); ctx.restore();
      ctx.strokeStyle = P.fil; ctx.lineWidth = Math.max(.6, 1.2 * r[1]); ctx.stroke(pa);
    });
    FAISCAS.forEach(function (f) { ctx.globalAlpha = Math.min(1, f[3] + .25); ctx.fillStyle = P.fais; ctx.beginPath(); ctx.arc(f[0], f[1], f[2] * 1.3, 0, 2 * Math.PI); ctx.fill(); });
    ctx.restore();
  }
  function arcosPNG(ctx, X, Y, W, H, S, P) {
    ctx.save(); ctx.globalAlpha = P.a; ctx.translate(X, Y); ctx.scale(W / 272, H / 392); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ARCOS.forEach(function (d) { var pa = new Path2D(d);
      ctx.save(); ctx.strokeStyle = P.arco; ctx.lineWidth = 3.4; ctx.shadowColor = P.arcoSh; ctx.shadowBlur = 9 * S; ctx.stroke(pa); ctx.restore();
      ctx.strokeStyle = P.arcoFil; ctx.lineWidth = 1.1; ctx.stroke(pa); });
    ctx.restore();
  }
  function pathCartao(ctx, x, y, w, h, S, d, continuar) { // retângulo arredondado (raio FORMA_R); d = recuo do anel
    d = d || 0; x -= d; y -= d; w += 2 * d; h += 2 * d;
    var r = Math.max(2, (FORMA_R * S) - d * 0.35);
    if (!continuar) ctx.beginPath();
    if (typeof ctx.roundRect === 'function') { ctx.roundRect(x, y, w, h, r); }
    else {
      ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
    }
  }
  function texto(ctx, txt, x, y, ls) { // letra a letra, para respeitar o espaçamento entre letras em qualquer navegador
    if (!ls) { ctx.fillText(txt, x, y); return; }
    for (var i = 0; i < txt.length; i++) { ctx.fillText(txt[i], x, y); x += ctx.measureText(txt[i]).width + ls; }
  }
  function pngCanvas(a, ms, opcoes) {   // plano B: redesenha a cartinha em canvas (menos fiel). O principal é pngDom.
    opcoes = opcoes || {};
    var S = 2, M = 30, host = document.createElement('div'), html0 = html(a, ms, opcoes.id, true);
    if (!html0) return Promise.reject(new Error('sem nota'));
    host.style.cssText = 'position:fixed;left:-9999px;top:0;width:272px;pointer-events:none'; host.innerHTML = html0; document.body.appendChild(host);
    var card = host.querySelector('.carta'), tier = (card.className.match(/t-\w+/) || [''])[0];
    var borda0 = (card.className.match(/b-(?:\d+|top)/) || [''])[0], oculta = !!opcoes.ocultarNomes, is100 = card.classList.contains('b-100'), isTop = card.classList.contains('b-top');
    if (opcoes.ocultarFoto) { var im0 = card.querySelector('.c-foto img'); if (im0) im0.remove(); } // sem foto: ficam as iniciais
    var imgFoto = card.querySelector('.c-foto img'), pronto = Promise.all([document.fonts ? document.fonts.ready : 0, document.fonts ? document.fonts.load('700 20px "Barlow Semi Condensed"') : 0, document.fonts ? document.fonts.load('600 14px "IBM Plex Sans"') : 0, carregar('assets/logo_carta.png'), imgFoto && !opcoes.ocultarFoto ? carregar(imgFoto.getAttribute('src')).catch(function () { return null; }) : null]);
    return pronto.then(function (r) {
      var logo = r[3], cr = card.getBoundingClientRect(), W = cr.width * S, H = cr.height * S;
      var cv = document.createElement('canvas'); cv.width = Math.round(W + 2 * M * S); cv.height = Math.round(H + 2 * M * S);
      var ctx = cv.getContext('2d'), cs = getComputedStyle(card), c1 = cs.getPropertyValue('--c1').trim(), c2 = cs.getPropertyValue('--c2').trim(), ln = cs.getPropertyValue('--ln').trim();
      if (isTop) { c1 = '#2E0A48'; c2 = '#080214'; }   // Destaque: o CSS pinta o fundo roxo em .carta.b-top (as variáveis --c1/--c2 seguem douradas)
      var X = M * S, Y = M * S;
      ctx.fillStyle = '#EEF2F8'; ctx.fillRect(0, 0, cv.width, cv.height);
      ornCanvas(ctx, borda0, 'atras', X, Y, S);   // louros / cristais / aletas atrás do cartão
      ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.30)'; ctx.shadowBlur = 28 * S; ctx.shadowOffsetY = 10 * S; pathCartao(ctx, X, Y, W, H, S); ctx.fillStyle = c2; ctx.fill(); ctx.restore();
      pathCartao(ctx, X, Y, W, H, S); ctx.save(); ctx.clip();
      ctx.fillStyle = gradCss(ctx, 155, X, Y, W, H, c1, c2); ctx.fillRect(X, Y, W, H);
      var fr100 = is100 ? (function () { var b = card.querySelector('.c-foto').getBoundingClientRect(); return { cx: X + (b.left - cr.left + b.width / 2) * S, cy: Y + (b.top - cr.top + b.height / 2) * S }; })() : null;
      if (isTop) raiosPNG(ctx, X, Y, W, H, S, PRAIO['b-top']);   // Destaque: raios magenta e ciano
      if (is100) {
        // clarão branco-quente atrás da foto (radial-gradient do ::after do CSS)
        var cx0 = X + W * .5, cy0 = Y + H * .28, R0 = Math.max(Math.hypot(cx0 - X, cy0 - Y), Math.hypot(X + W - cx0, cy0 - Y), Math.hypot(cx0 - X, Y + H - cy0), Math.hypot(X + W - cx0, Y + H - cy0)) * .58, g0 = ctx.createRadialGradient(cx0, cy0, 0, cx0, cy0, R0);
        g0.addColorStop(0, 'rgba(255,255,255,.75)'); g0.addColorStop(.6, 'rgba(255,250,230,.2)'); g0.addColorStop(1, 'rgba(255,250,230,0)'); ctx.fillStyle = g0; ctx.fillRect(X, Y, W, H);
        raiosPNG(ctx, X, Y, W, H, S, PRAIO['b-100']);   // raios dourados no instante do golpe (igual ao CSS)
        // filete interno dourado mais fino (alinhado ao CSS: 7px para dentro)
        ctx.save(); pathCartao(ctx, X + 7 * S, Y + 7 * S, W - 14 * S, H - 14 * S, S, 7 * S); ctx.lineWidth = 1.5 * S; ctx.strokeStyle = 'rgba(255,240,180,.85)'; ctx.shadowColor = 'rgba(220,170,50,.8)'; ctx.shadowBlur = 8 * S; ctx.stroke(); ctx.shadowBlur = 0; ctx.stroke(); ctx.restore();
      } else {
        // listras
        ctx.save(); ctx.translate(X + W / 2, Y + H / 2); ctx.rotate((115 - 90) * Math.PI / 180);
        ctx.fillStyle = tier === 't-destaque' ? 'rgba(255,120,210,.16)' : 'rgba(255,255,255,.14)';
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
        ctx.save(); ctx.shadowColor = 'rgba(220,170,50,.7)'; ctx.shadowBlur = 24 * S; ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, fr.w / 2 + 2.5 * S, 0, 2 * Math.PI);
        ctx.lineWidth = 5 * S; ctx.strokeStyle = 'rgba(232,196,96,.95)'; ctx.stroke(); ctx.restore();
      }
      ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, Math.max(0, fr.w / 2 - bw / 2), 0, 2 * Math.PI); ctx.fillStyle = fs.backgroundColor; ctx.fill();
      var ft = r[4];
      if (ft) { // foto recortada em círculo (object-fit: cover, ancorada em 50% 30%)
        var ds = fr.w - 2 * bw, k = Math.max(ds / ft.width, ds / ft.height), dw = ft.width * k, dh = ft.height * k;
        ctx.save(); ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, Math.max(0, ds / 2), 0, 2 * Math.PI); ctx.clip();
        ctx.drawImage(ft, fr.x + bw - (dw - ds) * .5, fr.y + bw - (dh - ds) * .3, dw, dh); ctx.restore();
      }
      ctx.beginPath(); ctx.arc(fr.x + fr.w / 2, fr.y + fr.h / 2, Math.max(0, fr.w / 2 - bw / 2), 0, 2 * Math.PI); ctx.lineWidth = bw; ctx.strokeStyle = ln; ctx.stroke();
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
          var og = ctx.createLinearGradient(0, Y + (b.top - cr.top) * S, 0, Y + (b.bottom - cr.top) * S); og.addColorStop(0, '#FFF8D0'); og.addColorStop(.48, '#E8B820'); og.addColorStop(1, '#A07010');
          ctx.fillStyle = og; ctx.shadowColor = 'rgba(220,160,30,.6)'; ctx.shadowBlur = 6 * S; ctx.shadowOffsetY = 0;
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
      // borda por faixa de nota (anel com degradê, igual ao CSS .c-borda)
      var B = (parseFloat(cs.getPropertyValue('--bw')) || 5) * S, bc = [cs.getPropertyValue('--b1').trim(), cs.getPropertyValue('--b2').trim(), cs.getPropertyValue('--b3').trim()];
      var bg = gradCss(ctx, 135, X, Y, W, H, bc[0], bc[0]); bg.addColorStop(.25, bc[1]); bg.addColorStop(.5, bc[2]); bg.addColorStop(.75, bc[1]);
      ctx.save(); ctx.beginPath(); pathCartao(ctx, X, Y, W, H, S, 0, true); pathCartao(ctx, X + B, Y + B, W - 2 * B, H - 2 * B, S, B, true); ctx.fillStyle = bg; ctx.fill('evenodd'); ctx.restore();
      // bisel do anel (igual ao CSS): luz em cima, sombra embaixo
      var bv = ctx.createLinearGradient(0, Y, 0, Y + H); bv.addColorStop(0, 'rgba(255,255,255,.5)'); bv.addColorStop(.28, 'rgba(255,255,255,0)'); bv.addColorStop(.62, 'rgba(0,0,0,0)'); bv.addColorStop(1, 'rgba(0,0,0,.38)');
      ctx.save(); ctx.beginPath(); pathCartao(ctx, X, Y, W, H, S, 0, true); pathCartao(ctx, X + B, Y + B, W - 2 * B, H - 2 * B, S, B, true); ctx.fillStyle = bv; ctx.fill('evenodd'); ctx.restore();
      if (is100 || isTop) arcosPNG(ctx, X, Y, W, H, S, PRAIO[is100 ? 'b-100' : 'b-top']);   // faíscas correndo pela borda (por cima do anel)
      ornCanvas(ctx, borda0, 'frente', X, Y, S);   // coroa e gema por cima do cartão
      return new Promise(function (ok, erro) { try { cv.toBlob(function (bl) { bl ? ok(bl) : erro(new Error('falha ao gerar a imagem')); }, 'image/png'); } catch (e) { erro(e); } });
    }).then(function (bl) { host.remove(); return bl; }, function (e) { host.remove(); throw e; });
  }

  /* PNG fiel: o navegador desenha a própria cartinha (HTML+CSS, com campos, brilhos e raios) e a biblioteca html-to-image a converte em imagem.
     Fica fora da tela, com as animações paradas (assets/carta.css: .c-captura). Se algo falhar (ex.: navegador sem suporte), cai no desenho em canvas. */
  var LIB = null;
  function carregarLib() {
    if (window.htmlToImage) return Promise.resolve();
    return LIB || (LIB = new Promise(function (ok, erro) { var sc = document.createElement('script'); sc.src = 'assets/html-to-image.js'; sc.onload = ok; sc.onerror = function () { LIB = null; erro(new Error('biblioteca de imagem indisponível')); }; document.head.appendChild(sc); }));
  }
  function pngDom(a, ms, opcoes) {
    var host = document.createElement('div'), html0 = html(a, ms, opcoes.id, true);
    if (!html0) return Promise.reject(new Error('sem nota'));
    // `fora` some da tela; `host` (o que vira imagem) fica em posição normal dentro dele, senão a imagem sai deslocada e em branco
    var fora = document.createElement('div'); fora.style.cssText = 'position:fixed;left:-9999px;top:0;pointer-events:none';
    host.className = 'c-captura'; host.style.cssText = 'width:332px;display:flow-root;background:' + (opcoes.transparente ? 'transparent' : '#EEF2F8'); host.innerHTML = html0; fora.appendChild(host); document.body.appendChild(fora);
    // ícones <use href="#i-..."> dependem dos símbolos da página: dentro da imagem eles somem, então o desenho é copiado para dentro do <svg>
    Array.prototype.forEach.call(host.querySelectorAll('svg use'), function (u) {
      var id = (u.getAttribute('href') || u.getAttribute('xlink:href') || '').replace('#', ''), sym = id && document.getElementById(id), sv = u.parentNode;
      if (sym && sv) { sv.setAttribute('viewBox', sym.getAttribute('viewBox') || '0 0 24 24'); sv.innerHTML = sym.innerHTML; }
    });
    if (opcoes.ocultarFoto) { var im = host.querySelector('.c-foto img'); if (im) im.remove(); }
    if (opcoes.ocultarNomes) Array.prototype.forEach.call(host.querySelectorAll('.nome'), function (n) { n.textContent = n.textContent.replace(/[^\s]/g, '•'); });
    var fotos = Array.prototype.slice.call(host.querySelectorAll('img')).map(function (i) { return i.complete ? 0 : new Promise(function (r) { i.onload = i.onerror = r; }); });
    return carregarLib().then(function () {
      return Promise.all([document.fonts ? document.fonts.ready : 0, document.fonts ? document.fonts.load('700 20px "Barlow Semi Condensed"') : 0, document.fonts ? document.fonts.load('600 14px "IBM Plex Sans"') : 0].concat(fotos));
    }).then(function () {
      var o = { pixelRatio: 2, cacheBust: false }; if (!opcoes.transparente) o.backgroundColor = '#EEF2F8';   // transparente: usada pelo vídeo, que desenha a cartinha sobre o próprio fundo
      if (opcoes.rapido) return window.htmlToImage.toBlob(host, o);   // lote (zip): a 1ª cartinha já aqueceu fontes e imagens
      return window.htmlToImage.toBlob(host, o).then(function () { return window.htmlToImage.toBlob(host, o); });   // 2ª passada: a 1ª às vezes sai sem fontes/imagens (Safari)
    }).then(function (bl) { if (!bl || bl.size < 4000) throw new Error('imagem vazia'); fora.remove(); return bl; }, function (e) { fora.remove(); throw e; });
  }
  function png(a, ms, opcoes) {
    opcoes = opcoes || {};
    return pngDom(a, ms, opcoes).catch(function () { return pngCanvas(a, ms, opcoes); });
  }

  /* Computador: o WhatsApp Web não aceita imagem por link, então a cartinha pronta aparece numa janela com os caminhos que funcionam:
     copiar + abrir o WhatsApp Web (colar com Ctrl+V), arrastar a própria imagem para a conversa, compartilhar pelo sistema ou baixar. */
  function painelEnvio(bl, arq, texto, titulo) {
    var url = URL.createObjectURL(bl), d = document.createElement('dialog'); d.className = 'c-envio';
    var pode = !!(navigator.canShare && navigator.share && navigator.canShare({ files: [arq] }));
    d.innerHTML = '<form method="dialog"><h2>' + esc(titulo) + ' — pronta para enviar</h2>' +
      '<img src="' + url + '" alt="Imagem da cartinha" draggable="true">' +
      '<p class="c-envio-dica">Clique em <b>Copiar e abrir o WhatsApp Web</b>, escolha a conversa e cole com <b>Ctrl+V</b> (⌘+V no Mac). Também dá para <b>arrastar a imagem</b> acima para dentro da conversa.</p>' +
      '<p class="c-envio-st" role="status" aria-live="polite"></p>' +
      '<div class="c-envio-bt"><button type="button" class="prim" data-a="zap">Copiar e abrir o WhatsApp Web</button>' + (pode ? '<button type="button" data-a="share">Compartilhar…</button>' : '') +
      '<button type="button" data-a="baixar">Baixar imagem</button><button value="fechar">Fechar</button></div></form>';
    var st = d.querySelector('.c-envio-st'), dica = function (t) { st.textContent = t; };
    d.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-a]'); if (!b) return;
      if (b.dataset.a === 'baixar') { var l = document.createElement('a'); l.href = url; l.download = arq.name; document.body.appendChild(l); l.click(); l.remove(); dica('Imagem baixada. Anexe-a na conversa (clipe ➜ Fotos e vídeos).'); }
      else if (b.dataset.a === 'share') { navigator.share({ files: [arq], title: titulo, text: texto }).then(function () { dica('Pronto!'); }, function (er) { dica(er && er.name === 'AbortError' ? '' : 'Não consegui abrir o compartilhamento. Use copiar ou baixar.'); }); }
      else {   // o clique é um gesto do usuário: pode copiar para a área de transferência e abrir a aba sem bloqueio
        window.open('https://web.whatsapp.com/send?text=' + encodeURIComponent(texto), '_blank', 'noopener');
        var ok = (navigator.clipboard && window.ClipboardItem) ? navigator.clipboard.write([new ClipboardItem({ 'image/png': bl })]).then(function () { return true; }, function () { return false; }) : Promise.resolve(false);
        ok.then(function (c) { dica(c ? 'Imagem copiada! No WhatsApp Web, abra a conversa e cole com Ctrl+V.' : 'Não consegui copiar. Arraste a imagem para a conversa ou baixe e anexe.'); });
      }
    });
    d.addEventListener('close', function () { URL.revokeObjectURL(url); d.remove(); });
    document.body.appendChild(d); if (d.showModal) d.showModal(); else d.setAttribute('open', '');
    return 'Cartinha pronta: use a janela que abriu para enviar pelo WhatsApp.';
  }

  /* «Melhor do ano»: ranking pela média de TODAS as cartinhas mensais do agente. É UMA conta só, usada pelo álbum e por agente.html
     (antes ficava dentro do álbum e a página do agente caía no mês mais recente). `ags` = [{k, a}]; devolve [{x, ms:[u], u, lugar}] já ordenado. */
  var MESES_ORD = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  function ordMes(l) { var p = String(l || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim().split('/'); return (parseInt(p[1], 10) || 0) * 20 + MESES_ORD.indexOf(p[0]); }
  var ROTULO_ANO = 'Melhor do ano';
  function anual(ags, minMeses) {
    var cl = function (v) { return Math.max(0, Math.min(99, Math.round(v))); }, lista = [];
    ags.forEach(function (x) {
      var ms = (x.a.meses || []).filter(function (m) { return m.pontos != null; }).sort(function (p, q) { return ordMes(p.mes) - ordMes(q.mes); });
      if (ms.length < minMeses) return;
      var soma = function (c) { return ms.reduce(function (t, m) { return t + (m[c] || 0); }, 0); }, notas = ms.map(function (m) { return m.pontos; });
      var media = Math.round(notas.reduce(function (t, n) { return t + n; }, 0) / notas.length * 10) / 10;
      var rec = notas.slice(-3), mr = rec.reduce(function (t, n) { return t + n; }, 0) / rec.length;
      var dp = rec.length > 1 ? Math.sqrt(rec.reduce(function (t, n) { return t + Math.pow(n - mr, 2); }, 0) / rec.length) : 0;
      var evo = notas.length > 1 ? cl(media + 5 * (notas[notas.length - 1] - notas[notas.length - 2])) : cl(media);
      var u = { mes: 'Média', pontos: media, trab: soma('trab'), esp: soma('esp'), turnos_sem: soma('turnos_sem'), con: cl(100 - 5 * dp), evo: evo, pos: 0, total: 0, n: ms.length };
      u.meses = ms;   // os meses reais que compõem a média: o detalhamento do «Melhor do ano» sai deles (só leitura; a fórmula acima não muda)
      lista.push({ x: x, ms: [u], u: u, meses: ms });
    });
    lista.sort(function (p, q) { return q.u.pontos - p.u.pontos || q.u.n - p.u.n || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'); });
    lista.forEach(function (l, i) { l.lugar = i + 1; l.u.pos = i + 1; l.u.total = lista.length; });
    return lista;
  }
  // a cartinha do ano tem u.mes = 'Média' (rótulo do cartão); nos links o mês é «Melhor do ano»
  function mesNoLink(m) { return m === 'Média' ? ROTULO_ANO : m; }
  function nomeArquivo(a, ms) {
    var u = ms[ms.length - 1], t = String(a.nome).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return 'cartinha-' + t + '-' + String(u.mes).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.png';
  }
  /* modo: 'baixar' | 'whatsapp'. Devolve uma frase para mostrar à pessoa. */
  function enviar(a, ms, modo, opcoes) {
    opcoes = opcoes || {};
    var u = ms[ms.length - 1], nome = opcoes.ocultarNomes ? 'Minha cartinha' : 'Cartinha de ' + a.nome;
    var texto = nome + ' — nota ' + f1(u.pontos) + ' em ' + u.mes + ' (Sentinela, Prefeitura de Ponta Porã)';
    var celular = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) || (navigator.maxTouchPoints > 1 && /Mac/.test(navigator.platform));
    return png(a, ms, opcoes).then(function (bl) {
      var arq = new File([bl], nomeArquivo(a, ms), { type: 'image/png' });
      var baixar = function () { var l = document.createElement('a'); l.href = URL.createObjectURL(bl); l.download = arq.name; document.body.appendChild(l); l.click(); setTimeout(function () { URL.revokeObjectURL(l.href); l.remove(); }, 800); };
      if (modo === 'baixar') { baixar(); return 'Imagem baixada. Procure em “Downloads”.'; }
      // Celular: abre a lista de compartilhar já com a imagem. Computador: abre o WhatsApp Web e deixa a imagem copiada (é só colar com Ctrl+V na conversa).
      if (celular && navigator.canShare && navigator.canShare({ files: [arq] }) && navigator.share) {
        return navigator.share({ files: [arq], title: nome, text: texto }).then(function () { return 'Pronto! Escolha o WhatsApp na lista que abriu.'; },
          function (e) { return e && e.name === 'AbortError' ? 'Envio cancelado.' : (baixar(), 'Não consegui abrir o compartilhamento; a imagem foi baixada. Anexe no WhatsApp.'); });
      }
      if (!celular) return painelEnvio(bl, arq, texto, nome);   // computador: mostra a cartinha pronta (copiar / arrastar / compartilhar / abrir o WhatsApp Web)
      window.open('https://wa.me/?text=' + encodeURIComponent(texto), '_blank', 'noopener'); baixar();
      return 'Abri o WhatsApp e baixei a imagem. Anexe a imagem baixada na conversa.';
    });
  }

  /* ---- Detalhamento ao passar o mouse / clicar na cartinha ----
     Mostra os critérios que formaram a nota do mês (mesma tabela "Detalhamento — Critérios Aplicados por Agente" do dashboard)
     e a média dos meses anteriores, que é o critério de desempate do ranking. */
  var fn = function (n) { return Number(n).toLocaleString('pt-BR', { maximumFractionDigits: 2 }); };
  var sg = function (n) { return (n > 0 ? '+' : n < 0 ? '−' : '') + f1(Math.abs(n)); };
  /* linhas da tabela de critérios de UM mês: [critério, qtd, peso, pontos] (detalhe) ou, nos meses sem ele, ganhos/perdas */
  function criterios(u) {
    var det = u.detalhe, linhas = '', soma = null;
    if (det && det.length) { // ganhos (maiores primeiro) e depois perdas (maiores primeiro)
      var ord = det.slice().sort(function (x, y) { return (y[3] > 0) - (x[3] > 0) || Math.abs(y[3]) - Math.abs(x[3]); });
      linhas = ord.map(function (x) { return '<tr><td>' + esc(x[0]) + '</td><td class="n">' + (x[1] == null ? '' : fn(x[1])) + '</td><td class="n">' + (x[2] == null ? '' : fn(x[2])) + '</td><td class="n ' + (x[3] < 0 ? 'neg' : 'pos') + '">' + sg(x[3]) + '</td></tr>'; }).join('');
      soma = det.reduce(function (t, x) { return t + x[3]; }, 0);
    } else {
      linhas = (u.ganhos || []).concat(u.perdas || []).map(function (x) { return '<tr><td>' + esc(x.c) + '</td><td class="n"></td><td class="n"></td><td class="n ' + (x.p < 0 ? 'neg' : 'pos') + '">' + sg(x.p) + '</td></tr>'; }).join('');
    }
    return { linhas: linhas, soma: soma, tem: !!linhas };
  }
  var CAB_CRIT = '<table><thead><tr><th>Critério</th><th class="n">Qtd</th><th class="n">Peso</th><th class="n">Pontos</th></tr></thead><tbody>';
  function semDetalhe(reg) {
    return '<div class="c-pop-topo"><div><b class="nome">' + esc(reg.a.nome) + '</b><span>Detalhamento indisponível</span></div><button type="button" data-fechar aria-label="Fechar">×</button></div><p class="c-pop-desempate">Não há detalhamento registrado para esta cartinha.</p>';
  }
  /* «Melhor do ano»: a nota é a MÉDIA dos meses. Mostra cada mês (nota e posição) e, ao abrir o mês, os critérios que formaram aquela nota. Nada é somado entre meses. */
  function detalheAnualHtml(reg, u) {
    var meses = u.meses || [], id = reg.id;
    var link = id != null && !/agente\.html$/.test(location.pathname) ? '<a class="c-pop-link" href="agente.html?id=' + encodeURIComponent(id) + '&mes=' + encodeURIComponent(ROTULO_ANO) + '">Ver evolução do agente →</a>' : '';
    var lista = meses.map(function (m) {
      var c = criterios(m), nota = f1(m.pontos), pos = posicao(m, id);
      var corpo = c.tem ? CAB_CRIT + '<tr class="base"><td>Pontos iniciais</td><td></td><td></td><td class="n">100,0</td></tr>' + c.linhas + '</tbody></table>' : '<p class="c-pop-desempate">Sem detalhamento registrado para este mês.</p>';
      return '<details class="c-mes"><summary><span>' + esc(m.mes) + '</span><span class="n">' + nota + (pos != null && m.total ? ' · ' + pos + 'º de ' + m.total : '') + '</span></summary>' + corpo + '</details>';
    }).join('');
    return '<div class="c-pop-topo"><div><b class="nome">' + esc(reg.a.nome) + '</b><span>' + esc(ROTULO_ANO) + ' · ' + u.pos + 'º de ' + u.total + '</span></div><button type="button" data-fechar aria-label="Fechar">×</button></div>' +
      '<table><thead><tr><th>Mês</th><th class="n">Nota · posição</th></tr></thead></table><div class="c-meses">' + lista + '</div>' +
      '<table><tfoot><tr class="final"><td>Média de ' + meses.length + (meses.length === 1 ? ' mês' : ' meses') + ' <small>(' + meses.map(function (m) { return f1(m.pontos); }).join(' + ') + ') ÷ ' + meses.length + '</small></td><td class="n">' + f1(u.pontos) + '</td></tr></tfoot></table>' +
      '<p class="c-pop-desempate">Clique em um mês para ver os critérios dele. No ranking do ano, empate na média é decidido por quem tem mais meses e, depois, pela ordem alfabética.</p>' + link;
  }
  function detalheHtml(reg) {
    var a = reg.a, ms = reg.ms, u = ms[ms.length - 1];
    if (!u || u.pontos == null) return semDetalhe(reg);
    if (u.meses && u.mes === 'Média') return detalheAnualHtml(reg, u);
    var c = criterios(u); if (!c.tem) return semDetalhe(reg);
    var linhas = c.linhas, det = u.detalhe, soma = c.soma, nota = Math.round(u.pontos * 10) / 10;
    var total = soma == null ? null : 100 + soma;
    var obs = total == null ? '' : (total < -0.05 ? ' <small>(a nota mínima é 0)</small>' : (Math.abs(total - nota) > 0.15 ? ' <small>(com ajustes do período, ex.: presença mínima)</small>' : ''));
    var ant = ms.slice(0, -1).map(function (m) { return m.pontos; }).filter(function (v) { return v != null; });
    var mh = ant.length ? ant.reduce(function (t, v) { return t + v; }, 0) / ant.length : null;
    var link = reg.id != null && !/agente\.html$/.test(location.pathname) ? '<a class="c-pop-link" href="agente.html?id=' + encodeURIComponent(reg.id) + '&mes=' + encodeURIComponent(mesNoLink(u.mes)) + '">Ver evolução do agente →</a>' : '';
    return '<div class="c-pop-topo"><div><b class="nome">' + esc(a.nome) + '</b><span>' + esc(u.mes) + ' · ' + posicao(u, reg.id) + 'º de ' + u.total + '</span></div><button type="button" data-fechar aria-label="Fechar">×</button></div>' +
      CAB_CRIT + '<tr class="base"><td>Pontos iniciais</td><td></td><td></td><td class="n">100,0</td></tr>' + linhas + '</tbody>' +
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
    try { el.innerHTML = detalheHtml(reg); } catch (err) { el.innerHTML = semDetalhe(reg); }
    el.hidden = false; el.classList.toggle('fixo', fixo);
    var estreito = window.innerWidth < 720; el.classList.toggle('folha', estreito);
    if (estreito) { el.style.left = el.style.top = ''; return; }
    var r = card.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight, x = r.right + 10;
    if (x + w > window.innerWidth - 8) x = r.left - w - 10;
    if (x < 8) x = Math.max(8, (window.innerWidth - w) / 2);
    el.style.left = Math.round(x) + 'px'; el.style.top = Math.round(Math.max(8, Math.min(r.top, window.innerHeight - h - 8))) + 'px';
  }
  // trocou de mês/agente (a cartinha foi refeita): o detalhamento antigo não pode ficar na tela
  if (window.MutationObserver) new MutationObserver(function () { if (atual && !atual.isConnected) fechar(); }).observe(document.body, { childList: true, subtree: true });
  var cartaDe = function (e) { var t = e.target; return t && t.closest ? t.closest('.carta[data-cid]') : null; };
  document.addEventListener('mouseover', function (e) { if (fixo) return; var c = cartaDe(e); if (c) { clearTimeout(timer); if (c !== atual) abrir(c, false); } });
  document.addEventListener('mouseout', function (e) { if (fixo) return; if (cartaDe(e) && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.c-pop'))) agendar(); });
  document.addEventListener('click', function (e) {
    var c = cartaDe(e);
    if (c) {
      var ln = c.closest('a[href]');
      if (ln && /agente\.html/.test(ln.getAttribute('href') || '')) return;   // no álbum a cartinha é um link: o clique abre a evolução do agente direto
      var reg = REG[c.getAttribute('data-cid')];
      if (reg && reg.id != null && !/agente\.html$/.test(location.pathname)) {   // fora da página do agente, clicar leva à evolução do mês da cartinha
        var um = reg.ms[reg.ms.length - 1];
        e.preventDefault(); location.href = 'agente.html?id=' + encodeURIComponent(reg.id) + (um && um.mes ? '&mes=' + encodeURIComponent(mesNoLink(um.mes)) : ''); return;
      }
      e.preventDefault(); if (fixo && atual === c) fechar(); else abrir(c, true);   // na página do agente, clicar fixa o detalhamento (no celular, é o toque)
    }
    else if (fixo && !(e.target.closest && e.target.closest('.c-pop'))) fechar();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') fechar(); });
  window.addEventListener('scroll', function () { if (!fixo) fechar(); }, true);
  window.Carta = { anual: anual, ROTULO_ANO: ROTULO_ANO, html: html, medidas: medidas, bruta: bruta, posicao: posicao, NOMES: NOMES, png: png, enviar: enviar, nomeArquivo: nomeArquivo };
})();
