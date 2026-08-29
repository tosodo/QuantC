#!/usr/bin/env python3
"""
mes_final_run.py - final MES-only research run per the user's directive
(2026-08-21): (1) confirm MES's own already-measured survivability alone,
(2) pre-register and test a 90-minute time-based invalidation exit, in
isolation and combined with the already-pre-registered 99th-percentile MAE
price stop (wide_stop_test.py), (3) report exact-dollar pass rate,
probability of ruin, and BOTH mean and median trades-to-target (ruin.py's
CLI only reports median; a faithful local port of its exact simulate()
algorithm is used here to add the mean - cross-checked against real
ruin.py's own reported median for every config before being trusted).

Directive 1 clarification (stated to the user before this ran): no test in
this project has ever combined MNQ and MES trades into one simulated
account - every survivability number so far, including MES's 64.41%
Model-A pass rate, is already MES measured completely alone. There is no
"MNQ drag" in that number to remove. This run reconfirms the 64.41% figure
for the record (config 2 below) and does not claim it as new.

Directive 2, "90 minutes post-entry": implemented as 90 minutes after each
TRADE's own entry timestamp (not a fixed 11:15 ET clock time), because
entries do not always happen at 09:45 - a trade entered later in the
morning would, under a fixed-clock rule, get an inconsistent (sometimes
negative or near-zero) holding window before the check. This is the
coherent, generalisable reading of "a time-based invalidation exit" and is
the version pre-registered and tested ONCE; no other cutoff is tried here.

Exit priority per trade, walking 1-min bars forward from entry in order:
    1. price stop (99th-percentile MAE, same distance already measured in
       wide_stop_test.py) - if a bar's low touches it first, exit there.
    2. otherwise, at the first bar at/after entry_ts + 90min, check whether
       the position is underwater net of round-trip cost; if so, exit at
       that bar's close. Checked once, not re-checked on later bars.
    3. otherwise, hold to session close (unchanged baseline exit).

Cost model, contract, and firm-rule parameters unchanged from every prior
file in this project (REAL_COST_POINTS free tier, half-cost per leg, MES
$5/pt, LucidPro 3% trailing DD / 6% target / no daily limit / 1 trade/day).

Usage
    python3 mes_final_run.py
"""

import os
import random
import subprocess
import sys
import tempfile

import pandas as pd
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, RANGE_START, RANGE_END_EXCL, INSTRUMENTS

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ES_LABEL = "ES (S&P500, repl.)"
ES_PATH = dict(INSTRUMENTS)[ES_LABEL]
PV_MES = 5.0
TIME_EXIT_MINUTES = 90
ET = ZoneInfo("America/New_York")
SESSION_WINDOW_END = "11:00"   # entries after this ET time are dropped for config 5


def in_session_window(t):
    """Entry already can't be before 09:45 ET (that's when the scan for a
    breakout starts) - this adds the requested 11:00 ET upper bound."""
    return t["entry_ts"].astimezone(ET).strftime("%H:%M") <= SESSION_WINDOW_END

FIRM_ARGS = ["--max-total-dd-pct", "3", "--dd-basis", "trailing",
             "--target-pct", "6", "--max-daily-dd-pct", "0",
             "--trades-per-day", "1", "--min-days", "0",
             "--max-days", "5000", "--sims", "20000"]


def build_mes_trades(df):
    """Long-side only, same entry rule as orb_test.py/wide_stop_test.py.
    Returns list of dicts: date, entry_ts, entry_price, close_exit_price,
    after_entry (DataFrame of bars strictly after the entry bar, with
    ts_event/low/close)."""
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
        })
    return out


def resolve_exit(t, half_cost, stop_points=None, time_exit_minutes=None, slippage_points=0.0):
    """Returns (exit_price, reason) where reason in {'stop','time','close'}.
    slippage_points, if nonzero, is subtracted from EVERY exit's fill price
    (stop, time, and the scheduled session-close) - all three are market
    orders sent to close a long, so an adverse fill is a LOWER price
    received in every case. Entry fills are NOT slipped here - only exits,
    per what was actually asked."""
    entry_price = t["entry_price"]
    entry_c = entry_price + half_cost
    stop_level = entry_price - stop_points if stop_points is not None else None
    time_cutoff = (t["entry_ts"] + pd.Timedelta(minutes=time_exit_minutes)
                   if time_exit_minutes is not None else None)

    time_checked = False
    for _, b in t["after_entry"].iterrows():
        if stop_level is not None and b["low"] <= stop_level:
            return stop_level - slippage_points, "stop"
        if (time_cutoff is not None and not time_checked
                and b["ts_event"] >= time_cutoff):
            time_checked = True
            if (b["close"] - half_cost) < entry_c:
                return float(b["close"]) - slippage_points, "time"
            # else: profitable/flat at the check - hold to close, don't re-check
    return t["close_exit_price"] - slippage_points, "close"


def r_series_for(trades, half_cost, stop_points=None, time_exit_minutes=None, slippage_points=0.0):
    r_series, reasons = [], {"stop": 0, "time": 0, "close": 0}
    for t in trades:
        exit_px, reason = resolve_exit(t, half_cost, stop_points, time_exit_minutes, slippage_points)
        entry_c = t["entry_price"] + half_cost
        exit_c = exit_px - half_cost
        dollar_pnl = (exit_c - entry_c) * PV_MES
        r_series.append(dollar_pnl / 1000.0)
        reasons[reason] += 1
    return r_series, reasons


def ruin_py_pass_pct(r_series):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
        for r in r_series:
            fh.write(f"{r:.6f}\n")
        path = fh.name
    try:
        out = subprocess.run(
            [sys.executable, RUIN_PY, "--r-file", path, "--risk-pct", "1.0"] + FIRM_ARGS,
            capture_output=True, text=True, check=True)
    finally:
        os.unlink(path)
    pass_pct, ruin_pct, median_days = None, None, None
    for line in out.stdout.splitlines():
        s = line.strip()
        if s.startswith("PASS") and "%" in s:
            pass_pct = float(s.split(":")[1].strip().rstrip("%"))
        if s.startswith("FAIL - total drawdown"):
            ruin_pct = float(s.split(":")[1].strip().rstrip("%"))
        if "Median days to pass" in s:
            median_days = int(s.split(":")[1].strip())
    return pass_pct, ruin_pct, median_days


def local_simulate_mean_days(r_series, sims=20000, seed=1, max_days=5000):
    """Faithful port of ruin.py's simulate() (risk_pct=1.0, trailing DD 3%,
    target 6%, no daily limit, 1 trade/day, min_days=0) - used ONLY to add
    the mean trades-to-pass alongside ruin.py's own reported median and
    PASS%, since the shared script's CLI does not expose the mean."""
    rng = random.Random(seed)
    pass_days = []
    for _ in range(sims):
        equity, peak = 100.0, 100.0
        for day in range(max_days):
            r = rng.choice(r_series)
            equity += r * 1.0
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100.0
            if dd >= 3.0:
                break
            if equity >= 106.0:
                pass_days.append(day + 1)
                break
    mean_days = sum(pass_days) / len(pass_days) if pass_days else None
    median_days = sorted(pass_days)[len(pass_days) // 2] if pass_days else None
    return 100.0 * len(pass_days) / sims, mean_days, median_days


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

    print("=" * 100)
    print("  MES FINAL RUN - single-leg isolation + 90-minute time-exit filter")
    print(f"  n={len(trades)} long trades, full 5-year history, price stop = "
          f"{stop_99:.2f} pts (99th pctile MAE, same as wide_stop_test.py)")
    print("=" * 100)

    window_trades = [t for t in trades if in_session_window(t)]
    n_dropped = len(trades) - len(window_trades)
    ES_TICK = 0.25   # ES/MES tick size, points

    configs = [
        ("1. MES alone, NO exit mechanism (raw baseline)", trades, None, None, 0.0),
        ("2. MES alone, 99th-pctile price stop ONLY (= Model A, reconfirming)", trades, stop_99, None, 0.0),
        ("3. MES alone, 90-min time exit ONLY (no price stop)", trades, None, TIME_EXIT_MINUTES, 0.0),
        ("4. MES alone, COMBINED price stop + 90-min time exit (LOCKED baseline, no slippage)",
         trades, stop_99, TIME_EXIT_MINUTES, 0.0),
        (f"5. Config 4 + 09:45-11:00 ET entry window only "
         f"({n_dropped}/{len(trades)} trades outside window dropped)",
         window_trades, stop_99, TIME_EXIT_MINUTES, 0.0),
        ("6. Config 4 + 1 tick (0.25 pt) adverse slippage on stop/time-exit fills",
         trades, stop_99, TIME_EXIT_MINUTES, 1 * ES_TICK),
        ("7. Config 4 + 2 ticks (0.50 pt) adverse slippage on stop/time-exit fills",
         trades, stop_99, TIME_EXIT_MINUTES, 2 * ES_TICK),
    ]

    for name, trade_set, sp, tm, slip in configs:
        r_series, reasons = r_series_for(trade_set, half_cost, sp, tm, slip)
        pass_pct, ruin_pct, median_days_ruinpy = ruin_py_pass_pct(r_series)
        _, mean_days, median_days_local = local_simulate_mean_days(r_series)
        n = len(r_series)
        print(f"\n  {name}")
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

    print("\n  NOT MEASURED / caveats:")
    print("   - 90-min cutoff is measured from each trade's OWN entry time, not a fixed")
    print("     11:15 ET clock - a trade entered later in the morning gets a later cutoff.")
    print("     Only this one interpretation was tested (pre-registered as such).")
    print("   - The time-exit check happens once (first bar at/after the cutoff); it does")
    print("     not re-check on every later bar if that check found the trade profitable.")
    print("   - Local mean/median-days simulation is a from-scratch reimplementation of")
    print("     ruin.py's algorithm, used only to add the mean stat; its median is printed")
    print("     alongside ruin.py's own reported median above as a cross-check.")
    print("   - No test in this project has ever combined MNQ+MES trades into one shared")
    print("     account equity curve - MES's numbers here (and everywhere else in this")
    print("     project) are, and always were, MES measured completely alone.")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main() or 0)
