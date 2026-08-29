#!/usr/bin/env python3
"""
baseline_reconciliation.py - re-measures RESULTS.md section 2.6's no-stop
survivability numbers (44.5% NQ full-size, 45.2% ES full-size, 89.1% MNQ,
99.1% MES) using each trade's EXACT historical dollar P&L, instead of that
section's median-$/1R flat-risk approximation.

Why this exists
    wide_stop_test.py's pre-registered wide-stop test (run earlier the same
    night) needed a risk-pct calibration for ruin.py and, as a side effect of
    doing that calibration exactly (dollar-for-dollar, no shortcut), produced
    a no-stop comparison number far below RESULTS.md's own reported baseline
    (31.3% vs 89.1% MNQ; 51.4% vs 99.1% MES) - but that side-effect run only
    used the High-vol-bucket subset of trades in one script and the 99th-
    percentile-stop-distance subset in another. Neither directly re-ran
    RESULTS.md section 2.6's own claim on the FULL, unfiltered trade
    population with the exact method. This file does exactly that - the
    direct, apples-to-apples reconciliation - so there is one trustworthy
    number instead of three partial ones.

Method
    Same entry/exit mechanism already validated (orb_test.py): first 1-min
    bar closing above the 09:30-09:44 ET opening range high, exit at session
    close, no stop. Same real Tradovate free-tier cost model, half-cost per
    leg (identical convention to stoploss_test.py / wide_stop_test.py).
    Exact dollar P&L computed per trade, per instrument, for BOTH full-size
    and micro contracts (NQ $20/pt & MNQ $2/pt; ES $50/pt & MES $5/pt).

    r fed to ruin.py = dollar_pnl / 1000 (r in units of $1,000).
    risk-pct fed to ruin.py = 1.0 (1 unit of r == 1% of the $100,000 starting
    balance == $1,000). This is algebraically exact: r * risk_pct always
    equals dollar_pnl as a percent of $100,000, for every trade, with no
    approximation and no dependence on any "typical" or median trade size -
    ruin.py sees the real historical dollar swing of every single trade.

    Same firm-rule parameters RESULTS.md section 2.6 used: $3,000 (3%) total
    drawdown, trailing to end-of-day balance; $6,000 (6%) profit target; no
    daily-loss check (Pro tier); 1 trade/day; unbounded horizon (no time
    limit, so max-days set high enough that timeout is not a factor).

Usage
    python3 baseline_reconciliation.py
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
from wide_stop_test import build_trades_with_mae

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]

POINT_VALUES = {
    "NQ (Nasdaq, primary)": {"full": ("NQ", 20.0), "micro": ("MNQ", 2.0)},
    "ES (S&P500, repl.)": {"full": ("ES", 50.0), "micro": ("MES", 5.0)},
}

# RESULTS.md section 2.6's own reported figures, for direct comparison.
ORIGINAL = {
    "NQ": 44.5, "ES": 45.2, "MNQ": 89.1, "MES": 99.1,
}


def ruin_pass_pct(r_series):
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
    for line in out.stdout.splitlines():
        if "PASS" in line and "%" in line:
            return float(line.split(":")[1].strip().rstrip("%"))
    return None


def main():
    print("=" * 96)
    print("  BASELINE RECONCILIATION - RESULTS.md section 2.6, re-measured with EXACT dollar P&L")
    print("  (no approximation - ruin.py fed each trade's real historical $ outcome directly)")
    print("=" * 96)

    results = {}
    for label, path in ONLY:
        df = load(path)
        cost_pts = smr.REAL_COST_POINTS[label]["free"]
        half_cost = cost_pts / 2.0
        trades = build_trades_with_mae(df)
        print(f"\n  {label}: n={len(trades)} long trades, full 5-year history")

        for size, (name, pv) in POINT_VALUES[label].items():
            r_series = []
            for t in trades:
                entry_c = t["entry_price"] + half_cost
                exit_c = t["close_exit_price"] - half_cost
                dollar_pnl = (exit_c - entry_c) * pv
                r_series.append(dollar_pnl / 1000.0)
            pct = ruin_pass_pct(r_series)
            results[name] = pct
            mean_dollar = 1000.0 * (sum(r_series) / len(r_series))
            print(f"    {name:4s} ({pv:5.1f} $/pt): mean $PnL/trade = ${mean_dollar:8.2f}   "
                  f"exact-dollar PASS = {pct:6.2f}%   "
                  f"(RESULTS.md 2.6 reported = {ORIGINAL[name]:.1f}%,  "
                  f"delta = {pct-ORIGINAL[name]:+.1f} pts)")

    print("\n" + "=" * 96)
    print("  SUMMARY TABLE")
    print("=" * 96)
    print(f"  {'Position':<22s} {'RESULTS.md 2.6 (approx.)':>26s} {'Exact-dollar (this run)':>26s}")
    for name in ("NQ", "ES", "MNQ", "MES"):
        label = "1 full-size " + name if name in ("NQ", "ES") else f"1 micro {name}"
        print(f"  {label:<22s} {ORIGINAL[name]:>25.1f}% {results[name]:>25.2f}%")

    print("\n  NOT MEASURED / caveats:")
    print("   - Same simplifications RESULTS.md section 2.6 already carried: 1 trade/day pacing")
    print("     approximation, drawdown checked mark-to-market per simulated trade rather than")
    print("     only at end-of-day (makes the simulation somewhat stricter than the real EOD-only")
    print("     rule, direction of bias only, not quantified).")
    print("   - Real Tradovate free-tier cost model, half-cost per leg; no slippage beyond quoted")
    print("     all-in rate.")


if __name__ == "__main__":
    sys.exit(main() or 0)
