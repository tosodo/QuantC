#!/usr/bin/env python3
"""
fetch_data_cash.py - pull DAILY cash-index bars from Yahoo Finance's public
chart API, for the deep-history re-test of the 20d-quintile mean-reversion
hypothesis (see screen_mean_reversion_deep.py / RESULTS_DEEP.md).

Why a separate script from fetch_data.py
    fetch_data.py pulls continuous FUTURES (NQ=F/ES=F/YM=F), which only run
    back to the mid-2000s on Yahoo, using range="25y" (range="max" was
    verified there to silently demote long series to MONTHLY bars).

    This script pulls CASH INDICES (^GSPC/^IXIC/^RUT) instead, which Yahoo
    carries back to 1970/1971/1987. For these symbols, a prior agent
    verified that `period1=0&interval=1d` (i.e. "give me everything from
    the Unix epoch forward, daily") returns TRUE DAILY bars for the full
    history - unlike range="max", which is the same monthly-demotion trap
    documented in fetch_data.py. period1=0 is used here deliberately,
    range=max/25y is NOT used.

What this is NOT
    A back-adjusted, dividend-adjusted, or survivorship-bias-free feed.
    These are raw cash-index levels (close = index level, not total return).
    No adjustment is needed for a price-return index level itself, but note
    this is not the same series as e.g. a futures-implied or total-return
    index.

Output
    One CSV per symbol in data/, columns: date,open,high,low,close
    (same format as fetch_data.py's output, so screen_mean_reversion.py's
    load() function reads these files unchanged).
"""

import csv
import datetime
import json
import sys
import urllib.parse
import urllib.request

SYMBOLS = {
    "GSPC": "^GSPC",   # S&P 500 cash index
    "IXIC": "^IXIC",   # Nasdaq Composite cash index
    "RUT": "^RUT",     # Russell 2000 cash index
}


def fetch(symbol, interval="1d"):
    # period1=0 -> Unix epoch (1970-01-01). period2 must be passed EXPLICITLY
    # as "now" - omitting it makes Yahoo default period2 to -1 and the API
    # returns HTTP 400 ("start date cannot be after end date"), discovered
    # while building this script. With period1=0 and an explicit period2,
    # verified (this task) to return true daily bars back to each series'
    # actual inception (^GSPC -> 1970-01-02, 14278 rows), NOT monthly-demoted
    # like range=max/range=25y can be for some symbols (see fetch_data.py).
    period2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol, safe='')}"
           f"?period1=0&period2={period2}&interval={interval}")
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
    # De-dup same-day entries.
    dedup = {}
    for row in rows:
        dedup[row[0]] = row
    return [dedup[k] for k in sorted(dedup)]


def _gap_check(rows, label):
    """Sanity check: median gap between consecutive bars should be ~1-3
    calendar days (daily bars), not ~30 (monthly bars). Print, don't hide."""
    if len(rows) < 3:
        return
    dates = [datetime.date.fromisoformat(r[0]) for r in rows[-260:]]  # last ~1y
    gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
    gaps.sort()
    median_gap = gaps[len(gaps) // 2]
    print(f"  [{label}] median gap over last {len(gaps)} bars: {median_gap} calendar day(s)"
          f"{'  WARNING: looks like NOT daily bars!' if median_gap > 5 else ''}")


def main():
    out_dir = "data"
    for label, symbol in SYMBOLS.items():
        print(f"Fetching {symbol} ({label}) daily bars, period1=0 ...")
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
        _gap_check(rows, label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
