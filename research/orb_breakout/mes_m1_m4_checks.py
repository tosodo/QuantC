#!/usr/bin/env python3
"""
mes_m1_m4_checks.py - QC report M1 and M4, each tested once against the
current validated mechanism (stop=$625/125pts, 90-min time-exit, no take-
profit - per the C1 re-run and the H3 take-profit sweep) before touching
the live DRAFT script. One variable changed at a time per test, same cost
model and firm rules as every prior file in this project.

M1 - "the time-exit is a single knife-edge checkpoint": current code checks
underwater status ONCE, at the first bar >=90min after entry, and never
re-checks even if the trade later goes underwater after being green at that
one moment. Tests CHECK-ONCE (current, reused from mes_final_run.py) against
CHECK-EVERY-BAR (re-evaluate underwater status on every bar from minute 90
onward, exit at the first one that's underwater).

M4 - "unfiltered gap/extension entries": nothing today caps how far above
rangeHigh the breakout close can be. Rather than introduce a new indicator
(ATR) not used anywhere else in this project, this uses the same structural
unit the strategy is already built around: the opening range's own width
(rangeHigh - rangeLow), which STOPLOSS_HYPOTHESIS.md's already-rejected stop
also used as its distance unit. Tests requiring the breakout NOT extend more
than N range-widths beyond rangeHigh, for a pre-registered N in
{1.0, 1.5, 2.0}, against the unfiltered baseline.

Trade-building duplicates build_mes_trades()'s day-grouping logic (from
mes_final_run.py) rather than modifying it, specifically to also capture
range_high/range_low per trade (not exposed by the original function) -
mes_final_run.py itself is left untouched, same convention as
mes_c1_stop_rerun.py and mes_takeprofit_sweep.py.

Usage
    python3 mes_m1_m4_checks.py
"""

import sys

import pandas as pd

from mes_final_run import (
    ES_LABEL, ES_PATH, PV_MES, TIME_EXIT_MINUTES,
    RANGE_START, RANGE_END_EXCL,
    resolve_exit, r_series_for, ruin_py_pass_pct, local_simulate_mean_days,
)
from orb_test import load
import screen_mean_reversion as smr

STOP_DOLLARS = 625.0
STOP_POINTS = STOP_DOLLARS / PV_MES   # 125.0 pts
M4_MULTIPLES = [1.0, 1.5, 2.0]         # pre-registered, tested once each


def build_mes_trades_with_range(df):
    """Same entry rule and fields as mes_final_run.py's build_mes_trades,
    plus range_high/range_low/range_width per trade for M4's filter."""
    out = []
    for date, day in df.groupby("date_et", sort=True):
        rng = day[(day["time_et"] >= RANGE_START) & (day["time_et"] < RANGE_END_EXCL)]
        if len(rng) < 15:
            continue
        range_high = rng["high"].max()
        range_low = rng["low"].min()

        scan = day[day["time_et"] >= RANGE_END_EXCL]
        if scan.empty:
            continue
        long_hit = scan[scan["close"] > range_high]
        short_hit = scan[scan["close"] < range_low]
        if long_hit.empty:
            continue
        first_long_ts = long_hit["ts_event"].min()
        if not short_hit.empty and short_hit["ts_event"].min() < first_long_ts:
            continue

        entry_price = float(day.loc[day["ts_event"] == first_long_ts, "close"].iloc[0])
        forward = day[day["ts_event"] >= first_long_ts]
        if len(forward) < 2:
            continue
        close_exit_price = float(day.iloc[-1]["close"])
        after_entry = forward.iloc[1:]

        out.append({
            "date": str(date),
            "entry_ts": first_long_ts,
            "entry_price": entry_price,
            "close_exit_price": close_exit_price,
            "after_entry": after_entry,
            "range_high": float(range_high),
            "range_low": float(range_low),
            "range_width": float(range_high - range_low),
        })
    return out


def resolve_exit_recheck(t, half_cost, stop_points, time_exit_minutes):
    """M1 variant: re-evaluates underwater status on EVERY bar from the
    time-exit cutoff onward (not just the first one), exiting at the first
    bar found underwater. Everything else identical to mes_final_run.py's
    resolve_exit."""
    entry_price = t["entry_price"]
    entry_c = entry_price + half_cost
    stop_level = entry_price - stop_points
    time_cutoff = t["entry_ts"] + pd.Timedelta(minutes=time_exit_minutes)

    for _, b in t["after_entry"].iterrows():
        if b["low"] <= stop_level:
            return stop_level, "stop"
        if b["ts_event"] >= time_cutoff and (b["close"] - half_cost) < entry_c:
            return float(b["close"]), "time"
    return t["close_exit_price"], "close"


def r_series_for_recheck(trades, half_cost, stop_points, time_exit_minutes):
    r_series, reasons = [], {"stop": 0, "time": 0, "close": 0}
    for t in trades:
        exit_px, reason = resolve_exit_recheck(t, half_cost, stop_points, time_exit_minutes)
        entry_c = t["entry_price"] + half_cost
        exit_c = exit_px - half_cost
        dollar_pnl = (exit_c - entry_c) * PV_MES
        r_series.append(dollar_pnl / 1000.0)
        reasons[reason] += 1
    return r_series, reasons


def report(name, r_series, reasons):
    pass_pct, ruin_pct, median_ruinpy = ruin_py_pass_pct(r_series)
    _, mean_days, median_local = local_simulate_mean_days(r_series)
    n = len(r_series)
    print(f"\n  {name}")
    print(f"    n={n} trades")
    print(f"    exits: " + "  ".join(f"{k}={v:3d} ({100*v/n:4.1f}%)" for k, v in reasons.items()))
    print(f"    PASS rate            = {pass_pct:.2f}%")
    print(f"    Probability of ruin  = {ruin_pct:.2f}%")
    if mean_days is not None:
        print(f"    Trades to target     : median(ruin.py)={median_ruinpy}  "
              f"median(local)={median_local}  mean(local)={mean_days:.1f}")
    else:
        print("    Trades to target     : n/a (no passing sims)")


def main():
    df = load(ES_PATH)
    cost_points = smr.REAL_COST_POINTS[ES_LABEL]["free"]
    half_cost = cost_points / 2.0
    trades = build_mes_trades_with_range(df)

    print("=" * 100)
    print("  M1 + M4 CHECKS - one variable changed at a time vs the current validated mechanism")
    print(f"  n={len(trades)} long trades, full 5-year history, stop={STOP_POINTS:.1f}pts (${STOP_DOLLARS:.0f})")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("  M1 - time-exit: CHECK-ONCE (current) vs CHECK-EVERY-BAR")
    print("-" * 100)
    r_series, reasons = r_series_for(trades, half_cost, STOP_POINTS, TIME_EXIT_MINUTES, 0.0)
    report("CHECK-ONCE (current mes_final_run.py behavior)", r_series, reasons)
    r_series, reasons = r_series_for_recheck(trades, half_cost, STOP_POINTS, TIME_EXIT_MINUTES)
    report("CHECK-EVERY-BAR (M1's proposed fix)", r_series, reasons)

    print("\n" + "-" * 100)
    print("  M4 - max breakout extension beyond rangeHigh, in opening-range widths")
    print("-" * 100)
    r_series, reasons = r_series_for(trades, half_cost, STOP_POINTS, TIME_EXIT_MINUTES, 0.0)
    report(f"NO FILTER (current, baseline) - n={len(trades)}", r_series, reasons)
    for mult in M4_MULTIPLES:
        filtered = [t for t in trades
                    if (t["entry_price"] - t["range_high"]) <= mult * t["range_width"]]
        n_dropped = len(trades) - len(filtered)
        r_series, reasons = r_series_for(filtered, half_cost, STOP_POINTS, TIME_EXIT_MINUTES, 0.0)
        report(f"max extension = {mult:.1f}x OR-width ({n_dropped}/{len(trades)} trades dropped)",
               r_series, reasons)

    print("\n  NOT MEASURED / caveats:")
    print("   - M1's CHECK-EVERY-BAR only changes trades whose underwater status flips between")
    print("     the 90-min mark and session close - most trades are unaffected either way.")
    print("   - M4 uses opening-range width as the extension unit (not ATR) - consistent with")
    print("     STOPLOSS_HYPOTHESIS.md's already-rejected stop, which used the same unit.")
    print("   - Both tested only against the current $625/125pt stop, no take-profit, no")
    print("     slippage - not re-run against every prior config combination.")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main() or 0)
