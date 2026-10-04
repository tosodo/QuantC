# 30 Oct review: pass/fail rules for the Nasdaq paper test

**Status: APPROVED by the user on 4 Oct 2026** (written the same day, before any paper results existed). These rules were set *before* any paper results exist, on purpose, so the results can't bend the rules. Change them only for a reason recorded here, and never after looking at paper results.

**Review date:** Friday 30 Oct 2026, after the US close. The paper test covers about 19 trading sessions (5–30 Oct).

**Numbers used below** come from `~/qc-demo-test/research-2026-10-03/review_thresholds.py` and `wiggle_test.py`: 5 years of NQ, 1 micro contract, today's prices, costs included.

---

## What 4 weeks can and can't tell us
- **Can tell us:** whether the signals reach Ghost correctly and on time, and whether the strategy behaves like the backtest (how often it trades, the size of its days).
- **Can't tell us:** whether it really makes money. Normal 4-week results range from **about −$1,300 to +$3,250**, so a losing month is **not** a failure and a winning month is **not** proof.
- **So the go-live decision rests mainly on the backtest evidence plus the costs, not on the 4-week P&L.**

---

## Part A: Does the machinery work? (all must pass)

| # | Rule | Pass if |
|---|---|---|
| A1 | Every signal the checker (`paper_check.py yahoo`) expects shows up in Ghost's log as a test signal | **No more than 1** missed or extra signal over the whole period, and any mismatch is explained by a price within a few points of the band. 2 or more = fail. |
| A2 | Every Ghost record of this ticker says "Test signal — not executed", on the practice account only | **Zero** real orders, anywhere. Any real order = fail, and stop everything at once. |
| A3 | Every paper position is flat by the 4pm New York close | Every day. |
| A4 | The TradingView alert stays active and the webhook points to the test ticker (address starts `a8e5bab1`) | The whole period. If it was off for some days, those days don't count. If fewer than 15 usable sessions remain, extend the test. |

**If any A rule fails:** don't go live. Fix the fault and restart the 4-week clock.

---

## Part B: Does it behave like the backtest? (all must pass)

| # | Rule | Backtest says (19 sessions) | Pass if |
|---|---|---|---|
| B1 | Number of days it trades | usually 10–13, rarely below 7 or above 15 | **7 to 15** trade days |
| B2 | Paper result over the period | middle 50%: −$570 to +$760; worst 5%: below about −$1,300 | **Not below −$1,300** |
| B3 | Worst single day | worst in 5 years: −$1,323 | **No day worse than −$1,400** (a little room for slippage) |
| B4 | Matches the checker on price | within about 2 ticks | Average gap of 2 points or less |

**If any B rule fails:** the live market isn't behaving like the backtest. Drop the idea; don't tune it.

---

## Part C: Is it worth switching the Lucid account to it? (decided only if A and B pass)

Even if it works, it has to be **worth it** for your account. What the evidence says at 1 micro contract, from your current position (balance $99,742, floor $97,178):

| If the true edge is… | Finish this attempt | With your one allowed reset | Typical time |
|---|---|---|---|
| +$40/day (the paper's lucky setting) | 56% | 82% | ~7 months |
| **+$20/day (realistic, after the wiggle test)** | **35%** | **60%** | ~7 months |
| +$10/day | 25% | 46% | ~7 months |
| $0 (no edge at all) | 18% | 34% | ~6 months |

For comparison, the **current MES rule on recent data: 0–14%**.

**Proposed rule:** switch only if **all** of these hold:
- **C1:** A and B both passed.
- **C2:** You accept the realistic case: about **1 in 3** to finish this attempt, about **3 in 5** with one reset, and roughly 7 months of Ghost fees (about $480, plus $180 for a reset if needed).
- **C3:** The account still has at least **$2,000 above the floor** on 30 Oct. The paper test doesn't touch the account, but the inactivity trade does, so this checks the room left.
- **C4:** It runs **alone**: 1 micro Nasdaq contract, MES alert off. Never both at once.

**If you switch:** your existing operating rules still apply. Reset once after a floor hit, a second hit means stop, no changes on the day of a loss, and the $670 spending cap stays.

**If you don't switch:** wind down. Cancel Ghost (about $69 a month) and stop all spending. Keep the Lucid account only while it costs nothing.

---

## Decision table for 30 Oct

| A (machinery) | B (behaviour) | C (worth it) | Decision |
|---|---|---|---|
| Fail | — | — | **Don't go live.** Fix, then a new 4-week paper test, or wind down if you'd rather stop. |
| Pass | Fail | — | **Drop the idea. Wind down.** |
| Pass | Pass | No | **Wind down.** The idea may be real, but the account can't carry it at an acceptable cost. |
| Pass | Pass | Yes | **Switch the Lucid account to the Nasdaq rule at 1 micro contract.** Needs your explicit yes on the day. |

---

## Housekeeping (not pass/fail)
- **Inactivity:** the last trade was 2 Oct, so the 30-day deadline is about 1 Nov, and **Fri 30 Oct is the last trading day**. You agreed (4 Oct) to place one small manual trade between **26 and 29 Oct**. A reminder is scheduled for Mon 26 Oct, 9am.
- **The current MES alert** was paused on 4 Oct 2026 (user approved). The QC Trend test alerts were stopped the same day. MES stays paused unless 30 Oct decides otherwise.
- **The MES alert expires on TradingView on 25 Nov.** Renew it only if MES is kept.
