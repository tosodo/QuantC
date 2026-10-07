# Overnight-Range Position as a Filter on the Live Opening-Range Breakout — Pre-Registered Test Plan

Status: PLAN ONLY (drafted 7 Oct 2026). No code written and no test run for
this idea. Every choice below is locked BEFORE any result is seen. If a choice
has to change after results are seen, that is a new test with a fresh
Bonferroni count, not an edit to this one.

## 1. Where the idea comes from (and how much to trust it)

A podcast interview (Matteo Conti, "overnight bias opening range breakout",
shown 7 Oct 2026) describes a Nasdaq strategy where the 9:30 open's position
inside the overnight range decides which direction is allowed:
top third of the range = longs only, bottom third = shorts only, middle third =
no trade. He then trades an opening-range breakout in that direction.

Trust level: LOW. The interview was sponsored by a prop firm; the numbers shown
were chosen by him after seeing the data ("developed 2018, out of sample from
2023"); no costs or slippage were stated; 53 outlier trades made about $88K of
about $200K. We are NOT testing his whole strategy. We test only the one
borrowable piece: does "where the open sits in the overnight range" predict
whether OUR existing long-only breakout wins?

## 2. Why this is worth a screen at all

- It is a filter on a rule we already run (MES v2 / the NQ+ES opening-range
  breakout in `../orb_breakout/`), so it adds no new strategy and no new
  moving parts if it works.
- It uses data we already hold: 5 years of 1-minute NQ and ES, 24-hour
  (`../orb_breakout/data/continuous/`), so the overnight range can be measured
  with no purchase.
- Related earlier work found little: the 2 Oct gap tests (`../orb_breakout/gap_tests.py`)
  found no fix and an edge that faded to about zero out of sample. Overnight
  range position is not the same thing as the gap, but it is a close cousin.
  Expect a small effect or none.

## 3. Domain check (honest risks)

- A filter that keeps only the top third of days cuts trade frequency to
  roughly a third. The live rule already trades about 133 times a year; a third
  of that is about 44. Fewer trades means slower to the $6,258 target unless
  the per-trade gain more than triples (see the economic bar in Section 5).
- "Top third of the range" is a close cousin of "gap up / open near highs",
  which the project has already examined. Part of any effect may simply be the
  market's upward drift in the sample period (he says so himself).
- Multiple-looks risk: we have already seen the ORB results overall and the
  gap results. The by-bucket split here has not been seen, but this is not a
  virgin dataset. Treated as a reason for a strict bar, not a loose one.

## 4. Rule under test (fixed now, not tuned)

- Instruments: NQ (primary) and ES (replication), the same continuous 1-minute
  series and the same ORB trade list the existing tests use. No new entry
  rule; the entry, stop and exit are exactly those in
  `../orb_breakout/orb_test.py` and `mes_final_run.py`.
- Overnight range: high and low from 01:00 ET to 09:29 ET on the same
  calendar day. (His "midnight Central" is 01:00 ET. The transcript also
  mentions 11 p.m.; this ambiguity is resolved NOW as 01:00 ET and is not
  swept.)
- Position in range: P = (09:30 open - overnight low) / (overnight high -
  overnight low).
- Buckets, fixed: TOP if P >= 2/3, BOTTOM if P <= 1/3, MIDDLE otherwise.
  Skip days where the overnight range is zero or the data has gaps.
- Test group: long ORB trades taken on TOP days. Comparison group: long ORB
  trades on all other days. Long side only, because the live rule is long only.
- Costs: the same real Tradovate free-plan rates the other tests use; no extra
  slippage layered on (same as the baseline it is compared with).
- No second threshold, no other overnight window, no combination with the
  gap filter, no parameter sweep.

## 5. Pre-registered hypotheses (k = 2)

- H_NQ: mean R per long trade on TOP days is greater than on all other days
  (NQ). Welch two-sample t-test on per-trade R, one-sided in the predicted
  direction.
- H_ES: the same on ES (replication).
- Bonferroni threshold = 0.05 / 2 = 0.025 for each.
- Chronological split: the first 70% in-sample (looked at), the last 30%
  held out and looked at ONCE, only if in-sample clears the bar. The existing
  ORB cut at 2025-02-14 is reused, not re-chosen.
- Pass bar to move on, ALL of:
  1. In-sample p < 0.025 on NQ AND on ES.
  2. The held-out difference has the same sign on both.
  3. Top-3-days and split-half checks (as in `../noise_area/overfit_check.py`)
     do not flip the verdict.
  4. Economic bar: trades per year x mean R per trade, on TOP days only, must be
     at least that of the unfiltered rule. With about one third of days in the
     top bucket, that means the mean R per trade there must be about 3x the
     unfiltered mean. A real but small effect does NOT clear this and is
     recorded as "real but not useful".

## 6. Sample-size reality

The unfiltered rule has about 660 long trades on MES-sized history (about 1,300
on NQ pooled across 5 years). A third of that is roughly 220 to 430 TOP trades
against roughly 440 to 870 others. With per-trade spread of about 1R, the
smallest difference that test can reliably detect (80% power, alpha 0.025) is
roughly 0.25R on the ES-sized sample and a bit under 0.2R on NQ. A true effect
smaller than that will show as "inconclusive", which is NOT a pass. The
held-out slice (about 30% of the trades) is far too small to confirm a small
effect on its own; it can only contradict a large one.

## 7. Lucid survivability (only if Section 5 passes)

Not measured, formulas only. Fewer trades per year means fewer chances to
build the $6,258 gap to target and a longer exposure to the inactivity-reset
clock, so any filtered version must be re-run through
`../orb_breakout/lucid_time_to_funded.py` and `lucid_barrier_model.py`
(shared drawdown budget, EOD trailing floor) before any change is considered.

## 8. Gating items — nothing runs until these are answered

1. The user's yes to run the screen. Building the test script is read-only
   analysis on local files; nothing touches TradingView, Ghost or Lucid.
2. Not to start before the 30 Oct review decides what the live setup looks like
   (`../noise_area/REVIEW_30OCT_RULES.md`). No changes to the live MES v2 rule
   are made on the strength of this screen alone, even if it passes; a pass
   only earns a forward paper test.
3. Confirm the existing ORB trade list can be re-used unchanged (same file the
   2 Oct audit used), so the baseline reconciles first.

## 9. What would make us stop

- In-sample fails 0.025 on either NQ or ES: drop it, record it.
- Effect appears only on a handful of days (top-3 check): drop it.
- Held-out slice disagrees in sign: drop it. No re-slicing, no new window.
- Passes statistically but fails the economic bar: record as "real but not
  useful" and do not pursue.
- No tuning of the 2/3, 1/3 thresholds or the 01:00 ET start after seeing any
  result.
