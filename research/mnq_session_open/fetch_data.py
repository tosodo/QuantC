#!/usr/bin/env python3
"""
fetch_data.py - pull hourly futures bars from Yahoo Finance's public chart API.

Purpose
    Get real historical price data for the US cash-open hypothesis test,
    with no paid data subscription and no dependencies beyond the standard
    library.

What this is NOT
    A CME/CQG-grade data feed. Yahoo's continuous front-month futures series
    (NQ=F, ES=F, YM=F) are a proxy, the same kind of proxy already used and
    disclosed in domain_priors.md for the FX/cross-asset screen. Good enough
    to screen a hypothesis before spending real backtest time on it; not a
    substitute for whatever data feed the eventual live/backtest engine uses.

Known limits (stated up front, not discovered later)
    - Yahoo's hourly ("60m") bars only go back ~730 days. That is what is
      fetched here. It is short of the "8+ years" test_design.md prefers -
      that shortfall is carried forward into the test output, not hidden.
    - Bars are aligned to the top of the hour in exchange-local time. The
      9:30am ET cash open falls inside the 9:00-10:00 bar, not at a bar
      boundary - so "the opening range" here means that bar's high/low, an
      hour-wide window, not a tunable N-minute window. Coarser than a real
      ORB study would use, and honestly labelled as such downstream.

Output
    One CSV per symbol in data/, columns: date_ny,time_ny,open,high,low,close
    Timestamps are US/Eastern (the exchange's own local time), so the
    9:00-10:00 bar is directly identifiable without further conversion.
"""

import csv
import datetime
import json
import sys
import urllib.request
import zoneinfo

NY = zoneinfo.ZoneInfo("America/New_York")

SYMBOLS = {
    "MNQ_proxy": "NQ=F",   # Micro Nasdaq mirrors NQ price action (1/10th size)
    "MES_proxy": "ES=F",   # Micro S&P mirrors ES
    "MYM_proxy": "YM=F",   # Micro Dow mirrors YM
}


def fetch(symbol, interval="60m", range_="730d"):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
           f"?interval={interval}&range={range_}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
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
            continue  # Yahoo pads illiquid hours with nulls; drop, don't guess.
        dt = datetime.datetime.fromtimestamp(t, tz=NY)
        rows.append((dt.date().isoformat(), dt.strftime("%H:%M"),
                      o[i], h[i], l[i], c[i]))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def main():
    out_dir = "data"
    for label, symbol in SYMBOLS.items():
        print(f"Fetching {symbol} ({label}) ...")
        rows = fetch(symbol)
        path = f"{out_dir}/{label}.csv"
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date_ny", "time_ny", "open", "high", "low", "close"])
            w.writerows(rows)
        first_day = rows[0][0] if rows else "n/a"
        last_day = rows[-1][0] if rows else "n/a"
        print(f"  {len(rows)} bars, {first_day} -> {last_day}  -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
