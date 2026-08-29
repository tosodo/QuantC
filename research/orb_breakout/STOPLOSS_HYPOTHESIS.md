# Adding a hard stop-loss to the validated long-side ORB — pre-registration

Status: PLAN ONLY at the time this file was first written. Locked before
`stoploss_test.py` was run or any output inspected, per this project's
standing discipline (see HYPOTHESIS.md / RESULTS.md in this folder).

## Why this test exists

RESULTS.md's own conclusion named the one thing still missing before the
validated long-side 9:30 ET ORB signal (NQ/ES, in-sample + out-of-sample
significant, no decay) could be considered for the actual challenge:

> A real hard stop-loss (an early exit if a trade goes badly wrong mid-day,
> rather than always holding to the close) — deliberately not designed here;
> would be a new mechanism requiring its own test, not pure sizing arithmetic.

This is that test. Position sizing is NOT re-opened here — RESULTS.md §2.6
already measured that micro contracts (MNQ/MES, qty=1) survive the corrected
$3,000 trailing drawdown at 89–99%, and that number stands.

## Rule under test (fixed before running, not tuned to the data)

Stop-loss = the **opposite side of the same 09:30–09:44 ET opening range**
already used to generate the entry signal. This is the natural, un-tuned
first candidate — the same distance already implicit in the range itself,
not a new free parameter chosen by looking at outcomes. No other stop
distance is tested in this pass; trying several and picking the best would
be curve-fitting, not a test.

Mechanically: entry unchanged (first 1-min bar closing beyond the range,
same as the validated mechanism). From the entry bar onward, scan forward
bar by bar:
- If a bar's low (long) touches or crosses the opposite side of the range
  before the session close → exit there, stop-loss triggered.
- Otherwise → exit at the session close, exactly as already validated.

Only the **long side** is tested — the short side was already rejected
(RESULTS.md §1, sign disagreement out-of-sample) and is out of scope here.

## What "R" means in this test

The original validated test normalized R by each trade's own realized
volatility, which has no natural connection to a stop distance. For a
stop-loss comparison, R here is redefined as **raw price move ÷ opening
range width** — the same convention already used in
`mnq_session_open/screen_session_open.py` for exactly this reason. This is
a different R unit than RESULTS.md's table; the two are not directly
comparable number-for-number, only in sign and shape.

## Pre-registered questions (not yet answered)

1. On the same trade population already found to have a positive edge
   (NQ + ES long side), does adding this stop **change the mean R**
   materially versus the no-stop baseline, computed in the same range-width
   R units for both?
2. What fraction of trades get stopped out before the session close?
3. Does the stop **reduce the worst-trade tail** (the red flag RESULTS.md
   already named — a no-stop exit lets one bad day dominate)?
4. Fed into the same `ruin.py` survivability machinery used in RESULTS.md
   §2 (corrected firm rules: $3,000 real trailing DD, $1,800 soft daily
   pause, no time limit), does survivability improve, stay flat, or worsen?

This is a comparison, not a fresh significance test against zero — the
edge's existence was already established. No new Bonferroni budget is
consumed; this doesn't test a new independent hypothesis about market
structure, it tests one specific, pre-named risk-management overlay on an
already-accepted signal.

## Sample / procedure

- Same instruments, same data, same in-sample/out-of-sample cutoff already
  used by `orb_test.py` (decided by chronological position on the primary
  instrument, never by outcome).
- In-sample first (default, safe to re-run); out-of-sample looked at once,
  after the in-sample design is frozen — no changes to the stop rule after
  seeing either slice.
- Real Tradovate cost model (same `REAL_COST_POINTS` table), plus mandatory
  zero-cost run.
- Reported honestly as MEASURED, whichever way it comes out. A stop-loss
  that turns out to hurt more than it helps is itself a usable answer — it
  would mean the validated version (already in `orb_long_ghost.pine`, no
  stop) should ship as-is rather than being modified.

## Results (MEASURED) — 2026-08-20

**In-sample** (n=455 NQ / 451 ES): mean R improves with the stop (NQ
+0.082→+0.155, ES +0.187→+0.185, range-width units), and the worst single
trade shrinks dramatically (NQ −8.79R→−1.91R, ES −25.84R→−1.43R). Stopped out
46.9% of NQ trades, 53.0% of ES trades before the close.

**Out-of-sample** (n=196 NQ / 211 ES, looked once, no changes made to the
rule after seeing it): mean-R effect is now mixed — helps NQ slightly
(+0.054→+0.068), hurts ES (+0.109→+0.026) — and neither the stopped nor
unstopped version reaches significance in this small, high-variance
out-of-sample slice (all p > 0.4). The tail-risk cut replicates cleanly
though: worst trade NQ −11.80R→−1.31R, ES −13.31R→−1.40R, both instruments,
both samples.

**Survivability** (the deciding question, #4 above): fed the full pooled
with-stop R series (n=1,313, real-cost-adjusted) into `ruin.py` against the
corrected LucidPro rules, with risk-pct calibrated to the *actual* dollar
value of the stop distance for each micro contract — median opening-range
width × point value (MNQ $2/pt, MES $5/pt) — the same method RESULTS.md §2.6
used for the no-stop baseline, so the comparison is apples-to-apples. (An
earlier pass reused the no-stop run's risk-pct labels directly, which was
invalid — the two tests use different R units with different typical size,
and that mismatch produced a misleadingly bad number; caught and redone
before reporting.)

| Position | No-stop (§2.6, baseline) | With stop |
|---|---|---|
| 1 micro NQ (MNQ) | 89.1% | **63.5%** |
| 1 micro ES (MES) | 99.1% | **94.3%** |

**Adding the stop makes survivability worse on both instruments**, despite
cutting the worst-case trade by 5–18x. The mechanism: the stop is hit on
roughly half of all trades (46.9–53.0%), converting many days that would
have closed flat or only mildly negative into a fixed ~−1R loss. LucidPro's
drawdown is *trailing* (resets to the highest close-of-day balance), so
frequent moderate losses erode the cushion faster than rare large losses do
— a trailing-DD rule punishes loss *frequency* more than it punishes loss
*size*. The stop wins on the metric it was designed for (tail risk) and
loses on the metric that actually decides the challenge (survivability).

**Verdict: reject.** ~~The stop-loss overlay is tested and does not improve
the account's chances — it makes them worse.~~ **SUPERSEDED — see the
correction below. Do not read this section's verdict on its own.**

## Correction (2026-08-27) — the survivability comparison above was invalid

RESULTS.md §2.6 (2026-08-21) found that the "median-$/1R" risk-pct
calibration this file's own survivability row used for the no-stop baseline
was too optimistic, and reversed the earlier 89.1%/99.1% no-stop figures
down to 31.30%/51.36% once each trade's *exact* real dollar P&L was fed to
`ruin.py` instead of one typical dollar-risk figure applied uniformly. That
correction explicitly flagged that this file's WITH-STOP column "has not
been re-run with the exact-dollar method and should not be read as still
applying."

`stoploss_reconciliation.py` does that re-run: both the no-stop and
with-stop columns recomputed with the exact-dollar method (same technique as
`baseline_reconciliation.py`), full 5-year history, same firm rules, same
entry/stop rule as above — nothing about the mechanism changed, only the
sizing arithmetic.

| Position | No-stop (exact-$) | With stop (exact-$) | Delta |
|---|---|---|---|
| 1 micro NQ (MNQ) | 31.30% | **54.30%** | **+23.0 pts** |
| 1 micro ES (MES) | 51.36% | **65.89%** | **+14.5 pts** |

**The direction flips entirely.** Under the correct, exact-dollar sizing
method, adding this stop-loss *improves* survivability on both instruments,
not worsens it. The earlier "reject" verdict was an artifact of comparing a
correctly-calibrated with-stop column against an incorrectly-calibrated
(inflated) no-stop baseline — not a real property of the stop-loss overlay
itself.

**Why the earlier reasoning was backwards**: the trailing-drawdown-punishes-
frequency argument is still true in isolation, but it was outweighed by a
bigger effect the old calibration couldn't see — cutting the catastrophic
left tail raises each instrument's *exact* mean dollar P&L per trade (MNQ:
$14.11 → $19.62) or, for MES, leaves it only slightly lower ($11.14 → $6.39)
while sharply cutting the variance that actually drives ruin in a Monte
Carlo simulation. Once ruin.py sees the real dollar swing of every trade
instead of a typical figure, the variance reduction dominates.

**Revised verdict: `promising_but_unproven`, not reject.** This is a genuine
reversal, not a refinement — the stop-loss overlay should not be treated as
closed or rejected. It is also not cleared for live use: this reconciliation
only re-measured *survivability* (a full-history stress test on the already-
realised trade sequence). It did **not** re-run the mean-R significance test
or the in/out-of-sample split from the section above — those numbers (mixed
significance out-of-sample, NQ helps slightly / ES hurts slightly) still
stand as originally measured and are not addressed by this correction. Real
slippage at the stop fill is also still unmodeled (assumed exact fill at
`range_low`), which would only work against the with-stop column, not for
it. This closes out the *sizing-arithmetic* half of the "next and final
gate" named in RESULTS.md §3 — it reopens, rather than closes, the question
of whether to deploy this stop.

**Pointer (2026-08-27, later same day)**: for **MES specifically**, this
verdict has since been narrowed further — see the reconciliation in
[RESULTS.md §3](RESULTS.md#3-not-measured--still-open), which compares this
file's stop (opposite side of the opening range, no slippage modeled) against
§2.7's separate MES-only combined price-stop + 90-min time-exit mechanism
(which *does* survive a realistic slippage test) and finds §2.7's mechanism
the stronger-tested candidate for MES. This file's 65.89% MES figure above
should be read as superseded by that reconciliation, not as the current
recommendation for MES. **For MNQ**, no such comparison exists — this file's
54.30% figure remains the only number on record, still with slippage
unmodeled.
