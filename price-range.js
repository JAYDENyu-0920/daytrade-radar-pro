(()=>{'use strict';
const $=id=>document.getElementById(id),KEY='radar-price-range-v056';
const clamp=x=>Math.max(0,Math.min(300,Number.isFinite(+x)?Math.round(+x):0));
let low=40,high=100;
try{const p=JSON.parse(localStorage.getItem(KEY)||'null');if(p&&Number.isFinite(+p.low)&&Number.isFinite(+p.high)){low=clamp(p.low);high=clamp(p.high);if(low>high)[low,high]=[high,low]}}catch{}
function sync(){for(const id of ['minprice','minprice-slider'])$(id).value=low;for(const id of ['maxprice','maxprice-slider'])$(id).value=high;$('price-summary').textContent=`目前範圍：${low}～${high} 元`;try{localStorage.setItem(KEY,JSON.stringify({low,high}))}catch{}}
function update(which,v){if(which==='low')low=Math.min(clamp(v),high);else high=Math.max(clamp(v),low);sync();}
for(const id of ['minprice','minprice-slider'])$(id).addEventListener('input',e=>update('low',e.target.value));
for(const id of ['maxprice','maxprice-slider'])$(id).addEventListener('input',e=>update('high',e.target.value));
$('price-reset').addEventListener('click',()=>{low=40;high=100;sync()});
$('price-all').addEventListener('click',()=>{low=0;high=300;sync()});
sync();
})();
