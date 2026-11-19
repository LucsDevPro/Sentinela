/* Sons da abertura de pacote (reunião), sintetizados na hora com Web Audio: não há arquivo de áudio nenhum.
   Começa DESLIGADO (a pessoa liga no botão «Som» do pacote ou na tecla S); a escolha fica guardada neste aparelho.
   Som.tocar('rasgar' | 'giro' | 'suspense' | 'ding' | 'bronze' | 'prata' | 'ouro' | 'fanfarra' | 'trovao' | 'batida', duracaoMs?) */
(function () {
  'use strict';
  var KEY = 'sentinela:som', ctx = null, mestre = null, nivel = 0;   // nivel: 0 desligado · 1 normal · 2 baixo (sala pequena / quem prefere menos volume)
  var GANHO = [0, 0.55, 0.2];
  try { var sv = localStorage.getItem(KEY); nivel = sv === '2' ? 2 : sv === '1' ? 1 : 0; } catch (e) {}

  /* cadeia de saída: som seco + «sala» (reverberação sintética de ~2,4 s, que dá o clima de estádio/orquestra) → filtro que tira o chiado agudo → compressor (não estoura). Devolve o nó de entrada. */
  function reverb(c) {
    var sr = c.sampleRate, n = Math.floor(sr * 2.4), ir = c.createBuffer(2, n, sr);
    for (var ch = 0; ch < 2; ch++) { var d = ir.getChannelData(ch), lp = 0; for (var k = 0; k < n; k++) { var u = k / n; lp += ((Math.random() * 2 - 1) - lp) * (0.9 - 0.75 * u); d[k] = lp * Math.pow(1 - u, 2.4) * 3.2; } }   // ruído que escurece e some com o tempo
    var cv = c.createConvolver(); cv.buffer = ir; return cv;
  }
  function limitador(c, saida) {
    var ent = c.createGain(), seco = c.createGain(), mol = c.createGain(), rv = reverb(c), lp = c.createBiquadFilter(), k = c.createDynamicsCompressor();
    seco.gain.value = 0.82; mol.gain.value = 0.42; lp.type = 'lowpass'; lp.frequency.value = 9500; lp.Q.value = 0.5;
    k.threshold.value = -17; k.knee.value = 14; k.ratio.value = 5; k.attack.value = 0.005; k.release.value = 0.3;
    ent.connect(seco); ent.connect(rv); rv.connect(mol); seco.connect(lp); mol.connect(lp); lp.connect(k); k.connect(saida); return ent;
  }
  function ac() {
    if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return ctx; }
    var C = window.AudioContext || window.webkitAudioContext; if (!C) return null;
    ctx = new C(); mestre = ctx.createGain(); mestre.gain.value = GANHO[nivel] || 0.55; mestre.connect(limitador(ctx, ctx.destination)); return ctx;
  }
  function ruido(dur) {
    var n = Math.max(1, Math.floor(ctx.sampleRate * dur)), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    var s = ctx.createBufferSource(); s.buffer = b; return s;
  }
  function env(g, t0, atk, dur, pico) {   // sobe rápido e desce exponencial, sem estalo
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(pico, t0 + atk); g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  }
  function tom(tipo, f0, f1, t0, dur, pico, atk) {
    var o = ctx.createOscillator(), g = ctx.createGain(); o.type = tipo; o.frequency.setValueAtTime(f0, t0);
    if (f1 && f1 !== f0) o.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    env(g, t0, atk || 0.01, dur, pico); o.connect(g); g.connect(mestre); o.start(t0); o.stop(t0 + dur + 0.05);
  }
  function sopro(t0, dur, tipo, f0, f1, pico) {   // ruído filtrado (rasgo, vento, platô)
    var s = ruido(dur), f = ctx.createBiquadFilter(), g = ctx.createGain(); f.type = tipo; f.frequency.setValueAtTime(f0, t0); f.Q.value = 0.9;
    if (f1) f.frequency.exponentialRampToValueAtTime(f1, t0 + dur);
    env(g, t0, Math.min(0.08, dur / 3), dur, pico); s.connect(f); f.connect(g); g.connect(mestre); s.start(t0); s.stop(t0 + dur);
  }
  var NOTA = { C4: 261.6, E4: 329.6, G4: 392, C5: 523.3, E5: 659.3, G5: 784, C6: 1046.5, A4: 440, B4: 493.9, D5: 587.3 };
  function acorde(t0, notas, tipo, dur, pico, passo) { notas.forEach(function (n, i) { tom(tipo, NOTA[n], 0, t0 + i * (passo || 0), dur, pico, 0.012); }); }

  /* ---- «orquestra» sintetizada (estilo abertura de campeonato: tímpanos, metais e coro). Melodias originais, só o clima é de estádio ---- */
  function timpano(t, f, pico) {   // pancada grave com queda de tom + um estalo de pele
    var o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(f * 1.9, t); o.frequency.exponentialRampToValueAtTime(f, t + 0.09);
    env(g, t, 0.004, 1.1, pico || 0.9); o.connect(g); g.connect(mestre); o.start(t); o.stop(t + 1.2);
    sopro(t, 0.12, 'lowpass', 1400, 300, (pico || 0.9) * 0.5);
  }
  function metal(t, f, dur, pico, abre) {   // trompa/trombone: serras desafinadas + corpo triangular, filtro que «abre» no ataque e vibrato leve
    var cut = Math.min(3800, f * (abre || 4.5));
    [-6, 6].forEach(function (c) {
      var o = ctx.createOscillator(), g = ctx.createGain(), fl = ctx.createBiquadFilter(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c;
      fl.type = 'lowpass'; fl.Q.value = 0.7; fl.frequency.setValueAtTime(f * 1.3, t); fl.frequency.exponentialRampToValueAtTime(cut, t + 0.2); fl.frequency.exponentialRampToValueAtTime(f * 2, t + dur);
      var l = ctx.createOscillator(), lg = ctx.createGain(); l.frequency.value = 5; lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(f * 0.004, t + 0.45); l.connect(lg); lg.connect(o.frequency); l.start(t); l.stop(t + dur + 0.05);
      env(g, t, 0.1, dur, pico * 0.7); o.connect(fl); fl.connect(g); g.connect(mestre); o.start(t); o.stop(t + dur + 0.05);
    });
    tom('triangle', f, 0, t, dur, pico * 0.55, 0.08);
  }
  function coro(t, freqs, dur, pico) {   // «aaah» de coro: poucas vozes, serra filtrada por dois formantes de vogal, vibrato lento
    freqs.forEach(function (f) {
      [-8, 8].forEach(function (c) {
        var o = ctx.createOscillator(), g = ctx.createGain(), l = ctx.createOscillator(), lg = ctx.createGain(), a = ctx.createBiquadFilter(), b = ctx.createBiquadFilter(), lp = ctx.createBiquadFilter();
        o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c; l.frequency.value = 4.8 + Math.random() * 0.8; lg.gain.value = f * 0.006; l.connect(lg); lg.connect(o.frequency);
        a.type = 'bandpass'; a.frequency.value = 650; a.Q.value = 1.6; b.type = 'bandpass'; b.frequency.value = 1100; b.Q.value = 2; lp.type = 'lowpass'; lp.frequency.value = 2400;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(pico * 1.4, t + Math.min(0.6, dur * 0.45)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        o.connect(a); o.connect(b); a.connect(lp); b.connect(lp); lp.connect(g); g.connect(mestre); o.start(t); l.start(t); o.stop(t + dur + 0.05); l.stop(t + dur + 0.05);
      });
    });
  }
  function sino(t, f, dur, pico) { tom('sine', f, 0, t, dur, pico, 0.004); tom('sine', f * 2.76, 0, t, dur * 0.5, pico * 0.35, 0.004); tom('sine', f * 5.4, 0, t, dur * 0.25, pico * 0.15, 0.004); }   // brilho agudo de sino, no lugar de metal estridente
  function prato(t, dur, pico) { sopro(t, dur, 'highpass', 5200, 8500, pico * 0.7); sopro(t, dur * 0.6, 'bandpass', 6800, 5200, pico * 0.4); }
  function rufar(t, d, f, pico) {   // rufar de tímpanos que acelera e cresce até o instante t+d
    var x = 0, passo = 0.16; while (x < d - 0.02) { timpano(t + x, f, pico * (0.25 + 0.75 * x / d)); x += passo; passo = Math.max(0.045, passo * 0.9); }
  }
  var F = { A3: 220, D2: 73.4, A2: 110, D3: 146.8, Bb3: 233.1, C4: 261.6, D4: 293.7, F4: 349.2, Fs4: 370, G4: 392, A4: 440, Bb4: 466.2, C5: 523.3, D5: 587.3, F5: 698.5, Fs5: 740, A5: 880, D6: 1174.7, E4: 329.6 };

  var SONS = {
    rasgar: function (t) { sopro(t, 0.55, 'highpass', 900, 5200, 0.5); sopro(t + 0.05, 0.35, 'bandpass', 3000, 900, 0.35); tom('sine', 120, 45, t, 0.4, 0.5); },
    giro: function (t, ms) { sopro(t, (ms || 900) / 1000, 'bandpass', 500, 2600, 0.28); },
    suspense: function (t, ms) {   // rufar de tímpanos que acelera, cordas/coro subindo e prato invertido até a revelação
      var d = (ms || 1500) / 1000; rufar(t, d, F.D2 * 1.5, 0.8);
      coro(t, [F.D3, F.A2 * 2], d + 0.1, 0.02 + d * 0.006); sopro(t, d, 'highpass', 1500, 9000, 0.3);
      var o = ctx.createOscillator(), g = ctx.createGain(), f = ctx.createBiquadFilter(); o.type = 'sawtooth'; o.frequency.setValueAtTime(F.D3, t); o.frequency.exponentialRampToValueAtTime(F.D4 * 1.5, t + d);
      f.type = 'lowpass'; f.frequency.setValueAtTime(500, t); f.frequency.exponentialRampToValueAtTime(3500, t + d); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.16, t + d * 0.95); g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.05);
      o.connect(f); f.connect(g); g.connect(mestre); o.start(t); o.stop(t + d + 0.1);
    },
    ding: function (t) { tom('sine', 880, 0, t, 0.5, 0.35); tom('sine', 1320, 0, t + 0.08, 0.6, 0.28); tom('triangle', 1760, 0, t + 0.16, 0.5, 0.12); },
    bronze: function (t) { timpano(t, F.D2, 0.9); metal(t, F.D4, 1.0, 0.16); metal(t, F.A4, 1.0, 0.14); metal(t + 0.12, F.D5, 0.9, 0.14); coro(t, [F.D3, F.A4], 1.1, 0.025); prato(t, 0.7, 0.12); },
    prata: function (t) { timpano(t, F.D2, 1); timpano(t + 0.2, F.D2, 0.8); [['D4', 0], ['A4', 0.12], ['D5', 0.24]].forEach(function (n) { metal(t + n[1], F[n[0]], 1.4, 0.16); }); metal(t + 0.36, F.Fs5, 1.2, 0.13); coro(t, [F.D3, F.A4, F.D5], 1.6, 0.03); prato(t, 1.2, 0.18); },
    ouro: function (t) {   // subida de metais, pancadas de tímpanos e acorde de Ré maior (voicing aberto) com coro, sinos e prato
      [['A3', 0], ['D4', 0.13], ['Fs4', 0.26], ['A4', 0.39]].forEach(function (n) { metal(t + n[1], F[n[0]], 0.55, 0.17); });
      timpano(t, F.D2, 1); timpano(t + 0.26, F.D2, 0.8); timpano(t + 0.52, F.D2, 0.85);
      var b = t + 0.62; timpano(b, F.D2, 1.1); [['D3', 0.22], ['A3', 0.2], ['D4', 0.2], ['Fs4', 0.19], ['A4', 0.19], ['D5', 0.14]].forEach(function (n) { metal(b, F[n[0]], 2.7, n[1], 4); });
      coro(b, [F.D3, F.A3, F.Fs4, F.D5, F.A4], 2.9, 0.034); [F.D5, F.Fs5, F.A5].forEach(function (f, k) { sino(b + 0.05 + k * 0.09, f, 1.8, 0.13); });
      prato(b, 2.6, 0.3); tom('sine', 55, 30, b, 1.3, 0.8);
    },
    fanfarra: function (t) {   // «tema» de campeonato: Ré menor → Si bemol → Dó → Ré maior, melodia de metais por cima e tímpanos marcando
      var P = [[['D3', 'A3', 'F4'], 'A4'], [['Bb3', 'F4', 'D4'], 'Bb4'], [['C4', 'G4', 'E4'], 'C5']];
      P.forEach(function (p, i) { var x = t + i * 0.8; timpano(x, F.D2, 0.8); coro(x, p[0].map(function (n) { return F[n]; }), 1.0, 0.028); metal(x, F[p[1]], 0.78, 0.15); metal(x, F[p[1]] / 2, 0.78, 0.11); });
      var g = t + 2.4; timpano(g, F.D2, 1.1); timpano(g + 0.3, F.D2, 0.8);
      [['D3', 0.22], ['A3', 0.2], ['D4', 0.2], ['Fs4', 0.19], ['A4', 0.19], ['D5', 0.15]].forEach(function (n) { metal(g, F[n[0]], 3.1, n[1], 4); });
      coro(g, [F.D3, F.A3, F.Fs4, F.D5, F.A4], 3.3, 0.036); [F.D5, F.Fs5, F.A5, F.D6].forEach(function (f, k) { sino(g + 0.05 + k * 0.1, f, 2, 0.12); });
      prato(g, 3, 0.33); tom('sine', 55, 30, g, 1.5, 0.85);
    },
    batida: function (t) { tom('sine', 72, 34, t, 0.32, 0.9); tom('sine', 60, 30, t + 0.16, 0.3, 0.6); },   // coração do suspense do 1º lugar
    trovao: function (t) {   // estalo seco do raio + trovoada grave que rola
      sopro(t, 0.22, 'highpass', 2500, 9000, 0.6); tom('sine', 70, 30, t, 0.5, 0.7);
      sopro(t + 0.12, 1.9, 'lowpass', 520, 70, 0.75); sopro(t + 0.7, 1.4, 'lowpass', 380, 60, 0.5); tom('sine', 48, 28, t + 0.2, 1.5, 0.5);
    }
  };

  function com(c, m, fn) { var pc = ctx, pm = mestre; ctx = c; mestre = m; try { fn(); } finally { ctx = pc; mestre = pm; } }
  window.Som = {
    /* trilha para o vídeo: um AudioContext à parte, ligado a um MediaStream que o gravador do vídeo junta à imagem. Funciona mesmo com o som da reunião desligado. */
    paraGravacao: function () {
      var C = window.AudioContext || window.webkitAudioContext; if (!C) return null;
      var c = new C(), dest = c.createMediaStreamDestination(), g = c.createGain(); g.gain.value = 0.85; g.connect(limitador(c, dest));
      return { stream: dest.stream, iniciar: function () { try { if (c.resume) c.resume(); } catch (e) {} }, tocar: function (nome, t, ms) { if (SONS[nome]) com(c, g, function () { SONS[nome](c.currentTime + 0.05 + (t || 0), ms); }); }, fade: function (t, d) { var x = c.currentTime + 0.05 + t; g.gain.setValueAtTime(0.85, x); g.gain.linearRampToValueAtTime(0.0001, x + d); },   // some o som no fim do vídeo (sem corte seco/estalo)
        fechar: function () { try { c.close(); } catch (e) {} } };
    },
    /* renderiza um som sem tocar (teste/medição): devolve uma AudioBuffer estéreo */
    renderizar: function (nome, ms, seg) {
      var O = window.OfflineAudioContext; if (!O || !SONS[nome]) return Promise.resolve(null);
      var c = new O(2, 44100 * (seg || 4), 44100), g = c.createGain(); g.gain.value = 0.85; g.connect(limitador(c, c.destination));
      com(c, g, function () { SONS[nome](0.02, ms); }); return c.startRendering();
    },
    ligado: function () { return nivel > 0; },
    nivel: function () { return nivel; },
    definir: function (n) { nivel = n === 2 ? 2 : n === 1 ? 1 : 0; try { localStorage.setItem(KEY, String(nivel)); } catch (e) {} if (nivel) { ac(); if (mestre) mestre.gain.value = GANHO[nivel]; this.tocar('ding'); } return nivel; },
    ligar: function (v) { return this.definir(v ? (nivel || 1) : 0) > 0; },
    alternar: function () { return this.ligar(nivel === 0); },
    ciclar: function () { return this.definir((nivel + 1) % 3); },   // desligado → normal → baixo → desligado
    preparar: function () { if (nivel) ac(); },   // chamado dentro de um gesto (clique/tecla): navegadores só liberam o áudio assim
    tocar: function (nome, ms) {
      if (!nivel || !SONS[nome]) return;
      try { if (!ac()) return; SONS[nome](ctx.currentTime + 0.02, ms); } catch (e) {}
    }
  };
})();
