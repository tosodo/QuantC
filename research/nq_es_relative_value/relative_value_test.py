#!/usr/bin/env python3
"""
relative_value_test.py - pre-registered test of the NQ-vs-ES relative-value
hypothesis (see HYPOTHESIS.md in this folder). Reuses the exact t-test,
percentile, non-overlapping, split, and cost machinery already built and
audited in research/index_mean_reversion/screen_mean_reversion.py - not
reimplemented, imported directly, so this test inherits the same discipline
(no-lookahead, non-overlapping-is-the-trustworthy-number, per-trade t-test
not Sharpe/win-rate).

Hypothesis under test (fixed in HYPOTHESIS.md before this was run)
    Spread = log(NQ close) - log(ES close).
    Z[t] = (spread[t] - mean(spread[t-N:t])) / stdev(spread[t-N:t]), using
    only the N days strictly BEFORE t (today's own spread is not inside its
    own normalisation window).
    Z[t] is then classified against the 20th/80th percentile of ITS OWN
    trailing 504-day distribution (strictly before t) - the exact same
    quintile machinery as the original test, just fed Z instead of r20.

    BOTTOM quintile (NQ cheap vs ES) -> predicts spread widens (long NQ /
    short ES).
    TOP quintile (NQ rich vs ES) -> predicts spread narrows (short NQ /
    long ES).

    3 parameters total: N=20 (Z window), 504 (quintile window), FORWARD=20
    (holding horizon) - reused verbatim from the original test's values,
    not re-tuned for this hypothesis.

Isolation
    Flat size both legs (dollar-notional matched at each leg's own entry
    price - see HYPOTHESIS.md #4), fixed holding period, no stop/target.
    Entry at t+1's open (both legs), exit at t+FORWARD's close (both legs).

Cost
    Real, MEASURED Tradovate round-turn cost on BOTH legs (same
    REAL_COST_POINTS table as the original test), each leg's cost converted
    to a fractional return using THAT leg's own entry price, summed.

Replication
    NQ-vs-ES is primary. NQ-vs-YM is the replication pair (tech-heavy vs.
    industrial-heavy, not just a second look at the same relationship).
    Each pair gets its OWN freshly-decided 70/30 chronological split on its
    OWN eligible-date population - the ES-pair cutoff is not reused for the
    YM-pair.

Regime sanity check (HYPOTHESIS.md #3)
    Before the significance numbers are read, this script reports how many
    times Z crosses zero over the full history. Frequent crossings ==
    behaviour consistent with reversion; a handful of crossings over 20+
    years would mean the spread mostly just trended, and the significance
    test below should be read with that in mind.

Usage
    python3 relative_value_test.py                # in-sample (default)
    python3 relative_value_test.py --sample out    # held-back slice, look ONCE
"""

import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr

Z_WINDOW = 20            # trailing window used to normalise the spread into a Z-score
QUINTILE_WINDOW = 504    # trailing 2-year window the Z-score is classified against
FORWARD = 20             # holding horizon, trading days

PAIRS = [
    ("NQ vs ES (primary)", "NQ (Nasdaq, primary)", "ES (S&P500, repl.)",
     os.path.join(MEAN_REV_DIR, "data/NQ.csv"), os.path.join(MEAN_REV_DIR, "data/ES.csv")),
    ("NQ vs YM (replication)", "NQ (Nasdaq, primary)", "YM (Dow, repl.)",
     os.path.join(MEAN_REV_DIR, "data/NQ.csv"), os.path.join(MEAN_REV_DIR, "data/YM.csv")),
]


def align(dates_a, opens_a, closes_a, dates_b, opens_b, closes_b):
    """Restrict both series to dates present in both, chronological order."""
    idx_a = {d: i for i, d in enumerate(dates_a)}
    idx_b = {d: i for i, d in enumerate(dates_b)}
    common = sorted(set(dates_a) & set(dates_b))
    oa = [opens_a[idx_a[d]] for d in common]
    ca = [closes_a[idx_a[d]] for d in common]
    ob = [opens_b[idx_b[d]] for d in common]
    cb = [closes_b[idx_b[d]] for d in common]
    return common, oa, ca, ob, cb


def zero_crossings(z_values):
    """Count how often a valid Z series crosses zero - crude reversion-vs-
    trend diagnostic, no scipy/statsmodels available on this machine."""
    vals = [z for z in z_values if z is not None]
    crossings = 0
    for i in range(1, len(vals)):
        if (vals[i - 1] < 0) != (vals[i] < 0):
            crossings += 1
    return crossings, len(vals)


def build_signals(dates, opens_a, closes_a, opens_b, closes_b, cost_points_a=None, cost_points_b=None):
    """Mirrors smr.build_signals structure exactly, fed the A-vs-B spread
    instead of a single instrument's own return. Returns signals list plus
    the raw Z series (for the regime sanity check)."""
    n = len(dates)
    logpa = [math.log(c) for c in closes_a]
    logoa = [math.log(o) for o in opens_a]
    logpb = [math.log(c) for c in closes_b]
    logob = [math.log(o) for o in opens_b]
    spread = [logpa[i] - logpb[i] for i in range(n)]

    z = [None] * n
    for t in range(Z_WINDOW, n):
        window = spread[t - Z_WINDOW:t]  # strictly before t
        m = sum(window) / len(window)
        var = sum((x - m) ** 2 for x in window) / max(len(window) - 1, 1)
        sd = math.sqrt(var)
        z[t] = (spread[t] - m) / sd if sd > 0 else None

    out = []
    min_t = Z_WINDOW + QUINTILE_WINDOW
    max_t = n - 1 - FORWARD
    for t in range(min_t, max_t + 1):
        if z[t] is None:
            continue
        window = [z[k] for k in range(t - QUINTILE_WINDOW, t) if z[k] is not None]
        if len(window) < QUINTILE_WINDOW // 2:
            continue
        window_sorted = sorted(window)
        p20 = smr.percentile(window_sorted, 0.20)
        p80 = smr.percentile(window_sorted, 0.80)
        val = z[t]

        side = None
        if val <= p20:
            side = "bottom"
        elif val >= p80:
            side = "top"
        if side is None:
            continue

        entry_idx = t + 1
        exit_idx = t + FORWARD
        fwd = (logpa[exit_idx] - logoa[entry_idx]) - (logpb[exit_idx] - logob[entry_idx])
        daily_rets = [(logpa[k + 1] - logpa[k]) - (logpb[k + 1] - logpb[k])
                      for k in range(entry_idx, exit_idx)]
        if len(daily_rets) < 2:
            continue
        m = sum(daily_rets) / len(daily_rets)
        var = sum((x - m) ** 2 for x in daily_rets) / (len(daily_rets) - 1)
        horizon_vol = math.sqrt(var) * math.sqrt(len(daily_rets))
        if horizon_vol <= 0:
            continue

        raw0 = fwd if side == "bottom" else -fwd

        if cost_points_a is not None and cost_points_b is not None:
            cost_ret = cost_points_a / opens_a[entry_idx] + cost_points_b / opens_b[entry_idx]
        else:
            cost_ret = 0.0
        rawc = raw0 - cost_ret

        out.append({
            "date": dates[t],
            "side": side,
            "R0": raw0 / horizon_vol,
            "Rc": rawc / horizon_vol,
        })
    return out, z


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"),
                     default="free",
                     help="real Tradovate round-turn cost tier applied to BOTH legs "
                          "(default: free, most conservative - no plan purchased)")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample 70pct (default, safe to re-run); "
                          "out = held-back 30pct, look ONCE; "
                          "full = whole history, final confirmation only")
    args = ap.parse_args()

    thresh = 0.025
    print("=" * 88)
    print("  NQ-vs-ES / NQ-vs-YM RELATIVE VALUE - pre-registered two-sided screen")
    print("  (see HYPOTHESIS.md - this is the plan the user approved, run verbatim)")
    print(f"  k = 2 (bottom quintile -> long spread, top quintile -> short spread)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {thresh}  (fresh budget, not shared "
          "with the single-instrument mean-reversion test)")
    print(f"  Cost model: REAL Tradovate {args.real_cost_tier} plan, BOTH legs, "
          "MEASURED (TradovateAllInRates PDF), per-trade at each leg's own entry price")
    print("=" * 88)

    all_results = {}
    for pair_label, label_a, label_b, path_a, path_b in PAIRS:
        dates_a, opens_a, closes_a = smr.load(path_a)
        dates_b, opens_b, closes_b = smr.load(path_b)
        dates, oa, ca, ob, cb = align(dates_a, opens_a, closes_a, dates_b, opens_b, closes_b)

        cutoff_date = smr.split_dates(dates)  # fresh split, decided on THIS pair's own dates

        cpa0 = smr.REAL_COST_POINTS[label_a][args.real_cost_tier]
        cpb0 = smr.REAL_COST_POINTS[label_b][args.real_cost_tier]

        sig0, z = build_signals(dates, oa, ca, ob, cb)
        sigc, _ = build_signals(dates, oa, ca, ob, cb, cost_points_a=cpa0, cost_points_b=cpb0)

        crossings, n_valid = zero_crossings(z)

        if args.sample == "in":
            sample_note = f"IN-SAMPLE (through {cutoff_date})"
        elif args.sample == "out":
            sample_note = f"*** OUT-OF-SAMPLE (after {cutoff_date}) - LOOK ONCE ***"
        else:
            sample_note = "FULL HISTORY (both slices combined)"

        print(f"\n--- {pair_label} --- sample: {sample_note}")
        print(f"  Aligned trading days: {len(dates)}  "
              f"({dates[0]} -> {dates[-1]})")
        print(f"  Regime sanity check: Z crossed zero {crossings} times over "
              f"{n_valid} valid days (~{crossings / max(n_valid / 252.0, 0.01):.1f} "
              f"crossings/year) - frequent crossings support reversion, a handful "
              f"over decades would mean mostly trending.")

        sig0f = smr.filter_sample(sig0, cutoff_date, args.sample)
        sigcf = smr.filter_sample(sigc, cutoff_date, args.sample)

        res = {}
        for side in ("bottom", "top"):
            s0 = [s["R0"] for s in sig0f if s["side"] == side]
            sc = [s["Rc"] for s in sigcf if s["side"] == side]
            smr.report(pair_label, s0, f"{side} (overlapping, zero-cost)", thresh)
            smr.report(pair_label, sc, f"{side} (overlapping, real-{args.real_cost_tier})", thresh)

            s0_sorted = sorted([s for s in sig0f if s["side"] == side], key=lambda s: s["date"])
            sc_sorted = sorted([s for s in sigcf if s["side"] == side], key=lambda s: s["date"])
            no0 = [s["R0"] for s in smr.non_overlapping(s0_sorted, stride=FORWARD)]
            noc = [s["Rc"] for s in smr.non_overlapping(sc_sorted, stride=FORWARD)]
            n0, m0, p0 = smr.report(pair_label, no0, f"{side} (NON-overlap, zero-cost)", thresh)
            nc, mc, pc = smr.report(pair_label, noc, f"{side} (NON-overlap, real-{args.real_cost_tier})", thresh)
            res[side] = {"nonoverlap_zero": (n0, m0, p0), "nonoverlap_cost": (nc, mc, pc)}
        all_results[pair_label] = res

    print("\n" + "=" * 88)
    print("  REPLICATION CHECK (sign agreement, NQ-vs-ES primary vs NQ-vs-YM, "
          "non-overlapping zero-cost)")
    print("=" * 88)
    for side in ("bottom", "top"):
        signs = {}
        for pair_label, *_ in PAIRS:
            m = all_results[pair_label][side]["nonoverlap_zero"][1]
            signs[pair_label] = 1 if m > 0 else (-1 if m < 0 else 0)
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        print(f"  {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n  NOT MEASURED / caveats:")
    print("   - Leg sizing assumed equal dollar-notional (log-return spread), not a "
          "beta/regression hedge ratio - a real design choice, not free of debate.")
    print("   - Cost is the quoted exchange/NFA/routing/clearing/commission all-in "
          "rate on both legs; slippage beyond that (resting vs market order, fill "
          "quality on 2 simultaneous legs) is NOT MEASURED.")
    print("   - Continuous front-month futures proxy (Yahoo), not back-adjusted for "
          "roll gaps, on either leg.")
    print("   - Overlapping-window p-values are optimistic; non-overlapping rows are "
          "the ones to trust.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample slice "
              "(--sample out) has not been looked at.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
