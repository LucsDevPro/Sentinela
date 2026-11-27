/* Exportar tabelas para planilha .xls (Excel/LibreOffice) — sem biblioteca externa.
   Formato «Planilha XML 2003»: o Excel abre direto, uma aba por tabela, números como número.
   Fonte única: este arquivo. O gerador (generate_dashboard.py) embute este código no bootstrap das páginas geradas,
   e resumo.html o carrega por <script>. Só exporta as linhas VISÍVEIS (respeita filtros de equipe/agente/semana). */
(function (g) {
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function texto(c) { return (c.innerText !== undefined ? c.innerText : c.textContent).replace(/\s+/g, ' ').trim(); }
  function numero(t) {   // «1.234,5» / «85,2» / «12» → número; «007», datas, horas e «85%» ficam texto
    if (/^-?(0|[1-9]\d{0,2}(\.\d{3})+|[1-9]\d*)(,\d+)?$/.test(t) || /^-?0,\d+$/.test(t)) return parseFloat(t.replace(/\./g, '').replace(',', '.'));
    return null;
  }
  function celula(t) {
    var n = numero(t);
    return n === null ? '<Cell><Data ss:Type="String">' + esc(t) + '</Data></Cell>' : '<Cell><Data ss:Type="Number">' + n + '</Data></Cell>';
  }
  function nomeAba(t, usados, i) {
    var n = (t || '').replace(/\s*\(\d+\)\s*$/, '').replace(/[\\\/?*\[\]:]/g, ' ').replace(/[^\x20-\x7EÀ-ÿ]/g, '').replace(/\s+/g, ' ').trim().slice(0, 28) || ('Tabela ' + i);
    var base = n, k = 2; while (usados[n.toLowerCase()]) n = base.slice(0, 26) + ' ' + k++;
    usados[n.toLowerCase()] = 1; return n;
  }
  function titulo(tab) {   // texto do h3/h4/caption mais próximo antes da tabela
    var cap = tab.querySelector('caption'); if (cap) return texto(cap);
    var el = tab.closest('.table-wrap') || tab;
    for (var p = el; p && p !== document.body; p = p.parentElement) {
      for (var s = p.previousElementSibling; s; s = s.previousElementSibling) {
        if (/^H[2-4]$/.test(s.tagName)) return texto(s);
        var h = s.querySelector && s.querySelector('h2,h3,h4'); if (h) return texto(h);
      }
      var hh = p.querySelector && p.querySelector(':scope > h2, :scope > h3, :scope > h4, :scope > summary'); if (hh) return texto(hh);
    }
    return '';
  }
  function linhas(tab) {
    var out = [];
    tab.querySelectorAll('thead tr').forEach(function (tr) { out.push([].map.call(tr.cells, texto)); });
    if (out.length > 1) out = [out[out.length - 1]];   // cabeçalho em várias linhas: fica a última (a das colunas)
    tab.querySelectorAll('tbody tr, tfoot tr').forEach(function (tr) {
      if (tr.style.display === 'none' || tr.hidden || tr.offsetParent === null && getComputedStyle(tr).display === 'none') return;
      out.push([].map.call(tr.cells, texto));
    });
    return out;
  }
  /** abas: [{nome, linhas:[[cabeçalho...],[linha...]]}]; arquivo: nome base do .xls (sem data) */
  g.exportarAbas = function (abasDef, arquivo) {
    var usados = {}, abas = [];
    abasDef.forEach(function (ab, i) {
      var ls = ab.linhas; if (!ls || !ls.length) return;
      var nome = nomeAba(ab.nome, usados, i + 1);
      var cab = '<Row ss:StyleID="h">' + ls[0].map(function (t) { return '<Cell><Data ss:Type="String">' + esc(t) + '</Data></Cell>'; }).join('') + '</Row>';
      var corpo = ls.slice(1).map(function (r) { return '<Row>' + r.map(function (v) { return typeof v === 'number' ? '<Cell><Data ss:Type="Number">' + v + '</Data></Cell>' : celula(String(v)); }).join('') + '</Row>'; }).join('');
      abas.push('<Worksheet ss:Name="' + esc(nome) + '"><Table>' + cab + corpo + '</Table><WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel"><FreezePanes/><FrozenNoSplit/><SplitHorizontal>1</SplitHorizontal><TopRowBottomPane>1</TopRowBottomPane></WorksheetOptions></Worksheet>');
    });
    if (!abas.length) { alert('Não há linhas para exportar.'); return; }
    var xml = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?>' +
      '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">' +
      '<Styles><Style ss:ID="h"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1F3A5F" ss:Pattern="Solid"/><Alignment ss:Vertical="Center" ss:WrapText="1"/></Style></Styles>' + abas.join('') + '</Workbook>';
    var d = new Date(), pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var nome = (arquivo || 'planilha').replace(/\s*\(\d+\)\s*$/, '').replace(/[^\w\-À-ÿ ]+/g, '').trim().replace(/\s+/g, '_') + '_' + d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + '.xls';
    var blob = new Blob(['\ufeff' + xml], { type: 'application/vnd.ms-excel;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = nome; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
  };
  /** tabelas: lista de <table>; arquivo: nome base do .xls; titulos: opcional, nomes das abas */
  g.exportarPlanilha = function (tabelas, arquivo, titulos) {
    var defs = [];
    [].forEach.call(tabelas, function (tab, i) { defs.push({ nome: (titulos && titulos[i]) || titulo(tab), linhas: linhas(tab) }); });
    g.exportarAbas(defs, arquivo);
  };
})(window);
