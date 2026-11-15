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

const NIVEIS = ['LENDÁRIA', 'DESTAQUE', 'OURO', 'PRATA', 'BRONZE', 'AÇO', 'FERRO'];
const COR_NIVEL = { 'LENDÁRIA': '#8A5CF6', 'DESTAQUE': '#EC4899', 'OURO': '#E0A400', 'PRATA': '#9AA9BA', 'BRONZE': '#C47A3A', 'AÇO': '#64748B', 'FERRO': '#4B5563' };
const MIN_MESES_ANO = 2;   // mínimo de cartinhas mensais para entrar no «Melhor do ano»
const ANO = 'Melhor do ano';   // opção do filtro: ranking pela média de todas as cartinhas (todos os meses)
const D = window.AGENTES_DADOS, ag = D && D.agentes ? Object.entries(D.agentes).map(([k, a]) => ({ k, a })) : [];
const meses = [...new Set(ag.flatMap(x => (x.a.meses || []).map(m => m.mes)))].sort((p, q) => ordMes(p) - ordMes(q));
if (!meses.length) { $('album').outerHTML = '<div class="card aviso">Ainda não há cartinhas. Volte depois da próxima atualização do site.</div>'; $('resumo').textContent = ''; }
else {
  $('fMes').innerHTML = `<option value="${ANO}">${ANO} (média de todos os meses)</option>` + meses.slice().reverse().map(m => `<option>${esc(m)}</option>`).join('');
  const q0 = new URLSearchParams(location.search).get('mes'); if (q0 && (q0 === ANO || meses.includes(q0))) $('fMes').value = q0;
  const eqs = [...new Set(ag.map(x => x.a.equipe).filter(Boolean))].sort((p, q) => p.localeCompare(q, 'pt-BR', { numeric: true }));
  $('fEq').insertAdjacentHTML('beforeend', eqs.map(e => `<option>${esc(e)}</option>`).join(''));
  // ---- Compartilhar: baixar a cartinha como imagem ou mandar pelo WhatsApp (a imagem é gerada por Carta.enviar, a mesma de agente.html)
  let visAtual = [];
  const IC_BAIXAR = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m0 0-4-4m4 4 4-4M5 19h14"/></svg>';
  const IC_ZAP = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3h-4l-5 4v-4H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3Z"/></svg>';
  const acoes = i => `<span class="acoes"><button type="button" data-acao="baixar" data-i="${i}" title="Baixar a cartinha como imagem" aria-label="Baixar a cartinha como imagem">${IC_BAIXAR}<span>Baixar</span></button><button type="button" data-acao="whatsapp" data-i="${i}" title="Enviar pelo WhatsApp (no computador abre o WhatsApp Web)" aria-label="Enviar a cartinha pelo WhatsApp">${IC_ZAP}<span>WhatsApp</span></button></span>`;
  const aviso = t => { const m = $('msgImg'); m.textContent = t; m.hidden = !t; clearTimeout(aviso.t); if (t) aviso.t = setTimeout(() => { m.hidden = true; }, 9000); };
  const compartilhar = e => {
    const b = e.target.closest('button[data-acao]'); if (!b) return;
    e.preventDefault(); e.stopPropagation();   // o botão fica dentro do link da cartinha: não abrir a página do agente
    const l = visAtual[+b.dataset.i]; if (!l) return;
    b.disabled = true; aviso('Preparando a imagem…');
    Carta.enviar(l.x.a, l.ms, b.dataset.acao, { id: l.x.k, ocultarNomes: document.body.classList.contains('modo-apresentacao'), ocultarFoto: document.body.classList.contains('sem-foto') })
      .then(aviso, () => aviso('Não consegui gerar a imagem aqui. Abra a página pelo endereço do site (não pelo arquivo no computador) e tente de novo.'))
      .then(() => { b.disabled = false; });
  };
  ['album', 'podio'].forEach(id => $(id).addEventListener('click', compartilhar));
  // botões em cima do link: Enter/Espaço no botão não pode acionar o link também
  ['album', 'podio'].forEach(id => $(id).addEventListener('keydown', e => { if (e.target.closest && e.target.closest('button[data-acao]') && (e.key === 'Enter' || e.key === ' ')) e.stopPropagation(); }, true));
  $('bImprimir').onclick = () => window.print();
  // «Modo reunião»: abre a tela de projeção direto nas cartinhas do mês escolhido (o «Melhor do ano» abre no mês mais recente)
  $('bReuniao').onclick = () => { const m = $('fMes').value; location.href = 'projecao.html' + (m && m !== ANO ? '?mes=' + encodeURIComponent(m) : '') + '#cartinhas'; };
  const desenhar = () => {
    const mes = $('fMes').value, eq = $('fEq').value, niv = $('fNivel').value, bu = norm($('fBusca').value);
    const lista = [], doAno = mes === ANO;
    const cl99 = v => Math.max(0, Math.min(99, Math.round(v)));
    if (doAno) {
      // Melhor do ano: média das notas de TODAS as cartinhas mensais do agente (jul → mês mais recente). Os demais números do cartão seguem a mesma conta de cada mês, somando o período.
      ag.forEach(x => { const ms = (x.a.meses || []).filter(m => m.pontos != null).sort((p, q) => ordMes(p.mes) - ordMes(q.mes)); if (ms.length < MIN_MESES_ANO) return;
        const soma = c => ms.reduce((t, m) => t + (m[c] || 0), 0), notas = ms.map(m => m.pontos), media = Math.round(notas.reduce((t, n) => t + n, 0) / notas.length * 10) / 10;
        const rec = notas.slice(-3), mr = rec.reduce((t, n) => t + n, 0) / rec.length, dp = rec.length > 1 ? Math.sqrt(rec.reduce((t, n) => t + (n - mr) ** 2, 0) / rec.length) : 0;
        const evo = notas.length > 1 ? cl99(50 + 5 * (notas[notas.length - 1] - notas[notas.length - 2])) : 50;
        const u = { mes: 'Média', pontos: media, trab: soma('trab'), esp: soma('esp'), turnos_sem: soma('turnos_sem'), con: cl99(100 - 5 * dp), evo, pos: 0, total: 0, n: ms.length };
        lista.push({ x, ms: [u], u }); });
      lista.sort((p, q) => q.u.pontos - p.u.pontos || q.u.n - p.u.n || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'));
      lista.forEach((l, i) => { l.lugar = i + 1; l.u.pos = i + 1; l.u.total = lista.length; });
    } else ag.forEach(x => { const ms = (x.a.meses || []).slice().sort((p, q) => ordMes(p.mes) - ordMes(q.mes)); const i = ms.findIndex(m => m.mes === mes);
      if (i < 0 || ms[i].pontos == null) return; lista.push({ x, ms: ms.slice(0, i + 1), u: ms[i] }); });
    // desempate: média das notas dos meses ANTERIORES ao mês mostrado (a mesma da tabela "Média Mensal por Agente"); sem histórico fica atrás
    const hist = l => { const v = l.ms.slice(0, -1).map(m => m.pontos).filter(n => n != null); return v.length ? Math.round(v.reduce((t, n) => t + n, 0) / v.length * 10) / 10 : -1; };
    if (!doAno) lista.forEach(l => { l.h = hist(l); });
    if (!doAno) lista.sort((p, q) => Carta.bruta(q.u) - Carta.bruta(p.u) || q.h - p.h || p.u.pos - q.u.pos || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'));
    if (!doAno) lista.forEach((l, i) => { l.lugar = i + 1; });
    lista.forEach(l => { l.nivel = Carta.medidas(l.ms, l.x.k).tier[1]; });
    const base = lista.filter(l => (!eq || l.x.a.equipe === eq) && (!bu || norm(l.x.a.nome).includes(bu)));   // equipe + busca; o nível entra depois
    const vis = base.filter(l => !niv || l.nivel === niv);
    visAtual = vis;
    // atalhos por nível, com a contagem do que está filtrado por equipe/busca (clicar preenche o filtro "Nível")
    $('niveis').innerHTML = [['', 'Todos']].concat(NIVEIS.map(n => [n, n])).map(([v, rot]) => {
      const q = v ? base.filter(l => l.nivel === v).length : base.length;
      return (v && !q && v !== niv) ? '' : `<button type="button" class="nv" data-nivel="${esc(v)}" aria-pressed="${v === niv}" style="--cor:${COR_NIVEL[v] || 'var(--mut)'}"><i></i>${esc(rot)} <b>${q}</b></button>`;
    }).join('');
    const slot = (l, cls) => {
      const qAg = (/^\d+$/.test(l.x.k) ? 'id=' + l.x.k : 'nome=' + encodeURIComponent(l.x.a.nome)) + (doAno ? '' : '&mes=' + encodeURIComponent(mes));
      return `<a class="slot ${cls || ''}" href="agente.html?${qAg}" title="Ver evolução de ${esc(l.x.a.nome)}${doAno ? '' : ' em ' + esc(mes)}"><span class="n${l.lugar <= 3 ? ' m' + l.lugar : ''}" aria-label="${l.lugar}º lugar">${l.lugar}º</span>${doAno ? Carta.html(l.x.a, l.ms, l.x.k, true).replace('1º mês', l.u.n + (l.u.n > 1 ? ' meses' : ' mês')) : Carta.html(l.x.a, l.ms, l.x.k)}${acoes(vis.indexOf(l))}</a>`;
    };
    // Pódio: só sem filtros (com filtro, o top 3 do mês pode nem estar na lista). No HTML a ordem é 1º, 2º, 3º; o CSS põe o 1º no meio.
    const pod = !eq && !bu && !niv && vis.length >= 3 ? vis.slice(0, 3) : [];
    $('podio').hidden = !pod.length;
    $('podio').innerHTML = pod.map((l, i) => slot(l, 'p' + (i + 1))).join('');
    [['p1', '650ms'], ['p2', '200ms'], ['p3', '0ms']].forEach(([c, t]) => $('podio').querySelectorAll('.slot.' + c + ' .carta').forEach(el => el.style.setProperty('--atraso', t)));
    $('album').innerHTML = vis.slice(pod.length).map(l => slot(l)).join('');
    $('resumo').textContent = vis.length ? (doAno ? `${vis.length} cartinha(s) de ${lista.length}: média de todos os meses (só quem tem ${MIN_MESES_ANO} meses ou mais).` : `${vis.length} cartinha(s) de ${lista.length} em ${mes}.`) : 'Nenhuma cartinha com esses filtros.';
  };
  ['fMes', 'fEq', 'fNivel'].forEach(i => $(i).onchange = desenhar); $('fBusca').oninput = desenhar;
  $('niveis').onclick = e => { const b = e.target.closest('.nv'); if (!b) return; $('fNivel').value = b.dataset.nivel; desenhar(); };
  desenhar();
}
document.addEventListener('sentinela:tema', () => {});
