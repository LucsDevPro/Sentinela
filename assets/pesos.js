/* Simulador de pesos (pesos.html): só simula, nunca grava.
   Nota simulada = nota bruta + Σ inclinação × (peso novo − peso atual), com piso/teto da regra.
   (Os dados vêm de scripts/gerar_simulador_pesos.py; scripts/test_simulador_pesos.py prova que bate com o cálculo real.) */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var D = window.SIMULADOR_PESOS;
  var novos = {}, atuais = {};
  function fmt(n, c) { return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: c == null ? 2 : c, maximumFractionDigits: c == null ? 2 : c }); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function valido(v) { return typeof v === 'number' && isFinite(v) && v >= 0 && v <= D.limite_max; }
  function lerInput(el) { var t = el.value.replace(',', '.').trim(); return t === '' ? NaN : Number(t); }

  function simular(ag) {
    var n = ag.bruta;
    Object.keys(novos).forEach(function (k) { if (valido(novos[k])) n += ag.inc[k] * (novos[k] - atuais[k]); });
    if (ag.maximo !== null && ag.maximo !== undefined) n = Math.min(n, ag.maximo);
    if (ag.minimo !== null && ag.minimo !== undefined) n = Math.max(n, ag.minimo);
    return Math.round(n * 100) / 100;
  }

  function desenharPesos() {
    var html = '';
    ['perdas', 'ganhos'].forEach(function (g) {
      html += '<div class="grupo">' + (g === 'perdas' ? 'Perdas (pontos tirados)' : 'Ganhos (pontos somados)') + '</div>';
      Object.keys(D.pesos).filter(function (k) { return D.pesos[k].grupo === g; }).forEach(function (k) {
        var p = D.pesos[k];
        html += '<div class="peso" data-k="' + k + '"><label for="p_' + k + '">' + esc(p.rotulo) + '</label>' +
          '<input id="p_' + k + '" data-k="' + k + '" inputmode="decimal" value="' + String(atuais[k]).replace('.', ',') + '" aria-describedby="d_' + k + '">' +
          '<span class="desc" id="d_' + k + '">' + esc(p.descricao) + '</span><span class="ref">atual: ' + fmt(atuais[k], 2) + '</span></div>';
      });
    });
    $('pesos').innerHTML = html;
    $('pesos').addEventListener('input', function (e) {
      var el = e.target; if (!el.dataset.k) return;
      novos[el.dataset.k] = lerInput(el); marcar(el.dataset.k); desenharRank();
    });
  }
  function marcar(k) {
    var linha = document.querySelector('.peso[data-k="' + k + '"]');
    linha.classList.toggle('invalido', !valido(novos[k]));
    linha.classList.toggle('mudou', valido(novos[k]) && novos[k] !== atuais[k]);
  }

  function seta(delta) { return delta > 0 ? '<span class="sobe">▲ ' + delta + '</span>' : delta < 0 ? '<span class="desce">▼ ' + (-delta) + '</span>' : '<span class="igual">=</span>'; }

  function desenharRank() {
    var mes = D.meses.filter(function (m) { return m.label === $('fMes').value; })[0];
    var ags = mes.agentes.map(function (a, i) { return { a: a, i: i, atual: a.pontos, sim: simular(a) }; });
    var porAtual = ags.slice().sort(function (x, y) { return y.atual - x.atual || x.i - y.i; });
    porAtual.forEach(function (x, i) { x.posAtual = i + 1; });
    var porSim = ags.slice().sort(function (x, y) { return y.sim - x.sim || x.posAtual - y.posAtual; });
    porSim.forEach(function (x, i) { x.posSim = i + 1; x.mov = x.posAtual - x.posSim; x.dn = Math.round((x.sim - x.atual) * 100) / 100; });
    var mudaram = porSim.filter(function (x) { return x.mov !== 0; }).length;
    var alta = porSim.reduce(function (m, x) { return x.dn > m.dn ? x : m; }, porSim[0]);
    var queda = porSim.reduce(function (m, x) { return x.dn < m.dn ? x : m; }, porSim[0]);
    var mediaA = ags.reduce(function (s, x) { return s + x.atual; }, 0) / ags.length, mediaS = ags.reduce(function (s, x) { return s + x.sim; }, 0) / ags.length;
    var sem = !Object.keys(novos).some(function (k) { return valido(novos[k]) && novos[k] !== atuais[k]; });
    $('resumo').innerHTML = sem ? '<div class="kpi"><b>' + ags.length + '</b><span>agentes no mês — mude um peso para simular</span></div>' :
      '<div class="kpi"><b>' + mudaram + '</b><span>mudam de posição</span></div>' +
      '<div class="kpi"><b>' + (alta.dn > 0 ? '+' : '') + fmt(alta.dn) + '</b><span>maior alta (' + esc(alta.a.nome.split(' ')[0]) + ')</span></div>' +
      '<div class="kpi"><b>' + fmt(queda.dn) + '</b><span>maior queda (' + esc(queda.a.nome.split(' ')[0]) + ')</span></div>' +
      '<div class="kpi"><b>' + fmt(mediaS - mediaA) + '</b><span>variação da média (' + fmt(mediaA) + ' → ' + fmt(mediaS) + ')</span></div>';
    $('rank').querySelector('tbody').innerHTML = porSim.map(function (x) {
      return '<tr class="' + (x.mov !== 0 || x.dn !== 0 ? 'mudou' : '') + '"><td><span class="pos">' + x.posSim + 'º ' + seta(x.mov) + '</span></td>' +
        '<td>' + esc(x.a.nome) + '</td><td>' + esc(x.a.equipe) + '</td><td class="n">' + fmt(x.atual) + '</td><td class="n"><b>' + fmt(x.sim) + '</b></td>' +
        '<td class="n delta ' + (x.dn > 0 ? 'sobe' : x.dn < 0 ? 'desce' : '') + '">' + (x.dn > 0 ? '+' : '') + fmt(x.dn) + '</td></tr>';
    }).join('');
  }

  function jsonPesos() {
    var o = { _aviso: "Pesos da pontuação. Edite só o campo 'valor'. Mudar aqui muda a nota de TODOS os meses ao regenerar. Nomes = constantes de scripts/coleta/pontos.py.", pesos: {} };
    Object.keys(D.pesos).forEach(function (k) { var p = D.pesos[k]; o.pesos[k] = { rotulo: p.rotulo, valor: valido(novos[k]) ? novos[k] : atuais[k], grupo: p.grupo, descricao: p.descricao }; });
    return JSON.stringify(o, null, 2) + '\n';
  }

  function iniciar() {
    if (!D || !D.meses || !D.meses.length) {
      $('aviso').className = 'aviso erro';
      $('aviso').innerHTML = '<b>Sem dados para simular.</b> Rode <code>python3 scripts/gerar_simulador_pesos.py</code> (o workflow faz isso sozinho).';
      return;
    }
    Object.keys(D.pesos).forEach(function (k) { atuais[k] = D.pesos[k].valor; novos[k] = atuais[k]; });
    var sel = $('fMes'), url = new URLSearchParams(location.search).get('mes');
    sel.innerHTML = D.meses.map(function (m) { return '<option>' + esc(m.label) + '</option>'; }).join('');
    sel.value = (url && D.meses.some(function (m) { return m.label === url; })) ? url : D.meses[D.meses.length - 1].label;
    sel.addEventListener('change', desenharRank);
    $('gerado').textContent = 'dados de ' + D.gerado_em;
    $('rodape').textContent = 'A nota "atual" é recalculada com os pesos oficiais de hoje; meses fechados só mudam de verdade quando forem regenerados.';
    desenharPesos(); desenharRank();
    $('bZerar').onclick = function () { Object.keys(atuais).forEach(function (k) { novos[k] = atuais[k]; document.getElementById('p_' + k).value = String(atuais[k]).replace('.', ','); marcar(k); }); desenharRank(); };
    $('bCopiar').onclick = function () {
      var t = jsonPesos(), b = $('bCopiar');
      (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { b.textContent = 'Copiado!'; }, function () { window.prompt('Copie o JSON dos pesos:', t); });
      setTimeout(function () { b.textContent = 'Copiar pesos (JSON)'; }, 1800);
    };
  }
  iniciar();
})();
