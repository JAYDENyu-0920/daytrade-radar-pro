(()=>{
'use strict';
const $=id=>document.getElementById(id),n=x=>Number(x)||0,fmt=x=>n(x).toLocaleString('zh-TW',{maximumFractionDigits:2}),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let stocks=[],timer=null,busy=false;
window.show=page=>['radar','live','settings','detail'].forEach(x=>$(x).hidden=x!==page);
const score=s=>Math.max(0,Math.min(100,Math.round(Math.min(40,n(s.volume)/1500)+Math.min(35,n(s.range)*5)+Math.min(25,Math.abs(n(s.change))*4))));
function render(){
 const sort=$('sort').value,min=n($('minvol').value);
 const list=stocks.filter(s=>s.close>=40&&s.close<=100&&s.volume>=min&&(!$('exclude').checked||!s.id.startsWith('0')));
 list.sort((a,b)=>sort==='volume'?b.volume-a.volume:sort==='change'?b.change-a.change:score(b)-score(a));
 $('stocks').innerHTML=list.length?list.slice(0,40).map(s=>`<div class="card stock" data-id="${esc(s.id)}"><div class="row"><b>${esc(s.id)} ${esc(s.name)}</b><span class="green">${score(s)} 分</span></div><p>收盤 ${fmt(s.close)} · ${esc(s.market)} · ${s.change>=0?'+':''}${fmt(s.change)}%</p><small>成交 ${fmt(s.volume)} 張 · 振幅 ${fmt(s.range)}%</small></div>`).join(''):'<div class="card">無符合條件股票</div>';
 document.querySelectorAll('.stock').forEach(e=>e.onclick=()=>detail(e.dataset.id));
}
function tick(v){return v<10?.01:v<50?.05:v<100?.1:v<500?.5:v<1000?1:5}
function detail(id){
 const s=stocks.find(x=>x.id===id);if(!s)return;
 const entry=Math.round((s.high+tick(s.high))/tick(s.high))*tick(s.high),stop=s.low,risk=entry-stop,target=entry+2*risk,lots=risk>0?Math.floor(n($('risk').value)/(risk*1000)):0;
 $('detailbody').innerHTML=`<h2>${esc(s.id)} ${esc(s.name)}</h2><div class="card"><p>收盤 ${fmt(s.close)} · 評分 ${score(s)}</p><p>開 ${fmt(s.open)} 高 ${fmt(s.high)} 低 ${fmt(s.low)}</p><p>突破觀察 ${fmt(entry)} / 停損 ${fmt(stop)} / 2R ${fmt(target)}</p><p>風險預算 ${lots} 張（未計費稅與滑價）</p><small>盤後歷史行情推算，非盤中交易訊號。</small></div>`;
 show('detail');
}
async function load(){
 const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),15000);
 try{
 const r=await fetch('./data/stocks.json?t='+Date.now(),{cache:'no-store',signal:ctl.signal});if(!r.ok)throw Error('HTTP '+r.status);
 const d=await r.json();if(!Array.isArray(d.stocks)||!d.stocks.length)throw Error('空資料');
 stocks=d.stocks.filter(s=>s&&/^\d{4}$/.test(String(s.id))&&Number.isFinite(Number(s.close)));
 $('meta').textContent=`資料擷取日：${d.date||'未提供'}｜來源：${(d.sources||[]).join('、')}｜${stocks.length} 檔（盤後快照，非即時）`;
 $('status').textContent='已載入';render();
 }catch(e){$('status').textContent='載入失敗';$('error').textContent=e.message}finally{clearTimeout(t)}
}
async function live(){
 if(busy)return;const key=$('apikey').value.trim(),symbols=[...new Set($('symbols').value.split(/[,，\s]+/).filter(Boolean))];
 if(!key){$('liveinfo').textContent='請輸入自己的 Fugle API Key';return}
 if(!symbols.length||symbols.length>5||symbols.some(s=>!/^\d{4,6}$/.test(s))){$('liveinfo').textContent='只能輸入 1～5 個有效代號';return}
 busy=true;$('fetchlive').disabled=true;
 try{
 const result=[];
 for(const symbol of symbols){
 try{
 const ctl=new AbortController(),t=setTimeout(()=>ctl.abort(),12000);let r;
 try{r=await fetch('https://api.fugle.tw/marketdata/v1.0/stock/intraday/quote/'+symbol,{headers:{'X-API-KEY':key},cache:'no-store',signal:ctl.signal})}finally{clearTimeout(t)}
 if(!r.ok)throw Error('HTTP '+r.status);
 const q=await r.json();if(q.symbol!==symbol)throw Error('代號不符');result.push({symbol,q});
 }catch(e){result.push({symbol,error:e.message})}
 }
 $('livequotes').innerHTML=result.map(x=>x.error?`<div class="card">${esc(x.symbol)}：${esc(x.error)}</div>`:`<div class="card"><b>${esc(x.q.symbol)} ${esc(x.q.name)}</b><p>最後成交 ${fmt(x.q.closePrice)} · 漲跌 ${fmt(x.q.changePercent)}%</p><small>報價日 ${esc(x.q.date)}｜${x.q.isTrial?'試撮':'一般行情'}｜更新時間戳 ${esc(x.q.lastUpdated)}</small></div>`).join('');
 $('liveinfo').textContent='查詢時間：'+new Date().toLocaleString('zh-TW')+'。若 Failed to fetch，可能是 Safari 跨網域限制。';
 if(!timer)timer=setInterval(()=>{if(!$('live').hidden&&document.visibilityState==='visible')live()},60000);
 }finally{busy=false;$('fetchlive').disabled=false}
}
$('fetchlive').onclick=live;
$('stoplive').onclick=()=>{clearInterval(timer);timer=null;$('liveinfo').textContent='已停止自動更新'};
$('sort').onchange=render;$('apply').onclick=()=>{render();show('radar')};
load();
if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js?v=0521',{updateViaCache:'none'}).catch(()=>{});
})();