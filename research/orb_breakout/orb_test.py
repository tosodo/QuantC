#!/usr/bin/env python3
"""
orb_test.py - pre-registered test of the 9:30am ET Opening Range Breakout
hypothesis on NQ/ES/YM index futures (see HYPOTHESIS.md in this folder).
Reuses the exact t-test, percentile, split, and cost machinery already built
and audited in research/index_mean_reversion/screen_mean_reversion.py -
imported directly, not reimplemented.

Hypothesis under test (fixed in HYPOTHESIS.md before this was run)
    Opening range = high/low of all 1-minute bars from 09:30:00-09:44:59 ET
    (15 bars). From 09:45 ET, scan forward minute by minute for the FIRST
    1-minute bar whose CLOSE is beyond the range (above high = long signal,
    below low = short signal). Entry = that bar's own close. Exit = the
    session's last bar before 16:00 ET. One trade per instrument per day,
    first occurrence only; a day where neither side triggers produces no
    trade.

    Two-sided, k=2, Bonferroni threshold 0.05/2 = 0.025 (fresh budget for
    this hypothesis family, see HYPOTHESIS.md #3).

Isolation
    Flat size, one trade per instrument per day, no stop/target - the outcome
    is the raw log-return from entry to session close, in the signal's
    direction, divided by that SAME window's own realised volatility (sd of
    the window's own 1-minute log returns, scaled by sqrt(minutes-in-window))
    - identical normalisation convention to screen_mean_reversion.py, just
    fed 1-minute returns instead of daily ones.

Overlap
    Every trade both enters and exits within the same calendar day, so
    unlike the daily 20-day-forward tests in this project, trades here never
    overlap in time by construction - there is no separate non-overlapping
    pass to run.

Cost
    Real, MEASURED Tradovate round-turn cost (REAL_COST_POINTS, same table
    as screen_mean_reversion.py), single leg, applied at each trade's own
    entry price. Zero-cost run required alongside.

Data completeness / pessimism
    A day is skipped (no trade) if the 09:30-09:44 opening-range window has
    fewer than 15 one-minute bars (incomplete data, e.g. a holiday-shortened
    session) - a signal is never computed from a partial range. Decisions
    use closed bars only; entry is the signal bar's own close (already known
    at the decision), never a bar not yet closed.

Known limitation, stated up front
    No special detection of exchange-shortened sessions (day-after-
    Thanksgiving, Christmas Eve, etc). The exit is whatever the data's last
    bar before 16:00 ET is that day, whether or not that day was a normal
    full session. Continuous front-month series (Databento, volume-roll, not
    back-adjusted) - see build_continuous.py.

Usage
    python3 orb_test.py                # in-sample (default, safe to re-run)
    python3 orb_test.py --sample out   # held-back slice, look ONCE
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

RANGE_START = "09:30"
RANGE_END_EXCL = "09:45"   # opening range = bars with start-time in [09:30,09:45)
SESSION_CLOSE = "16:00"    # exit = close of the last bar with start-time < 16:00

INSTRUMENTS = [
    ("NQ (Nasdaq, primary)", os.path.join(HERE, "data/continuous/NQ.csv")),
    ("ES (S&P500, repl.)", os.path.join(HERE, "data/continuous/ES.csv")),
    ("YM (Dow, repl.)", os.path.join(HERE, "data/continuous/YM.csv")),
]


def load(path):
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = df["ts_event"].dt.tz_convert(ET)
    df["date_et"] = ts_et.dt.date
    df["time_et"] = ts_et.dt.strftime("%H:%M")
    # Restrict to the RTH window up front (09:30-16:00) - cuts ~2/3 of the
    # near-24h data before the per-day loop, no effect on the result since
    # nothing outside this window is ever used.
    df = df[(df["time_et"] >= RANGE_START) & (df["time_et"] < SESSION_CLOSE)]
    return df.sort_values("ts_event")


def build_signals(df, cost_points=None):
    out = []
    total_days = 0
    incomplete_range_days = 0
    no_signal_days = 0

    for date, day in df.groupby("date_et", sort=True):
        total_days += 1
        rng = day[(day["time_et"] >= RANGE_START) & (day["time_et"] < RANGE_END_EXCL)]
        if len(rng) < 15:
            incomplete_range_days += 1
            continue
        range_high = rng["high"].max()
        range_low = rng["low"].min()

        scan = day[day["time_et"] >= RANGE_END_EXCL]
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
                     help="in = in-sample 70pct (default, safe to re-run); "
                          "out = held-back 30pct, look ONCE; "
                          "full = whole history, final confirmation only")
    ap.add_argument("--dump-long-r", default=None,
                     help="write the pooled NQ+ES long-side, cost-adjusted R "
                          "multiples (one per line) to this path - for "
                          "bootstrapping the propfirm-research-auditor "
                          "survivability check (ruin.py --r-file). Both "
                          "in-sample and out-of-sample slices have already "
                          "been inspected at this point, so this always pools "
                          "the FULL history regardless of --sample.")
    args = ap.parse_args()

    thresh = 0.025
    print("=" * 88)
    print("  9:30 ET OPENING RANGE BREAKOUT - pre-registered two-sided test")
    print("  (see HYPOTHESIS.md - this is the plan the user approved, run verbatim)")
    print("  k = 2 (close beyond range high -> long, close beyond range low -> short)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {thresh}  (fresh budget - see HYPOTHESIS.md #3)")
    print(f"  Cost model: REAL Tradovate {args.real_cost_tier} plan, MEASURED "
          "(TradovateAllInRates PDF), per-trade at entry price")
    print("  Every trade enters+exits same day -> no overlap between trades, "
          "no separate non-overlapping pass needed")
    print("=" * 88)

    dfs = {}
    for label, path in INSTRUMENTS:
        print(f"\nLoading {label} ...")
        dfs[label] = load(path)

    primary_label = INSTRUMENTS[0][0]
    primary_sig0, _ = build_signals(dfs[primary_label])
    cutoff_date = smr.split_dates([s["date"] for s in primary_sig0])

    if args.sample == "in":
        sample_note = f"IN-SAMPLE (through {cutoff_date})"
    elif args.sample == "out":
        sample_note = f"*** OUT-OF-SAMPLE (after {cutoff_date}) - LOOK ONCE ***"
    else:
        sample_note = "FULL HISTORY (both slices combined)"
    print(f"\nSample: {sample_note}  (cutoff decided on {primary_label}'s eligible "
          "trade days alone, fresh split for this hypothesis)")

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
              f"incomplete opening range: {stats['incomplete_range_days']}  |  "
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
    primary_long_n = all_results[primary_label]["long"]["zero"][0]
    primary_short_n = all_results[primary_label]["short"]["zero"][0]
    print(f"  Trades available, primary instrument: long={primary_long_n}  short={primary_short_n}")
    print("  N needed to detect a true edge: 0.30R -> ~170   0.20R -> ~380   0.10R -> ~1,530")
    print(f"  With ~{primary_long_n}-{primary_short_n} trades per side, this run can resolve "
          "roughly a 0.3-0.4R edge at 80% power - smaller true edges will show up as "
          "'not significant' even if real.")

    print("\n  NOT MEASURED / caveats:")
    print("   - Cost is MEASURED (Tradovate All-In Rates PDF) at entry price; slippage "
          "beyond the quoted all-in rate (spread-crossing, fill quality) is NOT MEASURED.")
    print("   - Continuous front-month futures (Databento, volume-roll), not back-adjusted "
          "for roll gaps.")
    print("   - No detection of exchange-shortened sessions; exit uses whatever the data's "
          "last pre-16:00-ET bar is that day.")
    print("   - R-histogram not visually inspected here (HYPOTHESIS.md red flag: a no-stop "
          "session-close exit can let one bad day dominate the t-test's normal approximation).")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample slice "
              "(--sample out) has not been looked at.")

    if args.dump_long_r:
        pooled = []
        for label in ("NQ (Nasdaq, primary)", "ES (S&P500, repl.)"):
            cost_pts = smr.REAL_COST_POINTS[label][args.real_cost_tier]
            sigc, _ = build_signals(dfs[label], cost_points=cost_pts)
            pooled.extend(s["Rc"] for s in sigc if s["side"] == "long")
        with open(args.dump_long_r, "w") as fh:
            fh.write("# pooled NQ+ES long-side, real-{} cost-adjusted R multiples, "
                      "full history (both slices already inspected)\n".format(args.real_cost_tier))
            for r in pooled:
                fh.write(f"{r:.6f}\n")
        print(f"\nWrote {len(pooled)} pooled NQ+ES long-side R multiples -> {args.dump_long_r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
