#!/usr/bin/env python3
"""
mes_takeprofit_sweep.py - QC report H3 finding: orb_long_ghost_DRAFT_mes_v2.pine
has no take-profit at all (exits are only the stop, the 90-min underwater
time-exit, and the scheduled session close), so reward:risk per trade is
undefined. This project has never tested a take-profit level for this
mechanism before (checked: no take-profit/target/R-multiple research exists
anywhere in this folder) - this file is that first test.

Pre-registered candidates, tested ONCE each, not iteratively optimized:
R-multiples 1.0, 1.5, 2.0, 3.0 relative to the CURRENT stop distance
(maxRiskDollars=$625 -> 125.0 pts on 1 MES, per the C1 re-run). Chosen as a
small, sensible spread rather than a fitted/searched value - the same
discipline wide_stop_test.py and the C1 re-run already used (test a short
pre-registered list, report all of them, do not cherry-pick the winner by
trying many and keeping the best).

Exit priority per trade, walking 1-min bars forward from entry (same
after_entry data mes_final_run.py already builds):
    1. price stop (125.0 pts, same distance the live DRAFT now uses)
       - if a bar's LOW touches it first, exit there.
    2. take-profit (entry + R x stop distance) - if a bar's HIGH touches it
       first, exit there. If a single bar's range would touch BOTH the stop
       and the target (a wide bar), the stop wins - the conservative
       assumption, consistent with how this project has always resolved
       same-bar ambiguity elsewhere.
    3. otherwise, at entry_ts + 90min, the existing underwater time-exit
       check (unchanged from mes_final_run.py).
    4. otherwise, hold to session close (unchanged baseline exit).

Take-profit is modeled as a resting LIMIT order (fills exactly at the
target price, no slippage) - this is NOT the same fill-quality assumption
as the stop and time-exit (market orders, slipped when requested). Flagged
explicitly rather than silently applying one slippage model to both order
types.

Cost model, contract, and firm-rule parameters unchanged from every prior
file in this project (REAL_COST_POINTS free tier, half-cost per leg, MES
$5/pt, LucidPro 3% trailing DD / 6% target / no daily limit / 1 trade/day).

Usage
    python3 mes_takeprofit_sweep.py
"""

import sys

from mes_final_run import (
    ES_LABEL, ES_PATH, PV_MES, TIME_EXIT_MINUTES,
    build_mes_trades, ruin_py_pass_pct, local_simulate_mean_days,
)
from orb_test import load
import screen_mean_reversion as smr

STOP_DOLLARS = 625.0          # current live DRAFT default (post C1 re-run correction)
STOP_POINTS = STOP_DOLLARS / PV_MES   # 125.0 pts
R_MULTIPLES = [1.0, 1.5, 2.0, 3.0]    # pre-registered candidates, tested once each


def resolve_exit_with_tp(t, half_cost, stop_points, tp_points, time_exit_minutes):
    """Same priority/logic as mes_final_run.py's resolve_exit, with a
    take-profit check inserted between the stop and the time-exit. No
    slippage parameter: stop/time fills use the project's existing
    zero-slippage baseline convention here (a slipped variant can be added
    the same way mes_final_run.py's configs 6-7 did, once a TP level is
    actually chosen); the TP fill itself is a resting limit order (no
    slippage modeled, by design)."""
    entry_price = t["entry_price"]
    entry_c = entry_price + half_cost
    stop_level = entry_price - stop_points
    tp_level = entry_price + tp_points
    time_cutoff = t["entry_ts"] + __import__("pandas").Timedelta(minutes=time_exit_minutes)

    time_checked = False
    for _, b in t["after_entry"].iterrows():
        hit_stop = b["low"] <= stop_level
        hit_tp = b["high"] >= tp_level
        if hit_stop:
            return stop_level, "stop"
        if hit_tp:
            return tp_level, "tp"
        if not time_checked and b["ts_event"] >= time_cutoff:
            time_checked = True
            if (b["close"] - half_cost) < entry_c:
                return float(b["close"]), "time"
    return t["close_exit_price"], "close"


def r_series_for_tp(trades, half_cost, stop_points, tp_points, time_exit_minutes):
    r_series, reasons = [], {"stop": 0, "tp": 0, "time": 0, "close": 0}
    for t in trades:
        exit_px, reason = resolve_exit_with_tp(t, half_cost, stop_points, tp_points, time_exit_minutes)
        entry_c = t["entry_price"] + half_cost
        exit_c = exit_px - half_cost
        dollar_pnl = (exit_c - entry_c) * PV_MES
        r_series.append(dollar_pnl / 1000.0)
        reasons[reason] += 1
    return r_series, reasons


def main():
    df = load(ES_PATH)
    cost_points = smr.REAL_COST_POINTS[ES_LABEL]["free"]
    half_cost = cost_points / 2.0
    trades = build_mes_trades(df)

    print("=" * 100)
    print("  MES TAKE-PROFIT SWEEP - H3: no take-profit exists today, this is the first test")
    print(f"  n={len(trades)} long trades, full 5-year history")
    print(f"  Stop distance held fixed at {STOP_POINTS:.1f} pts (${STOP_DOLLARS:.0f} on 1 MES, current C1 value)")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("  BASELINE - no take-profit (current live mechanism: stop + 90-min time-exit only)")
    print("-" * 100)
    from mes_final_run import resolve_exit, r_series_for
    r_series, reasons = r_series_for(trades, half_cost, STOP_POINTS, TIME_EXIT_MINUTES, 0.0)
    pass_pct, ruin_pct, median_ruinpy = ruin_py_pass_pct(r_series)
    _, mean_days, median_local = local_simulate_mean_days(r_series)
    n = len(r_series)
    print(f"    exits: stop={reasons['stop']:3d} ({100*reasons['stop']/n:4.1f}%)  "
          f"time={reasons['time']:3d} ({100*reasons['time']/n:4.1f}%)  "
          f"close={reasons['close']:3d} ({100*reasons['close']/n:4.1f}%)")
    print(f"    PASS rate            = {pass_pct:.2f}%")
    print(f"    Probability of ruin  = {ruin_pct:.2f}%")
    if mean_days is not None:
        print(f"    Trades to target     : median(ruin.py)={median_ruinpy}  "
              f"median(local)={median_local}  mean(local)={mean_days:.1f}")

    for r in R_MULTIPLES:
        tp_points = STOP_POINTS * r
        print("\n" + "-" * 100)
        print(f"  R = {r:.1f}  (take-profit = {tp_points:.1f} pts = ${tp_points*PV_MES:.2f} on 1 MES, "
              f"entry + {tp_points:.1f})")
        print("-" * 100)
        r_series, reasons = r_series_for_tp(trades, half_cost, STOP_POINTS, tp_points, TIME_EXIT_MINUTES)
        pass_pct, ruin_pct, median_ruinpy = ruin_py_pass_pct(r_series)
        _, mean_days, median_local = local_simulate_mean_days(r_series)
        n = len(r_series)
        print(f"    exits: stop={reasons['stop']:3d} ({100*reasons['stop']/n:4.1f}%)  "
              f"tp={reasons['tp']:3d} ({100*reasons['tp']/n:4.1f}%)  "
              f"time={reasons['time']:3d} ({100*reasons['time']/n:4.1f}%)  "
              f"close={reasons['close']:3d} ({100*reasons['close']/n:4.1f}%)")
        print(f"    PASS rate            = {pass_pct:.2f}%")
        print(f"    Probability of ruin  = {ruin_pct:.2f}%")
        if mean_days is not None:
            print(f"    Trades to target     : median(ruin.py)={median_ruinpy}  "
                  f"median(local)={median_local}  mean(local)={mean_days:.1f}")
        else:
            print("    Trades to target     : n/a (no passing sims)")

    print("\n  NOT MEASURED / caveats:")
    print("   - Take-profit modeled as a resting limit order: exact fill at the target price,")
    print("     no slippage. Stop and time-exit keep this project's existing zero-slippage")
    print("     baseline here too - a slipped variant was not run for this first pass.")
    print("   - Same-bar stop+TP conflicts resolve to the stop (conservative assumption).")
    print("   - Only long side tested, matching the already-validated mechanism's scope.")
    print("   - MES measured completely alone, same as everywhere else in this project.")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main() or 0)
