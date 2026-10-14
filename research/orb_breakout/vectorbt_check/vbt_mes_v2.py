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

--rules live replays what the LIVE script runs instead
(orb_long_ghost_DRAFT_mes_v2_accessible.pine, mirrored by ops/shadow_day.py):
  - no down-break skip (those days are traded)
  - stop = entry - 125 pts
  - 90-min exit re-checked on every bar: first bar >= 90 min after the entry
    bar with close <= entry (no cost term), exits at that close
  - session close on the 15:59 bar; catch-all exit on the first bar after
    entry outside 09:45-16:00 (half-days)
  - P&L gross of costs unless --rt-cost-usd is given (journal signal_pnl is gross)

Usage (venv with requirements.txt installed):
  python vbt_mes_v2.py --csv ../data/continuous/ES.csv            # 5-year, section 2.7 rules
  python vbt_mes_v2.py --csv bars.csv --compare                    # + trade-by-trade
                                                                   #   diff vs mes_final_run.py
  python vbt_mes_v2.py --csv bars.csv --rules live --compare       # live rules, diff vs
                                                                   #   ops/shadow_day.py
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


def load_bars(path, rth_only=True):
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    et = df["ts_event"].dt.tz_convert(ET)
    df["day"] = et.dt.date
    df["hhmm"] = et.dt.strftime("%H:%M")
    if rth_only:
        df = df[(df["hhmm"] >= "09:30") & (df["hhmm"] < "16:00")]
    else:
        # live rules: keep 09:30 onwards of the same ET date, so the
        # catch-all exit can see the first bar after 16:00 on a half-day
        df = df[df["hhmm"] >= "09:30"]
    return df.sort_values("ts_event").reset_index(drop=True)


def build_live_signals(df, stop_points, time_exit_minutes):
    """Signal arrays for the live script's rules (see module docstring)."""
    day = df["day"]
    in_rng = df["hhmm"] < "09:45"
    rng_n = in_rng.groupby(day).transform("sum")
    rh = df["high"].where(in_rng).groupby(day).transform("max")
    rl = df["low"].where(in_rng).groupby(day).transform("min")
    session = (df["hhmm"] >= "09:45") & (df["hhmm"] < "16:00")

    up = session & (df["close"] > rh) & (rng_n >= 15)
    entries = up & (up.astype(int).groupby(day).cumsum() == 1)
    dn = session & (df["close"] < rl)
    dn_first = (dn.astype(int).groupby(day).cumsum() > 0) & entries

    entry_px = df["close"].where(entries).groupby(day).ffill()
    entry_ts = df["ts_event"].where(entries).groupby(day).ffill()
    after = entry_px.notna() & ~entries

    timex = (df["ts_event"] - entry_ts >= pd.Timedelta(minutes=time_exit_minutes)) \
        & (df["close"] <= entry_px)
    exits = after & (~session | timex | (df["hhmm"] == "15:59"))
    sl = (stop_points / df["close"]).where(entries)
    return entries, exits, sl, dn_first


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


def run(df, stop_points, time_exit_minutes, half_cost, live=False):
    if live:
        entries, exits, sl, dn_first = build_live_signals(df, stop_points, time_exit_minutes)
    else:
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
    if live:
        out.insert(1, "down_break_first", dn_first.to_numpy()[tr["Entry Timestamp"]])
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


def reference_live_trades(df, stop_points):
    """ops/shadow_day.py replay_day - the journal's replay of the live script."""
    sys.path.insert(0, os.path.join(ORB_DIR, "ops"))
    import shadow_day
    shadow_day.STOP_PTS = stop_points      # module constant, read at call time
    replay_day = shadow_day.replay_day
    rows = []
    for day, g in df.groupby("day", sort=True):
        bars = [{"t": int(ts.timestamp()), "o": o, "h": h, "l": l, "c": c}
                for ts, o, h, l, c in zip(g["ts_event"], g["open"], g["high"],
                                          g["low"], g["close"])]
        r = replay_day(bars, str(day))
        if "exit" in r:
            rows.append({"date": str(day), "entry": r["entry"], "exit": r["exit"],
                         "reason": r["exit_reason"], "pnl_usd": r["pnl_usd"]})
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
    ap.add_argument("--rules", choices=("s27", "live"), default="s27",
                    help="s27 = RESULTS.md section 2.7 baseline (default); "
                         "live = the live Pine script's rules")
    ap.add_argument("--rt-cost-usd", type=float, default=0.0,
                    help="live rules only: round-turn cost per trade in $ (default 0 = gross)")
    ap.add_argument("--compare", action="store_true",
                    help="diff trade-by-trade against mes_final_run.py (s27) "
                         "or ops/shadow_day.py (live)")
    ap.add_argument("--trades-out", help="write config-4 trades to this CSV")
    args = ap.parse_args()

    if args.rules == "live":
        return main_live(args)
    half = COST_POINTS_ES_FREE / 2.0
    df = load_bars(args.csv)
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


def main_live(args):
    stop = 125.0 if args.stop == LOCKED_STOP_POINTS else args.stop
    half = args.rt_cost_usd / PV_MES / 2.0
    df = load_bars(args.csv, rth_only=False)
    print(f"LIVE rules  days={df['day'].nunique()}  {df['day'].iloc[0]} .. "
          f"{df['day'].iloc[-1]}  stop={stop} pts  rt_cost=${args.rt_cost_usd:.2f}")
    tr = run(df, stop, TIME_EXIT_MINUTES, half, live=True)
    print(f"  all days                {summary(tr)}")
    for flag, label in ((False, "range broke up first"), (True, "broke DOWN first (untested)")):
        sub = tr[tr["down_break_first"] == flag]
        if len(sub):
            print(f"  {label:23s} {summary(sub)}")
    if args.trades_out:
        tr.to_csv(args.trades_out, index=False)
    print("\n" + tr.to_string(index=False))

    if args.compare:
        if args.rt_cost_usd:
            print("\n--compare runs gross; drop --rt-cost-usd")
            return 1
        ref = reference_live_trades(df, stop)
        m = tr.merge(ref, on="date", how="outer", suffixes=("_vbt", "_ref"), indicator=True)
        bad = m[(m["_merge"] != "both")
                | ((m["entry_vbt"] - m["entry_ref"]).abs() > 1e-6)
                | ((m["exit_vbt"] - m["exit_ref"]).abs() > 1e-6)
                | ((m["pnl_usd_vbt"] - m["pnl_usd_ref"]).abs() > 0.01)]
        print(f"\ncompare vs ops/shadow_day.py: vbt={len(tr)} ref={len(ref)} "
              f"mismatches={len(bad)}  ref total=${ref['pnl_usd'].sum():,.2f}")
        if len(bad):
            print(bad.to_string(index=False))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
