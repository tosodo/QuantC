# NQ vs ES Relative Value — Pre-Registered Test Plan

Status: PLAN ONLY. No code written, no test run yet. This document is the
pre-registration — the prediction and test design are locked in BEFORE any
data is inspected, per the propfirm-research-auditor discipline used
throughout this project (see `research/index_mean_reversion/` for the
identical discipline applied to the prior hypothesis).

## 1. Constraints (Lucid Trading LucidPro $100K eval)

As stated earlier in this project (not re-verified this turn — flagged as
PRIOR, not measured):
- Profit target: $6,000 (6% of 100k)
- Max total loss: $3,000 (3%)
- EOD trailing drawdown: $1,800, trailing to highest close-of-day equity
- No intraday daily loss limit (Pro tier)
- 90/10 split once funded

Both a $3,000 static cap and a $1,800 trailing-to-peak cap were described
together; where both apply, the tighter one binds first, so **$1,800 is
treated as the effective governing limit** until clarified otherwise.

Losing-streak survival and trades-needed-to-target both depend on the
per-trade R and win rate this test would produce — those don't exist yet.
Formulas only, to be filled in once real numbers exist:
- Losing streak survived = floor($1,800 / risk-per-trade-in-dollars)
- Trades to target = $6,000 / (expected $ per trade)

NOT MEASURED: both, until the test below produces real R and win-rate figures.

## 2. Domain check

Relative-value / pairs trading between correlated instruments is a real,
long-standing professional approach (statistical arbitrage). But NQ and ES
are not a classic "pair" — they're both broad, highly-correlated US equity
indices (not two near-identical instruments). Their relationship can drift
for months or years on genuine macro trends (tech vs. broad-market rotation)
rather than reverting on a stable schedule. This is a real and known failure
mode of naive pairs trading (adding to a position as the spread gets more
"extreme," when the spread is actually just trending) — it is not
disqualifying on its own, but the test design below must check for it
directly rather than assume mean reversion exists.

The published academic pairs-trading literature (e.g. Gatev, Goetzmann &
Rouwenhorst) mostly studies same-industry single stocks, not cross-index
futures — so there is no directly-applicable published result for this exact
pair. Labeled NOT MEASURED, not assumed either way.

## 3. Pre-registered falsifiable hypothesis

Signal (reuses the exact lookback/quintile machinery already built, tested,
and trusted in `screen_mean_reversion.py` — same 3 core parameters, same
no-lookahead rule: everything computed strictly on data before the decision
day):

- Spread = log(NQ close) − log(ES close), each trading day.
- Z = (today's spread − trailing N-day mean of spread) / trailing N-day
  stdev of spread, using only data before the decision day.
- Classify today's Z against its own trailing rolling distribution
  (mirrors the original test's quintile approach).

Pre-registered, two-sided:
- Bottom quintile (NQ cheap vs ES) → next H-day return of (NQ − ES) is
  POSITIVE (long NQ / short ES) — p < 0.025
- Top quintile (NQ rich vs ES) → next H-day return of (NQ − ES) is
  NEGATIVE (short NQ / long ES) — p < 0.025

(α = 0.025 = 0.05 / k, k=2 for the two pre-registered sides — a fresh
Bonferroni budget for this hypothesis family, separate from the earlier
single-instrument mean-reversion test, since this is a structurally
different signal (relative value, not each market's own return). Flagged
as a judgment call, not a hidden decision.)

Required pre-check before the money question (part of this same test, not a
separate fishing expedition): does the spread actually stay in a bounded
range over the sample, or does it drift to new multi-year extremes without
reverting? If it's non-stationary over the sample, that's a direct answer
("this pair doesn't mean-revert at a tradeable frequency") and the
significance test result must be read in that light.

## 4. Test design

- **Isolation**: flat size both legs, fixed ±R, one spread-position at a
  time. No trade management logic tested here — that's a separate, later
  gate, only for whatever survives this one.
- **Leg sizing**: simplest option first — dollar value matched using each
  contract's own point value (not beta/regression-hedged). Flagged as a
  real design choice; a beta-neutral ratio is a legitimate later
  sensitivity check, not required for the first pass.
- **Sample**: 25 years of NQ=F / ES=F daily bars already on disk
  (`research/index_mean_reversion/data/`). Exact non-overlapping trade count
  will be whatever the data produces — not estimated in advance.
- **Significance**: per-trade t-test (not Sharpe), two-sided, threshold
  0.025 per side as above.
- **Replication**: NQ-vs-YM as a second, structurally different pair
  (tech-heavy vs. industrial-heavy, not just tech-heavy vs. broad-market),
  using data already on hand. A third independent pair is not available in
  this project without new data.
- **Cost model**: real, MEASURED Tradovate round-turn costs on BOTH legs
  (same table used throughout this project), applied at each trade's own
  entry price. Zero-cost run required alongside, per standard practice —
  if there's no edge before costs, costs are irrelevant.
- **Pessimism**: ambiguous bar (both legs' stop/target inside the same bar)
  scores as the loss. Decisions on closed bars only.
- **Out-of-sample**: fresh chronological 70/30 split, decided by position
  alone on this new eligible-date population, before any result is
  inspected — not reusing the cutoff date from the earlier, unrelated test.

## 5. Survivability

Deferred until the test above produces real numbers — no fabricated Monte
Carlo or drawdown estimate belongs here yet.

## 6. Red flags to watch for specifically in this test

- Spread trending rather than reverting (see section 3) — the single
  biggest risk specific to this pair.
- Any temptation to hedge-ratio-tune or window-tune after seeing a weak
  result — not permitted; if the first pass is weak, that's the answer.

## Verdict (as of this plan)

**needs_testing** — plausible domain (with one named, real caution), no data
cost (uses data already on hand and trusted), hypothesis is falsifiable and
pre-registered above. No claim yet about whether it works.
