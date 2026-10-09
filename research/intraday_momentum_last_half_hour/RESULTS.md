# First-Half-Hour Predicts Last-Half-Hour: Results (9 Oct 2026)

Status: IN-SAMPLE SCREEN RUN ONCE, as written in `HYPOTHESIS.md`. Nothing was
tuned. The held-out slice was NOT looked at (it is only opened for a predictor
that clears the in-sample bar, and none did). Raw output:
`RESULTS_in_sample_raw.txt`. Script: `screen_intraday_momentum.py`.

## Verdict: DROPPED. Intraday momentum is not present after publication.

In-sample = 70% of days through 2025-02-14 (about 870 valid days on each of
NQ and ES). Bar: one-sided p < 0.0167 on BOTH instruments with the momentum sign.

| Predictor | NQ p | ES p | NQ mean (bp) | ES mean (bp) | Candidate? |
|---|---|---|---|---|---|
| P1 prev close to 10:00 (Gao primary) | 0.958 | 0.743 | -1.87 | -0.62 | No: wrong sign on both |
| P2 14:59 to 15:29 (12th half-hour) | 0.092 | 0.069 | +1.42 | +1.39 | No: right sign, short of the bar |
| P3 09:30 to 10:00 (no overnight) | 0.909 | 0.808 | -1.43 | -0.81 | No: wrong sign on both |

- **P1 and P3 point the wrong way** (the morning move slightly predicts a
  reversal in the last half-hour, not momentum), and neither is close.
- **P2 is the nearest miss**: same sign as the published effect on both
  indices, but p is about 0.07-0.09 against the 0.0167 bar, it fails the
  top-3-days / halves check (positive in the first half of the sample,
  negative in the second, which looks like decay), and the plan forbids
  re-tuning it. Net of real costs its gross edge is about +1.9 NQ points and
  +0.6 ES points per trade, but that is not statistically distinguishable
  from luck at this bar.
- Always-long over the last half-hour was slightly negative in-sample on both
  indices, so drift is not helping any long-biased rule.
- Skipped days: 45 days without both 15:30 and 15:59 bars (holidays and early
  closes); P1 skipped 21 more (no previous-day close or a contract roll).

## What this means
- Rule from `HYPOTHESIS.md` Section 9: no predictor clears 0.0167 on both
  instruments with the momentum sign, so record "intraday momentum not
  present after publication" and drop it. Do not re-run or change predictors,
  times, the cutoff or the threshold.
- Counts toward the backup-screen list as one more idea that did not work.
- The held-out slice remains unused.

## Interpretation choices made before running (the plan was loose on these)
- Cost check: net mean (after real round-trip cost) must be at least 2x the
  cost. Verdict is unaffected: nothing reached the p bar.
- Cutoff decided on NQ valid-target dates, same date applied to ES.
- Normal-approximation p-values; slope t from a plain regression.
