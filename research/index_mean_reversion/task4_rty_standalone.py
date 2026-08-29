#!/usr/bin/env python3
"""
task4_rty_standalone.py - the SAME pre-registered 20d-quintile rule,
computed AND traded purely on RTY=F (Russell 2000 futures) alone: threshold
from RTY's own trailing 504-day distribution, trade on RTY=F itself. No
cash-index data is used anywhere in this script.

Why this exists (distinct question from task3_futures_translation.py)
    Task 3 asks: does a threshold CALIBRATED ON LONG CASH-INDEX HISTORY
    still work when TRADED on the real futures contract?
    Task 4 asks a simpler, more basic question: using ONLY the data that
    was ever actually available to trade Russell 2000 futures (RTY=F on
    Yahoo, ~9.1 years back to 2017-07-10), does the SAME rule independently
    show the same pattern, with no borrowing from the longer cash-index
    history at all? This is the direct futures-only replication, exactly
    the same shape as the original screen_mean_reversion.py test
    (NQ=F/ES=F/YM=F) with RTY=F added as a fourth genuine instrument.

Method
    Imports build_signals, split_dates, filter_sample, non_overlapping,
    report, load directly from screen_mean_reversion.py - identical
    mechanism, parameters, cost model, and statistical tests, not
    redefined. The ONLY new content here is RTY_COST_POINTS (see
    task3_futures_translation.py's docstring - MEASURED directly from
    Tradovate's All-In Rates PDF, CME RTY row) and a FRESH 70/30
    chronological split decided on RTY's OWN eligible signal dates alone
    (not reused from screen_mean_reversion.py's NQ-derived cutoff, nor
    from screen_mean_reversion_deep.py's GSPC-derived cutoff, nor from
    task3's IXIC-derived cutoff - RTY's eligible-date population here is
    smaller and starts far later than any of those, so a shared cutoff
    date would be meaningless).

Known data limitation, stated up front
    RTY=F only goes back to 2017-07-10 on Yahoo's public chart API (verified
    via fetch_data_rty.py's gap check: median 1 calendar day over the last
    ~260 bars, i.e. true daily bars, not the range=max monthly-demotion
    trap already documented in fetch_data.py). That is ~9.1 years, roughly
    2.7x SHORTER than NQ=F/ES=F's ~25 years and about half of YM=F's ~24.3
    years. This will produce a materially smaller in-sample and
    out-of-sample cell count than the original three-instrument test - an
    honest structural consequence of the data actually available for this
    contract, not a shortfall in how it was fetched.

Author: written for the QuantC index mean-reversion hypothesis audit,
Russell-2000-futures-standalone extension.
"""

import argparse
import sys

from screen_mean_reversion import (
    build_signals,
    filter_sample,
    load,
    non_overlapping,
    report,
    split_dates,
)

# MEASURED - see task3_futures_translation.py's docstring for the full
# derivation from Tradovate's All-In Rates PDF (CME RTY row, $50/pt,
# identical $ commission schedule to ES/NQ/YM full-size contracts).
RTY_COST_POINTS = {"free": 0.1152, "monthly": 0.1032, "lifetime": 0.0872}

LABEL = "RTY (Russell2000, futures-only)"
PATH = "data/RTY.csv"
THRESH = 0.025  # unchanged Bonferroni bar, k=2, same reasoning as the original script


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-cost-tier", choices=("free", "monthly", "lifetime"),
                     default="free",
                     help="REAL Tradovate round-turn cost tier (default: free, "
                          "worst-case/most conservative, matches RESULTS.md's primary table)")
    ap.add_argument("--sample", choices=("in", "out", "full"), default="in",
                     help="in = in-sample 70pct (default, safe to re-run); "
                          "out = held-back 30pct, look ONCE; "
                          "full = whole history, final confirmation only")
    args = ap.parse_args()

    dates, opens, closes = load(PATH)
    sig0 = build_signals(dates, opens, closes, cost_bps=0.0)
    cpts = RTY_COST_POINTS[args.real_cost_tier]
    sigc = build_signals(dates, opens, closes, cost_points=cpts)

    # Fresh split decided on RTY's OWN eligible signal dates alone.
    cutoff_date = split_dates([s["date"] for s in sig0])

    if args.sample == "in":
        sample_note = f"IN-SAMPLE (through {cutoff_date})"
    elif args.sample == "out":
        sample_note = (f"*** OUT-OF-SAMPLE (after {cutoff_date}) - "
                        f"LOOK ONCE, DO NOT RE-RUN AFTER CHANGING ANYTHING ***")
    else:
        sample_note = "FULL HISTORY (both slices combined)"

    print("=" * 92)
    print("  TASK 4 - RUSSELL 2000 FUTURES, STANDALONE (own threshold, own trade)")
    print(f"  Data: {PATH}  [{dates[0]} -> {dates[-1]}, n_bars={len(dates)}]")
    print(f"  Sample: {sample_note}")
    print(f"  Fresh split decided on RTY's own eligible dates alone. Cutoff: {cutoff_date}")
    print("  k = 2 (bottom quintile -> long, top quintile -> short)")
    print(f"  Bonferroni threshold = 0.05 / 2 = {THRESH}")
    print(f"  Cost: REAL Tradovate {args.real_cost_tier} plan (MEASURED, CME RTY row)")
    print("=" * 92)

    sig0_f = filter_sample(sig0, cutoff_date, args.sample)
    sigc_f = filter_sample(sigc, cutoff_date, args.sample)

    print(f"\n--- {LABEL} ---")
    res = {}
    for side in ("bottom", "top"):
        s0 = [s["R0"] for s in sig0_f if s["side"] == side]
        sc = [s["Rc"] for s in sigc_f if s["side"] == side]
        n0, m0, p0 = report(LABEL, s0, f"{side} (overlapping, zero-cost)", THRESH)
        nc, mc, pc = report(LABEL, sc, f"{side} (overlapping, real-{args.real_cost_tier})", THRESH)

        sig0_sorted = sorted([s for s in sig0_f if s["side"] == side], key=lambda s: s["date"])
        sigc_sorted = sorted([s for s in sigc_f if s["side"] == side], key=lambda s: s["date"])
        no0 = [s["R0"] for s in non_overlapping(sig0_sorted)]
        noc = [s["Rc"] for s in non_overlapping(sigc_sorted)]
        nno0, mno0, pno0 = report(LABEL, no0, f"{side} (NON-overlap, zero-cost)", THRESH)
        nnoc, mnoc, pnoc = report(LABEL, noc, f"{side} (NON-overlap, real-{args.real_cost_tier})", THRESH)

        res[side] = {
            "overlap_zero": (n0, m0, p0), "overlap_cost": (nc, mc, pc),
            "nonoverlap_zero": (nno0, mno0, pno0), "nonoverlap_cost": (nnoc, mnoc, pnoc),
        }

    print("\n  NOT MEASURED / caveats:")
    print("   - Cost is MEASURED (Tradovate All-In Rates PDF, CME RTY row), applied per-trade")
    print("     using that trade's own entry price. Slippage beyond the quoted all-in rate is")
    print("     NOT MEASURED.")
    print("   - Continuous front-month futures proxy (Yahoo RTY=F), not back-adjusted for roll gaps.")
    print("   - RTY=F's ~9.1y of history is far shorter than NQ/ES's ~25y - sample sizes here")
    print("     are structurally much smaller than the original three-instrument test.")
    print("   - Overlapping-window p-values are optimistic; non-overlapping rows are the ones to trust.")
    if args.sample == "in":
        print("   - This is the IN-SAMPLE slice only. The out-of-sample slice (--sample out)")
        print("     has not been looked at.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
