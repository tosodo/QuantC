# Index 20d-quintile mean reversion — cost & data refresh (2026-08-19)

## Verdict: `promising_but_unproven` (unchanged)

Real Tradovate costs turned out to be **immaterial** to this test, not
damaging — the opposite of what the 3.0bps placeholder implied. Nothing in
this refresh moves the needle. Out-of-sample, the three instruments still
agree on direction 6-for-6 (~1/64 odds under pure noise), but only NQ's top
quintile clears the pre-registered significance bar (p=0.0142, n=18) — same
as before. This is still not enough to trade; it is enough to keep watching.

**The 2-3 numbers that drive this:**
- Real round-turn cost (Tradovate Free plan, worst realistic full-size
  case) shifts in-sample NQ non-overlapping mean R by **-0.002R to -0.003R**
  (widens to about -0.007R to -0.010R if trading the MNQ micro leg instead —
  still small). Compare to the original 3bps placeholder's -0.006R to
  -0.008R shift on the same cells: broadly similar magnitude in this
  instance, but that's closer to coincidence than validation — the
  placeholder ignored 25 years of price-level change and was not a
  trustworthy stand-in (see below).
- Out-of-sample NQ top quintile: mean R +0.578→+0.578 (zero-cost → real
  cost, non-overlapping), t=-2.733→-2.733 to 4 decimals, p=0.0142 either way.
  Real costs did not change any OOS verdict cell.
- Out-of-sample directional agreement: **6 of 6** cells (bottom-long,
  top-short × NQ, ES, YM) — unchanged from the original run.

## What changed and why

**1. Cost model replaced.** The original 3.0bps flat placeholder is replaced
by Tradovate's real published round-turn cost, applied **per trade using
that trade's own entry price** (not one flat number for 25 years of data).

Why per-trade: Tradovate's commission/exchange/clearing fees are fixed in
**index points**, not a percentage. NQ ranged from 810 to 30,713 points over
this sample — a flat percentage cost is off by ~38x between the cheapest and
most expensive years. A single "current-price bps" number would have
silently understated cost in 2003-2010 and been roughly right for
2023-2026; a single "average-price bps" number would overstate today's real
cost. Neither is defensible for a 25-year sample, so the script now converts
`cost_points / entry_price` trade-by-trade (see `REAL_COST_POINTS` and
`build_signals()` in `screen_mean_reversion.py`).

**Source (MEASURED):** Tradovate's own "All-In Rates" PDF, fetched directly
from `https://www.tradovate.com/TradovateAllInRates120625.pdf` (linked from
`tradovate.com/pricing/`; footer dated NFA fee "Updated 12/5/25"). The PDF's
"All In Rate" column is **per side**; round-turn = 2×. Cross-checked against
the two figures already verified elsewhere in this project — MNQ Free
$1.90=0.95pts and NQ Free 0.288pts both reproduce exactly from the PDF's raw
table, confirming the read is correct.

| Instrument | Point value | Free plan RT | Monthly plan RT | Lifetime plan RT |
|---|---|---|---|---|
| NQ (full-size) | $20/pt | 0.288 pts | 0.258 pts | 0.218 pts |
| ES (full-size) | $50/pt | 0.1152 pts | 0.1032 pts | 0.0872 pts |
| YM (full-size) | $5/pt | 1.152 pts | 1.032 pts | 0.872 pts |
| MNQ (micro, alt. Nasdaq leg) | $2/pt | 0.95 pts | 0.85 pts | 0.65 pts |

ES and YM were **NOT MEASURED** before this refresh; they now are — Tradovate
charges the identical $ commission schedule across ES/NQ/YM full-size
contracts, so only the point-value conversion differs, and that conversion
is arithmetic, not a new lookup.

**Why the placeholder's "30-90% higher" framing didn't hold here:** that
comparison originates from a different research context in this project.
Measured directly against 2020-2026 price levels (where NQ trades ~15,000-
30,000), a sub-1-point round-turn cost is a few thousandths of a percent of
notional — far smaller than 3bps, not larger. Earlier in the sample (NQ near
1,000-3,000 in the 2000s), the same point-cost was a larger fraction, but
even then it stayed under ~3bps. The corrected, per-trade cost model settles
this: real costs cost this signal almost nothing, at any plan tier, in any
year of the sample.

**2. Out-of-sample extension: not possible right now — already at the data
frontier.** `fetch_data.py` was re-run as part of this refresh; both NQ and
ES data now run to 2026-08-19 (today), YM to the same date. There is no more
recent Yahoo data to append — this fetch already reaches the present. The
16-18-trades-per-cell OOS sample is a structural consequence of the design
(20-trading-day forward window, 20-day non-overlap stride, applied to a
~6.5-year OOS slice from 2020-01-24 onward), not a fetch shortfall: at
~12-13 non-overlapping windows per year, the OOS cell count grows by roughly
one trade every four weeks going forward, regardless of how the data is
sourced. The only way to legitimately thicken this sample is to let more
calendar time pass and re-look once, later — not to re-fetch today.

## Results table (non-overlapping, the trustworthy numbers)

Overlapping-window p-values are still reported in the script's console
output for transparency but are known to be optimistic (autocorrelated
observations) — do not use them to judge significance.

**Zero-cost vs. real cost (Free plan, worst realistic case) — in-sample:**

| Instrument | Side | n | Zero-cost mean R | Zero-cost p | Real-cost mean R | Real-cost p |
|---|---|---|---|---|---|---|
| NQ | bottom | 41 | +0.395 | 0.0111* | +0.393 | 0.0115* |
| NQ | top | 40 | -0.435 | 0.0071* | -0.438 | 0.0068* |
| ES | bottom | 41 | +0.431 | 0.0010* | +0.430 | 0.0010* |
| ES | top | 40 | -0.454 | 0.0015* | -0.456 | 0.0014* |
| YM | bottom | 42 | +0.365 | 0.0426 | +0.363 | 0.0436 |
| YM | top | 38 | -0.428 | 0.0373 | -0.431 | 0.0360 |

\* clears the pre-registered Bonferroni bar (p < 0.025)

**Zero-cost vs. real cost (Free plan) — out-of-sample (looked once):**

| Instrument | Side | n | Zero-cost mean R | Zero-cost p | Real-cost mean R | Real-cost p |
|---|---|---|---|---|---|---|
| NQ | bottom | 18 | +0.298 | 0.2873 | +0.297 | 0.2876 |
| NQ | top | 18 | -0.578 | 0.0142* | -0.578 | 0.0142* |
| ES | bottom | 18 | +0.303 | 0.1553 | +0.302 | 0.1559 |
| ES | top | 17 | -0.272 | 0.3428 | -0.272 | 0.3418 |
| YM | bottom | 16 | +0.261 | 0.3427 | +0.261 | 0.3438 |
| YM | top | 17 | -0.149 | 0.5386 | -0.150 | 0.5364 |

\* clears the pre-registered Bonferroni bar (p < 0.025)

**Directional agreement, out-of-sample, non-overlapping:** bottom-long
signs {NQ +, ES +, YM +} → AGREE. top-short signs {NQ -, ES -, YM -} →
AGREE. 6 of 6, unchanged by the cost refresh (cost does not flip signs at
this magnitude).

Lifetime-plan and MNQ-micro-leg cost tiers were also run (see commands
below) — differences from the Free-plan numbers above are in the 3rd-4th
decimal of mean R, i.e. not economically distinguishable from zero-cost at
this sample size. Not tabulated separately to keep this report tight.

## MEASURED vs. NOT MEASURED

**MEASURED**
- NQ, ES, YM, MNQ real Tradovate round-turn costs (Free/Monthly/Lifetime),
  sourced from Tradovate's own All-In Rates PDF as of this refresh.
- All in-sample and out-of-sample per-trade mean R, t-stat, p-value figures
  above — computed from the same script, same signal logic, same
  entry-at-next-open fix as the original run.
- Data coverage: NQ/ES to 2026-08-19, YM to 2026-08-19 (6311/6311/6134
  daily bars respectively) — confirmed by direct inspection of the fetched
  CSVs, not assumed.

**NOT MEASURED**
- Slippage / spread-crossing cost beyond Tradovate's quoted all-in rate
  (fill quality on market vs. resting orders). Real cost could be somewhat
  higher than shown.
- Continuous front-month futures proxy (Yahoo NQ=F/ES=F/YM=F), not
  back-adjusted for roll gaps — same limitation as the original run,
  unchanged by this refresh.
- Anything about instruments other than NQ/ES/YM/MNQ (e.g. MES, MYM), or
  costs beyond Tradovate (this test does not know what broker will actually
  be used to trade it).

## How to reproduce

```
cd /Users/osodo.t/QuantC/research/index_mean_reversion
python3 fetch_data.py                                          # re-pull data (already run 2026-08-19)
python3 screen_mean_reversion.py --sample in  --real-cost-tier free       # in-sample, worst-case real cost
python3 screen_mean_reversion.py --sample in  --real-cost-tier lifetime   # in-sample, best-case real cost
python3 screen_mean_reversion.py --sample out --real-cost-tier free       # OOS, worst-case real cost (look once)
python3 screen_mean_reversion.py --sample in  --real-cost-tier free --use-micro-nq   # if trading MNQ instead of NQ
```

## Bottom line for a non-technical read

The idea still shows the same pattern it showed before: after an unusually
large 4-week move, index futures tend to drift back the other way over the
following 4 weeks, and this held up (directionally) in fresh data the
strategy hadn't seen yet, 6 times out of 6 tested combinations. Real trading
costs, now actually looked up instead of guessed, turn out to be too small
to matter either way — they don't kill the idea, but they also don't rescue
it. The problem is still the same one as before: not enough out-of-sample
trades yet to call this proven (16-18 per cell), and only one of six cells
clears the strict statistical bar on its own. Verdict stands at
`promising_but_unproven` — worth continuing to track, not worth building or
trading yet. More out-of-sample evidence will accumulate at roughly one
trade per side every four weeks; there is nothing to fetch today that
would speed that up.
