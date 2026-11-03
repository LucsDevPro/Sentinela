function goToSection(id) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.section === id));
  document.querySelectorAll('.section').forEach(s => s.classList.toggle('active', s.id === id));
  document.querySelector('.container').scrollIntoView({ behavior: 'smooth' });
  if (id === 'alertas') carregarAlertas();
}
/* ===== Carregamento sob demanda (tabelas de alertas e extratos) =====
   Usa <script> (e não fetch) pra funcionar também com o arquivo aberto direto do disco. */
function _carregarScript(src) {
  return new Promise((ok, erro) => {
    const s = document.createElement('script');
    s.src = src; s.onload = ok; s.onerror = erro;
    document.head.appendChild(s);
  });
}
let _pAlertas = null;
function carregarAlertas() {
  const box = document.getElementById('alertas-conteudo');
  if (!box || box.dataset.carregado) return Promise.resolve();
  if (_pAlertas) return _pAlertas;
  _pAlertas = _carregarScript(box.dataset.src).then(() => {
    box.innerHTML = (window.SENT_PARTES || {}).alertas || '';
    box.dataset.carregado = '1';
    initTabelas(box);
  }).catch(() => {
    _pAlertas = null;
    box.innerHTML = '<p class="table-hint">Não foi possível carregar as tabelas de alertas. Atualize a página.</p>';
  });
  return _pAlertas;
}
let _pExtratos = null;
function carregarExtratos() {
  if (window.EXTRATOS || !window.EXTRATOS_SRC) return Promise.resolve();
  if (_pExtratos) return _pExtratos;
  _pExtratos = _carregarScript(window.EXTRATOS_SRC).catch(() => { _pExtratos = null; });
  return _pExtratos;
}
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => goToSection(tab.dataset.section));
});
function applyFilters() {
  const eq = document.getElementById('filterEquipe').value;
  const cl = document.getElementById('filterClass').value;
  const name = document.getElementById('filterName').value.toLowerCase();
  const semSel = document.getElementById('filterSemana');
  const sem = semSel ? semSel.value : 'todas';
  document.querySelectorAll('#tableAgentes tbody tr').forEach(tr => {
    const matchEq = !eq || tr.dataset.equipe === eq;
    const matchCl = !cl || (tr.dataset.class || '').includes(cl);
    const matchName = !name || tr.cells[0].textContent.toLowerCase().includes(name);
    const matchSemana = tr.dataset.semana === sem;
    tr.style.display = (matchEq && matchCl && matchName && matchSemana) ? '' : 'none';
  });
}
document.getElementById('filterEquipe').addEventListener('change', applyFilters);
document.getElementById('filterClass').addEventListener('change', applyFilters);
document.getElementById('filterName').addEventListener('input', applyFilters);
if (document.getElementById('filterSemana')) {
  document.getElementById('filterSemana').addEventListener('change', applyFilters);
}
function showAlert(id) {
  carregarAlertas().then(() => { const el = document.getElementById('alert-' + id); if (el) el.scrollIntoView({ behavior: 'smooth' }); });
}
/* ===== Filtro aba Área ===== */
function applyAreaFilters() {
  const areaSel = document.getElementById('filterAreaArea');
  const nameSel = document.getElementById('filterAreaName');
  if (!areaSel || !nameSel) return;
  const ar = areaSel.value;
  const name = nameSel.value.toLowerCase();
  document.querySelectorAll('#tableAreas tbody tr').forEach(tr => {
    const matchArea = !ar || tr.dataset.area === ar;
    const matchName = !name || tr.cells[0].textContent.toLowerCase().includes(name);
    tr.style.display = (matchArea && matchName) ? '' : 'none';
  });
}
const filterAreaAreaEl = document.getElementById('filterAreaArea');
const filterAreaNameEl = document.getElementById('filterAreaName');
if (filterAreaAreaEl) filterAreaAreaEl.addEventListener('change', applyAreaFilters);
if (filterAreaNameEl) filterAreaNameEl.addEventListener('input', applyAreaFilters);

/* ===== Ordenação estilo Excel (clique no cabeçalho) ===== */
function parseCellValue(text) {
  const t = text.trim();
  if (t === '' || t === '—') return { num: null, text: '' };
  // Data(s) no padrão dd/mm/aaaa, com ou sem hora (ex.: "17/07/2026" ou
  // "17/07/2026 14:30"), inclusive períodos "dd/mm/aaaa a dd/mm/aaaa" (usa a
  // primeira data do período pra ordenar). Convertida pra AAAAMMDDHHMM —
  // um número que ordena CRONOLOGICAMENTE (ano, depois mês, depois dia),
  // ao contrário do texto puro "dd/mm/aaaa", que ordenaria pelo DIA primeiro
  // (é o que aparece mais à esquerda na string) e ignoraria mês/ano.
  const dataMatch = t.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
  if (dataMatch) {
    const [, dd, mm, yyyy, hh, min] = dataMatch;
    const num = parseInt(yyyy + mm + dd + (hh || '00') + (min || '00'), 10);
    if (!isNaN(num)) return { num, text: t.toLowerCase() };
  }
  // tenta número no padrão pt-BR: "1.234,56" | "12,3%" | "R$ 93,80" | "225"
  let clean = t.replace(/^R\$\s?/, '').replace(/%$/, '').trim();
  clean = clean.replace(/^\+/, '');
  if (/^-?[\d.,]+$/.test(clean)) {
    clean = clean.replace(/\./g, '').replace(',', '.');
    const num = parseFloat(clean);
    if (!isNaN(num)) return { num, text: t.toLowerCase() };
  }
  return { num: null, text: t.toLowerCase() };
}
function sortTableBy(table, colIndex, th) {
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const currentDir = th.dataset.sortDir === 'desc' ? 'asc' : 'desc'; // primeiro clique = maior→menor, igual Excel
  table.querySelectorAll('thead th').forEach(h => { h.dataset.sortDir = ''; h.classList.remove('sorted-asc', 'sorted-desc'); });
  th.dataset.sortDir = currentDir;
  th.classList.add(currentDir === 'asc' ? 'sorted-asc' : 'sorted-desc');
  rows.sort((ra, rb) => {
    const ca = ra.cells[colIndex], cb = rb.cells[colIndex];
    if (!ca || !cb) return 0;
    const va = parseCellValue(ca.textContent);
    const vb = parseCellValue(cb.textContent);
    let cmp;
    if (va.num !== null && vb.num !== null) cmp = va.num - vb.num;
    else cmp = va.text.localeCompare(vb.text, 'pt-BR');
    return currentDir === 'asc' ? cmp : -cmp;
  });
  rows.forEach(r => tbody.appendChild(r));
}

/* ===== Filtro genérico (Agente + Equipe) e botão Imprimir em TODAS as tabelas ===== */
function findColIndex(table, headerText) {
  const ths = table.querySelectorAll('thead th');
  for (let i = 0; i < ths.length; i++) {
    if (ths[i].textContent.trim() === headerText) return i;
  }
  return -1;
}
// Marca tabelas com muitas colunas pra o CSS de impressão usar fonte menor
// (ver .print-wide em style.css) — sem isso, 29 colunas não cabem na folha.
function printPrepararTabelas() {
  document.querySelectorAll('table.data-table').forEach(t => {
    const n = t.querySelectorAll('thead th').length;
    t.classList.toggle('print-wide', n > 12);
    t.classList.toggle('print-muito-wide', n > 24);
  });
  // A 1ª tabela de cada aba NÃO quebra página antes (o seletor :first-of-type
  // do CSS não pega, porque os KPIs/gráficos da aba também são <div>) — sem
  // isso os KPIs ficavam sozinhos numa folha e a tabela vinha na seguinte.
  document.querySelectorAll('.section').forEach(sec => {
    const primeira = sec.querySelector(':scope > .table-section');
    sec.querySelectorAll(':scope > .table-section').forEach(t => t.classList.toggle('print-first', t === primeira));
  });
  // Legendas recolhidas (<details>) saem ABERTAS no papel; o estado é restaurado depois.
  document.querySelectorAll('details:not([open])').forEach(d => { d.dataset.fechadoPorImpressao = '1'; d.open = true; });
}
function printRestaurarDetails() {
  document.querySelectorAll('details[data-fechado-por-impressao]').forEach(d => {
    d.open = false; delete d.dataset.fechadoPorImpressao;
  });
}
function printSection(section) {
  printPrepararTabelas();
  document.querySelectorAll('.table-section.print-target').forEach(el => el.classList.remove('print-target'));
  section.classList.add('print-target');
  document.body.classList.add('print-mode');
  window.print();
}
function printFullReport() {
  // As tabelas de alertas carregam sob demanda: garante que estão na página antes de imprimir.
  carregarAlertas().then(() => {
    printPrepararTabelas();
    document.body.classList.add('print-mode-full');
    window.print();
  });
}
/* ===== Extrato por agente: folha com a conta da pontuação ===== */
function _esc(v) {
  return String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function _fmt(n, d) {
  if (n == null || n === '' || isNaN(Number(n))) return '—';
  return Number(n).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function abrirExtrato(nome) {
  carregarExtratos().then(() => _mostrarExtrato(nome));
}
function _extratoHtml(nome, comContestar) {
  const E = window.EXTRATOS || {};
  const a = (E.agentes || {})[nome];
  if (!a) return '';
  const oculto = document.body.classList.contains('modo-apresentacao');
  const semNorm = !!E.sem_normalizacao;
  const soma = (a.detalhes || []).reduce((t, d) => t + (Number(d.pontos) || 0), 0);
  const bruto = (E.pontos_iniciais || 100) + soma;
  const ajuste = Number(a.pontos) - bruto;
  const linhas = (a.detalhes || []).map(d => {
    const p = Number(d.pontos) || 0;
    const cols = semNorm
      ? `<td class="num">${_fmt(d.qtd, 0)}</td><td class="num">${_fmt(d.peso_nominal, 2)}</td>`
      : `<td class="num">${_fmt(d.qtd, 0)}</td><td class="num">${_fmt(d.peso_nominal, 2)}</td><td class="num">${_fmt(d.fator, 2)}</td><td class="num">${_fmt(d.peso, 2)}</td>`;
    return `<tr><td>${_esc(d.criterio)}</td>${cols}<td class="num ${p < 0 ? 'neg' : (p > 0 ? 'pos' : '')}">${p > 0 ? '+' : ''}${_fmt(p, 2)}</td></tr>`;
  }).join('');
  const cab = semNorm
    ? '<th>Critério</th><th>Quantidade</th><th>Peso</th><th>Pontos</th>'
    : '<th>Critério</th><th>Quantidade</th><th>Peso nominal</th><th>Fator</th><th>Peso efetivo</th><th>Pontos</th>';
  const nCols = semNorm ? 3 : 5;
  const metodo = semNorm
    ? 'Sem fator de normalização: todos os agentes usam o mesmo peso. Pontos = quantidade × peso.'
    : 'Com fator de normalização: peso efetivo = peso nominal × fator (ajuste pelo número de dias trabalhados no período).';
  return `
    <h2>Extrato de pontuação</h2>
    <div class="ex-sub">${oculto ? 'Agente (oculto no modo apresentação)' : _esc(a.agente)} · ${_esc(a.equipe)} · ${_esc(E.periodo || '')}</div>
    <div class="ex-resumo">
      <div><span>Posição</span><strong>${_fmt(a.posicao, 0)}º de ${_fmt(E.total_agentes, 0)}</strong></div>
      <div><span>Pontuação final</span><strong>${_fmt(a.pontos, 1)}</strong><em>${_esc(a.classificacao)}</em></div>
      <div><span>Dias trabalhados</span><strong>${_fmt(a.dias_trabalhados, 0)} de ${_fmt(a.dias_esperados, 0)} esperados</strong></div>
      <div><span>Turnos sem trabalhar</span><strong>${_fmt(a.turnos_sem, 0)}</strong></div>
    </div>
    ${a.observacao ? `<div class="ex-obs">${_esc(a.observacao)}</div>` : ''}
    <table class="ex-tabela">
      <thead><tr>${cab}</tr></thead>
      <tbody>
        <tr class="ex-base"><td colspan="${nCols}">Pontos iniciais</td><td class="num">${_fmt(E.pontos_iniciais || 100, 2)}</td></tr>
        ${linhas}
        ${Math.abs(ajuste) > 0.011 ? `<tr class="ex-base"><td colspan="${nCols}">Limite aplicado (a pontuação fica entre 0 e 100)</td><td class="num">${ajuste > 0 ? '+' : ''}${_fmt(ajuste, 2)}</td></tr>` : ''}
        <tr class="ex-total"><td colspan="${nCols}">Pontuação final</td><td class="num">${_fmt(a.pontos, 2)}</td></tr>
      </tbody>
    </table>
    <p class="ex-nota">${_esc(metodo)} Faixas: 🟢 ≥90 · 🟡 75–89,9 · 🟠 60–74,9 · 🔴 &lt;60. Dias esperados já descontam férias, folga, ausência justificada, chuva e reuniões registrados no cronograma (método novo). <a href="${_esc(window.TRANSPARENCIA_HREF || 'transparencia.html')}" target="_blank" rel="noopener">Como o ranking é calculado</a>.${comContestar && window.AGENTE_HREF && !oculto ? ` <a href="${_esc(window.AGENTE_HREF)}?nome=${encodeURIComponent(a.agente)}" target="_blank" rel="noopener">Ver minha evolução</a>` : ''}</p>
    ${comContestar ? _blocoContestar(a, E) : ''}`;
}
function _mostrarExtrato(nome) {
  const html = _extratoHtml(nome, true);
  if (!html) return;
  document.getElementById('extratoConteudo').innerHTML = html;
  document.getElementById('extratoOverlay').classList.add('open');
  document.body.classList.add('extrato-aberto');
}

/* ===== Contestação (só quando o serviço de lançamentos está configurado e o mês está aberto) ===== */
function _blocoContestar(a, E) {
  if (!window.WORKER_URL || !E.mes || !a.id_agente) return '';
  const criterios = [...new Set((a.detalhes || []).filter(d => Number(d.pontos) < 0).map(d => d.criterio))].slice(0, 30);
  const opts = criterios.map(c => `<option>${_esc(String(c).slice(0, 80))}</option>`).join('') + '<option>Outro / não sei dizer</option>';
  return `<div class="ex-contestar no-print">
    <details><summary>Algo errado? Peça uma revisão</summary>
      <p class="ex-nota">Escolha o critério e explique em uma frase. A coordenação responde; guarde o código para ver a resposta. Não escreva dados de saúde.</p>
      <label>Critério<select id="ctCriterio">${opts}</select></label>
      <label>O que está errado? <input id="ctTexto" maxlength="240" placeholder="Ex.: Estava em reunião na manhã do dia 14"></label>
      <input id="ctHp" tabindex="-1" autocomplete="off" aria-hidden="true" style="position:absolute;left:-9999px">
      <button type="button" class="extrato-fechar" onclick="enviarContestacao(${Number(a.id_agente)})">Enviar pedido</button>
      <div id="ctMsg" class="ex-nota" role="status"></div>
    </details></div>`;
}
async function enviarContestacao(idAgente) {
  const E = window.EXTRATOS || {}, msg = document.getElementById('ctMsg');
  const corpo = { id_agente: idAgente, mes: E.mes, criterio: document.getElementById('ctCriterio').value,
    texto: document.getElementById('ctTexto').value.trim(), hp: document.getElementById('ctHp').value };
  msg.textContent = 'Enviando…';
  try {
    const r = await fetch(String(window.WORKER_URL).replace(/\/$/, '') + '/contestar', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.erro || 'Não consegui enviar agora.');
    msg.innerHTML = `✅ Pedido enviado. Seu código: <strong>${_esc(j.codigo)}</strong> (anote). Consulte a resposta em <a href="${_esc(window.CONTESTACAO_HREF || 'contestacao.html')}?codigo=${_esc(j.codigo)}" target="_blank" rel="noopener">contestacao.html</a>.`;
  } catch (e) { msg.textContent = '❌ ' + e.message; }
}

/* ===== Impressão em lote: uma folha por agente ===== */
function imprimirExtratosLote(equipe) {
  carregarExtratos().then(() => {
    const E = window.EXTRATOS || {};
    const nomes = Object.keys(E.agentes || {}).filter(n => !equipe || E.agentes[n].equipe === equipe)
      .sort((x, y) => (E.agentes[x].posicao || 999) - (E.agentes[y].posicao || 999));
    if (!nomes.length) { alert('Nenhum agente encontrado para imprimir.'); return; }
    const antigo = document.getElementById('extratosLote'); if (antigo) antigo.remove();
    const cont = document.createElement('div');
    cont.id = 'extratosLote';
    cont.innerHTML = nomes.map(n => `<section class="ex-folha">${_extratoHtml(n, false)}</section>`).join('');
    document.body.appendChild(cont);
    document.body.classList.add('print-lote');
    window.print();
  });
}
function fecharExtrato() {
  document.getElementById('extratoOverlay').classList.remove('open');
  document.body.classList.remove('extrato-aberto');
}
function imprimirExtrato() {
  document.body.classList.add('print-extrato');
  window.print();
}
document.addEventListener('click', e => {
  const b = e.target.closest('.extrato-btn');
  if (b) { abrirExtrato(b.dataset.agente); return; }
  if (e.target.id === 'extratoOverlay') fecharExtrato();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharExtrato(); });

window.addEventListener('afterprint', () => {
  printRestaurarDetails();
  document.body.classList.remove('print-extrato');
  document.body.classList.remove('print-lote');
  const lote = document.getElementById('extratosLote'); if (lote) lote.remove();
  document.body.classList.remove('print-mode');
  document.body.classList.remove('print-mode-full');
  document.querySelectorAll('.table-section.print-target').forEach(el => el.classList.remove('print-target'));
});
const presentationToggle = document.getElementById('togglePresentationMode');
if (presentationToggle) {
  presentationToggle.addEventListener('change', () => {
    document.body.classList.toggle('modo-apresentacao', presentationToggle.checked);
  });
}
function buildGenericFilters(section) {
  const table = section.querySelector('table');
  if (!table) return;
  const equipeIdx = findColIndex(table, 'Equipe');
  const agenteIdx = findColIndex(table, 'Agente');
  let filterBar = section.querySelector('.filters');
  const hasOwnFilters = !!filterBar;

  if (!hasOwnFilters && (equipeIdx > -1 || agenteIdx > -1)) {
    filterBar = document.createElement('div');
    filterBar.className = 'filters';
    let html = '';
    if (equipeIdx > -1) {
      const equipes = new Set();
      table.querySelectorAll('tbody tr').forEach(tr => {
        const v = tr.cells[equipeIdx] ? tr.cells[equipeIdx].textContent.trim() : '';
        if (v) equipes.add(v);
      });
      html += `<select class="gen-filter-equipe"><option value="">Todas as equipes</option>${[...equipes].sort().map(e => `<option>${e}</option>`).join('')}</select>`;
    }
    if (agenteIdx > -1) {
      html += `<input type="text" class="gen-filter-name" placeholder="Buscar agente...">`;
    }
    filterBar.innerHTML = html;
    const wrap = section.querySelector('.table-wrap');
    section.insertBefore(filterBar, wrap);
  }

  if (filterBar && !filterBar.querySelector('.print-btn')) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'print-btn';
    btn.innerHTML = '<svg class="ico" aria-hidden="true"><use href="#i-print"/></svg> Imprimir';
    btn.addEventListener('click', () => printSection(section));
    filterBar.appendChild(btn);
  }

  if (!hasOwnFilters && filterBar) {
    const eqSel = filterBar.querySelector('.gen-filter-equipe');
    const nameInput = filterBar.querySelector('.gen-filter-name');
    function apply() {
      const eqVal = eqSel ? eqSel.value : '';
      const nameVal = nameInput ? nameInput.value.toLowerCase() : '';
      table.querySelectorAll('tbody tr').forEach(tr => {
        const eqOk = !eqVal || (equipeIdx > -1 && tr.cells[equipeIdx] && tr.cells[equipeIdx].textContent.trim() === eqVal);
        const nameOk = !nameVal || (agenteIdx > -1 && tr.cells[agenteIdx] && tr.cells[agenteIdx].textContent.toLowerCase().includes(nameVal));
        tr.style.display = ((eqVal ? eqOk : true) && (nameVal ? nameOk : true)) ? '' : 'none';
      });
    }
    if (eqSel) eqSel.addEventListener('change', apply);
    if (nameInput) nameInput.addEventListener('input', apply);
  }
}
function initTabelas(raiz) {
  raiz.querySelectorAll('table.sortable').forEach(table => {
    if (table.dataset.ordenavel) return;
    table.dataset.ordenavel = '1';
    table.querySelectorAll('thead th').forEach((th, idx) => {
      th.addEventListener('click', () => sortTableBy(table, idx, th));
    });
  });
  raiz.querySelectorAll('.table-section').forEach(sec => {
    if (sec.dataset.filtros) return;
    sec.dataset.filtros = '1';
    buildGenericFilters(sec);
  });
}
initTabelas(document);

/* ===== Filtro aba Ausências (equipe/turno/dia/nome + ocultar "todos ausentes") ===== */
function applyAusFilters() {
  const eq = document.getElementById('filterAusEquipe').value;
  const tn = document.getElementById('filterAusTurno').value;
  const dw = document.getElementById('filterAusDia').value;
  const name = document.getElementById('filterAusName').value.toLowerCase();
  const hideAllAbsent = document.getElementById('filterAusHideAllAbsent').checked;
  document.querySelectorAll('#tableAusencias tbody tr').forEach(tr => {
    const c = tr.cells;
    const matchEq = !eq || c[1].textContent === eq;
    const matchTn = !tn || c[4].textContent === tn;
    const matchDw = !dw || c[3].textContent === dw;
    const matchName = !name || c[0].textContent.toLowerCase().includes(name);
    const matchAllAbsent = !hideAllAbsent || tr.dataset.allabsent !== '1';
    tr.style.display = (matchEq && matchTn && matchDw && matchName && matchAllAbsent) ? '' : 'none';
  });
}
['filterAusEquipe','filterAusTurno','filterAusDia'].forEach(id => document.getElementById(id).addEventListener('change', applyAusFilters));
document.getElementById('filterAusName').addEventListener('input', applyAusFilters);
document.getElementById('filterAusHideAllAbsent').addEventListener('change', applyAusFilters);

/* ===== Ausências: mapa de calor ===== */
(function renderAusHeatmap(){
  const el = document.getElementById('heatmapAus');
  if (!el) return;
  const heat = JSON.parse(el.dataset.heat);
  const diaOrder = ['Segunda','Terça','Quarta','Quinta','Sexta'];
  const max = Math.max(1, ...diaOrder.flatMap(d => [heat[d]['Manhã'], heat[d]['Tarde']]));
  function color(v){
    const ratio = v / max;
    const r = Math.round(0 + (228-0)*ratio), g = Math.round(126 + (87-126)*ratio), b = Math.round(202 + (46-202)*ratio);
    return `rgb(${r},${g},${b})`;
  }
  let out = '<div></div>';
  diaOrder.forEach(d => out += `<div class="heat-label" style="justify-content:center">${d}</div>`);
  out += '<div class="heat-label">Manhã</div>';
  diaOrder.forEach(d => { const v = heat[d]['Manhã']; out += `<div class="heat-cell" style="background:${color(v)}">${v}<span>ausências</span></div>`; });
  out += '<div class="heat-label">Tarde</div>';
  diaOrder.forEach(d => { const v = heat[d]['Tarde']; out += `<div class="heat-cell" style="background:${color(v)}">${v}<span>ausências</span></div>`; });
  el.innerHTML = out;
})();

/* Baixar o ranking como planilha (CSV com ; e acentos certos para o Excel). No modo apresentação os nomes saem anônimos. */
function baixarRankingCSV() {
  const tb = document.getElementById('tableRanking'); if (!tb) return;
  const anon = document.body.classList.contains('modo-apresentacao');
  const cab = Array.from(tb.querySelectorAll('thead th')).map(th => th.textContent.trim()).filter(t => t !== 'Extrato');
  const lin = Array.from(tb.querySelectorAll('tbody tr')).map((tr, i) => {
    const tds = Array.from(tr.children).slice(0, cab.length);
    return tds.map((td, j) => (anon && cab[j] === 'Agente') ? 'Agente ' + (i + 1) : td.textContent.replace(/\s+/g, ' ').trim());
  });
  const q = v => '"' + String(v).replace(/"/g, '""') + '"';
  const txt = '\ufeff' + [cab].concat(lin).map(l => l.map(q).join(';')).join('\r\n');
  window.__ultimoCSV = txt;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([txt], { type: 'text/csv;charset=utf-8' }));
  a.download = 'ranking-sentinela.csv'; document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
