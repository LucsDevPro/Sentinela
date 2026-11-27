// Resumo do mês para a ata (resumo.html): pódio, números do mês, top 5, média por equipe e quem tirou 100. Sai em A4, uma página.
// Mesma ordem do álbum e da reunião: nota bruta → média dos meses anteriores → posição oficial → nome. Nada é calculado à parte: tudo vem de AGENTES_DADOS.
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var norm = function (t) { return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); };
  var br = function (v, d) { return Number(v).toFixed(d == null ? 1 : d).replace('.', ','); };
  var MESES = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  var ordMes = function (l) { var p = norm(l).split('/'); return (parseInt(p[1], 10) || 0) * 20 + MESES.indexOf(p[0]); };
  var D = window.AGENTES_DADOS, ag = D && D.agentes ? Object.keys(D.agentes).map(function (k) { return { k: k, a: D.agentes[k] }; }) : [];
  var meses = []; ag.forEach(function (x) { (x.a.meses || []).forEach(function (m) { if (meses.indexOf(m.mes) < 0) meses.push(m.mes); }); });
  meses.sort(function (p, q) { return ordMes(p) - ordMes(q); });
  var nota = function (l) { return Math.round(l.u.pontos * 10) / 10; };

  function lista(mes) {
    var L = [];
    ag.forEach(function (x) {
      var ms = (x.a.meses || []).slice().sort(function (p, q) { return ordMes(p.mes) - ordMes(q.mes); }), i = ms.map(function (m) { return m.mes; }).indexOf(mes);
      if (i < 0 || ms[i].pontos == null) return;
      var ant = ms.slice(0, i).map(function (m) { return m.pontos; }).filter(function (n) { return n != null; });
      L.push({ x: x, u: ms[i], h: ant.length ? ant.reduce(function (t, n) { return t + n; }, 0) / ant.length : -1 });
    });
    L.sort(function (p, q) { return window.Carta.bruta(q.u) - window.Carta.bruta(p.u) || q.h - p.h || (p.u.pos || 0) - (q.u.pos || 0) || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'); });
    return L;
  }
  function media(L) { return L.length ? L.reduce(function (t, l) { return t + l.u.pontos; }, 0) / L.length : 0; }
  function ini(n) { var p = String(n).trim().split(/\s+/); return (p[0][0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase(); }
  function foto(l) { var f = window.AGENTES_FOTOS && window.AGENTES_FOTOS[String(l.x.k)]; return f ? '<img src="' + esc(f) + '" alt="">' : '<span>' + esc(ini(l.x.a.nome)) + '</span>'; }

  function desenhar(mes) {
    var L = lista(mes), f = $('folha'); if (!L.length) { f.innerHTML = '<p class="vazio">Sem dados para este mês.</p>'; return; }
    var idx = meses.indexOf(mes), ant = idx > 0 ? lista(meses[idx - 1]) : [], mAnt = ant.length ? media(ant) : null, m = media(L), d = mAnt == null ? null : m - mAnt;
    var tiraram = L.filter(function (l) { return Math.round(l.u.pontos) >= 100; }), top5 = L.slice(0, 5), parcial = L.some(function (l) { return l.u.fechado === false; });
    var eqs = {}; L.forEach(function (l) { var e = l.x.a.equipe || 'Sem equipe'; (eqs[e] = eqs[e] || []).push(l); });
    var eqLinhas = Object.keys(eqs).sort(function (p, q) { return p.localeCompare(q, 'pt-BR', { numeric: true }); }).map(function (e) { var g = eqs[e]; return { e: e, n: g.length, m: media(g), c: g.filter(function (l) { return Math.round(l.u.pontos) >= 100; }).length }; });
    var melhorEq = eqLinhas.slice().sort(function (p, q) { return q.m - p.m; })[0];
    var med = ['🥇', '🥈', '🥉'];
    var pod = [1, 0, 2].filter(function (i) { return L[i]; }).map(function (i) { var l = L[i]; return '<div class="pcol p' + (i + 1) + '"><div class="foto">' + foto(l) + '</div><b class="n">' + med[i] + ' ' + (i + 1) + 'º</b><span class="nm">' + esc(l.x.a.nome) + '</span><span class="eq">' + esc(l.x.a.equipe || '') + '</span><span class="nt">' + br(nota(l)) + '</span></div>'; }).join('');
    var seta = d == null ? '' : '<small class="' + (d >= 0 ? 'up' : 'dn') + '">' + (d >= 0 ? '▲ ' : '▼ ') + br(Math.abs(d)) + ' em relação a ' + esc(meses[idx - 1]) + '</small>';
    f.innerHTML =
      '<header class="cab"><img class="logo" src="assets/logo_ponta_pora.png" alt="Prefeitura Municipal de Ponta Porã"><div><h1>Resumo do mês · ' + esc(mes) + '</h1><p>Sentinela — visitas dos agentes de campo · Ponta Porã/MS</p></div>' +
      '<span class="sit ' + (parcial ? 'parc' : 'ok') + '">' + (parcial ? 'Mês em andamento (parcial)' : 'Mês fechado') + '</span></header>' +
      '<section class="pod-s"><h2>Pódio</h2><div class="pod">' + pod + '</div></section>' +
      '<section class="nums"><div class="chip"><span>Nota média do mês</span><b>' + br(m) + '</b>' + seta + '</div><div class="chip"><span>Tiraram 100</span><b>' + tiraram.length + '</b><small>de ' + L.length + ' agentes (' + Math.round(tiraram.length * 100 / L.length) + '%)</small></div><div class="chip"><span>Média do top 5</span><b>' + br(media(top5)) + '</b><small>os cinco mais bem colocados</small></div><div class="chip"><span>Melhor equipe (média)</span><b>' + esc(melhorEq.e.replace(/^Equipe\s*/i, 'Eq. ')) + '</b><small>média ' + br(melhorEq.m) + '</small></div></section>' +
      '<div class="duas"><section><h2>Top 5</h2><table><thead><tr><th>#</th><th>Agente</th><th>Equipe</th><th class="r">Nota</th></tr></thead><tbody>' + top5.map(function (l, i) { return '<tr><td>' + (i + 1) + 'º</td><td>' + esc(l.x.a.nome) + '</td><td>' + esc(l.x.a.equipe || '') + '</td><td class="r">' + br(nota(l)) + '</td></tr>'; }).join('') + '</tbody></table></section>' +
      '<section><h2>Média por equipe</h2><table><thead><tr><th>Equipe</th><th class="r">Agentes</th><th class="r">Média</th><th class="r">Nota 100</th></tr></thead><tbody>' + eqLinhas.map(function (e) { return '<tr><td>' + esc(e.e) + '</td><td class="r">' + e.n + '</td><td class="r">' + br(e.m) + '</td><td class="r">' + e.c + '</td></tr>'; }).join('') + '</tbody></table></section></div>' +
      '<section class="cem"><h2>Tiraram 100 (' + tiraram.length + ')</h2>' + (tiraram.length ? '<ol>' + tiraram.map(function (l) { return '<li><span>' + esc(l.x.a.nome) + '</span> <i>' + esc((l.x.a.equipe || '').replace(/^Equipe\s*/i, 'Eq. ')) + '</i></li>'; }).join('') + '</ol>' : '<p class="mut">Ninguém chegou a 100 neste mês.</p>') + '</section>' +
      '<section class="obs"><h2>Anotações da reunião</h2><div class="linha"></div><div class="linha"></div><div class="linha"></div></section>' +
      '<footer class="rod">Ordem: nota (sem teto de 100); em empate, a nota bruta, depois a média dos meses anteriores, depois a posição oficial. Gerado em ' + new Date().toLocaleDateString('pt-BR') + ' a partir dos dados publicados no Sentinela.</footer>';
    document.title = 'Resumo ' + mes + ' — Sentinela';
  }

  if (!meses.length || !window.Carta) { $('folha').innerHTML = '<p class="vazio">Ainda não há dados. Volte depois da próxima atualização do site.</p>'; return; }
  $('fMes').innerHTML = meses.slice().reverse().map(function (m) { return '<option>' + esc(m) + '</option>'; }).join('');
  var q = new URLSearchParams(location.search).get('mes'); if (q && meses.indexOf(q) >= 0) $('fMes').value = q;
  $('fMes').onchange = function () { history.replaceState(null, '', '?mes=' + encodeURIComponent($('fMes').value)); desenhar($('fMes').value); };
  $('bImprimir').onclick = function () { window.print(); };
  $('bXls').onclick = function () { exportarPlanilha($('folha').querySelectorAll('table'), 'Resumo do mes ' + $('fMes').value); };   // assets/xls.js: uma aba por tabela da folha
  desenhar($('fMes').value);
  window.RESUMO = { lista: lista, desenhar: desenhar };
})();
