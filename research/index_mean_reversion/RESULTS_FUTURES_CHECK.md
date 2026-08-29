# Index 20d-quintile mean reversion — futures-tradability translation check (2026-08-19)

## Verdict: `promising_but_unproven` (unchanged from the original futures test — this check does NOT support the upgrade to `needs_testing` that the cash-index-only deep test earned)

This is **not a new hypothesis**. It is a validation check on the exact same
pre-registered rule already tested twice (`screen_mean_reversion.py`,
`screen_mean_reversion_deep.py`): nothing about the mechanism, the
20d/504d/20d parameters, the R-multiple formula, the entry-at-next-open
timing, or the statistical tests was changed anywhere in this task.

**The question:** `screen_mean_reversion_deep.py` found a *stronger* result
when the same rule was tested on 39-57 years of cash-index history
(^GSPC/^IXIC/^RUT) instead of ~25 years of futures history — 3 of 6
out-of-sample cells cleared the Bonferroni bar instead of 1 of 6, with
perfect 12/12 sign agreement. But nobody can trade a cash index; only the
futures contract is tradable on Tradovate. So: if the quintile *threshold*
is calibrated on the long, clean cash-index history, but the *trade* is
actually simulated on the real futures contract (real entry/exit prices,
real costs), does the stronger result survive?

**Short answer: no, not clearly.** In the out-of-sample slice, **0 of 6
cells cleared the Bonferroni bar** (weaker than even the original
futures-only test's 1 of 6), and one cell's direction flipped sign (Russell
top-quintile, though on a tiny, near-zero, non-significant reading). The
standalone Russell-futures-only check (Task 4) is similarly mixed. This
does not kill the underlying idea — the in-sample Nasdaq leg and most
out-of-sample directions still point the pre-registered way — but it is a
plain, un-rescued finding that the cash-index test's apparent improvement
did not carry over cleanly to what can actually be traded. Per this
project's methodology, results are reported as measured; nothing here has
been adjusted, filtered, or re-parameterized to look better.

---

## Task 1 — new data: RTY=F (Russell 2000 futures)

Fetched via a new standalone script, `fetch_data_rty.py` (does not modify
`fetch_data.py`), same approach already verified there: Yahoo v8 chart API,
`range=25y` (NOT `range=max`, which silently demotes continuous-futures
series to monthly bars — the trap already documented in `fetch_data.py`).

| Symbol | First bar | Last bar | Bar count | Gap check |
|---|---|---|---|---|
| RTY=F | 2017-07-10 | 2026-08-19 | 2,294 | median 1 calendar day over the last ~260 bars — true daily bars, not monthly-demoted |

**RTY=F only goes back to 2017-07-10 on Yahoo — ~9.1 years**, vs. ~24-25
years for NQ=F/ES=F/YM=F. This is not a fetch shortfall (the 25y range
parameter was requested, same as the others); Yahoo's continuous RTY=F
series simply doesn't extend further back. This shorter history is the
single biggest structural limitation of everything below involving RTY=F,
and it is **not** something a longer fetch window would fix (`range=max`
would only trigger the monthly-demotion trap, not add years).

## Task 2 — RTY/M2K real cost (MEASURED, not approximated)

Fetched `https://www.tradovate.com/TradovateAllInRates120625.pdf` directly
(same PDF already used for NQ/ES/YM/MNQ). **RTY and M2K ARE both listed** —
no fallback to the YM approximation was needed.

| Row (PDF) | Per-side all-in: Free / Monthly / Lifetime | Point value | Round-turn points: Free / Monthly / Lifetime |
|---|---|---|---|
| CME RTY — E-Mini Russell | 2.88 / 2.58 / 2.18 | $50/pt | **0.1152 / 0.1032 / 0.0872** |
| CME M2K — Micro E-Mini Russell | 0.95 / 0.85 / 0.65 | $5/pt | 0.38 / 0.34 / 0.26 |

Round-turn points = 2 × per-side $ rate, ÷ point multiplier (identical
method already used for NQ/ES/YM/MNQ in `screen_mean_reversion.py`).
RTY's row shares the identical $ commission schedule as ES/NQ/YM (all
full-size index products: Exchange&NFA $1.40, commission Free/Monthly/
Lifetime 1.29/0.99/0.59) and the same $50/pt multiplier as ES, so RTY's
round-turn point cost comes out numerically **identical to ES's**
(0.1152/0.1032/0.0872 pts) — a coincidence of Tradovate's flat fee
schedule and shared multiplier, verified directly against the PDF table,
not carried over as an approximation. This is used in both
`task3_futures_translation.py` and `task4_rty_standalone.py` as
`RTY_COST_POINTS`, Free-plan tier (worst-case, matches the tier already
used as the primary table in `RESULTS.md`/`RESULTS_DEEP.md`).

## Task 3 — translation test: cash-index-calibrated threshold, traded on real futures

New script: `task3_futures_translation.py` (does not modify either existing
script; imports `FORWARD`, `LOOKBACK_R20`, `LOOKBACK_QUINTILE`,
`REAL_COST_POINTS`, `percentile`, `load`, `filter_sample`, `non_overlapping`,
`split_dates`, `report` directly from `screen_mean_reversion.py`). Per leg:
threshold classified on the cash index's own trailing 504-day distribution
(byte-identical construction to `build_signals()`), then the SAME calendar
date is looked up in the futures series and a real trade is simulated there
(entry at futures' next-day open, exit at futures close 20 futures-trading
days later, real Tradovate cost ÷ that trade's own futures entry price —
the exact R-multiple formula copied from `build_signals()`, not reinvented).
Real-cost pass only (zero-cost pass skipped per task instructions).

**Eligible-signal accounting (skips reported, not hidden):**

| Leg | Futures data range | Index-side eligible signals | Translated to a trade | Skipped: outside futures range | Skipped: holiday/gap | Skipped: near data end |
|---|---|---|---|---|---|---|
| Nasdaq (IXIC→NQ) | 2001-08-20 → 2026-08-19 | 5,577 | 2,468 | 3,106 | 0 | 3 |
| S&P500 (GSPC→ES) | 2001-08-20 → 2026-08-19 | 5,634 | 2,509 | 3,122 | 0 | 3 |
| Russell (RUT→RTY) | 2017-07-10 → 2026-08-19 | 3,791 | 958 | 2,832 | 0 | 1 |

**Fresh split (Task 3d):** cutoff decided by position alone on the
Nasdaq leg's (IXIC→NQ) translated trade dates — a population never used
for a split decision before, not reused from either prior script. Cutoff:
**2019-08-23**. Same cutoff date applied to all three legs (same
convention as both prior scripts). Note this cutoff sits well before RTY=F
even has enough history for a meaningful in-sample slice — the Russell
leg's in-sample cell is consequently very small (its data only starts
2017-07-10, so the 2001–2019 window that defines "in-sample" for Nasdaq/
S&P barely overlaps the RTY leg). This is reported as-is, not adjusted.

**In-sample (through 2019-08-23), non-overlapping, real cost:**

| Leg | Side | n | mean R | t | p |
|---|---|---|---|---|---|
| Nasdaq | bottom | 44 | +0.5157 | +3.304 | 0.0019 * |
| Nasdaq | top | 44 | -0.4334 | -2.827 | 0.0071 * |
| S&P500 | bottom | 46 | +0.2814 | +1.796 | 0.0793 |
| S&P500 | top | 45 | -0.2000 | -1.602 | 0.1162 |
| Russell | bottom | 7 | +0.6674 | +1.578 | 0.1656 |
| Russell | top | 5 | -0.8024 | -1.168 | 0.3078 |

\* clears the pre-registered Bonferroni bar (p < 0.025). **2 of 6 in-sample
cells clear** (both Nasdaq only).

**Out-of-sample (after 2019-08-23), non-overlapping, real cost — looked
once:**

| Leg | Side | n | mean R | t | p |
|---|---|---|---|---|---|
| Nasdaq | bottom | 19 | +0.4435 | +2.155 | 0.0450 |
| Nasdaq | top | 19 | -0.4077 | -1.676 | 0.1111 |
| S&P500 | bottom | 18 | +0.5165 | +1.992 | 0.0626 |
| S&P500 | top | 19 | -0.2820 | -1.065 | 0.3007 |
| Russell | bottom | 17 | +0.5173 | +2.282 | 0.0365 |
| Russell | top | 20 | **+0.0513** | +0.216 | 0.8312 |

**0 of 6 out-of-sample cells clear the Bonferroni bar** — weaker than the
original futures-only test (1 of 6) and much weaker than the cash-index
deep test (3 of 6). Russell's top-quintile out-of-sample mean flipped sign
(should be negative under the hypothesis; came out +0.0513, small
magnitude, not significant, but a genuine sign disagreement, not rounding).

**Sign-agreement / replication check:**
- In-sample: bottom {Nasdaq +, S&P500 +, Russell +} → AGREE. top {Nasdaq -, S&P500 -, Russell -} → AGREE.
- Out-of-sample: bottom {Nasdaq +, S&P500 +, Russell +} → AGREE. top {Nasdaq -, S&P500 -, **Russell +**} → **DISAGREE**.

3 of 4 side/sample groups still agree in direction; the one disagreement is
small-magnitude and on the leg with by far the smallest, most recent, most
data-starved sample (Russell, n=20, futures history only since 2017).

## Task 4 — standalone RTY=F test (own threshold, own trade, no cash-index data used)

New script: `task4_rty_standalone.py` (imports `build_signals`,
`split_dates`, `filter_sample`, `non_overlapping`, `report`, `load`
directly from `screen_mean_reversion.py`, unmodified). Fresh split decided
on RTY's own eligible signal dates alone — cutoff **2023-12-15** (RTY data:
2017-07-10 → 2026-08-19, 2,294 bars).

**Non-overlapping results, real cost (Free plan):**

| Sample | Side | n | mean R | t | p |
|---|---|---|---|---|---|
| In-sample | bottom | 13 | +0.0971 | +0.454 | 0.6577 |
| In-sample | top | 13 | -0.5999 | -2.084 | 0.0592 |
| Out-of-sample | bottom | 5 | +1.0411 | +2.229 | 0.0897 |
| Out-of-sample | top | 7 | **+0.2606** | +0.861 | 0.4222 |

**0 of 4 cells clear the Bonferroni bar.** Directional signs: in-sample
bottom +/top - agree with the hypothesis; out-of-sample bottom + agrees,
but **out-of-sample top came out positive (+0.2606) — the same sign
disagreement seen in Task 3's Russell leg**, on an even smaller sample
(n=7). Given RTY=F's very short (~9.1y) tradable history, sample sizes here
are too small (n=5-13 per cell) to draw any real conclusion either way —
this is a "not enough data yet" result, not a "disproven" result, but it
provides no supporting evidence for the pattern either.

## Replication sign-agreement summary (all tasks combined)

| Test | Population | Sign agreement |
|---|---|---|
| Original futures test (`RESULTS.md`) | NQ/ES/YM, OOS | 6 of 6 |
| Deep cash-index test (`RESULTS_DEEP.md`) | GSPC/IXIC/RUT, in+OOS | 12 of 12 |
| Task 3 translation test (this file) | NQ/ES/RTY, in-sample | 3 of 3 pairs agree (bottom, top) |
| Task 3 translation test (this file) | NQ/ES/RTY, out-of-sample | bottom agrees (3/3); top disagrees (RTY flips) |
| Task 4 standalone RTY (this file) | RTY only, in+OOS | bottom agrees both samples; top agrees in-sample, flips OOS |

## MEASURED vs. NOT MEASURED

**MEASURED**
- RTY=F daily bars, 2017-07-10 → 2026-08-19, gap-checked (true daily bars).
- RTY and M2K round-turn costs, directly from Tradovate's All-In Rates PDF
  (CME RTY row) — no approximation, no YM fallback needed.
- All Task 3 and Task 4 n/mean R/t/p figures above, computed by the two new
  scripts, reusing `screen_mean_reversion.py`'s constants and R-multiple
  formula unchanged.
- Eligible-signal and skip counts for the translation test (Task 3 table).

**NOT MEASURED**
- Slippage/spread-crossing cost beyond Tradovate's quoted all-in rate, on
  any leg.
- Continuous front-month futures proxy (Yahoo), not back-adjusted for roll
  gaps, on any of NQ=F/ES=F/RTY=F.
- Whether the Task 3/4 weak-OOS result would look different with more
  Russell futures history — RTY=F's ~9.1y ceiling is a Yahoo data
  limitation, not something re-fetching today would change.
- Independence of the three legs (same caveat already stated in
  `RESULTS_DEEP.md` — these are correlated broad-equity measures, not
  independent replications).

## Bottom line for a non-technical read

Two things were tested here, and both came back weaker than hoped, not
stronger.

**Task 3** asked: if we use the *longer, cleaner* history (going back to the
1970s/80s) to decide when the signal should fire, but then actually place
the trade on the *real, tradable* futures contract with *real* trading
costs — does the improved result from the last report still hold up? The
honest answer is **not clearly**. In the fresh, never-before-looked-at data,
none of the six checks (three markets × two directions) were strong enough
to call statistically real — a weaker showing than even the very first test
run in this project, and one check (Russell 2000, the short-squeeze
direction) came out pointing the wrong way, though on a very small, mostly
noise-level reading.

**Task 4** asked a simpler, separate question: using *only* the roughly
nine years of real Russell 2000 futures data that actually exists (this
contract's tradable history doesn't go back further on the data source
used), does the same pattern show up on its own? Also **not clearly** —
the sample sizes are simply too small (5 to 13 trades per check) to say
much either way, and one check also came out pointing the wrong direction.

**What this does NOT mean:** it does not disprove the underlying idea, and
it does not undo the earlier finding that the pattern holds up well on the
long cash-index history alone (that finding, reported separately, still
stands as its own result). What it does mean is that the step this task
set out to check — "does the improved version of this idea survive being
translated onto the actual thing you'd trade, with real costs" — did not
succeed. This is exactly the kind of result the project's methodology
exists to surface honestly rather than explain away: the verdict for the
tradable-futures version of this idea stays at **`promising_but_unproven`**,
unchanged from the original test, and this check specifically does **not**
support carrying the cash-index test's upgraded `needs_testing` status over
to what can actually be traded on Tradovate. More Russell 2000 futures
history will accumulate with time (it cannot be back-filled), and that is
the only lever that would meaningfully thicken the weakest leg of this
check going forward.

## How to reproduce

```
cd /Users/osodo.t/QuantC/research/index_mean_reversion
python3 fetch_data_rty.py                                   # re-pull RTY=F (already run 2026-08-19)
python3 task3_futures_translation.py                        # translation test, both samples printed in one run
python3 task4_rty_standalone.py --sample in  --real-cost-tier free   # RTY-only, in-sample
python3 task4_rty_standalone.py --sample out --real-cost-tier free   # RTY-only, out-of-sample (look once)
```
