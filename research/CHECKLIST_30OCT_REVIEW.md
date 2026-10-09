# 30 Oct 2026 Review: Working Checklist

Status: DRAFT, written 9 Oct 2026. A checklist only. It does not change any
approved rule. The pass/fail rules live in `noise_area/REVIEW_30OCT_RULES.md`
(approved 4 Oct) and are not repeated in full here. Nothing on this list is
done without your explicit yes at the time.

## 1. Before the review (dates)

| When | Task | Needs your yes? |
|---|---|---|
| Ongoing | Paper test keeps running (alert active, webhook ticker starts `a8e5bab1`) | No change |
| Fri 23 Oct | Ghost bills about $69. Confirm the bill is expected and inside the $670 cap | You decide whether to pay |
| Mon 26 Oct, 9am | Inactivity-trade reminder fires | Reminder only |
| Tue 27 Oct (DECIDED 9 Oct; 28-29 Oct are spare days) | ONE small manual trade to avoid the 30-day inactivity reset (agreed 4 Oct; last trade was 2 Oct, deadline about 1 Nov) | Yes on the day; check the Lucid rules article first |
| Fri 30 Oct | Last trading day for inactivity purposes. Review after the US close | Yes for any decision |

## 2. What I gather on 30 Oct (read-only)

1. Run the checker (`paper_check.py yahoo`) for 5-30 Oct and compare with the Ghost log.
2. Count: missed or extra signals (A1), any real order (A2), days flat by 4pm (A3), days the alert was off (A4).
3. Paper result for the period, number of trade days, worst day, average price gap (B1-B4).
4. Account balance and distance above the floor from the Lucid dashboard (C3 needs at least $2,000).
5. Check the 5-30 Oct result against the normal range (about -$1,300 to +$3,250); a loss inside it is not a failure.
6. Report A, B, C as pass or fail in a table, using the approved decision table.

## 3. Decision table (from the approved rules)

- A fails: do not go live; fix and restart the 4-week clock, or wind down.
- A passes, B fails: drop the idea and wind down.
- A and B pass, C fails: wind down.
- A, B and C pass: switch the Lucid account to the Nasdaq rule at 1 micro contract, alone, MES alert off. Your explicit yes on the day.

## 3b. Extension limit (added 9 Oct 2026, before any results exist)

The test is NOT extended to keep hunting for an edge. At most ONE extra test
period is allowed, and only for one of these reasons:
- A machinery fault (Part A fails): fix it and restart the 4-week clock once.
- Too few usable sessions (fewer than 15, for example the alert was off): extend until there are enough.

If the strategy simply does not behave like the backtest (Part B fails), or is
not worth it for the account (Part C fails), the default is to wind down. A
second extra period, or any extension chosen after seeing the P&L, needs a new
written reason and your explicit yes. Reasons: eight ideas have failed their
screens, spending is capped at about $670, and Ghost costs about $69 a month.

## 4. Items added since 4 Oct (for you to rule on; not pass/fail)

1. **60-point stop on the live ORB** (agenda item from the 2 Oct audit). Only relevant if MES is kept; do not change before this review.
2. **Bench status (9 Oct).** Two screens run and dropped (last-half-hour momentum, hour-of-day). Nothing else on the bench is ready, so if the noise-area test fails, there is currently no tested fall-back. Wind-down is the default.
3. **Horner tests (H1-H5).** Frozen and not run. They may only start after this review and with a separate yes. Honest expectation: low.
4. **Lucid support reply.** Awaiting a human answer on multiple strategies and hedging. If it has arrived, add it to the bench plan with its source before the review. Lucid's own help article bars opposite positions in related contracts across separate accounts.
5. **Running two strategies at once.** The approved C4 rule says the Nasdaq strategy runs alone. Keep it that way unless Lucid confirms otherwise in writing.
6. **MES alert** is paused. It expires on TradingView on 25 Nov; renew only if MES is kept.

## 5. If you switch (only after a yes)

1. Confirm the live config matches the tested mechanism (ticker, size 1 micro, flat by close).
2. Keep MES alert off; update the daily checklist and memory notes.
3. Existing operating rules still apply: reset once then stop, no changes on the day of a loss, $670 cap, 40 and 100-trade checkpoints.

## 6. If you wind down (only after a yes)

1. Cancel Ghost (about $69 a month) and stop all spending.
2. Keep the Lucid account only while it costs nothing.
3. Stop the paper alert and webhook; archive the research folders.

## 7. Decisions I need from you before 30 Oct

1. Do you want this checklist saved as-is as the working copy? (Committing and pushing is a separate yes.)
2. Inactivity trade date: DECIDED 9 Oct, Tuesday 27 Oct.
