# Hour-of-Day Bias on Nasdaq and S&P Futures — Pre-Registered Test Plan

Status: PLAN ONLY (drafted 7 Oct 2026). No code written and no test run for
this idea. Every choice below is locked BEFORE any result is seen. If a choice
has to change after results are seen, that is a new test with a fresh
Bonferroni count, not an edit to this one.

## 1. Where the idea comes from (and how much to trust it)

A YouTube video by Matteo Conti, "Stop Guessing Your Daily Bias. Measure It."
(3 Oct 2026). From its description only (the transcript could not be read):
on S&P 60-minute bars he tests every hour of the day over the full history,
ranks all 24 windows, turns profitable hours into a long block and losing hours
into a short block, adds a stop and target to each leg, and then runs the
hours picked on early data over later years.

Trust level: LOW. We have not seen his numbers, only the description. His
channel sells a paid community and code templates, and says results are gross
of costs unless stated. We test the CLAIM ("some hours of the day have a
reliable direction"), not his results.

## 2. Why this is worth a screen

- Cheap and read-only: 5 years of 24-hour 1-minute NQ and ES are already on
  disk (`../orb_breakout/data/continuous/`).
- Hours-long holds fit Lucid's rules (flat by 16:45 ET) and could trade near
  daily, which the 5 Oct backup screen said a backup must do
  (`../BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`).
- Related work found little: the 5 Oct session-open test was a null, and the
  European-open drift test failed. Expect nothing, or only the known upward
  drift. This screen exists mainly to settle the question once.

## 3. Domain check (the honest risks)

- 22 windows means 22 chances for a lucky result. That is the main danger and
  is why the bar below is strict (Section 5).
- Both indices drifted up over the sample. Almost any "long" window looks
  positive for that reason alone. A window must beat the drift, not just zero.
- Trading hours hit by known events (the 08:30 and 10:00 ET data releases, the
  09:30 open) will look big. If a window's whole result is a few event days,
  it is an event effect, not an hour effect.
- Continuous front-month series are not back-adjusted; a contract roll inside a
  window would fake a move (handled in Section 4).

## 4. Rule under test (fixed now, not tuned)

- Instruments: NQ (primary) and ES (replication). Same continuous 1-minute
  files and the same 70/30 chronological split used in the other tests (cutoff
  decided on dates alone, as in `../orb_breakout/orb_test.py`).
- Windows: the 22 whole clock hours in New York time, 18:00-19:00 through
  23:00-24:00 and 00:00-01:00 through 15:00-16:00. Excluded: 16:00-17:00
  (Lucid closes everything at 16:45) and 17:00-18:00 (market halt).
- One observation per window per trading day: the log return from the open of
  the first minute to the close of the last minute of the window.
- A day-window is skipped if any of its 60 one-minute bars is missing, or if
  the contract symbol changes inside it (roll). Skips are counted and shown.
- Costs: the same real Tradovate 'free' round-trip points used elsewhere
  (`REAL_COST_POINTS`), applied once per window, shown alongside the gross
  numbers. No slippage layered on (labelled NOT MEASURED).
- No stops, no targets, no day-of-week or month splits, no combining windows,
  no other window lengths. One long or one short held for the full hour.
  Stops and targets, as in his video, are a separate later step and only if
  Section 5 passes.

## 5. Pre-registered hypotheses (k = 22)

- For each window w on each instrument: H_w: the mean log return of window w is
  not zero. Two-sided t-test on the daily returns (normal approximation is fine
  at about 880 in-sample days per window).
- Bonferroni threshold = 0.05 / 22 = 0.00227 per window, per instrument.
- Chronological split: first 70% in-sample (looked at), last 30% held out and
  looked at ONCE, and only for windows that clear the in-sample bar.
- A window becomes a CANDIDATE only if ALL hold in-sample:
  1. p < 0.00227 on NQ AND on ES, with the same sign.
  2. Its mean beats the average of all 22 windows by the same sign (so it is not
     just market drift).
  3. The result survives dropping its 3 best days and the top-3-days check from
     `../noise_area/overfit_check.py`; and both halves of the in-sample period
     have the same sign.
  4. After real costs the mean is still the same sign and still at least about
     twice the cost per window. A real but smaller effect is recorded as
     "real but not tradeable".
- A candidate then passes only if the held-out slice has the same sign on both
  instruments. No re-slicing and no second look.
- Expected number of false positives if nothing is real: about 0.05 across all
  22 windows after the Bonferroni cut. Seeing one or two windows pass is
  therefore meaningful; seeing exactly the ones with big scheduled events
  (08:30, 10:00) is an event effect and is not counted as a bias.

## 6. Sample-size reality

About 880 in-sample days and about 380 held-out days per window. At the strict
bar (z about 3.05) with 80% power, the smallest effect the in-sample test can
reliably see is about 0.13 of one day's hourly spread, which on Nasdaq is
roughly 0.03% of price (on the order of 6 points; about $12 per MNQ per hour at
today's prices) per window per day. Smaller true effects will show as
"nothing clears", which is NOT proof of no effect. The held-out slice is far too
small to confirm a small effect; it can only contradict a big one.

## 7. Lucid survivability (only if a candidate passes Section 5)

Not measured. A held hour of NQ moves about 0.25% on a typical day, so one MNQ
risks about $50-100 per window on a normal day and far more on a news day,
with no stop in this first version. Any candidate must be re-run through
`../orb_breakout/lucid_barrier_model.py` and `lucid_time_to_funded.py` together
with the live MES trades (shared $3,000 trailing floor), and adding a stop is a
new test. No live change is considered from this screen alone; a pass only earns
a forward paper test.

## 8. Gating items — nothing runs until these are answered

1. The user's yes to run the screen. It reads local files only; nothing touches
   TradingView, Ghost or Lucid.
2. Confirm the data's symbol column reliably flags rolls, so the roll skip in
   Section 4 works.
3. The reminder queued for 21:15 on 7 Oct and the 30 Oct review take priority;
   this screen must not delay or alter either.

## 9. What would make us stop

- No window clears 0.00227 in-sample on both instruments with the same sign:
  record "no hour-of-day bias", drop it.
- Only event-hour windows (08:30, 09:30, 10:00 ET) clear: record as event
  effects, drop it as a bias.
- Candidate fails the drift, top-3-days or cost checks: record, drop.
- Held-out slice disagrees in sign on either instrument: drop. No re-slicing.
- No change to the window list, the 70/30 cutoff or the threshold after any
  result is seen.
