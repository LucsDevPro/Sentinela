
const $ = id => document.getElementById(id);
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f1 = n => n == null ? '—' : Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const norm = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
$('apres').onchange = e => document.body.classList.toggle('modo-apresentacao', e.target.checked);
$('semFoto').onchange = e => document.body.classList.toggle('sem-foto', e.target.checked);
try { if (window.opener && window.opener.document.body.classList.contains('modo-apresentacao')) { $('apres').checked = true; document.body.classList.add('modo-apresentacao'); } } catch (e) {}
try { if (window.opener && window.opener.document.body.classList.contains('sem-foto')) { $('semFoto').checked = true; document.body.classList.add('sem-foto'); } } catch (e) {}

let idAgente = null; // id do agente aberto (usado para achar a foto da cartinha)
function achar(D, q) {
  const id = q.get('id'), nome = q.get('nome');
  idAgente = null;
  if (id && D.agentes[id]) { idAgente = id; return D.agentes[id]; }
  if (nome) { const e = Object.entries(D.agentes).find(([, a]) => norm(a.nome) === norm(nome)); if (e) { idAgente = e[0]; return e[1]; } }
  return null;
}
if (window.aplicarTemaGraficos) aplicarTemaGraficos(); Chart.defaults.font.family = "'IBM Plex Sans', system-ui, sans-serif";
const SV = (n, c) => `<svg class="ico${c ? ' ' + c : ''}" aria-hidden="true"><use href="#i-${n}"/></svg>`;
function carta(a, ms) {
  const c = Carta.html(a, ms, idAgente); if (!c) return '';
  const m = Carta.medidas(ms);
  return `<div class="carta-wrap">${c}
    <div class="carta-info"><h2>Como ler o cartão</h2><p class="mut">Passe o mouse (ou clique) na cartinha para ver como chegou na nota.</p><table>${m.st.map(x => `<tr><td>${x[0]}</td><td>${Carta.NOMES[x[0]]}</td></tr>`).join('')}</table>
      <p class="mut">A nota grande é a nota do mês. As seis medidas vão de 0 a 99 e usam só dados do ranking:
      <b>ASS</b> dias trabalhados ÷ esperados · <b>TUR</b> turnos com lançamento · <b>CON</b> quanto menos a nota oscila entre os meses, maior ·
      <b>EVO</b> 50 = igual ao mês anterior, sobe 5 por ponto ganho · <b>POS</b> lugar no ranking · <b>MED</b> média dos meses.
      Nível: ouro ≥ 90, prata ≥ 75, bronze abaixo disso; <b>destaque</b> = top 3 com nota ≥ 90.</p>
      <div class="acoes"><button type="button" class="bt-img" id="bBaixar">${SV('download')} Baixar imagem</button><button type="button" class="bt-img zap" id="bZap">${SV('share')} Enviar pelo WhatsApp</button></div>
      <p class="mut" id="msgImg" role="status" aria-live="polite"></p>
      <p><a href="album.html">Ver o álbum com todas as cartinhas →</a></p></div></div>`;
}
function qd(trab, esp) {
  const t = Math.max(0, Math.round(trab || 0)), e = Math.max(Math.round(esp || 0), t);
  return `<span class="qd" role="img" aria-label="${t} de ${e} dias trabalhados">${'<i class="on"></i>'.repeat(t)}${'<i></i>'.repeat(e - t)}</span>`;
}
const chipsPar = ps => (ps || []).map(p => `<span class="chip par" title="Parada da equipe: não conta como falta">${SV('cone')} ${esc(p.motivo)} · ${p.dias} ${p.dias === 1 ? 'dia' : 'dias'}</span>`).join('');
const dd = v => f1(v).replace(',0', '');
function linhaTempo(ms, sem) {
  if (!ms.length) return '';
  const itens = ms.slice().reverse().map(m => {
    const ss = sem.filter(s => s.mes === m.mes).sort((x, y) => x.n - y.n);
    const sub = ss.length ? `<ul>${ss.map(s => `<li><div class="lin"><span class="quando">Semana ${s.n}</span><span class="mut">${esc(s.periodo)}${s.parcial ? ' · parcial' : ''}</span>${qd(s.trab, s.esp)}<span>${dd(s.trab)} de ${dd(s.esp)} dias · nota ${f1(s.pontos)}</span>${chipsPar(s.paradas)}</div></li>`).join('')}</ul>` : '';
    return `<li><div class="lin"><span class="quando">${esc(m.mes)}</span>${qd(m.trab, m.esp)}<span>${dd(m.trab)} de ${dd(m.esp)} dias · nota <b>${f1(m.pontos)}</b> · ${m.pos}º de ${m.total}</span>${m.fechado ? '<span class="chip">mês fechado</span>' : ''}${chipsPar(m.paradas)}</div>${sub}</li>`;
  }).join('');
  return `<div class="card"><h2>${SV('timeline')} Linha do tempo</h2>
    <div class="tl-leg"><span><span class="qd"><i class="on"></i></span> dia trabalhado</span><span><span class="qd"><i></i></span> dia esperado sem lançamento</span><span>${SV('cone')} parada da equipe (chuva, reunião, mutirão…) não conta como falta</span></div>
    <ol class="tl">${itens}</ol></div>`;
}
function desenhar() {
  const D = window.AGENTES_DADOS, alvo = $('conteudo');
  if (!D || !D.agentes || !Object.keys(D.agentes).length) { alvo.innerHTML = '<div class="card aviso">Ainda não há dados de agentes. Volte depois da próxima atualização do site.</div>'; return; }
  const q = new URLSearchParams(location.search), a = achar(D, q);
  if (!a) {
    const busca = (q.get('id') || q.get('nome')) ? '<div class="card aviso">Não encontrei esse agente. Procure pelo nome:</div>' : '<p class="mut">Escolha o agente:</p>';
    alvo.innerHTML = `<h1><svg class="ico" aria-hidden="true"><use href="#i-trend"/></svg> Evolução do agente</h1>${busca}<input id="b" placeholder="Digite parte do nome" autocomplete="off"><div id="lista"></div>`;
    const lista = () => { const t = norm($('b').value);
      $('lista').innerHTML = Object.entries(D.agentes).filter(([, x]) => !t || norm(x.nome).includes(t)).sort((x, y) => x[1].nome.localeCompare(y[1].nome, 'pt-BR')).slice(0, 60)
        .map(([k, x]) => `<a href="?${/^\d+$/.test(k) ? 'id=' + k : 'nome=' + encodeURIComponent(x.nome)}"><span class="nome">${esc(x.nome)}</span> <span class="mut">· ${esc(x.equipe)}</span></a>`).join(''); };
    $('b').oninput = lista; lista(); return;
  }
  const ms = a.meses, ult = ms[ms.length - 1], sem = a.semanas;
  document.title = 'Evolução — ' + a.nome;
  const media = ms.length ? ms.reduce((t, m) => t + (m.pontos || 0), 0) / ms.length : null;
  const trab = ult ? `${f1(ult.trab).replace(',0', '')} de ${f1(ult.esp).replace(',0', '')}` : '—';
  let html = `<h1><svg class="ico" aria-hidden="true"><use href="#i-trend"/></svg> <span class="nome">${esc(a.nome)}</span></h1><div class="mut">${esc(a.equipe)} · atualizado em ${esc(D.gerado_em)}</div>`;
  html += carta(a, ms);
  if (ult) html += `<div class="card"><div class="kpis">
      <div class="kpi"><span>Nota em ${esc(ult.mes)}</span><strong>${f1(ult.pontos)}</strong></div>
      <div class="kpi"><span>Posição</span><strong>${ult.pos}º de ${ult.total}</strong></div>
      <div class="kpi"><span>Média dos meses</span><strong>${f1(media)}</strong></div>
      <div class="kpi"><span>Dias trabalhados</span><strong>${trab}</strong></div></div></div>`;
  if (ms.length) html += `<div class="card"><h2>Nota por mês</h2><div class="grafico"><canvas id="gMes" role="img" aria-label="Nota mensal"></canvas></div></div>
    <div class="card"><h2>Dias trabalhados × esperados</h2><div class="grafico"><canvas id="gDias" role="img" aria-label="Dias trabalhados e esperados por mês"></canvas></div></div>`;
  else html += '<div class="card aviso">Este agente ainda não tem mês registrado.</div>';
  if (sem.length >= 1) html += `<div class="card"><h2>Nota por semana (mês aberto)</h2><div class="grafico"><canvas id="gSem" role="img" aria-label="Nota semanal"></canvas></div>
      <p class="mut">Semana parcial = ainda em andamento; a nota dela pode mudar até sexta.</p></div>`;
  html += linhaTempo(ms, sem);
  if (ult) {
    const li = (arr, cls) => arr.length ? arr.map(x => `<tr><td>${esc(x.c)}</td><td class="n ${cls}">${x.p > 0 ? '+' : ''}${f1(x.p)}</td></tr>`).join('') : '<tr><td class="mut" colspan="2">Nenhum.</td></tr>';
    html += `<div class="card"><h2>O que mais tirou pontos em ${esc(ult.mes)}</h2><table>${li(ult.perdas, 'neg')}</table></div>
      <div class="card"><h2>O que mais deu pontos</h2><table>${li(ult.ganhos, 'pos')}</table></div>`;
  }
  html += `<p class="mut">Só dados públicos do ranking, sem informações de saúde. A conta completa está no Extrato do dashboard e em <a href="transparencia.html">Como o ranking é calculado</a>.</p>`;
  alvo.innerHTML = html;
  const ligar = (id, modo) => { const b = $(id); if (!b) return; b.onclick = () => {
    const msg = $('msgImg'); b.disabled = true; msg.textContent = 'Preparando a imagem…';
    Carta.enviar(a, ms, modo, { id: idAgente, ocultarNomes: document.body.classList.contains('modo-apresentacao'), ocultarFoto: document.body.classList.contains('sem-foto') })
      .then(t => { msg.textContent = t; }, () => { msg.textContent = 'Não consegui gerar a imagem aqui. Abra a página pelo endereço do site (não pelo arquivo no computador) e tente de novo.'; })
      .then(() => { b.disabled = false; }); }; };
  ligar('bBaixar', 'baixar'); ligar('bZap', 'whatsapp');
  const cor = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || '#888';
  if (ms.length && window.Chart) {
    new Chart($('gMes'), { type: 'line', data: { labels: ms.map(m => m.mes.replace('/20', '/')), datasets: [{ label: 'Nota', data: ms.map(m => m.pontos), borderColor: cor('--serie'), backgroundColor: cor('--serie'), tension: .25 }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } } });
    new Chart($('gDias'), { type: 'bar', data: { labels: ms.map(m => m.mes.replace('/20', '/')), datasets: [
      { label: 'Trabalhados', data: ms.map(m => m.trab), backgroundColor: cor('--serie') }, { label: 'Esperados', data: ms.map(m => m.esp), backgroundColor: cor('--mut') }] },
      options: { responsive: true, maintainAspectRatio: false } });
  }
  if (sem.length && window.Chart) {
    new Chart($('gSem'), { type: 'bar', data: { labels: sem.map(s => `S${s.n}${s.parcial ? ' (parcial)' : ''}`), datasets: [{ label: 'Nota da semana', data: sem.map(s => s.pontos),
      backgroundColor: sem.map(s => s.parcial ? cor('--mut') : cor('--info')) }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100 } }, plugins: { legend: { display: false } } } });
  }
}
desenhar();
document.addEventListener('sentinela:tema', () => location.reload());
