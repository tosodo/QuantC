# Edge search: pre-registration of four candidates and a sizing rule

Status: TESTED 2026-10-21, none adopted (see
[EDGE_SEARCH_RESULTS.md](EDGE_SEARCH_RESULTS.md)). Locked before any of this
code was written or run. Nothing here
changes the live script, the live alert or the risk pause.

## Why

Phase 3 (`phase3_report.md`, run 2026-10-20): the live rules net +$4,086 over
5 years at 1 MES, about $820 a year, with a worst drawdown of $2,066 against
Lucid's $3,000 trail. Passing the $6,000 target takes a median of about 4
years in the random-order simulation, and the first payout needs more profit
after that. The risk is not ruin, it is that the edge is too small to pay for
the evaluation. A research pass (web only, 2026-10-20) found no fast-pass
method that works without a bigger edge or more size; its sources are mostly
firm blogs and unverified, so every idea below is a hypothesis, not a
finding. Idea sources are in the session notes: Gao, Han, Li, Zhou (JFE
2018), the Concretum "Noise Area" write-up, and prop-firm drawdown guides.

## Common rules

- Data: `data/continuous/ES.csv`, 1m, 2021-08-19 to 2026-08-14 (MES proxy,
  as in `live_rules_backtest.py`). Regular session 9:30-15:59 ET.
- Costs (base): $2.50 per round turn, 1 tick adverse slippage per exit,
  $5 per point. Stress case: $4.00 and 2 ticks.
- No look-ahead: every signal uses only bars closed before the entry bar.
  Entry is at the close of the signal bar (same convention as the live ORB).
- Out-of-sample slice: trades after 2025-02-14 (the cutoff already used by
  the NY and London tests). It is looked at once, with the rest.
- Multiple tests: four candidates are tested, so the p-value bar is
  0.05 / 4 = **0.0125**. No candidate is added or altered after this file
  is committed. Sensitivity grids are reported, never used to pick a setting.

## Candidates

**S1. Noise Area intraday momentum (long and short).**
For minute m of the session, sigma(m) = mean over the previous 14 sessions of
|close(m) / open(9:30) - 1|. Upper band = max(today's open, previous close)
x (1 + sigma(m)); lower band = min(open, previous close) x (1 - sigma(m)).
At each :00 and :30 bar close from 10:00 to 15:30, go long if the close is
above the upper band, short if below the lower band, if flat. Exit when a
1m close crosses session VWAP against the position, or at the 15:59 close.
Report the long-only side separately. One position at a time.

**S2. Last-half-hour momentum.**
Signal = sign of (close of 9:59 bar / previous session close - 1). Enter at
the close of the 15:29 bar in that direction, exit at the 15:59 close. No
stop. One trade a day.

**S3. ORB with an ATR stop.**
Live ORB entry and 90-minute underwater exit, unchanged. The 125-point stop
is replaced by 1.0 x ATR, where ATR is the mean of the previous 14 sessions'
regular-session high minus low. Compared with the live rules on the same
days.

**S4. Opening-range width gate (filter on the live ORB).**
Skip the entry when the 9:30-9:44 range is below the median of the previous
20 sessions' 9:30-9:44 ranges. Judged like the divergence rules: the removed
trades must lose money.

## Adoption criteria

S1, S2 and S3 are adopted for further work only if **all** hold at 1 MES under
base costs:

1. Net profit of at least $3,000 a year averaged over the sample.
2. Day-block bootstrap p < 0.0125 for mean daily net P&L > 0 (10,000 draws,
   5-day blocks).
3. Positive net in at least 4 of the 6 calendar years.
4. Positive net in the out-of-sample slice.
5. Worst drawdown (closed-trade equity) of at most $2,500.
6. Still net positive under the stress costs.

S4 is adopted only if the removed trades lose money in total, the
permutation p (10,000 draws) is below 0.0125, they lose in at least 4 of 6
years, and the Lucid pass rate with the filter is no lower than without it.

For every candidate also report: correlation of daily P&L with the live ORB
(a candidate that is the same trade in other clothes is not diversification),
the rolling and bootstrap Lucid pass rates, and trades per year.

## S5. Cushion-scaled size (simulation on the trade list, not a signal)

Applies to the live ORB trade list, or to any adopted candidate. Before each
trade: cushion = balance minus the trailing floor; size n = the largest
integer up to 3 such that n x (worst-case stop loss in dollars + $2.50) is
at most 50% of the cushion, and at least 1. Intraday adverse excursion is
scaled by n in the floor test. Compare with fixed 1 MES on: rolling and
bootstrap pass rate, median trades to pass, and the share of runs that
breach the floor. Adopted for further work only if the breach share rises by
no more than 5 percentage points (absolute) and the median trades to pass
falls by at least 25%. The Lucid lock level is taken as $100,100 and must be
checked against Lucid's own rulebook before this is relied on.

## Not in scope

- Gap rules and event-day filters: no rigorous source and VIX is not in the
  data. Possible later if one of the above works.
- Any live change. A pass leads to a proposal and a decision record.
- Moving to another prop firm. That depends on a candidate first clearing
  the criteria above.

## Implementation notes (added when the test was written; rules above unchanged)

- The S4 pass-rate check uses the bootstrap pass rate, because the rolling
  rate is undefined at base costs (no real-order start finishes), as in
  Phase 3. The rolling figure is still printed.
- S1 is reported both long+short (the adoption test) and long-only (for
  information). S3 multipliers 0.5/1.5/2.0 and S4 windows 10/40 are printed as
  sensitivity only. None of them can be adopted instead of the primary.
- The Lucid simulator takes one entry a day, so a multi-trade day is folded
  into one pseudo-trade: points summed, the extra round turns charged inside
  the points, and the worst intraday loss counted from the day's running
  result.
- S5 is run on the live ORB trade list. It is run on an adopted candidate
  only if one passes.
- Code: `edge_search_test.py`; tests: `ops/tests/test_edge_search.py`.
