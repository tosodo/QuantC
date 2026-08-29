#!/usr/bin/env python3
"""
wide_stop_test.py - two parts, run together because part 2 depends on part 1's
own output (a genuinely measured number, not a guess):

PART 1 - Maximum Adverse Excursion (MAE) distribution.
    For every already-validated long-side NQ/ES trade (entry unchanged from
    orb_test.py: first 1-min bar closing above the 09:30-09:44 ET opening
    range high), walk forward bar-by-bar from the bar AFTER entry (same
    convention as stoploss_test.py's stop-touch check) to the session close,
    and record the worst (lowest) low reached. MAE_points = entry_price -
    that worst low, floored at 0 (a trade that never dipped below its own
    entry has zero adverse excursion, not a negative one). Reports the 50th,
    90th, 95th, 99th percentile and the single worst trade, in points and in
    dollars for the MICRO contract (MNQ $2/pt, MES $5/pt - same multipliers
    RESULTS.md section 2.6 already used). Pools the FULL history (both
    in-sample and out-of-sample) - this is a distributional measurement, not
    a significance test, matching the convention orb_test.py --dump-long-r
    already uses ("both slices already inspected, pool everything").

PART 2 - Pre-registered wide "catastrophic-only" stop, tested once.
    Candidate stop distance = the 99th-percentile MAE from part 1, PER
    INSTRUMENT, chosen because it is a natural "should almost never trigger"
    candidate - not selected by trying several distances and picking the one
    that scores best (that would be curve-fitting; see STOPLOSS_HYPOTHESIS.md
    for why only one distance was tested there too). No other candidate is
    tried in this file.

    This is mechanically different from the already-rejected stop in
    STOPLOSS_HYPOTHESIS.md: that stop was tight (the opposite side of the
    opening range) and triggered on 47-53% of trades, which is what hurt
    survivability under LucidPro's trailing-drawdown rule (frequent moderate
    losses erode a trailing cushion faster than rare large ones). A stop set
    at the 99th percentile of historical adverse excursion should, by
    construction, trigger on approximately 1% of trades - a materially
    different frequency regime. Whether that difference actually saves
    survivability is not assumed here - it is measured below, same as before.

    Position size = 1 micro contract (MNQ or MES), matching the already-
    validated sizing in RESULTS.md section 2.6. Because the stop distance is
    now a FIXED number of points (not a floating per-trade quantity as in the
    no-stop baseline), the dollar amount at risk is genuinely constant across
    all trades for a given instrument - R here is redefined as dollar P&L /
    (stop_points x point_value), and risk-pct fed to ruin.py is that same
    fixed dollar amount / $100,000. This is a more direct application of
    ruin.py's flat-risk assumption than RESULTS.md section 2.6's own median-
    $/1R approximation (used there because the no-stop mechanism has no fixed
    risk unit).

    Cost model: same REAL_COST_POINTS free-tier table already used throughout
    this project, half-cost applied at each leg - same convention as
    stoploss_test.py's build_stop_trades. Fill assumed exactly at the stop
    price (no slippage modeled) - same simplification as the already-
    rejected stop test, flagged again here as NOT MEASURED and, for a wide
    stop that would only be touched on a genuinely violent move, probably a
    more optimistic assumption than for the tight stop (a fast market is more
    likely to gap through a level that's further away).

Usage
    python3 wide_stop_test.py
"""

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, RANGE_START, RANGE_END_EXCL, SESSION_CLOSE, INSTRUMENTS

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]

POINT_VALUE_MICRO = {
    "NQ (Nasdaq, primary)": 2.0,   # MNQ, $/point
    "ES (S&P500, repl.)": 5.0,     # MES, $/point
}
CONTRACT_NAME = {
    "NQ (Nasdaq, primary)": "MNQ",
    "ES (S&P500, repl.)": "MES",
}
# RESULTS.md section 2.6 baseline (no-stop), reused for comparison only.
BASELINE_PASS = {
    "NQ (Nasdaq, primary)": 89.1,
    "ES (S&P500, repl.)": 99.1,
}


def build_trades_with_mae(df):
    """Long-side only, entry unchanged from orb_test.py. Returns list of dicts:
    date, entry_price, close_exit_price, mae_points (>=0)."""
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
            continue  # short signal fired first that day - not a long trade

        entry_price = float(day.loc[day["ts_event"] == first_long_ts, "close"].iloc[0])
        forward = day[day["ts_event"] >= first_long_ts]
        if len(forward) < 2:
            continue
        exit_row = day.iloc[-1]
        close_exit_price = float(exit_row["close"])

        after_entry = forward.iloc[1:]   # same convention as stoploss_test.py
        worst_low = after_entry["low"].min() if len(after_entry) else entry_price
        mae_points = max(0.0, entry_price - float(worst_low))

        out.append({
            "date": str(date),
            "entry_price": entry_price,
            "close_exit_price": close_exit_price,
            "after_entry": after_entry,
            "mae_points": mae_points,
        })
    return out


def part1_mae_distribution(dfs):
    print("=" * 92)
    print("  PART 1 - Maximum Adverse Excursion distribution, long-side ORB (NQ/ES, full history)")
    print("=" * 92)
    trades_by_label = {}
    for label, _ in ONLY:
        trades = build_trades_with_mae(dfs[label])
        trades_by_label[label] = trades
        pts = sorted(t["mae_points"] for t in trades)
        pv = POINT_VALUE_MICRO[label]
        contract = CONTRACT_NAME[label]
        print(f"\n  {label}  (n={len(pts)} long trades, full 5-year history)")
        for pctl in (50, 90, 95, 99, 100):
            if pctl == 100:
                v = pts[-1]
                tag = "max (worst single trade)"
            else:
                v = smr.percentile(pts, pctl / 100.0)
                tag = f"{pctl}th percentile"
            print(f"    {tag:26s} {v:8.2f} pts   ${v*pv:8.2f} on 1 {contract}")
    return trades_by_label


def r_of(exit_px, entry_c, half_cost, stop_points, point_value):
    exit_c = exit_px - half_cost
    raw_dollars = (exit_c - entry_c) * point_value
    risk_dollars = stop_points * point_value
    return raw_dollars / risk_dollars


def part2_wide_stop(trades_by_label, cost_tier="free"):
    print("\n" + "=" * 92)
    print("  PART 2 - PRE-REGISTERED wide stop = 99th-percentile MAE, one candidate, tested once")
    print("=" * 92)

    for label, _ in ONLY:
        trades = trades_by_label[label]
        pts_sorted = sorted(t["mae_points"] for t in trades)
        stop_points = smr.percentile(pts_sorted, 0.99)
        pv = POINT_VALUE_MICRO[label]
        contract = CONTRACT_NAME[label]
        cost_points = smr.REAL_COST_POINTS[label][cost_tier]
        half_cost = cost_points / 2.0
        risk_dollars = stop_points * pv
        risk_pct = risk_dollars / 100000.0 * 100.0

        print(f"\n  {contract} ({label})")
        print(f"    Pre-registered stop distance: {stop_points:.2f} pts "
              f"(99th pctile MAE) = ${risk_dollars:.2f} on 1 {contract}  "
              f"(risk-pct = {risk_pct:.4f}% of $100,000)")

        r_no_stop = []
        r_with_stop = []
        stopped_count = 0
        for t in trades:
            entry_c = t["entry_price"] + half_cost
            stop_level = t["entry_price"] - stop_points

            stop_hit = False
            exit_px = t["close_exit_price"]
            for _, b in t["after_entry"].iterrows():
                if b["low"] <= stop_level:
                    stop_hit = True
                    exit_px = stop_level
                    break

            r_no_stop.append(r_of(t["close_exit_price"], entry_c, half_cost, stop_points, pv))
            r_with_stop.append(r_of(exit_px, entry_c, half_cost, stop_points, pv))
            if stop_hit:
                stopped_count += 1

        n = len(trades)
        pct_stopped = 100.0 * stopped_count / n if n else 0.0
        n0, m0, sd0, t0, p0 = smr.t_test(r_no_stop)
        n1, m1, sd1, t1, p1 = smr.t_test(r_with_stop)
        worst0 = min(r_no_stop) if r_no_stop else float("nan")
        worst1 = min(r_with_stop) if r_with_stop else float("nan")
        print(f"    Stopped out: {stopped_count}/{n} trades ({pct_stopped:.2f}%)  "
              "(sanity check - should be close to 1% by construction)")
        print(f"    meanR  no-stop={m0:+.4f}  with-stop={m1:+.4f}   "
              f"(R = $PnL / stop-distance-dollars, this instrument's fixed risk unit)")
        print(f"    worst  no-stop={worst0:+.3f}R  with-stop={worst1:+.3f}R")

        def ruin_pass_pct(r_series):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
                for r in r_series:
                    fh.write(f"{r:.6f}\n")
                path = fh.name
            try:
                out = subprocess.run(
                    [sys.executable, RUIN_PY, "--r-file", path,
                     "--risk-pct", f"{risk_pct:.6f}",
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

        # Same risk-pct (this instrument's fixed stop-distance dollar amount)
        # fed to BOTH series, so the no-stop-vs-with-stop comparison is
        # apples-to-apples - unlike comparing against RESULTS.md section 2.6's
        # baseline, which used a DIFFERENT (median $/1R) risk-pct calibration.
        pct_nostop_samecal = ruin_pass_pct(r_no_stop)
        pct_withstop = ruin_pass_pct(r_with_stop)
        old_baseline = BASELINE_PASS[label]

        print(f"    SURVIVABILITY (ruin.py, same firm rules as RESULTS.md 2.6):")
        print(f"      RESULTS.md 2.6 baseline (different, median-$/1R risk-pct calibration) "
              f"= {old_baseline:.1f}%")
        if pct_nostop_samecal is not None and pct_withstop is not None:
            delta = pct_withstop - pct_nostop_samecal
            print(f"      SAME calibration as this test, NO STOP  = {pct_nostop_samecal:.2f}%")
            print(f"      SAME calibration as this test, WITH 99th-pctile stop = "
                  f"{pct_withstop:.2f}%  (delta vs same-calibration no-stop: {delta:+.1f} pts)")
        else:
            print("    SURVIVABILITY: could not parse ruin.py output")

    print("\n  NOT MEASURED / caveats:")
    print("   - Fill assumed exactly at the stop price - real slippage on a fast move through")
    print("     a level this far away is not modeled; a real fill would likely be worse.")
    print("   - Only NQ+ES long side tested, matching the already-validated mechanism's scope.")
    print("   - MAE computed from bars strictly after the entry bar (same convention as the")
    print("     already-rejected stop test), so the entry bar's own low is not counted.")


def main():
    dfs = {}
    for label, path in ONLY:
        dfs[label] = load(path)
    trades_by_label = part1_mae_distribution(dfs)
    part2_wide_stop(trades_by_label)


if __name__ == "__main__":
    sys.exit(main() or 0)
