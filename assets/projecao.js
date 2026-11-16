
(function(){
'use strict';
var MESES=['janeiro','fevereiro','março','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
var PAL=['#1E9AD8','#F7B500','#19B8A3','#FF5143','#7C5CD6','#5B6FA8'];
var D=(window.AGENTES_DADOS&&window.AGENTES_DADOS.agentes)||{};
var ag=Object.keys(D).map(function(k){var a=D[k];return {k:k,nome:a.nome,equipe:a.equipe||'—',meses:a.meses||[],semanas:a.semanas||[]};});
function ordMes(l){var p=String(l).toLowerCase().split('/');var i=MESES.indexOf(p[0]);if(i>2)i--;return (parseInt(p[1],10)||0)*20+i;}
var contagem={};ag.forEach(function(a){a.meses.forEach(function(m){contagem[m.mes]=(contagem[m.mes]||0)+1;});});
var listaMeses=Object.keys(contagem).sort(function(a,b){return ordMes(a)-ordMes(b);});
var mesAtual=listaMeses[listaMeses.length-1], mesAnt=listaMeses[listaMeses.length-2];
function nota(a,mes){var m=a.meses.filter(function(x){return x.mes===mes;})[0];return m?m.pontos:null;}
var mostrarNomes=false;
function nome(a,i){return mostrarNomes?a.nome:('Agente '+(i+1));}
function br(v,d){return Number(v).toLocaleString('pt-BR',{minimumFractionDigits:d||0,maximumFractionDigits:d||0});}
var charts=[];
function cor(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function opcoes(extra){var t=cor('--text2');var o={responsive:true,maintainAspectRatio:false,animation:{duration:400},color:t,
  plugins:{legend:{display:false,labels:{color:t,font:{size:16}}}},scales:{}};
  for(var k in extra){o[k]=extra[k];}return o;}
function eixos(x,y){return {x:Object.assign({ticks:{color:cor('--text2'),font:{size:16}},grid:{color:cor('--grid')}},x||{}),y:Object.assign({ticks:{color:cor('--text2'),font:{size:16}},grid:{color:cor('--grid')}},y||{})};}
var plugValores={id:'val',afterDatasetsDraw:function(ch){var c=ch.ctx;c.save();c.font='700 18px "IBM Plex Sans",sans-serif';c.fillStyle=cor('--text');c.textBaseline='middle';
  var h=ch.options.indexAxis==='y';
  ch.data.datasets.forEach(function(ds,i){ch.getDatasetMeta(i).data.forEach(function(b,j){var v=ds.data[j];if(v==null)return;var t=br(v,1);
    if(h){c.textAlign='left';c.fillText(t,b.x+8,b.y);}else{c.textAlign='center';c.textBaseline='bottom';c.fillText(t,b.x,b.y-4);}});});c.restore();}};

/* ---- as telas ---- */
var slides=[];
function slide(id,titulo,sub,montar){slides.push({id:id,titulo:titulo,sub:sub,montar:montar});}
function cartao(v,l){return '<div class="card"><div class="v">'+v+'</div><div class="l">'+l+'</div></div>';}
function canvasEm(el){var g=document.createElement('div');g.className='graf';var c=document.createElement('canvas');g.appendChild(c);el.appendChild(g);return c;}

if(mesAtual){
  var doMes=ag.map(function(a){return {a:a,v:nota(a,mesAtual)};}).filter(function(x){return x.v!==null;}).sort(function(p,q){return q.v-p.v;});
  slide('resumo','Resumo de '+mesAtual,'',function(el){
    var soma=0;doMes.forEach(function(x){soma+=x.v;});
    var exc=doMes.filter(function(x){var m=x.a.meses.filter(function(z){return z.mes===mesAtual;})[0];return m&&/EXCELENTE/i.test(m.cls||'');}).length;
    var eq={};doMes.forEach(function(x){eq[x.a.equipe]=1;});
    el.insertAdjacentHTML('beforeend','<div class="cards">'+cartao(br(doMes.length),'agentes avaliados')+cartao(br(soma/doMes.length,1),'nota média')+cartao(br(doMes[0].v,1),'maior nota')+cartao(br(Math.round(exc*100/doMes.length))+'%','com classificação excelente')+cartao(br(Object.keys(eq).length),'equipes')+'</div>');
  });
  slide('top','Top 10 de '+mesAtual,'maiores notas do mês',function(el){
    var t=doMes.slice(0,10);
    new Chart(canvasEm(el),{type:'bar',data:{labels:t.map(function(x,i){return (i+1)+'º  '+nome(x.a,i)+'  ·  '+x.a.equipe;}),datasets:[{data:t.map(function(x){return x.v;}),backgroundColor:PAL[0],borderRadius:6}]},
      options:opcoes({indexAxis:'y',scales:eixos({min:0,max:105,ticks:{color:cor('--text2'),font:{size:16}}},{grid:{display:false},ticks:{color:cor('--text'),font:{size:18}}})}),plugins:[plugValores]});
  });
  if(mesAnt){
    var evo=ag.map(function(a){var n=nota(a,mesAtual),o=nota(a,mesAnt);return (n!==null&&o!==null)?{a:a,d:n-o}:null;}).filter(Boolean).sort(function(p,q){return q.d-p.d;}).slice(0,10);
    if(evo.length) slide('evol','Maior evolução','de '+mesAnt+' para '+mesAtual+' (pontos a mais)',function(el){
      new Chart(canvasEm(el),{type:'bar',data:{labels:evo.map(function(x,i){return nome(x.a,i)+'  ·  '+x.a.equipe;}),datasets:[{data:evo.map(function(x){return Math.round(x.d*10)/10;}),backgroundColor:PAL[2],borderRadius:6}]},
        options:opcoes({indexAxis:'y',scales:eixos({beginAtZero:true},{grid:{display:false},ticks:{color:cor('--text'),font:{size:18}}})}),plugins:[plugValores]});
    });
  }
  // Nota média por equipe no mês inteiro (a visão semana a semana saiu: cada semana recomeça de 100 e mostrava notas mais altas que as do mês)
  var porEq={};ag.forEach(function(a){var v=nota(a,mesAtual);if(v===null)return;var e=porEq[a.equipe]=porEq[a.equipe]||{s:0,c:0};e.s+=v;e.c++;});
  var eqNomes=Object.keys(porEq).sort();
  if(eqNomes.length) slide('equipes-mes','Nota média por equipe',mesAtual+' · mês completo, mesma nota das cartinhas',function(el){
    new Chart(canvasEm(el),{type:'bar',data:{labels:eqNomes,datasets:[{casas:1,data:eqNomes.map(function(e){return Math.round(porEq[e].s/porEq[e].c*10)/10;}),backgroundColor:eqNomes.map(function(e,i){return PAL[i%PAL.length];}),borderRadius:6}]},
      options:opcoes({layout:{padding:{top:24}},plugins:{legend:{display:false}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:20}}},{min:0,max:100})}),plugins:[plugValores]});
  });
}
if(listaMeses.length>1) slide('media','Média por mês','nota média de todos os agentes',function(el){
  var vals=listaMeses.map(function(m){var s=0,c=0;ag.forEach(function(a){var v=nota(a,m);if(v!==null){s+=v;c++;}});return c?Math.round(s/c*10)/10:null;});
  new Chart(canvasEm(el),{type:'line',data:{labels:listaMeses,datasets:[{data:vals,borderColor:PAL[0],backgroundColor:PAL[0],tension:.25,pointRadius:6,borderWidth:4}]},
    options:opcoes({scales:eixos({ticks:{color:cor('--text'),font:{size:18}},grid:{display:false}},{min:0,max:105})}),plugins:[{id:'v2',afterDatasetsDraw:function(ch){plugValores.afterDatasetsDraw(ch);}}]});
});
/* ---- panorama: totais de visitas, mês a mês e por equipe (dados de assets/agentes_dados.js → "panorama") ---- */
var PANO=(window.AGENTES_DADOS&&window.AGENTES_DADOS.panorama)||{};
var mesesPano=listaMeses.filter(function(m){return PANO[m];});
function notasDo(m){return ag.map(function(a){return nota(a,m);}).filter(function(v){return v!==null;});}
function mediaDo(m){var n=notasDo(m);return n.length?n.reduce(function(t,v){return t+v;},0)/n.length:null;}
function andamento(m){return m===mesAtual&&!(PANO[m]&&PANO[m].fechado);}   // só o mês mais recente ainda está rodando
function rotulo(m){return m+(andamento(m)?' (em andamento)':'');}
function plugInt(){return {id:'valInt',afterDatasetsDraw:function(ch){var c=ch.ctx;c.save();c.font='700 18px "IBM Plex Sans",sans-serif';c.fillStyle=cor('--text');var h=ch.options.indexAxis==='y';
  ch.data.datasets.forEach(function(ds,i){ch.getDatasetMeta(i).data.forEach(function(b,j){var v=ds.data[j];if(v==null)return;var t=br(v,ds.casas||0);
    if(h){c.textAlign='left';c.textBaseline='middle';c.fillText(t,b.x+8,b.y);}else{c.textAlign='center';c.textBaseline='bottom';c.fillText(t,b.x,b.y-4);}});});c.restore();}};}
function duas(el){var w=document.createElement('div');w.className='linha';el.appendChild(w);return w;}
function tabela(cab,linhas,total){return '<table class="tab"><thead><tr>'+cab.map(function(c,i){return '<th'+(i?' class="n"':'')+'>'+c+'</th>';}).join('')+'</tr></thead><tbody>'+
  linhas.map(function(l){return '<tr>'+l.map(function(c,i){return '<td'+(i?' class="n"':'')+'>'+c+'</td>';}).join('')+'</tr>';}).join('')+'</tbody>'+(total?'<tfoot><tr>'+total.map(function(c,i){return '<td'+(i?' class="n"':'')+'>'+c+'</td>';}).join('')+'</tr></tfoot>':'')+'</table>';}
if(mesesPano.length){
  slide('pano-total','Panorama geral','todos os meses: '+mesesPano[0]+' a '+mesesPano[mesesPano.length-1],function(el){
    var t={im:0,vi:0,di:0,n:0,s:0};mesesPano.forEach(function(m){var p=PANO[m];t.im+=p.imoveis;t.vi+=p.visitas;t.di+=p.dias;notasDo(m).forEach(function(v){t.n++;t.s+=v;});});
    el.insertAdjacentHTML('beforeend','<div class="cards fino">'+cartao(br(t.im),'imóveis trabalhados')+cartao(br(t.vi),'visitas (imóveis abertos)')+cartao(br(t.di),'dias de trabalho dos agentes')+cartao(t.n?br(t.s/t.n,1):'—','nota média de todos os meses')+'</div>');
    var ls=mesesPano.map(function(m){var p=PANO[m],md=mediaDo(m);return [rotulo(m),br(p.agentes),br(p.visitas),br(p.imoveis),br(p.vis_dia,1),md===null?'—':br(md,1)];});
    el.insertAdjacentHTML('beforeend','<div class="graf rolar">'+tabela(['Mês','Agentes','Visitas','Imóveis trabalhados','Visitas por dia','Nota média'],ls,['Total','',br(t.vi),br(t.im),t.di?br(t.vi/t.di,1):'—',t.n?br(t.s/t.n,1):'—'])+'</div>');
  });
  slide('pano-evolucao','Mês a mês','imóveis trabalhados e ritmo de visitas por dia de trabalho',function(el){
    var w=duas(el),lab=mesesPano.map(function(m){return m.split('/')[0]+(andamento(m)?' *':'');});
    new Chart(canvasEm(w),{type:'bar',data:{labels:lab,datasets:[{casas:0,data:mesesPano.map(function(m){return PANO[m].imoveis;}),backgroundColor:mesesPano.map(function(m){return andamento(m)?PAL[0]+'88':PAL[0];}),borderRadius:6}]},
      options:opcoes({plugins:{legend:{display:false},title:{display:true,text:'Imóveis trabalhados',color:cor('--text'),font:{size:20}}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:16}}},{beginAtZero:true,ticks:{color:cor('--text2'),font:{size:16},callback:function(v){return br(v);}}})}),plugins:[plugInt()]});
    new Chart(canvasEm(w),{type:'line',data:{labels:lab,datasets:[{casas:1,data:mesesPano.map(function(m){return PANO[m].vis_dia;}),borderColor:PAL[1],backgroundColor:PAL[1],tension:.25,pointRadius:6,borderWidth:4}]},
      options:opcoes({layout:{padding:{left:24,top:8,right:12}},plugins:{legend:{display:false},title:{display:true,text:'Visitas por dia de trabalho',color:cor('--text'),font:{size:20}}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:16}}},{beginAtZero:true,ticks:{color:cor('--text2'),font:{size:16},callback:function(v){return br(v);}}})}),plugins:[plugInt()]});
    if(mesesPano.some(andamento))el.insertAdjacentHTML('beforeend','<p class="nota">* mês em andamento: os números ainda crescem até o fechamento.</p>');
  });
  mesesPano.slice().reverse().forEach(function(m){
    var p=PANO[m];
    slide('pm-'+m+'-1','Panorama de '+m,andamento(m)?'mês em andamento':'mês completo',function(el){
      var md=mediaDo(m);
      el.insertAdjacentHTML('beforeend','<div class="cards oito">'+cartao(br(p.visitas),'visitas (imóveis abertos)')+cartao(br(p.imoveis),'imóveis trabalhados')+cartao(br(p.dias),'dias de trabalho')+cartao(br(p.vis_dia,1),'visitas por dia')+
        cartao(br(p.tempo_min,1)+' min','tempo médio por visita')+cartao(br(p.areas),'áreas visitadas')+cartao(br(p.agentes),'agentes avaliados')+cartao(md===null?'—':br(md,1),'nota média do mês')+'</div>');
      var al=p.alertas||{};
      el.insertAdjacentHTML('beforeend','<p class="nota">Imóveis fechados: '+br(p.fechados)+' · recusados: '+br(p.recusados)+' · visitas duplicadas: '+br(al.duplicadas||0)+' · em sequência suspeita: '+br(al.suspeitas||0)+' · fora do expediente: '+br(al.fora||0)+'</p>');
    });
    slide('pm-'+m+'-2','Equipes e níveis de '+m,'visitas por equipe e agentes por nível',function(el){
      var w=duas(el),eqs=Object.keys(p.equipes||{});
      new Chart(canvasEm(w),{type:'bar',data:{labels:eqs,datasets:[{casas:0,data:eqs.map(function(e){return p.equipes[e].visitas;}),backgroundColor:eqs.map(function(e,i){return PAL[i%PAL.length];}),borderRadius:6}]},
        options:opcoes({plugins:{legend:{display:false},title:{display:true,text:'Visitas por equipe',color:cor('--text'),font:{size:20}}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:18}}},{beginAtZero:true,ticks:{color:cor('--text2'),font:{size:16},callback:function(v){return br(v);}}})}),plugins:[plugInt()]});
      var N=[['OURO 90+',90,1000,'#F7B500'],['PRATA 80-89',80,90,'#9DB2D0'],['BRONZE 70-79',70,80,'#C98A4B'],['AÇO 60-69',60,70,'#6F8F8A'],['FERRO <60',-1,60,'#8A8F98']];
      var nv=notasDo(m).map(Math.round);
      new Chart(canvasEm(w),{type:'bar',data:{labels:N.map(function(x){return x[0];}),datasets:[{casas:0,data:N.map(function(x){return nv.filter(function(v){return v>=x[1]&&v<x[2];}).length;}),backgroundColor:N.map(function(x){return x[3];}),borderRadius:6}]},
        options:opcoes({plugins:{legend:{display:false},title:{display:true,text:'Agentes por nível',color:cor('--text'),font:{size:20}}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:15}}},{beginAtZero:true,ticks:{precision:0,color:cor('--text2'),font:{size:16}}})}),plugins:[plugInt()]});
    });
  });
  // ordem das telas: panorama geral e mês a mês primeiro, depois o mês atual de sempre, e por último o panorama de cada mês (do mais recente ao mais antigo)
  var ini=slides.filter(function(x){return x.id==='pano-total'||x.id==='pano-evolucao';}),fim=slides.filter(function(x){return /^pm-/.test(x.id);}),meio=slides.filter(function(x){return ini.indexOf(x)<0&&fim.indexOf(x)<0;});
  slides.length=0;ini.concat(meio,fim).forEach(function(x){slides.push(x);});
}
if(!slides.length) slide('vazio','Sem dados ainda','',function(el){el.insertAdjacentHTML('beforeend','<p class="vazio">Ainda não há notas para mostrar.<br>Assim que o painel for atualizado, as telas aparecem aqui.</p>');});

/* ---- palco ---- */
var palco=document.getElementById('palco'),dots=document.getElementById('dots'),barra=document.getElementById('barra');
var atual=-1,pausado=false,seg=15,t0=0,raf=null;
var slidesPaineis=slides.slice();   // as telas de gráficos de sempre; o modo «cartinhas» troca o conteúdo de `slides`
function montarDots(){dots.innerHTML='';slides.forEach(function(s,i){var b=document.createElement('button');b.type='button';b.setAttribute('aria-label','Tela '+(i+1)+': '+s.titulo);b.onclick=function(){ir(i);};dots.appendChild(b);});}
montarDots();

/* ---- modo cartinhas: uma cartinha por tela, em tamanho grande, na ordem do álbum (maior nota primeiro) ---- */
var modo='paineis', qtdCartas=10;   // 10 = só o top 10; 0 = todas
var mesCartas=(function(){var q=new URLSearchParams(location.search).get('mes');return (q&&listaMeses.indexOf(q)>=0)?q:mesAtual;})();
function esc(t){return String(t==null?'':t).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function listaCartas(mes){
  var L=[];
  ag.forEach(function(a){var ms=a.meses.slice().sort(function(p,q){return ordMes(p.mes)-ordMes(q.mes);});
    var i=ms.map(function(m){return m.mes;}).indexOf(mes);if(i<0||ms[i].pontos==null)return;
    var ant=ms.slice(0,i).map(function(m){return m.pontos;}).filter(function(n){return n!=null;});
    L.push({a:a,ms:ms.slice(0,i+1),u:ms[i],h:ant.length?ant.reduce(function(t,n){return t+n;},0)/ant.length:-1});});
  // mesma ordem do álbum: nota bruta, depois a média dos meses anteriores, depois a posição oficial
  L.sort(function(p,q){return Carta.bruta(q.u)-Carta.bruta(p.u)||q.h-p.h||(p.u.pos||0)-(q.u.pos||0)||p.a.nome.localeCompare(q.a.nome,'pt-BR');});
  return L;
}
function listaPts(titulo,itens,cls){
  if(!itens||!itens.length)return '';
  return '<div class="cp-bloco"><h3>'+titulo+'</h3><ul>'+itens.slice(0,3).map(function(x){return '<li><span>'+esc(x.c)+'</span><b class="'+cls+'">'+(x.p>0?'+':'')+br(x.p,1)+'</b></li>';}).join('')+'</ul></div>';
}
// «Nomes: ocultos»: o texto é trocado (não só borrado) por «Agente N» e pelo número, e a foto sai
function anonCarta(raiz,i,u){
  var carta=raiz.querySelector('.carta');
  if(mostrarNomes||!carta)return;
  var cn=carta.querySelector('.c-nome');if(cn)cn.textContent='Agente '+(i+1);
  var ini=carta.querySelector('.c-foto .nome');if(ini)ini.textContent=String(i+1);
  var im=carta.querySelector('.c-foto img');if(im)im.remove();
  carta.setAttribute('aria-label','Cartinha do Agente '+(i+1)+': nota '+br(u.pontos,1));
}
/* ---- modo pacote (tecla P): só quem fez 100, revelado de trás pra frente até o 1º lugar (assets/pacote.js) ---- */
var pacoteCtl=null;
function slidesDoPacote(){
  if(!window.Carta||!window.Pacote||!mesCartas)return [];
  var L=listaCartas(mesCartas);if(!L.length)return [];
  var c100=[];L.forEach(function(l,i){if(Math.round(l.u.pontos)>=100)c100.push({l:l,i:i});});
  if(c100.length<3)c100=L.slice(0,3).map(function(l,i){return {l:l,i:i};});   // com menos de 3 notas 100, o pódio (top 3) aparece mesmo assim
  var itens=c100.map(function(x){var l=x.l,i=x.i;return {rank:i+1,rot:mostrarNomes?l.a.nome:('Agente '+(i+1)),eq:l.a.equipe,nota:br(l.u.pontos,1),
    mk:function(){return Carta.html({nome:l.a.nome,equipe:l.a.equipe},l.ms,l.a.k,true);},
    prep:function(raiz){anonCarta(raiz,i,l.u);}};});
  var fazVideo=window.CartaVideo&&CartaVideo.suportado()?function(it){var l=c100.filter(function(x){return x.i+1===it.rank;})[0].l;return CartaVideo.enviar(l.a,l.ms,{lugar:it.rank,id:l.a.k,ocultarNomes:!mostrarNomes,ocultarFoto:!mostrarNomes});}:null;
  return [{id:'pacote',titulo:'Pacote de cartinhas',sub:mesCartas,manual:true,montar:function(el){pacoteCtl=Pacote.iniciar(el,itens,{mes:mesCartas,video:fazVideo});}}];
}
function slidesDasCartas(){
  var out=[];
  if(!window.Carta||!mesCartas)return out;
  var L=listaCartas(mesCartas),N=L.length,lim=qtdCartas>0?Math.min(qtdCartas,N):N;
  if(!N)return out;
  out.push({id:'cartas-intro',titulo:'Cartinhas de '+mesCartas,sub:'',montar:function(el){
    el.insertAdjacentHTML('beforeend','<div class="cards">'+cartao(br(N),'cartinhas no mês')+cartao(lim<N?('Top '+lim):'Todas','que vão passar, da maior nota para a menor')+'</div><p class="nota">Setas ← → mudam de cartinha · N mostra ou oculta nomes e fotos · barra de espaço pausa.</p>');}});
  L.slice(0,lim).forEach(function(l,i){
    out.push({id:'carta-'+(i+1),titulo:'Cartinhas de '+mesCartas,sub:(i+1)+'º de '+N,montar:function(el){
      var u=l.u,rot=mostrarNomes?l.a.nome:('Agente '+(i+1));
      el.insertAdjacentHTML('beforeend','<div class="cartela"><div class="cslot" id="cslot">'+Carta.html({nome:l.a.nome,equipe:l.a.equipe},l.ms,l.a.k,true)+'</div>'+
        '<div class="cpainel"><div class="cp-nome">'+esc(rot)+'</div><div class="cp-eq">'+esc(l.a.equipe)+' · '+(i+1)+'º de '+N+'</div>'+
        '<div class="cp-nota"><b>'+br(u.pontos,1)+'</b><span>nota do mês</span></div>'+listaPts('O que mais deu pontos',u.ganhos,'pos')+listaPts('O que mais tirou pontos',u.perdas,'neg')+'</div></div>');
      var carta=el.querySelector('.carta');anonCarta(el,i,u);
      ajustarCarta(el);
      if(window.CartaFX&&carta)CartaFX.revelar(carta);   // o pacote vira e a cartinha aparece
    }});
  });
  return out;
}
// a cartinha ocupa a altura que sobra na tela (escala --e, a mesma conta do álbum: caixa de 272×392 px)
function ajustarCarta(el){
  var slot=el.querySelector('.cslot');if(!slot)return;
  var h=el.querySelector('h2'),disp=el.clientHeight-(h?h.offsetHeight:0)-24,larg=el.clientWidth*0.46;
  var e=Math.max(.5,Math.min(2.1,(disp-60)/392,(larg-60)/272));
  slot.style.setProperty('--e',e.toFixed(3));
}
function trocarModo(m){
  modo=m;slides.length=0;
  (m==='cartas'?slidesDasCartas():m==='pacote'?slidesDoPacote():[]).forEach(function(x){slides.push(x);});
  if(!slides.length){modo='paineis';slidesPaineis.forEach(function(x){slides.push(x);});}
  document.getElementById('bModo').querySelector('span').textContent=modo!=='paineis'?'Painéis':'Cartinhas';
  document.getElementById('qtd').hidden=modo!=='cartas';
  var sm=document.getElementById('mesApres');sm.hidden=modo==='paineis';
  if(!sm.options.length){listaMeses.slice().reverse().forEach(function(m){var o=document.createElement('option');o.value=m;o.textContent=m;sm.appendChild(o);});}
  sm.value=mesCartas;
  document.body.classList.toggle('modo-cartas',modo==='cartas');document.body.classList.toggle('modo-pacote',modo==='pacote');
  if(history.replaceState)history.replaceState(null,'',location.pathname+location.search+(modo==='cartas'?'#cartinhas':modo==='pacote'?'#pacote':''));
  montarDots();if(window.PROJECAO)window.PROJECAO.total=slides.length;
  ir(0);
}
function desenhar(){
  charts.forEach(function(c){c.destroy();});charts=[];
  var s=slides[atual];palco.innerHTML='';
  var el=document.createElement('section');el.className='slide on';
  el.innerHTML='<h2>'+s.titulo+(s.sub?'<small>'+s.sub+'</small>':'')+'</h2>';palco.appendChild(el);
  s.montar(el);
  Object.keys(Chart.instances||{}).forEach(function(k){charts.push(Chart.instances[k]);});
  Array.prototype.forEach.call(dots.children,function(d,i){d.classList.toggle('on',i===atual);});
  if(window.animarNumeros)window.animarNumeros(el);
}
function ir(i){atual=(i+slides.length)%slides.length;t0=performance.now();desenhar();}
function volta(){ir(atual-1);} function avanca(){ir(atual+1);}
function tick(t){
  if(!pausado&&slides.length>1&&!(slides[atual]&&slides[atual].manual)){var p=(t-t0)/(seg*1000);barra.style.width=Math.min(100,p*100)+'%';if(p>=1)avanca();}
  raf=requestAnimationFrame(tick);
}
function pausa(v){pausado=v;var b=document.getElementById('bPausa');b.querySelector('span').textContent=v?'Continuar':'Pausar';b.querySelector('use').setAttribute('href',v?'#i-play':'#i-pause');if(!v)t0=performance.now()-(parseFloat(barra.style.width)||0)/100*seg*1000;}
document.getElementById('bPausa').onclick=function(){pausa(!pausado);};
document.getElementById('vel').onchange=function(){seg=parseInt(this.value,10);t0=performance.now();};
function nomes(){mostrarNomes=!mostrarNomes;document.querySelector('#bNomes span').textContent='Nomes: '+(mostrarNomes?'visíveis':'ocultos');desenhar();}
document.getElementById('bNomes').onclick=nomes;
document.getElementById('bModo').onclick=function(){trocarModo(modo==='paineis'?'cartas':'paineis');};
document.getElementById('mesApres').onchange=function(){mesCartas=this.value;var u=new URLSearchParams(location.search);u.set('mes',mesCartas);if(history.replaceState)history.replaceState(null,'','?'+u.toString()+location.hash);if(modo!=='paineis')trocarModo(modo);};
document.getElementById('bPacote').onclick=function(){trocarModo(modo==='pacote'?'paineis':'pacote');};
document.getElementById('qtd').onchange=function(){qtdCartas=parseInt(this.value,10);if(modo==='cartas')trocarModo('cartas');};
window.addEventListener('resize',function(){var el=palco.querySelector('.slide');if(el&&modo==='cartas')ajustarCarta(el);});
function tela(){if(document.fullscreenElement)document.exitFullscreen();else if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen();}
document.getElementById('bTela').onclick=tela;
document.addEventListener('keydown',function(e){
  if(e.target&&/SELECT|INPUT/.test(e.target.tagName))return;
  if(modo==='pacote'&&pacoteCtl){   // no pacote a tela não passa sozinha: cada tecla abre/revela a próxima
    if(e.key==='ArrowRight'||e.key==='ArrowDown'||e.key==='PageDown'||e.key==='Enter'||e.key===' '||e.key==='.'){e.preventDefault();pacoteCtl.passo();return;}   // inclui as teclas dos controles remotos de apresentação
    if(e.key==='ArrowLeft'||e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();return;}
    if(e.key==='s'||e.key==='S'){pacoteCtl.alternarSom();return;}
    if(e.key==='a'||e.key==='A'){pacoteCtl.alternarAuto();return;}
    if(e.key==='ArrowLeft')return;
    if((e.key==='r'||e.key==='R')&&!pacoteCtl.ocupado()){ir(0);return;}
    if(e.key==='p'||e.key==='P'){trocarModo('paineis');return;}
  }
  if(e.key==='p'||e.key==='P'){trocarModo('pacote');return;}
  if(e.key==='ArrowRight')avanca();else if(e.key==='ArrowLeft')volta();else if(e.key===' '){e.preventDefault();pausa(!pausado);}
  else if(e.key==='f'||e.key==='F')tela();else if(e.key==='n'||e.key==='N')nomes();else if(e.key==='c'||e.key==='C')trocarModo(modo==='paineis'?'cartas':'paineis');
});
document.addEventListener('sentinela:tema',function(){if(window.aplicarTemaGraficos)window.aplicarTemaGraficos();desenhar();});
window.PROJECAO={modo:function(){return modo;},trocarModo:trocarModo,ir:ir,pausa:pausa,total:slides.length,ids:slides.map(function(s){return s.id;}),atual:function(){return atual;},pausado:function(){return pausado;}};
if(window.aplicarTemaGraficos)window.aplicarTemaGraficos();
if(location.hash==='#pacote')trocarModo('pacote');else if(location.hash==='#cartinhas')trocarModo('cartas');else ir(0);
raf=requestAnimationFrame(tick);
})();
