/* Sons da abertura de pacote (reunião), sintetizados na hora com Web Audio: não há arquivo de áudio nenhum.
   Começa DESLIGADO (a pessoa liga no botão «Som» do pacote ou na tecla S); a escolha fica guardada neste aparelho.
   Som.tocar('rasgar' | 'giro' | 'suspense' | 'ding' | 'bronze' | 'prata' | 'ouro' | 'fanfarra' | 'trovao' | 'batida', duracaoMs?) */
(function () {
  'use strict';
  var KEY = 'sentinela:som', ctx = null, mestre = null, nivel = 0;   // nivel: 0 desligado · 1 normal · 2 baixo (sala pequena / quem prefere menos volume)
  var GANHO = [0, 0.55, 0.2];
  try { var sv = localStorage.getItem(KEY); nivel = sv === '2' ? 2 : sv === '1' ? 1 : 0; } catch (e) {}

  function limitador(c, saida) {   // compressor no fim da cadeia: o acorde cheio de metais e coro não estoura
    var k = c.createDynamicsCompressor(); k.threshold.value = -16; k.knee.value = 12; k.ratio.value = 6; k.attack.value = 0.004; k.release.value = 0.25; k.connect(saida); return k;
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
  function metal(t, f, dur, pico, abre) {   // trompa/trombone: serra desafinada, filtro que «abre» no ataque
    [-7, 7].forEach(function (c) {
      var o = ctx.createOscillator(), g = ctx.createGain(), fl = ctx.createBiquadFilter(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c;
      fl.type = 'lowpass'; fl.Q.value = 1.2; fl.frequency.setValueAtTime(f * 1.5, t); fl.frequency.exponentialRampToValueAtTime(Math.min(7000, f * (abre || 6)), t + 0.16); fl.frequency.exponentialRampToValueAtTime(f * 2.2, t + dur);
      env(g, t, 0.07, dur, pico); o.connect(fl); fl.connect(g); g.connect(mestre); o.start(t); o.stop(t + dur + 0.05);
    });
  }
  function coro(t, freqs, dur, pico) {   // «aaah» de coro: serras desafinadas passando por dois formantes de vogal, com vibrato
    freqs.forEach(function (f) {
      [-9, 0, 9].forEach(function (c) {
        var o = ctx.createOscillator(), g = ctx.createGain(), l = ctx.createOscillator(), lg = ctx.createGain(), a = ctx.createBiquadFilter(), b = ctx.createBiquadFilter();
        o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c; l.frequency.value = 5.2 + Math.random(); lg.gain.value = f * 0.008; l.connect(lg); lg.connect(o.frequency);
        a.type = 'bandpass'; a.frequency.value = 800; a.Q.value = 2.2; b.type = 'bandpass'; b.frequency.value = 1250; b.Q.value = 3;
        g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(pico, t + Math.min(0.5, dur * 0.4)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        o.connect(a); o.connect(b); a.connect(g); b.connect(g); g.connect(mestre); o.start(t); l.start(t); o.stop(t + dur + 0.05); l.stop(t + dur + 0.05);
      });
    });
  }
  function prato(t, dur, pico) { sopro(t, dur, 'highpass', 5200, 9500, pico); sopro(t, dur * 0.6, 'bandpass', 7800, 6000, pico * 0.6); }
  function rufar(t, d, f, pico) {   // rufar de tímpanos que acelera e cresce até o instante t+d
    var x = 0, passo = 0.16; while (x < d - 0.02) { timpano(t + x, f, pico * (0.25 + 0.75 * x / d)); x += passo; passo = Math.max(0.045, passo * 0.9); }
  }
  var F = { D2: 73.4, A2: 110, D3: 146.8, Bb3: 233.1, C4: 261.6, D4: 293.7, F4: 349.2, Fs4: 370, G4: 392, A4: 440, Bb4: 466.2, C5: 523.3, D5: 587.3, F5: 698.5, Fs5: 740, A5: 880, D6: 1174.7, E4: 329.6 };

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
    ouro: function (t) {   // subida de metais, pancada de tímpanos e acorde de ré maior com coro e prato
      [['A4', 0], ['D5', 0.13], ['Fs5', 0.26], ['A5', 0.39]].forEach(function (n) { metal(t + n[1], F[n[0]], 0.5, 0.15); });
      timpano(t, F.D2, 1); timpano(t + 0.26, F.D2, 0.8); timpano(t + 0.52, F.D2, 0.8);
      var b = t + 0.62; timpano(b, F.D2, 1); [['D3', 0.2], ['D4', 0.18], ['A4', 0.18], ['Fs4', 0.18], ['D5', 0.2], ['Fs5', 0.15], ['A5', 0.1]].forEach(function (n) { metal(b, F[n[0]], 2.6, n[1] * 0.75, 5); });
      coro(b, [F.D3, F.A4, F.Fs4, F.D5, F.A5], 2.8, 0.035); prato(b, 2.6, 0.32); tom('sine', 55, 30, b, 1.2, 0.8);
    },
    fanfarra: function (t) {   // «tema» de campeonato: Ré menor → Si bemol → Dó → Ré maior, melodia de metais por cima e tímpanos marcando
      var P = [[['D3', 'A4', 'F4'], 'A4'], [['Bb3', 'F4', 'D4'], 'Bb4'], [['C4', 'G4', 'E4'], 'C5']];
      P.forEach(function (p, i) { var x = t + i * 0.8; timpano(x, F.D2, 0.8); coro(x, p[0].map(function (n) { return F[n]; }), 1.0, 0.028); metal(x, F[p[1]], 0.75, 0.14); metal(x, F[p[1]] / 2, 0.75, 0.1); });
      var g = t + 2.4; timpano(g, F.D2, 1); timpano(g + 0.3, F.D2, 0.8);
      [['D3', 0.2], ['D4', 0.18], ['A4', 0.18], ['Fs4', 0.18], ['D5', 0.22], ['Fs5', 0.15], ['A5', 0.12]].forEach(function (n) { metal(g, F[n[0]], 3, n[1] * 0.75, 5); });
      coro(g, [F.D3, F.A4, F.Fs4, F.D5, F.A5, F.D6], 3.2, 0.04); prato(g, 3, 0.36); tom('sine', 55, 30, g, 1.4, 0.85);
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
      return { stream: dest.stream, iniciar: function () { try { if (c.resume) c.resume(); } catch (e) {} }, tocar: function (nome, t, ms) { if (SONS[nome]) com(c, g, function () { SONS[nome](c.currentTime + 0.05 + (t || 0), ms); }); }, fechar: function () { try { c.close(); } catch (e) {} } };
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
