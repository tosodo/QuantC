#!/usr/bin/env python3
"""
stoploss_reconciliation.py - re-measures STOPLOSS_HYPOTHESIS.md's no-stop vs
with-stop survivability comparison (MNQ 89.1%->63.5%, MES 99.1%->94.3%) using
each trade's EXACT historical dollar P&L, instead of that file's median-$/1R
flat-risk approximation.

Why this exists
    RESULTS.md section 2.6 found that the median-$/1R approximation used for
    the plain no-stop baseline was too optimistic (MNQ 89.1% -> 31.30% exact-
    dollar, MES 99.1% -> 51.36% exact-dollar) and explicitly flagged that
    STOPLOSS_HYPOTHESIS.md's stop-loss comparison "has not been re-run with
    the exact-dollar method and should not be read as still applying." This
    script does that re-run, same method as baseline_reconciliation.py:
    ruin.py is fed each trade's real dollar P&L directly (r = dollar_pnl /
    1000, risk-pct = 1.0), no typical/median-size approximation anywhere.

Method
    Same entry and same stop rule already pre-registered in
    STOPLOSS_HYPOTHESIS.md / stoploss_test.py: long entry unchanged, stop-loss
    = opposite side of the same opening range, exit at session close if never
    touched. Real Tradovate free-tier cost model, half-cost per leg (same
    convention as stoploss_test.py / baseline_reconciliation.py). Exact dollar
    P&L computed per trade for MNQ ($2/pt) and MES ($5/pt), full 5-year
    history (no in/out split - this is a survivability stress test on the
    full realised trade sequence, same convention baseline_reconciliation.py
    and STOPLOSS_HYPOTHESIS.md's own pooled full-history ruin.py run used).

Usage
    python3 stoploss_reconciliation.py
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, RANGE_START, RANGE_END_EXCL, INSTRUMENTS

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]

POINT_VALUES = {
    "NQ (Nasdaq, primary)": ("MNQ", 2.0),
    "ES (S&P500, repl.)": ("MES", 5.0),
}

# STOPLOSS_HYPOTHESIS.md's own reported figures (median-$/1R approx.), for
# direct comparison.
ORIGINAL = {"MNQ": (89.1, 63.5), "MES": (99.1, 94.3)}


def build_trades(df):
    """Long-side only. Returns list of dicts: entry_price, close_exit_price,
    stop_exit_price, stopped (bool). Mirrors stoploss_test.py's
    build_stop_trades exactly, but keeps raw prices instead of collapsing to
    range-width R units."""
    out = []
    for date, day in df.groupby("date_et", sort=True):
        rng = day[(day["time_et"] >= RANGE_START) & (day["time_et"] < RANGE_END_EXCL)]
        if len(rng) < 15:
            continue
        range_high = rng["high"].max()
        range_low = rng["low"].min()
        if range_high - range_low <= 0:
            continue

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

        stopped = False
        stop_exit_price = close_exit_price
        for _, b in forward.iloc[1:].iterrows():
            if b["low"] <= range_low:
                stopped = True
                stop_exit_price = range_low
                break

        out.append({
            "date": str(date),
            "entry_price": entry_price,
            "close_exit_price": close_exit_price,
            "stop_exit_price": stop_exit_price,
            "stopped": stopped,
        })
    return out


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
    print("  STOPLOSS_HYPOTHESIS.md RECONCILIATION - re-measured with EXACT dollar P&L")
    print("  (no approximation - ruin.py fed each trade's real historical $ outcome directly,")
    print("   same method as RESULTS.md section 2.6's baseline_reconciliation.py)")
    print("=" * 96)

    results = {}
    for label, path in ONLY:
        df = load(path)
        cost_pts = smr.REAL_COST_POINTS[label]["free"]
        half_cost = cost_pts / 2.0
        trades = build_trades(df)
        name, pv = POINT_VALUES[label]
        n_stopped = sum(1 for t in trades if t["stopped"])
        print(f"\n  {label} -> {name}: n={len(trades)} long trades, full 5-year history, "
              f"stopped out {n_stopped} ({100*n_stopped/len(trades):.1f}%)")

        r_no_stop, r_with_stop = [], []
        for t in trades:
            entry_c = t["entry_price"] + half_cost

            exit_c = t["close_exit_price"] - half_cost
            r_no_stop.append(((exit_c - entry_c) * pv) / 1000.0)

            stop_px = t["stop_exit_price"] if t["stopped"] else t["close_exit_price"]
            exit_c_stop = stop_px - half_cost
            r_with_stop.append(((exit_c_stop - entry_c) * pv) / 1000.0)

        pct_no_stop = ruin_pass_pct(r_no_stop)
        pct_with_stop = ruin_pass_pct(r_with_stop)
        results[name] = (pct_no_stop, pct_with_stop)

        mean_no_stop = 1000.0 * (sum(r_no_stop) / len(r_no_stop))
        mean_with_stop = 1000.0 * (sum(r_with_stop) / len(r_with_stop))
        print(f"    mean $PnL/trade  no-stop=${mean_no_stop:8.2f}   with-stop=${mean_with_stop:8.2f}")
        print(f"    exact-dollar PASS   no-stop={pct_no_stop:6.2f}%   with-stop={pct_with_stop:6.2f}%   "
              f"delta={pct_with_stop-pct_no_stop:+.2f} pts")
        orig_ns, orig_ws = ORIGINAL[name]
        print(f"    (old median-$/1R approx, for reference: no-stop={orig_ns:.1f}% -> "
              f"with-stop={orig_ws:.1f}%, delta={orig_ws-orig_ns:+.1f} pts)")

    print("\n" + "=" * 96)
    print("  SUMMARY TABLE")
    print("=" * 96)
    print(f"  {'Position':<14s} {'No-stop (exact-$)':>18s} {'With-stop (exact-$)':>20s} {'Delta':>8s}")
    for name in ("MNQ", "MES"):
        ns, ws = results[name]
        print(f"  {name:<14s} {ns:>17.2f}% {ws:>19.2f}% {ws-ns:>+7.2f}pt")

    print("\n  NOT MEASURED / caveats:")
    print("   - Fill assumed exactly at the stop price (range_low) - real slippage through")
    print("     a fast-moving stop level is not modeled here; a real fill would likely be worse,")
    print("     which would make the with-stop column look WORSE than reported, not better.")
    print("   - Same simplifications RESULTS.md 2.6 carried: 1 trade/day pacing approximation,")
    print("     drawdown checked mark-to-market per simulated trade rather than only at EOD.")
    print("   - Full history, no in/out-of-sample split (this is a survivability stress test on")
    print("     the realised trade sequence, not a significance test).")
    print("   - Only NQ->MNQ and ES->MES tested (short side and YM out of scope, matching")
    print("     STOPLOSS_HYPOTHESIS.md's original pre-registration).")


if __name__ == "__main__":
    sys.exit(main() or 0)
