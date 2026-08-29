# LBMA/LPPM fix-window breakout on precious metals — pre-registration

Status: PLAN ONLY at the time this file was first written. Locked before any
data is touched, any script is run, or any output is inspected — per this
project's standing discipline (see `orb_breakout/HYPOTHESIS.md` and
`orb_breakout/RESULTS.md` for the convention this follows).

This is an independent research line, not a variant of `orb_breakout/`. It
trades a different asset class (precious metals, not equity-index futures)
on a different mechanism (a scheduled administered auction, not the NYSE
cash open), and does not share that folder's data, cost model, or multiple-
comparison budget.

## Why this exists

Came out of a `propfirm-research-auditor` domain-check conversation
(2026-08-28) started by the question "should we diversify off MNQ/MES into
an uncorrelated instrument." Two candidates were screened first and rejected
or downgraded:

- **10-year Treasury note futures (ZN), ORB copy-pasted to the 9:30 ET NYSE
  open** — `reject_early`. ZN has no equivalent of a single formal opening
  auction at that clock time; it trades nearly continuously across Tokyo,
  London and New York, so the mechanism the equity ORB is thought to exploit
  (overnight imbalance resolved by one auction) doesn't structurally exist
  there at 9:30 ET.
- **Gold (GC), ORB copy-pasted to the 9:30 ET NYSE open** — `needs_testing`
  but weak. Gold does react to cross-asset flows that spike at the US
  equity open, but that's a borrowed, secondhand rationale, not gold's own
  session structure.
- **Gold, anchored to its own fix times instead** — `needs_testing`, the
  strongest of the three. This file is that hypothesis, formalized.

## The mechanism

The LBMA Gold Price (and the LPPM-administered platinum/palladium
equivalents) is set twice daily via a real multilateral electronic auction —
major bullion banks execute genuine client orders to settle exactly at that
price. That is a structural cause (banks are obligated to execute client fix
orders, not discretionarily trading), not just a time of day with more
volume. This is a materially different rationale from the rejected ZN case
and stronger than the borrowed gold/9:30 case.

**Important framing correction**: this is not literally "the ORB, but timed
to the fix." A fix is one administered price point, not a session opening
that forms a range over several minutes. The actual claim is closer to a
post-event-drift hypothesis: does gold's price move in the minutes
immediately after a fix predict continuation over a subsequent fixed
horizon.

## Rule under test (fixed before running, not tuned to the data)

For each fix (AM ≈ 5:30am ET, PM ≈ 10:00am ET — both DST-adjusted; see caveat
below), take the high/low range of the **5-minute window immediately
following the fix** (5 minutes chosen for economic/prior reasons, not
fitting: it matches this project's existing ORB convention and matches the
window the Zarattini/Barbon/Aziz 2024 SSRN paper found strongest among 5/15/
30/60-minute variants for a structurally similar breakout mechanism).

If price closes beyond that 5-minute range's high (or low) within the
following 60 minutes, that's the entry, in the direction of the breakout.
Otherwise, no trade for that fix. Exit fixed at 60 minutes after entry.

**R** = raw price move ÷ the 5-minute fix-window's own range width (same
convention as `orb_breakout/STOPLOSS_HYPOTHESIS.md`).

## Pre-registered hypothesis

If gold (GC) breaks out beyond the 5-minute post-fix range in the direction
of that range's own move, then the forward return over the next 60 minutes
is **> 0 R with p < 0.05** (two-sided, per-trade t-test on R — not Sharpe),
pooled across the sample period below, net of a real futures cost model.

**k = 1.** This is the first test of this specific mechanism family. It does
not draw on or spend the FX price-only study's k=6 budget (`fp50k-ea`) — that
was a structurally different claim (price series alone, no external
information). It is still hypothesis N+1 in the overall research program and
should be logged as such for honesty, even though its own budget starts
fresh.

**Pre-registered second side**: none. Direction is set by the fix-window's
own move (mirrors `orb_long_ghost.pine`'s directional bias filter), not a
separate short-side claim.

**Pre-registered replication set**: silver (SI) and platinum (PL), chosen
before any run — both have the same twice-daily LBMA/LPPM administered-fix
structure. The sign of the effect must agree across GC, SI, and PL or the
mechanism is not believed; one instrument is an anecdote. AM-fix and PM-fix
results are reported separately as an internal replication check (both
shown, not just whichever looks better), not as two independently-budgeted
hypotheses.

## Testing plan

| | |
|---|---|
| Sample | 1-minute GC/SI/PL futures data, **2015-present only**. The LBMA fix process was redesigned in 2015 after the old "London Gold Fixing" manipulation scandal; data from before that describes a defunct mechanism and must not be pooled in. |
| Significance | Per-trade t-test on R: `t = mean(R) / (sd(R)/sqrt(N))`, two-sided, df = N-1. Reuse `~/Workspace/fp50k-ea/tools/edge_stats.py` (already built, no dependencies) rather than annualized Sharpe, which hides sample size. |
| Multiple comparisons | k=1 for this family (see above). |
| Replication | 3 instruments (GC, SI, PL), sign must agree. AM vs. PM shown as a secondary check, not separately budgeted. |
| Costs | Real commission + spread model for GC/SI/PL. **Does not exist yet** — unlike `orb_breakout`'s `REAL_COST_POINTS` table for NQ/ES/MNQ/MES, this has to be built from scratch before anything can run. |
| Zero-cost run | Mandatory alongside the costed run. If the zero-cost result is ≈0, the signal carries no directional information regardless of what costs do to it — reject outright, don't go hunting for cheaper execution. |
| Pessimism | Ambiguous bar (stop/target both inside one bar) scores as the loss, always. Closed bars only. No same-bar re-entry. Correct bid/ask fill direction (long fills at ask, exits trigger on bid). |
| Out-of-sample | Chronological split decided now, before looking at anything: most recent ~20% of the 2015-present window held out, looked at exactly once. If that result is bad, the hypothesis is dead — no re-testing on the same held-back data. |

## What's missing before this can actually run (not measured, not assumed)

- No intraday cost model for GC/SI/PL yet.
- No confirmed data source for GC/SI/PL 1-minute history. A Databento
  account exists (see the `databento-credit-check` reminder) but hasn't been
  checked for coverage or cost on these three instruments specifically.
- LBMA/LPPM fix times need explicit handling of UK/US daylight-saving
  mismatches — the UK and US do not switch clocks on the same calendar
  dates each year, so a fixed year-round ET clock time would drift wrong
  twice annually. Must be computed from the actual London local fix time,
  converted per-day, not hardcoded.
- Whether LucidPro's rules restrict trading around scheduled benchmark/news
  events is still unverified. If there's a blackout window near fix times,
  this could be untradeable regardless of edge — worth checking before
  investing in the cost model and data sourcing above.

## Status

`needs_testing`. Nothing in this file is a result, a green light to code
anything, or clearance to trade. The domain check and hypothesis design are
done; the data, cost model, and actual test run are not.
