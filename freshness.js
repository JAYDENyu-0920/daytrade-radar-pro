(()=>{'use strict';
const box=document.createElement('div');box.id='freshness-status';box.setAttribute('role','status');box.style.cssText='padding:12px;margin:10px 0;border-radius:12px;background:#382b20;color:#ffdb9d;border:1px solid #8c6c3b;font-size:14px;line-height:1.5';box.textContent='正在驗證盤後行情日期…';
const anchor=document.querySelector('#meta');if(anchor?.parentElement)anchor.parentElement.prepend(box);
const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
fetch('./data/stocks.json?fresh='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>{
 const day=d.trade_date||null,valid=d.date_verified===true&&/^\d{4}-\d{2}-\d{2}$/.test(day||'');
 if(!valid){box.textContent='⚠ 尚未驗證實際交易日：目前行情可能是前一交易日資料，請勿當作今日收盤價。';return}
 if(day===today){box.style.background='#153c33';box.style.borderColor='#286a58';box.style.color='#a7f0d1';box.textContent='✓ 已驗證 '+day+' 收盤行情（資料擷取：'+(d.fetched_at||'未提供')+'）'}
 else{box.textContent='⚠ 目前顯示 '+day+' 收盤行情，並非今天 '+today+' 的收盤價。最新交易日可能尚未更新或今天休市。'}
}).catch(e=>{box.textContent='⚠ 無法確認行情交易日：'+e.message});
})();
