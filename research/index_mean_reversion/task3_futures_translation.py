#!/usr/bin/env python3
"""
task3_futures_translation.py - TRANSLATION/VALIDATION check, not a new
hypothesis. The rule itself is not changed in any way.

Question this answers
    screen_mean_reversion_deep.py found a STRONGER version of the
    pre-registered 20d-quintile mean-reversion rule when tested on the long
    cash-index history (^GSPC/^IXIC/^RUT, 39-57 years): 3 of 6 out-of-sample
    cells cleared the Bonferroni bar, vs. 1 of 6 on the original ~25-year
    NQ=F/ES=F/YM=F futures test, with 12/12 sign agreement.

    But nobody can trade a cash index. Only the futures contract is
    tradable on Tradovate. So: does the STRONGER signal survive when the
    THRESHOLD is calibrated on the long cash-index history (more data ->
    a better-estimated quintile cutoff) but the TRADE is simulated on the
    real tradable futures contract (real entry/exit prices, real Tradovate
    costs)? That is what this script tests.

Method (byte-for-byte reuse of screen_mean_reversion.py's constants and
math - nothing about the rule, parameters, or formulas is redefined here)
    1. For each of 3 legs (Nasdaq: IXIC->NQ, S&P: GSPC->ES,
       Russell: RUT->RTY):
       a. Classify every eligible decision day t in the CASH-INDEX series
          using LOOKBACK_R20/LOOKBACK_QUINTILE/percentile imported directly
          from screen_mean_reversion.py - identical rolling-quintile
          construction, no lookahead (same as build_signals()'s internal
          classification step, decoupled here only because the trade will
          be executed on a DIFFERENT series).
       b. For every signal date d, look up the SAME calendar date in the
          FUTURES series. If found, simulate entry at the futures' next
          trading day's open and exit at the close FORWARD (20) futures
          trading days later, cost = real Tradovate round-turn points /
          that trade's own futures entry price, R-multiple = the exact
          formula in build_signals() (copied verbatim into
          simulate_futures_trade() below, not reinvented).
       c. If d has no matching futures trading day - either because it
          predates the futures data entirely, or a holiday/data-gap
          mismatch within the overlapping range, or the trade would need
          bars past the end of the futures data - the signal is SKIPPED
          and counted (printed per leg, not hidden).
    2. Split: a FRESH chronological 70/30 cutoff, decided by POSITION ALONE
       on the Nasdaq leg's (IXIC->NQ) successfully-translated trade dates -
       this is a different eligible-date population from either prior
       script's split and is NOT reused from them. The same cutoff date is
       then applied to all three legs (same convention as both prior
       scripts: one primary-instrument-derived cutoff, applied uniformly).
       Decided before any result was inspected; the out-of-sample slice is
       reported exactly once, regardless of outcome.
    3. Real-cost only (Tradovate Free-plan tier, the worst-case/most
       conservative tier already used as the primary tier in RESULTS.md and
       RESULTS_DEEP.md) - the zero-cost pass is skipped per the task
       instructions, because the question here is specifically "will this
       survive real costs on the real contract."

RTY real-cost points (MEASURED, not approximated - see task2 note below)
    CME RTY (full-size E-Mini Russell 2000, $50/pt) IS listed in Tradovate's
    All-In Rates PDF (https://www.tradovate.com/TradovateAllInRates120625.pdf,
    fetched 2026-08-19): per-side all-in Free/Monthly/Lifetime = 2.88/2.58/
    2.18 - IDENTICAL dollar figures to ES's row (same Exchange&NFA=1.40 and
    commission schedule for all full-size index products; RTY and ES also
    share the same $50/pt multiplier), so RTY's round-turn point cost comes
    out numerically identical to ES's: 0.1152/0.1032/0.0872 pts. This is a
    coincidence of Tradovate's fee schedule (flat $ fee across full-size
    index products, same multiplier), not an assumption - verified directly
    against the PDF table, not carried over from YM as an approximation.
    M2K (Micro E-Mini Russell, $5/pt) is also listed: 0.95/0.85/0.65 per
    side -> round-turn points 0.38/0.34/0.26 (included for completeness,
    not used in this script's trades, which use full-size RTY).

Author: written for the QuantC index mean-reversion futures-translation
validation check.
"""

import math
import sys

from screen_mean_reversion import (
    FORWARD,
    LOOKBACK_QUINTILE,
    LOOKBACK_R20,
    REAL_COST_POINTS,
    filter_sample,
    load,
    non_overlapping,
    percentile,
    report,
    split_dates,
)

# MEASURED (see module docstring): CME RTY row, TradovateAllInRates120625.pdf.
RTY_COST_POINTS = {"free": 0.1152, "monthly": 0.1032, "lifetime": 0.0872}
# MEASURED, included for reference (not used for trades in this script).
M2K_COST_POINTS = {"free": 0.38, "monthly": 0.34, "lifetime": 0.26}

LEGS = [
    ("Nasdaq (IXIC->NQ)", "data/IXIC.csv", "data/NQ.csv", REAL_COST_POINTS["NQ (Nasdaq, primary)"]),
    ("S&P500 (GSPC->ES)", "data/GSPC.csv", "data/ES.csv", REAL_COST_POINTS["ES (S&P500, repl.)"]),
    ("Russell (RUT->RTY)", "data/RUT.csv", "data/RTY.csv", RTY_COST_POINTS),
]

COST_TIER = "free"  # worst-case/most conservative tier, matches RESULTS.md's primary table
THRESH = 0.025  # unchanged Bonferroni bar, k=2, same reasoning as both prior scripts


def classify_index_signals(dates, closes):
    """Decouples the CLASSIFICATION half of build_signals() from its trade
    half. Uses the exact same LOOKBACK_R20 / LOOKBACK_QUINTILE / percentile
    construction (imported, not redefined) to flag every eligible decision
    day t in an index series as 'bottom' / 'top' / None - no lookahead,
    same "504 trailing observations strictly before t" rule as the
    original. Does NOT compute a forward window here (that happens on the
    FUTURES series instead, in simulate_futures_trade below) - this is the
    necessary decoupling the task calls for, not a change to the rule.
    """
    n = len(closes)
    logp = [math.log(c) for c in closes]
    r20 = [None] * n
    for t in range(LOOKBACK_R20, n):
        r20[t] = logp[t] - logp[t - LOOKBACK_R20]

    out = []
    min_t = LOOKBACK_R20 + LOOKBACK_QUINTILE
    for t in range(min_t, n):
        window = sorted(r20[k] for k in range(t - LOOKBACK_QUINTILE, t))
        p20 = percentile(window, 0.20)
        p80 = percentile(window, 0.80)
        val = r20[t]
        side = None
        if val <= p20:
            side = "bottom"
        elif val >= p80:
            side = "top"
        if side is not None:
            out.append({"date": dates[t], "side": side})
    return out


def simulate_futures_trade(fut_logp, fut_logo, fut_opens, t_fut, side, cost_points):
    """R-multiple math copied VERBATIM from build_signals() in
    screen_mean_reversion.py (same entry-at-next-open, same forward-window
    realised-vol scaling, same cost-per-trade-at-own-entry-price model) -
    not reinvented, only re-parameterized to take an externally-supplied
    decision index t_fut (the futures array position of the signal's
    calendar date) instead of computing t internally from the same series.
    Returns None if the FORWARD-day window runs past the end of the futures
    data (signal too close to the data frontier)."""
    n = len(fut_opens)
    entry_idx = t_fut + 1
    exit_idx = t_fut + FORWARD
    if entry_idx >= n or exit_idx >= n:
        return None
    fwd = fut_logp[exit_idx] - fut_logo[entry_idx]
    daily_rets = [fut_logp[k + 1] - fut_logp[k] for k in range(entry_idx, exit_idx)]
    if len(daily_rets) < 2:
        return None
    m = sum(daily_rets) / len(daily_rets)
    var = sum((x - m) ** 2 for x in daily_rets) / (len(daily_rets) - 1)
    sd_daily = math.sqrt(var)
    horizon_vol = sd_daily * math.sqrt(len(daily_rets))
    if horizon_vol <= 0:
        return None

    raw0 = fwd if side == "bottom" else -fwd
    trade_cost_ret = cost_points / fut_opens[entry_idx]
    rawc = raw0 - trade_cost_ret
    return raw0 / horizon_vol, rawc / horizon_vol


def build_translated_trades(index_path, fut_path, cost_points_table, tier):
    idx_dates, _idx_opens, idx_closes = load(index_path)
    fut_dates, fut_opens, fut_closes = load(fut_path)

    fut_date_to_idx = {d: i for i, d in enumerate(fut_dates)}
    fut_first, fut_last = fut_dates[0], fut_dates[-1]
    fut_logp = [math.log(c) for c in fut_closes]
    fut_logo = [math.log(o) for o in fut_opens]

    index_signals = classify_index_signals(idx_dates, idx_closes)

    trades = []
    skip_out_of_range = 0   # signal date predates or postdates the futures data entirely
    skip_holiday = 0        # date within futures range but no matching futures bar
    skip_near_end = 0       # matched, but FORWARD-day window runs past the data frontier
    cost_points = cost_points_table[tier]

    for s in index_signals:
        d, side = s["date"], s["side"]
        if d < fut_first or d > fut_last:
            skip_out_of_range += 1
            continue
        if d not in fut_date_to_idx:
            skip_holiday += 1
            continue
        t_fut = fut_date_to_idx[d]
        result = simulate_futures_trade(fut_logp, fut_logo, fut_opens, t_fut, side, cost_points)
        if result is None:
            skip_near_end += 1
            continue
        r0, rc = result
        trades.append({"date": d, "side": side, "R0": r0, "Rc": rc})

    skip_info = {
        "n_index_signals": len(index_signals),
        "n_translated": len(trades),
        "skip_out_of_range": skip_out_of_range,
        "skip_holiday": skip_holiday,
        "skip_near_end": skip_near_end,
        "fut_first": fut_first,
        "fut_last": fut_last,
    }
    return trades, skip_info


def main():
    print("=" * 92)
    print("  TASK 3 - CASH-INDEX-CALIBRATED SIGNAL, TRADED ON REAL FUTURES")
    print("  (translation/validation check - the rule is UNCHANGED)")
    print(f"  Cost: REAL Tradovate {COST_TIER} plan (MEASURED), per-trade at that trade's own")
    print("  futures entry price. Real-cost only (zero-cost pass skipped per task instructions).")
    print(f"  Bonferroni threshold = 0.05 / 2 = {THRESH}")
    print("=" * 92)

    all_trades = {}
    all_skip = {}
    for label, index_path, fut_path, cost_table in LEGS:
        trades, skip_info = build_translated_trades(index_path, fut_path, cost_table, COST_TIER)
        trades.sort(key=lambda s: s["date"])
        all_trades[label] = trades
        all_skip[label] = skip_info
        print(f"\n--- {label} ---")
        print(f"    futures data range: {skip_info['fut_first']} -> {skip_info['fut_last']}")
        print(f"    index-side eligible signals: {skip_info['n_index_signals']}")
        print(f"    translated to a futures trade: {skip_info['n_translated']}")
        print(f"    SKIPPED - signal date outside futures data range entirely: "
              f"{skip_info['skip_out_of_range']}")
        print(f"    SKIPPED - date within range but no matching futures trading day "
              f"(holiday/gap): {skip_info['skip_holiday']}")
        print(f"    SKIPPED - matched, but forward window runs past futures data frontier: "
              f"{skip_info['skip_near_end']}")

    # --- Fresh split: decided on the Nasdaq leg's translated trade dates alone ---
    primary_label = LEGS[0][0]
    cutoff_date = split_dates([s["date"] for s in all_trades[primary_label]])
    print("\n" + "=" * 92)
    print(f"  FRESH 70/30 SPLIT - decided on {primary_label}'s translated trade dates alone,")
    print(f"  position only, before any result was inspected. Cutoff date: {cutoff_date}")
    print("  (This population and cutoff are NOT reused from either prior script.)")
    print("=" * 92)

    def run_sample(sample):
        print("\n" + "=" * 92)
        if sample == "in":
            print(f"  IN-SAMPLE (through {cutoff_date}) - safe to re-run/inspect freely")
        else:
            print(f"  *** OUT-OF-SAMPLE (after {cutoff_date}) - LOOK ONCE ***")
        print("=" * 92)
        results = {}
        for label, _, _, _ in LEGS:
            trades = filter_sample(all_trades[label], cutoff_date, sample)
            print(f"\n--- {label} ---")
            res = {}
            for side in ("bottom", "top"):
                side_sorted = sorted([s for s in trades if s["side"] == side], key=lambda s: s["date"])
                rc_overlap = [s["Rc"] for s in side_sorted]
                rc_nonoverlap = [s["Rc"] for s in non_overlapping(side_sorted)]
                n_o, m_o, p_o = report(label, rc_overlap, f"{side} (overlapping, real-{COST_TIER})", THRESH)
                n_no, m_no, p_no = report(label, rc_nonoverlap, f"{side} (NON-overlap, real-{COST_TIER})", THRESH)
                res[side] = {"overlap": (n_o, m_o, p_o), "nonoverlap": (n_no, m_no, p_no)}
            results[label] = res
        return results

    in_results = run_sample("in")
    out_results = run_sample("out")

    print("\n" + "=" * 92)
    print("  REPLICATION CHECK (sign agreement across 3 legs, non-overlapping real-cost)")
    print("=" * 92)
    for sample_name, results in (("IN-SAMPLE", in_results), ("OUT-OF-SAMPLE", out_results)):
        for side in ("bottom", "top"):
            signs = {}
            for label, _, _, _ in LEGS:
                m = results[label][side]["nonoverlap"][1]
                signs[label] = (1 if m > 0 else (-1 if m < 0 else 0))
            agree = len(set(signs.values())) == 1 and 0 not in signs.values()
            print(f"  [{sample_name}] {side}: signs = {signs}  ->  {'AGREE' if agree else 'DISAGREE'}")

    print("\n  NOT MEASURED / caveats:")
    print("   - Slippage/spread-crossing cost beyond Tradovate's quoted all-in rate.")
    print("   - Continuous front-month futures proxy (Yahoo), not back-adjusted for roll gaps.")
    print("   - RTY=F only has ~9 years of Yahoo history (2017-07-10 onward) vs ~25y for")
    print("     NQ=F/ES=F - the Russell leg's eligible trade population is structurally much")
    print("     smaller and concentrated in the most recent years, not a comparable sample")
    print("     size to the Nasdaq/S&P legs. See per-leg skip counts above.")
    print("   - Overlapping-window p-values are optimistic (autocorrelated observations);")
    print("     non-overlapping rows are the ones to trust.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
