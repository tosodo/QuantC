#!/usr/bin/env python3
"""
stoploss_significance_check.py - two things, both re-checks of
STOPLOSS_HYPOTHESIS.md following the 2026-08-27 exact-dollar survivability
reversal (see stoploss_reconciliation.py):

  (1) AUDIT: re-run stoploss_test.py's own in-sample/out-of-sample mean-R
      report (range-width R units, NQ/ES separately) to confirm the numbers
      already written up in STOPLOSS_HYPOTHESIS.md actually reproduce from
      the code, rather than trusting the 2026-08-20 write-up on faith.

  (2) NEW CHECK: the range-width R unit used in (1) is not the unit that
      actually determines survival - real dollars per MNQ/MES contract are.
      Section 2.6/2.7's own lesson was "the unit you measure in can flip the
      answer" - that was true for survivability; this checks whether it's
      also true for the mean-effect significance test, by re-running the
      same in/out-of-sample split on each trade's EXACT dollar P&L (MNQ
      $2/pt, MES $5/pt) instead of range-width-normalized R. Because with-
      stop and no-stop share the same entry on every trade, the natural test
      is PAIRED: does the stop change that trade's dollar outcome, on
      average, by a statistically distinguishable amount from zero?

Same cutoff-date convention as stoploss_test.py: chronological split decided
on the primary instrument's (NQ) dates alone, never by outcome. Out-of-sample
here is being looked at again (it was already looked at once on 2026-08-20 in
range-width R units) - that slice is NOT being re-chosen or re-cut, only
re-measured in a different, non-approximated unit. No new Bonferroni budget
consumed - same comparison-not-a-fresh-hypothesis framing as
STOPLOSS_HYPOTHESIS.md itself and as stoploss_reconciliation.py.

Usage
    python3 stoploss_significance_check.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, INSTRUMENTS
from stoploss_test import build_stop_trades
from stoploss_reconciliation import build_trades as build_dollar_trades, POINT_VALUES

ONLY = [(l, p) for l, p in INSTRUMENTS if l != "YM (Dow, repl.)"]


def part1_reproduce_original():
    print("=" * 96)
    print("  PART 1 - AUDIT: reproducing STOPLOSS_HYPOTHESIS.md's own range-width-R")
    print("  in-sample / out-of-sample report directly from the code")
    print("=" * 96)

    dfs = {label: load(path) for label, path in ONLY}
    primary_label = ONLY[0][0]
    primary0, _ = build_stop_trades(dfs[primary_label])
    cutoff_date = smr.split_dates([s["date"] for s in primary0])
    print(f"\n  Cutoff date (chronological, decided on {primary_label} alone): {cutoff_date}\n")

    for sample in ("in", "out"):
        print(f"  --- sample = {sample} " + ("(*** OUT-OF-SAMPLE - already looked at once, "
              "not re-cut here ***)" if sample == "out" else "") + " ---")
        for label, _ in ONLY:
            df = dfs[label]
            cost_pts = smr.REAL_COST_POINTS[label]["free"]
            sigc, _ = build_stop_trades(df, cost_points=cost_pts)
            sigcf = smr.filter_sample(sigc, cutoff_date, sample)
            rc_close = [s["Rc_close"] for s in sigcf]
            rc_stop = [s["Rc_stop"] for s in sigcf]
            smr.report(label, rc_close, f"no-stop, exit@close (real-cost, {sample}-sample)")
            smr.report(label, rc_stop, f"WITH STOP (real-cost, {sample}-sample)")
        print()
    return cutoff_date


def paired_t_test(deltas):
    return smr.t_test(deltas)


def part2_dollar_significance(cutoff_date):
    print("=" * 96)
    print("  PART 2 - NEW: same in/out-of-sample split, but measured in EXACT dollars")
    print("  per MNQ/MES contract (paired: with-stop minus no-stop, per trade)")
    print("=" * 96)

    for label, path in ONLY:
        df = load(path)
        cost_pts = smr.REAL_COST_POINTS[label]["free"]
        half_cost = cost_pts / 2.0
        name, pv = POINT_VALUES[label]
        trades = build_dollar_trades(df)

        print(f"\n  --- {label} -> {name} ({pv:.1f} $/pt) ---")
        for sample in ("in", "out"):
            sub = smr.filter_sample(trades, cutoff_date, sample)
            deltas, no_stop_pnl, with_stop_pnl = [], [], []
            for t in sub:
                entry_c = t["entry_price"] + half_cost
                no_stop_exit = t["close_exit_price"] - half_cost
                stop_px = t["stop_exit_price"] if t["stopped"] else t["close_exit_price"]
                with_stop_exit = stop_px - half_cost
                d_no_stop = (no_stop_exit - entry_c) * pv
                d_with_stop = (with_stop_exit - entry_c) * pv
                no_stop_pnl.append(d_no_stop)
                with_stop_pnl.append(d_with_stop)
                deltas.append(d_with_stop - d_no_stop)

            n, mean_delta, sd, t_stat, p = paired_t_test(deltas)
            mean_no_stop = sum(no_stop_pnl) / len(no_stop_pnl) if no_stop_pnl else 0.0
            mean_with_stop = sum(with_stop_pnl) / len(with_stop_pnl) if with_stop_pnl else 0.0
            tag = "IN-SAMPLE " if sample == "in" else "OUT-OF-SAMPLE"
            print(f"    [{tag}] n={n:4d}  mean$ no-stop=${mean_no_stop:7.2f}  "
                  f"mean$ with-stop=${mean_with_stop:7.2f}  "
                  f"paired delta=${mean_delta:+7.2f}  t={t_stat:+.3f}  p={p:.4f}"
                  + ("  *** p<0.05 ***" if p < 0.05 else ""))


def main():
    cutoff_date = part1_reproduce_original()
    part2_dollar_significance(cutoff_date)

    print("\n" + "=" * 96)
    print("  NOT MEASURED / caveats")
    print("=" * 96)
    print("  - This re-checks significance of the STOP EFFECT (paired delta) and reproduces")
    print("    the original range-width-R report. It is still a comparison on an already-")
    print("    established edge, not a fresh hypothesis - no new Bonferroni budget consumed.")
    print("  - Out-of-sample slice is being re-measured (different unit), not re-chosen -")
    print("    same cutoff date, same trades, as the 2026-08-20 look.")
    print("  - Paired test only checks whether the STOP CHANGES the dollar outcome; it does")
    print("    not by itself re-test whether the underlying no-stop entry signal is significant")
    print("    against zero (that is orb_test.py's job and is unaffected by this file).")
    print("  - Fill still assumed exact at the stop price (range_low) - unmodeled slippage")
    print("    would bias the with-stop numbers worse, not better.")


if __name__ == "__main__":
    sys.exit(main() or 0)
