"""Update weekly closes and first US-trading-day-of-month close history.

Run in GitHub Actions. Uses Yahoo Finance unofficial feed (yfinance), so delays and
rate limits are possible. Last known JSON remains untouched on error.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import pandas as pd
import yfinance as yf

SYMBOLS = {
    'aapl': 'AAPL', 'nvda': 'NVDA', 'googl': 'GOOGL', 'tsla': 'TSLA',
    'meta': 'META', 'spx': '^GSPC', 'ixic': '^IXIC'
}
PATH = Path(__file__).resolve().parent / 'updates.json'
existing = json.loads(PATH.read_text(encoding='utf-8'))

# The single historical request per symbol supplies both latest and month-first closes.
series = {}
for key, ticker in SYMBOLS.items():
    df = yf.Ticker(ticker).history(start='2023-12-28', interval='1d', auto_adjust=False, actions=False)
    if df.empty or 'Close' not in df.columns:
        sys.exit(f'Failed to obtain closing prices for {ticker}; existing JSON unchanged')
    s = df['Close'].dropna().copy()
    s.index = [i.date().isoformat() for i in s.index]
    s = s.loc[~pd.Index(s.index).duplicated(keep='last')]
    series[key] = s

common = set.intersection(*(set(s.index) for s in series.values()))
common = sorted(day for day in common if day >= '2024-01-02')
if not common:
    sys.exit('No common trading date for requested symbols; existing JSON unchanged')
today = datetime.now(timezone.utc).date()
last = common[-1]
if (today - datetime.fromisoformat(last).date()).days > 8:
    sys.exit('Latest price is older than 8 days; existing JSON unchanged')

def make_row(day):
    out = {'date': day}
    for key in SYMBOLS:
        val = float(series[key].loc[day])
        if not (0 < val < 1000000):
            raise ValueError(f'Invalid value on {day} for {key}: {val}')
        out[key] = round(val, 4)
    return out

# First *common* trading day for every month. This captures actual first-month
# closes, not the previous month-end approximation used by the standalone HTML.
month_first = {}
for day in common:
    month = day[:7]
    if month not in month_first:
        month_first[month] = make_row(day)

# Keep the original reference snapshots as-is, add only later weekly closes.
new_rows = {r['date']: r for r in existing.get('rows', []) if r.get('date', '') > '2026-11-16'}
if last > '2026-11-16':
    row = make_row(last)
    prev_date = max((d for d in new_rows if d < last), default=None)
    if prev_date:
        for key in SYMBOLS:
            if abs(row[key] / new_rows[prev_date][key] - 1) > 0.60:
                sys.exit(f'Unexpected >60% change in {key}; existing JSON unchanged')
    new_rows[last] = row

data_rows = [new_rows[k] for k in sorted(new_rows)[-150:]]
month_rows = [month_first[k] for k in sorted(month_first)]
if data_rows == existing.get('rows', []) and month_rows == existing.get('monthly_first', []):
    print('No new verified price rows or monthly-first prices; keeping existing JSON')
    sys.exit(0)
out = {
    'updated': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    'source': 'Yahoo Finance via yfinance (unofficial, subject to gaps and changes)',
    'rows': data_rows,
    'monthly_first': month_rows
}
PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Price data through:', last, '| months:', len(month_first), '| new weekly rows:', len(new_rows))
