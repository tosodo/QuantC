# Index 20d-quintile mean reversion — deep-history cash-index re-test (2026-08-19)

## Verdict: `needs_testing` (upgraded from `promising_but_unproven`)

This is a genuine re-test of the exact same pre-registered rule from
`screen_mean_reversion.py` — same mechanism, same 20d/504d/20d parameters,
same R-multiple definition, same entry-at-next-open timing, same
non-overlapping discipline, same Bonferroni k=2 threshold (0.025) — run on
39–57 years of S&P 500 / Nasdaq Composite / Russell 2000 **cash-index**
history instead of the original ~24–25 years of NQ/ES/YM **futures**
history. Nothing about the rule was changed; only the data got longer and
cleaner (no futures-roll gaps).

The result is stronger than the original futures test, on both counts that
matter: **more out-of-sample cells clear the significance bar** (3 of 6 vs.
1 of 6 originally), and **directional sign agreement is perfect** (12 of 12
cells, in-sample and out-of-sample combined, across three different broad
market indices). That is enough new evidence to move this past "just keep
watching" into "worth actually building a realistic test of" — but it is
**not** enough to call it proven or approved: half the cells still miss the
pre-registered bar, the indices tested are not directly tradable, and the
three indices are highly correlated with each other so this is not really
three independent replications.

## Data used

Fetched via `fetch_data_cash.py` (period1=0, verified true daily bars, not
the range=max monthly-demotion trap documented in `fetch_data.py`):

| Symbol | Index | First bar | Last bar | Bar count | Median daily gap (last 1y) |
|---|---|---|---|---|---|
| ^GSPC | S&P 500 cash | 1970-01-02 | 2026-08-18 | 14,278 | 1 calendar day |
| ^IXIC | Nasdaq Composite cash | 1971-02-05 | 2026-08-18 | 14,000 | 1 calendar day |
| ^RUT | Russell 2000 cash | 1987-09-10 | 2026-08-18 | 9,808 | 1 calendar day |

No gaps over 10 calendar days anywhere in any series (checked
programmatically); gap distribution is dominated by 1-day (weekday-to-
weekday) and 3-day (weekend) spacing, confirming true daily bars throughout,
not a monthly-demoted series.

Eligible signal dates (after the 524-day burn-in for r20 + the 504-day
rolling-quintile window): GSPC 1972-05-03 → 2026-07-10 (5,631 dates), IXIC
1973-03-07 → 2026-07-20 (5,574 dates), RUT 1989-10-13 → 2026-06-18 (3,790
dates).

## Split

Chronological 70/30 split decided on GSPC's (primary instrument) eligible
signal dates alone, before any result was inspected: cutoff = **2009-04-27**
(position 3,941 of 5,631 = exactly 70.0%). In-sample = through 2009-04-27,
out-of-sample = after. Same cutoff date applied to all three instruments.
The out-of-sample slice was looked at exactly once, after this cutoff was
fixed and after the in-sample results were already recorded below.

## Cost model

No broker/commission table exists for a cash index — you cannot literally
trade ^GSPC/^IXIC/^RUT. Per the task's instructions, the cost-adjusted pass
reuses `REAL_COST_POINTS` from `screen_mean_reversion.py` (Tradovate's
measured futures round-turn costs) as the **closest available proxy**,
mapped by index family and applied per-trade via `cost_points / entry_price`
exactly as the original script does:

| Cash index | Proxy cost source | Free-plan round-turn |
|---|---|---|
| ^GSPC (S&P 500) | ES (S&P 500 e-mini) | 0.1152 pts |
| ^IXIC (Nasdaq Composite) | NQ (Nasdaq-100 e-mini) | 0.288 pts |
| ^RUT (Russell 2000) | YM (Dow e-mini) | 1.152 pts |

The RUT→YM mapping is the **weakest** of the three proxies: there is no
Russell-2000-specific futures cost anywhere in this project, so YM was used
only because it's the one remaining tier in `REAL_COST_POINTS`, not because
Dow and Russell-2000 are economically similar contracts. **This entire cost
column is an approximation, not a measured cost for any of these three
series — labeled NOT MEASURED below.**

## Results — non-overlapping (the trustworthy numbers)

Overlapping-window figures were also computed (all clear the bar, as
expected given ~19/20-day autocorrelation) but are not tabulated here for
the same reason the original RESULTS.md excludes them: they overstate
significance and are not the numbers to trust.

**In-sample (through 2009-04-27):**

| Instrument | Side | n | Zero-cost meanR | Zero-cost t | Zero-cost p | Proxy-cost meanR | Proxy-cost p |
|---|---|---|---|---|---|---|---|
| GSPC | bottom | 101 | +0.4297 | +4.111 | 0.0001\* | +0.4155 | 0.0001\* |
| GSPC | top | 97 | -0.1616 | -1.693 | 0.0937 | -0.1766 | 0.0669 |
| IXIC | bottom | 96 | +0.4401 | +2.849 | 0.0054\* | +0.4080 | 0.0092\* |
| IXIC | top | 96 | -0.6338 | -4.616 | 0.0000\* | -0.6721 | 0.0000\* |
| RUT | bottom | 56 | +0.1848 | +1.145 | 0.2573 | +0.0788 | 0.6195 |
| RUT | top | 50 | -0.3949 | -2.548 | 0.0140\* | -0.5128 | 0.0020\* |

4 of 6 cells clear the Bonferroni bar (p < 0.025), zero-cost and
cost-adjusted alike.

**Out-of-sample (after 2009-04-27, looked once):**

| Instrument | Side | n | Zero-cost meanR | Zero-cost t | Zero-cost p | Proxy-cost meanR | Proxy-cost p |
|---|---|---|---|---|---|---|---|
| GSPC | bottom | 42 | +0.3295 | +2.212 | 0.0326 | +0.3284 | 0.0332 |
| GSPC | top | 44 | -0.1210 | -0.872 | 0.3879 | -0.1226 | 0.3821 |
| IXIC | bottom | 44 | +0.4135 | +2.526 | 0.0153\* | +0.4125 | 0.0155\* |
| IXIC | top | 44 | -0.3389 | -2.532 | 0.0151\* | -0.3402 | 0.0147\* |
| RUT | bottom | 41 | +0.5680 | +3.462 | 0.0013\* | +0.5504 | 0.0017\* |
| RUT | top | 44 | -0.0819 | -0.574 | 0.5692 | -0.1009 | 0.4847 |

\* clears the pre-registered Bonferroni bar (p < 0.025)

3 of 6 cells clear the bar out-of-sample — three times the rate of the
original futures test's out-of-sample pass (1 of 6, NQ top only,
p=0.0142, n=18). Both in-sample and out-of-sample sample sizes here are
~2.3–2.6x larger per cell than the original run (42–44 OOS trades per cell
here vs. 16–18 originally), a direct consequence of using 39-57 years of
cash-index history instead of 24-25 years of futures history — the single
lever available to add real non-overlapping trades without touching the
rule.

## Replication / sign-agreement check

**In-sample:** bottom-long signs {GSPC +, IXIC +, RUT +} → AGREE. top-short
signs {GSPC -, IXIC -, RUT -} → AGREE.

**Out-of-sample:** bottom-long signs {GSPC +, IXIC +, RUT +} → AGREE.
top-short signs {GSPC -, IXIC -, RUT -} → AGREE.

**12 of 12 cells (both samples, both sides, all three instruments) agree in
sign with the pre-registered hypothesis direction.** This matches the
original futures test's 6-of-6 out-of-sample directional agreement, now
replicated on a fully independent dataset (cash indices, not futures) and
extended to the in-sample slice as well.

Cross-reference against the original NQ/ES/YM futures run (RESULTS.md):
that run's out-of-sample pass also showed 6-of-6 sign agreement but only 1
of 6 cells statistically significant. This deep-history cash-index run
shows the same perfect directional consistency with roughly triple the
statistical hit rate.

**Important caveat on "3 instruments":** GSPC, IXIC, and RUT are all broad
US equity indices with correlations typically above 0.85-0.95 on daily
returns. Sign agreement across them is only weak evidence of independent
replication — the same underlying macro mean-reversion pattern in "US
stocks" could easily drive all three cash indices together. This is the
same limitation the original NQ/ES/YM futures test carried (those three are
similarly correlated), not a new one introduced here, but it is worth
restating plainly: this is closer to "the pattern held up on longer history
of the same broad phenomenon" than "three genuinely independent markets."

## Sample-size context (sigma ≈ 1.0R)

Non-overlapping trades available, primary instrument (GSPC): in-sample
bottom=101, top=97; out-of-sample bottom=42, top=44.

N needed to detect a true edge at 80% power, alpha=0.025 two-sided,
sigma≈1.0R: 0.30R edge → N≈170; 0.20R edge → N≈380; 0.10R edge → N≈1,530.

With 42-101 non-overlapping trades per cell here (vs. 16-41 in the original
futures test's respective slices), this run can resolve roughly a
0.25-0.35R edge at 80% power in-sample, and a slightly weaker 0.35-0.45R
edge out-of-sample — better than the original test but still short of
being able to confidently rule out a smaller true edge.

## MEASURED vs. NOT MEASURED

**MEASURED**
- All in-sample and out-of-sample per-instrument, per-side n, mean R,
  t-stat, p-value figures above — computed by `screen_mean_reversion_deep.py`,
  which imports `build_signals`, `t_test`, `percentile`, `non_overlapping`,
  `split_dates`, `filter_sample`, `report` directly from
  `screen_mean_reversion.py` (identical math, not re-derived).
- Data coverage and gap-check for all three CSVs (dates, bar counts, gap
  distributions) — confirmed by direct inspection of the fetched files.
- The 70/30 chronological split point (2009-04-27) and its position (70.0%
  of GSPC's eligible signal dates) — computed, not assumed.

**NOT MEASURED**
- Real trading cost for any of these three cash indices. The cost-adjusted
  column uses ES/NQ/YM futures round-turn costs as a proxy (see Cost model
  above) — an approximation, not a measured cost for a cash index or for
  any actual tradable vehicle (e.g., SPY/QQQ/IWM ETFs, E-mini futures, or a
  CFD) that a trader would use to express this signal.
- Slippage/spread-crossing cost beyond the proxy figure.
- Whether the pattern survives on a *tradable* instrument at all — cash
  indices are not directly tradable; this test establishes the pattern
  exists in the index level itself, not that it survives translation to a
  real product with its own costs, dividends, and market-hours mismatch
  (e.g. RUT/IWM has a small dividend drag the raw ^RUT price index doesn't
  reflect).
- Independence of the three instruments — flagged above as a real
  limitation, not resolved by this test.

## Bottom line for a non-technical read

The original test found a pattern — after an unusually large 4-week move,
stock indices tend to drift back the other way over the next 4 weeks — but
only had about 16-18 "clean" (non-overlapping) test cases in its
out-of-sample data, and only one of six checks was strong enough to call
statistically real. That's why it was labeled "promising but unproven": an
interesting pattern with too small a sample to trust yet.

This re-test reruns the *exact same* idea, completely unchanged, on much
longer history — S&P 500, Nasdaq, and Russell 2000 index levels going back
39 to 57 years instead of the ~24-25 years of futures data used before. With
roughly 2.5x more clean test cases, the pattern held up better than before:
every single directional check (12 out of 12, across both the "already
seen" and "never looked at before" halves of the data) pointed the right
way, and three times as many checks cleared the strict statistical bar in
the never-before-seen half of the data as did originally (3 of 6, vs. 1 of
6). Trading costs — estimated using the closest comparable futures costs,
since you can't literally trade an index level — did not change any of
these results in a meaningful way.

This is genuinely better evidence than before, which is why the verdict is
moving from "promising but unproven" to **"needs testing"** — meaning it
has earned the next stage of scrutiny (a realistic simulation on an actual
tradable product, with its own real costs) rather than just continuing to
sit on a watch list. It has **not** earned a green light to build or trade:
half the checks still fall short of the statistical bar, the three indices
tested move together closely enough that this isn't really three
independent confirmations, and the costs used here are an educated
approximation, not a measured number for whatever product would actually be
traded.

## How to reproduce

```
cd /Users/osodo.t/QuantC/research/index_mean_reversion
python3 fetch_data_cash.py                                              # re-pull ^GSPC/^IXIC/^RUT (already run 2026-08-19)
python3 screen_mean_reversion_deep.py --sample in  --real-cost-tier free   # in-sample, safe to re-run
python3 screen_mean_reversion_deep.py --sample out --real-cost-tier free   # out-of-sample, look ONCE (already looked, this task)
```
