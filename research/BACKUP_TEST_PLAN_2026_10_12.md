# Backup Test Plan: Nasdaq Opening-Range Breakout, Long Side (12 Oct 2026)

Status: PLAN ONLY, written 12 Oct 2026 at the user's request. DRAFT until the
user says yes to Section 9. Nothing live, nothing in TradingView, Ghost, alerts
or Lucid is changed by this document. No test has been run for it. The user
retired the MES v2 ORB on 12 Oct after a four-reviewer review; this plan is the
search for a sound replacement on thin resources.

## 1. The question

Does the plain long-side opening-range breakout on Nasdaq keep its edge on days
the original test never saw, and is it safe and cheap enough to be a backup
for the 30 Oct review? The answer may be no. A no is a good outcome, because it
means we spend nothing more.

## 2. Why this candidate, and why it is not a diversifier

- It is the only candidate on the bench with a pre-registered test that passed
  out of sample. In `orb_breakout/RESULTS.md` section 1, the long side on NQ
  gave +0.167R in sample (p 0.0014) and +0.179R on the held-out slice (p
  0.0068), with ES agreeing. YM agreed in sign but was not significant.
- The MES v2 layer added on top (125-point stop, 90-minute exit) was the weak
  part. The statistics reviewer found it was tuned on all five years, had no
  held-out slice, and the edge was fading (+$15 per trade in the first half,
  +$3 in the second).
- **It is the same entry signal as the retired MES strategy.** On the signal
  alone, NQ and MES move together (r = 0.963, RESULTS.md section 2.8). So this
  is the same bet on a different instrument, NOT a second, independent idea.
  If the entry signal has faded since the held-out slice ended, this candidate
  fails for the same reason the MES strategy did.
- It competes with the Nasdaq noise-area test for the single Nasdaq slot. The
  approved 30 Oct rule C4 says a Nasdaq strategy runs ALONE, one micro
  contract. Two Nasdaq strategies live at once could also trade opposite ways
  on the same contract, which Lucid's hedging rule bars.

## 3. Ground rules (already approved, not changed here)

- Stay at the approved sizing; about $670 spending cap; reset once then stop.
- No same-day changes after a loss. No strategy hopping without good evidence.
- Nothing goes live without the user's explicit yes on the day.
- Do not tune. Do not re-run dropped ideas (`BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`).
- The cap of three active bench candidates (`BENCH_PLAN_2026_10_09.md`) holds.
  With this plan, two are active: the noise-area test and this one.

## 4. Frozen rules (set now, before any new look; no new parameters)

Entry, exactly as pre-registered in `orb_breakout/HYPOTHESIS.md` section 3:
- Opening range = high and low of the 1-minute bars from 09:30 to 09:44:59
  New York time. Real US daylight-saving handling, not a fixed offset.
- First 1-minute bar from 09:45 whose CLOSE is above the range high. One entry
  per day. Long side only (the short side was rejected).
- Instrument: Nasdaq (NQ for research, MNQ for any paper or live test).

Two exit variants, both taken unchanged from work already done. Nothing new is
invented here:
- **Variant A, plain:** hold to the 16:00 New York close. No stop. This is the
  mechanism the original significance test measured.
- **Variant B, range stop:** stop at the opposite side of the opening range,
  as in `orb_long_ghost_DRAFT_mnq_orwidth_stop.pine` and
  `STOPLOSS_HYPOTHESIS.md`. Its earlier survivability figure (31% to 54%) had
  no slippage applied, so it is treated as optimistic.

Neither variant uses the 125-point stop, the 90-minute rule or the 60-point
stop. Those belong to the retired MES strategy.

Known defect to avoid from day one (code reviewer, 12 Oct): the early-close
flatten only fires when a new price bar arrives, so on half-days (about 13:00
New York) a position could sit open through the halt. Any live or paper script
must flatten by a clock time on known half-days, or the plan skips those days.

## 5. Phase 1: read-only checks on data already on disk (free, no new tests)

These describe the old data. They do NOT count as passing any bar.

1. **Reconcile the two edge figures.** The pipeline reviewer quoted +1.3 points
   per trade (996 trades, t = 0.16) and the statistics reviewer +$9.10 (662
   MES trades). Find which data window and rule each one used, and write down
   which applies to which strategy.
2. **Fade check for the plain NQ entry.** Report mean R by calendar year for
   the original long-side entry on NQ and ES, from the existing files only.
   Flag it as a description. If the most recent year is at or below zero, say
   so plainly; that moves this candidate down the list.
3. **Count usable data after the held-out cut.** The data ends 18 Aug 2026.
   (Corrected after Phase 1: the held-out slice runs from 14 Feb 2025 to
   18 Aug 2026, about 18 months, and the original test already looked at all
   of it. The only truly unseen days are those after 18 Aug 2026.)

## 5b. Phase 1 results (run 12 Oct 2026, read-only)

Run on the existing NQ and ES files with the original `orb_test.py` signal and
real free-tier costs. Nothing was edited. These describe old data and do NOT
count as passing any bar.

**Check 1: the two edge figures.** They belong to different trade sets of the
retired MES rule, not to this candidate.
- +$9.10 per trade (662 trades, 44% wins): the old backtest. It skips days
  where a short broke out first and checks the 90-minute exit only once.
- +$7.3 per trade overall (996 trades, 30% wins): the rule the live script
  actually runs. In sample +$9.9 (t 2.3); after 14 Feb 2025 only +$1.3 (t
  0.16). By year it fades from +$19.5 in 2021 to +$3.0 in 2025 and -$1.6 in
  2026. Source: 2 Oct audit (`~/qc-demo-test/audit-2026-10-02`).
- The 662 also matches the ES long-trade count in the plain test below, so the
  old figure came from that same trade list.

**Check 2: fade check, plain long ORB held to the close (mean R per trade after
cost).**

| Year | NQ trades | NQ mean R | ES trades | ES mean R |
|---|---|---|---|---|
| 2021 (from Aug) | 54 | +0.22 | 56 | +0.10 |
| 2022 | 124 | +0.10 | 122 | +0.16 |
| 2023 | 142 | +0.16 | 138 | +0.18 |
| 2024 | 118 | +0.22 | 118 | +0.22 |
| 2025 | 129 | +0.19 | 137 | +0.17 |
| 2026 (to 18 Aug) | 84 | +0.17 | 91 | +0.20 |

- NQ: +0.17R overall (651 trades, t 4.1). Last 12 months +0.16R (t 1.9). Last
  80 trades +0.20R. ES: +0.18R overall (662 trades, t 4.4). Last 12 months
  +0.18R (t 2.2).
- **No fade.** Every year is positive on both instruments and the latest year
  is in line with the average. The fade the council found belongs to the MES
  rule's 90-minute exit layer, not to the plain entry held to the close.
  This matches the 2 Oct no-time-exit test (+$10.65 per trade against +$7.34).
- It is still NOT proof. All of it is old data that has been looked at, a
  single year's error bar is about ±0.10R, and the single-day dominance seen
  in the no-time-exit test could affect this too.

**Check 3: unseen data.** None exists on disk beyond 18 Aug 2026, so about
seven weeks (roughly 25 trades) are unseen. The forward test starts from that
point.

**What Phase 1 did not settle.**
- Money: the plain version scored 31% (MNQ) and 51% (MES) pass odds, and the
  opposite-range-stop version scored 54% (MNQ) without slippage. Even a real
  edge gives roughly a one-in-two to one-in-three chance per attempt.
- The earlier survivability sweep predates the later tests and should be
  re-checked before any money decision.
- Dollar size at 1 micro is small: about $14 per trade, per RESULTS.md 2.6.
  At about 130 trades a year that is roughly $1,800 a year before the 90/10
  split.

## 6. Phase 2: forward paper test on new days only

- Run Variant A and Variant B as free demo tests (Ghost DEMO slot and a
  TradingView alert, or a manual log) on days after the plan start date. First
  confirm slot limits and that this adds no cost. If a second demo slot
  needs a paid plan, stop and ask.
- Check first whether the free MNQ ORB demo set up on 23 Sep (`~/qc-demo-test`)
  is still running; if so it may be reusable. Do not reuse its results as
  evidence, because its rules were not frozen first.
- Log per trade: date, entry, exit, result in points and dollars at 1 micro.
- Machinery checks, same as the noise-area test: signals match an independent
  checker, zero real orders, flat by the close, half-days handled.

## 7. Decision bars (set before any result exists)

How much evidence is possible: the original test showed about 0.17R per trade
with a spread of about 1.04R. Detecting that takes roughly 330 trades. At about
130 trades a year, a forward test cannot confirm an edge inside the 30 Oct
window or for many months after. So the forward test can only REJECT a
collapse, never confirm a win. The bars are written that way.

- **Drop now:** Phase 1 shows the most recent year at or below zero, or the
  forward paper test places a real order, or two signal mismatches.
- **Keep running (not "go live"):** at 20 forward trades and again at 40, mean
  result per trade is not below -0.10R, no machinery fault, worst day inside
  what the original data showed.
- **Drop:** at 40 forward trades, mean result below -0.10R.
- **Never a pass on its own:** a good run of 20 to 40 trades earns more paper
  time, not live money.
- **Promotion to live** needs every item in the bench-plan promotion gate
  (`BENCH_PLAN_2026_10_09.md` section 7), plus: runs alone, noise-area is off
  or has failed, and the user's explicit yes on the day.

## 8. Costs and limits

- Phase 1: nothing. Phase 2: nothing if a free demo slot exists.
- Optional, NOT proposed without a quote and a yes: buying older price history
  (before 2021) would double the sample and give a truly untouched older slice.
  Get a price first, and keep it inside the $670 cap.
- Ghost costs about $69 on 23 Oct and is kept through 30 Oct for the
  noise-area test either way.

## 9. How this fits the 30 Oct review

- If the noise-area test passes: it goes live alone as already approved. This
  candidate stays on the bench as paper only.
- If the noise-area test fails: this candidate is NOT automatically next. At
  30 Oct it must already show Phase 1 plus a clean forward log. The default
  after a noise-area fail stays wind-down. A clean log earns a user decision on
  continuing paper testing, not a live switch.
- Horner H1 stays frozen until after 30 Oct, as already agreed.

## 10. Decisions needed from the user

1. Approve this plan as the working copy (committing it is a separate yes).
2. Yes or no to running Phase 1 (read-only, free, on existing files).
3. Later, before Phase 2: yes or no to adding paper alerts, after the slot and
   cost check.

## 11. What this plan does not do

- It does not restart, edit or delete the paused MES alert or Ghost ticker.
- It does not claim an edge. The honest expectation is low to moderate: a real
  past result, a shared entry signal with the retired strategy, and no way to
  confirm it quickly.
