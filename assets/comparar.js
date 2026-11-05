
const $ = id => document.getElementById(id);
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f1 = n => Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const sg = n => (n > 0.04 ? '+' : n < -0.04 ? '−' : '') + f1(Math.abs(n));
const MESES = ['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
const ordMes = l => { const p = String(l).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().split('/'); return (parseInt(p[1], 10) || 0) * 20 + MESES.indexOf(p[0]); };
const LIMIAR = 0.5; // até meio ponto de diferença = estável
const SV = n => `<svg class="ico" aria-hidden="true"><use href="#i-${n}"/></svg>`;
$('apres').onchange = e => document.body.classList.toggle('modo-apresentacao', e.target.checked);
try { if (window.opener && window.opener.document.body.classList.contains('modo-apresentacao')) { $('apres').checked = true; document.body.classList.add('modo-apresentacao'); } } catch (e) {}
let filtro = 'todos', grafico = null;
function dado() {
  const D = window.AGENTES_DADOS;
  return D && D.agentes ? Object.entries(D.agentes).map(([k, a]) => ({ k, nome: a.nome, equipe: a.equipe || '—', meses: a.meses || [] })) : [];
}
function nota(a, mes) { const m = a.meses.find(x => x.mes === mes); return m && m.pontos != null ? m : null; }
function seta(d) { return d > LIMIAR ? ['up', 'arrow-up', 'subiu'] : d < -LIMIAR ? ['down', 'arrow-down', 'caiu'] : ['eq0', 'minus', 'estável']; }
function montar() {
  const ag = dado(), alvo = $('conteudo');
  const cont = {}; ag.forEach(a => a.meses.forEach(m => { cont[m.mes] = 1; }));
  const meses = Object.keys(cont).sort((x, y) => ordMes(x) - ordMes(y));
  if (meses.length < 2) { alvo.innerHTML = '<div class="card aviso">Preciso de pelo menos dois meses com notas para comparar. Volte depois da próxima atualização.</div>'; return; }
  const q = new URLSearchParams(location.search);
  let de = meses.includes(q.get('de')) ? q.get('de') : meses[meses.length - 2], para = meses.includes(q.get('para')) ? q.get('para') : meses[meses.length - 1];
  const opt = sel => meses.map(m => `<option${m === sel ? ' selected' : ''}>${esc(m)}</option>`).join('');
  alvo.innerHTML = `<div class="card"><div class="ctl"><label>De<select id="sDe">${opt(de)}</select></label><label>Para<select id="sPara">${opt(para)}</select></label></div></div><div id="res"></div>`;
  $('sDe').onchange = $('sPara').onchange = () => { de = $('sDe').value; para = $('sPara').value; resultado(ag, de, para); };
  resultado(ag, de, para);
}
function resultado(ag, de, para) {
  const linhas = [];
  let semPar = 0;
  ag.forEach(a => { const x = nota(a, de), y = nota(a, para); if (x && y) linhas.push({ a, x, y, d: y.pontos - x.pontos, dpos: x.pos - y.pos }); else if (x || y) semPar++; });
  const sobe = linhas.filter(l => l.d > LIMIAR).length, cai = linhas.filter(l => l.d < -LIMIAR).length, est = linhas.length - sobe - cai;
  const mA = linhas.length ? linhas.reduce((t, l) => t + l.x.pontos, 0) / linhas.length : 0, mB = linhas.length ? linhas.reduce((t, l) => t + l.y.pontos, 0) / linhas.length : 0;
  const equipes = [...new Set(linhas.map(l => l.a.equipe))].sort((p, q) => p.localeCompare(q, 'pt-BR', { numeric: true }));
  const resEq = equipes.map(e => { const ls = linhas.filter(l => l.a.equipe === e); const m1 = ls.reduce((t, l) => t + l.x.pontos, 0) / ls.length, m2 = ls.reduce((t, l) => t + l.y.pontos, 0) / ls.length; return { e, ls, m1, m2, d: m2 - m1 }; });
  const abertos = [...new Set([de, para])].filter(m => linhas.some(l => { const x = l.x.mes === m ? l.x : l.y; return !x.fechado; }));
  const mostra = l => filtro === 'todos' || (filtro === 'sobe' && l.d > LIMIAR) || (filtro === 'cai' && l.d < -LIMIAR);
  const bloco = r => {
    const ls = r.ls.filter(mostra).sort((p, q) => q.d - p.d);
    const [c, ic] = seta(r.d);
    const tr = ls.map(l => { const [c2, i2, tx] = seta(l.d); const dp = l.dpos === 0 ? 'mesma posição' : l.dpos > 0 ? `${SV('arrow-up')} ${l.dpos} ${l.dpos === 1 ? 'posição' : 'posições'}` : `${SV('arrow-down')} ${-l.dpos} ${l.dpos === -1 ? 'posição' : 'posições'}`;
      return `<tr><td><a class="nome" href="agente.html?${/^\d+$/.test(l.a.k) ? 'id=' + l.a.k : 'nome=' + encodeURIComponent(l.a.nome)}">${esc(l.a.nome)}</a></td><td class="n">${f1(l.x.pontos)} → ${f1(l.y.pontos)}</td><td class="n"><span class="dl ${c2}">${SV(i2)} ${sg(l.d)}<span class="sr"> (${tx})</span></span></td><td class="n mut">${dp}</td></tr>`; }).join('');
    return `<div class="card eq"><h2><span>${esc(r.e)}</span><span class="dl ${c}">${SV(ic)} média ${f1(r.m1)} → ${f1(r.m2)} (${sg(r.d)})</span></h2>
      <table class="cmp">${tr || '<tr><td class="mut">Ninguém nesta lista.</td></tr>'}</table></div>`;
  };
  $('res').innerHTML = `<div class="card"><div class="kpis">
      <div class="kpi"><span>Média geral</span><strong>${f1(mA)} → ${f1(mB)}</strong></div>
      <div class="kpi"><span>Subiram</span><strong class="pos" id="nSobe">${sobe}</strong></div>
      <div class="kpi"><span>Caíram</span><strong class="neg" id="nCai">${cai}</strong></div>
      <div class="kpi"><span>Estáveis (até ${f1(LIMIAR)} pt)</span><strong>${est}</strong></div></div>
      ${abertos.length ? `<p class="aviso" id="avAberto">${esc(abertos.join(' e '))} ainda ${abertos.length > 1 ? 'estão abertos' : 'está aberto'}: a nota pode mudar até o fechamento do mês.</p>` : ''}
      ${semPar ? `<p class="mut">${semPar} agente(s) aparecem em só um dos dois meses e ficaram de fora da comparação.</p>` : ''}</div>
    <div class="card"><h2>Variação da média por equipe</h2><div class="grafico"><canvas id="gEq" role="img" aria-label="Variação da nota média por equipe"></canvas></div></div>
    <div class="abas" role="group" aria-label="Mostrar">${[['todos', 'Todos'], ['sobe', 'Quem subiu'], ['cai', 'Quem caiu']].map(([v, t]) => `<button type="button" data-f="${v}" aria-pressed="${filtro === v}">${t}</button>`).join('')}</div>
    ${resEq.map(bloco).join('') || '<div class="card aviso">Nenhum agente aparece nos dois meses.</div>'}
    <p class="mut">Nota de ${esc(de)} comparada à de ${esc(para)}. “Posições” mostra quantos lugares o agente ganhou (↑) ou perdeu (↓) no ranking. Meses ainda abertos podem mudar até o fechamento.</p>`;
  document.querySelectorAll('.abas button').forEach(b => b.onclick = () => { filtro = b.dataset.f; resultado(ag, de, para); });
  if (grafico) grafico.destroy();
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  if (window.aplicarTemaGraficos) aplicarTemaGraficos();
  grafico = new Chart($('gEq'), { type: 'bar', data: { labels: resEq.map(r => r.e), datasets: [{ data: resEq.map(r => Math.round(r.d * 10) / 10), backgroundColor: resEq.map(r => r.d >= 0 ? css('--ok') : css('--bad')), borderRadius: 5 }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grace: '10%' } } },
    plugins: [{ id: 'v', afterDatasetsDraw(ch) { const c = ch.ctx; c.save(); c.font = '600 12px "IBM Plex Sans",sans-serif'; c.fillStyle = css('--tx'); c.textAlign = 'center';
      ch.getDatasetMeta(0).data.forEach((b, i) => { const v = ch.data.datasets[0].data[i]; c.textBaseline = v >= 0 ? 'bottom' : 'top'; c.fillText(sg(v), b.x, v >= 0 ? b.y - 3 : b.y + 3); }); c.restore(); } }] });
}
montar();
document.addEventListener('sentinela:tema', () => location.reload());
