#!/usr/bin/env python3
"""
fetch_data_rty.py - pull DAILY RTY=F (Russell 2000 e-mini, continuous
front-month) futures bars from Yahoo Finance's public chart API.

Written as a standalone one-off script (rather than editing fetch_data.py)
so the original, already-audited fetch script is not modified. Uses the
IDENTICAL approach fetch_data.py already verified for NQ=F/ES=F/YM=F:
range="25y", NOT range="max" (range="max" silently demotes continuous
futures series to MONTHLY bars - documented and discovered in
fetch_data.py's docstring/comments). Gap-checked below before trusting
the download, same discipline as fetch_data_cash.py's _gap_check.

Output: data/RTY.csv, columns date,open,high,low,close (same format as
the other files in data/, so screen_mean_reversion.py's load() reads it
unchanged).
"""

import csv
import datetime
import json
import sys
import urllib.request

SYMBOL = "RTY=F"   # Russell 2000 e-mini future
LABEL = "RTY"


def fetch(symbol, interval="1d", range_="25y"):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval={interval}&range={range_}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    result = data["chart"]["result"]
    if not result:
        raise SystemExit(f"No data returned for {symbol}")
    res = result[0]
    ts = res["timestamp"]
    quote = res["indicators"]["quote"][0]
    o, h, l, c = quote["open"], quote["high"], quote["low"], quote["close"]
    rows = []
    for i, t in enumerate(ts):
        if None in (o[i], h[i], l[i], c[i]):
            continue
        dt = datetime.datetime.utcfromtimestamp(t)
        rows.append((dt.date().isoformat(), o[i], h[i], l[i], c[i]))
    rows.sort(key=lambda r: r[0])
    dedup = {}
    for row in rows:
        dedup[row[0]] = row
    return [dedup[k] for k in sorted(dedup)]


def _gap_check(rows, label):
    if len(rows) < 3:
        return
    dates = [datetime.date.fromisoformat(r[0]) for r in rows[-260:]]
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    gaps.sort()
    median_gap = gaps[len(gaps) // 2]
    print(f"  [{label}] median gap over last {len(gaps)} bars: {median_gap} calendar day(s)"
          f"{'  WARNING: looks like NOT daily bars!' if median_gap > 5 else ''}")


def main():
    out_dir = "data"
    print(f"Fetching {SYMBOL} ({LABEL}) daily bars, range=25y ...")
    rows = fetch(SYMBOL)
    path = f"{out_dir}/{LABEL}.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "open", "high", "low", "close"])
        w.writerows(rows)
    first_day = rows[0][0] if rows else "n/a"
    last_day = rows[-1][0] if rows else "n/a"
    years = (len(rows) / 252.0) if rows else 0.0
    print(f"  {len(rows)} bars, {first_day} -> {last_day}  (~{years:.1f}y)  -> {path}")
    _gap_check(rows, LABEL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
