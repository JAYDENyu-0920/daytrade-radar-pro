"""Radar Pro V0.5.3.5: dated official reports with TPEx diagnostics."""
import datetime as dt
import json, os, pathlib, re, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parent
TZ=ZoneInfo('Asia/Taipei')
TWSE_URL='https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={}&type=ALLBUT0999&response=json'
TPEX_URL='https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?response=json&date={}'
def fetch(url):
    err=None
    for i in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Cache-Control':'no-cache'})
            with urllib.request.urlopen(req,timeout=55) as res:return json.loads(res.read().decode('utf-8-sig'))
        except Exception as e:
            err=e
            if i<2:time.sleep(2**i)
    raise RuntimeError(f'官方資料取得失敗：{err}')
def number(v):
    if v is None:return None
    s=re.sub(r'<[^>]*>','',str(v)).replace(',','').replace('%','').strip()
    try:return float(s)
    except (ValueError,TypeError):return None
def parse_date(v):
    s=str(v or '').strip()
    m=re.search(r'(?<!\d)(\d{2,4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?(?!\d)',s)
    if not m:m=re.search(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)',s)
    if not m:return None
    y,mo,d=map(int,m.groups())
    if y<1911:y+=1911
    try:return dt.date(y,mo,d).isoformat()
    except ValueError:return None
def market_date(p):
    vals=[p.get(k) for k in ('date','Date','tradeDate','TradeDate','queryDate','reportDate','title','reportTitle')]
    vals += [t.get('title') for t in p.get('tables',[]) if isinstance(t,dict)]
    dates={x for v in vals if (x:=parse_date(v))}
    return next(iter(dates)) if len(dates)==1 else None
def table_rows(p,market):
    tables=p.get('tables') or []
    for t in tables:
        if not isinstance(t,dict):continue
        f=[re.sub(r'\s+','',str(x)) for x in t.get('fields',[])]
        if '證券代號' in f and '收盤價' in f and ('開盤價' in f or '最高價' in f):
            return [dict(zip(f,row)) for row in t.get('data',[]) if isinstance(row,list)]
    for suf in ('9','8','7',''):
        f=p.get('fields'+suf);d=p.get('data'+suf)
        if isinstance(f,list) and isinstance(d,list):
            f=[re.sub(r'\s+','',str(x)) for x in f]
            if '證券代號' in f and '收盤價' in f:return [dict(zip(f,row)) for row in d if isinstance(row,list)]
    if market=='TPEx':
        for key in ('tables','aaData','data'):
            d=p.get(key)
            if isinstance(d,list) and d and isinstance(d[0],dict):return d
        for t in tables:
            if isinstance(t,dict) and isinstance(t.get('data'),list) and isinstance(t.get('fields'),list):
                return [dict(zip(t['fields'],row)) for row in t['data'] if isinstance(row,list)]
    raise RuntimeError(f'{market} 無法辨識行情表格欄位')
def get(row,*keys):
    norm=lambda s:re.sub(r'[\s　（）()\[\]_]','',str(s)).replace('臺','台')
    lookup={norm(k):v for k,v in row.items()}
    for k in keys:
        v=lookup.get(norm(k))
        if v is not None and str(v).strip() not in ('','--','---'):return v
    return None
def parse_stocks(rows,market,day):
    if market=='TPEx':
        print('TPEx 原始資料筆數：',len(rows),flush=True)
        print('TPEx 欄位名稱：',list(rows[0]) if rows else [],flush=True)
        print('TPEx 前兩筆資料：',json.dumps(rows[:2],ensure_ascii=False)[:2000],flush=True)
    out=[];rejected={'代號':0,'欄位缺漏':0,'價格範圍':0}
    for row in rows:
        code=str(get(row,'證券代號','代號','股票代號','股票代碼','Code','SecuritiesCompanyCode','證券代碼') or '').strip()
        if not re.fullmatch(r'[1-9]\d{3}',code):rejected['代號']+=1;continue
        close=number(get(row,'收盤價','收盤','ClosingPrice','Close'))
        op=number(get(row,'開盤價','開盤','OpeningPrice','Open'))
        high=number(get(row,'最高價','最高','HighestPrice','High'))
        low=number(get(row,'最低價','最低','LowestPrice','Low'))
        vol=number(get(row,'成交股數','TradeVolume','TradingVolume','TradingShares','成交量'))
        if any(x is None for x in (close,op,high,low,vol)):rejected['欄位缺漏']+=1;continue
        if not (40<=close<=100 and 0<low<=op<=high and low<=close<=high and vol>=0):rejected['價格範圍']+=1;continue
        change=number(get(row,'漲跌價差','漲跌','Change'))
        sign=str(get(row,'漲跌(+/-)','漲跌(+／-)','漲跌符號') or '')
        if change is not None and ('-' in sign or '跌' in sign or 'green' in sign.lower()):change=-abs(change)
        elif change is not None and ('+' in sign or '漲' in sign or 'red' in sign.lower()):change=abs(change)
        prev=close-change if change is not None else None
        pct=change/prev*100 if prev and prev>0 else 0
        lots=vol/1000;amplitude=(high-low)/close*100
        out.append(dict(id=code,name=str(get(row,'證券名稱','名稱','股票名稱','Name','CompanyName') or ''),market=market,open=op,high=high,low=low,close=close,volume=round(lots),change=round(pct,2),range=round(amplitude,2),score=round(min(40,lots/1500)+min(35,amplitude*5)+min(25,abs(pct)*4)),trade_date=day))
    if market=='TPEx':print('TPEx 排除統計：',rejected,'有效股票：',len(out),flush=True)
    if len(out)<30:raise RuntimeError(f'{market} 僅解析 {len(out)} 檔，拒絕發布')
    return out
def retrieve(market,day):
    url=TWSE_URL.format(day.replace('-','')) if market=='TWSE' else TPEX_URL.format(urllib.parse.quote(day.replace('-','/'),safe=''))
    p=fetch(url)
    if not isinstance(p,dict):raise RuntimeError('官方回傳不是 JSON 物件')
    stat=str(p.get('stat',p.get('status',''))).lower()
    if stat and stat not in ('ok','success','200'):raise RuntimeError(f'官方資料狀態：{stat}')
    confirmed=market_date(p)
    if confirmed!=day:raise RuntimeError(f'官方日期未驗證為 {day}，辨識：{confirmed}')
    out=parse_stocks(table_rows(p,market),market,day)
    print(f'{market} {day} 已驗證 {len(out)} 檔',flush=True)
    return out
def main():
    now=dt.datetime.now(TZ);test=os.environ.get('RADAR_TEST_DATE','').strip()
    if test:
        try:day=dt.date.fromisoformat(test)
        except ValueError:raise RuntimeError('測試日期格式需 YYYY-MM-DD')
        if day>now.date() or day.weekday()>=5:raise RuntimeError('測試日期不可為未來或週末')
        day=day.isoformat();print(f'唯讀歷史測試：{day}；不寫入 stocks.json',flush=True)
        results={}
        for m in ('TWSE','TPEx'):
            try:
                rows=retrieve(m,day)
                results[m]={'ok':True,'count':len(rows),'examples':[x for x in rows if x['id'] in ('1802','4526','2330')]}
            except Exception as e:results[m]={'ok':False,'error':str(e)}
        print('測試結果：'+json.dumps(results,ensure_ascii=False),flush=True)
        if not all(v['ok'] for v in results.values()):raise RuntimeError('有市場未通過驗證；未修改正式資料')
        return
    day=now.date().isoformat()
    if now.weekday()>=5 or now.hour<16:raise RuntimeError('僅台灣交易日 16:00 後更新當日資料')
    target=ROOT/'data'/'stocks.json';previous=json.loads(target.read_text('utf-8')) if target.exists() else {}
    prior=previous.get('stocks',[]);status=dict(previous.get('market_status',{}))
    bymarket={m:[x for x in prior if x.get('market')==m] for m in ('TWSE','TPEx')};updated=[];errors={}
    for m in ('TWSE','TPEx'):
        try:
            bymarket[m]=retrieve(m,day);status[m]={'trade_date':day,'date_verified':True,'updated_at':now.isoformat()};updated.append(m)
        except Exception as e:
            errors[m]=str(e);print(f'{m} 未更新：{e}',file=sys.stderr,flush=True)
            if not previous.get('market_status',{}).get(m,{}).get('date_verified'):
                status[m]={'trade_date':None,'date_verified':False,'reason':'舊行情日期未驗證'}
    if not updated:raise RuntimeError(f'兩市場皆未通過驗證，保留舊檔：{errors}')
    stocks=bymarket['TWSE']+bymarket['TPEx']
    full=all(status.get(m,{}).get('date_verified') and status[m].get('trade_date')==day for m in ('TWSE','TPEx'))
    result={'date':day if full else '各市場交易日不同，請參照 market_status','trade_date':day if full else None,'date_verified':bool(full),'fetched_at':now.isoformat(),'sources':updated,'market_status':status,'stocks':stocks}
    target.parent.mkdir(exist_ok=True);temp=target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8');temp.replace(target)
    print(f'成功更新：{updated}；未更新：{errors}；共 {len(stocks)} 檔',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR:',e,file=sys.stderr);sys.exit(1)
