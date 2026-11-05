
const $ = id => document.getElementById(id);
let WORKER = '', pin = '', quem = '', nomes = {}, dets = [];
try { pin = sessionStorage.getItem('pinSentinela') || ''; } catch (e) {}

const TIPOS = {
  ausencia_justificada: 'Ausência justificada', folga: 'Folga', meia_folga: 'Meia folga',
  meia_ausencia_justificada: 'Meia ausência justificada', ferias: 'Férias'
};
const DICAS = {
  ausencia_justificada: 'Informe só as datas. Não digite CID nem diagnóstico. Não desconta pontos.',
  folga: 'Dia de folga: os dois turnos saem da cobrança.',
  meia_folga: 'Só o turno escolhido sai da cobrança (conta 0,5 dia esperado).',
  meia_ausencia_justificada: 'Só o turno escolhido sai da cobrança. Não informe CID nem diagnóstico.',
  ferias: 'Máximo de 30 dias corridos. O que passar disso conta como falta.'
};

/* ---------- utilidades ---------- */
function el(tag, attrs, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === 'class') e.className = v; else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? '' : v);
  }
  for (const f of filhos.flat()) if (f != null) e.append(f.nodeType ? f : document.createTextNode(String(f)));
  return e;
}
const brData = iso => iso ? iso.split('-').reverse().join('/') : '';
const isoData = br => { const [d, m, a] = br.split('/'); return `${a}-${m}-${d}`; };
const paraDate = br => { const [d, m, a] = br.split('/').map(Number); return new Date(a, m - 1, d); };
const hoje = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const diasEntre = (ini, fim) => Math.round((paraDate(fim) - paraDate(ini)) / 86400000) + 1;
function toast(msg, erro) {
  const t = $('toast'); t.textContent = msg; t.style.display = 'block'; t.style.background = erro ? 'var(--bad)' : '';
  t.style.color = erro ? '#fff' : ''; clearTimeout(toast.t); toast.t = setTimeout(() => { t.style.display = 'none'; }, erro ? 7000 : 4500);
}
const nomeDe = id => (nomes[String(id)] || {}).nome || `Agente ${id}`;
const equipeDe = id => (nomes[String(id)] || {}).equipe || '';

async function api(caminho, corpo) {
  const r = await fetch(WORKER + caminho, {
    method: corpo ? 'POST' : 'GET',
    headers: { 'Content-Type': 'application/json', 'X-PIN': pin },
    body: corpo ? JSON.stringify({ ...corpo, pin }) : undefined
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.erro || `Erro ${r.status}`);
  return j;
}
async function enviar(dec, okMsg) {
  try { await api('/acao', dec); toast(okMsg || 'Enviado! O site atualiza em alguns minutos.'); return true; }
  catch (e) { toast(e.message, true); return false; }
}

/* ---------- entrada ---------- */
async function iniciar() {
  try {
    const cfg = await (await fetch('data/config_worker.json?' + Date.now())).json();
    WORKER = (cfg.url || '').replace(/\/$/, '');
  } catch (e) { WORKER = ''; }
  if (!WORKER) { $('semWorker').hidden = false; return; }
  if (pin) { try { await entrar(pin, true); return; } catch (e) { pin = ''; } }
  $('entrada').hidden = false;
}
async function entrar(p, silencioso) {
  pin = p;
  const j = await api('/log');
  quem = j.quem; try { sessionStorage.setItem('pinSentinela', pin); } catch (e) {}
  $('quem').textContent = quem; $('entrada').hidden = true; $('app').hidden = false;
  await carregarBase(); mostrarAba('ferias');
}
$('btnEntrar').onclick = async () => {
  $('erroPin').hidden = true;
  try { await entrar($('pin').value.trim()); }
  catch (e) { $('erroPin').textContent = e.message; $('erroPin').hidden = false; }
};
$('pin').addEventListener('keydown', e => { if (e.key === 'Enter') $('btnEntrar').click(); });
$('btnSair').onclick = () => { try { sessionStorage.removeItem('pinSentinela'); } catch (e) {} location.reload(); };

async function carregarBase() {
  try { nomes = await (await fetch('data/agentes_nomes.json?' + Date.now())).json(); } catch (e) { nomes = {}; }
  try { dets = await (await fetch('data/deteccoes_pendentes.json?' + Date.now())).json(); } catch (e) { dets = []; }
  const ag = $('nvAg');
  ag.innerHTML = '<option value="">Escolha…</option>';
  Object.keys(nomes).sort((a, b) => nomeDe(a).localeCompare(nomeDe(b), 'pt-BR'))
    .forEach(id => ag.append(el('option', { value: id }, `${nomeDe(id)} — ${equipeDe(id)}`)));
  $('nvIni').value = $('nvFim').value = hoje();
  $('ajAg').innerHTML = ag.innerHTML; $('ajData').value = hoje(); $('pdIni').value = $('pdFim').value = hoje();
  const eq = [...new Set(Object.values(nomes).map(a => a.equipe).filter(Boolean))].sort();
  $('pdAlvo').replaceChildren(el('option', { value: 'todos' }, 'Todas as equipes'), ...eq.map(e => el('option', { value: e }, e)));
  atualizarDicaNovo();
}

/* ---------- abas ---------- */
function mostrarAba(nome) {
  document.querySelectorAll('.abas button').forEach(b => b.setAttribute('aria-selected', b.dataset.aba === nome));
  ['ferias', 'dias', 'novo', 'ajuste', 'parada', 'contest', 'fechar', 'hist', 'ajuda'].forEach(a => { $('aba-' + a).hidden = a !== nome; });
  if (nome === 'ferias') desenharFerias(); if (nome === 'dias') carregarDias(); if (nome === 'hist') carregarHist();
  if (nome === 'ajuste') carregarAjustes(); if (nome === 'parada') carregarParadas();
  if (nome === 'contest') carregarContest(); if (nome === 'fechar') carregarFechar();
}
document.querySelectorAll('.abas button').forEach(b => b.onclick = () => mostrarAba(b.dataset.aba));

/* ---------- aba Férias ---------- */
$('buscaFerias').addEventListener('input', desenharFerias);
function desenharFerias() {
  const busca = $('buscaFerias').value.trim().toLowerCase();
  const corte = new Date(); corte.setDate(corte.getDate() - 90);
  let itens = dets.filter(e => e.tipo === 'possiveis_ferias' && (e.status === 'confirmada' || e.status === 'falta'));
  if (!busca) itens = itens.filter(e => paraDate(e.fim) >= corte);
  else itens = itens.filter(e => (e.nome_agente || '').toLowerCase().includes(busca));
  itens.sort((a, b) => paraDate(b.fim) - paraDate(a.fim));
  $('infoFerias').textContent = busca ? `${itens.length} período(s) encontrado(s).`
    : `${itens.length} período(s) dos últimos 90 dias. Use a busca para ver períodos mais antigos.`;
  const lista = $('listaFerias'); lista.replaceChildren();
  if (!itens.length) lista.append(el('p', { class: 'mut' }, 'Nada por aqui.'));
  for (const e of itens.slice(0, 60)) lista.append(cartaoFerias(e));
}
function cartaoFerias(e) {
  const falta = e.status === 'falta';
  const badges = [];
  if (falta) badges.push(el('span', { class: 'badge bad' }, 'Conta como falta'));
  else if (e.validada_por) badges.push(el('span', { class: 'badge ok' }, `Validada por ${e.validada_por}`));
  else badges.push(el('span', { class: 'badge' }, e.ajustado_manual ? 'Ajustada pela coordenação' : 'Confirmada automaticamente'));
  if (e.revisao_classificacao_necessaria && !falta) badges.push(el('span', { class: 'badge warn' }, 'Conferir: outro agente da equipe também ausente'));
  const sub = el('div', { class: 'sub', hidden: true });
  const cartao = el('div', { class: 'card' },
    el('h2', {}, e.nome_agente || nomeDe(e.id_agente)),
    el('div', { class: 'mut' }, `${e.equipe || equipeDe(e.id_agente)} · ${e.inicio} a ${e.fim} (${diasEntre(e.inicio, e.fim)} dias corridos)`),
    el('div', {}, badges), sub);
  const acoes = el('div', { class: 'acoes' });
  const dec = extra => ({ id_agente: e.id_agente, inicio: e.inicio, fim: e.fim, ...extra });
  if (!falta) {
    acoes.append(el('button', { class: 'pri', onclick: async () => { if (await enviar(dec({ acao: 'ferias_confirmar' }), 'Férias validadas.')) cartao.remove(); } }, '✅ Está certo'));
  }
  acoes.append(el('button', { onclick: () => abrirAjuste(sub, e, falta) }, falta ? '↩️ Era férias' : 'Ajustar datas'));
  if (!falta) acoes.append(el('button', { class: 'bad', onclick: async () => {
    if (!confirm(`Os dias de ${e.nome_agente} (${e.inicio} a ${e.fim}) deixam de ser férias e passam a contar como FALTA. Confirmar?`)) return;
    if (await enviar(dec({ acao: 'ferias_nao' }), 'Marcado como falta. Atualizando o site…')) cartao.remove();
  } }, '❌ Não é férias'));
  cartao.append(acoes); return cartao;
}
function abrirAjuste(sub, e, falta) {
  sub.hidden = !sub.hidden; if (sub.hidden) return;
  const ini = el('input', { type: 'date', value: isoData(e.inicio) });
  const fim = el('input', { type: 'date', value: isoData(e.fim) });
  const aviso = el('p', { class: 'mut' }, falta ? 'Informe os dias que SÃO férias (máximo 30 dias corridos).'
    : 'O período informado vira o período final das férias (máximo 30 dias corridos). Dias fora dele contam como falta se não houve trabalho.');
  const btn = el('button', { class: 'pri', onclick: async () => {
    if (!ini.value || !fim.value || fim.value < ini.value) return toast('Confira as datas.', true);
    if (diasEntre(brData(ini.value), brData(fim.value)) > 30) return toast('Férias têm no máximo 30 dias corridos.', true);
    btn.disabled = true;
    if (await enviar({ acao: 'ferias_ajustar', id_agente: e.id_agente, inicio: brData(ini.value), fim: brData(fim.value) }, 'Férias ajustadas. Atualizando o site…')) sub.hidden = true;
    btn.disabled = false;
  } }, 'Salvar período');
  sub.replaceChildren(aviso, el('div', { class: 'linha' }, el('div', {}, el('label', {}, 'Primeiro dia'), ini), el('div', {}, el('label', {}, 'Último dia'), fim)), el('div', { class: 'acoes' }, btn));
}

/* ---------- aba Dias sem trabalho ---------- */
let sugestoes = [], mostrar = 20;
async function carregarDias() {
  $('infoDias').textContent = 'Carregando…';
  try {
    const j = await api('/sugestoes');
    sugestoes = j.itens || [];
    $('infoDias').textContent = sugestoes.length
      ? `${sugestoes.length} período(s) sem trabalho para classificar (lista de ${j.gerado_em || 'data desconhecida'}). Enquanto não classificar, o dia conta como falta.`
      : 'Nada para classificar agora.';
    mostrar = 20; desenharDias();
  } catch (e) { $('infoDias').textContent = ''; $('listaDias').replaceChildren(el('div', { class: 'erro' }, e.message)); }
}
$('buscaDias').addEventListener('input', () => { mostrar = 20; desenharDias(); });
$('maisDias').onclick = () => { mostrar += 20; desenharDias(); };
function desenharDias() {
  const busca = $('buscaDias').value.trim().toLowerCase();
  const itens = sugestoes.filter(s => !busca || (s.nome + ' ' + s.equipe).toLowerCase().includes(busca));
  const lista = $('listaDias'); lista.replaceChildren();
  for (const s of itens.slice(0, mostrar)) lista.append(cartaoDia(s, itens));
  $('maisDias').hidden = itens.length <= mostrar;
}
function cartaoDia(s, todos) {
  const chips = s.dias.map(d => el('span', { class: 'chip' }, `${d.dia.slice(0, 5)} ${d.turnos.length === 2 ? '(dia todo)' : '(' + d.turnos[0].toLowerCase() + ')'}`));
  const sub = el('div', { class: 'sub', hidden: true });
  const cartao = el('div', { class: 'card' },
    el('h2', {}, s.nome), el('div', { class: 'mut' }, `${s.equipe} · ${s.inicio === s.fim ? s.inicio : s.inicio + ' a ' + s.fim} · ${s.dias.length} dia(s)`),
    el('div', { class: 'mut' }, 'Sugestão: ' + s.sugestao), el('div', {}, chips), sub);
  const unicoTurno = s.dias.every(d => d.turnos.length === 1 && d.turnos[0] === s.dias[0].turnos[0]) ? s.dias[0].turnos[0] : 'Manhã';
  const remover = () => { sugestoes = sugestoes.filter(x => x !== s); cartao.remove(); };
  const acoes = el('div', { class: 'acoes' });
  [['ausencia_justificada', 'Ausência justificada'], ['folga', 'Folga'], ['meia_folga', 'Meia folga']].forEach(([tipo, rotulo]) =>
    acoes.append(el('button', { onclick: () => abrirClassificar(sub, s, tipo, unicoTurno, remover) }, rotulo)));
  acoes.append(el('button', { class: 'bad', onclick: async () => {
    if (!confirm(`Confirmar FALTA para ${s.nome} em ${s.inicio === s.fim ? s.inicio : s.inicio + ' a ' + s.fim}?`)) return;
    if (await enviar({ acao: 'falta', id_agente: s.id_agente, inicio: s.inicio, fim: s.fim }, 'Falta registrada.')) remover();
  } }, 'Falta'));
  cartao.append(acoes);
  const doAgente = todos.filter(x => x.id_agente === s.id_agente);
  if (doAgente.length > 1 && doAgente[0] === s) {
    cartao.append(el('div', { class: 'acoes' }, el('button', { class: 'bad', onclick: async () => {
      if (!confirm(`Marcar os ${doAgente.length} períodos de ${s.nome} como FALTA?`)) return;
      for (const x of doAgente) { if (!(await enviar({ acao: 'falta', id_agente: x.id_agente, inicio: x.inicio, fim: x.fim }, 'Falta registrada.'))) break;
        sugestoes = sugestoes.filter(y => y !== x); }
      desenharDias();
    } }, `Todos os ${doAgente.length} períodos de ${s.nome.split(' ')[0]} → Falta`)));
  }
  return cartao;
}
function abrirClassificar(sub, s, tipo, turnoPadrao, aoTerminar) {
  const ini = el('input', { type: 'date', value: isoData(s.inicio) }), fim = el('input', { type: 'date', value: isoData(s.fim) });
  const turno = el('select', {}, el('option', { selected: turnoPadrao === 'Manhã' }, 'Manhã'), el('option', { selected: turnoPadrao === 'Tarde' }, 'Tarde'));
  const meio = tipo.startsWith('meia');
  const btn = el('button', { class: 'pri', onclick: async () => {
    if (!ini.value || !fim.value || fim.value < ini.value) return toast('Confira as datas.', true);
    btn.disabled = true;
    const ok = await enviar({ acao: 'lancar', tipo, id_agente: s.id_agente, inicio: brData(ini.value), fim: brData(fim.value), ...(meio ? { turno: turno.value } : {}) },
      `${TIPOS[tipo]} enviada. Atualizando o site…`);
    btn.disabled = false; if (ok) aoTerminar();
  } }, `Confirmar ${TIPOS[tipo].toLowerCase()}`);
  sub.hidden = false;
  sub.replaceChildren(el('p', { class: 'mut' }, 'Ajuste as datas se precisar (por exemplo, se só parte dos dias foi folga).' + (tipo === 'ausencia_justificada' ? ' Não digite CID nem diagnóstico.' : '')),
    el('div', { class: 'linha' }, el('div', {}, el('label', {}, 'Primeiro dia'), ini), el('div', {}, el('label', {}, 'Último dia'), fim)),
    meio ? el('div', {}, el('label', {}, 'Turno'), turno) : null, el('div', { class: 'acoes' }, btn));
}

/* ---------- aba Novo lançamento ---------- */
function atualizarDicaNovo() {
  const t = $('nvTipo').value; $('nvDica').textContent = DICAS[t]; $('nvTurnoBox').hidden = !t.startsWith('meia');
}
$('nvTipo').onchange = atualizarDicaNovo;
$('nvIni').onchange = () => { if (!$('nvFim').value || $('nvFim').value < $('nvIni').value) $('nvFim').value = $('nvIni').value; };
$('nvBtn').onclick = async () => {
  const tipo = $('nvTipo').value, id = $('nvAg').value, ini = $('nvIni').value, fim = $('nvFim').value;
  if (!id) return toast('Escolha o agente.', true);
  if (!ini || !fim || fim < ini) return toast('Confira as datas.', true);
  if (tipo === 'ferias' && diasEntre(brData(ini), brData(fim)) > 30) return toast('Férias têm no máximo 30 dias corridos.', true);
  $('nvBtn').disabled = true;
  const ok = await enviar({ acao: 'lancar', tipo, id_agente: Number(id), inicio: brData(ini), fim: brData(fim), ...(tipo.startsWith('meia') ? { turno: $('nvTurno').value } : {}) },
    `${TIPOS[tipo]} enviada. Atualizando o site…`);
  $('nvBtn').disabled = false; if (ok) { $('nvAg').value = ''; }
};

/* ---------- aba Histórico ---------- */
$('histAtualizar').onclick = carregarHist;
async function carregarHist() {
  const alvo = $('listaHist'); alvo.replaceChildren(el('p', { class: 'mut' }, 'Carregando…'));
  try {
    const j = await api('/log'); const log = j.log || [];
    if (!log.length) return alvo.replaceChildren(el('p', { class: 'mut' }, 'Nenhuma decisão registrada ainda.'));
    const ACOES = { ferias_confirmar: 'Férias validadas', ferias_nao: 'Não é férias', ferias_ajustar: 'Férias ajustadas', lancar: 'Lançamento', remover: 'Lançamento removido', falta: 'Falta', falta_remover: 'Falta desfeita', ajuste: 'Ajuste de pontos', ajuste_remover: 'Ajuste desfeito', parada: 'Equipe parada', parada_remover: 'Parada removida', fechar_mes: 'Mês fechado', reabrir_mes: 'Mês reaberto', contestacao_responder: 'Contestação respondida' };
    const tb = el('table', {}, el('thead', {}, el('tr', {}, ...['Quando', 'Quem', 'O quê', 'Situação'].map(t => el('th', {}, t)))));
    const corpo = el('tbody');
    for (const l of log.slice(0, 100)) {
      const d = l.dados || {}; const q = new Date(l.quando);
      const oque = l.resumo && !d.id_agente ? `${ACOES[d.acao] || d.acao}: ${l.resumo.split(': ').slice(1).join(': ')}` : `${ACOES[d.acao] || d.acao}${d.tipo ? ' — ' + (TIPOS[d.tipo] || d.tipo) + (d.turno ? ' (' + d.turno.toLowerCase() + ')' : '') : ''}: ${nomeDe(d.id_agente)}, ${d.inicio}${d.fim !== d.inicio ? ' a ' + d.fim : ''}`;
      const sit = l.status === 'ok' ? '✅ Aplicado' : l.status === 'erro' ? '❌ ' + (l.msg || 'Erro') : '⏳ Aguardando';
      corpo.append(el('tr', {}, el('td', {}, q.toLocaleDateString('pt-BR') + ' ' + q.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })), el('td', {}, l.quem), el('td', {}, oque), el('td', {}, sit)));
    }
    tb.append(corpo); alvo.replaceChildren(el('div', { class: 'card', style: 'overflow-x:auto' }, tb));
  } catch (e) { alvo.replaceChildren(el('div', { class: 'erro' }, e.message)); }
}

/* ---------- Sessão 8: ajuste de pontos ---------- */
const lerPublico = async c => { try { return await (await fetch(c + '?' + Date.now())).json(); } catch (e) { return []; } };
const fmtPts = n => (n > 0 ? '+' : '') + String(n).replace('.', ',');
$('ajBtn').onclick = async () => {
  const id = $('ajAg').value, data = $('ajData').value, pts = Number($('ajPts').value.replace(',', '.')), mot = $('ajMot').value.trim();
  if (!id) return toast('Escolha o agente.', true);
  if (!data) return toast('Escolha o dia.', true);
  if (!pts || Math.abs(pts) > 20) return toast('Pontos: diferente de zero e no máximo 20 (para mais ou para menos).', true);
  if (mot.length < 3) return toast('Escreva o motivo.', true);
  if (!confirm(`Confirmar?\n\n${nomeDe(id)}\nDia ${brData(data)}\n${fmtPts(pts)} ponto(s)\nMotivo: ${mot}\n\nO motivo aparecerá no Extrato.`)) return;
  $('ajBtn').disabled = true;
  const ok = await enviar({ acao: 'ajuste', id_agente: Number(id), data: brData(data), pontos: pts, motivo: mot }, 'Ajuste enviado. Atualizando o site…');
  $('ajBtn').disabled = false; if (ok) { $('ajMot').value = ''; $('ajPts').value = ''; setTimeout(carregarAjustes, 1500); }
};
async function carregarAjustes() {
  const lista = (await lerPublico('data/ajustes_ranking.json')).slice().reverse().slice(0, 40);
  const alvo = $('listaAjustes'); alvo.replaceChildren();
  if (!lista.length) return alvo.append(el('p', { class: 'mut' }, 'Nenhum ajuste lançado.'));
  for (const a of lista) {
    const c = el('div', { class: 'card' }, el('h2', {}, nomeDe(a.id_agente)),
      el('div', { class: 'mut' }, `${a.data} · ${fmtPts(a.pontos)} ponto(s) · ${a.motivo}${a.por ? ' · por ' + a.por : ''}`),
      el('div', { class: 'acoes' }, el('button', { class: 'bad', onclick: async () => {
        if (!confirm(`Desfazer o ajuste de ${fmtPts(a.pontos)} ponto(s) de ${nomeDe(a.id_agente)} em ${a.data}?`)) return;
        if (await enviar({ acao: 'ajuste_remover', id_agente: a.id_agente, data: a.data, pontos: a.pontos, motivo: a.motivo }, 'Ajuste desfeito. Atualizando o site…')) c.remove();
      } }, 'Desfazer')));
    alvo.append(c);
  }
}

/* ---------- equipe parada ---------- */
$('pdIni').onchange = () => { if ($('pdFim').value < $('pdIni').value) $('pdFim').value = $('pdIni').value; };
$('pdBtn').onclick = async () => {
  const ini = $('pdIni').value, fim = $('pdFim').value, alvo = $('pdAlvo').value, turno = $('pdTurno').value, mot = $('pdMot').value;
  if (!ini || !fim || fim < ini) return toast('Confira as datas.', true);
  if (diasEntre(brData(ini), brData(fim)) > 30) return toast('No máximo 30 dias de uma vez.', true);
  const quem = alvo === 'todos' ? 'TODAS as equipes' : alvo;
  if (!confirm(`Confirmar?\n\n${mot}\n${quem}\n${brData(ini)}${ini !== fim ? ' a ' + brData(fim) : ''}${turno ? ' — só ' + turno.toLowerCase() : ' — dia inteiro'}\n\nNesses dias ninguém é cobrado por visitas.`)) return;
  $('pdBtn').disabled = true;
  const ok = await enviar({ acao: 'parada', alvo: alvo === 'todos' ? 'todos' : 'equipe', ...(alvo === 'todos' ? {} : { equipe: alvo }), motivo: mot,
    inicio: brData(ini), fim: brData(fim), ...(turno ? { turno } : {}) }, 'Parada enviada. Atualizando o site…');
  $('pdBtn').disabled = false; if (ok) setTimeout(carregarParadas, 1500);
};
const MOTIVOS_PARADA = ['Chuva', 'Reunião/Treinamento', 'Levantamento de Índice', 'Instalação de Ovitrampa', 'Recolha de Ovitrampa', 'Recuperação de Casas'];
async function carregarParadas() {
  const lista = (await lerPublico('data/cronograma_ausencias.json')).filter(e => e.alvo !== 'agente' && MOTIVOS_PARADA.includes(e.motivo))
    .sort((a, b) => paraDate(b.inicio) - paraDate(a.inicio)).slice(0, 30);
  const alvo = $('listaParadas'); alvo.replaceChildren();
  if (!lista.length) return alvo.append(el('p', { class: 'mut' }, 'Nenhuma parada lançada.'));
  for (const e of lista) {
    const c = el('div', { class: 'card' }, el('h2', {}, e.motivo),
      el('div', { class: 'mut' }, `${e.alvo === 'todos' ? 'Todas as equipes' : e.equipe} · ${e.inicio}${e.fim !== e.inicio ? ' a ' + e.fim : ''}${e.turno ? ' · ' + e.turno : ''}`),
      el('div', { class: 'acoes' }, el('button', { class: 'bad', onclick: async () => {
        if (!confirm('Remover esta parada? Os dias voltam a ser cobrados.')) return;
        if (await enviar({ acao: 'parada_remover', alvo: e.alvo, ...(e.equipe ? { equipe: e.equipe } : {}), motivo: e.motivo, inicio: e.inicio, fim: e.fim, ...(e.turno ? { turno: e.turno } : {}) }, 'Parada removida. Atualizando o site…')) c.remove();
      } }, 'Remover')));
    alvo.append(c);
  }
}

/* ---------- fechar mês ---------- */
let checklistMes = null;
async function carregarFechar() {
  const alvo = $('checklist'); alvo.replaceChildren(el('p', { class: 'mut' }, 'Carregando…')); $('fcBtn').disabled = true;
  const arq = await lerPublico('data/meses_arquivados.json');
  $('raMes').replaceChildren(...(Array.isArray(arq) ? arq : []).map(a => el('option', { value: a.mes }, a.mes)).reverse());
  try {
    const j = await api('/checklist'); checklistMes = j;
    if (j.vazio) return alvo.replaceChildren(el('p', { class: 'mut' }, 'A lista de conferência ainda não foi gerada. Ela aparece depois da próxima atualização do site.'));
    alvo.replaceChildren(el('p', {}, el('b', {}, j.mes), j.periodo ? ` (${j.periodo})` : ''),
      ...(j.itens || []).map(i => el('p', {}, (i.ok === true ? '✅ ' : '❌ ') + i.texto)));
    if (j.erro) alvo.append(el('div', { class: 'aviso' }, j.erro));
    $('fcBtn').disabled = !j.pronto; $('fcBtn').textContent = `Fechar ${j.mes}`;
  } catch (e) { alvo.replaceChildren(el('div', { class: 'erro' }, e.message)); }
}
$('fcBtn').onclick = async () => {
  if (!checklistMes || !checklistMes.pronto) return;
  if (!confirm(`Fechar ${checklistMes.mes}?\n\nAs notas do mês ficam congeladas e o mês seguinte passa a ser o aberto.`)) return;
  $('fcBtn').disabled = true;
  if (await enviar({ acao: 'fechar_mes', mes: checklistMes.mes }, 'Fechamento enviado. Em alguns minutos o mês aparece como fechado.')) setTimeout(carregarFechar, 2000);
};
$('raBtn').onclick = async () => {
  const mes = $('raMes').value, conf = $('raConf').value.trim();
  if (!mes) return toast('Nenhum mês fechado para reabrir.', true);
  if (conf.toLowerCase() !== mes.toLowerCase()) return toast(`Digite exatamente: ${mes}`, true);
  if (!confirm(`REABRIR ${mes}? Uma cópia de segurança será feita antes.`)) return;
  if (await enviar({ acao: 'reabrir_mes', mes, confirmacao: conf }, 'Reabertura enviada. Veja o resultado em Histórico.')) $('raConf').value = '';
};

/* ---------- contestações ---------- */
$('ctAtualizar').onclick = carregarContest;
async function carregarContest() {
  const alvo = $('listaContest'); alvo.replaceChildren(el('p', { class: 'mut' }, 'Carregando…'));
  try {
    const j = await api('/contestacoes'); const itens = j.itens || [];
    const abertas = itens.filter(i => i.status === 'aberta');
    alvo.replaceChildren(el('p', { class: 'mut' }, abertas.length ? `${abertas.length} pedido(s) esperando resposta.` : 'Nenhum pedido esperando resposta.'));
    for (const c of abertas) alvo.append(cartaoContest(c));
    const resp = itens.filter(i => i.status !== 'aberta').slice(0, 15);
    if (resp.length) alvo.append(el('h2', {}, 'Respondidos'), ...resp.map(c => el('div', { class: 'card' }, el('b', {}, nomeDe(c.id_agente)),
      el('div', { class: 'mut' }, `${c.criterio} · ${c.mes} · ${c.status === 'aceita' ? '✅ aceita' : '⛔ recusada'} · ${c.resposta || ''}`))));
  } catch (e) { alvo.replaceChildren(el('div', { class: 'erro' }, e.message)); }
}
function cartaoContest(c) {
  const sub = el('div', { class: 'sub', hidden: true });
  const cartao = el('div', { class: 'card' }, el('h2', {}, nomeDe(c.id_agente)),
    el('div', { class: 'mut' }, `${equipeDe(c.id_agente)} · ${c.mes} · critério: ${c.criterio} · código ${c.codigo}`),
    el('p', {}, `“${c.texto}”`), sub);
  const resp = el('input', { maxlength: 240, placeholder: 'Resposta curta para o agente' });
  const pts = el('input', { type: 'number', step: '0.5', min: '-20', max: '20', placeholder: 'Pontos (deixe vazio se não der pontos)' });
  const data = el('input', { type: 'date', value: hoje() });
  const mot = el('input', { maxlength: 80, value: 'Contestação aceita' });
  const campos = el('div', {}, el('label', {}, 'Resposta'), resp);
  const extra = el('div', { hidden: true }, el('label', {}, 'Pontos a dar'), pts, el('label', {}, 'Dia do ajuste'), data, el('label', {}, 'Motivo (aparece no Extrato)'), mot);
  async function responder(decisao) {
    if (resp.value.trim().length < 3) return toast('Escreva uma resposta curta.', true);
    const corpo = { acao: 'contestacao_responder', codigo: c.codigo, decisao, resposta: resp.value.trim() };
    if (decisao === 'aceitar' && pts.value !== '') Object.assign(corpo, { pontos: Number(pts.value.replace(',', '.')), data: brData(data.value), motivo: mot.value.trim() });
    if (await enviar(corpo, decisao === 'aceitar' ? 'Pedido aceito.' : 'Pedido recusado.')) cartao.remove();
  }
  sub.append(campos, extra);
  cartao.append(el('div', { class: 'acoes' },
    el('button', { class: 'pri', onclick: () => { sub.hidden = false; extra.hidden = false; if (!cartao.dataset.ac) { cartao.dataset.ac = 1; sub.append(el('div', { class: 'acoes' }, el('button', { class: 'pri', onclick: () => responder('aceitar') }, 'Confirmar: aceitar'))); } } }, 'Aceitar'),
    el('button', { class: 'bad', onclick: () => { sub.hidden = false; extra.hidden = true; if (!cartao.dataset.rc) { cartao.dataset.rc = 1; sub.append(el('div', { class: 'acoes' }, el('button', { class: 'bad', onclick: () => responder('recusar') }, 'Confirmar: recusar'))); } } }, 'Recusar')));
  return cartao;
}

/* ---------- aplicativo instalável ---------- */
if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});

iniciar();
