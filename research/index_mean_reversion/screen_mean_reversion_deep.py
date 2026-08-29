#!/usr/bin/env python3
"""
screen_mean_reversion_deep.py - re-test of the SAME pre-registered 20d-
quintile mean-reversion hypothesis (screen_mean_reversion.py), on much
longer cash-index history, as an audit of whether the original
promising_but_unproven finding holds up on cleaner, deeper data.

THE RULE IS UNCHANGED. This script imports build_signals, t_test,
percentile, non_overlapping, split_dates, filter_sample, and report
DIRECTLY from screen_mean_reversion.py rather than re-deriving them, so the
signal construction, R-multiple definition, no-lookahead entry timing,
overlap/non-overlap logic, and t-test math are byte-for-byte identical to
the original, audited script. Nothing about the mechanism, parameters,
horizons, or statistical tests has been changed. Only the DATA changed:

    Original (screen_mean_reversion.py): NQ=F/ES=F/YM=F continuous
        FUTURES, ~24-25 years of history (from 2001-08-20/2002-04-05).
    This script: ^GSPC/^IXIC/^RUT CASH INDICES, 39-57 years of history
        (from 1970-01-02/1971-02-05/1987-09-10), fetched via
        fetch_data_cash.py.

Why this exists
    The original run's biggest stated limitation was sample size: 16-18
    out-of-sample trades per cell, "can resolve roughly a 0.3-0.4R edge at
    80% power - smaller true edges will show up as 'not significant' even
    if real" (screen_mean_reversion.py output). Cash indices give 2-3x the
    calendar history of the futures proxies, which is the single lever
    available to add real (non-overlapping) trades without changing
    anything about the rule itself.

Costs - IMPORTANT CAVEAT
    There is no Tradovate (or any other broker) commission table for a cash
    index - you cannot literally trade ^GSPC/^IXIC/^RUT, they are index
    levels, not tradable contracts. Per the task instructions, the
    cost-adjusted pass here REUSES the existing REAL_COST_POINTS figures
    from screen_mean_reversion.py as the closest available proxy, applied
    per-trade using that trade's own entry price exactly as the original
    script does (cost_points / entry_price). Mapping (by index family,
    the only non-arbitrary pairing available):
        ^GSPC (S&P 500)        -> ES real-cost-points (S&P 500 e-mini)
        ^IXIC (Nasdaq Comp.)   -> NQ real-cost-points (Nasdaq-100 e-mini)
        ^RUT  (Russell 2000)   -> YM real-cost-points (Dow e-mini) - WEAKEST
            proxy of the three: there is no Russell-2000 futures cost
            already measured in this project, so YM is used only because
            it is the one remaining tier in REAL_COST_POINTS, not because
            Dow and Russell-2000 are economically comparable instruments.
    This is explicitly an APPROXIMATION, not a measured cost for any of
    these three series. Labeled NOT MEASURED throughout the output and in
    RESULTS_DEEP.md.

Multiple comparisons
    Same k=2 logic as the original (bottom quintile / top quintile), on
    this new set of 3 instruments. This is the SAME hypothesis re-tested on
    different data, not a new fishing expedition, so it does not get a
    fresh multiple-comparisons budget stacked on top of the original run -
    per test_design.md's reasoning (screen_mean_reversion.py lines 72-77),
    k=2, Bonferroni threshold = 0.05/2 = 0.025, unchanged.

Out-of-sample
    Same discipline as the original: split decided by chronological
    position alone on the PRIMARY instrument's (GSPC) eligible signal
    dates, before any result was inspected, 70% in-sample / 30%
    out-of-sample. The out-of-sample slice is a brand-new dataset never
    inspected before this task - looked at exactly once, per instrument,
    reported regardless of outcome.

Author: written for the QuantC index mean-reversion hypothesis audit,
deep-history extension.
"""

import sys

from screen_mean_reversion import (
    FORWARD,
    REAL_COST_POINTS,
    build_signals,
    filter_sample,
    load,
    non_overlapping,
    report,
    split_dates,
)

# Cash-index -> proxy futures-cost-table key mapping (see module docstring).
COST_PROXY = {
    "GSPC (S&P500 cash)":     "ES (S&P500, repl.)",
    "IXIC (Nasdaq Comp cash)": "NQ (Nasdaq, primary)",
    "RUT (Russell2000 cash)": "YM (Dow, repl.)",
}

INSTRUMENTS = [
    ("GSPC (S&P500 cash)", "data/GSPC.csv"),
    ("IXIC (Nasdaq Comp cash)", "data/IXIC.csv"),
    ("RUT (Russell2000 cash)", "data/RUT.csv"),
]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"),
                     default="free",
                     help="which REAL_COST_POINTS tier to use as the cost-adjusted "
                          "pass proxy (default: free, the worst-case/most conservative "
                          "tier, matching the primary table in RESULTS.md)")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample 70pct (default, safe to re-run); "
                          "out = held-back 30pct, look ONCE; "
                          "full = whole history, final confirmation only")
    args = ap.parse_args()

    # Split decided on the PRIMARY instrument's (GSPC) eligible signal dates
    # alone, same discipline as the original script.
    primary_label, primary_path = INSTRUMENTS[0]
    primary_dates, primary_opens, primary_closes = load(primary_path)
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
    cost_desc = (f"PROXY cost (REAL_COST_POINTS['{{proxy}}']['{args.real_cost_tier}'] "
                 f"from screen_mean_reversion.py, applied per-trade using this trade's "
                 f"own entry price - APPROXIMATION, not a measured cash-index cost)")

    print("=" * 88)
    print("  INDEX 20D-QUINTILE MEAN-REVERSION - DEEP-HISTORY CASH-INDEX RE-TEST")
    print("  SAME rule, SAME parameters, SAME cost model, SAME stat tests as")
    print("  screen_mean_reversion.py - only the underlying data changed.")
    print(f"  Sample: {sample_note}")
    print("  k = 2 (bottom quintile -> long, top quintile -> short)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {thresh}")
    print(f"  Cost tier: {args.real_cost_tier} (see COST_PROXY mapping, APPROXIMATION)")
    print("=" * 88)

    all_results = {}
    for label, path in INSTRUMENTS:
        dates, opens, closes = load(path)
        sig0 = build_signals(dates, opens, closes, cost_bps=0.0)

        proxy_key = COST_PROXY[label]
        cpts = REAL_COST_POINTS[proxy_key][args.real_cost_tier]
        sigc = build_signals(dates, opens, closes, cost_points=cpts)
        cost_tag = f"proxy-{proxy_key.split()[0]}-{args.real_cost_tier}"

        sig0 = filter_sample(sig0, cutoff_date, args.sample)
        sigc = filter_sample(sigc, cutoff_date, args.sample)

        print(f"\n--- {label}  [first bar {dates[0]}, last bar {dates[-1]}, n_bars={len(dates)}] ---")
        print(f"    cost proxy: {proxy_key} @ {args.real_cost_tier} = {cpts} pts/round-turn")
        res = {}
        for side in ("bottom", "top"):
            s0 = [s["R0"] for s in sig0 if s["side"] == side]
            sc = [s["Rc"] for s in sigc if s["side"] == side]
            n0, m0, p0 = report(label, s0, f"{side} (overlapping, zero-cost)", thresh)
            nc, mc, pc = report(label, sc, f"{side} (overlapping, {cost_tag})", thresh)

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
    print("  REPLICATION CHECK (sign agreement across 3 cash indices, non-overlapping zero-cost)")
    print("=" * 88)
    for side in ("bottom", "top"):
        signs = {}
        for label, _ in INSTRUMENTS:
            m = all_results[label][side]["nonoverlap_zero"][1]
            signs[label] = (1 if m > 0 else (-1 if m < 0 else 0))
        agree = len(set(signs.values())) == 1 and 0 not in signs.values()
        print(f"  {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n" + "=" * 88)
    print("  SAMPLE SIZE REALITY CHECK (sigma ~= 1.0R)")
    print("=" * 88)
    primary_bottom_n = all_results[INSTRUMENTS[0][0]]["bottom"]["nonoverlap_zero"][0]
    primary_top_n = all_results[INSTRUMENTS[0][0]]["top"]["nonoverlap_zero"][0]
    print(f"  Non-overlapping trades available, primary instrument (GSPC): "
          f"bottom={primary_bottom_n}  top={primary_top_n}")
    print("  N needed to detect a true edge at 80% power, alpha=0.025 (2-sided), sigma~=1.0R:")
    print("    0.30R edge: ~N=170   0.20R edge: ~N=380   0.10R edge: ~N=1,530")

    print("\n  NOT MEASURED / caveats:")
    print("   - Cost-adjusted pass uses PROXY futures costs (ES/NQ/YM real-cost-points "
          "from screen_mean_reversion.py's REAL_COST_POINTS), NOT a measured cash-index "
          "trading cost - cash indices are not directly tradable. Approximation only.")
    print("   - Cash-index levels are raw price-return series (not total-return, not "
          "back-adjusted for anything) - this is the standard Yahoo ^GSPC/^IXIC/^RUT feed.")
    print("   - Overlapping-window p-values are optimistic (autocorrelated observations); "
          "the non-overlapping rows are the ones to trust.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample slice "
              "(--sample out) has not been looked at.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
