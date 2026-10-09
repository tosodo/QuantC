# Bench Plan: Having Something to Fall Back On (9 Oct 2026)

Status: PLAN ONLY. Written 9 Oct 2026 at the user's request. Nothing live,
nothing in TradingView, Ghost, alerts or Lucid is changed by this document.
Statuses below come from the research files read on 9 Oct; anything not
re-checked is marked. APPROVED by the user on 9 Oct 2026: the setback
definition (Section 6), the promotion gate (Section 7), the order and cap of
three (Section 5), and the Lucid rules check (Section 3).

## 1. The question

If the live opening-range breakout (ORB, MES v2, 2 contracts) hits a setback,
what is ready to take over, and how do we know it is good enough, without
hopping between strategies on a bad week?

Short answer: build a **bench** of candidates tested at no risk, with a written
promotion rule, and a written definition of "setback", agreed in advance.

## 2. Ground rules (already approved, not changed here)

- Stay at 2 contracts; no changes on the day of a loss; reset once then stop;
  about $670 spending cap; 40 / 100-trade checkpoints (29 Sep operating rules).
- No strategy hopping without good evidence; shifting WITH evidence is welcome.
- The approved 30 Oct rules (`noise_area/REVIEW_30OCT_RULES.md`) say the
  Nasdaq noise-area strategy, if adopted, runs ALONE: one micro Nasdaq
  contract, MES alert off, "never both at once".
- Do not re-run dropped ideas (`BACKUP_STRATEGY_OUTCOMES_2026_10_05.md`).
- A backup must trade near-daily to be judged inside a 30-day window.

## 3. Why "concurrent" should mean paper, not live (for now)

- One Lucid account has one trailing floor. A second live strategy shares the
  same cushion (about $2,564 per the 5 Oct file; re-check the live figure).
  It adds risk to the same account; it is not a safety net.
- The approved C4 rule already says the noise-area strategy runs alone.
- Two strategies that trade the same hours in opposite directions on one
  contract cancel each other out.
- Nothing on the bench has yet cleared a test. Live money should not be the
  first test.
- **Lucid rules check (9 Oct, from Lucid's own help-centre article "Prohibited
  hedging", support.lucidtrading.com, article 11404734; re-read it before any
  live change):**
  - Different contracts in the SAME account may be long and short at once.
  - You cannot be long and short the same contract, in the same or separate
    accounts.
  - You cannot hold opposite positions in correlated contracts across
    SEPARATE accounts (their example: long ES in one account, short NQ in
    another). This covers accounts held by the same person.
  - Penalty: the flagged accounts are reset to the prior day's balance (the
    remaining drawdown is NOT restored); repeat offences breach all involved
    accounts and can mean a permanent ban.
  - Consequence for us: a second evaluation account running an opposite-way
    strategy on Nasdaq / S&P (for example the Horner sweep-and-reverse
    against the ORB breakout) would very likely count as hedging. Same-
    direction strategies, or different, uncorrelated markets, are the safer
    shape. Third-party sites agree on the hedging ban but disagree on other
    numbers; I found no Lucid rule specifically about running several
    strategies. Ask Lucid support in writing before any live concurrency.
- Another evaluation account is an option only if a candidate clears the
  whole gate below AND passes the hedging check above; it costs another
  one-time fee (about $307 per my notes) and is NOT recommended before then.

So "concurrent" here means: run candidates in parallel as read-only tests and
paper (demo) forward tests, and keep ONE strategy live.

## 4. The bench (candidates, as of 9 Oct)

| # | Candidate | Status | Hours / market | Overlap with ORB | Trust | Next step |
|---|---|---|---|---|---|---|
| 1 | Nasdaq noise-area (`noise_area/`) | **Paper test running** (about 19 sessions, 5-30 Oct) | Nasdaq, intraday | Same market; run ALONE if adopted | Backtest-based; 4 weeks cannot prove profit | 30 Oct review, Parts A-C |
| 2 | First-half-hour predicts last-half-hour (`intraday_momentum_last_half_hour/`) | **DROPPED 9 Oct**: in-sample screen run once, no predictor cleared the bar; two pointed the wrong way, the nearest (P2) missed at p about 0.07-0.09 | Nasdaq / S&P, trade at 15:30-16:00 | **None**: different hours | Was medium; effect not present after publication | None. Do not re-run. Held-out slice unused. |
| 3 | Hour-of-day bias (`hour_of_day_bias/`) | **DROPPED 9 Oct**: in-sample screen run once, no window cleared the bar (best p about 0.02 at 23:00, chance level for 22 windows) | Nasdaq / S&P, hours-long holds | Partly overlaps | Was low; nothing found | None. Do not re-run. Held-out slice unused. |
| 4 | Horner sweep-and-reverse, H1 (`horner_channel/`) | Plan FINAL and frozen (9 Oct); not run | Nasdaq / S&P, 09:30-12:00 | **Same hours, opposite direction**: a replacement, not a partner | Low | Run only after 30 Oct and a separate yes |
| 5 | MCL oil breakout (`mcl_oil_breakout/`) | Plan only (5 Oct); no oil intraday data inspected | Oil; different market | Low (daily co-movement about -0.05) | Low; oil is event-driven | Data check; re-verify Lucid MCL approval |
| 6 | Gold fix breakout (`gold_fix_breakout/`) | **Parked** | Gold, scheduled auctions | Low | Unknown | Needs a data purchase and a Lucid events check |
| 7 | London-open breakout | **Parked (maybe)** | London morning | Different hours | Weak | Forward paper test on new days only (out-of-sample data already used once) |

Not on the bench (do not re-run): index mean-reversion, Nasdaq vs S&P relative
value, 9:30 session-open, overnight-range filter, European-open drift. The
VWAP-fade is uncorrelated with the ORB but its draft rule loses money; do not
tune it on this data.

The Horner H2-H5 tests (30-minute range, retest entry, previous-close and
7am-VWAP filters) are variants of the LIVE ORB, not fall-backs, so they sit
outside the bench.

## 5. Suggested order

1. Keep the noise-area paper test running (already the designated alternative
   at the 30 Oct review).
2. Candidate 2 was the first new screen: run 9 Oct and DROPPED (see table).
   The next candidate in order moves up.
3. Candidate 3: run 9 Oct and DROPPED (see table).
4. Candidate 4 as the replacement idea if the ORB fails at a checkpoint;
   do not run it beside the ORB.
5. Candidates 5-7 stay parked until 1-4 resolve.

Cap: at most **three** active candidates at a time (limits both paper-trading
capacity and the number of lucky results we can fool ourselves with). Each
plan keeps its own multiple-testing bar; running more screens raises the
overall chance of a false winner, so a pass is treated as "earns a paper
test", never "go live".

## 6. What counts as a setback (APPROVED 9 Oct)

A setback triggers a REVIEW, never an automatic switch:
- S1: the Lucid floor is hit (the one allowed reset is used).
- S2: the live ORB fails the 40- or 100-trade checkpoint set in the 29 Sep
  operating rules.
- S3: the same pipeline fault causes a missed trade more than once in a
  month (4 of 5 missed trades in the 2 Oct audit were pipeline failures).
- S4: the 30 Oct review outcome.

A losing week, or a loss on its own, is NOT a setback.

## 7. Promotion gate for any bench candidate (APPROVED 9 Oct; mirrors 30 Oct Parts A-C)

All must hold before the user is even asked to switch anything live:
1. Passed its own pre-registered screen (in-sample bar, held-out once).
2. Forward paper test of at least about 19 sessions with no machinery faults
   (signals match the checker, zero real orders, flat by the close).
3. Behaviour in line with its backtest (trade frequency, worst day).
4. Daily-result correlation with the ORB measured (the VWAP-fade was
   r = -0.161 for comparison); same-hour overlap flagged.
5. Worst-case loss at the chosen size fits inside the cushion on the day.
6. Runs ALONE, or is shown to be safe alongside ORB under Lucid's rules.
7. The user's explicit yes on the day.

## 8. Costs and capacity (to confirm)
- Ghost bills about $69 on the 23rd; every paper ticker uses a Ghost DEMO
  slot and a TradingView alert. Confirm limits before adding a second paper
  test. Stay inside the $670 spending cap.
- Read-only screens on files already on disk cost nothing.

## 9. Do not
- Switch because of one bad week.
- Tune a failed idea.
- Pay for Horner's or QuantCrawler's products.
- Run the CRT idea and the ORB on the same contract at once.

## 10. Decisions
1. Setback definition (Section 6): APPROVED 9 Oct.
2. Promotion gate (Section 7): APPROVED 9 Oct.
3. Order and cap of three (Section 5): APPROVED 9 Oct.
4. Lucid rules check: DONE 9 Oct (Section 3). Still open: written
   confirmation from Lucid support on running several strategies, if it ever
   matters.
