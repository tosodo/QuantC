# VWAP Fade — Correlation test against the live ORB strategy

Run: `orb_vwap_correlation.py` (2026-09-11), 1,289 sessions of ES 1-minute data
(2021-08-19 → 2026-08-14), the same dataset every file in
`research/orb_breakout/` uses. Both strategies priced on MES ($5/pt) with the
same Tradovate free-tier cost model and 1 tick of adverse slippage on every
exit, so the two series are directly comparable in dollars.

## Why this test was run

`research/orb_breakout/RESULTS.md` §2.10 established the binding constraint on
the whole account: the live ORB mechanism produces +$9.10/trade × ~133
trades/year = **~$1,208/year**, and no contract-sizing choice changes that
(size multiplies the edge and the risk in lockstep). Only two levers raise
return *without* paying for it in pass-probability:

- **(a) more trades per year that are genuinely uncorrelated with ORB**
- **(b) higher expectancy per trade at the same risk**

§2.8 already killed the obvious candidate for (a): running the same ORB logic
on MNQ measured **r = +0.963** against MES — the same bet twice, not
diversification. `vwap_fade_ghost_DRAFT.pine` was written as the deliberate
alternative: a mean-reversion fade, a different *edge type*, intended to do
well on exactly the choppy days that hurt a momentum breakout.

This test asks §2.8's question of that draft.

## 1. The correlation result — the fade PASSES, decisively (MEASURED)

| | Measured |
|---|---|
| ORB trading days | 662 |
| Fade trading days | 1,063 (2,286 trades, up to 3/day) |
| Days both fired | 542 |
| **Fade-only days (ORB never trades)** | **521** |
| **Correlation of same-day $ P&L (n=542)** | **r = −0.161** |
| **Shared variance** | **2.6%** |
| Both won or both lost | 46.1% |
| One won, one lost | **53.9%** |

Against MNQ's +0.963, this is a different universe. **r = −0.161 is not merely
uncorrelated — it is very slightly *negatively* correlated.** Only 2.6% of the
movement is shared, and more often than not (53.9%) one strategy wins on a day
the other loses. That is the diversification profile §2.8 looked for and did
not find.

It also opens **521 additional trading days a year-for-year** that ORB never
participates in at all — real incremental opportunity, not a re-slicing of the
same days.

**Finding: the diversification slot this account needs is real, and a
mean-reversion fade genuinely fills its shape.** The concept is validated.

## 2. The fade itself — FAILS, and not narrowly (MEASURED, in-sample)

| | Measured |
|---|---|
| Trades | 2,286 (447/year) |
| Win rate | **25.2%** |
| Average winner | +$62.88 |
| Average loser | −$26.63 |
| Reward : risk | 2.36 : 1 |
| **Break-even win rate** | **29.8%** |
| **Expectancy per trade** | **−$4.04** |
| Total over 5.1 years | **−$9,237** (−$1,806/year) |
| Long leg | n=1,115, WR 25.8%, −$4.26 |
| Short leg | n=1,171, WR 24.7%, −$3.83 |
| Exit mix | **stop 1,796 (78.6%)**, vwap_revert 374 (16.4%), session_close 116 |

The fade loses money, on both legs independently, and it does so **in-sample,
on its own hand-picked parameters, on its first look at the data.** A strategy
that cannot look good under those maximally favourable conditions is not a
marginal call.

**The mechanism diagnosis is in the exit mix: 78.6% of trades were stopped out
and only 16.4% ever reverted to VWAP.** The core thesis — that price stretched
2 SD from VWAP on fading volume tends to snap back — does not hold at these
thresholds. Price mostly kept going. It is 4.6 points of win rate short of
break-even.

## 3. Portfolio effect (MEASURED)

Daily dollar P&L across all 1,289 sessions:

| | sd / day | mean / day |
|---|---|---|
| ORB alone | $105.75 | **+$4.67** |
| Fade alone | $68.11 | −$7.17 |
| ORB + Fade | $119.77 | **−$2.49** |

Combining them turns a profitable account into a losing one. The volatility
also rises (+13.3%) rather than falling — but note *why*: it rises by **less**
than the $125.79 that two independent series would have produced. The
diversification is genuinely working; it is simply being swamped by the fade's
negative expectancy.

## Verdict

**reject_early — for this implementation. The slot stays open.**

Two separate conclusions that must not be collapsed into one:

1. **The strategic hypothesis is CONFIRMED.** A mean-reversion fade is a
   genuinely independent bet from ORB (r = −0.161 vs MNQ's +0.963), and it
   trades on 521 days ORB ignores. This is the only lever measured so far that
   could raise the account's ~$1,208/year without spending pass-probability to
   do it.
2. **This particular rule set is not the thing that fills it.** −$4.04/trade,
   78.6% stopped out, losing in-sample on its own chosen parameters.

**Because r is slightly negative, the bar for this slot is unusually low: a
fade would be worth adding at merely break-even**, since at r = −0.16 it would
reduce account volatility for free. It does not need to be as good as ORB. It
needs to be **non-negative**, and it currently is not — by $4.04 a trade, or
about $1,806 a year.

## DO NOT tune these parameters on this data

The obvious next move — widen the 3 SD stop, loosen RSI 30/70, drop the short
leg — is exactly the trap this project's pre-registration discipline exists to
prevent. The 4.6-point gap to break-even is small enough that parameter search
on 5 years of already-inspected data would almost certainly close it, and the
result would be worthless.

If this line is pursued, it needs the same treatment §1 of
`research/orb_breakout/RESULTS.md` gave ORB: a **pre-registered** hypothesis
locked before the data is re-inspected, an in-sample/out-of-sample split, a
Bonferroni-corrected significance threshold, and replication across
instruments. Anything less is curve-fitting with extra steps.

## NOT MEASURED

- **This is in-sample and unregistered by construction.** §2's figures are not
  evidence of an edge in either direction beyond "it does not work as
  specified"; a negative in-sample result is, however, much stronger evidence
  than a positive one would have been.
- RSI(14) and the 5-bar volume average are computed on the RTH-only series
  (09:30–16:00 ET), matching an RTH TradingView chart. An ETH chart seeds both
  differently and would shift marginal signals.
- Stops assumed to fill at the stop price plus 1 tick adverse. A gap through
  the stop fills worse; not modelled.
- **No survivability/ruin simulation was run.** This measures whether the two
  are the same bet, not what running both would do to the pass rate — the same
  boundary §2.8 drew.
- The fade was tested on ES/MES only. `vwap_fade_ghost_DRAFT.pine` notes the
  logic is instrument-agnostic and that the instrument choice was never made.
