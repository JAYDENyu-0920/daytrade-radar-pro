(()=>{
'use strict';
const $=id=>document.getElementById(id);
let stocks=[];
const num=v=>Number(v)||0, fmt=v=>num(v).toLocaleString('zh-TW',{maximumFractionDigits:2});
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function show(page){['radar','detail','settings'].forEach(x=>$(x).hidden=x!==page)}
window.show=show;
function render(){
 const min=num($('minvol').value),sort=$('sort').value;
 const list=stocks.filter(s=>s.close>=40&&s.close<=100&&s.volume>=min);
 list.sort((a,b)=>sort==='volume'?b.volume-a.volume:sort==='change'?b.change-a.change:b.score-a.score);
 $('stocks').innerHTML=list.length?list.slice(0,40).map(s=>`<div class="card stock" data-id="${safe(s.id)}"><div class="row"><strong>${safe(s.id)} ${safe(s.name)}</strong><span class="green">${fmt(s.score)} 分</span></div><div class="row"><span>收盤 ${fmt(s.close)} · ${safe(s.market)}</span><span class="${s.change<0?'amber':'green'}">${s.change>=0?'+':''}${fmt(s.change)}%</span></div><small>成交 ${fmt(s.volume)} 張 · 振幅 ${fmt(s.range)}%</small></div>`).join(''):'<div class="card">目前沒有符合條件的股票。請確認資料日期或降低成交量門檻。</div>';
 document.querySelectorAll('.stock').forEach(el=>el.onclick=()=>detail(el.dataset.id));
}
function tick(p){return p<50?.05:p<100?.1:.5}
function round(p){let t=tick(p);return Math.round(p/t)*t}
function detail(id){
 const s=stocks.find(x=>x.id===id);if(!s)return;
 const entry=round(s.high+tick(s.high)),stop=round(s.low),risk=entry-stop,target=round(entry+2*risk),lots=risk>0?Math.floor(num($('risk').value)/(risk*1000)):0;
 $('detailbody').innerHTML=`<h2>${safe(s.id)} ${safe(s.name)}</h2><div class="card"><p>市場 ${safe(s.market)} · 收盤 ${fmt(s.close)} · 評分 ${fmt(s.score)}</p><p>開 ${fmt(s.open)} / 高 ${fmt(s.high)} / 低 ${fmt(s.low)}</p><p>成交量 ${fmt(s.volume)} 張 · 振幅 ${fmt(s.range)}%</p><hr><p>多方突破觀察價：<b class="green">${fmt(entry)}</b></p><p>參考停損：${fmt(stop)} · 2R 目標：${fmt(target)}</p><p>單筆風險預算：約 ${lots} 張（未計費稅與滑價）</p><small>前一交易日價格推算，非即時報價或買進訊號。</small></div>`;
 show('detail');
}
async function load(){
 const ctl=new AbortController(), timer=setTimeout(()=>ctl.abort(),12000);
 try{
  const res=await fetch('./data/stocks.json?t='+Date.now(),{cache:'no-store',signal:ctl.signal});
  if(!res.ok)throw Error('行情檔案 HTTP '+res.status);
  const d=await res.json();
  if(!Array.isArray(d.stocks)||!d.stocks.length)throw Error('行情資料為空');
  if(!d.date||!Array.isArray(d.sources))throw Error('行情日期或來源欄位缺失');
  stocks=d.stocks.filter(s=>s&&/^\d{4}$/.test(String(s.id))&&Number.isFinite(Number(s.close)));
  if(!stocks.length)throw Error('沒有可辨識的股票資料');
  $('meta').textContent=`行情日期：${d.date} ｜ 來源：${d.sources.join('、')} ｜ ${stocks.length} 檔（非即時）`;
  $('error').textContent='';
  $('status').textContent='資料已載入';render();
 }catch(e){
  $('status').textContent='載入失敗';
  $('meta').textContent='無法取得官方行情快照';
  $('error').textContent=(e.name==='AbortError'?'等待超過 12 秒，請檢查網路或資料檔。':e.message)+'；請確認 GitHub Actions「更新台股行情」已成功執行。';
  $('stocks').innerHTML='<div class="card">目前沒有可驗證的行情資料，暫不顯示候選股票。</div>';
 }finally{clearTimeout(timer)}
}
$('sort').onchange=render;
$('apply').onclick=()=>{render();show('radar')};
load();
if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js?v=0510',{updateViaCache:'none'}).catch(()=>{});
})();