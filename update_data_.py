"""當沖雷達 Pro V0.5.3.6 — TWSE/TPEx dated closing reports."""
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
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=55) as response:
                return json.loads(response.read().decode('utf-8-sig'))
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f'官方資料取得失敗：{last}')


def number(value):
    if value is None:
        return None
    s = re.sub(r'<[^>]*>', '', str(value)).replace(',', '').replace('%', '').strip()
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    s = str(value or '').strip()
    m = re.search(r'(?<!\d)(\d{2,4})[年/\-.](\d{1,2})[月/\-.](\d{1,2})日?(?!\d)', s)
    if not m:
        m = re.search(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)', s)
    if not m:
        return None
    year, month, day = map(int, m.groups())
    if year < 1911:
        year += 1911
    try:
        return dt.date(year, month, day).isoformat()
    except ValueError:
        return None


def market_date(payload):
    values = [payload.get(k) for k in ('date', 'Date', 'tradeDate', 'TradeDate', 'queryDate', 'reportDate', 'title', 'reportTitle')]
    for table in payload.get('tables', []):
        if isinstance(table, dict):
            values.append(table.get('title'))
    dates = {date for v in values if (date := parse_date(v))}
    return next(iter(dates)) if len(dates) == 1 else None


def norm(key):
    return re.sub(r'[\s　（）()\[\]_]', '', str(key)).replace('臺', '台')


def table_rows(payload, market):
    tables = payload.get('tables') or []
    if isinstance(tables, list):
        for table in tables:
            if not isinstance(table, dict):
                continue
            fields = table.get('fields')
            data = table.get('data')
            if not isinstance(fields, list) or not isinstance(data, list):
                continue
            cols = [norm(f) for f in fields]
            if ('證券代號' in cols and '收盤價' in cols) or (market == 'TPEx' and '代號' in cols and '收盤' in cols and '開盤' in cols and '成交股數' in cols):
                print(f'{market} 報表欄位：{fields[:18]}；原始筆數：{len(data)}', flush=True)
                return [dict(zip(fields, row)) for row in data if isinstance(row, list)]
    for suffix in ('9', '8', '7', ''):
        fields, data = payload.get('fields' + suffix), payload.get('data' + suffix)
        if isinstance(fields, list) and isinstance(data, list):
            cols = [norm(f) for f in fields]
            if ('證券代號' in cols and '收盤價' in cols) or (market == 'TPEx' and '代號' in cols and '收盤' in cols and '開盤' in cols and '成交股數' in cols):
                print(f'{market} 報表欄位：{fields[:18]}；原始筆數：{len(data)}', flush=True)
                return [dict(zip(fields, row)) for row in data if isinstance(row, list)]
    if market == 'TPEx':
        # TPEx's `tables` may be absent; its `data` is a list of report objects,
        # each containing its own `fields` and `data`. Never parse report objects as stocks.
        for key in ('data', 'aaData', 'tables'):
            reports = payload.get(key)
            if not isinstance(reports, list):
                continue
            for report in reports:
                if not isinstance(report, dict):
                    continue
                fields, data = report.get('fields'), report.get('data')
                if not isinstance(fields, list) or not isinstance(data, list):
                    continue
                cols = [norm(f) for f in fields]
                if '代號' in cols and '收盤' in cols and '開盤' in cols and '成交股數' in cols:
                    print(f'TPEx 報表欄位：{fields[:18]}；原始筆數：{len(data)}', flush=True)
                    return [dict(zip(fields, row)) for row in data if isinstance(row, list)]
        if isinstance(payload.get('data'), list) and payload['data'] and isinstance(payload['data'][0], dict):
            first = payload['data'][0]
            print('TPEx 回傳物件欄位：', list(first), flush=True)
    raise RuntimeError(f'{market} 找不到具備股票代號、開盤、收盤、成交股數的行情表格')


def get(row, *keys):
    lookup = {norm(k): v for k, v in row.items()}
    for key in keys:
        value = lookup.get(norm(key))
        if value is not None and str(value).strip() not in ('', '--', '---'):
            return value
    return None


def parse_stocks(rows, market, day):
    stocks = []
    rejected = {'代號': 0, '缺少數字': 0, '價格範圍': 0}
    for row in rows:
        code = str(get(row, '證券代號', '代號', '股票代號', '股票代碼', 'Code', 'SecuritiesCompanyCode', '證券代碼') or '').strip()
        if not re.fullmatch(r'[1-9]\d{3}', code):
            rejected['代號'] += 1
            continue
        close = number(get(row, '收盤價', '收盤', 'ClosingPrice', 'Close'))
        op = number(get(row, '開盤價', '開盤', 'OpeningPrice', 'Open'))
        high = number(get(row, '最高價', '最高', 'HighestPrice', 'High'))
        low = number(get(row, '最低價', '最低', 'LowestPrice', 'Low'))
        volume = number(get(row, '成交股數', 'TradeVolume', 'TradingVolume', 'TradingShares', '成交量'))
        if any(v is None for v in (close, op, high, low, volume)):
            rejected['缺少數字'] += 1
            continue
        if not (40 <= close <= 100 and 0 < low <= op <= high and low <= close <= high and volume >= 0):
            rejected['價格範圍'] += 1
            continue
        raw_change = str(get(row, '漲跌價差', '漲跌', 'Change') or '')
        change = number(raw_change)
        sign = str(get(row, '漲跌(+/-)', '漲跌(+／-)', '漲跌符號') or '')
        if change is not None:
            if '-' in sign or '跌' in sign or 'green' in sign.lower() or raw_change.strip().startswith('-'):
                change = -abs(change)
            elif '+' in sign or '漲' in sign or 'red' in sign.lower() or raw_change.strip().startswith('+'):
                change = abs(change)
        previous = close - change if change is not None else None
        pct = change / previous * 100 if previous and previous > 0 else 0
        lots = volume / 1000
        amplitude = (high - low) / close * 100
        stocks.append({'id': code, 'name': str(get(row, '證券名稱', '名稱', '股票名稱', 'Name', 'CompanyName') or ''), 'market': market, 'open': op, 'high': high, 'low': low, 'close': close, 'volume': round(lots), 'change': round(pct, 2), 'range': round(amplitude, 2), 'score': round(min(40, lots / 1500) + min(35, amplitude * 5) + min(25, abs(pct) * 4)), 'trade_date': day})
    print(f'{market} 篩選統計：{rejected}；符合條件：{len(stocks)} 檔', flush=True)
    if len(stocks) < 30:
        raise RuntimeError(f'{market} 僅解析 {len(stocks)} 檔，拒絕發布')
    return stocks


def retrieve(market, day):
    if market == 'TWSE':
        url = TWSE_URL.format(day.replace('-', ''))
    else:
        url = TPEX_URL.format(urllib.parse.quote(day.replace('-', '/'), safe=''))
    payload = fetch(url)
    if not isinstance(payload, dict):
        raise RuntimeError('官方回傳非 JSON 物件')
    status = str(payload.get('stat', payload.get('status', ''))).lower()
    if status and status not in ('ok', 'success', '200'):
        raise RuntimeError(f'官方資料狀態：{status}')
    confirmed = market_date(payload)
    if confirmed != day:
        raise RuntimeError(f'官方報表日期不符：要求 {day}，辨識 {confirmed or "無日期"}')
    stocks = parse_stocks(table_rows(payload, market), market, day)
    print(f'{market} {day} 官方報表已驗證：{len(stocks)} 檔', flush=True)
    return stocks


def main():
    now = dt.datetime.now(TZ)
    test_date = os.environ.get('RADAR_TEST_DATE', '').strip()
    if test_date:
        try:
            requested = dt.date.fromisoformat(test_date)
        except ValueError:
            raise RuntimeError('測試日期必須是 YYYY-MM-DD')
        if requested > now.date() or requested.weekday() >= 5:
            raise RuntimeError('測試日期不可為未來日期或週末')
        day = requested.isoformat()
        print(f'歷史唯讀測試：{day}；不修改 stocks.json', flush=True)
        results = {}
        for market in ('TWSE', 'TPEx'):
            try:
                rows = retrieve(market, day)
                results[market] = {'ok': True, 'count': len(rows), 'examples': [s for s in rows if s['id'] in ('1802', '4526', '2330')]}
            except Exception as exc:
                results[market] = {'ok': False, 'error': str(exc)}
        print('測試結果：' + json.dumps(results, ensure_ascii=False), flush=True)
        if not all(v['ok'] for v in results.values()):
            raise RuntimeError('至少一個市場驗證失敗；正式行情未修改')
        print('歷史行情測試通過；正式行情未修改', flush=True)
        return
    day = now.date().isoformat()
    if now.weekday() >= 5 or now.hour < 16:
        raise RuntimeError('只在台灣交易日 16:00 後嘗試發布當日行情')
    target = ROOT / 'data' / 'stocks.json'
    previous = json.loads(target.read_text('utf-8')) if target.exists() else {}
    prior_stocks = previous.get('stocks', [])
    status = dict(previous.get('market_status', {}))
    by_market = {m: [s for s in prior_stocks if s.get('market') == m] for m in ('TWSE', 'TPEx')}
    errors = {}
    updated = []
    for market in ('TWSE', 'TPEx'):
        try:
            by_market[market] = retrieve(market, day)
            status[market] = {'trade_date': day, 'date_verified': True, 'updated_at': now.isoformat()}
            updated.append(market)
        except Exception as exc:
            errors[market] = str(exc)
            print(f'警告：{market} 未更新：{exc}', file=sys.stderr, flush=True)
            if not previous.get('market_status', {}).get(market, {}).get('date_verified'):
                status[market] = {'trade_date': None, 'date_verified': False, 'reason': '舊行情日期未驗證'}
    if not updated:
        raise RuntimeError(f'兩市場均未通過驗證；原檔不變：{errors}')
    stocks = by_market['TWSE'] + by_market['TPEx']
    full = all(status.get(m, {}).get('date_verified') and status[m].get('trade_date') == day for m in ('TWSE', 'TPEx'))
    output = {'date': day if full else '各市場交易日不同，請參照 market_status', 'trade_date': day if full else None, 'date_verified': bool(full), 'fetched_at': now.isoformat(), 'sources': updated, 'market_status': status, 'stocks': stocks}
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    tmp.replace(target)
    print(f'已更新：{updated}；失敗：{errors}；同日驗證：{full}；總數：{len(stocks)}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:', exc, file=sys.stderr)
        sys.exit(1)
