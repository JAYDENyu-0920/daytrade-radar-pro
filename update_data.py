"""V0.5.3.4 — dated official daily reports, independent market validation.
Never label undated OpenAPI snapshots with the fetch date.
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
TZ = ZoneInfo('Asia/Taipei')
TWSE_URL = 'https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={}&type=ALLBUT0999&response=json'
TPEX_URL = 'https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes?response=json&date={}'


def fetch(url):
    err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; RadarDaily/0.5.3.3)', 'Accept': 'application/json', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=55) as response:
                return json.loads(response.read().decode('utf-8-sig'))
        except Exception as exc:
            err = exc
            if attempt < 2: time.sleep(2 ** attempt)
    raise RuntimeError(f'官方資料取得失敗：{err}')


def number(value):
    if value is None: return None
    value = re.sub(r'<[^>]*>', '', str(value)).replace(',', '').replace('%', '').strip()
    if value in ('', '--', '---', '－', '除權', '除息', '除權息'): return None
    try: return float(value)
    except ValueError: return None


def parse_date(value):
    if not value: return None
    s = str(value).strip()
    # Only recognize an actual date token, never the server's retrieval time.
    match = re.search(r'(?<!\d)(\d{2,4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?(?!\d)', s)
    if not match:
        match = re.search(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)', s)
    if not match: return None
    year, month, day = map(int, match.groups())
    if year < 1911: year += 1911
    try: return dt.date(year, month, day).isoformat()
    except ValueError: return None


def market_date(payload):
    if not isinstance(payload, dict): return None
    values = [payload.get(k) for k in ('date', 'Date', 'tradeDate', 'TradeDate', 'queryDate', 'reportDate')]
    values += [payload.get(k) for k in ('title', 'reportTitle')]
    values += [t.get('title') for t in payload.get('tables', []) if isinstance(t, dict)]
    dates = {d for value in values if (d := parse_date(value))}
    return next(iter(dates)) if len(dates) == 1 else None


def table_rows(payload, market):
    tables = payload.get('tables') or []
    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict): continue
            fields = [re.sub(r'\s+', '', str(f)) for f in table.get('fields', [])]
            if '證券代號' in fields and '收盤價' in fields and ('開盤價' in fields or '最高價' in fields):
                return [dict(zip(fields, row)) for row in table.get('data', []) if isinstance(row, list)]
    for suffix in ('9', '8', '7', ''):
        fields = payload.get('fields' + suffix)
        data = payload.get('data' + suffix)
        if isinstance(fields, list) and isinstance(data, list):
            cols = [re.sub(r'\s+', '', str(f)) for f in fields]
            if '證券代號' in cols and '收盤價' in cols:
                return [dict(zip(cols, row)) for row in data if isinstance(row, list)]
    if market == 'TPEx':
        for key in ('tables', 'aaData', 'data'):
            data = payload.get(key)
            if isinstance(data, list) and data and isinstance(data[0], dict): return data
        # TPEx commonly returns table rows plus columns in tables[0].
        for table in tables:
            if isinstance(table, dict) and isinstance(table.get('data'), list) and isinstance(table.get('fields'), list):
                return [dict(zip(table['fields'], row)) for row in table['data'] if isinstance(row, list)]
    raise RuntimeError(f'{market} 找不到可識別的收盤行情欄位（API 格式可能改變）')


def value(row, *keys):
    for key in keys:
        if key in row and row[key] not in ('', None, '--', '---'): return row[key]
    return None


def parse_stocks(rows, market, day):
    stocks = []
    for row in rows:
        code = str(value(row, '證券代號', '代號', '股票代號', 'Code', 'SecuritiesCompanyCode', '證券代碼') or '').strip()
        if not re.fullmatch(r'[1-9]\d{3}', code): continue
        close = number(value(row, '收盤價', '收盤', 'ClosingPrice', 'Close'))
        op = number(value(row, '開盤價', '開盤', 'OpeningPrice', 'Open'))
        high = number(value(row, '最高價', '最高', 'HighestPrice', 'High'))
        low = number(value(row, '最低價', '最低', 'LowestPrice', 'Low'))
        volume = number(value(row, '成交股數', 'TradeVolume', 'TradingVolume', 'TradingShares', '成交量'))
        if any(v is None for v in (close, op, high, low, volume)): continue
        if not (40 <= close <= 100 and 0 < low <= op <= high and low <= close <= high and volume >= 0): continue
        change = number(value(row, '漲跌價差', '漲跌', 'Change'))
        sign = str(value(row, '漲跌(+/-)', '漲跌(+／-)', '漲跌(+/-)', '漲跌符號') or '')
        if change is not None and ('-' in sign or '跌' in sign or 'green' in sign.lower()): change = -abs(change)
        elif change is not None and ('+' in sign or '漲' in sign or 'red' in sign.lower()): change = abs(change)
        previous = close - change if change is not None else None
        pct = change / previous * 100 if previous and previous > 0 else 0
        lots = volume / 1000
        amplitude = (high - low) / close * 100
        stocks.append({'id': code, 'name': str(value(row, '證券名稱', '名稱', '股票名稱', 'Name', 'CompanyName') or ''), 'market': market,
                       'open': op, 'high': high, 'low': low, 'close': close, 'volume': round(lots), 'change': round(pct, 2),
                       'range': round(amplitude, 2), 'score': round(min(40, lots / 1500) + min(35, amplitude * 5) + min(25, abs(pct) * 4)), 'trade_date': day})
    if len(stocks) < 30: raise RuntimeError(f'{market} 僅解析 {len(stocks)} 檔，疑似資料格式錯誤，拒絕發布')
    return stocks


def retrieve(market, day):
    if market == 'TWSE': url = TWSE_URL.format(day.replace('-', ''))
    else: url = TPEX_URL.format(urllib.parse.quote(day.replace('-', '/'), safe=''))
    payload = fetch(url)
    if not isinstance(payload, dict): raise RuntimeError('官方回傳非 JSON 物件')
    status = str(payload.get('stat', payload.get('status', ''))).lower()
    if status and status not in ('ok', 'success', '200'): raise RuntimeError(f'官方資料狀態：{status}')
    confirmed = market_date(payload)
    if confirmed != day: raise RuntimeError(f'官方報表未能證明交易日為 {day}（辨識結果：{confirmed or "無日期"}）；拒絕標成今日')
    result = parse_stocks(table_rows(payload, market), market, day)
    print(f'{market} {day} 官方指定日期報表驗證通過：{len(result)} 檔', flush=True)
    return result


def main():
    now = dt.datetime.now(TZ)
    test_date = os.environ.get('RADAR_TEST_DATE', '').strip()
    if test_date:
        try:
            requested = dt.date.fromisoformat(test_date)
        except ValueError:
            raise RuntimeError('測試日期必須是 YYYY-MM-DD，例如 2026-10-28')
        if requested > now.date() or requested.weekday() >= 5:
            raise RuntimeError('測試日期不可為未來日期或週末')
        day = requested.isoformat()
        print(f'🧪 歷史行情唯讀測試：{day}；不會寫入 data/stocks.json', flush=True)
        results = {}
        for market in ('TWSE', 'TPEx'):
            try:
                rows = retrieve(market, day)
                results[market] = {'ok': True, 'count': len(rows), 'examples': [s for s in rows if s['id'] in ('1802', '4526', '2330')]}
            except Exception as exc:
                results[market] = {'ok': False, 'error': str(exc)}
        print('測試結果：' + json.dumps(results, ensure_ascii=False), flush=True)
        if not all(v['ok'] for v in results.values()):
            raise RuntimeError('至少一個市場驗證失敗；以上為實際錯誤，不會修改正式行情')
        print('🧪 歷史行情測試通過；正式行情檔案保持不變', flush=True)
        return
    day = now.date().isoformat()
    if now.weekday() >= 5 or now.hour < 16: raise RuntimeError('只在台灣交易日 16:00 後嘗試發布當日行情')
    target = ROOT / 'data' / 'stocks.json'
    previous = json.loads(target.read_text('utf-8')) if target.exists() else {}
    prior_stocks = previous.get('stocks', [])
    status = dict(previous.get('market_status', {}))
    stocks_by_market = {m: [s for s in prior_stocks if s.get('market') == m] for m in ('TWSE', 'TPEx')}
    errors = {}
    updated = []
    for market in ('TWSE', 'TPEx'):
        try:
            stocks_by_market[market] = retrieve(market, day)
            status[market] = {'trade_date': day, 'date_verified': True, 'updated_at': now.isoformat()}
            updated.append(market)
        except Exception as exc:
            errors[market] = str(exc)
            print(f'⚠ {market} 本次未更新：{exc}', file=sys.stderr, flush=True)
            # Older snapshots lacking verified trade dates must not inherit verified status.
            if not previous.get('market_status', {}).get(market, {}).get('date_verified'):
                status[market] = {'trade_date': None, 'date_verified': False, 'reason': '舊行情日期未驗證'}
    if not updated: raise RuntimeError(f'兩市場均未通過驗證；原檔保持不變：{errors}')
    all_stocks = stocks_by_market['TWSE'] + stocks_by_market['TPEx']
    full = all(status.get(m, {}).get('date_verified') and status[m].get('trade_date') == day for m in ('TWSE', 'TPEx'))
    output = {'date': day if full else '各市場交易日不同，請參照 market_status', 'trade_date': day if full else None,
              'date_verified': bool(full), 'fetched_at': now.isoformat(), 'sources': updated,
              'market_status': status, 'stocks': all_stocks}
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    temp.replace(target)
    print(f'成功更新：{updated}；未更新：{errors}；全市場同日驗證：{full}；共 {len(all_stocks)} 檔', flush=True)


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
