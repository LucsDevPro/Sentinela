
const CATEGORIAS_PARALISACAO_COLETIVA = ["Chuva", "Capacitação", "Reunião/atividade coletiva", "Outra atividade coletiva"];

let registros = []; // conteúdo bruto de deteccoes_pendentes.json
let registrosOriginais = []; // snapshot do que foi importado no passo 2 — usado só pro resumo/preview do passo 4
let NOMES_AGENTES = {}; // id_agente (string) -> {nome, equipe}
let filtroAtual = 'todos';

function carregarNomes() {
  const txt = document.getElementById('nomesBox').value.trim();
  if (!txt) { NOMES_AGENTES = {}; mostrarToast('Nenhum nome carregado — a lista vai mostrar os IDs.'); }
  else {
    try {
      NOMES_AGENTES = JSON.parse(txt);
      mostrarToast(`${Object.keys(NOMES_AGENTES).length} nome(s) carregado(s).`);
    } catch (e) {
      mostrarToast('JSON inválido — confira se copiou o arquivo certo.');
      return;
    }
  }
  renderizar();
}

function nomeAgente(id) {
  const info = NOMES_AGENTES[String(id)];
  return info ? info.nome : `Agente ID ${id}`;
}

function quemFmt(r) {
  if (r.tipo === 'possiveis_ferias') return r.nome_agente || nomeAgente(r.id_agente);
  const nomes = r.nomes_envolvidos || [];
  return nomes.length ? nomes.join(', ') : `${(r.agentes_envolvidos || []).length} agente(s)`;
}

function importarJson() {
  const txt = document.getElementById('importBox').value.trim();
  if (!txt) { registros = []; registrosOriginais = []; renderizar(); return; }
  try {
    const dados = JSON.parse(txt);
    if (!Array.isArray(dados)) throw new Error('não é uma lista');
    registros = dados;
    registrosOriginais = JSON.parse(JSON.stringify(dados)); // snapshot pro resumo do passo 4
    renderizar();
    mostrarToast(`${registros.length} detecção(ões) carregada(s).`);
  } catch (e) {
    mostrarToast('JSON inválido — confira se copiou o arquivo certo.');
  }
}

function mudarFiltro(f) {
  filtroAtual = f;
  ['Todos','Revisao','Sobreposicao','Ferias','Chuva'].forEach(k => {
    document.getElementById('tab' + k).classList.toggle('active', k.toLowerCase() === f || (f === 'todos' && k === 'Todos'));
  });
  renderizar();
}

function passaNoFiltro(r) {
  if (filtroAtual === 'todos') return true;
  if (filtroAtual === 'revisao') return !!r.revisao_necessaria;
  if (filtroAtual === 'sobreposicao') return !!r.revisao_classificacao_necessaria;
  if (filtroAtual === 'ferias') return r.tipo === 'possiveis_ferias';
  if (filtroAtual === 'chuva') return r.tipo === 'paralisacao_coletiva';
  return true;
}

function statusCelula(r, idx) {
  if (r.status === 'falta' || r.status === 'rejeitada') {
    return `<span class="badge badge-falta">Marcado como falta</span>
            <div><button class="btn-mini btn-confirmar" onclick="marcarConfirmada(${idx})">Desfazer (voltar a confirmar)</button></div>`;
  }
  if (r.tipo === 'possiveis_ferias') {
    return `<span class="badge badge-ferias">✅ Confirmado — Férias</span>
            <div><button class="btn-mini btn-falta" onclick="marcarFalta(${idx})">Marcar falta</button></div>`;
  }
  // paralisacao_coletiva
  const catual = r.categoria_coletiva || 'Chuva';
  const opts = CATEGORIAS_PARALISACAO_COLETIVA.map(c =>
    `<option value="${c}" ${c === catual ? 'selected' : ''}>${c}</option>`).join('');
  return `<span class="badge badge-chuva">✅ Confirmado</span>
          <div>
            <select class="motivo-select" onchange="mudarCategoria(${idx}, this.value)">${opts}</select>
            <button class="btn-mini btn-falta" onclick="marcarFalta(${idx})">Marcar falta</button>
          </div>`;
}

function marcarFalta(idx) {
  registros[idx].status = 'falta';
  registros[idx].corrigido_manualmente = true;
  renderizar();
  mostrarToast('Marcado como falta — não esqueça de copiar o JSON no passo 4.');
}

function marcarConfirmada(idx) {
  registros[idx].status = 'confirmada';
  renderizar();
  mostrarToast('Voltou a ficar confirmado.');
}

function mudarCategoria(idx, valor) {
  registros[idx].categoria_coletiva = valor;
  registros[idx].corrigido_manualmente = true;
  renderizar();
  mostrarToast('Motivo atualizado — não esqueça de copiar o JSON no passo 4.');
}

function renderizar() {
  const tbody = document.getElementById('tbody');
  const visiveis = registros.map((r, i) => ({ r, i })).filter(({ r }) => passaNoFiltro(r));

  const nFerias = registros.filter(r => r.tipo === 'possiveis_ferias').length;
  const nSobreposicao = registros.filter(r => r.revisao_classificacao_necessaria).length;
  document.getElementById('cTodos').textContent = registros.length;
  document.getElementById('cRevisao').textContent = registros.filter(r => r.revisao_necessaria).length;
  document.getElementById('cSobreposicao').textContent = nSobreposicao;
  document.getElementById('cFerias').textContent = nFerias;
  document.getElementById('cChuva').textContent = registros.filter(r => r.tipo === 'paralisacao_coletiva').length;

  const avisoEl = document.getElementById('avisoSobreposicao');
  if (avisoEl) {
    // Só mostra o aviso quando uma FRAÇÃO grande das férias está marcada
    // (equipes pequenas, com várias pessoas de férias no mesmo mês, geram
    // isso naturalmente e em volume — não é sinal de bug, é o esperado).
    if (nFerias >= 4 && nSobreposicao / nFerias >= 0.3) {
      avisoEl.style.display = 'block';
      avisoEl.innerHTML = `💡 <b>${nSobreposicao} de ${nFerias}</b> férias estão marcadas como "sobrepõe outro agente" — isso é `
        + `normal em equipes pequenas quando várias pessoas tiram férias no mesmo período. Não precisa revisar tudo às pressas: `
        + `cada uma já está confirmada e contando normalmente na pontuação; a marcação é só um convite pra você conferir com calma `
        + `se algum desses casos era, na real, uma paralisação coletiva.`;
    } else {
      avisoEl.style.display = 'none';
    }
  }

  if (visiveis.length === 0) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Nenhum registro nessa aba.</td></tr>';
  } else {
    tbody.innerHTML = visiveis.map(({ r, i }) => `
      <tr>
        <td>
          ${r.tipo === 'possiveis_ferias' ? '🌴' : '🌧️'} ${quemFmt(r)}
          ${r.revisao_necessaria ? `<div><span class="badge badge-revisao">⚠️ Padrão sumiu</span></div>
             <div class="nota-revisao">${r.nota_revisao || ''}</div>` : ''}
          ${r.revisao_classificacao_necessaria ? `<div><span class="badge badge-sobreposicao">🔎 Sobrepõe outro agente</span></div>
             <div class="nota-revisao">${r.nota_revisao_classificacao || ''}</div>` : ''}
        </td>
        <td>${r.equipe || '—'}</td>
        <td>${r.inicio} a ${r.fim}</td>
        <td colspan="2">${statusCelula(r, i)}</td>
      </tr>`).join('');
  }
  document.getElementById('outputBox').value = JSON.stringify(registros, null, 2);
  atualizarResumo();
}

function chaveRegistro(r) {
  const quem = r.tipo === 'possiveis_ferias' ? r.id_agente : r.equipe;
  return `${r.tipo}|${quem}|${r.inicio}|${r.fim}`;
}

function calcularDiff() {
  const origPorChave = new Map(registrosOriginais.map(r => [chaveRegistro(r), r]));
  let corrigidos = 0, novos = 0, inalterados = 0;
  registros.forEach(r => {
    const orig = origPorChave.get(chaveRegistro(r));
    if (!orig) { novos++; return; }
    if (orig.status !== r.status || orig.categoria_coletiva !== r.categoria_coletiva) corrigidos++;
    else inalterados++;
  });
  const curChaves = new Set(registros.map(chaveRegistro));
  const removidos = registrosOriginais.filter(r => !curChaves.has(chaveRegistro(r))).length;
  return { corrigidos, novos, removidos, inalterados };
}

function atualizarResumo() {
  const el = document.getElementById('resumoMudancas');
  if (!el) return;
  const { corrigidos, novos, removidos, inalterados } = calcularDiff();
  if (corrigidos === 0 && novos === 0 && removidos === 0) {
    el.innerHTML = registrosOriginais.length
      ? '<span class="resumo-ok">✅ Nada foi corrigido em relação ao que foi importado no passo 2 — tudo continua como a detecção automática decidiu.</span>'
      : '<span class="resumo-info">Nada importado ainda — carregue o JSON no passo 2 primeiro.</span>';
    return;
  }
  const partes = [];
  if (corrigidos) partes.push(`<span class="resumo-corrigido">✏️ ${corrigidos} corrigido(s) manualmente</span>`);
  if (novos) partes.push(`<span class="resumo-add">+${novos} novo(s)</span>`);
  if (removidos) partes.push(`<span class="resumo-rem">−${removidos} removido(s)</span>`);
  if (inalterados) partes.push(`<span class="resumo-inalt">${inalterados} sem alteração</span>`);
  el.innerHTML = '📝 Mudanças em relação ao que foi importado: ' + partes.join(' · ');
}

function copiarJson() {
  const { corrigidos, novos, removidos } = calcularDiff();
  if (corrigidos + novos + removidos > 0) {
    const msg = `Confirma copiar?\n\n✏️ ${corrigidos} corrigido(s) manualmente\n+${novos} novo(s)\n−${removidos} removido(s)\n\n`
              + `Isso vai SUBSTITUIR o arquivo inteiro no GitHub quando você colar — confira se está certo antes de continuar.`;
    if (!window.confirm(msg)) { mostrarToast('Cópia cancelada.'); return; }
  }
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

renderizar();
