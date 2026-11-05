
// Lista de agentes (ID + equipe) — mesma configuração do coletor.
const AGENTES_POR_EQUIPE = {
  "Equipe 1":        [116, 73, 1935, 470, 672, 3037, 79, 85, 30, 3101],
  "Equipe 2":        [115, 125, 3035, 3127, 2030, 134, 99, 142, 465, 81, 151, 2917],
  "Equipe 3":        [113, 2951, 120, 1938, 2721, 3128, 3038, 2918, 1936],
  "Equipe 4":        [80, 124, 161, 1943, 2789, 1996, 157, 110, 149, 86, 1942],
  "Equipe Bloqueio": [162, 1088, 1934, 109, 155, 126, 476, 122, 2101],
};

let registros = []; // {alvo, id_agente?, equipe?, motivo, inicio: "dd/mm/aaaa", fim: "dd/mm/aaaa"}
let NOMES_AGENTES = {}; // id_agente (string) -> {nome, equipe}, vem de data/agentes_nomes.json (opcional)

function rotuloAgente(id, equipeFallback) {
  const info = NOMES_AGENTES[String(id)];
  return info ? `${info.nome} — ${info.equipe}` : `ID ${id} — ${equipeFallback}`;
}

function carregarNomes() {
  const txt = document.getElementById('nomesBox').value.trim();
  if (!txt) { NOMES_AGENTES = {}; mostrarToast('Nenhum nome carregado — o menu vai mostrar os IDs.'); }
  else {
    try {
      const dados = JSON.parse(txt);
      NOMES_AGENTES = dados;
      mostrarToast(`${Object.keys(dados).length} nome(s) carregado(s).`);
    } catch (e) {
      mostrarToast('JSON inválido — confira se copiou o arquivo certo.');
      return;
    }
  }
  popularSelectAgentes();
  renderizar();
}

function popularSelectAgentes() {
  const sel = document.getElementById('selAgente');
  if (!sel) return;
  sel.innerHTML = '';
  for (const [equipe, ids] of Object.entries(AGENTES_POR_EQUIPE)) {
    const og = document.createElement('optgroup');
    og.label = equipe;
    ids.forEach(id => {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = rotuloAgente(id, equipe);
      og.appendChild(opt);
    });
    sel.appendChild(og);
  }
}

function popularSelectEquipes() {
  return Object.keys(AGENTES_POR_EQUIPE).map(eq => `<option value="${eq}">${eq}</option>`).join('');
}

function onAlvoChange() {
  const alvo = document.getElementById('selAlvo').value;
  const wrap = document.getElementById('alvoDetalheWrap');
  if (alvo === 'agente') {
    wrap.innerHTML = `<label for="selAgente">Agente</label><select id="selAgente"></select>`;
    popularSelectAgentes();
  } else if (alvo === 'equipe') {
    wrap.innerHTML = `<label for="selEquipe">Equipe</label><select id="selEquipe">${popularSelectEquipes()}</select>`;
  } else {
    wrap.innerHTML = `<label>&nbsp;</label><input type="text" value="Todos os agentes" disabled>`;
  }
}

function isoParaBr(iso) {
  if (!iso) return '';
  const [a, m, d] = iso.split('-');
  return `${d}/${m}/${a}`;
}
function brParaIso(br) {
  const [d, m, a] = br.split('/');
  return `${a}-${m}-${d}`;
}

document.addEventListener('DOMContentLoaded', () => {
  const sm = document.getElementById('selMotivo');
  sm.addEventListener('change', () => { document.getElementById('turnoWrap').style.display = sm.value.startsWith('Meia ') ? '' : 'none'; });
});

function adicionar() {
  const alvo = document.getElementById('selAlvo').value;
  const motivo = document.getElementById('selMotivo').value;
  const inicioIso = document.getElementById('dataInicio').value;
  const fimIso = document.getElementById('dataFim').value;
  if (!inicioIso || !fimIso) { mostrarToast('Preencha os dois dias (entrada e saída).'); return; }
  if (fimIso < inicioIso) { mostrarToast('O dia de saída não pode ser antes do dia de entrada.'); return; }

  const registro = { alvo, motivo, inicio: isoParaBr(inicioIso), fim: isoParaBr(fimIso) };
  if (motivo.startsWith('Meia ')) registro.turno = document.getElementById('selTurno').value;
  if (alvo === 'agente') {
    const sel = document.getElementById('selAgente');
    if (!sel || !sel.value) { mostrarToast('Escolha um agente.'); return; }
    registro.id_agente = parseInt(sel.value, 10);
  } else if (alvo === 'equipe') {
    const sel = document.getElementById('selEquipe');
    if (!sel || !sel.value) { mostrarToast('Escolha uma equipe.'); return; }
    registro.equipe = sel.value;
  }

  registros.push(registro);
  renderizar();
  document.getElementById('dataInicio').value = '';
  document.getElementById('dataFim').value = '';
  mostrarToast('Adicionado à lista — não esqueça de copiar o JSON no passo 4.');
}

function remover(i) {
  registros.splice(i, 1);
  renderizar();
}

function badgeClass(motivo) {
  const m = motivo.toLowerCase();
  if (m.includes('féria') || m.includes('feria')) return 'badge-ferias';
  if (m.includes('folga')) return 'badge-folga';
  if (m.includes('atestado') || m.includes('justificada')) return 'badge-atestado';
  if (m.includes('chuva')) return 'badge-chuva';
  if (m.includes('reunião') || m.includes('reuniao') || m.includes('treinamento')) return 'badge-reuniao';
  if (m.includes('índice') || m.includes('indice') || m.includes('ovitrampa') || m.includes('recuperação') || m.includes('recuperacao')) return 'badge-atividade';
  return 'badge-folga';
}

function quemFmt(r) {
  if (r.alvo === 'todos') return 'Todos os agentes';
  if (r.alvo === 'equipe') return r.equipe;
  const info = NOMES_AGENTES[String(r.id_agente)];
  return info ? info.nome : `Agente ID ${r.id_agente}`;
}

function renderizar() {
  const tbody = document.getElementById('tbody');
  if (registros.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Nenhum registro adicionado ainda.</td></tr>';
  } else {
    tbody.innerHTML = registros.map((r, i) => `
      <tr>
        <td>${quemFmt(r)}</td>
        <td><span class="badge ${badgeClass(r.motivo)}">${r.motivo}${r.turno ? ' (' + r.turno.toLowerCase() + ')' : ''}</span></td>
        <td>${r.inicio}</td>
        <td>${r.fim}</td>
        <td><button class="btn-danger-mini" onclick="remover(${i})" title="Remover">🗑️</button></td>
      </tr>`).join('');
  }
  document.getElementById('outputBox').value = JSON.stringify(registros, null, 2);
}

function importarJson() {
  const txt = document.getElementById('importBox').value.trim();
  if (!txt) { registros = []; renderizar(); return; }
  try {
    const dados = JSON.parse(txt);
    if (!Array.isArray(dados)) throw new Error('não é uma lista');
    registros = dados.filter(r => r && r.alvo && r.motivo && r.inicio && r.fim);
    renderizar();
    mostrarToast(`${registros.length} registro(s) carregado(s).`);
  } catch (e) {
    mostrarToast('JSON inválido — confira se copiou o arquivo certo.');
  }
}

function copiarJson() {
  const box = document.getElementById('outputBox');
  box.select();
  navigator.clipboard.writeText(box.value).then(() => {
    mostrarToast('JSON copiado! Agora é só colar no GitHub.');
  }).catch(() => {
    document.execCommand('copy');
    mostrarToast('JSON copiado! Agora é só colar no GitHub.');
  });
}

function mostrarToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2800);
}

popularSelectAgentes();
renderizar();
