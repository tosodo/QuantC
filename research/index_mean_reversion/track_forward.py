#!/usr/bin/env python3
"""
track_forward.py - live forward-paper-test log for the pre-registered
20d-quintile index mean-reversion hypothesis (see screen_mean_reversion.py).

Purpose
    The backtest already used every day of history through 2026-08-19 - there
    is no more historical data left to hold back. The only way to get MORE
    evidence now is to let real time pass and watch the exact same
    pre-registered rule fire on brand-new days that no previous test has ever
    looked at. This script IS that: each run re-checks NQ/ES/YM for a new
    signal, logs it the moment it fires (side + date, nothing added after the
    fact), and later fills in the realised result once enough trading days
    have passed.

    Zero money, zero account, zero broker connection. This produces evidence;
    it does not place a trade.

Rule under test (identical to screen_mean_reversion.py, not redefined here)
    BOTTOM quintile of trailing-20d return (vs its own trailing 504-day
    distribution) -> predicts next 20d return positive (long).
    TOP quintile -> predicts next 20d return negative (short).

Cutoff (no reusing data any test has already inspected)
    Only signals dated AFTER 2026-08-19 (the last date already used in
    RESULTS.md) are logged here. Anything on or before that date was already
    looked at and does not count again.

Cost
    Real, MEASURED Tradovate "free" plan round-turn cost (most conservative -
    no plan has been purchased yet), same REAL_COST_POINTS table as
    screen_mean_reversion.py, applied per-trade at that trade's own entry
    price.

Usage
    python3 track_forward.py            # refetch data, update the log, print status
    python3 track_forward.py --no-fetch # use whatever's already in data/ (offline)
"""

import argparse
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_data
import screen_mean_reversion as smr

SETUP_DATE = "2026-08-19"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "forward_log.csv")
COST_TIER = "free"

INSTRUMENTS = [
    ("NQ (Nasdaq, primary)", "NQ", "data/NQ.csv"),
    ("ES (S&P500, repl.)", "ES", "data/ES.csv"),
    ("YM (Dow, repl.)", "YM", "data/YM.csv"),
]


def detect_all_signals(dates, opens, closes):
    """Same classification rule as smr.build_signals, but does not require
    the forward window to already exist - returns every eligible decision
    day through the most recent bar, so today's signal is returned even
    though its 20-day outcome isn't knowable yet."""
    n = len(closes)
    logp = [math.log(c) for c in closes]
    r20 = [None] * n
    for t in range(smr.LOOKBACK_R20, n):
        r20[t] = logp[t] - logp[t - smr.LOOKBACK_R20]

    out = []
    min_t = smr.LOOKBACK_R20 + smr.LOOKBACK_QUINTILE
    for t in range(min_t, n):
        window = sorted(r20[k] for k in range(t - smr.LOOKBACK_QUINTILE, t))
        p20 = smr.percentile(window, 0.20)
        p80 = smr.percentile(window, 0.80)
        val = r20[t]
        side = None
        if val <= p20:
            side = "bottom"
        elif val >= p80:
            side = "top"
        if side is not None:
            out.append({"t": t, "date": dates[t], "side": side})
    return out


def load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="") as fh:
        return list(csv.DictReader(fh))


def save_log(rows):
    fields = ["signal_date", "instrument", "side", "entry_date", "entry_price",
              "exit_date", "exit_price", "R0", "Rcost", "status"]
    with open(LOG_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def cost_points_for(short_symbol):
    label = next(lbl for lbl, s, _ in INSTRUMENTS if s == short_symbol)
    return smr.REAL_COST_POINTS[label][COST_TIER]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-fetch", action="store_true",
                     help="skip re-downloading data, use what's already in data/")
    args = ap.parse_args()
    os.chdir(HERE)

    if not args.no_fetch:
        print("Fetching latest daily bars ...")
        fetch_data.main()
        print()

    log_rows = load_log()
    existing_keys = {(r["signal_date"], r["instrument"], r["side"]) for r in log_rows}

    new_signals = []
    data_by_inst = {}
    for label, short, path in INSTRUMENTS:
        dates, opens, closes = smr.load(path)
        data_by_inst[short] = (dates, opens, closes)
        for s in detect_all_signals(dates, opens, closes):
            if s["date"] <= SETUP_DATE:
                continue
            key = (s["date"], short, s["side"])
            if key in existing_keys:
                continue
            entry_idx = s["t"] + 1
            has_entry = entry_idx < len(dates)
            row = {
                "signal_date": s["date"], "instrument": short, "side": s["side"],
                "entry_date": dates[entry_idx] if has_entry else "",
                "entry_price": opens[entry_idx] if has_entry else "",
                "exit_date": "", "exit_price": "", "R0": "", "Rcost": "",
                "status": "open" if has_entry else "pending_entry",
            }
            log_rows.append(row)
            new_signals.append(row)

    newly_closed = []
    for row in log_rows:
        if row["status"] not in ("open", "pending_entry"):
            continue
        dates, opens, closes = data_by_inst[row["instrument"]]

        if row["status"] == "pending_entry":
            try:
                t_idx = dates.index(row["signal_date"])
            except ValueError:
                continue
            entry_idx = t_idx + 1
            if entry_idx >= len(dates):
                continue
            row["entry_date"] = dates[entry_idx]
            row["entry_price"] = opens[entry_idx]
            row["status"] = "open"

        entry_idx = dates.index(row["entry_date"])
        exit_idx = entry_idx + smr.FORWARD - 1
        if exit_idx >= len(dates):
            continue

        entry_price = float(row["entry_price"])
        exit_price = closes[exit_idx]
        fwd = math.log(exit_price) - math.log(entry_price)
        daily_rets = [math.log(closes[k + 1]) - math.log(closes[k])
                      for k in range(entry_idx, exit_idx)]
        m = sum(daily_rets) / len(daily_rets)
        var = sum((x - m) ** 2 for x in daily_rets) / max(len(daily_rets) - 1, 1)
        horizon_vol = math.sqrt(var) * math.sqrt(len(daily_rets))

        raw0 = fwd if row["side"] == "bottom" else -fwd
        cost_ret = cost_points_for(row["instrument"]) / entry_price
        rawc = raw0 - cost_ret
        R0 = raw0 / horizon_vol if horizon_vol > 0 else 0.0
        Rc = rawc / horizon_vol if horizon_vol > 0 else 0.0

        row["exit_date"] = exit_idx and dates[exit_idx]
        row["exit_price"] = exit_price
        row["R0"] = f"{R0:.4f}"
        row["Rcost"] = f"{Rc:.4f}"
        row["status"] = "closed"
        newly_closed.append(row)

    save_log(log_rows)

    print("=" * 70)
    print("  FORWARD LIVE TRACKER - index mean-reversion (evidence dated after "
          f"{SETUP_DATE} only)")
    print("=" * 70)

    if new_signals:
        print(f"\n{len(new_signals)} NEW signal(s) fired:")
        for r in new_signals:
            print(f"  {r['signal_date']}  {r['instrument']:3s}  {r['side']:6s}  "
                  f"-> entry {r['entry_date'] or '(next session, not open yet)'}")
    else:
        print("\nNo new signal fired since the last check.")

    if newly_closed:
        print(f"\n{len(newly_closed)} position(s) just closed:")
        for r in newly_closed:
            verdict = "CORRECT" if float(r["Rcost"]) > 0 else "WRONG"
            print(f"  {r['signal_date']}  {r['instrument']:3s}  {r['side']:6s}  "
                  f"R(real-cost)={r['Rcost']:>7s}  {verdict}")

    open_rows = [r for r in log_rows if r["status"] in ("open", "pending_entry")]
    closed_rows = [r for r in log_rows if r["status"] == "closed"]
    print(f"\nRunning total: {len(closed_rows)} closed, {len(open_rows)} still open")
    print(f"Log file: {LOG_PATH}")
    if closed_rows:
        wins = sum(1 for r in closed_rows if float(r["Rcost"]) > 0)
        note = " (too few yet for any statistical read)" if len(closed_rows) < 10 else ""
        print(f"  Closed so far: {wins}/{len(closed_rows)} correct{note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
