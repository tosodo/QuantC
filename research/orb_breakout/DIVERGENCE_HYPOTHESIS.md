# RSI divergence zones as an ORB filter: pre-registration

Status: TESTED 2026-10-20, neither rule adopted (see
[DIVERGENCE_RESULTS.md](DIVERGENCE_RESULTS.md)). This plan was locked
before `divergence_filter_test.py` was run on the history. Idea source: the ChartPrime "RSI Momentum Divergence Zones"
indicator (a video walkthrough, no published statistics).

## Question

The live ORB (orb_long_mes_v2.pine) buys the first 1m close above the
9:30-9:44 ET range. Does it do worse when that entry runs straight into a
recent, still-unbroken **bearish divergence zone** just overhead? And on
down-break-first days, does a **bullish divergence** during the dip pick out
the days worth trading?

## Zone construction (fixed)

- **Bars:** 5-minute bars built from the full Globex 1m stream (ES as the
  MES proxy, the same data as `live_rules_backtest.py`), so zones from the
  overnight session and earlier days exist at 9:45.
- **Oscillator:** Wilder RSI(14) on 5m closes. The video's "momentum RSI" is
  not specified well enough to copy; plain RSI is the honest stand-in.
- **Pivots:** RSI pivot high/low with 5 bars left and 5 right. A pivot at
  bar *i* is only **known at the close of bar i+5**. Nothing may use it
  earlier.
- **Bearish divergence:** RSI pivot high at *i*, previous RSI pivot high at
  *p* with 5 <= i-p <= 60 bars, RSI lower (rsi[i] < rsi[p]) while price high
  is higher (high[i] > high[p]). Zone = bar *i*, from max(open, close) up to
  high.
- **Bullish divergence:** the mirror image on RSI pivot lows. Zone = bar
  *i*, from low up to min(open, close).
- **Invalidation:** a bearish zone is broken by the first later 5m close
  above its top (bullish: close below its bottom). Only the last 10 zones of
  each kind are kept, as the indicator displays.

## Rules under test

- **A (primary):** skip the ORB entry if, at the entry decision (the close
  of the 1m signal bar), an active bearish zone overlaps
  [entry, entry + 10 pts], i.e. top >= entry and bottom <= entry + 10.
- **B (secondary):** on down-break-first days, take the entry only if a
  bullish divergence was confirmed between 9:30 ET and the entry decision.
  Clean days are unaffected.

## How it is judged (fixed)

Base costs as Phase 3: $2.50 a round turn, 1 tick adverse slippage on exit.

Rule A is adopted for further work only if **all** hold:

1. The removed trades lose money in total.
2. Permutation test: removing that many trades at random gives a total at
   least as bad as the removed set's in fewer than 5% of 10,000 draws
   (p < 0.05).
3. The removed trades lose money in at least 4 of the calendar years.
4. The rolling Lucid pass rate with the filter is no lower than without it.

Rule B is judged the same way on the down-break-first trades only.

The sensitivity grid (RSI 9/14, pivots 3/5, distance 5/10/20 pts) is
reported in full to show whether the result is stable. It is **not** used
to pick a better setting. If only some other cell passes, the verdict is
"not adopted".

## Not in scope

- The video's own entries (bounce off a zone, stops and targets at zones).
  That is a different, discretionary strategy.
- Any live change. A pass here leads to a proposal and a decision record,
  not to an edit of the live script.
