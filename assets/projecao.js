
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
  var sems={};ag.forEach(function(a){a.semanas.filter(function(s){return s.mes===mesAtual;}).forEach(function(s){var k=s.n;sems[k]=sems[k]||{n:s.n,parcial:!!s.parcial,por:{}};sems[k].parcial=sems[k].parcial||!!s.parcial;var e=sems[k].por[a.equipe]=sems[k].por[a.equipe]||{s:0,c:0};e.s+=s.pontos;e.c++;});});
  var sl=Object.keys(sems).map(function(k){return sems[k];}).sort(function(p,q){return p.n-q.n;});
  if(sl.length){
    var eqs={};sl.forEach(function(s){Object.keys(s.por).forEach(function(e){eqs[e]=1;});});var eql=Object.keys(eqs).sort();
    slide('semanas','Equipes semana a semana',mesAtual+' · média da nota; semana parcial em tom mais claro',function(el){
      new Chart(canvasEm(el),{type:'bar',data:{labels:sl.map(function(s){return 'Semana '+s.n+(s.parcial?' (parcial)':'');}),
        datasets:eql.map(function(e,i){var c=PAL[i%PAL.length];return {label:e,backgroundColor:function(x){return sl[x.dataIndex].parcial?c+'88':c;},borderRadius:5,
          data:sl.map(function(s){var p=s.por[e];return p?Math.round(p.s/p.c*10)/10:null;})};})},
        options:opcoes({plugins:{legend:{display:true,position:'bottom',labels:{color:cor('--text2'),font:{size:18}}}},scales:eixos({grid:{display:false},ticks:{color:cor('--text'),font:{size:18}}},{min:0,max:105})}),plugins:[plugValores]});
    });
  }
}
if(listaMeses.length>1) slide('media','Média por mês','nota média de todos os agentes',function(el){
  var vals=listaMeses.map(function(m){var s=0,c=0;ag.forEach(function(a){var v=nota(a,m);if(v!==null){s+=v;c++;}});return c?Math.round(s/c*10)/10:null;});
  new Chart(canvasEm(el),{type:'line',data:{labels:listaMeses,datasets:[{data:vals,borderColor:PAL[0],backgroundColor:PAL[0],tension:.25,pointRadius:6,borderWidth:4}]},
    options:opcoes({scales:eixos({ticks:{color:cor('--text'),font:{size:18}},grid:{display:false}},{min:0,max:105})}),plugins:[{id:'v2',afterDatasetsDraw:function(ch){plugValores.afterDatasetsDraw(ch);}}]});
});
if(!slides.length) slide('vazio','Sem dados ainda','',function(el){el.insertAdjacentHTML('beforeend','<p class="vazio">Ainda não há notas para mostrar.<br>Assim que o painel for atualizado, as telas aparecem aqui.</p>');});

/* ---- palco ---- */
var palco=document.getElementById('palco'),dots=document.getElementById('dots'),barra=document.getElementById('barra');
var atual=-1,pausado=false,seg=15,t0=0,raf=null;
slides.forEach(function(s,i){var b=document.createElement('button');b.type='button';b.setAttribute('aria-label','Tela '+(i+1)+': '+s.titulo);b.onclick=function(){ir(i);};dots.appendChild(b);});
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
  if(!pausado&&slides.length>1){var p=(t-t0)/(seg*1000);barra.style.width=Math.min(100,p*100)+'%';if(p>=1)avanca();}
  raf=requestAnimationFrame(tick);
}
function pausa(v){pausado=v;var b=document.getElementById('bPausa');b.querySelector('span').textContent=v?'Continuar':'Pausar';b.querySelector('use').setAttribute('href',v?'#i-play':'#i-pause');if(!v)t0=performance.now()-(parseFloat(barra.style.width)||0)/100*seg*1000;}
document.getElementById('bPausa').onclick=function(){pausa(!pausado);};
document.getElementById('vel').onchange=function(){seg=parseInt(this.value,10);t0=performance.now();};
function nomes(){mostrarNomes=!mostrarNomes;document.querySelector('#bNomes span').textContent='Nomes: '+(mostrarNomes?'visíveis':'ocultos');desenhar();}
document.getElementById('bNomes').onclick=nomes;
function tela(){if(document.fullscreenElement)document.exitFullscreen();else if(document.documentElement.requestFullscreen)document.documentElement.requestFullscreen();}
document.getElementById('bTela').onclick=tela;
document.addEventListener('keydown',function(e){
  if(e.target&&/SELECT|INPUT/.test(e.target.tagName))return;
  if(e.key==='ArrowRight')avanca();else if(e.key==='ArrowLeft')volta();else if(e.key===' '){e.preventDefault();pausa(!pausado);}
  else if(e.key==='f'||e.key==='F')tela();else if(e.key==='n'||e.key==='N')nomes();
});
document.addEventListener('sentinela:tema',function(){if(window.aplicarTemaGraficos)window.aplicarTemaGraficos();desenhar();});
window.PROJECAO={ir:ir,pausa:pausa,total:slides.length,ids:slides.map(function(s){return s.id;}),atual:function(){return atual;},pausado:function(){return pausado;}};
if(window.aplicarTemaGraficos)window.aplicarTemaGraficos();
ir(0);raf=requestAnimationFrame(tick);
})();
