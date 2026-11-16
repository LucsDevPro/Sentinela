/* Vídeo de 5 segundos da cartinha animada, para mandar no WhatsApp (principalmente top 3).
   A cartinha é a MESMA imagem do botão «Baixar» (Carta.png, com fundo transparente); aqui só se anima em volta dela num <canvas> 720×1280 (vertical)
   e se grava com MediaRecorder: pacote que gira e se revela, clarão, ondas, partículas, raios e relâmpagos, brilho passando, estrelinhas, faixa «3º LUGAR» e o nome.
   Os efeitos crescem com a posição (1º ouro > 2º prata > 3º bronze > demais). MP4 quando o navegador grava MP4 (o que o WhatsApp aceita em qualquer aparelho); senão WebM.
   CartaVideo.enviar(a, ms, opcoes) → abre a janela de envio e devolve uma frase. CartaVideo.gerar(...) → Promise<Blob>. */
(function () {
  'use strict';
  var W = 720, H = 1280, FPS = 30, DUR = 5, T_REV = 1.15;
  var TIER = {
    1: { a: '#FFD25A', b: '#FFF3B0', c: '#F0B020', bg: ['#2b1c00', '#120b00'], rot: 'CAMPEÃO', raios: 9, part: 96, ondas: 4 },
    2: { a: '#DDE8F8', b: '#FFFFFF', c: '#8FA9CF', bg: ['#11213d', '#070f1f'], rot: '2º LUGAR', raios: 6, part: 64, ondas: 3 },
    3: { a: '#E8A060', b: '#FFE2C4', c: '#B8662A', bg: ['#2a1608', '#120a04'], rot: '3º LUGAR', raios: 4, part: 46, ondas: 2 },
    0: { a: '#FFD25A', b: '#FFF3B0', c: '#2BA8E8', bg: ['#0f2547', '#060f20'], rot: null, raios: 0, part: 26, ondas: 1 }
  };
  function mulberry(s) { return function () { s |= 0; s = s + 0x6D2B79F5 | 0; var t = Math.imul(s ^ s >>> 15, 1 | s); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function ease(x) { x = clamp(x, 0, 1); return 1 - Math.pow(1 - x, 3); }
  function rgba(hex, al) { var n = parseInt(hex.slice(1), 16); return 'rgba(' + (n >> 16) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + al + ')'; }
  function f1(n) { return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }); }

  /* ---- tudo que é aleatório é sorteado UMA vez (semente fixa): o mesmo vídeo sai igual e o teste pode conferir quadros ---- */
  function preparar(img, info) {
    var T = TIER[info.lugar >= 1 && info.lugar <= 3 ? info.lugar : 0], R = mulberry(info.lugar * 977 + 13), cor = [T.a, T.b, T.c, '#FFFFFF'], i;
    var S = { img: img, info: info, T: T, part: [], conf: [], estr: [], sc: document.createElement('canvas') };
    S.sc.width = img.width; S.sc.height = img.height;
    for (i = 0; i < T.part; i++) { var a = R() * 6.2832; S.part.push({ dx: Math.cos(a), dy: Math.sin(a), v: 260 + R() * 620, vida: 0.9 + R() * 0.9, c: cor[i % 4], r: 3 + R() * 5 }); }
    S.raios = [];   // relâmpagos: caminho irregular do topo até perto da carta, com ramificações; o 1º cai junto com a revelação
    function caminho(x0, y0, x1, y1, amp, seg) { var p = [[x0, y0]]; for (var k = 1; k < seg; k++) { var u = k / seg; p.push([x0 + (x1 - x0) * u + (R() - 0.5) * amp, y0 + (y1 - y0) * u + (R() - 0.5) * amp * 0.35]); } p.push([x1, y1]); return p; }
    for (i = 0; i < T.raios; i++) {
      var xr = i === 0 ? 150 + R() * 420 : 40 + R() * 640, pr = caminho(xr, -20, xr + (R() - 0.5) * 140, 420 + R() * 620, 70, 12), rm = [];
      for (var q = 0; q < 3; q++) { var m = pr[2 + Math.floor(R() * 8)], dr = R() < 0.5 ? -1 : 1; rm.push(caminho(m[0], m[1], m[0] + dr * (50 + R() * 120), m[1] + 70 + R() * 150, 30, 5)); }
      S.raios.push({ ts: T_REV + 0.05 + i * (3.3 / Math.max(1, T.raios)) + (i ? R() * 0.2 : 0), pr: pr, rm: rm });
    }
    var nEst = info.lugar <= 3 ? 34 : 16;
    for (i = 0; i < nEst; i++) { var an = R() * 6.2832, rd = 280 + R() * 230; S.estr.push({ x: 360 + Math.cos(an) * rd * 0.82, y: 640 + Math.sin(an) * rd * 1.18, f: R() * 6.2832, v: 2 + R() * 3, s: 10 + R() * 18 }); }
    return S;
  }

  function fundo(ctx, t, S) {
    var T = S.T, g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, T.bg[0]); g.addColorStop(1, T.bg[1]); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    var vis = ease((t - 0.2) / 0.9), n = 18;
    ctx.save(); ctx.translate(360, 640); ctx.rotate(t * 0.22);
    for (var i = 0; i < n; i++) { ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, 1300, i * 6.2832 / n, i * 6.2832 / n + 6.2832 / n * 0.5); ctx.closePath(); ctx.fillStyle = rgba(T.a, 0.07 * vis * (S.info.lugar <= 3 ? 1.5 : 1)); ctx.fill(); }
    ctx.restore();
    var h = ctx.createRadialGradient(360, 640, 40, 360, 640, 640); h.addColorStop(0, rgba(T.a, 0.38 * vis)); h.addColorStop(1, rgba(T.a, 0)); ctx.fillStyle = h; ctx.fillRect(0, 0, W, H);
    var v = ctx.createRadialGradient(360, 640, 380, 360, 640, 900); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,.6)'); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
  }

  function verso(ctx, w, h, T) {   // costas do pacote, desenhadas na hora (a carta só aparece no clarão)
    var x = -w / 2, y = -h / 2, c = 0.075 * w;
    ctx.beginPath(); ctx.moveTo(x + c, y); ctx.lineTo(x + w - c, y); ctx.lineTo(x + w, y + c); ctx.lineTo(x + w, y + h - c); ctx.lineTo(x + w - c * 1.2, y + h); ctx.lineTo(x + c * 1.2, y + h); ctx.lineTo(x, y + h - c); ctx.lineTo(x, y + c); ctx.closePath();
    var g = ctx.createLinearGradient(x, y, x + w, y + h); g.addColorStop(0, '#1D4F8F'); g.addColorStop(0.5, '#0A1F45'); g.addColorStop(1, '#1B3F78'); ctx.fillStyle = g; ctx.fill();
    ctx.lineWidth = 6; ctx.strokeStyle = rgba(T.a, 0.85); ctx.stroke();
    ctx.fillStyle = '#F7B500'; ctx.textAlign = 'center'; ctx.font = '700 ' + Math.round(w * 0.11) + 'px "Barlow Semi Condensed", system-ui, sans-serif'; ctx.fillText('SENTINELA', 0, -4);
    ctx.fillStyle = '#9DD6F4'; ctx.font = '600 ' + Math.round(w * 0.05) + 'px "Barlow Semi Condensed", system-ui, sans-serif'; ctx.fillText('C A R T I N H A', 0, w * 0.09);
  }

  function estrela(ctx, x, y, s, al, cor) {
    ctx.save(); ctx.translate(x, y); ctx.globalAlpha = al; ctx.fillStyle = cor; ctx.beginPath();
    ctx.moveTo(0, -s); ctx.quadraticCurveTo(s * 0.12, -s * 0.12, s, 0); ctx.quadraticCurveTo(s * 0.12, s * 0.12, 0, s); ctx.quadraticCurveTo(-s * 0.12, s * 0.12, -s, 0); ctx.quadraticCurveTo(-s * 0.12, -s * 0.12, 0, -s); ctx.fill(); ctx.restore();
  }

  /* ---- UM quadro do vídeo no instante t (segundos, 0 a 5) ---- */
  function quadro(ctx, t, S) {
    var T = S.T, info = S.info, img = S.img, top = info.lugar <= 3;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.shadowBlur = 0;
    fundo(ctx, t, S);
    var tr = t - T_REV, k = 0.9 * (W / 664) * 0.99;   // a imagem da cartinha (664 px de largura) ocupa quase toda a largura
    // 1) pacote que gira e se aproxima, até virar a carta no clarão
    var p = ease(t / T_REV), ang = (1 - p) * -Math.PI * 3, cx = Math.cos(ang), sc = 0.55 + 0.45 * p, y = 640 - Math.sin(Math.PI * p) * 140;
    if (t < T_REV) {
      ctx.save(); ctx.translate(360, y); ctx.scale(Math.max(0.03, Math.abs(cx)) * sc, sc); ctx.shadowColor = rgba(T.a, 0.9); ctx.shadowBlur = 50;
      if (cx >= 0) verso(ctx, 520, 760, T); else { ctx.scale(1, 1); verso(ctx, 520, 760, T); }
      ctx.restore();
    } else {
      // 2) a cartinha: flutua, inclina de leve e recebe um brilho que passa
      var sx = 0.985 + 0.015 * Math.cos(tr * 1.7), rot = Math.sin(tr * 1.3) * 0.012, fl = Math.sin(tr * 2.2) * 10, ent = ease(tr / 0.45), esc = 1.12 - 0.12 * ent;
      var sctx = S.sc.getContext('2d'); sctx.globalCompositeOperation = 'source-over'; sctx.clearRect(0, 0, S.sc.width, S.sc.height); sctx.drawImage(img, 0, 0);
      var per = 2.1, fase = ((tr % per) / per) * 1.6 - 0.3, px = fase * S.sc.width;
      sctx.globalCompositeOperation = 'source-atop'; sctx.save(); sctx.transform(1, 0, -0.35, 1, 0, 0);
      var gb = sctx.createLinearGradient(px - 90, 0, px + 90, 0); gb.addColorStop(0, 'rgba(255,255,255,0)'); gb.addColorStop(0.5, 'rgba(255,255,255,' + (top ? 0.55 : 0.38) + ')'); gb.addColorStop(1, 'rgba(255,255,255,0)');
      sctx.fillStyle = gb; sctx.fillRect(-S.sc.height * 0.4, 0, S.sc.width + S.sc.height * 0.8, S.sc.height); sctx.restore();
      ctx.save(); ctx.translate(360, 640 + fl); ctx.rotate(rot); ctx.scale(sx * k * esc, k * esc);
      ctx.shadowColor = rgba(T.a, top ? 0.85 : 0.5); ctx.shadowBlur = top ? 60 : 34; ctx.drawImage(S.sc, -S.sc.width / 2, -S.sc.height / 2); ctx.restore();
      // estrelinhas piscando em volta
      for (var i = 0; i < S.estr.length; i++) { var e = S.estr[i], al = Math.pow(Math.max(0, Math.sin(t * e.v + e.f)), 4); if (al > 0.02) estrela(ctx, e.x, e.y, e.s, al, '#FFFFFF'); }
      // partículas da explosão
      for (i = 0; i < S.part.length; i++) {
        var q = S.part[i], u = tr / q.vida; if (u < 0 || u > 1) continue; var d = q.v * tr * (1 - 0.35 * u);
        ctx.globalAlpha = 1 - u; ctx.fillStyle = q.c; ctx.beginPath(); ctx.arc(360 + q.dx * d, 640 + q.dy * d + 260 * tr * tr * 0.5, q.r * (1 - 0.5 * u), 0, 6.2832); ctx.fill();
      }
      ctx.globalAlpha = 1;
      // ondas de choque
      for (i = 0; i < T.ondas; i++) { var o = tr - i * 0.14; if (o < 0 || o > 0.9) continue; ctx.lineWidth = 10 * (1 - o / 0.9) + 1; ctx.strokeStyle = rgba(i % 2 ? T.b : T.a, 1 - o / 0.9); ctx.beginPath(); ctx.arc(360, 640, 60 + o * 900, 0, 6.2832); ctx.stroke(); }
      // clarão
      if (tr < 0.45) { ctx.fillStyle = rgba(top ? T.b : '#FFFFFF', 0.95 * (1 - tr / 0.45)); ctx.fillRect(0, 0, W, H); }
    }
    // raios (só no pódio): três traços (brilho largo, médio e núcleo branco) que piscam, mais um clarão azulado no instante da queda
    for (var j = 0; j < S.raios.length; j++) {
      var rb = S.raios[j], ru = (t - rb.ts) / 0.45; if (ru < 0 || ru > 1) continue;
      var fa = ru < 0.15 ? 1 : ru < 0.3 ? 0.25 : ru < 0.45 ? 1 : ru < 0.6 ? 0.5 : (1 - ru) / 0.4 * 0.5;
      if (ru < 0.12) { ctx.fillStyle = 'rgba(215,230,255,' + (0.3 * (j === 0 ? 1.4 : 1)) + ')'; ctx.fillRect(0, 0, W, H); }
      ctx.save(); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.shadowColor = T.a; ctx.shadowBlur = 36; var trs = [rb.pr].concat(rb.rm);
      [[22, rgba(T.a, 0.22 * fa)], [9, rgba(T.a, 0.6 * fa)], [3.6, 'rgba(255,255,255,' + fa + ')']].forEach(function (cfg) {
        ctx.lineWidth = cfg[0]; ctx.strokeStyle = cfg[1];
        trs.forEach(function (pp, ix) { ctx.lineWidth = ix ? cfg[0] * 0.5 : cfg[0]; ctx.beginPath(); ctx.moveTo(pp[0][0], pp[0][1]); for (var z = 1; z < pp.length; z++) ctx.lineTo(pp[z][0], pp[z][1]); ctx.stroke(); });
      });
      ctx.restore();
    }
    // faixa, nome e rodapé
    ctx.textAlign = 'center'; ctx.shadowBlur = 0;
    var rot2 = T.rot || (info.lugar + 'º LUGAR'), bp = ease((t - 1.3) / 0.5);
    if (bp > 0) {
      ctx.save(); ctx.globalAlpha = bp; ctx.translate(360, 118); ctx.scale(1 + (1 - bp) * 1.6, 1 + (1 - bp) * 1.6);
      ctx.font = '700 ' + (top ? 92 : 70) + 'px "Barlow Semi Condensed", system-ui, sans-serif'; ctx.shadowColor = rgba(T.a, 0.9); ctx.shadowBlur = 30;
      var gg = ctx.createLinearGradient(0, -70, 0, 20); gg.addColorStop(0, T.b); gg.addColorStop(1, T.a); ctx.fillStyle = gg; ctx.fillText(rot2, 0, 0); ctx.restore();
    }
    var np = ease((t - 1.7) / 0.5);
    if (np > 0) {
      ctx.save(); ctx.globalAlpha = np; ctx.translate(0, (1 - np) * 30);
      ctx.fillStyle = '#FFFFFF'; ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = 12;
      var nome = info.nome, fs = 58; ctx.font = '700 ' + fs + 'px "Barlow Semi Condensed", system-ui, sans-serif';
      while (ctx.measureText(nome).width > W - 70 && fs > 30) { fs -= 2; ctx.font = '700 ' + fs + 'px "Barlow Semi Condensed", system-ui, sans-serif'; }
      ctx.fillText(nome, 360, 1128);
      ctx.font = '600 30px "IBM Plex Sans", system-ui, sans-serif'; ctx.fillStyle = T.a; ctx.fillText([info.eq, info.mes, 'nota ' + info.nota].filter(Boolean).join(' · '), 360, 1178);
      ctx.restore();
    }
    var fp = ease((t - 2.2) / 0.6);
    if (fp > 0) { ctx.save(); ctx.globalAlpha = 0.75 * fp; ctx.fillStyle = '#9DB2D0'; ctx.font = '600 24px "IBM Plex Sans", system-ui, sans-serif'; ctx.fillText('SENTINELA · Prefeitura de Ponta Porã', 360, 1236); ctx.restore(); }
    ctx.globalAlpha = 1;
  }

  function escolherMime() {
    if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return null;
    var c = ['video/mp4;codecs=avc1.42E01E', 'video/mp4;codecs=avc1', 'video/mp4', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
    for (var i = 0; i < c.length; i++) if (MediaRecorder.isTypeSupported(c[i])) return c[i];
    return null;
  }
  function imagemDe(bl) {
    return new Promise(function (ok, no) { var u = URL.createObjectURL(bl), im = new Image(); im.onload = function () { URL.revokeObjectURL(u); ok(im); }; im.onerror = function () { URL.revokeObjectURL(u); no(new Error('imagem')); }; im.src = u; });
  }
  function fontes() { return document.fonts ? Promise.all([document.fonts.load('700 60px "Barlow Semi Condensed"'), document.fonts.load('600 30px "IBM Plex Sans"')]).catch(function () {}) : Promise.resolve(); }

  /* grava o quadro a quadro em tempo real (5 s) */
  function gravar(S) {
    return new Promise(function (ok, no) {
      var mime = escolherMime(); if (!mime) return no(new Error('sem MediaRecorder'));
      var c = document.createElement('canvas'); c.width = W; c.height = H; var ctx = c.getContext('2d'); quadro(ctx, 0, S);
      var rec, partes = [];
      try { rec = new MediaRecorder(c.captureStream(FPS), { mimeType: mime, videoBitsPerSecond: 5000000 }); } catch (e) { return no(e); }
      rec.ondataavailable = function (e) { if (e.data && e.data.size) partes.push(e.data); };
      rec.onerror = function (e) { no(e.error || new Error('gravação')); };
      rec.onstop = function () { var b = new Blob(partes, { type: mime.split(';')[0] }); b.size > 2000 ? ok(b) : no(new Error('vídeo vazio')); };
      var ini = performance.now(), id;
      rec.start(250);
      id = setInterval(function () {
        var t = (performance.now() - ini) / 1000;
        if (t >= DUR) { clearInterval(id); quadro(ctx, DUR, S); setTimeout(function () { rec.stop(); }, 120); return; }
        quadro(ctx, t, S);
      }, 1000 / FPS);
    });
  }

  function infoDe(a, ms, o) {
    var u = ms[ms.length - 1], anon = !!o.ocultarNomes;
    return { lugar: Math.max(1, Math.round(o.lugar || u.pos || 99)), nome: anon ? 'Agente' : String(a.nome), eq: a.equipe || '', mes: String(u.mes) === 'Média' ? 'Melhor do ano' : String(u.mes), nota: f1(u.pontos) };
  }
  function gerar(a, ms, o) {
    o = o || {};
    return Promise.all([window.Carta.png(a, ms, Object.assign({}, o, { transparente: true })).then(imagemDe), fontes()]).then(function (r) { return gravar(preparar(r[0], infoDe(a, ms, o))); });
  }

  /* ---- janela de envio (parecida com a da imagem): ver, compartilhar, baixar, abrir o WhatsApp Web ---- */
  function painel(bl, arq, texto, titulo) {
    var url = URL.createObjectURL(bl), d = document.createElement('dialog'); d.className = 'c-envio c-envio-video';
    var pode = !!(navigator.canShare && navigator.share && navigator.canShare({ files: [arq] })), mp4 = /mp4/.test(bl.type);
    d.innerHTML = '<form method="dialog"><h2>' + String(titulo).replace(/[&<>"]/g, '') + ' — vídeo pronto</h2>' +
      '<video src="' + url + '" controls autoplay loop muted playsinline></video>' +
      '<p class="c-envio-dica">' + (pode ? 'Toque em <b>Compartilhar…</b> e escolha o WhatsApp.' : 'Clique em <b>Baixar vídeo</b>, abra o <b>WhatsApp Web</b> e anexe pelo clipe (<b>Fotos e vídeos</b>) ou arraste o arquivo para a conversa.') + '</p>' +
      (mp4 ? '' : '<p class="c-envio-dica">Seu navegador gravou em WebM. Se o WhatsApp não aceitar, gere o vídeo no Chrome, Edge ou Safari atualizados (eles gravam MP4).</p>') +
      '<p class="c-envio-st" role="status" aria-live="polite"></p>' +
      '<div class="c-envio-bt">' + (pode ? '<button type="button" class="prim" data-a="share">Compartilhar…</button>' : '') + '<button type="button"' + (pode ? '' : ' class="prim"') + ' data-a="baixar">Baixar vídeo</button><button type="button" data-a="zap">Abrir o WhatsApp Web</button><button value="fechar">Fechar</button></div></form>';
    var st = d.querySelector('.c-envio-st'), dica = function (t) { st.textContent = t; };
    d.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-a]'); if (!b) return;
      if (b.dataset.a === 'baixar') { var l = document.createElement('a'); l.href = url; l.download = arq.name; document.body.appendChild(l); l.click(); l.remove(); dica('Vídeo baixado. No WhatsApp: clipe ➜ Fotos e vídeos.'); }
      else if (b.dataset.a === 'share') { navigator.share({ files: [arq], title: titulo, text: texto }).then(function () { dica('Pronto!'); }, function (er) { dica(er && er.name === 'AbortError' ? '' : 'Não consegui abrir o compartilhamento. Baixe o vídeo.'); }); }
      else { window.open('https://web.whatsapp.com/send?text=' + encodeURIComponent(texto), '_blank', 'noopener'); dica('WhatsApp Web aberto. Baixe o vídeo e anexe na conversa (clipe ➜ Fotos e vídeos).'); }
    });
    d.addEventListener('close', function () { URL.revokeObjectURL(url); d.remove(); });
    document.body.appendChild(d); if (d.showModal) d.showModal(); else d.setAttribute('open', '');
    return 'Vídeo pronto: use a janela que abriu para enviar pelo WhatsApp.';
  }
  function enviar(a, ms, o) {
    o = o || {};
    var inf = infoDe(a, ms, o), titulo = o.ocultarNomes ? 'Minha cartinha' : 'Cartinha de ' + a.nome;
    var texto = titulo + ' — ' + inf.lugar + 'º lugar, nota ' + inf.nota + ' em ' + inf.mes + ' (Sentinela, Prefeitura de Ponta Porã)';
    return gerar(a, ms, o).then(function (bl) {
      var ext = /mp4/.test(bl.type) ? 'mp4' : 'webm', arq = new File([bl], window.Carta.nomeArquivo(a, ms).replace(/\.png$/, '-video.' + ext), { type: bl.type });
      return painel(bl, arq, texto, titulo);
    });
  }
  window.CartaVideo = { gerar: gerar, enviar: enviar, quadro: quadro, preparar: preparar, DUR: DUR, W: W, H: H, FPS: FPS, suportado: function () { return !!escolherMime(); } };
})();
