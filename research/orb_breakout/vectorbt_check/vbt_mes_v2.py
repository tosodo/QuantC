#!/usr/bin/env python3
"""
vbt_mes_v2.py - independent re-run of the MES v2 ORB backtest (RESULTS.md
section 2.7, mes_final_run.py config 4) on vectorbt's portfolio engine.

Why: a second implementation of the same rules, written from the rule text
rather than by reusing orb_test.py / mes_final_run.py code, so that a bug in
either one shows up as a mismatch. vectorbt does the fills, stop handling,
fees and P&L accounting; this file only builds the entry/exit signal arrays.

Rules replayed (the locked v2 baseline, no slippage):
  - range = 09:30-09:44 ET bars (all 15 must exist); scan from 09:45
  - entry = close of the first bar that closes above the range high, unless a
    bar closed below the range low first (those days are skipped, as in the
    backtest) - one trade per day, long only
  - price stop = entry - STOP points, checked from the bar after entry
  - 90-min check: at the first bar at/after entry + 90 min, exit at its close
    if underwater net of round-trip cost; checked once
  - otherwise exit at the close of the last bar before 16:00 ET
  - cost = REAL_COST_POINTS ES free tier, half per leg; MES = $5/pt

Usage (venv with requirements.txt installed):
  python vbt_mes_v2.py --csv ../data/continuous/ES.csv            # 5-year re-run
  python vbt_mes_v2.py --csv bars.csv --compare                    # + trade-by-trade
                                                                   #   diff vs mes_final_run.py
CSV columns: ts_event (UTC), open, high, low, close - the build_continuous.py
format. --compare imports the project's own backtest functions and fails
loudly (exit 1) on any trade that differs.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd
import vectorbt as vbt

HERE = os.path.dirname(os.path.abspath(__file__))
ORB_DIR = os.path.dirname(HERE)

ET = "America/New_York"
PV_MES = 5.0
COST_POINTS_ES_FREE = 0.1152      # screen_mean_reversion.REAL_COST_POINTS, ES free tier
LOCKED_STOP_POINTS = 124.75       # RESULTS.md 2.7 (99th-pct MAE on the 5-year history)
TIME_EXIT_MINUTES = 90
RUIN_PY = os.path.expanduser("~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")


def load_rth(path):
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    et = df["ts_event"].dt.tz_convert(ET)
    df["day"] = et.dt.date
    df["hhmm"] = et.dt.strftime("%H:%M")
    df = df[(df["hhmm"] >= "09:30") & (df["hhmm"] < "16:00")]
    return df.sort_values("ts_event").reset_index(drop=True)


def build_signals(df, stop_points, time_exit_minutes, half_cost):
    """Vectorised per-day signal arrays aligned to df's rows."""
    g = df.groupby("day", sort=False)
    in_rng = df["hhmm"] < "09:45"
    rng_n = in_rng.groupby(df["day"]).transform("sum")
    rh = df["high"].where(in_rng).groupby(df["day"]).transform("max")
    rl = df["low"].where(in_rng).groupby(df["day"]).transform("min")
    scan = ~in_rng

    up = scan & (df["close"] > rh)
    dn = scan & (df["close"] < rl)
    first_up = up & (up.astype(int).groupby(df["day"]).cumsum() == 1)
    dn_before = dn.astype(int).groupby(df["day"]).cumsum() > 0
    pos_in_day = g.cumcount()
    day_len = g["close"].transform("size")
    entries = first_up & ~dn_before & (rng_n >= 15) & (pos_in_day < day_len - 1)

    entry_px = df["close"].where(entries).groupby(df["day"]).ffill()
    entry_ts = df["ts_event"].where(entries).groupby(df["day"]).ffill()
    after = entry_px.notna() & ~entries

    exits = pd.Series(False, index=df.index)
    if time_exit_minutes is not None:
        due = after & (df["ts_event"] >= entry_ts + pd.Timedelta(minutes=time_exit_minutes))
        check_bar = due & (due.astype(int).groupby(df["day"]).cumsum() == 1)
        underwater = (df["close"] - half_cost) < (entry_px + half_cost)
        exits |= check_bar & underwater
    exits |= pos_in_day == day_len - 1          # session close

    sl = (stop_points / df["close"]).where(entries) if stop_points is not None else None
    return entries, exits, sl


def run(df, stop_points, time_exit_minutes, half_cost):
    entries, exits, sl = build_signals(df, stop_points, time_exit_minutes, half_cost)
    kw = dict(close=df["close"].to_numpy(), entries=entries.to_numpy(),
              exits=exits.to_numpy(), size=1.0, fixed_fees=half_cost,
              init_cash=1e9, accumulate=False)
    if sl is not None:
        kw.update(open=df["open"].to_numpy(), high=df["high"].to_numpy(),
                  low=df["low"].to_numpy(), sl_stop=sl.to_numpy(),
                  stop_exit_price="StopLimit")
    pf = vbt.Portfolio.from_signals(**kw)
    tr = pf.trades.records_readable
    out = pd.DataFrame({
        "date": df["day"].iloc[tr["Entry Timestamp"]].astype(str).to_numpy(),
        "entry": tr["Avg Entry Price"].to_numpy(),
        "exit": tr["Avg Exit Price"].to_numpy(),
        "exit_hhmm": df["hhmm"].iloc[tr["Exit Timestamp"]].to_numpy(),
        # fixed_fees = half cost in points per order, size 1, so PnL is net points
        "pnl_usd": tr["PnL"].to_numpy() * PV_MES,
    })
    return out


def reference_trades(csv, stop_points, time_exit_minutes, half_cost):
    """The project's own backtest code (mes_final_run.py) on the same bars."""
    sys.path.insert(0, ORB_DIR)
    sys.path.insert(0, os.path.join(os.path.dirname(ORB_DIR), "index_mean_reversion"))
    import mes_final_run as mfr
    from orb_test import load
    trades = mfr.build_mes_trades(load(csv))
    rows = []
    for t in trades:
        px, reason = mfr.resolve_exit(t, half_cost, stop_points, time_exit_minutes)
        rows.append({"date": t["date"], "entry": t["entry_price"], "exit": px,
                     "reason": reason,
                     "pnl_usd": ((px - half_cost) - (t["entry_price"] + half_cost)) * PV_MES})
    return pd.DataFrame(rows)


def summary(tr):
    p = tr["pnl_usd"]
    eq = p.cumsum()
    return (f"trades={len(p)}  total=${p.sum():,.2f}  avg=${p.mean():,.2f}  "
            f"win={100 * (p > 0).mean():.1f}%  maxDD=${(eq.cummax() - eq).max():,.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--stop", type=float, default=LOCKED_STOP_POINTS)
    ap.add_argument("--compare", action="store_true",
                    help="diff config 4 trade-by-trade against mes_final_run.py")
    ap.add_argument("--trades-out", help="write config-4 trades to this CSV")
    args = ap.parse_args()

    half = COST_POINTS_ES_FREE / 2.0
    df = load_rth(args.csv)
    print(f"bars={len(df)}  days={df['day'].nunique()}  "
          f"{df['day'].iloc[0]} .. {df['day'].iloc[-1]}  stop={args.stop} pts")

    configs = [
        ("1. no exit mechanism (hold to close)", None, None),
        ("2. price stop only", args.stop, None),
        ("3. 90-min time exit only", None, TIME_EXIT_MINUTES),
        ("4. stop + 90-min time exit (LOCKED v2)", args.stop, TIME_EXIT_MINUTES),
    ]
    results = {}
    for name, sp, tm in configs:
        tr = run(df, sp, tm, half)
        results[name] = tr
        print(f"  {name:42s} {summary(tr)}")
        if os.path.exists(RUIN_PY) and len(tr) >= 100:
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
                fh.write("\n".join(f"{x / 1000.0:.6f}" for x in tr["pnl_usd"]))
            out = subprocess.run(
                [sys.executable, RUIN_PY, "--r-file", fh.name, "--risk-pct", "1.0",
                 "--max-total-dd-pct", "3", "--dd-basis", "trailing", "--target-pct", "6",
                 "--max-daily-dd-pct", "0", "--trades-per-day", "1", "--min-days", "0",
                 "--max-days", "5000", "--sims", "20000"],
                capture_output=True, text=True)
            os.unlink(fh.name)
            for line in out.stdout.splitlines():
                if line.strip().startswith("PASS"):
                    print(f"      ruin.py {line.strip()}")

    locked = results[configs[3][0]]
    if args.trades_out:
        locked.to_csv(args.trades_out, index=False)
    print("\n" + locked.to_string(index=False))

    if args.compare:
        ref = reference_trades(args.csv, args.stop, TIME_EXIT_MINUTES, half)
        m = locked.merge(ref, on="date", how="outer", suffixes=("_vbt", "_ref"),
                         indicator=True)
        bad = m[(m["_merge"] != "both")
                | ((m["entry_vbt"] - m["entry_ref"]).abs() > 1e-6)
                | ((m["exit_vbt"] - m["exit_ref"]).abs() > 1e-6)
                | ((m["pnl_usd_vbt"] - m["pnl_usd_ref"]).abs() > 1e-6)]
        print(f"\ncompare vs mes_final_run.py: vbt={len(locked)} ref={len(ref)} "
              f"mismatches={len(bad)}  ref total=${ref['pnl_usd'].sum():,.2f}")
        if len(bad):
            print(bad.to_string(index=False))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
