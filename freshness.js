(()=>{'use strict';
const box=document.createElement('div');box.id='freshness-status';box.setAttribute('role','status');box.style.cssText='padding:12px;margin:10px 0;border-radius:12px;background:#382b20;color:#ffdb9d;border:1px solid #8c6c3b;font-size:14px;line-height:1.6';
const anchor=document.querySelector('#meta');if(anchor?.parentElement)anchor.parentElement.prepend(box);
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
fetch('./data/stocks.json?fresh='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>{
 const markets=['TWSE','TPEx'];const state=d.market_status||{};
 const lines=markets.map(m=>{const s=state[m];return s?.date_verified===true&&s.trade_date?`${m}：已驗證 ${s.trade_date}${s.trade_date===today?'（今日）':'（非今日）'}`:`${m}：尚無已驗證交易日，可能是舊行情`});
 const all=markets.every(m=>state[m]?.date_verified===true&&state[m]?.trade_date===today);
 if(all){box.style.background='#153c33';box.style.borderColor='#286a58';box.style.color='#a7f0d1';box.textContent='✓ 今日盤後行情已驗證｜'+lines.join('｜');}
 else box.textContent='⚠ 行情交易日檢查｜'+lines.join('｜')+'。未驗證或過期市場的價格不得視為今日收盤價。';
}).catch(e=>{box.textContent='⚠ 無法確認行情交易日：'+e.message});
})();
