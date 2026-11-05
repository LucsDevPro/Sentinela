
let opcoes = [{ arquivo: "data/Analise_Consolidada.xlsx", label: "Acumulado (todas as semanas)", valor: "acumulado" }];

function carregarManifest() {
  const txt = document.getElementById('importBox').value.trim();
  opcoes = [{ arquivo: "data/Analise_Consolidada.xlsx", label: "Acumulado (todas as semanas)", valor: "acumulado" }];
  if (txt) {
    try {
      const entries = JSON.parse(txt);
      if (!Array.isArray(entries)) throw new Error('não é uma lista');
      entries.forEach(e => {
        if (e && e.arquivo && e.label && e.tipo !== 'semana') {
          opcoes.push({ arquivo: `data/historico/${e.arquivo}`, label: e.label, valor: e.arquivo });
        }
      });
      mostrarToast(`${entries.length} período(s) carregado(s) do histórico.`);
    } catch (e) {
      mostrarToast('JSON inválido — confira se copiou o manifest.json certo.');
      return;
    }
  }
  const sel = document.getElementById('selPeriodo');
  sel.innerHTML = opcoes.map(o =>
    `<option value="${o.valor}">${o.valor === 'acumulado' ? '📊 ' : '📅 '}${o.label}</option>`
  ).join('');
  atualizarSaida();
}

function atualizarSaida() {
  const valor = document.getElementById('selPeriodo').value;
  const escolhida = opcoes.find(o => o.valor === valor) || opcoes[0];
  const config = { arquivo: escolhida.arquivo, label: escolhida.label };
  document.getElementById('outputBox').value = JSON.stringify(config, null, 2);
  document.getElementById('preview').innerHTML =
    `A home vai mostrar: <b>${escolhida.label}</b><br>Arquivo: <code>${escolhida.arquivo}</code>`;
}

function copiarJson() {
  const box = document.getElementById('outputBox');
  box.select();
  navigator.clipboard.writeText(box.value).then(() => {
    mostrarToast('JSON copiado! Agora é só colar em data/config_home.json no GitHub.');
  }).catch(() => {
    document.execCommand('copy');
    mostrarToast('JSON copiado! Agora é só colar em data/config_home.json no GitHub.');
  });
}

function mostrarToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2800);
}

atualizarSaida();
