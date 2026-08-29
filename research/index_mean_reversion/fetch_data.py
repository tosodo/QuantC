#!/usr/bin/env python3
"""
fetch_data.py - pull DAILY futures bars from Yahoo Finance's public chart API.

Purpose
    Get real daily-close history for the index mean-reversion hypothesis test
    (trailing/forward 20-trading-day returns need years of daily bars, not the
    ~730-day hourly window used by the mnq_session_open screen). No paid data
    subscription, no dependencies beyond the standard library - same approach
    as `research/mnq_session_open/fetch_data.py`, just interval=1d and a much
    longer range.

What this is NOT
    A CME/CQG-grade data feed. Yahoo's continuous front-month futures series
    (NQ=F, ES=F, YM=F) are a proxy - the same proxy already disclosed in
    domain_priors.md for the original cross-asset variance-ratio screen. Good
    enough to test a hypothesis; not a substitute for the eventual live/
    backtest engine's actual data feed.

Known limits (stated up front, not discovered later)
    - Yahoo continuous front-month futures series (NQ=F/ES=F/YM=F) typically
      run back to the mid-2000s on the "1d" interval, not the multi-decade
      history a cash index would offer. Whatever range actually comes back is
      printed below and carried into the test output, not hidden.
    - Front-month continuous contracts are NOT back-adjusted for roll gaps
      here. Roll-date jumps sit in the daily-return series as ordinary
      returns. This inflates realised volatility around roll dates by a small
      amount; it does not selectively bias the direction of the mean-
      reversion signal, but it is a real limitation of using unadjusted
      continuous futures rather than a back-adjusted or cash-index series.

Output
    One CSV per symbol in data/, columns: date,open,high,low,close
"""

import csv
import datetime
import json
import sys
import urllib.request

SYMBOLS = {
    "NQ": "NQ=F",   # Nasdaq-100 e-mini future (Nasdaq leg)
    "ES": "ES=F",   # S&P 500 e-mini future (S&P leg)
    "YM": "YM=F",   # Dow e-mini future (Dow leg)
}


def fetch(symbol, interval="1d", range_="25y"):
    # NOTE: range="max" silently demotes Yahoo's continuous-futures series to
    # MONTHLY bars once the requested window is long enough (discovered while
    # building this fetch - the first cut of this script used "max" and
    # produced ~266 "daily" bars spanning 25 years, i.e. one bar/month). A
    # bounded range of 25y was verified by hand (curl + timestamp gap check)
    # to return true one-trading-day-apart bars for NQ=F/ES=F/YM=F. Do not
    # switch this back to "max" without re-checking the gap spacing.
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
            continue  # Yahoo pads illiquid/missing sessions with nulls; drop, don't guess.
        dt = datetime.datetime.utcfromtimestamp(t)
        rows.append((dt.date().isoformat(), o[i], h[i], l[i], c[i]))
    rows.sort(key=lambda r: r[0])
    # De-dup same-day entries (can happen at the boundary of Yahoo's range param).
    dedup = {}
    for row in rows:
        dedup[row[0]] = row
    return [dedup[k] for k in sorted(dedup)]


def main():
    out_dir = "data"
    for label, symbol in SYMBOLS.items():
        print(f"Fetching {symbol} ({label}) daily bars ...")
        rows = fetch(symbol)
        path = f"{out_dir}/{label}.csv"
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "open", "high", "low", "close"])
            w.writerows(rows)
        first_day = rows[0][0] if rows else "n/a"
        last_day = rows[-1][0] if rows else "n/a"
        years = (len(rows) / 252.0) if rows else 0.0
        print(f"  {len(rows)} bars, {first_day} -> {last_day}  (~{years:.1f}y)  -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
