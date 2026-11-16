# 2026-10-26: TradingView connector lost its authorisation, 15 trading days blind

**Status:** closed 2026-11-16.

## What happened
- **The connector dropped:** from Monday 26 Oct the TradingView MCP needed
  re-authorisation. Only the user can do that, in claude.ai connector
  settings.
- **The routines kept running, blind:** every 8:45 check logged "NO-GO,
  MCP down". Every 9:50 watch logged `MCP_DOWN` and sent a push. Every 4:15
  close reported that it could not run.
- **It lasted 15 trading days,** 26 Oct to 13 Nov. The connector was
  re-authorised on 16 Nov.
- **The 23 Oct close was also missed,** so the journal stopped at 22 Oct.

## Impact
- **No known trading impact:** the risk pause was in place and the MES v2
  alert was last seen inactive on 23 Oct.
- **That cannot be proven.** The MES v2 alert (5849779220) was deleted
  during the outage, and deleting an alert deletes its fire history.
- **A permanent gap in the journal:** 12 trading days, 23 Oct to 9 Nov.
  TradingView's 1-minute history only goes back about a week, so by 16 Nov
  it started on 10 Nov. Only 10 to 13 Nov could be backfilled.
- **Three weekly reviews had no market data.**
- **A live alert went unseen:** the user created alert 6073505338 on MNQ on
  15 Nov (D-019). No routine could have seen it while the connector was
  down, and the checks do not look for it by name either (G1.4).
- **`main` fell a month behind:** the state branch was not merged after
  15 Oct.

## How it was found
The routines reported it every day from 26 Oct. It was acted on when the
user asked for a diagnosis on 16 Nov.

## Root cause
- **Detection worked. Escalation did not.** The same push went out every
  morning for three weeks and became background noise.
- **One connector, no fallback** (G6.1). The failure mode is safe for
  trading, because unknown means NO-GO, but not for the records.
- **Nothing said how short the backfill window is.** Nobody knew that a
  week's delay makes the gap permanent.

## What we changed
- **Connector guide written:** `docs/TRADINGVIEW_MCP_GUIDE.md`. It says how
  to reconnect, and that it must be done the same day.
- **Backfilled 10 to 13 Nov** in `ops/journal.csv`, each row flagged
  `backfilled`.
- **Recorded the alert changes** in `ops/alert_actions.csv` and D-019.
- **Merged the state branch** into the working line, so the records are in
  one place again.

## Lessons
- A warning that repeats unchanged stops being read. After two days down,
  the message should say what is being lost and by when.
- Save the alert log before any alert is deleted.
- Merge the state branch to `main` every week, not only with the next PR.

## Open items
- **User:** decide D-020, how the routines and risk rules apply to the MNQ
  alert.
- **User:** decide whether to buy the 23 Oct to 9 Nov bars from Databento
  to fill the journal gap.
- **Claude, if approved:** escalate the outage message after two days
  (G6.3).

## Evidence
- `ops/golive_log.csv` and `ops/watch_log.csv`, 26 Oct to 13 Nov.
- `ops/weekly_reviews.md`, weeks of 26 Oct, 2 Nov and 9 Nov, and the
  16 Nov correction.
- `ops/journal.csv`, rows for 10 to 13 Nov.
- `ops/alert_actions.csv`, 15 and 16 Nov.
