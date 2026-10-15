# 2026-09-21: CME real-time data lapsed, every alert ~10 min late

**Status:** closed 2026-09-28 (probe fires on time again).

## What happened
- **The delay:** from the 21 Sep open, every TradingView alert fired about
  10 minutes after its signal bar closed. It hit both symbols (MES 1m, MNQ
  3m) and every script. Up to the 18 Sep close, alerts fired 0–1 min after
  the bar.
- **Where it sat:** inside TradingView, before the webhook. Ghost accepted
  every webhook at once (HTTP 200).

## Impact
- **21 Sep:** the "session close" exit fired at 4:10pm ET, after the
  regular session.
- **24 Sep:** the signal trade was −$67.50 and Lucid reported −$80. Delay
  and commissions cost about $10–20.
- **Tested pass rates no longer applied:** RESULTS.md §2.7 shows just 2
  ticks of adverse exit slippage cuts survival from 77.8% to 64.3%, and a
  10-min delay is far outside what was tested.
- **Trading paused** from 25 Sep ~9:47 ET.

## How it was found
By hand on 25 Sep, from the alert log: `fired_at` was about 600 s after the
`time` the script stamps in each message. The MES chart confirmed it with
TradingView's orange "D" (delayed data) badge, and the newest bar was about
10 min behind the clock.

## Root cause
The account's real-time CME market data subscription lapsed over the 19–20
Sep weekend. Without it, TradingView serves CME data 10 min late, and
server-side alerts see the same delayed bars. The billing cause was never
confirmed: there was no TradingView billing email in Gmail.

## What we changed
- Renewed the data on 25 Sep (non-professional CME, about $7/month).
- **Stale-data guard in the script** (PR #5): it blocks an entry whose bar
  is more than 90 s late. Exits are never blocked.
- **Daily 8:45 go/no-go with a latency gate** (PR #6), made more robust in
  PR #15 (probe lag plus MES bar freshness).
- **4:15 close routine** (PR #7): flags late fires every day.

## Lessons
- **Lag has to be measured.** It used to be visible only by reading the
  alert log by hand. Now it's measured every morning and on every trade.
- **Mid-session alert edits are dangerous.** The script can take a late
  entry (18 Sep entered at 3:49pm ET), and saving an edit can switch a
  paused alert back on. This became a standing rule in SETUP_GUIDE.md.

## Open items
None. Probe expiry is tracked in PRODUCTION_READINESS.md (G3.1).

## Evidence
- `ops/journal.csv` rows 2026-09-21 to 2026-09-28 (`late_fire`, 600 s lags).
- The archived guide, "Current live state and open issue (2026-09-25)".
- PRs #1–#5.
