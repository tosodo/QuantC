#!/usr/bin/env python3
"""
dynamic_sizing_matrix.py - Models A/B/C survivability + time-to-target matrix,
directed by the user's "Actionable Directive" (2026-08-21) after the exact-
dollar reconciliation (baseline_reconciliation.py) showed the currently-
recommended 1-micro-contract sizing survives the LucidPro challenge only
31.3% (MNQ) / 51.4% (MES) of the time, not the originally reported 89.1%/99.1%.

Two numbers in the user's original directive were checked against already-
measured data BEFORE this file was written, and corrected with the user's
explicit sign-off (not assumed):
  - The original $250 ATR-sizing target was checked against the ATR20 range
    already measured in regime_segment.py (NQ ~210-320 pts/day). At $250,
    contracts = max(1, round($250 / (ATR_pts * point_value))) rounds to 1
    on essentially every day for every instrument - i.e. it would not be
    "dynamic" at all. User chose $1,000 instead (confirmed).
  - The original Model C $150 hard-cap stop sits BELOW the already-measured
    50th-percentile MAE ($164 MNQ / $89 MES from wide_stop_test.py part 1),
    meaning it would trigger on a majority of trades - mechanically the same
    shape as the tight stop already tested and REJECTED in
    STOPLOSS_HYPOTHESIS.md (47-53% trigger rate, worse survivability under a
    trailing-drawdown rule). User chose $450 instead (confirmed).

Three models, micro contracts only (MNQ/MES), long-side ORB entries
unchanged from orb_test.py (build_trades_with_mae, imported from
wide_stop_test.py):

  Model A - Static 1 micro contract + the already-pre-registered wide stop
            (99th-percentile MAE from wide_stop_test.py part 1). This is the
            same computation as wide_stop_test.py's "with-stop" run, redone
            here so all three models share one script and one new metric
            (days-to-target).

  Model B - Dynamic ATR-based sizing: contracts = max(1, round($1000 /
            (ATR20_pts_that_day * micro_point_value))), ATR20 shifted 1 day
            (regime_segment.py's daily_true_range, no lookahead), same 99th-
            percentile-MAE stop distance as Model A but its dollar value now
            scales with that day's contract count. Trades before the 20-day
            ATR warmup has enough history are excluded (no valid regime
            label yet) - same exclusion regime_segment.py already applies.

  Model C - Static 1 micro contract + a flat $450 hard-dollar stop cap
            (converted to points per instrument), instead of the measured
            99th-percentile distance. Tests whether a round, easier-to-set
            broker-side number costs much versus the data-derived one.

Sizing is baked into each trade's own dollar P&L BEFORE it is handed to
ruin.py, so variable per-trade risk (Model B) is handled exactly - same
technique baseline_reconciliation.py already used: r = dollar_pnl / 1000,
risk-pct = 1.0 fixed (1 unit of r == $1,000 == 1% of the $100,000 starting
balance), for every trade, no approximation.

New this file: ruin.py's own "Median days to pass" line (trades-per-day=1
here, so trades-to-target == days-to-target) is captured for every model,
answering whether smaller/reshaped risk still reaches the profit target or
just trades ruin for timeout.

Usage
    python3 dynamic_sizing_matrix.py
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, INSTRUMENTS
from wide_stop_test import build_trades_with_mae, POINT_VALUE_MICRO, CONTRACT_NAME
from regime_segment import daily_true_range

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]

ATR_SIZE_TARGET_DOLLARS = 1000.0   # user-confirmed, replacing the original $250
FLAT_STOP_CAP_DOLLARS = 450.0      # user-confirmed, replacing the original $150


def run_ruin_full(r_series):
    """Returns (pass_pct, median_trades_to_pass_or_None)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
        for r in r_series:
            fh.write(f"{r:.6f}\n")
        path = fh.name
    try:
        out = subprocess.run(
            [sys.executable, RUIN_PY, "--r-file", path,
             "--risk-pct", "1.0",
             "--max-total-dd-pct", "3", "--dd-basis", "trailing",
             "--target-pct", "6", "--max-daily-dd-pct", "0",
             "--trades-per-day", "1", "--min-days", "0",
             "--max-days", "5000", "--sims", "20000"],
            capture_output=True, text=True, check=True)
    finally:
        os.unlink(path)
    pass_pct, median_days = None, None
    for line in out.stdout.splitlines():
        if line.strip().startswith("PASS") and "%" in line:
            pass_pct = float(line.split(":")[1].strip().rstrip("%"))
        if "Median days to pass" in line:
            median_days = int(line.split(":")[1].strip())
    return pass_pct, median_days


def build_r_series(trades, stop_points_fn, contracts_fn, pv, half_cost):
    """stop_points_fn(trade) -> stop distance in points (or None to skip).
    contracts_fn(trade) -> contract count (or None to skip)."""
    r_series = []
    stopped = 0
    sizes = []
    skipped = 0
    for t in trades:
        stop_points = stop_points_fn(t)
        contracts = contracts_fn(t)
        if stop_points is None or contracts is None:
            skipped += 1
            continue
        sizes.append(contracts)
        entry_c = t["entry_price"] + half_cost
        stop_level = t["entry_price"] - stop_points
        exit_px = t["close_exit_price"]
        stop_hit = False
        for _, b in t["after_entry"].iterrows():
            if b["low"] <= stop_level:
                stop_hit = True
                exit_px = stop_level
                break
        if stop_hit:
            stopped += 1
        exit_c = exit_px - half_cost
        dollar_pnl = (exit_c - entry_c) * pv * contracts
        r_series.append(dollar_pnl / 1000.0)
    return r_series, stopped, sizes, skipped


def main():
    print("=" * 100)
    print("  SIZING/STOP MATRIX - Models A (static+measured stop), B (dynamic ATR sizing),")
    print("  C (static+flat $450 stop) - all micro contracts, same firm rules throughout")
    print("=" * 100)

    for label, path in ONLY:
        df = load(path)
        cost_points = smr.REAL_COST_POINTS[label]["free"]
        half_cost = cost_points / 2.0
        pv = POINT_VALUE_MICRO[label]
        contract = CONTRACT_NAME[label]

        trades = build_trades_with_mae(df)
        pts_sorted = sorted(t["mae_points"] for t in trades)
        stop_99 = smr.percentile(pts_sorted, 0.99)
        flat_stop_pts = FLAT_STOP_CAP_DOLLARS / pv

        atr = daily_true_range(path)
        atr_by_date = {str(d): v for d, v in atr["atr20"].items()}
        for t in trades:
            t["atr20"] = atr_by_date.get(t["date"])

        print(f"\n{'#'*100}\n# {contract} ({label})  n={len(trades)} long trades, full 5-year history")
        print(f"{'#'*100}")
        print(f"  Model A/B shared stop distance (99th pctile MAE): {stop_99:.2f} pts = "
              f"${stop_99*pv:.2f} on 1 {contract}")
        print(f"  Model C flat stop distance ($450 cap):            {flat_stop_pts:.2f} pts")

        # --- Model A: static 1 contract, 99th-pctile stop ---
        rA, stoppedA, sizesA, skipA = build_r_series(
            trades, lambda t: stop_99, lambda t: 1, pv, half_cost)
        passA, daysA = run_ruin_full(rA)

        # --- Model B: dynamic ATR sizing, same 99th-pctile stop ---
        def size_b(t):
            a = t["atr20"]
            if a is None or (isinstance(a, float) and a != a):  # NaN check
                return None
            raw = ATR_SIZE_TARGET_DOLLARS / (a * pv)
            return max(1, round(raw))
        rB, stoppedB, sizesB, skipB = build_r_series(
            trades, lambda t: stop_99, size_b, pv, half_cost)
        passB, daysB = run_ruin_full(rB)

        # --- Model C: static 1 contract, flat $450 stop ---
        rC, stoppedC, sizesC, skipC = build_r_series(
            trades, lambda t: flat_stop_pts, lambda t: 1, pv, half_cost)
        passC, daysC = run_ruin_full(rC)

        def fmt(name, r_series, stopped, sizes, skip, passp, days):
            n = len(r_series)
            pct_stop = 100.0 * stopped / n if n else 0.0
            size_note = ""
            if sizes and len(set(sizes)) > 1:
                mean_sz = sum(sizes) / len(sizes)
                size_note = (f"  size: min={min(sizes)} mean={mean_sz:.2f} max={max(sizes)} "
                             f"(n at 1 contract={sizes.count(1)}/{len(sizes)})")
            skip_note = f"  ({skip} trades skipped, no ATR20 yet)" if skip else ""
            days_note = f"{days}" if days is not None else "n/a (no passing sims)"
            print(f"  {name:8s} n={n:4d}  stopped={stopped:3d} ({pct_stop:4.1f}%)  "
                  f"PASS={passp:6.2f}%  median trades-to-target={days_note}{size_note}{skip_note}")

        print()
        fmt("Model A", rA, stoppedA, sizesA, skipA, passA, daysA)
        fmt("Model B", rB, stoppedB, sizesB, skipB, passB, daysB)
        fmt("Model C", rC, stoppedC, sizesC, skipC, passC, daysC)

    print("\n" + "=" * 100)
    print("  NOT MEASURED / caveats:")
    print("   - Model B's contract count is fixed for the whole day using that day's own")
    print("     pre-trade ATR20 (no lookahead) - it does not re-check size mid-trade.")
    print("   - Fill assumed exactly at the stop price for all three models (same simplification")
    print("     as wide_stop_test.py); a real fast-market fill would likely be worse.")
    print("   - 'median trades-to-target' is computed only across PASSING simulations - it does")
    print("     not describe attempts that failed or timed out.")
    print("   - Model B trades before the ATR20 warmup period (~20 trading days into the")
    print("     dataset) are excluded, same convention as regime_segment.py.")
    print("=" * 100)


if __name__ == "__main__":
    sys.exit(main() or 0)
