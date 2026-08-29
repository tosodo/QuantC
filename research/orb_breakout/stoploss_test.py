#!/usr/bin/env python3
"""
stoploss_test.py - pre-registered test of adding a hard stop-loss to the
already-validated long-side 9:30 ET ORB signal (NQ/ES). See
STOPLOSS_HYPOTHESIS.md in this folder - the plan locked before this was run.

Entry: unchanged from orb_test.py - first 1-minute bar (from 09:45 ET) whose
close is above the 09:30-09:44 ET opening range high, provided that happens
before any close below the range low that same day (long side only; the
short side was already rejected in RESULTS.md).

Stop-loss under test: the OPPOSITE side of the same opening range (the range
low, for a long). Walked forward bar by bar from the entry bar; if any bar's
LOW touches or crosses the stop before the session close, the trade exits
there. Otherwise it exits at the session close, exactly as already validated.
No target - this tests a stop only, matching the "still holds to close
unless stopped" framing in STOPLOSS_HYPOTHESIS.md.

R unit here = raw price move / opening-range width (NOT the volatility-
normalized R used in orb_test.py - see STOPLOSS_HYPOTHESIS.md for why). The
no-stop comparison column is recomputed in this SAME unit for a fair
side-by-side, so it will not numerically match orb_test.py's own table.

Pessimism: decisions on closed bars only. A bar's low is checked for the
stop; entry price is the signal bar's own close (already known). No target
exists, so there is no ambiguous-bar case to resolve.

Usage
    python3 stoploss_test.py                # in-sample (default)
    python3 stoploss_test.py --sample out    # held-back slice, look ONCE
    python3 stoploss_test.py --dump-r PATH   # pooled NQ+ES with-stop R, for ruin.py
"""

import argparse
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, RANGE_START, RANGE_END_EXCL, SESSION_CLOSE, INSTRUMENTS


def build_stop_trades(df, cost_points=None):
    """Long-side only. Returns list of dicts: date, R0_close, R0_stop,
    Rc_close, Rc_stop, stopped (bool). *_close = exit-at-session-close
    (no-stop baseline, recomputed in range-width units). *_stop = exit at
    stop-loss if hit, else same as close."""
    out = []
    stats = {"total_days": 0, "incomplete_range_days": 0, "no_long_signal_days": 0,
              "trade_days": 0, "stopped_out": 0}

    for date, day in df.groupby("date_et", sort=True):
        stats["total_days"] += 1
        rng = day[(day["time_et"] >= RANGE_START) & (day["time_et"] < RANGE_END_EXCL)]
        if len(rng) < 15:
            stats["incomplete_range_days"] += 1
            continue
        range_high = rng["high"].max()
        range_low = rng["low"].min()
        r = range_high - range_low
        if r <= 0:
            stats["incomplete_range_days"] += 1
            continue

        scan = day[day["time_et"] >= RANGE_END_EXCL]
        if scan.empty:
            stats["no_long_signal_days"] += 1
            continue

        long_hit = scan[scan["close"] > range_high]
        short_hit = scan[scan["close"] < range_low]
        if long_hit.empty:
            stats["no_long_signal_days"] += 1
            continue
        first_long_ts = long_hit["ts_event"].min()
        if not short_hit.empty and short_hit["ts_event"].min() < first_long_ts:
            # short signal came first this day - not a long trade, skip
            # (matches orb_test.py's "first occurrence only" rule)
            stats["no_long_signal_days"] += 1
            continue

        entry_price = float(day.loc[day["ts_event"] == first_long_ts, "close"].iloc[0])
        forward = day[day["ts_event"] >= first_long_ts]
        if len(forward) < 2:
            continue

        exit_row = day.iloc[-1]
        close_exit_price = float(exit_row["close"])

        # Walk bars strictly after the entry bar, checking for a stop touch
        # on each bar's low before the session close.
        stopped = False
        stop_exit_price = close_exit_price
        for _, b in forward.iloc[1:].iterrows():
            if b["low"] <= range_low:
                stopped = True
                stop_exit_price = range_low  # filled at the stop level
                break

        half_cost = (cost_points / 2.0) if cost_points is not None else 0.0
        entry_c = entry_price + half_cost

        def r_of(exit_px, is_stop):
            exit_c = exit_px - half_cost
            raw = exit_c - entry_c
            return raw / r

        out.append({
            "date": str(date),
            "R0_close": (close_exit_price - entry_price) / r,
            "R0_stop": ((stop_exit_price - entry_price) / r) if stopped else ((close_exit_price - entry_price) / r),
            "Rc_close": r_of(close_exit_price, False),
            "Rc_stop": r_of(stop_exit_price, stopped) if stopped else r_of(close_exit_price, False),
            "stopped": stopped,
        })
        stats["trade_days"] += 1
        if stopped:
            stats["stopped_out"] += 1

    return out, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"), default="free")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in")
    ap.add_argument("--dump-r", default=None,
                     help="write pooled NQ+ES with-stop, cost-adjusted R multiples "
                          "(one per line) for ruin.py --r-file")
    args = ap.parse_args()

    print("=" * 92)
    print("  STOP-LOSS OVERLAY TEST - opposite side of opening range (long side only)")
    print("  (see STOPLOSS_HYPOTHESIS.md - plan locked before this was run)")
    print("  R = raw price move / opening-range width (NOT orb_test.py's vol-normalized R)")
    print("=" * 92)

    only = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]  # long side only tested on NQ+ES per pre-reg
    dfs = {}
    for label, path in only:
        print(f"\nLoading {label} ...")
        dfs[label] = load(path)

    primary_label = only[0][0]
    primary0, _ = build_stop_trades(dfs[primary_label])
    cutoff_date = smr.split_dates([s["date"] for s in primary0])

    if args.sample == "in":
        sample_note = f"IN-SAMPLE (through {cutoff_date})"
    elif args.sample == "out":
        sample_note = f"*** OUT-OF-SAMPLE (after {cutoff_date}) - LOOK ONCE ***"
    else:
        sample_note = "FULL HISTORY"
    print(f"\nSample: {sample_note}\n")

    pooled_stop_c = []
    for label, _ in only:
        df = dfs[label]
        cost_pts = smr.REAL_COST_POINTS[label][args.real_cost_tier]
        sig0, stats = build_stop_trades(df)
        sigc, _ = build_stop_trades(df, cost_points=cost_pts)
        sig0f = smr.filter_sample(sig0, cutoff_date, args.sample)
        sigcf = smr.filter_sample(sigc, cutoff_date, args.sample)

        print(f"--- {label} ---")
        print(f"  Trading days: {stats['total_days']}  |  long trade days: {stats['trade_days']}  "
              f"|  stopped out: {stats['stopped_out']} ({100*stats['stopped_out']/max(1,stats['trade_days']):.1f}%)")

        r0_close = [s["R0_close"] for s in sig0f]
        r0_stop = [s["R0_stop"] for s in sig0f]
        rc_close = [s["Rc_close"] for s in sigcf]
        rc_stop = [s["Rc_stop"] for s in sigcf]

        smr.report(label, r0_close, "no-stop, exit@close (zero-cost)")
        smr.report(label, r0_stop, "WITH STOP (zero-cost)")
        smr.report(label, rc_close, f"no-stop, exit@close (real-{args.real_cost_tier})")
        smr.report(label, rc_stop, f"WITH STOP (real-{args.real_cost_tier})")

        if rc_close:
            worst_no_stop = min(rc_close)
            worst_stop = min(rc_stop)
            print(f"  Worst single trade: no-stop={worst_no_stop:+.3f}R  with-stop={worst_stop:+.3f}R")
        print()

        pooled_stop_c.extend(rc_stop)

    print("=" * 92)
    print("  NOT MEASURED / caveats:")
    print("   - Fill assumed exactly at the stop price (range_low) - real slippage through")
    print("     a fast-moving stop level is not modeled here; a real fill would likely be worse.")
    print("   - Only NQ+ES tested (short side and YM out of scope per STOPLOSS_HYPOTHESIS.md).")
    if args.sample == "in":
        print("   - IN-SAMPLE slice only. --sample out has not been looked at.")
    print("=" * 92)

    if args.dump_r:
        with open(args.dump_r, "w") as fh:
            fh.write("# pooled NQ+ES long-side, WITH STOP, real-{} cost-adjusted R "
                      "(range-width units), full history\n".format(args.real_cost_tier))
            for r in pooled_stop_c:
                fh.write(f"{r:.6f}\n")
        print(f"\nWrote {len(pooled_stop_c)} pooled with-stop R multiples -> {args.dump_r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
