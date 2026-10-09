# Horner Ideas — Combined Pre-Registered Test Plan (FINAL)

Status: FINAL and FROZEN 9 Oct 2026 (user approved). PLAN ONLY. No code written and no test run. Every
choice below is locked BEFORE any result is seen. If a choice has to change
after results are seen, that is a new test with a fresh Bonferroni count, not
an edit to this one.

FREEZE NOTE: Box Theory transcript was read on 9 Oct and added NO new test (too
discretionary; its one clear filter, previous-session close, is already H4;
a prior-day high / low fade would overlap dropped mean-reversion work). The
follow-up video on "levels" (volume profile) was read on 9 Oct and also added
NO new test (triggers left to the trader; prior-value-area return overlaps
gap / return-to-open work). All requested transcripts are now read. After this
draft is marked FINAL, it is frozen.

Source and trust: Raghee Horner YouTube channel (see `REVIEW_2026_10_09.md`).
Trust level: LOW. No results are shown by her anywhere; these are rule
descriptions only, and her entries are partly discretionary, so each is
reduced to ONE mechanical version below.

## 1. Why a screen is worth it
- It uses data we hold: 5 years of 24-hour 1-minute NQ and ES in
  `../orb_breakout/data/continuous/` (so the 05:00-09:00 ET range, the 07:00
  anchor and the previous 16:00 close can all be built with no purchase).
- The CRT idea is a possible backup strategy: it can trade almost every
  morning, which our backup screen requires (see
  `../BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`; do not re-run dropped ideas).
- The ORB variants reuse the existing ORB trade list and exit rules, so they
  add no new moving parts if one works.

## 2. Domain risks (honest)
- Morning-hours cousins already failed (overnight-range filter, 9:30 open
  continuation / reversal, return-to-open). Expect a small effect or none.
- The ORB baseline has been looked at many times (not a virgin dataset).
- Retest entries skip the strongest days and cut trade count; a "better per
  trade" result can still lose on total R per year.
- CRT stops sit beyond the sweep and may be wide for 2 MES contracts on the
  Lucid trailing floor.
- Run at the same hours as the live ORB, so correlation matters (see 6).

## 3. Rules under test (fixed now, not tuned)

Instruments: NQ (primary) and ES (replication). Same continuous 1-minute series,
same split date (2025-02-14), same real Tradovate cost rates as the existing
tests. Same-bar stop and target both touched: stop assumed first.

### H1 — CRT sweep-and-reverse (new strategy)
- Range: high and low of all 1-minute bars 05:00:00 to 08:59:59 ET.
- Sweep: the first 5-minute bar starting 09:30 to 10:25 ET whose high exceeds
  the range high (short setup) or whose low is below the range low (long setup).
  One setup per day: the first sweep seen. If both edges sweep in the same bar,
  skip the day.
- Entry (ONE version): at the close of the first later 5-minute bar that closes
  back INSIDE the range, on or before the 10:55 bar. No resting-order entry and
  no inside-candle / minor-high entry are tested (partly discretionary in her
  description).
- Stop: sweep extreme (highest high for a short, lowest low for a long, from
  the sweep bar to the entry bar) plus 1 tick.
- Target: the midpoint of the 05:00-09:00 range, full exit. Skip the trade if
  the entry is already beyond the midpoint. Time exit at 12:00 ET.
- No ranging / trending filter (undefined by her); no previous-close filter in
  the primary test. A previous-close split is reported as description only.
- R is measured against the stop distance. Report: trades per year, mean R
  after costs, average winner / loser, stop-distance distribution, share of
  trades whose 2-MES stop loss exceeds 25% of the Lucid cushion in force at the
  30 Oct review.

### H2 — ORB with a 30-minute range
- Range: 09:30:00 to 09:59:59 ET. Entry, stop and exit rules exactly those of
  the baseline ORB in `../orb_breakout/orb_test.py`, except the entry cannot
  occur before 10:00 ET.

### H3 — ORB with a retest entry
- Range, stop and exit as baseline (15-minute range, 09:30-09:44 ET). After the
  baseline breakout close, a limit buy at the range midpoint (50%, the centre of
  her 38-62% zone, resolved now); valid until the baseline time exit. No fill
  = no trade.

### H4 — ORB with previous-session-close filter
- Baseline trades kept only if the 09:30 open is above the previous 16:00 ET
  cash close. Long side only (the live rule is long only).

### H5 — ORB with 07:00 ET anchored-VWAP filter
- Baseline trades kept only if the entry price is above the volume-weighted
  average price anchored at 07:00 ET that day (1-minute volume, continuous
  contract).

No second threshold, window or combination of H2-H5, and no parameter sweep.

## 4. Pre-registered hypotheses (k = 5)
- H1: mean R per trade after costs is greater than zero (one-sided t-test).
- H2-H5: mean R per trade of the variant is greater than the baseline's
  (Welch, one-sided); for H4 and H5 the comparison is kept trades vs excluded
  trades.
- Each must pass on NQ AND ES. Bonferroni threshold = 0.05 / 5 = 0.01.
- Split: first 70% in-sample (looked at); the last 30% looked at ONCE, only if
  in-sample passes.

## 5. Pass bar (ALL of)
1. In-sample p < 0.01 on both NQ and ES.
2. Held-out difference has the same sign on both.
3. Top-3-days and split-half checks (as in
   `../noise_area/overfit_check.py`) do not flip the verdict.
4. Economic bar: trades per year x mean R per trade must be at least that of
   the unfiltered / baseline rule (H2-H5). For H1 (backup): at least 100
   trades per year pooled AND mean R after costs positive on both
   instruments.
5. For H1 only: the 2-MES stop-loss check in Section 3 must not show frequent
   losses large enough to threaten the floor.

## 6. Extra reporting (description, not tests)
- Daily-result correlation of H1 with the live ORB (the VWAP-fade was
  r = -0.161; compare).
- Overlap days between H1 and the live ORB (same hours: cannot be run together
  on one contract).
- Smallest detectable effect at 80% power (computed from the realised sample
  before anything is read).

## 7. Lucid survivability (only if Section 5 passes)
Not measured. Any passing variant is re-run through
`../orb_breakout/lucid_time_to_funded.py` and `lucid_barrier_model.py` before
any change is even considered. A pass only earns a forward paper test.

## 8. Gating items — nothing runs until these are answered
1. The user's separate yes to run the screen (read-only on local files;
   nothing touches TradingView, Ghost or Lucid).
2. Not before the 30 Oct review decides the live setup
   (`../noise_area/REVIEW_30OCT_RULES.md`).
3. The baseline ORB trade list must reconcile to the 2 Oct audit first.
4. Box Theory and the "levels" (volume profile) transcripts read; nothing added.
   Any further rule must be written in here BEFORE this draft is marked FINAL.

## 9. What would make us stop
- Any H fails 0.01 on NQ or ES: drop it, record it.
- Effect from a handful of days: drop it.
- Held-out sign disagrees: drop it. No re-slicing, no new window.
- Passes but fails the economic bar: record "real but not useful".
- No tuning of the 38-62% choice, the 25-minute sweep window, or any other
  number above after seeing a result.
