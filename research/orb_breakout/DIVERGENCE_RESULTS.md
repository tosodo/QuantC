# RSI divergence zones as an ORB filter: results

Pre-registration: [DIVERGENCE_HYPOTHESIS.md](DIVERGENCE_HYPOTHESIS.md),
locked before the test was run on the history. Run 2026-10-20 by the user
on the full 5-year file (`python3 divergence_filter_test.py`); the output
below is copied verbatim from that run. Nothing here is estimated.

**Verdict: neither rule is adopted.** The trades each rule would skip made
money (A +$520, B +$105), the permutation p-values are about 0.45, and the
skipped trades lost money in only 2 of 6 years. Every cell of the
sensitivity grid agrees: the skipped trades are profitable. The live rules
are unchanged.

**Side finding (about the live rules, not the filter):** over the full
history at 1 MES the live rules net +$4,086 on 996 trades. No start point
in the real sequence ever reaches the Lucid target (+$6,000) or the $3,000
trailing floor, which is why the rolling pass rate reads "nan (0)". The
iid bootstrap passes 55% of the time with a median of 782 trades. To be
examined in the Phase 3 report (`live_rules_backtest.py`).

---

## RSI divergence filter on the live ORB rules

Data: `data/continuous/ES.csv`, 2021-08-19 to 2026-08-14, 996 trades. Rules and pass criteria: DIVERGENCE_HYPOTHESIS.md. Costs $2.50/RT, 1 tick exit slippage.

### Primary spec (RSI 14, pivots 5/5, 10 pts)

| set | n | win % | avg $ | total $ | PF |
|---|---|---|---|---|---|
| baseline (live rules) | 996 | 29.1 | 4.10 | 4086 | 1.11 |
| A: kept | 820 | 28.9 | 4.35 | 3566 | 1.11 |
| A: removed | 176 | 30.1 | 2.95 | 520 | 1.08 |
| B: kept | 759 | 29.4 | 5.25 | 3981 | 1.13 |
| B: removed (dbf, no bull dip) | 237 | 28.3 | 0.44 | 105 | 1.01 |

### Pre-registered checks

| rule | removed | removed total $ | perm p | losing years | 1-3 pass |
|---|---|---|---|---|---|
| A | 176 | 520 | 0.4577 | 2/6 | no |
| B | 237 | 105 | 0.4473 | 2/6 | no |

Removed P&L by year: A 2021 649, 2022 49, 2023 348, 2024 738, 2025 -1048, 2026 -215; B 2021 191, 2022 -1409, 2023 381, 2024 398, 2025 608, 2026 -64.

### Check 4: Lucid pass rate

| set | rolling pass % (starts) | bootstrap pass % | median trades |
|---|---|---|---|
| baseline | nan (0) | 55.2 | 782 |
| A | nan (0) | 57.5 | 737 |
| B | nan (0) | 61.8 | 667 |

**Verdict:** rule A is not adopted; rule B is not adopted.

### Sensitivity grid (rule A; reported, not used to choose)

| RSI | pivots | dist | removed | removed total $ | perm p | losing years |
|---|---|---|---|---|---|---|
| 9 | 3 | 5 | 122 | 1562 | 0.8046 | 2/6 |
| 9 | 3 | 10 | 187 | 1862 | 0.7666 | 2/6 |
| 9 | 3 | 20 | 278 | 3935 | 0.9463 | 1/6 |
| 9 | 5 | 5 | 133 | 1680 | 0.8074 | 1/6 |
| 9 | 5 | 10 | 201 | 710 | 0.4813 | 1/6 |
| 9 | 5 | 20 | 292 | 1840 | 0.6358 | 2/6 |
| 14 | 3 | 5 | 107 | 2039 | 0.9071 | 0/6 |
| 14 | 3 | 10 | 166 | 2224 | 0.8601 | 1/6 |
| 14 | 3 | 20 | 251 | 3015 | 0.8798 | 1/6 |
| 14 | 5 | 5 | 116 | 1201 | 0.7343 | 1/6 |
| 14 | 5 | 10 | 176 | 520 | 0.4577 | 2/6 |
| 14 | 5 | 20 | 270 | 940 | 0.4665 | 2/6 |

### Caveats

- ES bars as the MES proxy; plain RSI stands in for the indicator's momentum RSI.
- Zones use completed 5m bars only, so a divergence confirmed inside the current 5m bar is not seen until that bar closes.
