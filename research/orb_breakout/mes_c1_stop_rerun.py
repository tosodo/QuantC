#!/usr/bin/env python3
"""
mes_c1_stop_rerun.py - re-runs mes_final_run.py's exact methodology with the
C1 dollar-capped stop (orb_long_ghost_DRAFT_mes_v2.pine, updated 2026-09-03)
substituted for the original 99th-percentile MAE stop, on the FULL 5-year
history - not the ~8-day window TradingView's Strategy Tester was limited to.

Why this file exists: the DRAFT script's stop used to be a fixed 124.75-point
constant (the 99th-percentile Maximum-Adverse-Excursion measured in
wide_stop_test.py), worth $623.77 on 1 MES - about 31% of the LucidPro eval's
real $1,800 daily loss limit in a single trade. C1 replaced that with a
dollar-risk cap: stop_points = maxRiskDollars / (qty * point_value). With the
chosen default (maxRiskDollars=$270, qty=1, MES point value=$5) that is a
FIXED 54.0-point stop - tighter than the old 124.75pt stop, landing just
under MES's own measured 90th-percentile MAE (64.70 pts / $323.50). The open
question flagged when C1 shipped: that tighter distance had never been
backtested for trigger frequency or survivability - only the 99th-percentile
distance had (64.41% pass rate, 1.06% trigger rate). This file answers that,
using the exact same data, cost model, and firm rules as mes_final_run.py so
the two are directly comparable - not a new methodology.

Everything except the stop distance is reused verbatim by importing from
mes_final_run.py (same trade-building, same resolve_exit priority order,
same REAL_COST_POINTS free-tier cost model, same LucidPro firm-rule
parameters, same ruin.py invocation) - this file adds nothing new except
computing a second stop distance and running the same config sweep with it,
printed alongside the original 99th-percentile numbers for direct comparison.

Usage
    python3 mes_c1_stop_rerun.py
"""

import sys

from mes_final_run import (
    ES_LABEL, ES_PATH, PV_MES, TIME_EXIT_MINUTES,
    build_mes_trades, in_session_window, r_series_for, ruin_py_pass_pct,
    local_simulate_mean_days,
)
from orb_test import load
import screen_mean_reversion as smr

C1_MAX_RISK_DOLLARS = 270.0   # first-tried value, backtested and superseded - see module
                              # docstring. orb_long_ghost_DRAFT_mes_v2.pine's maxRiskDollars
                              # default is now $625 (~125 pts), set after THIS file's own
                              # result showed $270 (54 pts) measurably hurt survivability.
                              # Left at $270 here so this file keeps reproducing the exact
                              # comparison that motivated the change, rather than comparing
                              # a value against a near-copy of itself.


def run_config_set(label_prefix, trades, window_trades, n_dropped, half_cost, stop_points, es_tick):
    configs = [
        (f"2. MES alone, {label_prefix} price stop ONLY", trades, stop_points, None, 0.0),
        (f"4. MES alone, COMBINED {label_prefix} stop + 90-min time exit (no slippage)",
         trades, stop_points, TIME_EXIT_MINUTES, 0.0),
        (f"5. Config 4 + 09:45-11:00 ET entry window only "
         f"({n_dropped}/{len(trades)} trades outside window dropped)",
         window_trades, stop_points, TIME_EXIT_MINUTES, 0.0),
        (f"6. Config 4 + 1 tick (0.25 pt) adverse slippage on stop/time-exit fills",
         trades, stop_points, TIME_EXIT_MINUTES, 1 * es_tick),
        (f"7. Config 4 + 2 ticks (0.50 pt) adverse slippage on stop/time-exit fills",
         trades, stop_points, TIME_EXIT_MINUTES, 2 * es_tick),
    ]
    for name, trade_set, sp, tm, slip in configs:
        r_series, reasons = r_series_for(trade_set, half_cost, sp, tm, slip)
        pass_pct, ruin_pct, median_days_ruinpy = ruin_py_pass_pct(r_series)
        _, mean_days, median_days_local = local_simulate_mean_days(r_series)
        n = len(r_series)
        print(f"\n  {name}")
        print(f"    stop distance         = {stop_points:.2f} pts = ${stop_points * PV_MES:.2f} on 1 MES")
        print(f"    exits: stop={reasons['stop']:3d} ({100*reasons['stop']/n:4.1f}%)  "
              f"time={reasons['time']:3d} ({100*reasons['time']/n:4.1f}%)  "
              f"close={reasons['close']:3d} ({100*reasons['close']/n:4.1f}%)")
        print(f"    PASS rate            = {pass_pct:.2f}%")
        print(f"    Probability of ruin  = {ruin_pct:.2f}%  (fails total-drawdown before target)")
        if mean_days is not None:
            print(f"    Trades to target     : median(ruin.py)={median_days_ruinpy}  "
                  f"median(local)={median_days_local}  mean(local)={mean_days:.1f}")
        else:
            print("    Trades to target     : n/a (no passing sims)")


def main():
    df = load(ES_PATH)
    cost_points = smr.REAL_COST_POINTS[ES_LABEL]["free"]
    half_cost = cost_points / 2.0
    trades = build_mes_trades(df)

    mae_pts = []
    for t in trades:
        worst_low = t["after_entry"]["low"].min() if len(t["after_entry"]) else t["entry_price"]
        mae_pts.append(max(0.0, t["entry_price"] - float(worst_low)))
    stop_99 = smr.percentile(sorted(mae_pts), 0.99)
    stop_c1 = C1_MAX_RISK_DOLLARS / PV_MES

    window_trades = [t for t in trades if in_session_window(t)]
    n_dropped = len(trades) - len(window_trades)
    ES_TICK = 0.25

    print("=" * 100)
    print("  MES C1-STOP RE-RUN - same methodology as mes_final_run.py, two stops compared")
    print(f"  n={len(trades)} long trades, full 5-year history")
    print(f"  OLD stop (99th pctile MAE, wide_stop_test.py) = {stop_99:.2f} pts = "
          f"${stop_99 * PV_MES:.2f} on 1 MES")
    print(f"  NEW stop (C1 dollar cap, ${C1_MAX_RISK_DOLLARS:.0f} / ${PV_MES:.0f} per pt) = "
          f"{stop_c1:.2f} pts = ${stop_c1 * PV_MES:.2f} on 1 MES")
    print("=" * 100)

    print("\n" + "-" * 100)
    print("  BASELINE (config 1, no price stop at all - unaffected by C1, printed once for reference)")
    print("-" * 100)
    r_series, reasons = r_series_for(trades, half_cost, None, None, 0.0)
    pass_pct, ruin_pct, median_days_ruinpy = ruin_py_pass_pct(r_series)
    _, mean_days, median_days_local = local_simulate_mean_days(r_series)
    n = len(r_series)
    print(f"    exits: stop={reasons['stop']:3d} ({100*reasons['stop']/n:4.1f}%)  "
          f"time={reasons['time']:3d} ({100*reasons['time']/n:4.1f}%)  "
          f"close={reasons['close']:3d} ({100*reasons['close']/n:4.1f}%)")
    print(f"    PASS rate            = {pass_pct:.2f}%")
    print(f"    Probability of ruin  = {ruin_pct:.2f}%")
    if mean_days is not None:
        print(f"    Trades to target     : median(ruin.py)={median_days_ruinpy}  "
              f"median(local)={median_days_local}  mean(local)={mean_days:.1f}")

    print("\n" + "-" * 100)
    print("  OLD STOP - 99th percentile MAE (mes_final_run.py's original numbers, reconfirmed)")
    print("-" * 100)
    run_config_set("OLD 99th-pctile", trades, window_trades, n_dropped, half_cost, stop_99, ES_TICK)

    print("\n" + "-" * 100)
    print("  NEW STOP - C1 dollar cap (the question this file exists to answer)")
    print("-" * 100)
    run_config_set("NEW C1 dollar-cap", trades, window_trades, n_dropped, half_cost, stop_c1, ES_TICK)

    print("\n  NOT MEASURED / caveats (same as mes_final_run.py, repeated here):")
    print("   - 90-min cutoff is measured from each trade's OWN entry time.")
    print("   - The time-exit check happens once (first bar at/after the cutoff).")
    print("   - Local mean/median-days simulation cross-checked against ruin.py's own median.")
    print("   - MES measured completely alone, same as everywhere else in this project.")
    print("   - The C1 stop distance (54.0 pts) was chosen from a dollar-risk fraction of the")
    print("     LucidPro account's $1,800 daily loss limit, NOT from this instrument's own MAE")
    print("     distribution - unlike the 99th-percentile stop, it was not designed to trigger")
    print("     at any particular rate. Whatever trigger rate shows up above is a side effect")
    print("     of the dollar cap, not something pre-registered or targeted.")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main() or 0)
