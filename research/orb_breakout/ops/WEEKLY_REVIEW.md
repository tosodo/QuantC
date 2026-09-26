# Weekly review: MES v2 ORB

Runs every **Friday at 4:40 ET**, after the 4:15 close routine, as a
Claude routine. It is Phase 3 of the 2026-09-26 council review. It is
read-only: it changes no alert, rule or setting. It **proposes** changes;
the user decides.

First run `git pull origin claude/beautiful-cray-9vkxjd`. The journal and
logs live there (see `RISK_RULES.md`).

## 1. The week in numbers

From `ops/journal.csv`, for Mon-Fri of this week:

- **Days:** live, shadow, stale-skip, no-breakout, missed.
- **Per trade:** entry and exit reason, signal P&L, and Lucid P&L where it
  is known.
- **Totals:** signal P&L for all entries; live P&L (Lucid where known,
  otherwise estimated).
- **Execution:** average `buy_lag_s` and `exit_lag_s`, average `slippage`,
  and every `flags` entry.
- **Down-break-first entries:** how many, and their P&L. These days are
  untested in the original research; see Phase 3 item 1.

From `ops/golive_log.csv`: count the GO and NO-GO days and give the reasons
for each NO-GO. Give the median probe lag for each day.

Run `python3 research/orb_breakout/ops/risk_state.py` and report:
- the buffer, and whether it is estimated
- consecutive stops
- week P&L
- any rule tripped or paused this week

## 2. Against expectations

Compare with what the backtest leads us to expect:
- about **2.6 trades a week**
- about **$11 a trade** at signal prices before costs
- most losing trades cut by the 90-min exit, at a few points each; full
  stops are rare

One week is noise. Say so, and don't draw conclusions from it. Once 4 or
more weeks of `live` rows exist, also give the running totals since
2026-09-28:
- trades
- win rate
- average signal P&L
- average slippage

Compare them with `phase3_report.md`, if it has been committed.

## 3. Open items

List what is still waiting on the user:
- the Phase 1 D actions (Ghost SL/TP toggles and flat-account exit
  handling, Tradovate fills and commission, data renewal confirmed, alert
  redeploy)
- any live day with a blank `lucid_pnl`
- whether a newer Lucid balance is needed in `account.csv` (older than 2
  weeks)
- the alert expiry
- a missing or unrun `phase3_report.md`

## 4. Write and report

Append a dated section to `research/orb_breakout/ops/weekly_reviews.md`,
newest at the bottom, keeping it short. Commit and push to the working
branch. Then send the user a summary of at most 8 lines:
- the week's P&L
- anything abnormal
- the open items
- at most **one** proposed change, with its evidence

Never propose a new filter or parameter from a single week's results. A
change to the strategy needs a backtest first (Phase 3 policy: no
untested rules).
