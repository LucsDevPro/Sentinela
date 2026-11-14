/* Gráficos do dashboard. Cores, tooltip, grade, legenda e os plugins `valores` e `centro` vêm de assets/tema.js (window.SENT_GRAF):
   aqui só se diz o PAPEL de cada série (serie1/serie2/serie3/neutro) ou o estado de cada barra (bom/atencao/critico). */
const G = window.SENT_GRAF;
if (window.aplicarTemaGraficos) window.aplicarTemaGraficos();

function papelClasse(cls) { return cls.includes('CRÍTICO') ? 'critico' : cls.includes('ATENÇÃO') ? 'atencao' : 'bom'; }
// `respiro: true` = 2 px da cor do fundo entre segmentos. A borda precisa existir JÁ na criação: o Chart.js não anima de "indefinido" para uma cor.
function respiro(ds) { return ds.respiro ? Object.assign({ borderColor: G.superficie(), borderWidth: 2 }, ds) : ds; }
function serie(papel, extra) { return respiro(Object.assign({ papel: papel, backgroundColor: G.cor(papel) }, extra || {})); }
function porEstado(papeis, extra) { return respiro(Object.assign({ papeis: papeis, backgroundColor: papeis.map(G.cor) }, extra || {})); }

// Gráficos de barra horizontal com 1 barra por agente precisam de altura
// proporcional à quantidade de agentes, senão as barras ficam espremidas
// e sobrepostas. Chama isso ANTES de criar o Chart.
function sizeForAgents(canvasId, count) {
  const el = document.getElementById(canvasId);
  if (el) el.parentElement.style.height = Math.max(260, count * 17 + 34) + 'px';
}
// Barra horizontal por agente: nome à esquerda, valor na ponta, sem legenda (o título do cartão já diz o que é)
function opcoesAgentes(extra) {
  const o = { indexAxis: 'y', responsive: true, maintainAspectRatio: false, layout: { padding: { right: 64 } },
    scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } },
    plugins: { legend: { display: false }, valores: { ativo: true, posicao: 'ponta', tamanho: 10 } } };
  return Object.assign(o, extra || {});
}

(function () {   // Distribuição por classificação: rosca fina com o total de agentes no centro
  const c = {{ chart_data.class_counts | tojson }};
  new Chart(document.getElementById('chartClass'), {
    type: 'doughnut',
    data: { labels: ['Normal', 'Atenção', 'Crítico'],
      datasets: [porEstado(['bom', 'atencao', 'critico'], { data: c, respiro: true, hoverOffset: 4 })] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '68%',
      plugins: { legend: { position: 'bottom' }, centro: { valor: c.reduce((a, b) => a + b, 0), rotulo: 'agentes' } } }
  });
})();

new Chart(document.getElementById('chartTeam'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      serie('serie1', { label: 'Imóveis abertos', data: {{ chart_data.team_abertos | tojson }} }),
      serie('serie2', { label: 'Visitas rápidas', data: {{ chart_data.team_rapidas | tojson }} })
    ] },
  options: { responsive: true, maintainAspectRatio: false, layout: { padding: { top: 20 } },
    scales: { y: { beginAtZero: true } },
    plugins: { legend: { position: 'bottom' }, valores: { ativo: true, posicao: 'ponta' } } }
});

(function(){
  const d = {{ chart_data.agents_pct | tojson }}.slice().sort((a,b) => b.v - a.v);
  sizeForAgents('chartPct', d.length);
  new Chart(document.getElementById('chartPct'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [porEstado(d.map(a => papelClasse(a.cls)), { label: '% de visitas rápidas', data: d.map(a => a.v), sufixo: '%', casas: 1 })] },
    options: opcoesAgentes()
  });
})();

{% if comparacao_semanal %}
(function () {   // Nota média por equipe no MÊS INTEIRO (a visão semana a semana saiu: cada semana parte de 100 e escondia as perdas acumuladas)
  const C = {{ comparacao_semanal | tojson }};
  const eqs = Object.keys(C.equipes), valores = eqs.map(eq => C.equipes[eq][C.equipes[eq].length - 1]);
  new Chart(document.getElementById('chartTeamSemanal'), {
    type: 'bar',
    data: { labels: eqs, datasets: [serie('serie1', { label: 'Nota média do mês', data: valores, casas: 1 })] },
    options: { responsive: true, maintainAspectRatio: false, layout: { padding: { top: 26 } },
      scales: { y: { min: 0, max: 100 } },
      plugins: { legend: { display: false }, valores: { ativo: true, posicao: 'ponta', tamanho: 13 } } }
  });
})();
{% endif %}

new Chart(document.getElementById('chartTeamStack'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      serie('bom', { label: 'Normal', data: {{ chart_data.team_stack.normal | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false }),
      serie('atencao', { label: 'Atenção', data: {{ chart_data.team_stack.atencao | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false }),
      serie('critico', { label: 'Crítico', data: {{ chart_data.team_stack.critico | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false })
    ] },
  options: { responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
    plugins: { legend: { position: 'bottom' }, valores: { ativo: true, posicao: 'dentro', omitirZero: true } } }
});

new Chart(document.getElementById('chartTeamStatus'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      serie('serie1', { label: 'Abertos', data: {{ chart_data.team_status.abertos | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false }),
      serie('neutro', { label: 'Fechados', data: {{ chart_data.team_status.fechados | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false }),
      serie('serie2', { label: 'Recusados', data: {{ chart_data.team_status.recusados | tojson }}, respiro: true, borderRadius: 0, borderSkipped: false })
    ] },
  options: { responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } },
    plugins: { legend: { position: 'bottom' }, valores: { ativo: true, posicao: 'dentro', omitirZero: true } } }
});

(function(){
  const d = {{ chart_data.custo_data | tojson }}.slice().sort((a,b) => b.v - a.v);
  sizeForAgents('chartCusto', d.length);
  new Chart(document.getElementById('chartCusto'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [porEstado(d.map(a => a.v > {{ custo_faixa_alto }} ? 'critico' : a.v > {{ custo_faixa_medio }} ? 'atencao' : 'bom'),
        { label: 'Custo real da hora útil', data: d.map(a => a.v), prefixo: 'R$ ', casas: 2 })] },
    options: opcoesAgentes({ layout: { padding: { right: 84 } },
      scales: { x: { beginAtZero: true, max: {{ custo_grafico_max }} }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } } })
  });
})();

(function(){
  const d = {{ chart_data.horas_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHoras', d.length);
  new Chart(document.getElementById('chartHoras'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [porEstado(d.map(a => a.v < {{ horas_uteis_baixo }} ? 'critico' : a.v < {{ horas_uteis_alto }} ? 'atencao' : 'bom'),
        { label: 'Horas úteis por dia', data: d.map(a => a.v), sufixo: ' h', casas: 1 })] },
    options: opcoesAgentes()
  });
})();

(function(){
  const d = {{ chart_data.horas_trab_dia_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHorasTrabDia', d.length);
  new Chart(document.getElementById('chartHorasTrabDia'), {
    type: 'bar',
    data: { labels: d.map(a => a.label), datasets: [serie('serie1', { label: 'Horas trabalhadas por dia', data: d.map(a => a.v), sufixo: ' h', casas: 1 })] },
    options: opcoesAgentes()
  });
})();

(function(){
  const d = {{ chart_data.horas_trab_semana_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHorasTrabSemana', d.length);
  new Chart(document.getElementById('chartHorasTrabSemana'), {
    type: 'bar',
    data: { labels: d.map(a => a.label), datasets: [serie('serie1', { label: 'Horas trabalhadas por semana', data: d.map(a => a.v), sufixo: ' h', casas: 1 })] },
    options: opcoesAgentes()
  });
})();

{% if chart_data.pend_top15 %}
(function(){
  const p = {{ chart_data.pend_top15 | map(attribute="pct") | list | tojson }};
  new Chart(document.getElementById('chartPendTop'), {
    type: 'bar',
    data: { labels: {{ chart_data.pend_top15 | map(attribute="label") | list | tojson }},
      datasets: [porEstado(p.map(v => v > 40 ? 'critico' : v > 25 ? 'atencao' : 'bom'), { label: '% de pendência', data: p, sufixo: '%', casas: 1 })] },
    options: opcoesAgentes({ scales: { x: { beginAtZero: true }, y: { grid: { display: false } } } })
  });
})();
{% endif %}

{% if chart_data.ranking_chart and not acumulado_so_media %}
(function(){
  const d = {{ chart_data.ranking_chart | tojson }};
  sizeForAgents('chartRanking', d.length);
  new Chart(document.getElementById('chartRanking'), {
    type: 'bar',
    data: { labels: d.map(x => x.label),
      datasets: [{ label: 'Pontuação final', data: d.map(x => x.v), backgroundColor: d.map(x => x.color), casas: 1 }] },
    options: opcoesAgentes()
  });
})();
{% endif %}

{% if chart_data.pe_trend %}
(function(){
  const peTrend = {{ chart_data.pe_trend | tojson }};
  new Chart(document.getElementById('chartPeTrend'), {
    data: { labels: peTrend.map(p => 'Semana ' + p.semana),
      datasets: [
        serie('serie1', { type: 'bar', label: 'Imóveis abertos', data: peTrend.map(p => p.abertos), yAxisID: 'y', order: 2 }),
        serie('serie2', { type: 'line', label: 'Visitas por dia', data: peTrend.map(p => p.visitas_dia), casas: 1, yAxisID: 'y1', order: 1, pointBorderColor: G.superficie() })
      ] },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      scales: { y: { beginAtZero: true, position: 'left', title: { display: true, text: 'Imóveis abertos' } },
                y1: { beginAtZero: true, position: 'right', grid: { display: false }, title: { display: true, text: 'Visitas por dia' } } },
      plugins: { legend: { position: 'bottom' } } }
  });
})();
{% endif %}

{% if ausencias_agg.top15 %}
new Chart(document.getElementById('chartAusTop'), {
  type: 'bar',
  data: { labels: {{ ausencias_agg.top15 | map(attribute=0) | list | tojson }},
    datasets: [serie('serie1', { label: 'Ausências', data: {{ ausencias_agg.top15 | map(attribute=1) | list | tojson }} })] },
  options: opcoesAgentes({ scales: { x: { beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } })
});
{% endif %}

if (window.aplicarTemaGraficos) window.aplicarTemaGraficos();
