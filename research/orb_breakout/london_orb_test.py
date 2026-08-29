#!/usr/bin/env python3
"""
london_orb_test.py - pre-registered test of the 08:00 London-time Opening
Range Breakout hypothesis on NQ/ES/YM index futures (see LONDON_HYPOTHESIS.md
in this folder). Adapted directly from orb_test.py (the NY-session test) -
same isolation, cost, split, and reporting machinery, reused via the same
screen_mean_reversion import, not reimplemented. The only mechanical
difference: the opening-range window is defined in Europe/London civil time
(DST-adjusted) instead of America/New_York civil time. Exit and the trading-
day boundary stay anchored to the NY session, unchanged from orb_test.py.

Hypothesis under test (fixed in LONDON_HYPOTHESIS.md before this was run)
    Opening range = high/low of all 1-minute bars from 08:00:00-08:14:59
    LONDON time (15 bars). From 08:15 London onward, scan forward minute by
    minute for the FIRST 1-minute bar whose CLOSE is beyond the range
    (above high = long signal, below low = short signal). Entry = that
    bar's own close. Exit = the SAME US trading session's last bar before
    16:00 ET (identical exit convention to the NY test - not a new rule).
    One trade per instrument per day, first occurrence only.

    Two-sided, k=2, Bonferroni threshold 0.05/2 = 0.025 (fresh budget for
    this specific test, see LONDON_HYPOTHESIS.md).

Out-of-sample cutoff
    Reuses the IDENTICAL cutoff date already locked by orb_test.py's NQ
    70/30 split (2025-02-14), rather than computing a fresh split on this
    window's smaller eligible-day population - a deliberate choice to avoid
    a new researcher degree of freedom (see LONDON_HYPOTHESIS.md #3).

Usage
    python3 london_orb_test.py                # in-sample (default, safe to re-run)
    python3 london_orb_test.py --sample out   # held-back slice, look ONCE
"""

import argparse
import math
import os
import sys

import pandas as pd
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr

ET = ZoneInfo("America/New_York")
LDN = ZoneInfo("Europe/London")

RANGE_START_LDN = "08:00"
RANGE_END_EXCL_LDN = "08:15"   # opening range = bars with London-time start in [08:00,08:15)
SESSION_CLOSE_ET = "16:00"     # exit = close of the last bar with ET start-time < 16:00, unchanged from orb_test.py

# Reuse the NY test's own locked cutoff date instead of computing a fresh
# split - see LONDON_HYPOTHESIS.md #3.
NY_TEST_CUTOFF_DATE = "2025-02-14"

INSTRUMENTS = [
    ("NQ (Nasdaq, primary)", os.path.join(HERE, "data/continuous/NQ.csv")),
    ("ES (S&P500, repl.)", os.path.join(HERE, "data/continuous/ES.csv")),
    ("YM (Dow, repl.)", os.path.join(HERE, "data/continuous/YM.csv")),
]


def load(path):
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = df["ts_event"].dt.tz_convert(ET)
    ts_ldn = df["ts_event"].dt.tz_convert(LDN)
    df["date_et"] = ts_et.dt.date          # trading-day boundary anchored on NY, same as orb_test.py
    df["time_et"] = ts_et.dt.strftime("%H:%M")
    df["time_ldn"] = ts_ldn.dt.strftime("%H:%M")
    # Keep everything from the London range start through the NY session
    # close - covers both the (earlier) range window and the (later) scan +
    # exit, all still tagged with the correct NY calendar date.
    df = df[(df["time_et"] < SESSION_CLOSE_ET)]
    return df.sort_values("ts_event")


def build_signals(df, cost_points=None):
    out = []
    total_days = 0
    incomplete_range_days = 0
    no_signal_days = 0

    for date, day in df.groupby("date_et", sort=True):
        total_days += 1
        rng = day[(day["time_ldn"] >= RANGE_START_LDN) & (day["time_ldn"] < RANGE_END_EXCL_LDN)]
        if len(rng) < 15:
            incomplete_range_days += 1
            continue
        range_high = rng["high"].max()
        range_low = rng["low"].min()

        range_end_ts = rng["ts_event"].max()
        scan = day[day["ts_event"] > range_end_ts]
        if scan.empty:
            no_signal_days += 1
            continue

        long_hit = scan[scan["close"] > range_high]
        short_hit = scan[scan["close"] < range_low]
        first_long_ts = long_hit["ts_event"].min() if not long_hit.empty else None
        first_short_ts = short_hit["ts_event"].min() if not short_hit.empty else None

        if first_long_ts is None and first_short_ts is None:
            no_signal_days += 1
            continue
        if first_short_ts is None or (first_long_ts is not None and first_long_ts < first_short_ts):
            side, sig_ts = "long", first_long_ts
        else:
            side, sig_ts = "short", first_short_ts

        entry_price = float(day.loc[day["ts_event"] == sig_ts, "close"].iloc[0])
        exit_row = day.iloc[-1]
        exit_price = float(exit_row["close"])

        window = day[(day["ts_event"] >= sig_ts) & (day["ts_event"] <= exit_row["ts_event"])]
        closes = window["close"].to_numpy()
        if len(closes) < 3:
            continue
        log_closes = [math.log(c) for c in closes]
        rets = [log_closes[i + 1] - log_closes[i] for i in range(len(log_closes) - 1)]
        m = sum(rets) / len(rets)
        var = sum((x - m) ** 2 for x in rets) / (len(rets) - 1)
        sd = math.sqrt(var)
        horizon_vol = sd * math.sqrt(len(rets))
        if horizon_vol <= 0:
            continue

        if side == "long":
            raw0 = math.log(exit_price) - math.log(entry_price)
        else:
            raw0 = math.log(entry_price) - math.log(exit_price)

        cost_ret = (cost_points / entry_price) if cost_points is not None else 0.0
        rawc = raw0 - cost_ret

        out.append({
            "date": str(date),
            "side": side,
            "R0": raw0 / horizon_vol,
            "Rc": rawc / horizon_vol,
        })

    stats = {
        "total_days": total_days,
        "incomplete_range_days": incomplete_range_days,
        "no_signal_days": no_signal_days,
        "trade_days": len(out),
    }
    return out, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"),
                     default="free",
                     help="real Tradovate round-turn cost tier (default: free, "
                          "most conservative - no plan purchased)")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample, cutoff reused from the NY test "
                          "(default, safe to re-run); "
                          "out = held-back slice, look ONCE; "
                          "full = whole history, final confirmation only")
    args = ap.parse_args()

    thresh = 0.025
    cutoff_date = NY_TEST_CUTOFF_DATE
    print("=" * 88)
    print("  08:00 LONDON-TIME OPENING RANGE BREAKOUT - pre-registered two-sided test")
    print("  (see LONDON_HYPOTHESIS.md - locked before this was run)")
    print("  k = 2 (close beyond range high -> long, close beyond range low -> short)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {thresh}")
    print(f"  Cost model: REAL Tradovate {args.real_cost_tier} plan, MEASURED "
          "(TradovateAllInRates PDF), per-trade at entry price")
    print(f"  Out-of-sample cutoff REUSED from the NY test: {cutoff_date} "
          "(not a fresh split - see LONDON_HYPOTHESIS.md #3)")
    print("=" * 88)

    dfs = {}
    for label, path in INSTRUMENTS:
        print(f"\nLoading {label} ...")
        dfs[label] = load(path)

    if args.sample == "in":
        sample_note = f"IN-SAMPLE (through {cutoff_date})"
    elif args.sample == "out":
        sample_note = f"*** OUT-OF-SAMPLE (after {cutoff_date}) - LOOK ONCE ***"
    else:
        sample_note = "FULL HISTORY (both slices combined)"
    print(f"\nSample: {sample_note}")

    all_results = {}
    for label, _ in INSTRUMENTS:
        df = dfs[label]
        cost_pts = smr.REAL_COST_POINTS[label][args.real_cost_tier]

        sig0, stats = build_signals(df)
        sigc, _ = build_signals(df, cost_points=cost_pts)

        sig0f = smr.filter_sample(sig0, cutoff_date, args.sample)
        sigcf = smr.filter_sample(sigc, cutoff_date, args.sample)

        print(f"\n--- {label} ---")
        print(f"  Trading days seen: {stats['total_days']}  |  "
              f"incomplete London range: {stats['incomplete_range_days']}  |  "
              f"no breakout: {stats['no_signal_days']}  |  "
              f"trade days: {stats['trade_days']}")

        res = {}
        for side in ("long", "short"):
            s0 = [s["R0"] for s in sig0f if s["side"] == side]
            sc = [s["Rc"] for s in sigcf if s["side"] == side]
            n0, m0, p0 = smr.report(label, s0, f"{side} (zero-cost)", thresh)
            nc, mc, pc = smr.report(label, sc, f"{side} (real-{args.real_cost_tier})", thresh)
            res[side] = {"zero": (n0, m0, p0), "cost": (nc, mc, pc)}
        all_results[label] = res

    print("\n" + "=" * 88)
    print("  REPLICATION CHECK (sign agreement across NQ/ES/YM, zero-cost)")
    print("=" * 88)
    for side in ("long", "short"):
        signs = {}
        for label, _ in INSTRUMENTS:
            m = all_results[label][side]["zero"][1]
            signs[label] = 1 if m > 0 else (-1 if m < 0 else 0)
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        print(f"  {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n" + "=" * 88)
    print("  SAMPLE SIZE REALITY CHECK (sigma ~= 1.0R, alpha=0.025 two-sided, 80% power)")
    print("=" * 88)
    primary_label = INSTRUMENTS[0][0]
    primary_long_n = all_results[primary_label]["long"]["zero"][0]
    primary_short_n = all_results[primary_label]["short"]["zero"][0]
    print(f"  Trades available, primary instrument: long={primary_long_n}  short={primary_short_n}")
    print("  N needed to detect a true edge: 0.30R -> ~170   0.20R -> ~380   0.10R -> ~1,530")
    print(f"  With ~{primary_long_n}-{primary_short_n} trades per side, this run can resolve "
          "roughly a 0.3-0.4R edge at 80% power - smaller true edges will show up as "
          "'not significant' even if real.")

    print("\n  NOT MEASURED / caveats:")
    print("   - Cost is MEASURED (Tradovate All-In Rates PDF) at entry price; slippage "
          "beyond the quoted all-in rate is NOT MEASURED.")
    print("   - Continuous front-month futures (Databento, volume-roll), not back-adjusted "
          "for roll gaps.")
    print("   - ~17% of trading days lack complete 08:00-08:15 London-time pre-market "
          "coverage in this feed and are skipped (no trade, not counted as a loss) - "
          "see LONDON_HYPOTHESIS.md #5 for the caveat on whether that gap is random.")
    print("   - R-histogram not visually inspected here.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample slice "
              "(--sample out) has not been looked at.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
