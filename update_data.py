"""V0.5.3.2: fail-closed daily market snapshot with independently checked trade date."""
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
TWSE = 'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'
TPEX = 'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'
ANCHOR = 'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={date}&stockNo=2330'
TZ = ZoneInfo('Asia/Taipei')

def fetch(url):
    last = None
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0','Accept':'application/json','Cache-Control':'no-cache'})
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode('utf-8-sig'))
        except Exception as e:
            last=e
            if i<3: time.sleep(2**i)
    raise RuntimeError(f'無法取得官方資料 {url}: {last}')

def num(v):
    try: return float(str(v).replace(',','').replace('+','').replace('%','').strip())
    except (ValueError,TypeError): return None

def pick(r,*names):
    for k in names:
        v=r.get(k)
        if v is not None and str(v).strip() not in ('','--','---','None'): return v
    return None

def iso_date(v):
    s=str(v or '').strip().replace('/','-')
    if re.fullmatch(r'\d{8}',s): s=f'{s[:4]}-{s[4:6]}-{s[6:]}'
    m=re.fullmatch(r'(\d{2,4})-(\d{1,2})-(\d{1,2})',s)
    if not m:return None
    y,mo,day=map(int,m.groups())
    if y<1911:y+=1911
    try:return dt.date(y,mo,day).isoformat()
    except ValueError:return None

def rows_of(payload):
    if isinstance(payload,list):return payload
    if isinstance(payload,dict):
        for key in ('data','items'):
            if isinstance(payload.get(key),list):return payload[key]
    raise RuntimeError('官方資料格式不是陣列')

def verify_twse(raw, day):
    """Cross-check raw TWSE anchor close against independently dated monthly daily report."""
    anchor=next((r for r in raw if str(pick(r,'Code','證券代號') or '')=='2330'),None)
    if not anchor:raise RuntimeError('TWSE 找不到 2330 交叉核對樣本')
    observed=num(pick(anchor,'ClosingPrice','Close','收盤價'))
    report=fetch(ANCHOR.format(date=day.replace('-','')))
    records=report.get('data',[]) if isinstance(report,dict) else []
    matching=[r for r in records if isinstance(r,list) and r and iso_date(r[0])==day]
    if not matching:raise RuntimeError(f'TWSE 獨立日報尚無 {day} 資料，拒絕將舊價標成今日')
    verified=num(matching[-1][6]) if len(matching[-1])>6 else None
    if observed is None or verified is None or abs(observed-verified)>.001:
        raise RuntimeError(f'TWSE 價格核對不符：總表 {observed} / {day} 日報 {verified}')
    return True

def verify_tpex(raw,day):
    dates=set()
    for r in raw:
        if isinstance(r,dict):
            for key in ('Date','date','TradeDate','TradingDate','資料日期','交易日期'):
                if key in r:
                    parsed=iso_date(r[key])
                    if parsed:dates.add(parsed)
    if dates=={day}:return True
    raise RuntimeError(f'TPEx 無法驗證交易日期（資料標示：{sorted(dates)}）；不採用')

def parse(market,raw,day):
    result=[]
    for r in raw:
        if not isinstance(r,dict):continue
        code=str(pick(r,'Code','SecuritiesCompanyCode','證券代號','代號','股票代號') or '').strip()
        if not re.fullmatch(r'\d{4}',code) or code.startswith('0'):continue
        close=num(pick(r,'ClosingPrice','Close','收盤價','收盤'))
        op=num(pick(r,'OpeningPrice','Open','開盤價','開盤'))
        high=num(pick(r,'HighestPrice','High','最高價','最高'))
        low=num(pick(r,'LowestPrice','Low','最低價','最低'))
        volume=num(pick(r,'TradeVolume','TradingVolume','TradingShares','成交股數','成交量'))
        if any(x is None for x in (close,op,high,low,volume)):continue
        if not (40<=close<=100 and op>0 and low>0 and high>=low and volume>=0):continue
        lots=volume/1000
        change=num(pick(r,'Change','漲跌價差','漲跌'))
        prev=close-change if change is not None else None
        pct=100*change/prev if prev and prev>0 else 0
        amplitude=(high-low)/close*100
        result.append(dict(id=code,name=str(pick(r,'Name','CompanyName','證券名稱','名稱','股票名稱') or ''),market=market,open=op,high=high,low=low,close=close,volume=round(lots),change=round(pct,2),range=round(amplitude,2),score=round(min(40,lots/1500)+min(35,amplitude*5)+min(25,abs(pct)*4)),trade_date=day))
    if not result:raise RuntimeError(f'{market} 解析後沒有有效股票')
    return result

def main():
    now=dt.datetime.now(TZ)
    day=now.date().isoformat()
    if now.weekday()>=5:raise RuntimeError('週末不應更新為當日收盤')
    if now.hour<16:raise RuntimeError('台灣時間 16:00 前不發布當日驗證收盤資料')
    all_stocks=[];verified=[];errors={}
    for market,url,check in [('TWSE',TWSE,verify_twse),('TPEx',TPEX,verify_tpex)]:
        try:
            raw=rows_of(fetch(url));check(raw,day)
            parsed=parse(market,raw,day)
            all_stocks+=parsed;verified.append(market)
            print(f'{market} {day} 已驗證 {len(parsed)} 檔',flush=True)
        except Exception as e:
            errors[market]=str(e);print(f'{market} 驗證失敗：{e}',file=sys.stderr,flush=True)
    # Never overwrite a valid previous snapshot with an unverified or partial market snapshot.
    if errors or len(verified)!=2:
        raise RuntimeError('行情日期核對未全數通過，保留前次檔案；'+str(errors))
    target=ROOT/'data'/'stocks.json';target.parent.mkdir(exist_ok=True)
    output=dict(date=day,trade_date=day,date_verified=True,fetched_at=now.isoformat(),sources=verified,stocks=all_stocks)
    tmp=target.with_suffix('.json.tmp');tmp.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(target)
    print(f'成功發布 {day} 收盤資料 {len(all_stocks)} 檔')

if __name__=='__main__':
    try:main()
    except Exception as e:print(str(e),file=sys.stderr);sys.exit(1)
