import datetime as dt
import json, pathlib, re, sys, urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
URLS={
 "TWSE":"https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
 "TPEx":"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
 with urllib.request.urlopen(req,timeout=35) as resp:return json.load(resp)
def pick(row,*keys):
 for key in keys:
  value=row.get(key)
  if value is not None and str(value).strip() not in ("","--","---","None","除權息"):return value
 return None
def number(value):
 try:return float(str(value).replace(",","").replace("+","").replace("%","").strip())
 except (TypeError,ValueError):return None
def parse(market,rows):
 stocks=[]
 for r in rows:
  if not isinstance(r,dict):continue
  code=str(pick(r,"Code","SecuritiesCompanyCode","證券代號","代號","股票代號") or "").strip()
  if not re.fullmatch(r"\d{4}",code):continue
  name=str(pick(r,"Name","CompanyName","證券名稱","名稱","股票名稱") or "")
  close=number(pick(r,"ClosingPrice","Close","收盤價","收盤"))
  op=number(pick(r,"OpeningPrice","Open","開盤價","開盤"))
  high=number(pick(r,"HighestPrice","High","最高價","最高"))
  low=number(pick(r,"LowestPrice","Low","最低價","最低"))
  volume=number(pick(r,"TradeVolume","TradingVolume","成交股數","成交量"))
  if None in (close,op,high,low,volume) or not 40<=close<=100 or high<low:continue
  # Verify volume units per endpoint before ranking. TWSE reports shares;
  # TPEx daily close quotes generally report shares as well.
  lots=volume/1000
  change=number(pick(r,"Change","漲跌價差","漲跌"))
  previous=close-change if change is not None else None
  pct=100*change/previous if previous and previous>0 else 0
  amplitude=(high-low)/close*100
  score=round(min(40,lots/1500)+min(35,amplitude*5)+min(25,abs(pct)*4))
  stocks.append(dict(id=code,name=name,market=market,open=op,high=high,low=low,close=close,volume=round(lots),change=round(pct,2),range=round(amplitude,2),score=score))
 return stocks
def main():
 all_stocks=[];sources=[]
 for market,url in URLS.items():
  data=get(url)
  if isinstance(data,dict):data=data.get("data",data.get("items",[]))
  if not isinstance(data,list):raise RuntimeError(f"{market}: 非陣列資料")
  parsed=parse(market,data)
  if not parsed:raise RuntimeError(f"{market}: 無法解析股票，請檢查官方 API 欄位")
  print(market,len(parsed))
  all_stocks+=parsed;sources.append(market)
 # Endpoints may not provide a verified quote date. Do not mislabel fetch date as quote date.
 # The date below is a snapshot retrieval date, NOT a verified trading date.
 now=dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
 output={"date":now.strftime("%Y-%m-%d")+"（擷取日，非已驗證交易日）","fetched_at":now.isoformat(),"sources":sources,"stocks":all_stocks}
 target=ROOT/"data"/"stocks.json";target.parent.mkdir(exist_ok=True)
 target.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 print("saved",len(all_stocks))
if __name__=="__main__":
 try:main()
 except Exception as exc:print("更新失敗：",exc,file=sys.stderr);sys.exit(1)
