// Álbum de cartinhas (album.html): abas, filtros, pódio e grade. A aparência das cartas está em carta.css / carta_fx.js.

const $ = id => document.getElementById(id);
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm = t => String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
const MESES = ['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
const ordMes = l => { const p = norm(l).split('/'); return (parseInt(p[1], 10) || 0) * 20 + MESES.indexOf(p[0]); };
$('apres').onchange = e => document.body.classList.toggle('modo-apresentacao', e.target.checked);
$('semFoto').onchange = e => document.body.classList.toggle('sem-foto', e.target.checked);
try { if (window.opener && window.opener.document.body.classList.contains('modo-apresentacao')) { $('apres').checked = true; document.body.classList.add('modo-apresentacao'); } } catch (e) {}
try { if (window.opener && window.opener.document.body.classList.contains('sem-foto')) { $('semFoto').checked = true; document.body.classList.add('sem-foto'); } } catch (e) {}

// ---- Abas: Cartinhas | Como é calculado (o texto vem de assets/como_calcula.js, gerado por scripts/gerar_transparencia.py)
const PAINEIS = { cartas: ['abaCartas', 'painelCartas'], calc: ['abaCalc', 'painelCalc'] };
let calcPronto = false;
function carregarCalc() {
  if (calcPronto) return;
  const pintar = () => { $('painelCalc').innerHTML = '<div class="calc">' + window.COMO_CALCULA.html + '</div>'; calcPronto = true; };
  if (window.COMO_CALCULA) return pintar();
  $('painelCalc').innerHTML = '<p class="mut">Carregando…</p>';
  const s = document.createElement('script'); s.src = 'assets/como_calcula.js'; s.onload = pintar;
  s.onerror = () => { $('painelCalc').innerHTML = '<div class="card aviso">Não consegui carregar o texto. Recarregue a página.</div>'; };
  document.head.appendChild(s);
}
function mostrar(qual, gravarHash) {
  Object.entries(PAINEIS).forEach(([k, [aba, painel]]) => { $(aba).setAttribute('aria-selected', String(k === qual)); $(painel).hidden = k !== qual; });
  if (qual === 'calc') carregarCalc();
  if (gravarHash) history.replaceState(null, '', qual === 'calc' ? '#como-calcula' : location.pathname + location.search);
  document.title = (qual === 'calc' ? 'Como é calculado' : 'Álbum de cartinhas') + ' — Sentinela';
}
$('abaCartas').onclick = () => mostrar('cartas', true);
$('abaCalc').onclick = () => mostrar('calc', true);
window.addEventListener('hashchange', () => mostrar(location.hash === '#como-calcula' ? 'calc' : 'cartas', false));
mostrar(location.hash === '#como-calcula' ? 'calc' : 'cartas', false);

const D = window.AGENTES_DADOS, ag = D && D.agentes ? Object.entries(D.agentes).map(([k, a]) => ({ k, a })) : [];
const meses = [...new Set(ag.flatMap(x => (x.a.meses || []).map(m => m.mes)))].sort((p, q) => ordMes(p) - ordMes(q));
if (!meses.length) { $('album').outerHTML = '<div class="card aviso">Ainda não há cartinhas. Volte depois da próxima atualização do site.</div>'; $('resumo').textContent = ''; }
else {
  $('fMes').innerHTML = meses.slice().reverse().map(m => `<option>${esc(m)}</option>`).join('');
  const q0 = new URLSearchParams(location.search).get('mes'); if (q0 && meses.includes(q0)) $('fMes').value = q0;
  const eqs = [...new Set(ag.map(x => x.a.equipe).filter(Boolean))].sort((p, q) => p.localeCompare(q, 'pt-BR', { numeric: true }));
  $('fEq').insertAdjacentHTML('beforeend', eqs.map(e => `<option>${esc(e)}</option>`).join(''));
  const desenhar = () => {
    const mes = $('fMes').value, eq = $('fEq').value, niv = $('fNivel').value, bu = norm($('fBusca').value);
    const lista = [];
    ag.forEach(x => { const ms = (x.a.meses || []).slice().sort((p, q) => ordMes(p.mes) - ordMes(q.mes)); const i = ms.findIndex(m => m.mes === mes);
      if (i < 0 || ms[i].pontos == null) return; lista.push({ x, ms: ms.slice(0, i + 1), u: ms[i] }); });
    // desempate: média das notas dos meses ANTERIORES ao mês mostrado (a mesma da tabela "Média Mensal por Agente"); sem histórico fica atrás
    const hist = l => { const v = l.ms.slice(0, -1).map(m => m.pontos).filter(n => n != null); return v.length ? Math.round(v.reduce((t, n) => t + n, 0) / v.length * 10) / 10 : -1; };
    lista.forEach(l => { l.h = hist(l); });
    lista.sort((p, q) => Carta.bruta(q.u) - Carta.bruta(p.u) || q.h - p.h || p.u.pos - q.u.pos || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'));
    lista.forEach((l, i) => { l.lugar = i + 1; });
    const vis = lista.filter(l => (!eq || l.x.a.equipe === eq) && (!bu || norm(l.x.a.nome).includes(bu)) && (!niv || Carta.medidas(l.ms, l.x.k).tier[1] === niv));
    const slot = (l, cls) => `<a class="slot ${cls || ''}" href="agente.html?${/^\d+$/.test(l.x.k) ? 'id=' + l.x.k : 'nome=' + encodeURIComponent(l.x.a.nome)}" title="Ver evolução de ${esc(l.x.a.nome)}"><span class="n${l.lugar <= 3 ? ' m' + l.lugar : ''}" aria-label="${l.lugar}º lugar">${l.lugar}º</span>${Carta.html(l.x.a, l.ms, l.x.k)}</a>`;
    // Pódio: só sem filtros (com filtro, o top 3 do mês pode nem estar na lista). No HTML a ordem é 1º, 2º, 3º; o CSS põe o 1º no meio.
    const pod = !eq && !bu && !niv && vis.length >= 3 ? vis.slice(0, 3) : [];
    $('podio').hidden = !pod.length;
    $('podio').innerHTML = pod.map((l, i) => slot(l, 'p' + (i + 1))).join('');
    [['p1', '650ms'], ['p2', '200ms'], ['p3', '0ms']].forEach(([c, t]) => $('podio').querySelectorAll('.slot.' + c + ' .carta').forEach(el => el.style.setProperty('--atraso', t)));
    $('album').innerHTML = vis.slice(pod.length).map(l => slot(l)).join('');
    $('resumo').textContent = vis.length ? `${vis.length} cartinha(s) de ${lista.length} em ${mes}.` : 'Nenhuma cartinha com esses filtros.';
  };
  ['fMes', 'fEq', 'fNivel'].forEach(i => $(i).onchange = desenhar); $('fBusca').oninput = desenhar;
  desenhar();
}
document.addEventListener('sentinela:tema', () => {});
