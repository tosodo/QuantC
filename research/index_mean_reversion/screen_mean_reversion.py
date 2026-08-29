#!/usr/bin/env python3
"""
screen_mean_reversion.py - pre-registered test of the 20d-quintile mean-
reversion hypothesis on stock-index futures.

Hypothesis under test (fixed before this was run, not adjusted afterwards)
    Two-sided, k=2:

    BOTTOM QUINTILE: if the trailing 20-trading-day return sits in the bottom
    quintile of its own trailing 2-year (504 trading day) rolling
    distribution, the FOLLOWING 20-trading-day return is positive.

    TOP QUINTILE: if the trailing 20-day return sits in the top quintile of
    the same trailing distribution, the following 20-day return is negative.

    Both are tested, once each, on three instruments. Neither was chosen
    after looking at results. k=2 -> Bonferroni threshold 0.05/2 = 0.025.

Why this test exists
    domain_priors.md records a MEASURED but never-audited observation: a
    Lo-MacKinlay variance-ratio screen (2026-08-02, `Research/cross_asset_screen
    /step0_screen.py` in ~/Workspace/fp50k-ea) found equity indices to be the
    most mean-reverting asset class studied (mean VR 0.776 at 60 trading days,
    vs 0.840 for the FX control sleeve), and the effect gets STRONGER as the
    horizon lengthens from 5 to 60 days. That was an unconditional,
    unfiltered statistic on the whole return series - it says nothing about
    whether conditioning on an EXTREME recent move, and trading the reversal,
    survives costs or a drawdown-style test. This script is that audit.

Isolation (test_design.md #1)
    Signal decided on the trailing 20-day return through a CLOSED bar (today's
    close). The forward 20-day return is measured strictly after the signal
    day - no lookahead. This is a raw forward-return test, not a stop/target
    trade simulation (a flat ±R framing is awkward for an N-day-forward-return
    hypothesis, per instructions) - but each side is still reported as a
    directional bet: BOTTOM QUINTILE = long, TOP QUINTILE = short, so "R > 0"
    always means "the hypothesis was right" on both sides.

    R-multiple definition: forward 20-day return (long or short, as above)
    divided by that SAME window's own realised volatility
    (sd of the 20 daily log returns inside the window, scaled by sqrt(20)).
    This makes the number comparable to the R-multiples used in the FX audit,
    without inventing a stop distance that was never traded.

Rolling-quintile construction (no lookahead)
    At decision day t: take the 504 trailing 20-day-return OBSERVATIONS
    strictly BEFORE t (i.e. the r20 values computed at t-504 .. t-1). The
    20th/80th percentile of THAT set (never including r20[t] itself) is the
    bottom/top quintile cutoff used to classify r20[t]. This deliberately
    avoids ranking a value against a distribution that contains itself.

Costs (test_design.md #6)
    Zero-cost pass, then a cost-adjusted pass. Cost is a flat round-trip
    basis-point haircut on notional (--cost-bps, default 3.0bps - a
    PLACEHOLDER for commission + slippage on a liquid front-month index
    future; NOT the real Tradovate figure, which is a separate research task
    - see NOT MEASURED at the end).

Overlapping vs non-overlapping (test_design.md #5)
    The 20-day forward windows overlap on every trading day the signal
    fires, so consecutive observations share up to 19 of their 20 return
    days - they are NOT independent, and the overlapping-window t-test
    overstates the effective sample size and understates the true p-value.
    Every run prints BOTH:
      - the overlapping version (every eligible day the signal fires), and
      - a non-overlapping sanity check (signals sampled at a 20-trading-day
        stride, so forward windows never share a day).
    The non-overlapping number is the one to trust; the overlapping number is
    reported because it is what a careless version of this test would have
    reported alone.

Multiple comparisons (test_design.md #4)
    k = 2 (bottom quintile, top quintile). This is a fresh, structurally
    different idea from the six FX/MNQ mechanisms already on record (new
    market class, ~4-week holding period vs intraday/daily) so it does not
    inherit their budget - see domain_priors.md discussion. Bonferroni
    threshold = 0.05 / 2 = 0.025.
    Replication requirement (test_design.md #5): Nasdaq (NQ=F) primary,
    S&P 500 (ES=F) and Dow (YM=F) replication - sign agreement is checked,
    not independently thresholded.

Out-of-sample (test_design.md #8)
    Split decided by chronological position ALONE on the primary instrument's
    eligible signal dates, before any result was inspected: earliest 70% =
    in-sample (developed/inspected freely), most recent 30% = out-of-sample
    (looked at once, via --sample out, reported regardless of outcome). The
    same cutoff DATE is applied to all three instruments.

Known data limitation, stated up front
    ~25 years of daily bars for NQ=F/ES=F (from 2001-08-20), ~24.3 years for
    YM=F (from 2002-04-05) - continuous front-month futures from Yahoo's
    public chart API, NOT back-adjusted for roll gaps (see fetch_data.py
    docstring). This exceeds test_design.md's "8+ years beats 2" preference,
    but the 504-day rolling-quintile lookback burns roughly the first 2 years
    of each series before any signal can fire.

Author: written for the QuantC index mean-reversion hypothesis audit.
"""

import argparse
import csv
import math
import sys


# --------------------------------------------------------------------------
# Student's t two-sided p-value, no scipy (scipy is not installed on this
# machine) - same continued-fraction implementation already used in
# fp50k-ea/tools/edge_stats.py and research/mnq_session_open/screen_session_open.py.
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


def percentile(sorted_vals, pct):
    """Linear-interpolated percentile, pct in [0,1]. sorted_vals must be sorted."""
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    pos = pct * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load(path):
    dates, opens, closes = [], [], []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            dates.append(row["date"])
            opens.append(float(row["open"]))
            closes.append(float(row["close"]))
    return dates, opens, closes


LOOKBACK_R20 = 20      # trailing return horizon (trading days)
LOOKBACK_QUINTILE = 504  # trailing 2-year window over which quintiles are computed
FORWARD = 20            # forward return horizon (trading days)


# ---------------------------------------------------------------------------
# REAL Tradovate costs (2026-08-19 refresh; replaces the 3.0bps placeholder)
#
# Source: Tradovate's own published "All-In Rates" PDF
#   https://www.tradovate.com/TradovateAllInRates120625.pdf
#   (linked from https://www.tradovate.com/pricing/, footer dated
#    "Eurex Exchange Converted at ... Updated 5/2/25" / "NFA Fee ... Updated
#    12/5/25" - fetched and read directly, table below transcribed verbatim).
#
# The PDF's "All In Rate" column is PER SIDE (exchange+NFA+routing+clearing+
# commission, one side of the trade). Round-turn = 2x that figure. Verified
# against the two numbers already confirmed elsewhere in this project:
#   MNQ Free plan:  PDF all-in/side = 0.95  -> RT = $1.90 = 0.95 index pts
#                   (MNQ multiplier $2/pt: 1.90/2 = 0.95pts)  MATCHES.
#   NQ  Free plan:  PDF all-in/side = 2.88  -> RT = $5.76 = 0.288 index pts
#                   (NQ multiplier $20/pt: 5.76/20 = 0.288pts)  MATCHES.
# Same table rows give ES and YM (previously NOT MEASURED in this project):
#   ES (CME, $50/pt) and YM (CBOT, $5/pt) share the IDENTICAL per-side
#   all-in row as NQ in Tradovate's table (2.88/2.58/2.18 Free/Monthly/
#   Lifetime) - the $ commission schedule does not vary by these three
#   full-size index products, only the point value used to convert $ -> pts
#   differs.
#
# Units: ROUND-TURN cost in INDEX POINTS (not dollars, not bps). Index
# points are the same unit this script's Yahoo price series is already in,
# for both the full-size and micro version of the same underlying index
# (NQ and MNQ both quote the Nasdaq-100 in the same points; the $2 vs $20
# multiplier only changes the dollar value of a point, not the point count).
# This makes an index-point cost portable across contract sizes without
# re-deriving anything - MEASURED, not estimated.
# ---------------------------------------------------------------------------
REAL_COST_POINTS = {
    "NQ (Nasdaq, primary)": {"free": 0.288, "monthly": 0.258, "lifetime": 0.218},
    "ES (S&P500, repl.)":   {"free": 0.1152, "monthly": 0.1032, "lifetime": 0.0872},
    "YM (Dow, repl.)":      {"free": 1.152, "monthly": 1.032, "lifetime": 0.872},
}
# Alternate leg: if the Nasdaq side is actually traded as the MICRO (MNQ)
# rather than full-size NQ - same underlying index points, different (higher,
# because the fixed $ fee is a bigger share of a 1/10-size contract) round-
# turn point cost. Included because MNQ is the contract a small prop-firm
# account would realistically use.
MNQ_COST_POINTS = {"free": 0.95, "monthly": 0.85, "lifetime": 0.65}


def build_signals(dates, opens, closes, cost_bps=0.0, cost_points=None):
    """Returns a list of dicts, one per eligible decision day t:
       date, side ('bottom'/'top'/None), R0 (zero-cost), Rc (cost-adjusted).
       Both sides use the sign convention R>0 == hypothesis correct.

    No-lookahead / no-same-bar-re-entry (test_design.md #7): the signal is
    read off the CLOSED bar at day t, but the simulated fill is at day t+1's
    OPEN, never at day t's own close. An earlier version of this script
    entered at day t's close (the same bar used to compute the signal) - the
    exact bug class test_design.md calls out as having inflated an FX result
    by ~0.10R before it was caught. Fixed before any number below was looked
    at as a "result".

    Cost model: EITHER a flat cost_bps (legacy placeholder path, a constant
    fraction of notional applied to every trade regardless of price level)
    OR a fixed cost_points (real Tradovate round-turn cost, quoted in INDEX
    POINTS, converted to that specific trade's own fractional cost using
    ITS OWN entry price). The two are not equivalent once price has moved:
    NQ ranged from ~810 to ~30,700 over this 25-year sample, so a fixed
    point-cost is a ~38x larger fraction of notional in 2003 than in 2026.
    Using cost_points (per-trade, price-aware) is the realistic model;
    cost_bps is kept only to reproduce the original placeholder run.
    """
    n = len(closes)
    logp = [math.log(c) for c in closes]
    logo = [math.log(o) for o in opens]

    # r20[t] defined for t >= LOOKBACK_R20
    r20 = [None] * n
    for t in range(LOOKBACK_R20, n):
        r20[t] = logp[t] - logp[t - LOOKBACK_R20]

    flat_cost_ret = cost_bps / 10000.0
    out = []
    min_t = LOOKBACK_R20 + LOOKBACK_QUINTILE
    # entry at t+1's open, exit at (t+1 + FORWARD - 1)'s close == t+FORWARD's close
    max_t = n - 1 - FORWARD
    for t in range(min_t, max_t + 1):
        window = [r20[k] for k in range(t - LOOKBACK_QUINTILE, t)]  # strictly before t
        window_sorted = sorted(window)
        p20 = percentile(window_sorted, 0.20)
        p80 = percentile(window_sorted, 0.80)
        val = r20[t]

        side = None
        if val <= p20:
            side = "bottom"
        elif val >= p80:
            side = "top"
        if side is None:
            continue

        entry_idx = t + 1
        exit_idx = t + FORWARD  # a FORWARD-trading-day hold starting at entry_idx
        fwd = logp[exit_idx] - logo[entry_idx]  # next-bar-open entry, no lookahead
        daily_rets = [logp[k + 1] - logp[k] for k in range(entry_idx, exit_idx)]
        if len(daily_rets) < 2:
            continue
        m = sum(daily_rets) / len(daily_rets)
        var = sum((x - m) ** 2 for x in daily_rets) / (len(daily_rets) - 1)
        sd_daily = math.sqrt(var)
        horizon_vol = sd_daily * math.sqrt(len(daily_rets))
        if horizon_vol <= 0:
            continue

        if side == "bottom":
            raw0 = fwd
        else:
            raw0 = -fwd

        if cost_points is not None:
            # Real, price-aware cost: fixed round-turn point cost divided by
            # THIS trade's own entry price (opens[entry_idx]), not a flat
            # bps applied uniformly across 25 years of very different price
            # levels.
            trade_cost_ret = cost_points / opens[entry_idx]
        else:
            trade_cost_ret = flat_cost_ret
        rawc = raw0 - trade_cost_ret

        out.append({
            "date": dates[t],
            "side": side,
            "R0": raw0 / horizon_vol,
            "Rc": rawc / horizon_vol,
        })
    return out


def split_dates(all_dates, frac_in_sample=0.70):
    """Chronological 70/30 split, decided by position alone - never by
    looking at any outcome. test_design.md #8."""
    dates = sorted(set(all_dates))
    cut = int(len(dates) * frac_in_sample)
    return dates[cut - 1] if cut > 0 else dates[0]  # cutoff date (last in-sample date)


def filter_sample(signals, cutoff_date, which):
    if which == "in":
        return [s for s in signals if s["date"] <= cutoff_date]
    if which == "out":
        return [s for s in signals if s["date"] > cutoff_date]
    return signals


def non_overlapping(signals, stride=FORWARD):
    """Sample signals at a >= `stride` trading-day gap per side, so forward
    windows never share a day. Signals list must be date-sorted already."""
    out = []
    last_idx_by_side = {}
    for i, s in enumerate(signals):
        side = s["side"]
        last = last_idx_by_side.get(side, -stride)
        if i - last >= stride:
            out.append(s)
            last_idx_by_side[side] = i
    return out


def report(label, values, tag, thresh=None):
    n, mean, sd, t, p = t_test(values)
    mark = ""
    if thresh is not None and not math.isnan(p):
        mark = "  *** clears 0.025 ***" if p < thresh else ""
    print(f"  [{label:22s}] {tag:34s} n={n:5d}  meanR={mean:+.4f}  "
          f"sd={sd:.4f}  t={t:+.3f}  p={p:.4f}{mark}")
    return n, mean, p


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cost-bps", type=float, default=3.0,
                     help="round-trip cost in basis points of notional, applied "
                          "FLAT across the whole sample (legacy PLACEHOLDER path; "
                          "ignored if --real-cost-tier is set)")
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"),
                     default=None,
                     help="use REAL, MEASURED Tradovate round-turn costs "
                          "(source: TradovateAllInRates PDF, see REAL_COST_POINTS "
                          "in this file), applied per-trade using that trade's own "
                          "entry price. Overrides --cost-bps.")
    ap.add_argument("--use-micro-nq", action="store_true",
                     help="with --real-cost-tier, cost the Nasdaq leg as MNQ "
                          "(micro) round-turn points instead of full-size NQ")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample 70pct (default, safe to re-run); "
                          "out = held-back 30pct, look ONCE; "
                          "full = whole history, final confirmation only")
    args = ap.parse_args()

    instruments = [
        ("NQ (Nasdaq, primary)", "data/NQ.csv"),
        ("ES (S&P500, repl.)", "data/ES.csv"),
        ("YM (Dow, repl.)", "data/YM.csv"),
    ]

    # Split decided on the PRIMARY instrument's eligible signal dates alone.
    primary_dates, primary_opens, primary_closes = load(instruments[0][1])
    primary_signals_for_split = build_signals(primary_dates, primary_opens, primary_closes, cost_bps=0.0)
    cutoff_date = split_dates([s["date"] for s in primary_signals_for_split])

    if args.sample == "in":
        sample_note = f"IN-SAMPLE (through {cutoff_date})"
    elif args.sample == "out":
        sample_note = (f"*** OUT-OF-SAMPLE (after {cutoff_date}) - "
                        f"LOOK ONCE, DO NOT RE-RUN AFTER CHANGING ANYTHING ***")
    else:
        sample_note = "FULL HISTORY (both slices combined)"

    thresh = 0.025

    if args.real_cost_tier is not None:
        cost_desc = f"REAL Tradovate {args.real_cost_tier} plan (MEASURED, per-trade, source: TradovateAllInRates PDF)"
    else:
        cost_desc = f"{args.cost_bps} bps round-trip (PLACEHOLDER, not measured)"

    print("=" * 88)
    print("  INDEX 20D-QUINTILE MEAN-REVERSION - pre-registered two-sided screen")
    print(f"  Sample: {sample_note}")
    print("  k = 2 (bottom quintile -> long, top quintile -> short)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {thresh}")
    print(f"  Cost model: {cost_desc}")
    print("=" * 88)

    all_results = {}
    for label, path in instruments:
        dates, opens, closes = load(path)
        sig0 = build_signals(dates, opens, closes, cost_bps=0.0)

        if args.real_cost_tier is not None:
            if label.startswith("NQ") and args.use_micro_nq:
                cpts = MNQ_COST_POINTS[args.real_cost_tier]
            else:
                cpts = REAL_COST_POINTS[label][args.real_cost_tier]
            sigc = build_signals(dates, opens, closes, cost_points=cpts)
            cost_tag = f"real-{args.real_cost_tier}"
        else:
            sigc = build_signals(dates, opens, closes, cost_bps=args.cost_bps)
            cost_tag = f"{args.cost_bps}bps"

        sig0 = filter_sample(sig0, cutoff_date, args.sample)
        sigc = filter_sample(sigc, cutoff_date, args.sample)

        print(f"\n--- {label} ---")
        res = {}
        for side in ("bottom", "top"):
            s0 = [s["R0"] for s in sig0 if s["side"] == side]
            sc = [s["Rc"] for s in sigc if s["side"] == side]
            n0, m0, p0 = report(label, s0, f"{side} (overlapping, zero-cost)", thresh)
            nc, mc, pc = report(label, sc, f"{side} (overlapping, {cost_tag})", thresh)

            # non-overlapping sanity check, on the zero-cost and cost series
            sig0_side_sorted = sorted([s for s in sig0 if s["side"] == side], key=lambda s: s["date"])
            sigc_side_sorted = sorted([s for s in sigc if s["side"] == side], key=lambda s: s["date"])
            no0 = [s["R0"] for s in non_overlapping(sig0_side_sorted)]
            noc = [s["Rc"] for s in non_overlapping(sigc_side_sorted)]
            nno0, mno0, pno0 = report(label, no0, f"{side} (NON-overlap, zero-cost)", thresh)
            nnoc, mnoc, pnoc = report(label, noc, f"{side} (NON-overlap, {cost_tag})", thresh)

            res[side] = {
                "overlap_zero": (n0, m0, p0),
                "overlap_cost": (nc, mc, pc),
                "nonoverlap_zero": (nno0, mno0, pno0),
                "nonoverlap_cost": (nnoc, mnoc, pnoc),
            }
        all_results[label] = res

    print("\n" + "=" * 88)
    print("  REPLICATION CHECK (sign agreement across 3 instruments, non-overlapping zero-cost)")
    print("=" * 88)
    for side in ("bottom", "top"):
        signs = {}
        for label, _ in instruments:
            m = all_results[label][side]["nonoverlap_zero"][1]
            signs[label] = (1 if m > 0 else (-1 if m < 0 else 0))
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        print(f"  {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n" + "=" * 88)
    print("  SAMPLE SIZE REALITY CHECK (test_design.md #9, sigma ~= 1.0R)")
    print("=" * 88)
    primary_bottom_n = all_results[instruments[0][0]]["bottom"]["nonoverlap_zero"][0]
    primary_top_n = all_results[instruments[0][0]]["top"]["nonoverlap_zero"][0]
    print(f"  Non-overlapping trades available, primary instrument: "
          f"bottom={primary_bottom_n}  top={primary_top_n}")
    print("  N needed to detect a true edge at 80% power, alpha=0.025 (2-sided), sigma~=1.0R:")
    print("    0.30R edge: ~N=170   0.20R edge: ~N=380   0.10R edge: ~N=1,530")
    print(f"  With ~{primary_bottom_n}-{primary_top_n} non-overlapping trades per side, this run "
          f"can resolve roughly a 0.3-0.4R edge at 80% power - smaller true edges will show up "
          f"as 'not significant' even if real.")

    print("\n  NOT MEASURED / caveats:")
    if args.real_cost_tier is not None:
        print("   - Cost is MEASURED (Tradovate All-In Rates PDF) and applied per-trade"
              " using that trade's own entry price. Slippage beyond the quoted"
              " exchange/NFA/routing/clearing/commission all-in rate is NOT MEASURED"
              " (spread-crossing cost on a resting vs. market order, fill quality)"
              " - the real number could be somewhat higher than shown here.")
    else:
        print("   - Real Tradovate/broker commission: not verified in this run,"
              " cost uses a flat bps placeholder.")
    print("   - Continuous front-month futures proxy (Yahoo), not back-adjusted"
          " for roll gaps, not the CQG/Tradovate feed the account would trade on.")
    print("   - Overlapping-window p-values are optimistic (autocorrelated"
          " observations); the non-overlapping rows are the ones to trust.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample"
              " slice (--sample out) has not been looked at.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
