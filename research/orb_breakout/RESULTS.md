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

  **Still not a go-live decision** — three gaps remain before either
  mechanism ships: (1) §2.7's combined mechanism has never been tested on
  MNQ or NQ/ES, only MES; (2) neither line reran the entry-predicts-direction
  significance test after the sizing correction — the original mixed/
  inconclusive out-of-sample result (NQ helps slightly, ES hurts slightly)
  still stands untouched; (3) nobody has committed to shipping *one*
  mechanism — the live script still runs no-stop, with two different
  unreconciled stop-loss drafts sitting unused.

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
