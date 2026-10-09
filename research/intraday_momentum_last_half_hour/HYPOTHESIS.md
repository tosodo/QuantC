# First-Half-Hour Predicts Last-Half-Hour on Nasdaq and S&P Futures — Pre-Registered Test Plan

Status: PLAN ONLY (drafted 8 Oct 2026). No code written and no test run for
this idea. Every choice below is locked BEFORE any result is seen. If a choice
has to change after results are seen, that is a new test with a fresh
Bonferroni count, not an edit to this one.

## 1. Where the idea comes from (and how much to trust it)

Gao, Han, Li and Zhou, "Market Intraday Momentum", Journal of Financial
Economics, 2018. On the S&P 500 ETF (SPY), 1993-2013, the return from the
previous close to 10:00 ET predicts the return of the last half-hour of the
day (15:30-16:00), with the same sign. They report it also holds on ten other
heavily traded ETFs. A summary reports out-of-sample R-squared up to about
0.018 and a gross annualised 6.3% from holding SPY only after a positive first
half-hour (CXO Advisory summary of an earlier draft; we have NOT read the paper
itself).

Trust level: MEDIUM for "it existed in 1993-2013", UNKNOWN for "it exists now".
I found no study that tests whether it survived publication (2018). Related
published edges (ORB, noise area) shrank or vanished after costs in independent
checks, and stock-anomaly research finds about a third of an effect disappears
after publication. Expect the effect to be small or gone.

## 2. Why this is worth a screen

- It is the one well-documented intraday effect we are NOT already running or
  have not already tested (ORB, noise area, session open, hour-of-day are
  covered in sibling folders).
- 2021-2026 data is, by construction, after publication, so the test doubles as
  a first look at whether the effect decayed.
- One 30-minute trade a day fits Lucid (flat well before 16:45 ET) and could
  trade near daily, which the 5 Oct backup screen said a backup must do
  (`../BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`).
- Read-only on files already on disk
  (`../orb_breakout/data/continuous/`).

## 3. Domain check (the honest risks)

- The published effect is tiny (R-squared about 0.02). One MNQ moves very little
  in 30 minutes, so real costs may exceed the whole effect. "Real but not
  tradeable" is the most likely good outcome.
- Both indices drifted up over the sample. A "long after up-morning" rule looks
  positive from drift alone, so the signal must beat always-long (Section 5).
- Gao's first-half-hour return runs from the PREVIOUS CLOSE, so it contains the
  overnight gap. Futures trade 24 hours, so the previous cash close is a price we
  can read, but the move across the overnight session is mostly driven by
  scheduled news. A gap-only result is the gap effect, not a half-hour effect.
- Contract rolls inside the measured span would fake a move (Section 4).
- 15:30-16:00 is already one of the 22 windows in the hour-of-day plan
  (`../hour_of_day_bias/HYPOTHESIS.md`, 15:00-16:00). This test conditions on a
  signal; the two are different questions. Results are counted separately.

## 4. Rule under test (fixed now, not tuned)

- Instruments: NQ (primary) and ES (replication). Same continuous 1-minute
  files and the same 70/30 chronological split used in the other tests (cutoff
  decided on dates alone, as in `../orb_breakout/orb_test.py`).
- Times are New York clock time, cash-session days only.
- Target: R_last = log return from the open of the 15:30 bar to the close of the
  15:59 bar.
- Three predictors, defined before looking:
  - P1 (Gao primary): log return from the previous day's 15:59 close to the
    09:59 close (previous cash close to 10:00).
  - P2 (Gao second): log return from the 14:59 close to the 15:29 close (the
    12th half-hour, 15:00-15:30).
  - P3 (strict, no overnight): log return from the 09:30 open to the 09:59 close
    only.
- Trade: if the predictor is positive go long at the 15:30 open; if negative go
  short; exit at the 15:59 close. No stops, no targets, no filters, no
  combining the predictors, one position, one trade per day.
- A day is skipped if any bar needed is missing, or the contract symbol changes
  between the first and last bar used (roll). Skips are counted and shown.
- Costs: the same real Tradovate 'free' round-trip points used elsewhere
  (`REAL_COST_POINTS`), shown next to the gross numbers. No slippage layered on
  (labelled NOT MEASURED).

## 5. Pre-registered hypotheses (k = 3)

- For each predictor Pi: H_i: the mean of sign(Pi) x R_last is greater than
  zero (one-sided, because the published direction is momentum). Test on daily
  trades, normal approximation (about 880 in-sample days).
- Bonferroni threshold = 0.05 / 3 = 0.0167 per predictor, per instrument.
- Chronological split: first 70% in-sample (looked at), last 30% held out and
  looked at ONCE, and only for predictors that clear the in-sample bar.
- A predictor becomes a CANDIDATE only if ALL hold in-sample:
  1. p < 0.0167 on NQ AND on ES, momentum sign on both.
  2. Its mean beats the always-long mean of R_last over the same days (so it
     is not just drift), and a plain slope regression of R_last on Pi has the
     same sign and t above 2 on both.
  3. The result survives dropping its 3 best days (top-3-days check from
     `../noise_area/overfit_check.py`) and both halves of the in-sample period
     have the same sign.
  4. After real costs the mean is still positive and at least about twice the
     cost per trade. A real but smaller effect is recorded as "real but not
     tradeable".
- A candidate then passes only if the held-out slice has the same sign on both
  instruments. No re-slicing and no second look.
- If P1 passes but P3 does not, the effect is the overnight gap, not the first
  half-hour; record it that way and do not count it as the Gao effect.
- Expected false positives if nothing is real: about 0.05 across all three
  after the Bonferroni cut.

## 6. Sample-size reality

About 880 in-sample days and about 380 held-out days, 2021-2026. A 30-minute NQ
move has a spread of roughly 0.1% of price. At this bar (z about 2.1 one-sided
after Bonferroni, 80% power) the smallest effect reliably seen is about 0.1 of
one day's 30-minute spread, on the order of 3-4 NQ points, about $6-8 per MNQ
per trade, before costs. The published R-squared of 0.018 would sit near or
below that line, so "nothing clears" is the likely result and is NOT proof of no
effect. The held-out slice can only contradict a big effect, not confirm a small
one.

## 7. Lucid survivability (only if a candidate passes Section 5)

Not measured. A 30-minute MNQ position risks roughly $20-60 on a normal day and
far more on a news or close-auction day, with no stop in this first version. Any
candidate must be re-run through `../orb_breakout/lucid_barrier_model.py` and
`lucid_time_to_funded.py` together with the live MES trades (shared $3,000
trailing floor), and adding a stop is a new test. A pass only earns a forward
paper test, not a live change. Ghost (or any alert-to-broker fee) would also be
charged per month regardless of the extra trades, so the edge must also cover
that running cost.

## 8. Gating items — nothing runs until these are answered

1. The user's yes to run the screen. It reads local files only; nothing touches
   TradingView, Ghost or Lucid.
2. Confirm the data's symbol column reliably flags rolls and that 15:59 and 09:59
   bars exist on early-close days (these are dropped, shown in the skip count).
3. The reminder queued for 21:15 on 7 Oct and the 30 Oct review take priority;
   this screen must not delay or alter either.

## 9. What would make us stop

- No predictor clears 0.0167 in-sample on both instruments with the momentum
  sign: record "intraday momentum not present after publication", drop it.
- Only P1 clears and P3 does not: record as overnight-gap effect, drop it.
- Candidate fails the drift, top-3-days or cost checks: record, drop.
- Held-out slice disagrees in sign on either instrument: drop. No re-slicing.
- No change to the predictors, times, 70/30 cutoff or threshold after any result
  is seen.
