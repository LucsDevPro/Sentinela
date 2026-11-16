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

const NIVEIS = ['LENDÁRIA', 'DESTAQUE', 'ELITE', 'OURO', 'PRATA', 'BRONZE', 'AÇO', 'FERRO'];
const COR_NIVEL = { 'LENDÁRIA': '#8A5CF6', 'DESTAQUE': '#EC4899', 'ELITE': '#F2C230', 'OURO': '#E0A400', 'PRATA': '#9AA9BA', 'BRONZE': '#C47A3A', 'AÇO': '#64748B', 'FERRO': '#4B5563' };
const MIN_MESES_ANO = 2;   // mínimo de cartinhas mensais para entrar no «Melhor do ano»
const ANO = 'Melhor do ano';   // opção do filtro: ranking pela média de todas as cartinhas (todos os meses)
const D = window.AGENTES_DADOS, ag = D && D.agentes ? Object.entries(D.agentes).map(([k, a]) => ({ k, a })) : [];
const meses = [...new Set(ag.flatMap(x => (x.a.meses || []).map(m => m.mes)))].sort((p, q) => ordMes(p) - ordMes(q));
if (!meses.length) { $('album').outerHTML = '<div class="card aviso">Ainda não há cartinhas. Volte depois da próxima atualização do site.</div>'; $('resumo').textContent = ''; }
else {
  $('fMes').innerHTML = `<option value="${ANO}">${ANO} (média de todos os meses)</option>` + meses.slice().reverse().map(m => `<option>${esc(m)}</option>`).join('');
  const q0 = new URLSearchParams(location.search).get('mes'); if (q0 && (q0 === ANO || meses.includes(q0))) $('fMes').value = q0;
  const eqs = [...new Set(ag.map(x => x.a.equipe).filter(Boolean))].sort((p, q) => p.localeCompare(q, 'pt-BR', { numeric: true }));
  $('fEq').insertAdjacentHTML('beforeend', eqs.map(e => `<option value="${esc(e)}">${esc(e)}</option>`).join(''));
  // filtros que vêm no endereço (?eq=Equipe 3&q=ana&nivel=OURO): dá para mandar o link do álbum de uma equipe
  { const qs = new URLSearchParams(location.search), e0 = qs.get('eq'), n0 = qs.get('nivel');
    if (e0 && eqs.includes(e0)) $('fEq').value = e0; if (n0) $('fNivel').value = n0; if (qs.get('q')) $('fBusca').value = qs.get('q'); }
  // ---- Compartilhar: baixar a cartinha como imagem ou mandar pelo WhatsApp (a imagem é gerada por Carta.enviar, a mesma de agente.html)
  let visAtual = [], mesAnim = null; const confeteVisto = new Set();
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
    if (doAno) {
      // Melhor do ano: média das notas de TODAS as cartinhas mensais do agente (a conta mora em Carta.anual, a mesma usada por agente.html)
      Carta.anual(ag, MIN_MESES_ANO).forEach(l => lista.push(l));
    } else ag.forEach(x => { const ms = (x.a.meses || []).slice().sort((p, q) => ordMes(p.mes) - ordMes(q.mes)); const i = ms.findIndex(m => m.mes === mes);
      if (i < 0 || ms[i].pontos == null) return; lista.push({ x, ms: ms.slice(0, i + 1), u: ms[i] }); });
    // desempate: média das notas dos meses ANTERIORES ao mês mostrado (a mesma da tabela "Média Mensal por Agente"); sem histórico fica atrás
    const hist = l => { const v = l.ms.slice(0, -1).map(m => m.pontos).filter(n => n != null); return v.length ? Math.round(v.reduce((t, n) => t + n, 0) / v.length * 10) / 10 : -1; };
    if (!doAno) lista.forEach(l => { l.h = hist(l); });
    if (!doAno) lista.sort((p, q) => Carta.bruta(q.u) - Carta.bruta(p.u) || q.h - p.h || p.u.pos - q.u.pos || p.x.a.nome.localeCompare(q.x.a.nome, 'pt-BR'));
    if (!doAno) lista.forEach((l, i) => { l.lugar = i + 1; });
    lista.forEach(l => { l.nivel = Carta.medidas(l.ms, l.x.k).tier[1]; });
    // rótulo de cada equipe com quantas cartinhas ela tem NESTE mês (antes de filtrar), para achar a equipe certa sem abrir uma a uma
    [...$('fEq').options].forEach(o => { if (o.value) o.textContent = `${o.value} (${lista.filter(l => l.x.a.equipe === o.value).length})`; });
    $('bLimpar').hidden = !(eq || niv || bu);
    try { const u = new URLSearchParams(location.search); [['eq', eq], ['nivel', niv], ['q', $('fBusca').value.trim()]].forEach(([k, v]) => v ? u.set(k, v) : u.delete(k)); u.set('mes', mes); history.replaceState(null, '', '?' + u.toString() + location.hash); } catch (e) {}
    const base = lista.filter(l => (!eq || l.x.a.equipe === eq) && (!bu || norm(l.x.a.nome).includes(bu)));   // equipe + busca; o nível entra depois
    const vis = base.filter(l => !niv || l.nivel === niv);
    visAtual = vis; $('bZip').querySelector('span').textContent = vis.length ? `Baixar todas (${vis.length}) .zip` : 'Baixar todas (.zip)'; $('bZip').disabled = !vis.length;
    // atalhos por nível, com a contagem do que está filtrado por equipe/busca (clicar preenche o filtro "Nível")
    $('niveis').innerHTML = [['', 'Todos']].concat(NIVEIS.map(n => [n, n])).map(([v, rot]) => {
      const q = v ? base.filter(l => l.nivel === v).length : base.length;
      return (v && !q && v !== niv) ? '' : `<button type="button" class="nv" data-nivel="${esc(v)}" aria-pressed="${v === niv}" style="--cor:${COR_NIVEL[v] || 'var(--mut)'}"><i></i>${esc(rot)} <b>${q}</b></button>`;
    }).join('');
    const reduz = !!(window.CartaFX && CartaFX.reduz), antes = new Map();   // posições de antes, para as cartas deslizarem até o novo lugar
    if (!reduz && mesAnim === mes) document.querySelectorAll('#podio .slot[data-k], #album .slot[data-k]').forEach(el => antes.set(el.dataset.k, el.getBoundingClientRect()));
    const slot = (l, cls) => {
      const qAg = (/^\d+$/.test(l.x.k) ? 'id=' + l.x.k : 'nome=' + encodeURIComponent(l.x.a.nome)) + '&mes=' + encodeURIComponent(mes);
      return `<a class="slot ${cls || ''}" data-k="${esc(l.x.k)}" href="agente.html?${qAg}" title="Ver evolução de ${esc(l.x.a.nome)} · ${esc(mes)}"><span class="n${l.lugar <= 3 ? ' m' + l.lugar : ''}" aria-label="${l.lugar}º lugar">${l.lugar}º</span>${doAno ? Carta.html(l.x.a, l.ms, l.x.k, true).replace('1º mês', l.u.n + (l.u.n > 1 ? ' meses' : ' mês')) : Carta.html(l.x.a, l.ms, l.x.k)}${acoes(vis.indexOf(l))}</a>`;
    };
    // Pódio: só sem filtros (com filtro, o top 3 do mês pode nem estar na lista). No HTML a ordem é 1º, 2º, 3º; o CSS põe o 1º no meio.
    const pod = !eq && !bu && !niv && vis.length >= 3 ? vis.slice(0, 3) : [];
    $('podio').hidden = !pod.length;
    $('podio').innerHTML = pod.map((l, i) => slot(l, 'p' + (i + 1))).join('');
    [['p1', '650ms'], ['p2', '200ms'], ['p3', '0ms']].forEach(([c, t]) => $('podio').querySelectorAll('.slot.' + c + ' .carta').forEach(el => el.style.setProperty('--atraso', t)));
    $('album').innerHTML = vis.slice(pod.length).map(l => slot(l)).join('');
    if (antes.size) document.querySelectorAll('#podio .slot[data-k], #album .slot[data-k]').forEach(el => {
      const o = antes.get(el.dataset.k); if (!o || !el.animate) return;
      const c = el.querySelector('.carta'); if (c) { c.setAttribute('data-visto', '1'); const b = c.querySelector('.c-ovr b'); if (b) b.setAttribute('data-contou', '1'); }   // quem já estava na tela não entra de novo
      const r = el.getBoundingClientRect(), dx = o.left - r.left, dy = o.top - r.top;
      if (Math.abs(dx) + Math.abs(dy) > 2) el.animate({ translate: [dx + 'px ' + dy + 'px', '0px 0px'] }, { duration: 420, easing: 'cubic-bezier(.2,.8,.2,1)' });
    });
    if (!reduz && pod.length && mesAnim !== mes && window.CartaFX) {   // confete no pódio, uma vez por mês neste aparelho
      let jaViu = false, chave = 'sentinela:confete:' + mes;
      try { jaViu = !!localStorage.getItem(chave); if (!jaViu) localStorage.setItem(chave, '1'); } catch (e) { jaViu = confeteVisto.has(mes); }
      confeteVisto.add(mes);
      if (!jaViu) setTimeout(() => { const p = $('podio'); if (p && !p.hidden) CartaFX.confete(p, 70); }, 900);
    }
    mesAnim = mes;
    $('resumo').textContent = vis.length ? (doAno ? `${vis.length} cartinha(s) de ${lista.length}: média de todos os meses (só quem tem ${MIN_MESES_ANO} meses ou mais).` : `${vis.length} cartinha(s) de ${lista.length} em ${mes}.`) : 'Nenhuma cartinha com esses filtros.';
  };
  ['fMes', 'fEq', 'fNivel'].forEach(i => $(i).onchange = desenhar); $('fBusca').oninput = desenhar;
  $('bLimpar').onclick = () => { $('fEq').value = ''; $('fNivel').value = ''; $('fBusca').value = ''; desenhar(); };

  // ---- Baixar todas: um .zip com a imagem de cada cartinha que está na tela, numa pasta por equipe, na ordem do ranking ----
  let zipCancelado = false;
  const semAcento = t => String(t).normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const seguro = t => semAcento(t).replace(/[^A-Za-z0-9 ._-]+/g, '').trim() || 'sem-equipe';
  $('bZip').onclick = async () => {
    const itens = visAtual.slice(), n = itens.length, anon = document.body.classList.contains('modo-apresentacao'), btn = $('bZip');
    if (!n) return;
    if (n > 40 && !confirm(`Gerar ${n} imagens pode levar alguns minutos (principalmente no celular). Continuar?`)) return;
    const msg = $('msgImg'); clearTimeout(aviso.t); zipCancelado = false; btn.disabled = true;
    const mostra = (t, cancelar) => { msg.hidden = false; msg.innerHTML = esc(t) + (cancelar ? ' <button type="button" class="bt-limpar" id="bCancelaZip">Cancelar</button>' : ''); const c = $('bCancelaZip'); if (c) c.onclick = () => { zipCancelado = true; }; };
    const arquivos = [], falhas = [];
    try {
      for (let i = 0; i < n; i++) {
        if (zipCancelado) { mostra('Geração cancelada.'); return; }
        mostra(`Gerando imagens: ${i + 1} de ${n}…`, true);
        const l = itens[i];
        try {
          const bl = await Carta.png(l.x.a, l.ms, { id: l.x.k, ocultarNomes: anon, ocultarFoto: anon || document.body.classList.contains('sem-foto'), rapido: i > 0 });
          const nome = String(l.lugar).padStart(2, '0') + '-' + (anon ? 'agente-' + l.lugar : Carta.nomeArquivo(l.x.a, l.ms).replace(/\.png$/, '')) + '.png';
          arquivos.push({ nome: seguro(l.x.a.equipe || '') + '/' + nome, dados: bl });
        } catch (e) { falhas.push(l.x.a.nome); }
        await new Promise(r => setTimeout(r, 0));   // devolve o controle ao navegador (a tela não congela)
      }
      if (!arquivos.length) { mostra('Não consegui gerar as imagens aqui. Abra a página pelo endereço do site (não pelo arquivo no computador) e tente de novo.'); return; }
      mostra('Montando o arquivo .zip…');
      const zip = await ZipSimples.criar(arquivos);
      const f = [$('fMes').value, $('fEq').value].filter(Boolean).map(seguro).join('-').replace(/\s+/g, '-').toLowerCase();
      const a = document.createElement('a'); a.href = URL.createObjectURL(zip); a.download = `cartinhas-${f || 'todas'}.zip`; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 60000);
      mostra(`Pronto: ${arquivos.length} imagens no .zip (pastas por equipe)${falhas.length ? '. Não consegui gerar: ' + falhas.join(', ') : ''}.`);
    } catch (e) { mostra('Não consegui montar o .zip. Tente de novo.'); } finally { btn.disabled = !visAtual.length; }
  };
  $('niveis').onclick = e => { const b = e.target.closest('.nv'); if (!b) return; $('fNivel').value = b.dataset.nivel; desenhar(); };
  desenhar();
}
document.addEventListener('sentinela:tema', () => {});
