# NQ / ES Opening Range Breakout — Pre-Registered Test Plan

Status: ~~PLAN ONLY. No code written, no test run yet.~~ **SUPERSEDED
2026-08-27 — the test has been run.** This document remains the
pre-registration record (the prediction and test design were locked in
BEFORE any data was inspected, per the propfirm-research-auditor discipline
used throughout this project — see `research/index_mean_reversion/` and
`research/nq_es_relative_value/` for the identical discipline applied to the
earlier two hypotheses), but the actual measured outcome now lives in
[RESULTS.md](RESULTS.md): the entry-predicts-direction test (§1), the
survivability simulation against the real firm rules (§2/§2.6), the MES-only
combined stop-loss + time-exit line of research (§2.7), and the reconciled
stop-loss recommendation (§3) covering both this file and
[STOPLOSS_HYPOTHESIS.md](STOPLOSS_HYPOTHESIS.md). Read this file for what
was predicted and why; read RESULTS.md for what actually happened.

Rule specified by the user, not by this audit (per that discipline, entry/exit
mechanism is the user's call, not something this process is allowed to
propose):
- Session open: 9:30am US Eastern (the NYSE cash-market open)
- Opening range: the high/low of the first 15 minutes after that open
  (09:30–09:45 ET)
- Breakout: a 1-minute bar **closing** beyond the range high (long) or range
  low (short) — a full close, not just a wick touch. This is already the more
  conservative of the two common definitions.

## 1. Constraints (Lucid Trading LucidPro $100K eval)

**Re-confirmed 2026-08-27** directly against Lucid Trading's own help center
(support.lucidtrading.com, LucidPro collection + Rules and Guidelines
collection) and the live account dashboard (LTE10089070250001) — this
replaces the 2026-08-19 version's two facts that had previously only been
corroborated by third-party trackers, not Lucid's own docs. Everything below
is now sourced to Lucid directly, not inferred:
- Profit target: $6,000 (6% of 100k) — confirmed on dashboard and in the
  "LucidPro Evaluation Account" article's account-size table.
- **Max Loss Limit (the real, account-failing barrier): $3,000 (3%),
  trailing to end-of-day balance only** — confirmed in the "LucidPro
  Drawdown" article. New detail not previously on record: the trail is not
  unbounded. Once the account's balance exceeds the Initial Trail Balance
  ($103,100 on a $100k account), the MLL **locks permanently at $100,100**
  and stops rising with further gains — the account gets less fragile to a
  single bad day as the challenge progresses, not more.
- **Daily Loss Limit: $1,800 - a SOFT limit**, now confirmed in Lucid's own
  words in the "LucidPro Daily Loss Limit" article: "you do not lose your
  account for hitting DLL as long as the Max Loss Limit has not been
  reached." Hitting it locks trading until the next session only.
- **No time limit, no minimum trading days** — confirmed in Lucid's own
  copy on the "LucidPro Evaluation Account" article: "take as long as you
  need to pass" / "pass the evaluation in one trading day."
- **Overnight/weekend holding**: confirmed in the "Allowed Trading Times"
  article — all positions must be closed by 4:45 PM EST Mon-Fri (market
  reopens Sun 6 PM EST); holding past that time is auto-liquidated by Lucid
  and is NOT a failed-account event, but the live script's own exit
  (~15:59 ET) and Ghost's backup flatten (16:05 EST) both sit comfortably
  inside this cutoff regardless.
- **News-trading stance**: confirmed ALLOWED on LucidPro in the "Other
  Trading Activities" article ("Traders may enter or exit positions around
  scheduled or unscheduled news events... without it being a breach") —
  execution risk during news is the trader's own, but it is not a rule
  violation. Ghost's unused "News Filter" is optional headroom, not a
  compliance requirement.
- **Automated trading**: explicitly permitted per the same article
  ("Automated trading systems and trade copiers are permitted") — the
  Ghost/webhook architecture this whole project runs on is compliant by
  name, not by inference.
- **Consistency rule**: exists but only applies once funded and requesting
  a payout, confirmed in the "LucidPro Consistency Percentage" article —
  largest single day's profit must stay under 40% of total account profit
  to request a payout (resets after each payout; does not apply to the eval
  stage or to Live-status accounts). Not a risk to passing the challenge,
  but worth remembering post-funding: a single outsized winning day could
  delay (not fail) a payout request.
- **Inactivity rule** (new, not previously on record): an account with $0
  net P&L for 30 straight calendar days is deemed abandoned and deleted,
  per the "Inactivity Policy" article. Not a practical risk for a strategy
  that trades most days, but worth knowing it exists.
- 90/10 split once funded (unchanged, not re-verified this turn)

- Losing streak survived = floor($1,800 / risk-per-trade-in-dollars)
- Trades to target = $6,000 / (expected $ per trade)

NOT MEASURED: both, until the test below produces real R and win-rate figures.

## 2. Domain check

Opening Range Breakout is one of the most famous published systematic
strategies in retail/CTA futures trading (Toby Crabel, early 1990s), and it
was designed specifically for this instrument class (index futures) and this
exact session transition (the cash-market open). That gives it a real,
structural rationale: overnight information from Asia and Europe sessions
gets absorbed into a single discrete price-discovery event at 9:30 ET, and
the first few minutes can plausibly carry genuine order-flow imbalance rather
than noise. That is a PRIOR, not a measurement.

Directly relevant local evidence, already on record in this project (see
`~/.claude/skills/propfirm-research-auditor/references/domain_priors.md`,
MEASURED section):

> H1 — Session breakout (London open, H1/H4), FX: 291 trades, mean R
> −0.0937, p = 0.2487 → REJECT.

That is the same *family* of mechanism (trade a breakout of the range set
right after a session opens) tested and rejected before — but on a different
market (FX, not index futures) and a different, arguably weaker session
transition (an arbitrary hourly FX "session" boundary has no true
open/auction; the NYSE cash open does). It is named here as a real caution,
not as disqualifying: the domain has changed on two of the three legs the
audit checklist asks about (different market, and the mechanism claim rests
on a session transition that carries more genuine information than an FX
hour-boundary does).

Also worth saying plainly, since it cuts the other way: ORB has been public
and heavily traded for over 30 years. Any edge simple enough to describe in
one sentence, on the most liquid index futures in the world, has had three
decades for the crowd to arbitrage it away. Being famous is not the same as
being current.

NOT MEASURED: whether this specific mechanism (9:30 ET open, 15-minute range,
close-beyond confirmation) carries any edge on NQ/ES. No local test has ever
looked at this exact construction.

## 3. Pre-registered falsifiable hypothesis

Signal, computed with no lookahead (everything known strictly at or before
the entry bar's close):

- Opening range = high and low of all 1-minute bars from 09:30:00 to
  09:44:59 ET.
- From 09:45 ET onward, scan forward minute by minute. The **first** 1-minute
  bar whose close is above the range high, or below the range low, is the
  signal — whichever happens first, only once per instrument per day. A day
  where neither happens (range never closed-beyond) produces no trade, not a
  loss.
- Entry price = that signal bar's own close (the price already known at the
  decision, consistent with every other test in this project — no entering
  at a price that has already passed).
- Exit = that same trading session's close (16:00 ET). This is the test-design
  choice for measuring "did the breakout's implied direction hold," not a
  proposed trading rule — it asks the plainest possible version of the
  question (did the rest of the day agree with the breakout) before any
  stop/target engineering is considered. A stop-loss/target layer is a later,
  separate gate for whatever survives this pass, per the isolation principle
  below.

Pre-registered, two-sided:
- Close above range high → next return to session close is POSITIVE
  (long) — p < 0.025
- Close below range low → next return to session close is NEGATIVE
  (short) — p < 0.025

(α = 0.025 = 0.05 / k, k = 2 for the two pre-registered sides — a fresh
Bonferroni budget for this hypothesis family, separate from the earlier two
tests in this project, since this is a structurally different signal
(intraday session-open breakout, not a daily quintile or a cross-instrument
spread). Flagged as a judgment call, not a hidden decision.)

## 4. Test design

- **Isolation**: flat size, one position per instrument per day, no trade
  management. Outcome = raw log-return from entry to session close, in the
  signal's direction, normalized by realized volatility over that same
  window (identical R-normalization machinery already built and trusted in
  `index_mean_reversion/screen_mean_reversion.py` / `track_forward.py` —
  reused, not redesigned). No stop-loss is simulated in this pass, so the
  "ambiguous bar" rule doesn't apply the same way it did for the swing tests;
  the close-beyond-range confirmation the user specified is itself the more
  conservative choice compared to a wick-touch trigger.
- **Sample**: NQ, ES, and YM, 1-minute bars, 2021-08-19 → 2026-08-18 (5 years,
  continuous front-month series built from two real Databento pulls — see
  `data/continuous/`). Exact trade count (days that actually produce a
  breakout) is not estimated in advance — it's whatever the data produces,
  reported once measured.
- **Significance**: per-trade t-test (not Sharpe), two-sided, threshold 0.025
  per side, computed with `~/Workspace/fp50k-ea/tools/edge_stats.py` (scipy
  is not installed on this machine; that script already does the regularized
  incomplete-beta t-test with no dependencies and is the standing convention
  in this project).
- **Sample-size reality check**: with the typical isolation-test σ ≈ 1.1R, a
  true edge of 0.10R needs ~950 trades to detect at α=0.025 (roughly, scaling
  the project's own reference table); 0.30R needs ~120. Whether NQ+ES produce
  enough breakout days over 5 years to resolve a small edge is NOT MEASURED
  yet — reported honestly once the actual trade count is known, before any
  conclusion is drawn from a possibly-underpowered result.
- **Replication**: NQ (primary) vs ES vs YM — sign must agree across all
  three, meeting the checklist's minimum-three-instrument standard. YM was a
  second, separate Databento purchase (same schema/date range as NQ+ES) made
  specifically to close the 2-instrument gap this plan originally flagged.
- **Cost model**: real, MEASURED Tradovate round-turn costs on entry and the
  session-close exit (same `REAL_COST_POINTS` table already used throughout
  this project), applied at each trade's own entry price. Zero-cost run
  required alongside, per standard practice — if there's no edge before
  costs, costs are irrelevant.
- **Pessimism**: decisions on closed 1-minute bars only, no same-bar
  re-entry, no lookahead from a bar's close into that same bar's entry.
- **Out-of-sample**: fresh chronological 70/30 split on the eligible
  (breakout-producing) day population, decided by position alone before any
  result is inspected — a new split, not reusing either earlier test's
  cutoff.
- **Timezone note** (implementation detail, not a judgment call): the raw
  data is UTC; 9:30/9:45/16:00 ET must be converted with real US
  Eastern-time DST rules (UTC-4 in summer, UTC-5 in winter), not a fixed
  offset. Getting this wrong would silently shift the "opening range" window
  on part of the year. Flagged so it gets checked, not assumed correct.

## 5. Survivability

Deferred until the test above produces real numbers — no fabricated Monte
Carlo or drawdown estimate belongs here yet.

## 6. Red flags to watch for specifically in this test

- ORB is a famous, decades-old public strategy — the single biggest risk is
  finding a paper-thin, curve-fit-looking edge and treating "it's a
  well-known strategy" as if that were evidence for it, rather than a reason
  for extra skepticism.
- Session-close exit with no stop-loss means a single bad day's tail can
  dominate the R distribution — worth a visual check of the R histogram
  before trusting the t-test's normal-approximation p-value.
  **Checked (2026-08-27, retroactively noting work already done):** the
  visual/statistical check is RESULTS.md §2.5 — no isolated outlier bin, a
  roughly bell-shaped distribution, and the mean stays positive even after
  removing the best 5% of trades. The natural follow-up this red flag
  implies — should the tail be cut with an actual stop-loss — is the
  question STOPLOSS_HYPOTHESIS.md and RESULTS.md §3's reconciliation were
  built to answer; see those for the current, still-unproven-for-live-use
  answer.

## Verdict (as of this plan)

~~**needs_testing** — plausible domain with a real structural rationale
(named above) alongside a real caution (a structurally similar mechanism
already measured at zero on FX), no new data cost (both Databento pulls
already paid for and built into continuous series), hypothesis is
falsifiable and pre-registered above. Replication now meets the project's
own 3-instrument standard (NQ, ES, YM). No claim yet about whether it works
— the test itself has not been run.~~

**SUPERSEDED 2026-08-27**: the test has been run and produced real,
MEASURED numbers — see [RESULTS.md](RESULTS.md). Short version: the
long-side entry showed a real, significant edge in-sample and out-of-sample
on NQ/ES; plain no-stop position sizing against the real firm rules sits in
a 31-51% survivability range for all four positions tested (§2.6); a
stop-loss overlay was tested, initially rejected, then found on correction
to actually *improve* survivability (§3 of this file / STOPLOSS_HYPOTHESIS.md);
and a separate MES-only combined stop + time-exit mechanism (RESULTS.md
§2.7) was reconciled against that finding on 2026-08-27 (RESULTS.md §3) as
the stronger candidate for MES specifically. None of this has been shipped
to the live script — see RESULTS.md §3 for the exact gaps still open before
any of it is deployable. This file's own verdict language above is left
untouched as the historical pre-registration record; do not read it as the
current state of the research.
