import json,datetime,urllib.request,re,pathlib,sys
ROOT=pathlib.Path(__file__).parent
URLS={'TWSE':'https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL','TPEx':'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes'}
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 DaytradeRadar/0.5','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def pick(row,*keys):
 for k in keys:
  if k in row and str(row[k]).strip() not in ('','--','---','None'):return row[k]
 return None
def number(x):
 try:return float(str(x).replace(',','').replace('+','').replace('%','').strip())
 except:return None
def parse(market,rows):
 result=[]; dates=[]
 for r in rows:
  if not isinstance(r,dict):continue
  id=str(pick(r,'Code','SecuritiesCompanyCode','證券代號','代號','股票代號') or '').strip()
  if not re.fullmatch(r'\d{4}',id):continue
  name=str(pick(r,'Name','CompanyName','證券名稱','名稱','股票名稱') or '').strip()
  close=number(pick(r,'ClosingPrice','Close','收盤價','收盤'))
  op=number(pick(r,'OpeningPrice','Open','開盤價','開盤'))
  high=number(pick(r,'HighestPrice','High','最高價','最高'))
  low=number(pick(r,'LowestPrice','Low','最低價','最低'))
  volume=number(pick(r,'TradeVolume','TradingVolume','成交股數','成交量'))
  date=pick(r,'Date','資料日期','日期')
  if date:dates.append(str(date))
  if None in (close,op,high,low,volume) or not (40<=close<=100) or close<=0 or high<low:continue
  # Official sources generally report volume in shares; verify units before changing this conversion.
  lots=volume/1000
  change=number(pick(r,'Change','漲跌價差','漲跌')) or 0
  # Absolute change amount, not percent
  previous=close-change
  pct=100*change/previous if previous>0 else 0
  amplitude=(high-low)/close*100
  score=round(min(40,lots/1500)+min(35,amplitude*5)+min(25,abs(pct)*4))
  result.append(dict(id=id,name=name,market=market,open=op,high=high,low=low,close=close,volume=round(lots),change=round(pct,2),range=round(amplitude,2),score=score))
 return result,dates
all_stocks=[];sources=[];errors=[];all_dates=[]
for market,url in URLS.items():
 try:
  rows=get(url)
  if isinstance(rows,dict):rows=rows.get('data',rows.get('items',[]))
  parsed,dates=parse(market,rows)
  if not parsed:raise ValueError('沒有解析出符合條件的股票，請檢查官方 API 欄位')
  all_stocks+=parsed;sources.append(market);all_dates+=dates
  print(market,len(parsed))
 except Exception as exc:errors.append(f'{market}: {exc}');print(errors[-1],file=sys.stderr)
if errors or not all_stocks:
 print('資料來源未完整成功，為避免誤導，拒絕覆蓋既有資料。',file=sys.stderr);sys.exit(1)
# Never label an API fetch timestamp as a verified trading date.
if not all_dates:
 print('官方資料缺少日期欄位，拒絕產生未標示交易日的行情。',file=sys.stderr);sys.exit(1)
unique=set(all_dates)
if len(unique)>1:
 print('官方資料日期不一致：'+str(unique),file=sys.stderr);sys.exit(1)
out={'date':all_dates[0],'fetched_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':sources,'stocks':all_stocks}
p=ROOT/'data'/'stocks.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf8')
print('saved',len(all_stocks),out['date'])
