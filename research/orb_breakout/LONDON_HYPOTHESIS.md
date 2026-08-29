# London-session Opening Range Breakout — Pre-Registered Test Plan

Status: PLAN ONLY at the time this file was first written, before
`london_orb_test.py` was run or any output inspected. Same discipline as
[HYPOTHESIS.md](HYPOTHESIS.md), gated first through the
propfirm-research-auditor methodology check (verdict: `needs_testing`,
2026-08-20).

## 0. What this is and isn't

This tests whether the **same mechanism already validated at the NY open**
(HYPOTHESIS.md, RESULTS.md) also carries a signal at the **London equity
open**, on the same instruments (NQ/ES/YM, full-size data — same convention
the NY test used before any micro-contract sizing step). It does not
propose combining the two signals, sizing a live position, or running them
concurrently on the LucidPro account — that is a separate decision, gated
on this test's result plus a fresh joint-survivability simulation, per the
audit.

## 1. Domain check (carried over from the audit, not re-derived here)

- Same market (index futures) that already showed a real, replicated,
  out-of-sample-significant edge at the NY open — unlike the FX pairs this
  project already rejected on this same mechanism family.
- Weaker structural story than the NY open: 9:30 ET is NYSE's actual
  opening auction. London's 08:00 open has no equivalent formal auction for
  a CME-listed US index future — it's a real increase in European trading
  activity, not a discrete price-discovery event for *this* instrument.
  Treated as a real reason to expect a smaller or absent edge, not a reason
  to skip the test.
- domain_priors.md's H1 (FX, London-open session breakout, REJECTED,
  mean −0.09R) is the same mechanism shape on a different market — named as
  caution, not disqualifying, same reasoning HYPOTHESIS.md already applied
  to the NY version.

## 2. Rule under test (fixed before running, mirrors the NY convention — not tuned to this data)

- **Session**: London equity-market open, 08:00 **Europe/London civil
  time** (properly DST-adjusted via the `Europe/London` zone, not a fixed
  ET offset — London and NY change clocks on different dates, so a fixed
  offset would silently shift the window a few weeks a year).
- **Opening range**: high/low of all 1-minute bars from 08:00:00 to
  08:14:59 London time (15 bars) — same 15-minute width as the NY test,
  the un-tuned, already-established convention, not re-chosen here.
- **Breakout**: first 1-minute bar (in absolute time order, scanning
  forward from the end of the range window) whose **close** is beyond the
  range high (long) or range low (short) — same close-beyond-range,
  no-wick-touch definition as the NY test.
- **Entry price**: that signal bar's own close.
- **Exit**: same trading day's regular session close, 16:00 ET — identical
  exit convention to the NY test (same instrument, same day, same
  session-close discipline), not a new rule invented for this window.
- **Day boundary**: the calendar date is anchored on the US Eastern trading
  day (`date_et`), same as every other test in this project. London's
  08:00 open falls at roughly 03:00-04:00 ET (varies with the DST-offset
  mismatch weeks), which is always *before* that same date's 9:30 ET open
  — so it maps cleanly onto one trading day with no boundary ambiguity.

Pre-registered, two-sided (same structure as HYPOTHESIS.md §3):
- Close above London range high → return to session close is POSITIVE
  (long), p < 0.025
- Close below London range low → return to session close is NEGATIVE
  (short), p < 0.025

k = 2, fresh Bonferroni budget for this specific test (same reasoning
HYPOTHESIS.md used: a structurally distinct signal from the daily/spread
tests already run in this project; this is its first and only run so far,
k does not need to fold in the NY ORB test, which is a different session
window even though it shares the entry-confirmation mechanism).

## 3. Test design

- **Isolation**: identical machinery to orb_test.py — flat size, one trade
  per instrument per day, no stop/target, R = raw log-return
  entry-to-session-close in the signal's direction, divided by that same
  window's own realized volatility. Reused via the same
  `screen_mean_reversion.py` import, not reimplemented.
- **Sample**: NQ, ES, YM continuous front-month 1-minute data, same files
  already built for the NY test (`data/continuous/`), 2021-08-18 →
  2026-08-18. Confirmed before running: NQ has 08:00-08:14 London-time
  coverage on 1,291 of 1,558 total trading days (~83% — some days lack
  pre-market data in this feed, handled the same way orb_test.py already
  handles an incomplete range: skip the day, no trade, not a loss).
- **Significance**: per-trade t-test, same `edge_stats.py`-equivalent
  machinery already in `screen_mean_reversion.py`, threshold 0.025/side.
- **Replication**: NQ/ES/YM sign agreement required, same 3-instrument
  standard.
- **Cost**: real Tradovate cost model, same `REAL_COST_POINTS` table.
  Zero-cost run required alongside.
- **Pessimism**: closed bars only, no same-bar re-entry, no lookahead —
  identical to orb_test.py.
- **Out-of-sample split**: reuses the **identical, already-locked cutoff
  date from the NY test** (2025-02-14, from `orb_test.py`'s NQ-day 70/30
  split) rather than computing a fresh split on this window's smaller
  eligible-day population. Deliberate: picking a new cutoff for this test
  would itself be a researcher degree of freedom the discipline is meant to
  remove.

## 4. Survivability

Deferred. Not run in this pass — no fabricated Monte Carlo belongs here
before the signal itself is measured. If this signal clears steps 1-3, the
required next step (named explicitly in the audit) is a **joint**
survivability simulation with the NY signal's trade dates combined, not a
reuse of RESULTS.md's single-signal ruin numbers.

## 5. Red flags to watch for specifically in this test

- Weaker structural rationale than the NY open (§1) — a passing result here
  deserves more scrutiny than the NY result got, not less.
- London-time coverage gaps in the data (~17% of days missing pre-market
  bars) could bias the eligible-day sample if the gaps aren't random with
  respect to trading conditions — not something this pass can rule out, but
  handled the same conservative way (skip, don't guess) as
  every other incomplete-data day in this project.

## Verdict (as of this plan)

**needs_testing**, per the propfirm-research-auditor audit. This document
locks the design; `london_orb_test.py` runs it next, in-sample first.
