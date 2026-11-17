"""Fetch latest common date close for 7 tickers (unadjusted), with validation. Best effort unofficial Yahoo Finance/yfinance feed."""
from datetime import datetime, timezone
from pathlib import Path
import json, sys
import pandas as pd
import yfinance as yf

SYMBOLS={'aapl':'AAPL','nvda':'NVDA','googl':'GOOGL','tsla':'TSLA','meta':'META','spx':'^GSPC','ixic':'^IXIC'}
PATH=Path(__file__).resolve().parent/'updates.json'
data=json.loads(PATH.read_text(encoding='utf-8'))
histories={}
for key,ticker in SYMBOLS.items():
    df=yf.Ticker(ticker).history(period='20d',interval='1d',auto_adjust=False,actions=False)
    if df.empty or 'Close' not in df.columns:
        sys.exit(f'Failed to obtain daily closing prices for {ticker}; keeping existing JSON')
    ser=df['Close'].dropna().copy()
    ser.index=[x.date().isoformat() for x in ser.index]
    histories[key]=ser

dates=set.intersection(*(set(s.index) for s in histories.values()))
if not dates:
    sys.exit('No common market date; keeping existing JSON')
day=max(dates)
if (datetime.now(timezone.utc).date()-datetime.fromisoformat(day).date()).days>8:
    sys.exit('Price feed older than 8 days; keeping existing JSON')
if day<='2026-11-16':
    print('No newer confirmed date yet; no changes.')
    sys.exit(0)
row={'date':day}
for key,ser in histories.items():
    value=float(ser.loc[day])
    if not (value>0 and value<1_000_000):
        sys.exit(f'Unexpected price for {key}: {value}')
    row[key]=round(value,4)
rows={r['date']:r for r in data.get('rows',[]) if r['date']>'2026-11-16'}
prevdate=max(rows) if rows else None
if prevdate and day>prevdate:
    old=rows[prevdate]
    for key in SYMBOLS:
        if abs(row[key]/old[key]-1)>.60:
            sys.exit(f'Unexpected >60% jump for {key}; manual verification required')
rows[day]=row
out={'updated':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'source':'Yahoo Finance via yfinance (unofficial, no SLA)','rows':[rows[d] for d in sorted(rows)[-120:]]}
PATH.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated:',day,row)
