# Overnight-range filter: in-sample result (7 Oct 2026)

Plan: [HYPOTHESIS.md](HYPOTHESIS.md). Script: `overnight_range_screen.py`. In-sample only (through 2025-02-14).
The held-out slice was NOT looked at, as the plan requires when in-sample fails.

| | NQ | ES |
|---|---|---|
| Long trades | 457 (TOP 165) | 453 (TOP 181) |
| Mean R, TOP vs other | +0.253 vs +0.118 | +0.215 vs +0.144 |
| Difference | +0.136 | +0.071 |
| One-sided p (bar 0.025) | 0.109 | 0.244 |
| Without best 3 TOP trades | diff +0.093, p 0.195 | diff +0.031, p 0.378 |
| Economic bar (sum of R, TOP-only vs all) | 41.8 vs 76.1: NOT met | 38.9 vs 78.0: NOT met |

Verdict: FAILS pass bar 1 on both instruments. Direction is positive on both and in both
halves, but small and not distinguishable from noise; filtering would roughly halve total R.
DROP per Section 9. No re-slicing, no threshold changes.

Disclosed choices made while coding (not in the plan): overnight days need >= 400 of the 509
one-minute bars (01:00-09:29 ET) to count; p-values use a normal approximation to Welch's t;
R is the existing test's volatility-normalised session-close R (no stop), not the live MES v2
stop/time-exit rule.
