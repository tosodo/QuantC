#!/usr/bin/env python3
"""
regime_segment.py - volatility-regime segmentation of the validated long-side
9:30 ET ORB signal (NQ/ES). Diagnostic follow-up to RESULTS.md / STOPLOSS_
HYPOTHESIS.md (both closed): does the edge, and the tail risk RESULTS.md
already flagged, hold up specifically in high-volatility regimes (COVID 2020,
the 2022 rate-hike period, etc), or is the pooled result quietly propped up
by calm-market days while high-vol days are where it actually breaks?

Pure read-only diagnostic on data already collected. Does not touch
orb_long_ghost.pine or the live/demo Ghost-Tradovate setup. No new trading
rule is proposed here - this is a subgroup analysis of the existing,
already-validated signal, plus a stress-test of the existing survivability
conclusion (RESULTS.md section 2.6) restricted to the worst regime alone.

Regime measure: ATR20, the 20-trading-day rolling mean of each day's TRUE
RANGE (max(high-low, |high-prevclose|, |low-prevclose|)), computed from the
FULL daily bar (open/high/low/close across the whole ~24h contract session,
not the 09:30-16:00 ET RTH window used for the signal itself), so it reflects
the instrument's whole realized range, not just the traded window. Shifted by
one day - a trade taken on day t is bucketed using the mean TRUE RANGE of the
20 days strictly BEFORE t, so the regime label is knowable before the trade
is taken. No lookahead.

Bucket thresholds (25th / 75th percentile of ATR20) are fit on the IN-SAMPLE
slice only, per instrument, then applied unchanged to the out-of-sample
slice - a threshold is never re-derived from data not yet allowed to be
looked at, same discipline as the entry/exit rules themselves.

R unit: same vol-normalized Rc (cost-adjusted, real Tradovate free-tier cost)
already used in orb_test.py / RESULTS.md section 1 - NOT the range-width R
used in STOPLOSS_HYPOTHESIS.md. Numbers in this file are comparable to
RESULTS.md's table directly.

Usage
    python3 regime_segment.py
"""

import math
import os
import subprocess
import sys
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, build_signals, RANGE_START, RANGE_END_EXCL, SESSION_CLOSE, INSTRUMENTS

RUIN_PY = os.path.expanduser(
    "~/.claude/skills/propfirm-research-auditor/scripts/ruin.py")

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]  # long side, NQ/ES only, per RESULTS.md

# RESULTS.md section 2.6 MEASURED median $/1R risk-pct for 1 micro contract,
# reused verbatim here (not recomputed) for the regime-restricted survivability
# stress test, so the comparison is apples-to-apples against that baseline.
MICRO_RISK_PCT = {
    "NQ (Nasdaq, primary)": 0.257,   # ~$257 / $100,000 -> MNQ baseline PASS 89.1%
    "ES (S&P500, repl.)": 0.141,     # ~$141 / $100,000 -> MES baseline PASS 99.1%
}
MICRO_BASELINE_PASS = {
    "NQ (Nasdaq, primary)": 89.1,
    "ES (S&P500, repl.)": 99.1,
}


def daily_true_range(raw_path):
    """Full-session (not RTH-restricted) daily OHLC -> ATR20, shifted 1 day.
    Returns a DataFrame indexed by date (python date objects) with column
    atr20 (NaN for the first 20 available days)."""
    df = pd.read_csv(raw_path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = df["ts_event"].dt.tz_convert("America/New_York")
    df["date_et"] = ts_et.dt.date
    df = df.sort_values("ts_event")

    daily = df.groupby("date_et", sort=True).agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"))
    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr20 = tr.rolling(20).mean().shift(1)   # only days strictly before t
    return pd.DataFrame({"atr20": atr20})


def bucket_of(value, lo_cut, hi_cut):
    if pd.isna(value):
        return None
    if value < lo_cut:
        return "Low"
    if value > hi_cut:
        return "High"
    return "Medium"


def run_ruin(r_series, risk_pct, label):
    if len(r_series) < 20:
        return None, f"only {len(r_series)} trades in this bucket - too few to " \
                      "bootstrap a meaningful ruin.py run (not measured)"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as fh:
        for r in r_series:
            fh.write(f"{r:.6f}\n")
        path = fh.name
    try:
        out = subprocess.run(
            [sys.executable, RUIN_PY, "--r-file", path,
             "--risk-pct", str(risk_pct),
             "--max-total-dd-pct", "3", "--dd-basis", "trailing",
             "--target-pct", "6", "--max-daily-dd-pct", "0",
             "--trades-per-day", "1", "--min-days", "0",
             "--max-days", "5000", "--sims", "20000"],
            capture_output=True, text=True, check=True)
    finally:
        os.unlink(path)
    for line in out.stdout.splitlines():
        if "PASS" in line and "%" in line:
            pct = float(line.split(":")[1].strip().rstrip("%"))
            return pct, None
    return None, "could not parse ruin.py output"


def main():
    print("=" * 92)
    print("  VOLATILITY-REGIME SEGMENTATION - diagnostic follow-up, long-side ORB (NQ/ES)")
    print("  ATR20 = 20-day rolling mean TRUE RANGE, full session, shifted 1 day (no lookahead)")
    print("  Bucket cutoffs (25th/75th pctile) fit on IN-SAMPLE only, reused on out-of-sample")
    print("=" * 92)

    pooled_high_vol_rc = {}   # label -> list of Rc, full history, High bucket only

    for label, path in ONLY:
        print(f"\n{'#'*92}\n# {label}\n{'#'*92}")
        df = load(path)
        cost_pts = smr.REAL_COST_POINTS[label][ "free"]
        sig0, _ = build_signals(df)
        sigc, _ = build_signals(df, cost_points=cost_pts)
        cutoff_date = smr.split_dates([s["date"] for s in sig0])

        atr = daily_true_range(path)
        atr_by_date = {str(d): v for d, v in atr["atr20"].items()}

        # merge Rc trades with the (shifted, no-lookahead) ATR20 as of that date
        merged = []
        for s in sigc:
            if s["side"] != "long":
                continue
            a = atr_by_date.get(s["date"])
            merged.append({"date": s["date"], "Rc": s["Rc"], "atr20": a})

        in_sample = [m for m in merged if m["date"] <= cutoff_date and m["atr20"] is not None
                     and not (isinstance(m["atr20"], float) and math.isnan(m["atr20"]))]
        all_valid = [m for m in merged if m["atr20"] is not None
                     and not (isinstance(m["atr20"], float) and math.isnan(m["atr20"]))]

        in_atrs = sorted(m["atr20"] for m in in_sample)
        lo_cut = smr.percentile(in_atrs, 0.25)
        hi_cut = smr.percentile(in_atrs, 0.75)
        print(f"  IN-SAMPLE ATR20 cutoffs (points): 25th={lo_cut:.2f}  75th={hi_cut:.2f}"
              f"  (n={len(in_atrs)} in-sample days with a valid ATR20)")

        for m in all_valid:
            m["bucket"] = bucket_of(m["atr20"], lo_cut, hi_cut)
            m["sample"] = "in" if m["date"] <= cutoff_date else "out"

        for sample in ("in", "out"):
            print(f"\n  --- {('IN-SAMPLE' if sample=='in' else 'OUT-OF-SAMPLE')} ---")
            for bucket in ("Low", "Medium", "High"):
                vals = [m["Rc"] for m in all_valid if m["sample"] == sample and m["bucket"] == bucket]
                if not vals:
                    print(f"    {bucket:6s} n=0")
                    continue
                n, mean, sd, t, p = smr.t_test(vals)
                win = 100.0 * sum(1 for v in vals if v > 0) / n
                worst = min(vals)
                print(f"    {bucket:6s} n={n:4d}  meanRc={mean:+.4f}  sd={sd:.4f}  "
                      f"t={t:+.3f}  p={p:.4f}  win%={win:5.1f}  worst={worst:+.3f}R")

        pooled_high_vol_rc[label] = [m["Rc"] for m in all_valid if m["bucket"] == "High"]

    print("\n" + "=" * 92)
    print("  SURVIVABILITY STRESS TEST: what if this account only ever traded High-vol days?")
    print("  (same ruin.py machinery / firm rules as RESULTS.md section 2.6, same micro-contract")
    print("   risk-pct already measured there - reused, not recomputed)")
    print("=" * 92)
    for label, _ in ONLY:
        vals = pooled_high_vol_rc[label]
        risk_pct = MICRO_RISK_PCT[label]
        baseline = MICRO_BASELINE_PASS[label]
        pct, err = run_ruin(vals, risk_pct, label)
        contract = "MNQ" if "Nasdaq" in label else "MES"
        if err:
            print(f"  {contract}: n(High-vol trades)={len(vals)} -> {err}")
        else:
            delta = pct - baseline
            print(f"  {contract}: n(High-vol trades)={len(vals):4d}  PASS={pct:6.2f}%  "
                  f"(all-regime baseline {baseline:.1f}%, delta {delta:+.1f} pts)")

    print("\n  NOT MEASURED / caveats:")
    print("   - ATR20 uses full-session (near-24h) daily range, not RTH-only; a reasonable")
    print("     volatility-regime proxy but not identical to intraday RTH volatility.")
    print("   - High-vol-only ruin.py run pools that bucket's trades across the WHOLE history")
    print("     (not separated by in/out sample) - a stress test of 'what if regime persisted',")
    print("     not a fresh significance test.")
    print("   - Bucket boundaries are per-instrument (NQ's High-vol days need not be the same")
    print("     calendar days as ES's High-vol days).")


if __name__ == "__main__":
    sys.exit(main() or 0)
