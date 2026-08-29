#!/usr/bin/env python3
"""
screen_session_open.py - pre-registered test of the US cash-open hypothesis.

Hypothesis under test (fixed before this was run, not adjusted afterwards)
    Two-sided, on the hour-wide bar that contains the 9:30am ET cash open:

    CONTINUATION: if price closes beyond that bar's high/low later the same
    session, the following 1R move happens in the SAME direction more often
    than a coin flip would predict.

    REVERSAL: the same break is instead followed by a 1R move in the
    OPPOSITE direction more often than a coin flip would predict.

    Both are tested. Neither was chosen after looking at results.

Isolation (test_design.md #1)
    Flat R per trade. One position per day. Fixed 1:1 stop/target, sized off
    the opening bar's own range - a structural, non-tuned choice, not fit to
    this data. Baseline expectancy at 1:1 is exactly 0.00R under a random
    walk (test_design.md #2): win rate alone proves nothing here.

Signal + entry (mirrors the no-lookahead convention already used in
~/Workspace/fp50k-ea/tools/screen.py: decide on a CLOSED bar, fill at the
NEXT bar's open)
    - Opening range = the 09:00-10:00 ET bar's [low, high].
    - Walk forward bars from 10:00 same day. The first bar whose CLOSE is
      beyond the range marks the signal bar.
    - Fill at the following bar's open. Only one signal per day; if the
      range isn't broken before the day's cutoff, there is no trade.
    - Cutoff: no new entries once bars would extend management past 4:45pm
      ET (Lucid's mandatory flat time - not a chosen parameter, a firm rule).
      Any position still open at the last usable bar is time-stopped at that
      bar's close.

Exit
    - Stop and target are each 1R from entry, R = opening-range width.
    - Ambiguous bar (stop AND target both inside one forward bar's range) is
      always scored as the LOSS (test_design.md #7). No exception.

Costs
    Every run reports BOTH a zero-cost pass and a cost-adjusted pass
    (test_design.md #6). Cost is a flat round-trip points haircut
    (--cost-pts, default 0.5 = 2 ticks on the index, a placeholder for real
    Tradovate/Lucid commission and slippage, which have NOT been verified -
    see the NOT MEASURED note this script prints).

Multiple comparisons (test_design.md #4)
    k = 2 (continuation, reversal), tested once each on the primary
    instrument. Bonferroni threshold = 0.05 / 2 = 0.025.
    ES=F and YM=F are the required replication set (test_design.md #5): sign
    agreement is checked, not independently thresholded - they are not a
    second bite at significance.

Known data limitation, stated up front
    ~2.4 years of hourly bars (Yahoo's practical hourly history limit), not
    the 8+ years test_design.md prefers. At roughly one signal opportunity
    per trading day, this run cannot resolve an edge smaller than roughly
    0.2-0.3R at conventional significance - see the sample-size arithmetic
    printed at the end. That is a real constraint on what this run can prove,
    not a reason to skip running it.

Author: written for the QuantC / Lucid MNQ session-open hypothesis audit.
"""

import argparse
import csv
import math
import sys
from datetime import datetime, timedelta


# --------------------------------------------------------------------------
# Student's t two-sided p-value, no scipy - same continued-fraction
# implementation already used in fp50k-ea/tools/edge_stats.py.
# --------------------------------------------------------------------------
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3.0e-16, 1.0e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < FPMIN:
            d = FPMIN
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < FPMIN:
            d = FPMIN
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
           + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_test(values):
    n = len(values)
    if n < 2:
        return n, (values[0] if values else 0.0), 0.0, 0.0, 1.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    sd = math.sqrt(var)
    if sd <= 0.0:
        return n, mean, sd, 0.0, 1.0
    t = mean / (sd / math.sqrt(n))
    df = n - 1
    p = _betai(df / 2.0, 0.5, df / (df + t * t))
    return n, mean, sd, t, p


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
class Bar:
    __slots__ = ("date", "time", "o", "h", "l", "c")

    def __init__(self, date, time, o, h, l, c):
        self.date, self.time = date, time
        self.o, self.h, self.l, self.c = o, h, l, c


def load(path):
    bars = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            bars.append(Bar(row["date_ny"], row["time_ny"],
                             float(row["open"]), float(row["high"]),
                             float(row["low"]), float(row["close"])))
    bars.sort(key=lambda b: (b.date, b.time))
    by_day = {}
    for b in bars:
        by_day.setdefault(b.date, []).append(b)
    return by_day


# --------------------------------------------------------------------------
# One day's worth of the test
# --------------------------------------------------------------------------
def simulate_day(day_bars, cost_pts):
    """Returns (continuation_R, reversal_R) or (None, None) if no trade."""
    by_time = {b.time: b for b in day_bars}
    if "09:00" not in by_time:
        return None, None
    orb = by_time["09:00"]
    or_hi, or_lo = orb.h, orb.l
    r = or_hi - or_lo
    if r <= 0:
        return None, None

    # Forward bars strictly after the opening bar, in time order, cut off
    # once a new entry could not be flattened by Lucid's 4:45pm ET rule.
    # The 15:00-16:00 bar is the last one allowed to open a fresh position;
    # anything still open is time-stopped at its close.
    forward = [b for b in day_bars if "10:00" <= b.time <= "15:00"]
    if not forward:
        return None, None

    signal_idx, direction = None, None
    for i, b in enumerate(forward):
        if b.c > or_hi:
            signal_idx, direction = i, "long"
            break
        if b.c < or_lo:
            signal_idx, direction = i, "short"
            break
    if signal_idx is None or signal_idx + 1 >= len(forward):
        return None, None  # no break, or broke on the last usable bar

    entry_bar = forward[signal_idx + 1]
    entry = entry_bar.o
    half_cost = cost_pts / 2.0

    def run_trade(trade_long):
        px_entry = entry + half_cost if trade_long else entry - half_cost
        if trade_long:
            stop, target = px_entry - r, px_entry + r
        else:
            stop, target = px_entry + r, px_entry - r
        for b in forward[signal_idx + 1:]:
            if trade_long:
                hit_stop = b.l <= stop
                hit_target = b.h >= target
            else:
                hit_stop = b.h >= stop
                hit_target = b.l <= target
            if hit_stop and hit_target:
                return -1.0  # ambiguous bar -> always the loss
            if hit_stop:
                return -1.0
            if hit_target:
                return 1.0
        # time-stop at the last usable bar's close
        exit_px = forward[-1].c
        exit_px = exit_px - half_cost if trade_long else exit_px + half_cost
        raw = (exit_px - px_entry) if trade_long else (px_entry - exit_px)
        return raw / r

    cont_long = (direction == "long")
    cont_R = run_trade(cont_long)
    rev_R = run_trade(not cont_long)
    return cont_R, rev_R


def split_dates(all_dates, frac_in_sample=0.8):
    """80/20 chronological split, decided by position alone - never by
    looking at any trade outcome. test_design.md #8: fixed before looking."""
    dates = sorted(all_dates)
    cut = int(len(dates) * frac_in_sample)
    return dates[:cut], dates[cut:]


def run_instrument(path, cost_pts, dates_filter=None):
    by_day = load(path)
    cont, rev = [], []
    for date in sorted(by_day):
        if dates_filter is not None and date not in dates_filter:
            continue
        c, rv = simulate_day(by_day[date], cost_pts)
        if c is not None:
            cont.append(c)
            rev.append(rv)
    return cont, rev


def report(label, values, tag):
    n, mean, sd, t, p = t_test(values)
    print(f"  [{label}] {tag:12s} n={n:4d}  mean={mean:+.4f}R  "
          f"sd={sd:.4f}  t={t:+.3f}  p={p:.4f}")
    return n, mean, p


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cost-pts", type=float, default=0.5,
                     help="round-trip cost in index points (placeholder - "
                          "real Tradovate/Lucid commission not yet verified)")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample (default, safe to re-run); "
                          "out = the held-back slice, look at this ONCE; "
                          "full = whole history, for final confirmation only")
    args = ap.parse_args()

    instruments = [
        ("MNQ_proxy (primary)", "data/MNQ_proxy.csv"),
        ("MES_proxy (replication)", "data/MES_proxy.csv"),
        ("MYM_proxy (replication)", "data/MYM_proxy.csv"),
    ]

    # Split decided by chronological position alone, using the primary
    # instrument's date range - never by looking at any outcome.
    primary_days = sorted(load(instruments[0][1]).keys())
    in_sample_dates, out_sample_dates = split_dates(primary_days)
    if args.sample == "in":
        dates_filter = set(in_sample_dates)
        sample_note = f"IN-SAMPLE ({in_sample_dates[0]} -> {in_sample_dates[-1]})"
    elif args.sample == "out":
        dates_filter = set(out_sample_dates)
        sample_note = (f"*** OUT-OF-SAMPLE ({out_sample_dates[0]} -> "
                        f"{out_sample_dates[-1]}) - LOOK ONCE, DO NOT RE-RUN "
                        f"AFTER CHANGING ANYTHING ***")
    else:
        dates_filter = None
        sample_note = "FULL HISTORY (both slices combined)"

    print("=" * 78)
    print("  US CASH-OPEN HYPOTHESIS - pre-registered two-sided screen")
    print(f"  Sample: {sample_note}")
    print("  k = 2 (continuation, reversal) on the primary instrument")
    print("  Bonferroni threshold = 0.05 / 2 = 0.025")
    print("=" * 78)

    results = {}
    for label, path in instruments:
        print(f"\n--- {label} ---")
        cont0, rev0 = run_instrument(path, cost_pts=0.0, dates_filter=dates_filter)
        report(label, cont0, "continuation (zero-cost)")
        report(label, rev0, "reversal (zero-cost)")

        contC, revC = run_instrument(path, cost_pts=args.cost_pts, dates_filter=dates_filter)
        n_c, mean_c, p_c = report(label, contC, f"continuation (cost {args.cost_pts}pt)")
        n_r, mean_r, p_r = report(label, revC, f"reversal (cost {args.cost_pts}pt)")
        results[label] = {
            "cont": (n_c, mean_c, p_c),
            "rev": (n_r, mean_r, p_r),
        }

    print("\n" + "=" * 78)
    print("  REPLICATION CHECK (sign agreement across instruments)")
    print("=" * 78)
    for side in ("cont", "rev"):
        signs = {label: (1 if results[label][side][1] > 0 else
                          (-1 if results[label][side][1] < 0 else 0))
                 for label in results}
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        print(f"  {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n" + "=" * 78)
    print("  SAMPLE SIZE REALITY CHECK (test_design.md #9, sigma ~= 1.0R)")
    print("=" * 78)
    primary_n = results["MNQ_proxy (primary)"]["cont"][0]
    print(f"  Trades available on the primary instrument: {primary_n}")
    print("  N needed to detect a true edge at 80% power (sigma ~= 1.0R):")
    print("    0.30R edge: ~N=105 (alpha 0.05) / ~N=170 (alpha 0.025)")
    print("    0.10R edge: ~N=950 (alpha 0.05) / ~N=1,530 (alpha 0.025)")
    print(f"  This run cannot resolve an edge smaller than roughly 0.25-0.30R"
          f" with the {primary_n} trades the data actually provides.")

    print("\n  NOT MEASURED / caveats:")
    print("   - Real Tradovate/Lucid commission and slippage: not verified,"
          " cost run uses a placeholder.")
    print("   - Data is a continuous front-month futures proxy (Yahoo),"
          " not the CQG/Tradovate feed the account would actually trade on.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample"
              " slice (--sample out) has not been looked at.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
