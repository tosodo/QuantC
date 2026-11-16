# ORB cross-instrument and out-of-period replication: pre-registration

Written 2026-10-20, committed **before any replication data is pulled or any replication
code is written or run**. Nothing changes in the live trading rules: no alert is touched,
no candidate is adopted, no PR is made. Lucid price, trail lock, funded payout cap and
cycle length stay **UNVERIFIED** (FIRM_RULES_SURVEY.md) and are used only as the existing
rule sets define them.

## Why

The live ORB-long rules earn about $4 a trade (sd about $84) over 5 years on ES, a t-stat of
about 1.5. `edge_calculator.py plan` shows a 60% Lucid pass rate needs about $2.1 a trade
and an edge that size takes decades to confirm from one instrument. The cheapest honest
test is data the rules have never seen. This study asks one question: **does the live
rule, unchanged, make money on index futures outside the 2021-2026 ES sample?**

## What is not fresh (disclosed now)

- ES and NQ over 2021-08-19 to 2026-08-18 were already examined (RESULTS.md: long side,
  R-multiple entry test; NQ and ES significant, YM not). That period is **P0**. P0 results
  are reported for information and **never count toward confirmation**.
- ES, NQ and YM index returns are highly correlated, so three instruments are not three
  independent samples. Inference clusters by day (below).
- No YM data exists in `data/continuous/` (build_continuous.py makes ES and NQ only).

## Data (user action needed; nothing is run until it exists)

- **P1 (confirmation sample):** 2010-06-06 to 2021-08-18, Databento GLBX.MDP3, 1-minute
  OHLCV, parent symbols ES, NQ and YM, volume-roll continuous series built exactly as
  `build_continuous.py` does (YM added, no other change). Check the Databento cost estimate
  before pulling; if the full range is too costly, pull the **most recent 6 years of P1**
  (2015-08 to 2021-08) first and amend this file with the dated range before running.
- **P2 (forward):** trading days after this commit. ES is the live alert. NQ and YM are
  shadow-replayed only, never traded. Judged later under a separate dated amendment.

## Rules replicated (frozen; no tuning, no variants)

Live ORB-long as in `ops/shadow_day.replay_day`: range 9:30-9:44 ET (15 bars); entry on the
first 1-minute close above the range high from 9:45; one attempt a day; long only; exit on
the 90-minute underwater rule or the 15:59 bar; 1 micro contract. Short side, partial exits,
other windows and other stops are **not** tested.

The only adaptation: the 125-point ES stop is a point count that means 2.5% in 2021-26 but
10% in 2010, so on every instrument and period **stop = 2.5% of the range-end close
(9:44 close), rounded to a tick**. Parity check: the same code with the fixed 125-point
stop on ES in P0 must reproduce the live replay's trade list; reported, not a hypothesis.

Costs per micro contract: $2.50 round turn plus 1 tick adverse on the exit (tick values
MES $1.25, MNQ $0.50, MYM $0.50). Stops fill exact plus slippage, as in the live backtest.

## Hypotheses and decision rules (set now)

Unit: net return per trade as a fraction of entry price (bps), so instruments pool. Daily
value = mean of that day's available instrument trades. **H1 (the only primary test):** the
mean daily value over P1 is above zero.

- Inference: one-sided, day-block bootstrap (blocks of 5 trading days, 5,000 resamples).
  One pre-specified test of an existing rule, not a search, so the bar is one-sided 5%
  (t of about 1.65), not t = 3. Reported with the Deflated Sharpe at 1 trial and again at 4
  (H1 plus three per-instrument reads).
- **CONFIRMED** only if: (1) H1 one-sided p < 0.05; (2) at least 2 of 3 instruments have a
  positive P1 mean; (3) the pooled P1 mean is at least half the pooled P0 (ES, NQ) mean in
  bps, so a collapse counts as failure; (4) at least 1,500 pooled trades.
- **FALSIFIED** if the pooled P1 mean is zero or negative, or if 2 or 3 instruments are
  negative.
- Anything else is **INCONCLUSIVE** and is reported as such, not rounded up.

Power, stated honestly: if the true edge equals the ES P0 figure ($4.1, sd $84) a single
instrument with about 2,200 P1 trades reaches t of about 2.3, about 74% power at one-sided
5%. The P0 figure is probably inflated by selection, so true power is lower. An
INCONCLUSIVE result is a real possibility and counts as no evidence of an edge.

## What each result changes

- CONFIRMED: the live rules stay; a forward-paper period on NQ and YM is the next step; a
  separate pre-registration decides sizing. It does not shorten the time to a Lucid pass.
- FALSIFIED: stop paying evaluation fees on ORB-long alone; the next study targets
  independent edges (breadth), not variants of this rule.
- INCONCLUSIVE: no change; report the interval.

## Multiplicity and limits

One primary test; three per-instrument reads are secondary. Earlier looks at the same rule
family (RESULTS.md, EDGE_SEARCH_RESULTS.md, LUCID_WF_HYPOTHESIS.md) were all on P0, so P1 is
not contaminated by them. Limits: 2010-2021 has different volatility and tick behaviour;
volume-roll series are not back-adjusted; fills are modelled, not measured; YM liquidity at
the open was thinner in 2010; Databento ES versus TradingView MES is not compared here.
