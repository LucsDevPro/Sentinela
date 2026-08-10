Chart.defaults.color = '#6B7A8F';
Chart.defaults.borderColor = '#E7ECF3';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";

function classColor(cls) {
  return cls.includes('CRÍTICO') ? '#E4572E' : cls.includes('ATENÇÃO') ? '#F2B01E' : '#12B76A';
}

// Gráficos de barra horizontal com 1 barra por agente precisam de altura
// proporcional à quantidade de agentes, senão as barras ficam espremidas
// e sobrepostas. Chama isso ANTES de criar o Chart.
function sizeForAgents(canvasId, count) {
  const el = document.getElementById(canvasId);
  if (el) el.parentElement.style.height = Math.max(260, count * 15 + 30) + 'px';
}

new Chart(document.getElementById('chartClass'), {
  type: 'doughnut',
  data: { labels: ['🟢 Normal', '🟡 Atenção', '🔴 Crítico'],
    datasets: [{ data: {{ chart_data.class_counts | tojson }}, backgroundColor: ['#12B76A', '#F2B01E', '#E4572E'], borderWidth: 0 }] },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
});

new Chart(document.getElementById('chartTeam'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      { label: 'Imóveis Abertos', data: {{ chart_data.team_abertos | tojson }}, backgroundColor: '#1080D6', borderRadius: 6 },
      { label: 'Visitas Rápidas', data: {{ chart_data.team_rapidas | tojson }}, backgroundColor: '#E4572E', borderRadius: 6 }
    ] },
  options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true }, x: { grid: { display: false } } }, plugins: { legend: { position: 'bottom' } } }
});

(function(){
  const d = {{ chart_data.agents_pct | tojson }}.slice().sort((a,b) => b.v - a.v);
  sizeForAgents('chartPct', d.length);
  new Chart(document.getElementById('chartPct'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [{ label: '% Rápidas', data: d.map(a => a.v), backgroundColor: d.map(a => classColor(a.cls)), borderRadius: 4, barThickness: 12 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 9 } } } },
      plugins: { legend: { display: false } } }
  });
})();

new Chart(document.getElementById('chartTeamStack'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      { label: 'Normal', data: {{ chart_data.team_stack.normal | tojson }}, backgroundColor: '#12B76A', borderRadius: 4 },
      { label: 'Atenção', data: {{ chart_data.team_stack.atencao | tojson }}, backgroundColor: '#F2B01E', borderRadius: 4 },
      { label: 'Crítico', data: {{ chart_data.team_stack.critico | tojson }}, backgroundColor: '#E4572E', borderRadius: 4 }
    ] },
  options: { responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, ticks: { stepSize: 2 } } },
    plugins: { legend: { position: 'bottom' } } }
});

new Chart(document.getElementById('chartTeamStatus'), {
  type: 'bar',
  data: { labels: {{ chart_data.teams | tojson }},
    datasets: [
      { label: 'Abertos', data: {{ chart_data.team_status.abertos | tojson }}, backgroundColor: '#1080D6', borderRadius: 4 },
      { label: 'Fechados', data: {{ chart_data.team_status.fechados | tojson }}, backgroundColor: '#F2994A', borderRadius: 4 },
      { label: 'Recusados', data: {{ chart_data.team_status.recusados | tojson }}, backgroundColor: '#E4572E', borderRadius: 4 }
    ] },
  options: { responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true } },
    plugins: { legend: { position: 'bottom' } } }
});

(function(){
  const d = {{ chart_data.custo_data | tojson }}.slice().sort((a,b) => b.v - a.v);
  sizeForAgents('chartCusto', d.length);
  new Chart(document.getElementById('chartCusto'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [{ label: 'Custo Hora Útil (R$)', data: d.map(a => a.v),
        backgroundColor: d.map(a => a.v > 150 ? '#E4572E' : a.v > 100 ? '#F2B01E' : '#12B76A'), borderRadius: 4, barThickness: 12 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 9 } } } },
      plugins: { legend: { display: false } } }
  });
})();

(function(){
  const d = {{ chart_data.horas_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHoras', d.length);
  new Chart(document.getElementById('chartHoras'), {
    type: 'bar',
    data: { labels: d.map(a => a.label),
      datasets: [{ label: 'Horas Úteis/Dia', data: d.map(a => a.v),
        backgroundColor: d.map(a => a.v < 1.5 ? '#E4572E' : a.v < 2.5 ? '#F2B01E' : '#12B76A'), borderRadius: 4, barThickness: 9 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 8 } } } },
      plugins: { legend: { display: false } } }
  });
})();

(function(){
  const d = {{ chart_data.horas_trab_dia_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHorasTrabDia', d.length);
  new Chart(document.getElementById('chartHorasTrabDia'), {
    type: 'bar',
    data: { labels: d.map(a => a.label), datasets: [{ label: 'Horas Trabalhadas/Dia', data: d.map(a => a.v), backgroundColor: '#6B62D6', borderRadius: 4, barThickness: 9 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 8 } } } },
      plugins: { legend: { display: false } } }
  });
})();

(function(){
  const d = {{ chart_data.horas_trab_semana_data | tojson }}.slice().sort((a,b) => a.v - b.v);
  sizeForAgents('chartHorasTrabSemana', d.length);
  new Chart(document.getElementById('chartHorasTrabSemana'), {
    type: 'bar',
    data: { labels: d.map(a => a.label), datasets: [{ label: 'Horas Trabalhadas/Semana', data: d.map(a => a.v), backgroundColor: '#29AEE0', borderRadius: 4, barThickness: 9 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 8 } } } },
      plugins: { legend: { display: false } } }
  });
})();

{% if chart_data.pend_top15 %}
new Chart(document.getElementById('chartPendTop'), {
  type: 'bar',
  data: { labels: {{ chart_data.pend_top15 | map(attribute="label") | list | tojson }},
    datasets: [{ label: '% Pendência', data: {{ chart_data.pend_top15 | map(attribute="pct") | list | tojson }},
      backgroundColor: {{ chart_data.pend_top15 | map(attribute="pct") | list | tojson }}.map(p => p > 40 ? '#E4572E' : p > 25 ? '#F2B01E' : '#12B76A'),
      borderRadius: 4, barThickness: 16 }] },
  options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    scales: { x: { beginAtZero: true }, y: { grid: { display: false } } },
    plugins: { legend: { display: false } } }
});
{% endif %}

{% if chart_data.ranking_chart %}
(function(){
  const d = {{ chart_data.ranking_chart | tojson }};
  sizeForAgents('chartRanking', d.length);
  new Chart(document.getElementById('chartRanking'), {
    type: 'bar',
    data: { labels: d.map(x => x.label),
      datasets: [{ label: 'Pontuação Final', data: d.map(x => x.v),
        backgroundColor: d.map(x => x.color), borderRadius: 4, barThickness: 12 }] },
    options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 9 } } } },
      plugins: { legend: { display: false } } }
  });
})();
{% endif %}

{% if chart_data.pe_trend %}
(function(){
  const peTrend = {{ chart_data.pe_trend | tojson }};
  new Chart(document.getElementById('chartPeTrend'), {
    data: { labels: peTrend.map(p => 'Semana ' + p.semana),
      datasets: [
        { type: 'bar', label: 'Imóveis Abertos', data: peTrend.map(p => p.abertos), backgroundColor: '#29AEE0', borderRadius: 4, yAxisID: 'y' },
        { type: 'line', label: 'Visitas/Dia', data: peTrend.map(p => p.visitas_dia), borderColor: '#E4572E', backgroundColor: '#E4572E', tension: 0.3, yAxisID: 'y1' }
      ] },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, position: 'left', title: { display: true, text: 'Imóveis Abertos' } },
                y1: { beginAtZero: true, position: 'right', grid: { display: false }, title: { display: true, text: 'Visitas/Dia' } } },
      plugins: { legend: { position: 'bottom' } } }
  });
})();
{% endif %}

{% if ausencias_agg.top15 %}
new Chart(document.getElementById('chartAusTop'), {
  type: 'bar',
  data: { labels: {{ ausencias_agg.top15 | map(attribute=0) | list | tojson }},
    datasets: [{ label: 'Ausências', data: {{ ausencias_agg.top15 | map(attribute=1) | list | tojson }}, backgroundColor: '#E4572E', borderRadius: 4, barThickness: 14 }] },
  options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    scales: { x: { beginAtZero: true }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } },
    plugins: { legend: { display: false } } }
});
{% endif %}
