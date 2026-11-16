# Edge search results: S1-S5

Pre-registration: [EDGE_SEARCH_HYPOTHESIS.md](EDGE_SEARCH_HYPOTHESIS.md),
locked before `edge_search_test.py` was written. Run 2026-10-21 by the user on
the full 5-year ES file; the report below is the script's output, copied
verbatim. Nothing here is estimated.

**Verdict: none of S1-S5 is adopted.** The live rules are unchanged.

- **S1 Noise Area** is the only candidate with signs of life, and it is weak.
  Long+short nets $1,451 a year (bar: $3,000), block p 0.019 (bar: 0.0125),
  out-of-sample -$378, worst drawdown $3,038 (bar: $2,500). Long-only, a
  variant reported for information and not the adoption test, nets $1,076 a
  year with p 0.011, out-of-sample +$569 and drawdown $1,702: it fails only
  the $3,000 bar. Both variants lose money in 2026, and 2022 supplies 61% of the
  long+short 5-year profit ($4,430 of $7,250): the edge looks like a trending-market effect. Its daily P&L has
  correlation 0.21 (long+short) and 0.38 (long-only) with the live ORB.
- **S2 last half hour** loses in every year. Its gross is about -$240 a year
  before costs; costs are about $930 a year at 248 trades, so trading the
  opposite way would also lose. There is nothing to invert.
- **S3 ATR stop** is the same trade as the live ORB (correlation 1.00): $4,214
  against $3,920 on the same days, p 0.11. No meaningful gain.
- **S4 width gate** is rejected firmly. The 500 narrow-range days it removes
  made +$2,830 of the $3,920 total, and the bootstrap pass rate fell from 55%
  to 36%. Narrow opening ranges are the good days for this strategy. (Trading
  only those days would be a new hypothesis chosen after seeing this result;
  it would need its own pre-registration and the same multiple-testing bar.)
- **S5 cushion-scaled size** cuts the median trades to pass from 771 to 412 but
  raises the bootstrap breach rate from 42.8% to 51.1% and lowers the pass
  rate from 55.4% to 48.7%. It fails the breach criterion.

**Correction to the Phase 3 reading.** In the real historical order the
live rules never came near the $3,000 trail (worst drawdown $2,066). That is
one path. In random-order resampling, 42.8% of runs at 1 MES hit the trailing
floor before the target (55.4% pass, the rest still open). The Phase 3 note
that the other 44% "don't pass within 2,000 trades" was wrong: most of them
breach. At 1 MES the evaluation is closer to a coin flip with a slow clock
than to a safe grind.

Counting the median "trades to pass" for S1: the simulator takes one entry per
trading day, so its trades are days with a trade (S1 long-only has about 117
a year, so 441 such days is about 3.8 years, no faster than the live ORB).

---

## Report (verbatim)

# Edge search: S1-S5 on the live ORB history

Data: `data/continuous/ES.csv`, 2021-08-19 to 2026-08-18, 1289 sessions. Rules and bars: EDGE_SEARCH_HYPOTHESIS.md. Base costs $2.50/RT + 1 tick; stress $4.00 + 2 ticks. p bar 0.0125.

## S1-S3 against the six adoption criteria

| candidate | trades/yr | win % | annual $ | block p | + years | OOS $ | max DD $ | stress $ | corr live | pass rolling (n) / boot / median |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Noise Area (long+short) | 252 | 36.0 | 1,451 | 0.0188 | 5/6 | -378 | 3,038 | 3,782 | 0.21 | 42.8 (355) / 89.5 / 541 |
| S1 Noise Area (long only) | 117 | 40.6 | 1,076 | 0.0106 | 5/6 | 569 | 1,702 | 3,764 | 0.38 | 100.0 (39) / 99.7 / 441 |
| S2 last half hour | 248 | 46.1 | -1,170 | 0.9933 | 0/6 | -1,224 | 6,576 | -9,248 | -0.06 | 0.0 (781) / 0.0 / nan |
| S3 ORB, 1.0 x ATR stop | 197 | 29.0 | 843 | 0.1125 | 4/6 | -209 | 1,713 | 1,511 | 1.00 | nan (0) / 58.6 / 782 |

Criteria met (annual >= $3,000, p < bar, >= 4 positive years, OOS > 0, DD <= $2,500, stress > 0):

| candidate | annual | p | years | OOS | DD | stress | adopted |
|---|---|---|---|---|---|---|---|
| S1 Noise Area (long+short) | NO | NO | yes | NO | NO | yes | no |
| S1 Noise Area (long only) | NO | yes | yes | yes | yes | yes | no |
| S2 last half hour | NO | NO | NO | NO | NO | NO | no |
| S3 ORB, 1.0 x ATR stop | NO | NO | yes | NO | yes | yes | no |

Net by year (base costs):

- S1 Noise Area (long+short): 2021 551, 2022 4,430, 2023 1,030, 2024 1,555, 2025 1,176, 2026 -1,492
- S1 Noise Area (long only): 2021 282, 2022 2,459, 2023 1,374, 2024 652, 2025 924, 2026 -316
- S2 last half hour: 2021 -1,430, 2022 -2,096, 2023 -24, 2024 -1,002, 2025 -996, 2026 -295
- S3 ORB, 1.0 x ATR stop: 2021 884, 2022 1,702, 2023 501, 2024 1,436, 2025 -71, 2026 -237

Live ORB on the same 1274 days (S3 comparison): 983 trades, $3,920; S3: 983 trades, $4,214.

S3 multiplier sensitivity (reported, not used to choose):

| ATR multiple | trades | net $ | win % |
|---|---|---|---|
| 0.5 | 983 | 5,522 | 28.9 |
| 1.0 | 983 | 4,214 | 29.0 |
| 1.5 | 983 | 3,846 | 29.0 |
| 2.0 | 983 | 3,920 | 29.0 |

## S4 opening-range width gate on the live ORB

| window | removed | removed $ | perm p | losing years | pass boot % (with / without) | adopted |
|---|---|---|---|---|---|---|
| 20 (primary) | 500 | 2,830 | 0.6605 | 1/6 | 36.3 / 55.1 | no |
| 10 | 516 | 2,622 | 0.6248 | 2/6 | 38.5 / 53.8 | no |
| 40 | 500 | 1,428 | 0.3635 | 2/6 | 59.5 / 56.3 | no |

The pass-rate check uses the bootstrap column because the rolling rate is undefined at base costs (no real-order start finishes), as in Phase 3.

## S5 cushion-scaled size on the live ORB trades

| sizing | rolling pass % | rolling breach % (n) | bootstrap pass % | bootstrap breach % | median trades to pass |
|---|---|---|---|---|---|
| fixed 1 MES | nan | nan (0) | 55.4 | 42.8 | 771 |
| cushion-scaled (max 3) | nan | nan (0) | 48.7 | 51.1 | 412 |

S5 adopted for further work: **no** (breach up by at most 5 points and median trades to pass down by 25% or more).

## Verdict

- S1 Noise Area (long+short): not adopted
- S1 Noise Area (long only): not adopted
- S2 last half hour: not adopted
- S3 ORB, 1.0 x ATR stop: not adopted

## Caveats

- ES bars as the MES proxy. VWAP uses the typical price (H+L+C)/3 weighted by 1m volume.
- The Lucid simulator takes one entry a day, so multi-trade days are folded into one pseudo-trade with the extra round turns charged inside its points.
- The stop fills exactly at its price plus slippage. Gaps and partial fills are not modelled.
- Four candidates were tested, so the p bar is 0.0125; one lucky pass among many is expected.
