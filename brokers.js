(()=>{'use strict';
const $=x=>document.getElementById(x),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const K='radar-broker-trades-v053',S='radar-broker-settings-v053';let groups={},trades=[];
try{trades=JSON.parse(localStorage.getItem(K)||'[]');if(!Array.isArray(trades))trades=[]}catch{trades=[]}
try{const s=JSON.parse(localStorage.getItem(S)||'{}');for(const id of ['stock','minbuy','minratio','totalvol'])if(s[id]!=null)$(id).value=s[id]}catch{}
const index=()=>{let m=new Map();for(const [category,arr] of Object.entries(groups))for(const name of arr){if(!m.has(name))m.set(name,[]);m.get(name).push(category)}return m};
function renderGroups(){const q=$('search').value.trim();$('groups').innerHTML=Object.entries(groups).map(([cat,arr])=>{const filtered=arr.filter(x=>x.includes(q));return filtered.length?`<details class="group" ${q?'open':''}><summary>${esc(cat)} · ${filtered.length} 分點</summary><div>${filtered.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</div></details>`:''}).join('')||'<p>沒有符合的分點</p>'}
function state(){$('state').textContent=trades.length?`已匯入 ${trades.length} 筆紀錄（僅本機）`:'尚未匯入分點交易紀錄'}
function save(){localStorage.setItem(K,JSON.stringify(trades));state()}
function csvLine(line){let out=[],part='',quote=false;for(let i=0;i<line.length;i++){let c=line[i];if(c==='"'){if(quote&&line[i+1]==='"'){part+='"';i++}else quote=!quote}else if(c===','&&!quote){out.push(part.trim());part=''}else part+=c}out.push(part.trim());return out}
$('import').onclick=()=>{const lines=$('csv').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean),lookup=index();let added=[],errors=[];
for(let i=0;i<lines.length;i++){let a=csvLine(lines[i]);if(a[0]==='日期'||a[0].toLowerCase()==='date')continue;
if(a.length!==5||!/^\d{4}-\d{2}-\d{2}$/.test(a[0])||!/^[0-9]{4,6}$/.test(a[1])||!lookup.has(a[2])||!Number.isFinite(Number(a[3]))||!Number.isFinite(Number(a[4]))||Number(a[3])<0||Number(a[4])<0){errors.push(i+1);continue}
added.push({date:a[0],stock:a[1],broker:a[2],buy:Number(a[3]),sell:Number(a[4])})}
if(added.length){let map=new Map(trades.map(t=>[`${t.date}|${t.stock}|${t.broker}`,t]));for(const t of added)map.set(`${t.date}|${t.stock}|${t.broker}`,t);trades=[...map.values()];save()}
$('importinfo').textContent=`成功匯入 ${added.length} 筆；${errors.length?'第 '+errors.join('、')+' 行格式錯誤或分點未在名單中。':'沒有格式錯誤。'}${added.length?' 相同日期／股票／分點的舊紀錄已覆蓋。':''}`;evaluate()};
$('example').onclick=()=>{$('csv').value='2026-10-28,4526,凱基－台北,1500,300';$('importinfo').textContent='這是假資料，僅供測試格式。請勿當作真實交易。'};
$('clear').onclick=()=>{if(confirm('確定清除這台裝置所有匯入的分點交易紀錄？')){trades=[];save();evaluate()}};
function evaluate(){const stock=$('stock').value.trim(),minbuy=Number($('minbuy').value),ratio=Number($('minratio').value),vol=Number($('totalvol').value);for(const id of ['stock','minbuy','minratio','totalvol']){}localStorage.setItem(S,JSON.stringify(Object.fromEntries(['stock','minbuy','minratio','totalvol'].map(x=>[x,$(x).value]))));
if(!/^[0-9]{4,6}$/.test(stock)){$('result').innerHTML='<p class="warning">請先輸入股票代號。</p>';return}
const matches=trades.filter(x=>x.stock===stock);if(!matches.length){$('result').innerHTML='<p class="warning">此股票沒有已匯入的分點交易紀錄，無法判定警報。</p>';return}
const last=[...new Set(matches.map(x=>x.date))].sort().at(-1),items=matches.filter(x=>x.date===last),lookup=index();let alerts=[];
for(const t of items){const net=t.buy-t.sell,cats=lookup.get(t.broker)||[],pct=vol>0?net/vol*100:null,trigger=net>=minbuy&&(pct===null||pct>=ratio);if(trigger)alerts.push({t,net,cats,pct})}
alerts.sort((a,b)=>b.net-a.net);$('result').innerHTML=`<p>股票 ${esc(stock)} · 資料日期 ${esc(last)} · ${items.length} 個分點紀錄。${vol>0?'以使用者填入成交量計算占比。':'未填總成交量，僅依淨買超張數判斷。'}</p>`+(alerts.length?alerts.map(a=>`<div class="card"><b class="${a.cats.some(x=>x.startsWith('隔日沖'))?'danger':'warning'}">${a.cats.some(x=>x.startsWith('隔日沖'))?'隔日沖觀察警報':'分點買超觀察'}</b><p><b>${esc(a.t.broker)}</b> ${a.cats.map(x=>`<span class="tag">${esc(x)}</span>`).join('')}</p><p>買進 ${a.t.buy.toLocaleString()} 張 · 賣出 ${a.t.sell.toLocaleString()} 張 · 淨買超 +${a.net.toLocaleString()} 張${a.pct!==null?' · 占比 '+a.pct.toFixed(2)+'%':''}</p><small>這是依匯入紀錄及設定門檻的規則提醒，不代表確定隔日沖或未來賣壓。</small></div>`).join(''):'<p class="good">有分點資料，但沒有達到警報門檻。</p>')}
$('evaluate').onclick=evaluate;$('search').oninput=renderGroups;
fetch('./brokers.json?t='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>{groups=d.categories;renderGroups();state()}).catch(e=>{$('groups').textContent='名單載入失敗：'+e.message});
})();