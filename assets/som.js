/* Sons da abertura de pacote (reunião), sintetizados na hora com Web Audio: não há arquivo de áudio nenhum.
   Começa DESLIGADO (a pessoa liga no botão «Som» do pacote ou na tecla S); a escolha fica guardada neste aparelho.
   Som.tocar('rasgar' | 'giro' | 'suspense' | 'ding' | 'bronze' | 'prata' | 'ouro' | 'fanfarra' | 'trovao', duracaoMs?) */
(function () {
  'use strict';
  var KEY = 'sentinela:som', ctx = null, mestre = null, on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}

  function ac() {
    if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return ctx; }
    var C = window.AudioContext || window.webkitAudioContext; if (!C) return null;
    ctx = new C(); mestre = ctx.createGain(); mestre.gain.value = 0.55; mestre.connect(ctx.destination); return ctx;
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

  var SONS = {
    rasgar: function (t) { sopro(t, 0.55, 'highpass', 900, 5200, 0.5); sopro(t + 0.05, 0.35, 'bandpass', 3000, 900, 0.35); tom('sine', 120, 45, t, 0.4, 0.5); },
    giro: function (t, ms) { sopro(t, (ms || 900) / 1000, 'bandpass', 500, 2600, 0.28); },
    suspense: function (t, ms) {   // tom que sobe, com tremor, até o instante da revelação
      var d = (ms || 1500) / 1000, o = ctx.createOscillator(), g = ctx.createGain(), l = ctx.createOscillator(), lg = ctx.createGain();
      o.type = 'sawtooth'; o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(520, t + d);
      l.frequency.setValueAtTime(5, t); l.frequency.linearRampToValueAtTime(18, t + d); lg.gain.value = 0.18; l.connect(lg); lg.connect(g.gain);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.22, t + d * 0.9); g.gain.exponentialRampToValueAtTime(0.0001, t + d + 0.05);
      var f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.setValueAtTime(400, t); f.frequency.exponentialRampToValueAtTime(3500, t + d);
      o.connect(f); f.connect(g); g.connect(mestre); o.start(t); l.start(t); o.stop(t + d + 0.1); l.stop(t + d + 0.1);
    },
    ding: function (t) { tom('sine', 880, 0, t, 0.5, 0.35); tom('sine', 1320, 0, t + 0.08, 0.6, 0.28); tom('triangle', 1760, 0, t + 0.16, 0.5, 0.12); },
    bronze: function (t) { tom('sine', 90, 40, t, 0.5, 0.7); acorde(t, ['C4', 'E4', 'G4'], 'triangle', 0.9, 0.25); sopro(t, 0.5, 'highpass', 4000, 6000, 0.18); },
    prata: function (t) { tom('sine', 100, 40, t, 0.6, 0.8); acorde(t, ['C4', 'G4', 'C5', 'E5'], 'triangle', 1.1, 0.25); sopro(t, 0.8, 'highpass', 3500, 7000, 0.25); },
    ouro: function (t) {
      tom('sine', 110, 35, t, 0.9, 0.95); sopro(t, 1.2, 'highpass', 2500, 8000, 0.4);
      acorde(t, ['C4', 'E4', 'G4', 'C5', 'E5', 'G5'], 'sawtooth', 1.8, 0.14); acorde(t + 0.02, ['C5', 'E5', 'G5', 'C6'], 'triangle', 1.8, 0.2);
    },
    fanfarra: function (t) {
      [['C5', 0], ['E5', 0.16], ['G5', 0.32], ['C6', 0.5]].forEach(function (n) { tom('square', NOTA[n[0]], 0, t + n[1], 0.45, 0.16); tom('triangle', NOTA[n[0]] / 2, 0, t + n[1], 0.45, 0.2); });
      acorde(t + 0.75, ['C5', 'E5', 'G5', 'C6'], 'sawtooth', 1.6, 0.12); sopro(t + 0.75, 1.2, 'highpass', 3000, 9000, 0.3);
    },
    trovao: function (t) {   // estalo seco do raio + trovoada grave que rola
      sopro(t, 0.22, 'highpass', 2500, 9000, 0.6); tom('sine', 70, 30, t, 0.5, 0.7);
      sopro(t + 0.12, 1.9, 'lowpass', 520, 70, 0.75); sopro(t + 0.7, 1.4, 'lowpass', 380, 60, 0.5); tom('sine', 48, 28, t + 0.2, 1.5, 0.5);
    }
  };

  window.Som = {
    ligado: function () { return on; },
    ligar: function (v) { on = !!v; try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {} if (on) { ac(); this.tocar('ding'); } return on; },
    alternar: function () { return this.ligar(!on); },
    preparar: function () { if (on) ac(); },   // chamado dentro de um gesto (clique/tecla): navegadores só liberam o áudio assim
    tocar: function (nome, ms) {
      if (!on || !SONS[nome]) return;
      try { if (!ac()) return; SONS[nome](ctx.currentTime + 0.02, ms); } catch (e) {}
    }
  };
})();
