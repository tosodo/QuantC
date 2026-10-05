# MCL (Micro Crude Oil) Daily Opening-Range Breakout — Pre-Registered Test Plan

Status: PLAN ONLY (drafted 5 Oct 2026). No code written, no oil intraday data
inspected, no test run. Every choice below is locked BEFORE any results are
seen. If a choice has to change after results are seen, that is a new test
with a fresh Bonferroni count, not an edit to this one.

## 1. Why oil, and why this is a backup candidate

- Trades near-daily (one entry per day at most), so it can be judged within a
  30-day Lucid window, unlike the slow ideas already dropped
  (see `../BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`).
- Moves for different reasons than Nasdaq/S&P. Measured 5 Oct on daily data
  (Yahoo CL=F, 2 years): co-movement with Nasdaq about -0.05 (none).
  So it would not be the same bet as MES v2 / the Nasdaq paper test.
- Per micro contract (MCL, 100 barrels, $1 per 0.01 tick) the average daily
  range is about $304 and the worst single close-to-close day was about
  -$1,854 (Yahoo continuous series, roll jumps not checked).
- Lucid lists MCL as an approved product at about $0.50/side
  (third-party source dated 12 Aug 2026 — PRIOR, re-verify on Lucid's own page
  before any paper or live use).

NOT MEASURED: whether oil has any edge at all. This is a screen, not a promise.

## 2. Domain check (the honest risks)

- The opening-range breakout idea worked on index futures at the NYSE 9:30
  open because that is a real price-discovery event. Oil's equivalent
  (NYMEX 09:00 ET open, 14:30 ET settlement) is weaker; the project's own
  FX and London-open versions of this idea were flat or marginal.
  Treated as a reason to expect a SMALL edge or none.
- Oil is event-driven: weekly EIA inventory report (Wednesdays 10:30 ET) and
  OPEC headlines can gap the price through any stop. Lucid documents no news
  restriction (third-party source) but this must be re-checked.
- Yahoo-style continuous series are not back-adjusted for roll gaps and are
  not the Tradovate feed. Results from them are indicative only.

## 3. Rule under test (fixed now, not tuned)

- Instrument: CL full-size history as the primary (longer, cleaner data),
  traded as MCL. Replication instrument: none free; see Section 7.
- Opening range: 09:00-09:14 ET (first 15 minutes of the NYMEX day session).
- Entry: first 5-minute bar that CLOSES above the range high (long) or below
  the range low (short), between 09:15 and 12:00 ET. One trade per day max.
- Stop: opposite side of the opening range. Risk 1R = range width.
  Skip the day if range width in dollars at 1 MCL exceeds a fixed cap
  (set to $250 per contract) or is under 5 ticks (noise).
- Exit: stop, or flat at 14:25 ET at the latest (before settlement), always
  well before Lucid's 16:45 ET auto-close.
- Costs: real Tradovate free-plan rates (as in the other tests), plus a fixed
  1-tick slippage each side as a placeholder, labelled NOT MEASURED.
- No filter, no second window, no parameter sweep.

## 4. Pre-registered hypotheses (k = 2)

- H_long: mean R per trade of long breakouts > 0.
- H_short: mean R per trade of short breakouts > 0 (mirror).
- Bonferroni threshold = 0.05 / 2 = 0.025, two-sided t-test on per-trade R.
- Chronological split: first 70% in-sample (looked at), last 30% held out and
  looked at ONCE, only if in-sample clears the bar.
- Pass bar to move on: in-sample clears 0.025 AND the held-out sign agrees
  AND the top-3-days and split-half checks (as in `noise_area/overfit_check.py`)
  do not flip the verdict.

## 5. Sample-size reality (this decides feasibility)

With per-trade spread of about 1R, detecting a true edge at 80% power needs
roughly N = 170 trades for 0.30R, and N = 1,500 for 0.10R (alpha 0.025).
At about one trade per trading day that is 8 months for a big edge and
years for a small one. A realistic oil edge is small, so a screen on a few
months of data cannot confirm it. Any result under ~170 trades is
"inconclusive", never "pass".

## 6. Lucid survivability (to be filled only if Section 4 passes)

Formulas only, not measured:
- Losing streak survived = floor(cushion / dollar risk per trade).
  Current cushion $2,564; target gap $6,258 (as of 2 Oct).
- Capped at $250 risk per contract, 2 contracts risks about $500 per trade,
  about 5 straight losses to the floor. Fine for a screen; real sizing is
  decided later with a Monte Carlo against Lucid's EOD trailing floor.
- Run the same Monte Carlo (`orb_breakout/lucid_barrier_model.py` family)
  JOINT with the live MES trades, since both would share one drawdown budget.

## 7. Gating items — nothing runs until these are answered

1. DATA: free sources give only ~60 days of 30-minute history, nowhere near
   enough. Need 5-minute (or 1-minute) CL history for at least 2-3 years.
   Likely a paid data purchase. COST AND SOURCE NOT YET CHECKED.
2. Lucid's own approved-products page and news-trading rules re-verified.
3. Decision on whether a forward paper test (new days, no purchase) is a
   better route than a historical screen, given Section 5.
4. Not to start before the 30 Oct review decides whether the Nasdaq
   noise-area backup is already enough.

## 8. What would make us stop

- In-sample t-test fails the 0.025 bar on both sides: drop it, record it.
- Edge appears only on a handful of days (top-3 check): drop it.
- Held-out slice disagrees in sign: drop it. No re-slicing.
