# NQ / ES / YM Opening Range Breakout — Results

Pre-registration: [HYPOTHESIS.md](HYPOTHESIS.md) (locked before this data was
inspected). This file records what was actually MEASURED — nothing here is
invented or estimated, everything is labeled MEASURED, ASSUMPTION, or NOT
MEASURED per the propfirm-research-auditor discipline.

## 1. Entry-predicts-direction test (MEASURED)

Run: `orb_test.py`, in-sample (through 2025-02-14) then the held-out
out-of-sample slice (after 2025-02-14), looked at once, per the pre-registered
70/30 split.

### Long side (close above the 09:30–09:44 ET opening range)

| Instrument | In-sample meanR (n) | p | Out-of-sample meanR (n) | p |
|---|---|---|---|---|
| NQ (primary) | +0.167R (457) | 0.0014 | +0.179R (194) | 0.0068 |
| ES (repl.) | +0.172R (453) | 0.0007 | +0.184R (209) | 0.0041 |
| YM (repl.) | +0.074R (442) | 0.1411 | +0.078R (206) | 0.2331 |

Both NQ and ES clear the pre-registered Bonferroni threshold (p < 0.025) in
**both** slices, with the edge size essentially unchanged out-of-sample (no
decay). YM agrees in sign in both slices but is not independently
significant. Sign agreement across all three instruments: **AGREE**, both
slices — meets the project's 3-instrument replication standard (the
checklist requires sign agreement, not independent significance per leg).

Real Tradovate cost (free-plan tier) barely moves any of these numbers —
reported above is zero-cost; cost-adjusted is ~0.002–0.005R lower per row.

### Short side (close below the range) — REJECTED

In-sample: directionally negative on all three (weak, none significant).
Out-of-sample: **YM flips sign positive** — NQ/ES/YM no longer agree in
direction. Replication check: DISAGREE. This side does not survive its own
pre-registered test and should be dropped, consistent with the domain
caution already on record (a structurally similar FX session-breakout
mechanism was previously measured at zero/negative — see HYPOTHESIS.md §2).

## 2. Survivability against the real firm limits (MEASURED simulation, one input remains an ASSUMPTION)

Run: `ruin.py`, bootstrapped from **1,313 real, cost-adjusted R multiples**
(pooled NQ+ES long-side trades, full 5-year history — the mechanism that
survived step 1; YM and the short side excluded). Mean of that pooled series:
**+0.1731R**. This is a real, measured trade-outcome distribution, not a
parametric guess.

**Firm limits corrected 2026-08-19** (see HYPOTHESIS.md §1 - the first pass
of this section used wrong numbers, carried over from an earlier,
never-re-verified assumption in this project): account-failing drawdown is
**$3,000 (3%), trailing to end-of-day balance, verified directly against
lucidtrading.com's own LucidPro EVAL 100K page. The $1,800 figure is a soft
daily pause, not an account-failing rule, and is correctly excluded from
this simulation. There is no time limit and no minimum trading days** -
**re-confirmed 2026-08-27 directly against Lucid's own help-center articles
and the live account dashboard** (previously this was only corroborated by
two independent third-party trackers; see HYPOTHESIS.md §1 for the full
re-confirmation, including a previously-unrecorded detail that the $3,000
trail locks permanently at $100,100 once the account clears $103,100) - the
earlier assumed ~250-day horizon is gone; the simulation below uses an
effectively unbounded horizon (5,000 trading days) with zero timeouts as a
result.

**One input remains a genuine gap:** risk-per-trade sizing. The tested
mechanism has no stop-loss (exit is always the session close) - "R" here is
return normalized by that trade's own realized volatility, not a fixed stop
distance. Converting that into a real position size (how many dollars of the
account move on a "1R" trade) requires designing a stop-loss/sizing rule,
which this audit process does not do (see the "never invent a number" and
"never propose entries/exits" rules). The table below sweeps a range of
illustrative risk levels instead of assuming one.

| Risk per trade (of $100k) | PASS | FAIL (hits $3,000 DD) | Median days to pass |
|---|---|---|---|
| 0.10% ($100/trade) | 99.9% | 0.1% | 333 |
| 0.15% ($150/trade) | 98.8% | 1.2% | 216 |
| 0.25% ($250/trade) | **89.9%** | 10.1% | 119 |
| 0.50% ($500/trade) | 65.6% | 34.4% | 45 |
| 0.75% ($750/trade) | 54.3% | 45.7% | 24 |
| 1.00% ($1,000/trade) | 48.7% | 51.3% | 15 |

Reading this plainly: **with the correct, much wider $3,000 trailing limit
and no time pressure, this account survives comfortably at conservative
sizing** - 90%+ pass rates through 0.25% risk/trade ($250), and even 0.50%
risk still passes about two-thirds of the time. It only becomes a coin flip
or worse once risk climbs toward 0.75-1.0% of the account per trade. This is
a materially better picture than the earlier (wrong) $1,800-limit run, which
capped pass rates around 62% even at its best setting.

Other simplifications in this simulation (secondary, smaller effect):
- Trades-per-day set to 1 (pooled NQ+ES actually fire slightly less than
  1/day combined on average; a minor pacing approximation, not a rule).
- The drawdown check marks to market on every simulated trade, not only at
  end-of-day like the real Lucid rule - this makes the simulation somewhat
  *stricter* than reality (real survivability is likely a bit better than
  shown, not worse), direction of the bias only, not quantified.

## 2.5. Outlier / tail check (MEASURED)

Distribution of all 1,313 pooled NQ+ES long-side R multiples: win rate
**57.2%**, mean **+0.1731R**, median **+0.2145R**, sd 1.04R, range −3.13R to
+2.67R. Shape is a single roughly bell-shaped hump straddling zero (see
histogram) — no isolated outlier bin disconnected from the rest.

Sensitivity to removing the best days (does the edge collapse without them?):

| Removed | New mean |
|---|---|
| (none) | +0.173R |
| best single trade | +0.171R |
| best 1% (13 trades) | +0.149R |
| best 5% (65 trades) | +0.069R |

Removing even the best 5% of trades still leaves a **positive** mean — the
edge is not a single lucky day's work, though a meaningful chunk of it does
come from the right tail (normal for a no-stop, ride-to-close exit; a
handful of trend days do more work than an average day). Removing the worst
days moves the mean the other way (up, as expected) — no hidden left-tail
disaster sitting outside what the survivability simulation already sampled
from, since that simulation drew from this exact same series.

## 2.6. Position sizing on the real firm limits (MEASURED)

The tested mechanism has no stop-loss (holds to session close), so "risk
per trade" is really "how many contracts." Computed the real, MEASURED
dollar swing per 1R for one contract, from the actual historical trades
(horizon volatility × entry price × point multiplier, per trade):

- NQ, 1 full-size contract: median $2,570/1R (p10 $1,548, p90 $5,014)
- ES, 1 full-size contract: median $1,412/1R (p10 $817, p90 $2,733)

Fed those directly into the same ruin.py simulation (corrected firm rules):

| Position | Typical risk/trade | PASS (median-$/1R approx.) | PASS (exact-dollar, reconciled 2026-08-21) |
|---|---|---|---|
| 1 full-size NQ | ~$2,570 | 44.5% | 38.45% |
| 1 full-size ES | ~$1,412 | 45.2% | 35.65% |
| 1 micro NQ (MNQ, 1/10 size) | ~$257 | 89.1% | **31.30%** |
| 1 micro ES (MES, 1/10 size) | ~$141 | 99.1% | **51.36%** |

**Correction (2026-08-21):** the original "PASS (median-$/1R approx.)" column
fed `ruin.py` one *typical* dollar-risk figure per instrument (the median
trade's $/1R), applied uniformly to every simulated trade. `baseline_reconciliation.py`
re-ran the same instruments and firm rules feeding `ruin.py` each trade's
**exact** real historical dollar P&L instead (the same technique used
throughout §2.7 below) — no approximation, so it captures the fat-tailed
trades the median figure smooths away. The exact-dollar numbers are the
ones to trust; they are markedly lower, in one case (MNQ) reversing the
original ranking entirely — the micro contract ends up *less* survivable
than full-size NQ, not more, because MNQ's very small per-trade dollar
swing (~$14 mean) means far more trades are needed to reach the $6,000
target, giving far more chances for a bad stretch to breach the trailing
drawdown before getting there.

**Revised finding: none of the four plain no-stop positions clear a
"comfortable" bar once measured exactly — all four sit in the 31-51% range,
closer to a coin flip than a safe bet.** The original claim that micro
contracts fix the full-size sizing problem does not hold up; sizing alone,
with this no-stop exit mechanism, is not enough. See §2.7 for a mechanism
that was later found to meaningfully improve this (for MES specifically).

## 2.7. MES-only: combined stop-loss + 90-min time exit, with slippage (MEASURED)

Separate, later line of research (2026-08-21), narrower in scope than
sections 1–2.6 above: **MES only** (not pooled with NQ/ES/MNQ), testing a
different exit mechanism — a 99th-percentile price stop (124.75 pts, from
the MAE distribution) combined with a 90-minute "exit if still underwater"
time filter — instead of the no-stop, hold-to-close mechanism used
everywhere above. Run: `mes_final_run.py`, 662 MES long trades, full 5-year
history, via the same `ruin.py` survivability simulator and the corrected
LucidPro firm rules (§2).

| Configuration | PASS rate | Prob. of ruin |
|---|---|---|
| No exit mechanism (hold to close, raw baseline) | 51.36% | 48.64% |
| Price stop only | 64.41% | 35.59% |
| 90-min time exit only | 73.67% | 26.32% |
| **Price stop + 90-min time exit (combined, no slippage)** | **77.82%** | 22.18% |
| Combined + 1 tick (0.25 pt) adverse slippage, all exits | 71.60% | 28.40% |
| Combined + 2 ticks (0.50 pt) adverse slippage, all exits | 64.29% | 35.71% |

Slippage was applied to **every** exit fill — the price stop, the time
exit, and the scheduled session close — not just the two market-triggered
exits. This matters because roughly 57% of trades still exit at the
scheduled session close rather than the stop or time trigger, so slipping
only the other two (an earlier, narrower version of this test) understated
the real effect. Reading this plainly: the 77.8% headline assumes a perfect
fill and is optimistic; realistic execution (1–2 ticks of adverse slippage)
brings survivability down to somewhere between 71.6% and 64.3% — at the
higher end of that range the combined-exit mechanism's edge over the raw
no-exit baseline (51.4%) is largely given back.

~~Status: this mechanism exists only as a reviewed **draft**
(`orb_long_ghost_DRAFT_mes_v2.pine`), separate from the live
`orb_long_ghost.pine` (which still runs the no-stop, NQ+MNQ+MES-agnostic
mechanism described in §1–2.6).~~ **Correction 2026-08-27: this was wrong —
the v2 draft is already live**, wired to a "MES(v2 Draft)" ticker on the
real account (LTE10089070250001), not sitting in review. Checking it
directly in Ghost turned up two problems, found and partly fixed the same
day: (1) its broker-side stop toggle was off entirely, so real trades were
running with **zero** stop-loss despite the script being designed around
one — fixed by enabling the toggle; (2) once enabled, Ghost revealed the
ticker's actual TradingView alerts aren't sending `sl`/`tp` values at all,
so it now runs on an untested fixed 10pt-stop/20pt-target fallback instead
of this section's actual tested mechanism (~125pt stop + 90-min time exit,
no take-profit) — ~~that part is **still open**~~.

**Resolved 2026-08-28**: the root cause was that the ticker's TradingView
alert was linked to the wrong script (the plain validated one, which never
sends `sl`) rather than to this draft — the draft itself had been sitting
on the chart correctly marked "NOT LIVE" with no alert of its own the whole
time. Fixed by creating a new alert directly on the draft script and
pointing it at the same Ghost webhook, so the ticker now actually runs
*this* section's tested mechanism (~125pt stop + 90-min time exit) rather
than the 10/20 fallback. Full detail in
[SETUP_GUIDE.md](SETUP_GUIDE.md). The same mis-wiring was found and fixed
for MNQ too, which is now running STOPLOSS_HYPOTHESIS.md's opposite-range
stop instead of the plain no-stop mechanism — also detailed in
SETUP_GUIDE.md. The two mechanisms (this section's vs. the plain no-stop
one) have still not been reconciled into one *research* recommendation for
which is objectively better — see the note in §3 below — but operationally,
both live accounts now run their respective best-tested draft rather than
the plain no-stop mechanism.

## 2.8. MNQ + MES on one account: diversification or the same bet twice? (MEASURED)

Run: `mnq_mes_correlation.py` (2026-09-10). Closes the gap `mes_final_run.py`
prints in its own NOT MEASURED block — "no test in this project has ever
combined MNQ+MES trades into one shared account equity curve." Prompted by a
live operational question: whether to run this same ORB-long mechanism on a
second ticker against the one shared $3,000 drawdown budget.

Deliberately **assumption-free**: identical entry rule on both instruments,
measuring the raw hold-to-session-close percentage return. Percentage return
makes the two price levels comparable; the raw close exit means **no stop
distance had to be invented for NQ** (none has ever been validated there).

| | Measured |
|---|---|
| ES ORB-long days / NQ ORB-long days | 662 / 651 |
| Days both fired | 548 |
| Of ES's signal days, NQ also fired | 82.8% |
| Correlation of same-day returns (n=548) | **r = 0.963** |
| Shared variance | **92.7%** |
| Both won or both lost | **90.7%** (306 both-win, 191 both-lose) |
| One won, one lost | 9.3% (51 days) |

Volatility of an equal-weight blend versus one leg alone:

| | sd of daily return |
|---|---|
| ES alone | 0.892% |
| NQ alone | 1.129% |
| 50/50 blend | **1.001%** (**+12.3%** vs ES alone) |
| Same blend if the two were uncorrelated | −29.3% vs ES alone |

Reading this plainly: **r = 0.963 is not "correlated," it is effectively the
same instrument** — only ~7% of the movement is independent, and nine times in
ten both legs share the same outcome on the same day. The blend is *more*
volatile than MES alone, not less, because at this correlation there is nothing
to offset and NQ is simply the choppier leg. The −29.3% figure is the
diversification benefit that would have been available had the two been
independent, and is not obtained. Adding MNQ alongside MES is therefore an
increase in exposure, not a reduction in variance — the same trade-off as
raising contract size, but taken on an instrument whose exit mechanism §2.7
never tested.

The one genuine point on the other side: 114 ES-only and 103 NQ-only days are
real additional trade opportunities, and more trades does shorten time-to-target
at a given size. That benefit is orthogonal to diversification and does not
change the correlation finding.

**NOT MEASURED here:**
- This is the raw **entry signal's** co-movement, not the deployed mechanism's
  dollar-P&L correlation. Measuring that needs a 99th-percentile MAE stop
  distance for NQ, which has never been measured or validated.
- No combined equity curve was simulated and **no combined survivability/ruin
  number is produced**. This measures whether the two legs are the same bet —
  not what running both would do to the pass rate.
- Equal-weight blend. In contracts, 1 MNQ carries ~1.5x the notional of 1 MES
  (~$58k vs ~$38k), so a 1-and-1 position would tilt further toward NQ's higher
  volatility than the blend figure above shows.

## 2.9. Contract sizing: decision to stay at 1 (2026-09-11)

A sizing sweep dated 2026-09-10 is quoted in the MES v2 scripts' `qty` tooltip:
on the full 5-year history at 1 tick slippage, starting from the account's real
state, 1/2/3/4 contracts gave **77 / 52 / 43 / 39%** chance of passing, with
median time-if-passing of ~3.7yr / 1.2yr / 7mo / 5mo. More size does not improve
the odds — it buys speed by selling certainty.

**Decision 2026-09-11: stay at 1 contract.** `qty` is back to 1 and hard-locked
at `maxval=1` in both MES v2 files, so a live chart's input panel cannot be
nudged. Raising size requires a deliberate source edit. The decision was taken
on the morning of an 8:30am ET CPI print with FOMC five days later — doubling
real per-trade risk ($625 → $1,250) into that was not a trade worth making.

The **per-CONTRACT risk-cap fix is kept** and is a no-op at 1 contract
($625 / $5 = the same validated 125pt stop). Its value is defensive: the old
`stop = maxRiskDollars / (qty × pointvalue)` silently halved stop distance the
moment `qty` rose above 1, which would have recreated the too-tight-stop failure
measured live on MNQ.

~~**NOT MEASURED / caveat:** no script in this repo reproduces the 77/52/43/39
sweep — `grep` finds no contract-count loop and none of those figures in any
`.py` here. The numbers currently exist only as prose in the script tooltip and
in this section. **Re-run and commit the sweep script before any future decision
leans on them**; they are not independently reproducible as things stand.~~
**RESOLVED 2026-09-18 — see section 2.11.** `lucid_barrier_model.py` reproduces
this sweep from a committed script for the first time (77.11/52.94/44.37/39.95%,
matching the prose almost exactly) and additionally models the account's real
drawdown lock, which the original sweep's method did not.

## 2.10. Venture economics: will this PAY? (MEASURED + VERIFIED, 2026-09-11)

Run: `venture_economics.py`. Every prior section in this file optimises one
question — *will this account PASS*. None has ever asked *will this venture
PAY*. They are different questions and a configuration can win the first while
losing the second. This section closes that hole.

### The mechanism that is actually deployed, priced exactly

Measured on the same 5-year 1-minute dataset every other section uses, with the
**live** parameters read out of `orb_long_ghost_DRAFT_mes_v2_accessible.pine`
(MES, 1 contract, 125pt stop = $625/contract, 90-min underwater time exit),
net of real Tradovate free-tier costs and 1 tick of adverse slippage on every
exit — 662 trades, 2021-08-19 to 2026-08-14:

| | MEASURED |
|---|---|
| Win rate | **44.4%** |
| Average winner | +$133.21 |
| Average loser | −$90.06 |
| Reward : risk | 1.48 : 1 |
| **Expectancy per trade** | **+$9.10** |
| Worst single trade | −$626.83 |
| Best single trade | +$789.42 |
| Longest losing run (actual historical order) | 9 trades |
| Trade frequency | 132.8 / year |

**The 57.2% win rate quoted in §2.5 is not this mechanism.** That figure
belongs to the retired no-stop, NQ+ES-pooled series and has been carried
around this project as though it described what runs. It does not. The
deployed mechanism wins **less than half** its trades and makes its money on
a 1.48:1 payoff. Both facts are fine on their own; what matters is what they
imply together, below.

The +$9.10 figure independently reproduces the number recorded on 2026-09-10,
from source, by a committed script — it is no longer prose-only.

### Margin of safety — the number that decides everything

At 1.48:1, the **break-even win rate is 40.3%**. The measured win rate is
**44.4%**. The entire edge is a **+4.1 percentage point** margin.

Read plainly: lose four points of win rate to real-world execution — worse
fills than modelled, Ghost latency, one missed or mis-routed alert per
twenty-five trades — and the edge is *gone*, not reduced. This is a thin,
real edge, not a comfortable one. It is also the strongest argument on record
for why the live-vs-backtest reconciliation discipline in the `lucid-review`
skill is not optional bookkeeping: a 4-point gap is inside the range that
sloppy execution can open on its own, and it would not be visible as a
dramatic failure — just as an edge that quietly never shows up.

### Time to target, and what it costs to wait

At +$9.10 × 132.8 trades/year the mechanism generates **$1,208/year** of gross
raw material. Against the $6,083 still needed (recorded 2026-09-10 — CONFIRM
against the live dashboard before leaning on it), that is **669 trades, ~5.0
years on the mean path**. `ruin.py`'s 77% pass / ~3.7yr median is the
variance-aware, conditional-on-passing figure; both are correct and they
answer different questions.

### The fee structure — VERIFIED, and it corrects an assumption

Read live from lucidtrading.com's own pricing table and FAQ on 2026-09-11
(not a third-party tracker):

| | VERIFIED |
|---|---|
| LucidPro 100K EVAL | **one-time $307** ($225.40 w/ coupon `VAULT`) |
| Reset fee | $225 |
| Account activation fee | **FREE** |
| Recurring / monthly | **$0 — none** |
| Funded split | 90/10 to trader |
| Payout target | $750 / cycle |

Lucid's FAQ, verbatim: *"Do I have to pay monthly for my accounts? No. All of
our accounts are a one-time fee, we do not have monthly subscriptions for
trading accounts."*

**This corrects a concern raised earlier the same day** — that a multi-year
grind would bleed subscription fees until the attempt was underwater. It does
not. The cost of the attempt is **sunk and bounded at ~$225–307, already
paid**, and holding the evaluation open costs nothing. Time spent grinding is
not money bleeding. What is actually at risk over those years is attention and
opportunity cost, not fees — a materially different, and much more favourable,
decision than a recurring-fee model would present.

### What it pays if it works

Once funded, at this same size and frequency: $1,208/year gross → **$1,087/year**
at the 90/10 split → **1.6 payout cycles per year** against the $750/cycle
target.

### The binding constraint (the actual finding)

Expectancy is +$9.10 per trade and the mechanism fires ~133 times a year.
**No sizing choice changes that.** Raising contracts multiplies the $9.10 and
the $625 of risk in exact lockstep — it slides along the already-measured
77/52/43/39 curve without ever improving the ratio, which is precisely why
the 2026-09-11 decision to stay at 1 contract was correct and why revisiting
it would not help.

Only two levers raise return *without* paying for it in pass-probability:

- **(a) more trades per year that are genuinely uncorrelated with this one.**
  §2.8 already ruled MNQ out for this purpose at r = 0.963 — that is the same
  bet twice, not diversification. An uncorrelated *mechanism* was the open
  candidate — **MEASURED 2026-09-11, see
  [research/vwap_fade/RESULTS.md](../vwap_fade/RESULTS.md)**. Split decision:
  the VWAP-fade draft is genuinely independent of ORB (**r = −0.161**, 2.6%
  shared variance, 521 trading days ORB never sees — against MNQ's +0.963),
  which **confirms this slot is real and fillable**. But the draft rule itself
  loses money (−$4.04/trade, 78.6% stopped out, negative in-sample on its own
  hand-picked parameters) and is rejected. **The slot stays open; this
  candidate does not fill it.** Because r is slightly negative the bar is
  unusually low — a fade would be worth adding at merely break-even. Any
  successor must be pre-registered with an out-of-sample split before the data
  is re-inspected.
- **(b) higher expectancy per trade at the same risk.** `mes_takeprofit_sweep.py`
  and the untested NQ application of §2.7's mechanism both sit here.

Everything else is a speed-versus-certainty trade, not an improvement.

**NOT MEASURED here:** this section deliberately does not model the trailing
drawdown — it is arithmetic about money, not a pass-probability; `ruin.py`
owns that. The funded-phase figures assume the eval mechanism carries over
unchanged, but the funded stage has a different daily loss limit (60% of peak
EOD balance) and the 40% consistency rule, and **no test in this project has
ever simulated the funded stage.** Trade frequency assumes the alert is
running — it was paused 2026-09-11, and a paused alert trades zero times a
year.

## 2.11. The Lucid barrier model: how much of survivability is geometry vs edge? (MEASURED, 2026-09-18)

Run: `lucid_barrier_model.py`. Prompted by an external source — Villahermosa
(2026), *"Prop-Firm Challenges: A Barrier Model of Pass Rates and Expected
Value"* (SSRN 7445798) — which models challenge products as a barrier-crossing
problem and derives a closed-form ceiling on pass probability, independent of
skill, for ANY prop-firm evaluation. Two questions this project had never
asked: (1) what does that ceiling say about *this* account specifically, and
(2) does the paper's central finding — that pass probability is *non-monotonic*
in position size for a skill-free participant, peaking at an interior size
rather than falling steadily — change anything about the 2.9 sizing decision.

**A methodology note, kept on the record per this project's own discipline:**
the first version of this script's "zero-edge control" accidentally carried a
small phantom edge (a one-time random win/loss sign assignment across the 662
trades that happened to land at +$4.80/trade average by chance, then got
reused on every resample instead of re-flipped). It was caught by validating
the code against the paper's own worked example (a symmetric random walk
should reproduce the closed-form ceiling under a fixed floor, and land
*strictly below* it under a trailing floor) before any number below was
trusted. Fixed by drawing a fresh 50/50 sign on every simulated trade instead
of fixing the signs once. Recorded here, not silently corrected, per this
project's "never invent a number" standard.

### The ceiling, and what a zero-edge trader actually gets on Lucid's exact rules

Lucid's own numbers (VERIFIED, HYPOTHESIS.md / RESULTS.md 2): loss limit
$3,000, profit target $6,000, trailing drawdown that **locks permanently at
$100,100 once the account's peak balance clears $103,100** (this lock has
never been modelled anywhere in this project before — `ruin.py`'s
`--dd-basis trailing` trails the peak forever).

| | Value |
|---|---|
| Theoretical ceiling, L/(T+L) | **33.3%** (Lucid's 2:1 target:loss ratio is steeper than the paper's own studied product's 1.25:1, whose ceiling was 44.4% — Lucid caps lower before any friction) |
| Zero-edge control, 1 contract, WITH the real lock | **19.41%** |
| Zero-edge control, 1 contract, WITHOUT the lock (old `ruin.py` assumption) | 14.88% |

Both control figures sit **below** the 33.3% ceiling, as the paper's own math
requires (real commissions/slippage and the trailing-floor mechanic eat the
rest) — this is the check that caught the bug above, and the fixed version
passes it. Read plainly: **a perfectly disciplined trader with zero real edge
would pass this specific evaluation roughly 1 time in 5**, not 1 time in 3.

### The live mechanism, reproduced and extended

The 77/52/43/39% figures quoted since 2026-09-10 (§2.9) existed only as prose
— no committed script reproduced them. They are reproduced here, and for the
first time the real drawdown lock is included rather than assumed away:

| Contracts | PASS, lock modelled (this run) | PASS, no lock (old assumption) | Lock is worth |
|---|---|---|---|
| 1 | **77.11%** | 69.02% | +8.09 pts |
| 2 | **52.94%** | 44.08% | +8.86 pts |
| 3 | **44.37%** | 36.23% | +8.14 pts |
| 4 | **39.95%** | 33.38% | +6.57 pts |

The reproduced figures (77.11/52.94/44.37/39.95) match the 2026-09-10 prose
(77/52/43/39) almost exactly, which is a strong independent validation of
that earlier, previously-unreproducible sweep. The lock is worth a real and
now-quantified **+6.6 to +8.9 percentage points** at every size — this
precisely answers the "~8 points pessimistic" note carried in project memory
since 2026-09-11, which had never been measured until now.

### Does the paper's "peaks at an interior size" finding apply here? No.

The paper's central claim is that pass probability is non-monotonic in
position size — too large blows through the floor fast, too small pays a
fixed per-trade friction cost repeatedly, so a skill-free participant's best
odds sit at an interior sweet spot, not at the smallest size. Tested directly
against Lucid's exact rules across 1–4 contracts:

- Live mechanism (real edge): 77.11% → 52.94% → 44.37% → 39.95% —
  **monotonically decreasing.**
- Zero-edge control: 19.41% → 20.80% → 21.49% → 22.93% — mildly
  **monotonically increasing** (consistent with the "bold play" principle the
  paper itself cites — Dubins & Savage, 1965 — for a sub-fair game: fewer,
  larger bets mean fewer chances for fixed per-trade friction to bite before
  the barrier is reached; this is the zero-edge mirror image of why bigger
  size does NOT help the live mechanism).

**No hidden sizing lever found.** The 2026-09-11 decision to stay at 1
contract is not just unchanged — it is now the best-tested conclusion in this
file, having survived a second independent model built specifically to find
a counterexample to it.

### What was actually riding on the 4.1-point margin, quantified for the first time

§2.10 already established the live mechanism's edge is a thin +4.1
percentage-point margin over break-even win rate. This section shows what
that margin is worth in practice: at 1 contract, the live mechanism passes
77.11% of the time against a zero-edge trader's 19.41% on the **identical**
rules — a 57.7-point gap produced entirely by that one thin margin compounding
across hundreds of trades. The edge is not fragile in the sense of being
small in its effect — it is fragile only in the sense that if real-world
execution erodes the 4.1-point margin toward zero, survivability does not
degrade gently; it collapses back toward the 19–23% zero-edge band. This is
the sharpest number yet for why the `lucid-review` live-vs-backtest
reconciliation discipline is load-bearing, not optional bookkeeping.

**NOT MEASURED here:**
- The funded-stage rules (60% of peak EOD daily-loss limit, 40% consistency
  cap) are not modelled — this section, like `ruin.py` and §2.9/2.10 before
  it, answers the EVALUATION pass question only.
- The $1,800 Ghost-side daily limit is not modelled (confirmed soft, not
  account-failing — RESULTS.md section 2).
- The zero-edge control matches trade magnitude and real cost/slippage drag
  exactly; only the win/loss sign is randomised per draw. It is not a
  synthetic parametric distribution.
- One simulated "tick" = one historical trade occurrence, matching this
  project's existing `--trades-per-day 1` convention; non-trading days are a
  no-op for both the peak and the floor either way.

## 3. NOT MEASURED / still open

- **A real hard stop-loss** — tested 2026-08-20, see
  [STOPLOSS_HYPOTHESIS.md](STOPLOSS_HYPOTHESIS.md#results-measured--2026-08-20).
  Original verdict was reject (cuts the worst-case trade 5–18x but appeared
  to lower survivability, MNQ 89.1%→63.5%, MES 99.1%→94.3%) — **but that
  comparison used the same pre-correction median-$/1R sizing this section's
  own §2.6 later found to be invalid.** Re-measured 2026-08-27 with the
  exact-dollar method (`stoploss_reconciliation.py`): survivability actually
  *improves* with the stop — MNQ 31.30%→54.30% (+23.0 pts), MES
  51.36%→65.89% (+14.5 pts) — see the correction section at the bottom of
  STOPLOSS_HYPOTHESIS.md. **Verdict is now `promising_but_unproven`, not
  reject** — this is not closed, and the no-stop mechanism is not the only
  option that ships as-is by default.
- ~~The firm-rules correction (§2) was verified against Lucid Trading's own
  site for the $3,000 MLL figure; the "$1,800 is soft, no time limit" details
  are corroborated by two independent third-party trackers but not directly
  quoted from Lucid's own help-center article~~ **RESOLVED 2026-08-27**:
  re-checked directly against Lucid's own help-center articles and the live
  dashboard — both facts confirmed exactly as stated, plus several
  previously-unaddressed items (overnight/weekend rule, news-trading
  stance, consistency rule, automated-trading permission, inactivity
  policy, and the $3,000 trail's lock-in point) are now confirmed too. Full
  detail in HYPOTHESIS.md §1.
- ~~The Verdict below (and §3's stop-loss rejection) describes the earlier,
  broader NQ/ES/YM no-stop mechanism only. §2.7's MES-only combined
  stop + time-exit result is a separate, later line of research that this
  file has not reconciled into a single updated recommendation — the two
  sections currently describe two different mechanisms without stating
  which one should actually be deployed.~~ **RECONCILED 2026-08-27:**

  Comparing the two lines of research directly (STOPLOSS_HYPOTHESIS.md's
  exact-dollar-corrected NQ/ES/MNQ/MES result vs. this section's MES-only
  combined price-stop + 90-min time-exit result):

  | | STOPLOSS_HYPOTHESIS.md | §2.7 (this section) |
  |---|---|---|
  | Instruments | NQ + ES pooled (reported as MNQ/MES micros) | MES only |
  | Stop mechanism | Opposite side of the opening range (varies per trade) | Fixed 99th-pct worst-case distance (~125 pts) |
  | Extra exit rule | None | + exit early if still losing after 90 min |
  | Slippage modeled? | **No** — assumes a perfect fill at the stop | **Yes** — 1-2 ticks on every exit, including the close |
  | MES survivability | 51.36% → 65.89% | 51.36% → 77.82% (perfect fill) → **64.29-71.60%** (realistic) |
  | MNQ survivability | 31.30% → 54.30% | not tested |

  **Agreement**: both independently found that giving MES an early-exit
  mechanism raises survival odds well above the plain hold-to-close baseline
  (51.4%), landing in roughly the same realistic 64-72% range despite using
  two different stop designs — two different mechanisms pointing the same
  direction is decent evidence the underlying effect is real, not an
  artifact of one parameter choice.

  **Resolution**: §2.7's combined price-stop + 90-min time-exit is the
  stronger-tested design of the two for MES — it already survived a
  realistic slippage haircut that STOPLOSS_HYPOTHESIS.md's simpler
  opposite-range stop never had applied (and slippage would only push that
  number down, not up). Treat §2.7's mechanism as the leading candidate for
  MES specifically, and STOPLOSS_HYPOTHESIS.md's version as superseded for
  MES — but **not** for MNQ, since §2.7 never tested MNQ at all; MNQ's
  54.30% figure is the only number on record for it, and is likely
  optimistic for the same untested-slippage reason MES's originally was.

  ~~**Still not a go-live decision** — three gaps remain before either
  mechanism ships: (1) §2.7's combined mechanism has never been tested on
  MNQ or NQ/ES, only MES; (2) neither line reran the entry-predicts-direction
  significance test after the sizing correction — the original mixed/
  inconclusive out-of-sample result (NQ helps slightly, ES hurts slightly)
  still stands untouched; (3) nobody has committed to shipping *one*
  mechanism — the live script still runs no-stop, with two different
  unreconciled stop-loss drafts sitting unused.~~

  **Partly superseded 2026-09-10.** Gap (3) is closed: one mechanism was
  committed to and is live. §2.7's combined price-stop + 90-min time exit runs
  on MES via `orb_long_ghost_DRAFT_mes_v2_accessible.pine` (testMode off since
  2026-09-09) on the real eval account. Verified end-to-end in Ghost the same
  day: the ticker's "Use Webhook SL/TP" is ON (so the script's ~125pt `sl`
  applies and the ticker card's "10 pts" is a *fallback* only), "No Take Profit
  (Let Runners Run)" is ON (so the card's "20 pts" is excluded and the right
  tail is uncapped, as the mechanism requires), and that day's trade exited via
  `time_exit_90min` as designed. The no-stop mechanism is no longer what runs.
  Gaps (1) and (2) remain open exactly as written — see §2.8 for what *was*
  measured on the MNQ question (co-movement only; the mechanism itself still
  has no MNQ test).

## Verdict (updated 2026-08-21 — supersedes the version below)

**promising_but_unproven, and narrower than previously stated.** The
underlying entry signal (§1) still holds up: NQ and ES clear their
pre-registered significance test in both the in-sample and out-of-sample
slices, with no decay, real costs barely denting it, and a broad-based edge
rather than a few lucky trades (§2.5). None of that changes here.

What changes is the sizing/survivability picture. The §2.6 correction above
shows the original "micro contracts make this comfortably survivable" claim
does not hold up under exact-dollar measurement — plain no-stop, hold-to-
close survivability for NQ, ES, MNQ, and MES all sit in the 31-51% range,
not the 89-99% previously reported. **No instrument, on the plain no-stop
mechanism, clears a bar anyone should call "comfortable."**

Separately, §2.7's later, MES-only test found that a real mechanism change —
a 99th-percentile price stop combined with a 90-minute underwater time exit
— meaningfully improves on that reconciled MES baseline: 51.4% (no-stop) →
77.8% (combined exit, ideal fills) → 64.3-71.6% (combined exit, realistic
1-2 tick slippage). That is the strongest, most rigorously-tested MES result
in this project to date, and every step of it used the same exact-dollar
method as the §2.6 correction, so it's a fair, like-for-like comparison.

**Two things this file does NOT have, and should not be read as having:**
- The combined stop + time-exit mechanism has only ever been tested on
  **MES**. It has not been run on NQ, ES, or MNQ — there is no evidence one
  way or the other for those instruments with this mechanism.
- §3's stop-loss test (single price stop, no time exit, tested on pooled
  NQ+ES, MNQ/MES-scaled) predates the 90-minute time-exit idea and is a
  different, narrower mechanism than §2.7's combined stop+time-exit — the
  two are not directly comparable. It **has now been re-run with the
  exact-dollar method** (2026-08-27, `stoploss_reconciliation.py`): the
  simple opposite-side-of-range stop alone improves survivability on both
  MNQ (31.30%→54.30%) and MES (51.36%→65.89%) — a reversal of the original
  "reject" verdict, which rested on the pre-correction sizing. It is still
  only a survivability re-measurement, not a fresh significance or
  out-of-sample test, and is not cleared for live use — see
  STOPLOSS_HYPOTHESIS.md's correction section for the full caveats.

**Net effect:** MES, using the price-stop + 90-min time-exit combination
(currently a reviewed draft — `orb_long_ghost_DRAFT_mes_v2.pine`, not live),
is the best-supported single recommendation this file can currently make —
better than the plain no-stop version of any instrument once measured
exactly, and better-tested than the alternative (it already survived a
realistic slippage haircut the alternative never had applied — see the §3
reconciliation, 2026-08-27). ~~NQ, ES, and MNQ have no equivalent tested
improvement~~ **correction (2026-08-27): MNQ does have a tested
improvement** — the simple opposite-range stop-loss (§3 /
STOPLOSS_HYPOTHESIS.md) raises its survivability from 31.30% to 54.30% — but
it is the weaker-tested of the two MES-side mechanisms (no slippage modeled
on the stop fill, and slippage would only push that number down), and it is
the *only* tested improvement for MNQ, not a second option to choose between.
NQ and ES genuinely have no equivalent tested improvement and, on the
numbers actually measured for them, should not be assumed "comfortable."
Not yet cleared to trade real money on any instrument — that remains a
separate, deliberate decision (see SETUP_GUIDE.md), not a research gap.

---

## Verdict (original, 2026-08-19 — see correction above)

**promising_but_unproven.** The long-side ("buy the breakout") mechanism on
NQ and ES cleared its pre-registered significance test on both the in-sample
and the one-time out-of-sample look, with no decay and real costs barely
denting it — a genuinely rare outcome in this project's track record. With
the corrected firm rules, it also comfortably survives the drawdown/ruin
check at conservative-to-moderate position sizing, and the outlier check
shows a broad-based edge (57% win rate, positive even after removing the
best 5% of trades) rather than a few lucky days. The one remaining gate — a
hard stop-loss — was tested and **rejected** (§3): it reduces survivability
against LucidPro's trailing drawdown rule, so the no-stop mechanism, exactly
as already built in `orb_long_ghost.pine`, is the version to run. No open
methodology items remain. Not yet cleared to trade real money — that is a
separate, deliberate decision (see SETUP_GUIDE.md), not a research gap.

*(This original verdict's "comfortably survives" claim and its recommendation
to run `orb_long_ghost.pine` as-is are superseded by the correction above —
kept here for the record, not as current guidance.)*
