# Lucid walk-forward: pre-registration

Written 2026-10-20, committed **before any candidate was run** on any data. Nothing in the
live trading rules changes: no candidate is adopted, no alert is touched, no PR is made.
The question is whether any change to the live ORB rules passes the Lucid $100K evaluation
more often, and more cheaply per pass, on trades it never saw.

## Unverified inputs (repeated in every report)

These come from FIRM_RULES_SURVEY.md (search snippets, not read on the firms' pages). No
rule number is changed by this study.

| item | value used | status |
|---|---|---|
| Lucid eval price | $170 first try and each reset | **UNVERIFIED (GUESS)** |
| Lucid trail lock | floor stops at start + $100 | **UNVERIFIED (GUESS)** |
| Lucid funded payout cap | none | **UNVERIFIED (GUESS)** |
| Lucid funded cycle length | 3 days minimum | **UNVERIFIED (third-party)** |
| Lucid eval target / drawdown | $6,000 / $3,000 EOD trailing | official help-center snippet |
| Lucid eval consistency / minimum days | none / none | none found in the snippets |

The eval rule set is `Lucid 100K LucidPro (price GUESS)` in `firm_fit_test.py`; the funded
model is `Lucid 100K funded` in `funded_stage_test.py`. Both are used as they stand.

## 1. What trade profile passes

The eval has no consistency rule and no minimum days, so a pass needs +$6,000 before the
balance touches a floor that trails the closing peak by $3,000 (locked at +$100).

`lucid_wf_test.py threshold` solves, by simulation on the unchanged rule engine, the
**smallest expectancy per trade** that gives a **60% per-attempt pass rate** for a grid of
win rate (0.30, 0.40, 0.50, 0.60) and risk per trade ($250, $500, $625, $1,250, $1,875;
$625 / $1,250 / $1,875 are the live 125-point stop at 1 / 2 / 3 MES). Winners are a fixed
size and losers lose exactly the risk. Winners are assumed to have no adverse excursion
(optimistic), losers touch their full risk. 200 trades a year. It reports the expectancy in
$ per trade, per MES in points, and as a share of the risk. The live rules' own figure
(about $820 a year per MES, about $4 a trade) is shown beside it.

## 2. Stop against the floor

One full stop is `contracts x stop points x $5`. The share of the $3,000 floor:

| stop | 1 MES | 2 MES | 3 MES |
|---|---|---|---|
| 125 pts (live) | 20.8% | 41.7% | 62.5% |
| 100 pts | 16.7% | 33.3% | 50.0% |
| 75 pts | 12.5% | 25.0% | 37.5% |

**Cap: one full stop must be at most 40% of the floor** ($1,200). At 2 MES that means a
stop of 120 points or less, so the live 125-point stop at 2 MES breaches the cap by 1.7
points. At 3 MES every stop in this study is over the cap, so 3 MES is reported but never
decides anything. A candidate is judged at a size only if its stop is within the cap at
that size; the live rules are the baseline at every size regardless, and the report states
where the baseline itself is over the cap.

## 3. Candidates (cap 12, including the live rules)

One change at a time from the live rules, then four fixed combinations. Nothing else varies.
Live: range 9:30-9:44 (15 bars), entries from 9:45 to the 15:59 bar, 125-pt stop, 90-minute
underwater exit, flat on the 15:59 bar, no partial.

| id | stop | range build | last entry bar | partial exit |
|---|---|---|---|---|
| LIVE | 125 | 15 min | to 15:59 | none |
| S100 | 100 | 15 | to 15:59 | none |
| S75 | 75 | 15 | to 15:59 | none |
| E1030 | 125 | 15 | before 10:30 | none |
| E1130 | 125 | 15 | before 11:30 | none |
| R5 | 125 | 5 (9:30-9:34, entries from 9:35) | to 15:59 | none |
| R30 | 125 | 30 (9:30-9:59, entries from 10:00) | to 15:59 | none |
| P60 | 125 | 15 | to 15:59 | half off at entry + 60 pts |
| S100E1130 | 100 | 15 | before 11:30 | none |
| S100P60 | 100 | 15 | to 15:59 | half off at entry + 60 pts |
| S100R30 | 100 | 30 | to 15:59 | none |
| E1030P60 | 125 | 15 | before 10:30 | half off at entry + 60 pts |

Rules for the variants: the entry is still the first 1-minute close above the range high,
one attempt a day. The partial exit is a limit order for half the position at entry + 60
points, placed from the bar after the entry bar; if one bar touches both the stop and the
60-point level the stop is taken first; the rest follows the live exits. The stop never
exceeds 125 points. The partial exit needs two contracts, so a candidate with a partial is
**judged at 2 MES only**; its 1 MES figures are a half-contract idealisation, shown but not
used. Commissions are per contract per side, so a partial exit adds none.

## 4. Walk-forward

- Data: the real ES history on the user's Mac (2021-08-19 to 2026-08-18), MES proxy as in
  `firm_fit_test.py`. Base costs $2.50 per round turn plus 1 tick.
- Fit on a rolling **24 months**, trade the next **6 months** blind, step 6 months. That gives
  6 folds and about 36 months out of sample.
- Selection in each fold uses training trades only: the per-attempt Lucid pass rate at 2 MES
  from a block bootstrap of the training trades (400 paths, 600 trades, block 5, fixed
  seed), ties broken by higher mean net per trade. The live rules are in the pool.
  Choosing the best of 12 on a rolling window is the **walk-forward selector (WF)**.
- Out-of-sample trades of the selected candidate are joined end to end. LIVE is scored on
  exactly the same test windows, and so is every fixed candidate.

## 5. Scoring

Each sequence (WF, LIVE, each fixed candidate) is fed to `firm_fit_test.py` (bootstrap
paths, block 5, Lucid eval rule set) and `funded_stage_test.py` (Lucid 100K funded) at
1, 2 and 3 MES. Tables: pass rate, median calendar days, cost per pass (5 attempts), and
mean paid minus the evaluation cost per funded account (400 trades, about 2 years).
Backtest profit is reported but never decides.

## 6. Pass criteria (set now, applied to WF and to each fixed candidate)

A sequence **beats the live rules** only if, at every deciding size (1 and 2 MES; 2 MES
only if it has a partial exit; 3 MES never decides), it meets all of:

1. **Pass rate**: at least **5.0 percentage points** above LIVE.
2. **Cost per pass**: at most **85%** of LIVE's (a cut of 15% or more).
3. **Significance**: the paired pass-rate difference (same resampled weeks for both
   sequences; outer resamples of whole weeks of the out-of-sample period, inner bootstrap
   paths) has mean minus z x sd above zero, with z = 2.87 (two-sided Bonferroni for 12
   comparisons, alpha = 0.05 / 12 = 0.0042).
4. **Not fewer, bigger bets**: trades a year at least **80%** of LIVE's; mean stop distance
   no larger than LIVE's (125 pts); stop within the 40% cap at that size; and the
   comparison uses the same contract count for both.
5. **Enough trades to judge**: at least **400** out-of-sample trades and at least **150** a
   year.
6. **No funded regression**: mean paid minus cost per funded account (400 trades) at least
   LIVE's at that size. This stops a pass-rate gain that pays less once funded.

If nothing meets all six, the answer is that nothing beat the live rules, and the
recommendation is to keep them.

## 7. Multiplicity

12 comparisons are counted: the 11 fixed challengers and the WF selector. The significance
bar above is the discount. Earlier searches on the same data (EDGE_SEARCH_RESULTS.md: four
candidates, the stop and wide-stop studies) are not in the 12 but make the true number of
looks larger, so the bar is, if anything, lenient. Any candidate that passes is a lead for a
fresh, separately pre-registered forward test, never a basis for changing the alert.

## 8. Known limits

- Only about 3 years and about 600 trades out of sample; real-order starts are few and
  overlap, so the bootstrap decides and real-order starts are a check only.
- ES bars are the MES proxy. Stop fills are exact plus slippage; gaps are not modelled.
- Fitting happens on 24 months, enough to rank candidates roughly, not to find small edges.
- The eval price, trail lock, payout cap and cycle length are unverified (section above).
- Not modelled: scaling plans, the funded daily loss limit, tax, re-buying after a breach.
