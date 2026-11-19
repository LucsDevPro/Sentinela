
const $ = id => document.getElementById(id);
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const f1 = n => n == null ? '—' : Number(n).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const norm = t => String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
const MESES_ORD = ['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
const ordMes = l => { const p = norm(l).split('/'); return (parseInt(p[1], 10) || 0) * 20 + MESES_ORD.indexOf(p[0]); };
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

// ---- «Por que esta nota?»: a conta inteira do mês, critério a critério, com os dias e turnos de cada desconto (para quando o agente questionar) ----
const fnum = n => Number(n).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
const sg = n => (n > 0 ? '+' : n < 0 ? '−' : '') + f1(Math.abs(n));
const AJUDA = [
  [/^Turno sem lançamento/, 'Turno de dia útil sem nenhuma visita registrada e sem justificativa no cronograma (chuva, folga, atestado, reunião, férias…). Os dias e turnos estão listados abaixo.'],
  [/^Dia inteiro sem lançamento/, 'Manhã e tarde do mesmo dia sem lançamento: além dos dois turnos, perde um adicional por dia inteiro.'],
  [/^Início manhã/, 'Primeira visita da manhã registrada depois das 08h30 (−0,3 por dia).'],
  [/^Fim manhã/, 'Última visita da manhã registrada antes das 10h00 (parou cedo demais).'],
  [/^Início tarde/, 'Primeira visita da tarde registrada depois das 14h30.'],
  [/^Fim tarde/, 'Última visita da tarde registrada antes das 16h00 (parou cedo demais).'],
  [/^Visita rápida/, 'Visita com menos de 3 minutos de duração.'],
  [/^Visita duplicada/, 'Mesmo imóvel lançado mais de uma vez.'],
  [/sequência suspeita/, 'Visitas lançadas com menos de 50 segundos de diferença uma da outra (lista abaixo).'],
  [/^Visita fora do expediente/, 'Visita lançada fora do expediente (manhã 07–11h, tarde 13–17h) ou em fim de semana.'],
  [/^Dia sem bater a meta/, 'Dia trabalhado com menos visitas que a meta diária da equipe.'],
  [/^Dia com meta/, 'Dia trabalhado com a meta diária batida.'],
  [/^Bônus não concedido/, 'O bônus só vale com presença mínima no período.'],
  [/^Bônus/, 'Bônus único do período.'],
  [/^Presença abaixo do mínimo/, 'Ajuste final: a nota inteira é multiplicada por um fator quando os dias trabalhados ficam abaixo do mínimo exigido.']
];
const ajuda = c => (AJUDA.find(([r]) => r.test(c)) || [0, ''])[1];
const TURNO = { M: 'manhã', T: 'tarde' };
function porque(a, ult) {
  const det = (ult.detalhe || []).map(x => ({ c: x[0], q: x[1], w: x[2], p: x[3] }));
  if (!det.length) return '';
  const ehAjuste = x => /^Presença abaixo do mínimo/.test(x.c);
  const corpo = det.filter(x => !ehAjuste(x)), ajuste = det.filter(ehAjuste);
  const desc = corpo.filter(x => x.p < 0).sort((x, y) => x.p - y.p), bon = corpo.filter(x => x.p > 0), neutros = corpo.filter(x => x.p === 0);
  const somaDesc = desc.reduce((t, x) => t + x.p, 0), somaBon = bon.reduce((t, x) => t + x.p, 0), somaAj = ajuste.reduce((t, x) => t + x.p, 0);
  let saldo = 100;
  const linha = (x, aj) => { saldo += x.p;
    return `<tr><td><b>${esc(x.c)}</b><small>${esc(ajuda(x.c))}</small></td><td class="n mut">${aj ? '—' : fnum(x.q) + ' × ' + fnum(x.w)}</td><td class="n ${x.p < 0 ? 'neg' : x.p > 0 ? 'pos' : 'mut'}">${x.p === 0 ? '0,0' : sg(x.p)}</td><td class="n mut">${f1(Math.max(0, saldo))}</td></tr>`; };
  const corpoTab = desc.map(x => linha(x)).join('') + bon.map(x => linha(x)).join('') + neutros.map(x => linha(x)).join('') + ajuste.map(x => linha(x, true)).join('');
  const total = 100 + somaDesc + somaBon + somaAj, nota = Math.round(ult.pontos * 10) / 10;
  const obs = total < -0.05 ? ' (a nota mínima é 0)' : Math.abs(total - nota) > 0.15 ? ' (com ajustes do período)' : '';
  const pct = ult.esp ? Math.round(ult.trab / ult.esp * 100) : null;
  const ev = ult.ev || {};
  // turnos sem lançamento (descontam), agrupados por dia
  let blocoTurnos = '';
  if (ev.sem && ev.sem.length) {
    const dias = {}; ev.sem.forEach(([d, w, t]) => { (dias[d] = dias[d] || { w, t: [] }).t.push(t); });
    const lista = Object.entries(dias).sort((x, y) => x[0].split('/').reverse().join('').localeCompare(y[0].split('/').reverse().join('')))
      .map(([d, o]) => `<li><b>${esc(o.w)} ${esc(d)}</b> — ${o.t.length > 1 ? 'manhã e tarde <em>(dia inteiro)</em>' : TURNO[o.t[0]]}</li>`).join('');
    blocoTurnos = `<h3>Turnos descontados (${ev.sem.length} em ${Object.keys(dias).length} dia${Object.keys(dias).length > 1 ? 's' : ''})</h3><ul class="dias">${lista}</ul>
      <p class="mut">Sem nenhuma visita registrada no turno e sem justificativa no cronograma. Se havia motivo (folga, atestado, reunião, chuva…), a coordenação registra no cronograma e o ranking é refeito.</p>`;
  }
  let blocoJust = '';
  const just = Object.entries(ev.just || {});
  if (just.length || (ult.paradas && ult.paradas.length)) {
    const j1 = just.map(([m, it]) => `<li><b>${esc(m)}</b> — ${it.map(([d, t]) => esc(d) + ' (' + TURNO[t] + ')').join(', ')}</li>`).join('');
    const j2 = (ult.paradas || []).map(p => `<li><b>${esc(p.motivo)}</b> — ${fnum(p.dias)} dia${p.dias === 1 ? '' : 's'}</li>`).join('');
    blocoJust = `<h3>Não descontaram (justificados)</h3><ul class="dias">${j1}${j2}</ul>`;
  }
  let blocoSusp = '';
  const susp = Object.entries(ev.susp || {});
  if (susp.length) {
    blocoSusp = `<h3>Visitas em sequência suspeita</h3>` + susp.map(([c, it]) => `<p class="mut">Sequência ${esc(c)}: ${it.length} visitas começando com menos de 50 segundos de diferença</p><ul class="dias">${it.map(([h, id, ar, q]) => `<li><b>${esc(h)}</b> · visita ${esc(id)} · ${esc(ar)}${q ? ' · ' + esc(q) : ''}</li>`).join('')}</ul>`).join('');
  }
  const motivoBaixa = ajuste.length ? `<p class="aviso-presenca"><b>Principal efeito:</b> ${esc(ajuste[0].c.replace(/\s*—.*$/, ''))}. Por isso a nota inteira foi multiplicada (${sg(somaAj)}).</p>` : '';
  return `<div class="card" id="detalhamento"><h2>Por que esta nota? — <span class="nome">${esc(a.nome)}</span> · ${esc(ult.mes)}</h2>
    <div class="kpis kpis-porque">
      <div class="kpi"><span>Nota do mês</span><strong>${f1(ult.pontos)}</strong></div>
      <div class="kpi"><span>Descontos</span><strong class="neg">${somaDesc ? sg(somaDesc) : '0,0'}</strong></div>
      <div class="kpi"><span>Bônus e metas</span><strong class="pos">${somaBon ? sg(somaBon) : '0,0'}</strong></div>
      <div class="kpi"><span>Presença</span><strong>${f1(ult.trab).replace(',0', '')} de ${f1(ult.esp).replace(',0', '')}${pct == null ? '' : ' (' + pct + '%)'}</strong></div></div>
    ${motivoBaixa}
    <div class="tabela-rolagem"><table class="porque"><thead><tr><th>Critério</th><th class="n">Qtd × peso</th><th class="n">Pontos</th><th class="n">Saldo</th></tr></thead><tbody>
      <tr class="base"><td><b>Pontos iniciais</b><small>Todo agente começa o mês com 100.</small></td><td></td><td></td><td class="n mut">100,0</td></tr>${corpoTab}</tbody>
      <tfoot><tr><td colspan="3">Total (100 + critérios)</td><td class="n">${f1(total)}</td></tr><tr class="final"><td colspan="3">Nota final${esc(obs)}</td><td class="n">${f1(ult.pontos)}</td></tr></tfoot></table></div>
    ${blocoTurnos}${blocoJust}${blocoSusp}
    <p class="mut">Dúvida ou discordância? Procure a coordenação ou abra um pedido em <a href="contestacao.html">Contestação</a>, levando esta página. A conta completa está em <a href="album.html#como-calcula">Como o ranking é calculado</a>.</p>
    <p class="no-print"><button type="button" class="bt-det" id="bImprimirDet">Imprimir este detalhamento</button></p></div>`;
}

// «Por que esta nota?» no Melhor do ano: a nota é a média das notas mensais. Mostra cada mês (com link para a conta completa dele).
function porqueAno(a, l) {
  const qs = idAgente && /^\d+$/.test(String(idAgente)) ? 'id=' + idAgente : 'nome=' + encodeURIComponent(a.nome);
  const linhas = l.meses.map(m => `<tr><td><b>${esc(m.mes)}</b></td><td class="n">${f1(m.pontos)}</td><td class="n mut">${m.pos}º de ${m.total}</td><td class="n"><a href="agente.html?${qs}&mes=${encodeURIComponent(m.mes)}">ver a conta do mês</a></td></tr>`).join('');
  const soma = l.meses.reduce((t, m) => t + m.pontos, 0);
  return `<div class="card" id="detalhamento"><h2>Por que esta nota? — <span class="nome">${esc(a.nome)}</span> · Melhor do ano</h2>
    <p>A nota do <b>Melhor do ano</b> é a <b>média das notas de todos os meses</b> do agente (${l.meses.length} ${l.meses.length === 1 ? 'mês' : 'meses'}): ${l.meses.map(m => f1(m.pontos)).join(' + ')} = ${f1(soma)} ÷ ${l.meses.length} = <b>${f1(l.u.pontos)}</b>. Só entra quem tem pelo menos 2 meses. A posição <b>${l.u.pos}º de ${l.u.total}</b> é neste ranking anual; o ranking de cada mês é outro e pode ser diferente.</p>
    <div class="tabela-rolagem"><table class="porque"><thead><tr><th>Mês</th><th class="n">Nota</th><th class="n">Posição no mês</th><th class="n"></th></tr></thead><tbody>${linhas}</tbody>
      <tfoot><tr class="final"><td>Média (nota do ano)</td><td class="n">${f1(l.u.pontos)}</td><td class="n">${l.u.pos}º de ${l.u.total}</td><td></td></tr></tfoot></table></div>
    <p class="mut">Dúvida ou discordância? Procure a coordenação ou abra um pedido em <a href="contestacao.html">Contestação</a>. A conta de cada critério está na página de cada mês (link acima).</p>
    <p class="no-print"><button type="button" class="bt-det" id="bImprimirDet">Imprimir este detalhamento</button></p></div>`;
}
function carta(a, ms) {
  const c = Carta.html(a, ms, idAgente); if (!c) return '';
  const m = Carta.medidas(ms);
  return `<div class="carta-wrap">${c}
    <div class="carta-info"><h2>Como ler o cartão</h2><p class="mut">Passe o mouse (ou clique) na cartinha para ver como chegou na nota.</p><table>${m.st.map(x => `<tr><td>${x[0]}</td><td>${Carta.NOMES[x[0]]}</td></tr>`).join('')}</table>
      <p class="mut">A nota grande é a nota do mês. As seis medidas vão de 0 a 99 e usam só dados do ranking:
      <b>ASS</b> dias trabalhados ÷ esperados · <b>TUR</b> turnos com lançamento · <b>CON</b> quanto menos a nota oscila entre os meses, maior ·
      <b>EVO</b> parte da nota e sobe ou cai 5 por ponto de diferença para o mês anterior · <b>POS</b> lugar pela nota (empate = mesmo lugar) · <b>MED</b> média dos meses. Nenhuma medida fica mais de 20 pontos longe da nota do cartão.
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
  // ?mes= define o mês de referência (ex.: link do álbum). Sem parâmetro → mês mais recente.
  const todosMeses = (a.meses || []).slice().sort((p, q) => ordMes(p.mes) - ordMes(q.mes));
  const mesParam = q.get('mes');
  let idxRef = todosMeses.length - 1;
  if (mesParam) {
    const i = todosMeses.findIndex(m => m.mes === mesParam);
    if (i >= 0) idxRef = i;
  }
  // ?mes=Melhor do ano: a mesma cartinha e a mesma posição do álbum (média de todos os meses), não o mês mais recente
  const anoL = mesParam === Carta.ROTULO_ANO ? Carta.anual(Object.entries(D.agentes).map(([k, x]) => ({ k, a: x })), 2).find(l => l.x.k === idAgente) : null;
  const msHist = todosMeses.slice(0, anoL ? todosMeses.length : idxRef + 1);   // histórico mensal (gráficos e linha do tempo)
  const ms = anoL ? anoL.ms : msHist;   // o que a cartinha mostra: o ano (1 cartão «Média») ou o histórico até o mês escolhido
  const ult = ms[ms.length - 1];
  const rotMes = anoL ? Carta.ROTULO_ANO : (ult && ult.mes);
  const sem = anoL ? [] : (a.semanas || []).filter(s => s.mes === (ult && ult.mes)).slice().sort((x, y) => x.n - y.n);
  document.title = 'Evolução — ' + a.nome + (ult ? ' · ' + rotMes : '');
  const media = msHist.length ? msHist.reduce((t, m) => t + (m.pontos || 0), 0) / msHist.length : null;
  const trab = ult ? `${f1(ult.trab).replace(',0', '')} de ${f1(ult.esp).replace(',0', '')}` : '—';
  const qsAgente = idAgente && /^\d+$/.test(String(idAgente)) ? 'id=' + idAgente : 'nome=' + encodeURIComponent(a.nome);
  const linkRecente = (anoL || idxRef < todosMeses.length - 1)
    ? ` · <a href="agente.html?${qsAgente}">ver mês mais recente</a>`
    : '';
  const linkAlbum = ` · <a href="album.html?mes=${encodeURIComponent(rotMes || '')}">álbum</a>`;
  let html = `<h1><svg class="ico" aria-hidden="true"><use href="#i-trend"/></svg> <span class="nome">${esc(a.nome)}</span></h1><div class="mut">${esc(a.equipe)} · atualizado em ${esc(D.gerado_em)}${linkAlbum}${linkRecente}</div>`;
  html += carta(a, ms);
  if (ult) html += `<div class="card"><div class="kpis">
      <div class="kpi"><span>${anoL ? 'Nota (média do ano)' : 'Nota em ' + esc(ult.mes)}</span><strong>${f1(ult.pontos)}</strong></div>
      <div class="kpi"><span>${anoL ? 'Posição no ano' : 'Posição'}</span><strong>${ult.pos}º de ${ult.total}</strong></div>
      <div class="kpi"><span>Média dos meses</span><strong>${f1(media)}</strong></div>
      <div class="kpi"><span>Dias trabalhados</span><strong>${trab}</strong></div></div></div>`;
  const detHtml = ult ? (anoL ? porqueAno(a, anoL) : porque(a, ult)) : '';
  html += detHtml;   // a explicação da nota logo abaixo dos indicadores: é a primeira coisa que o agente pergunta
  if (msHist.length) html += `<div class="card"><h2>Nota por mês</h2><div class="grafico"><canvas id="gMes" role="img" aria-label="Nota mensal"></canvas></div></div>
    <div class="card"><h2>Dias trabalhados × esperados</h2><div class="grafico"><canvas id="gDias" role="img" aria-label="Dias trabalhados e esperados por mês"></canvas></div></div>`;
  else html += '<div class="card aviso">Este agente ainda não tem mês registrado.</div>';
  if (sem.length >= 1) html += `<div class="card"><h2>Nota por semana (${esc(ult ? ult.mes : '')})</h2><div class="grafico"><canvas id="gSem" role="img" aria-label="Nota semanal"></canvas></div>
      <p class="mut">Semana parcial = ainda em andamento; a nota dela pode mudar até sexta.</p></div>`;
  html += linhaTempo(msHist, sem);
  if (ult && !anoL) {
    if (!detHtml) {
      const li = (arr, cls) => arr.length ? arr.map(x => `<tr><td>${esc(x.c)}</td><td class="n ${cls}">${x.p > 0 ? '+' : ''}${f1(x.p)}</td></tr>`).join('') : '<tr><td class="mut" colspan="2">Nenhum.</td></tr>';
      html += `<div class="card"><h2>O que mais tirou pontos em ${esc(ult.mes)}</h2><table>${li(ult.perdas, 'neg')}</table></div>
        <div class="card"><h2>O que mais deu pontos</h2><table>${li(ult.ganhos, 'pos')}</table></div>`;
    }
  }
  html += `<p class="mut">Só dados públicos do ranking, sem informações de saúde. A conta completa está no Extrato do dashboard e em <a href="album.html#como-calcula">Como o ranking é calculado</a>.</p>`;
  alvo.innerHTML = html;
  const ligar = (id, modo) => { const b = $(id); if (!b) return; b.onclick = () => {
    const msg = $('msgImg'); b.disabled = true; msg.textContent = 'Preparando a imagem…';
    Carta.enviar(a, ms, modo, { id: idAgente, ocultarNomes: document.body.classList.contains('modo-apresentacao'), ocultarFoto: document.body.classList.contains('sem-foto') })
      .then(t => { msg.textContent = t; }, () => { msg.textContent = 'Não consegui gerar a imagem aqui. Abra a página pelo endereço do site (não pelo arquivo no computador) e tente de novo.'; })
      .then(() => { b.disabled = false; }); }; };
  ligar('bBaixar', 'baixar'); ligar('bZap', 'whatsapp');
  const bd = $('bImprimirDet'); if (bd) bd.onclick = () => { document.body.classList.add('so-det'); window.print(); };
  window.addEventListener('afterprint', () => document.body.classList.remove('so-det'));
  const cor = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || '#888';
  if (msHist.length && window.Chart) {
    new Chart($('gMes'), { type: 'line', data: { labels: msHist.map(m => m.mes.replace('/20', '/')), datasets: [{ label: 'Nota', data: msHist.map(m => m.pontos), borderColor: cor('--serie'), backgroundColor: cor('--serie'), tension: .25 }] },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, suggestedMax: 100 } }, plugins: { legend: { display: false } } } });
    new Chart($('gDias'), { type: 'bar', data: { labels: msHist.map(m => m.mes.replace('/20', '/')), datasets: [
      { label: 'Trabalhados', data: msHist.map(m => m.trab), backgroundColor: cor('--serie') }, { label: 'Esperados', data: msHist.map(m => m.esp), backgroundColor: cor('--mut') }] },
      options: { responsive: true, maintainAspectRatio: false } });
  }
  if (sem.length && window.Chart) {
    new Chart($('gSem'), { type: 'bar', data: { labels: sem.map(s => `S${s.n}${s.parcial ? ' (parcial)' : ''}`), datasets: [{ label: 'Nota da semana', data: sem.map(s => s.pontos),
      backgroundColor: sem.map(s => s.parcial ? cor('--mut') : cor('--info')) }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, suggestedMax: 100 } }, plugins: { legend: { display: false } } } });
  }
}
desenhar();
document.addEventListener('sentinela:tema', () => location.reload());
