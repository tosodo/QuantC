# Setup guide: TradingView → QuantCrawler Ghost → Tradovate (MES v2)

This is a **live document**: it describes the setup as it is now, and it's
edited in place when that changes. It holds no history. How the setup was
first built, the v1 script, and every past status update are frozen in
[`archive/…/SETUP_GUIDE_2026-08-27_to_2026-10-15.md`](../../archive/research/orb_breakout/SETUP_GUIDE_2026-08-27_to_2026-10-15.md).
What went wrong and what it taught us is in [`docs/incidents/`](../../docs/incidents/).

## Current state (checked 2026-10-15)

- **Account:** Lucid LucidPro $100K evaluation on Tradovate account
  LTE10089070250001. It's **simulated**: what's at risk is the evaluation
  fee, not trading capital.
- **Trading:** paused by risk rule R5 since 30 Sep (`ops/RISK_PAUSE`). It
  resumes only when you say "resume" (`ops/RISK_RULES.md`).
- **What blocks going live again:** the blocking rows in
  [`ops/PRODUCTION_READINESS.md`](ops/PRODUCTION_READINESS.md).

**TradingView alerts**

| alert | id | symbol | state |
|---|---|---|---|
| QuantC ORB Long MES v2 (validated) - Ghost (Accessible) | 5571966155 | MES1! 1m | **Inactive. Must be replaced, not restarted:** it's the 9 Sep build with no stale-data guard and qty input 2. The 8:45 check fails it. Expires 25 Nov. |
| QC Trend DEMO test BUY / SELL (dry run) | 5662901850 / 5662914432 | MNQ1! 3m | Latency probes, `"test":true` so no orders. Show active but **silent since 2 Oct**: recreate them. **Expire 21 Oct.** |
| QuantC Noise-Area MNQ - PAPER TEST ONLY | 5760603790 | MNQ1! 30m | Active, `"test":true`, paper only. Expires 2 Dec. |
| v1 "Ghost alerts" (MES and MNQ) and the MNQ OR-width-stop draft | 5461765534, 5490124255, 5478843448 | 1m | Inactive and expired. MNQ isn't traded. |

## The live script

[`orb_long_mes_v2.pine`](orb_long_mes_v2.pine). Its indicator name is
"QuantC ORB Long MES v2 (validated) - Ghost (Accessible)", and the routines
find the alert by that name. It runs on **MES1!, 1-minute** only: any other
symbol or timeframe is a hard gate, and no signal fires.

- **Range:** 9:30–9:44 ET. **Entry:** the first 1m close above the range
  high, from 9:45. Long only: the short side was tested and rejected
  (`RESULTS.md` §1).
- **Stop:** a broker stop (`sl`) 125 pts ($625) below entry.
- **90-min exit:** at 90 minutes, and on every bar after, exit if close ≤
  entry.
- **Close:** exits on the 15:59 bar, with a catch-all flatten on half-days.
- **Stale-data guard:** no buy if the breakout bar is more than 90 s late;
  it stands down for the day. Exits are never blocked. The chart dashboard
  has a DATA LAG row.
- **Inputs to check:** qty **1**, Data Safety
  guard ON at 90 s, Test mode OFF, $625 risk, 90 min.
- **Deployed copy:** the copy on TradingView must be this file. The repo
  caps qty at 1, yet the 9 Sep alert was created at qty 2, so the deployed
  copy had drifted. After any redeploy, check the alert name shows
  `(1, 625, 90, …)`.

Why each rule exists, and the evidence for it: `RESULTS.md` §2.7 and
[`docs/DECISIONS.md`](../../docs/DECISIONS.md).

## Ghost ticker ("MES(v2 Draft)", account LTE10089070250001)

- **Stop loss:** "Use Stop Loss and Take Profit" ON, "Use Webhook SL/TP"
  ON, "No Take Profit" ON, last confirmed 28 Aug. With either of the first
  two off, the script's `sl` is ignored silently (see the
  [2026-08-27 incident](../../docs/incidents/2026-08-27_ghost-stop-miswiring.md)).
- **Size:** the 30 Sep and 2 Oct buys went out at the alert's qty 2. Treat
  the alert's `qty` as what Ghost trades, and keep the script's input at 1.

## Replacing the live alert (outside market hours only)

Do this after 4pm ET, or between Fri 5pm and Sun 6pm ET. A TradingView alert
keeps running the script version it was created with, so updating the
script alone changes nothing: the alert has to be recreated.

1. On the MES1! 1m chart, open the Pine Editor on the indicator, replace its
   code with `orb_long_mes_v2.pine`, and **Save**. Check the inputs listed
   above.
2. Open the old alert 5571966155 (Alerts panel → Edit) and **copy its Ghost
   webhook URL**. Close without saving.
3. Create the new alert:
   - Condition: the script → "Any alert() function call"
   - Webhook: the same Ghost URL
   - Message: default
   - Expiration: the latest date offered
4. **Delete 5571966155.** Two live alerts on one webhook double every order.
5. Check that the new alert's name shows `(1, 625, 90, …)` and that the chart
   dashboard has the DATA LAG row.
6. While you're there, recreate the two DEMO probes with the latest expiry.
7. Tell Claude. The next 8:45 check audits the new alert (qty 1, guard
   version, exactly one live alert).

## Daily operation

| when (ET) | routine | checklist | writes |
|---|---|---|---|
| 8:45 weekdays | go/no-go: switches the alert on or off | [`ops/GO_NO_GO.md`](ops/GO_NO_GO.md) | `ops/golive_log.csv` |
| 9:50 weekdays | watch: read-only, pushes to your phone on URGENT | [`ops/WATCH.md`](ops/WATCH.md) | `ops/watch_log.csv` |
| 4:15 weekdays | close: shadow replay and reconcile | [`ops/CLOSE_ROUTINE.md`](ops/CLOSE_ROUTINE.md) | `ops/journal.csv` |
| Fri 4:40 | weekly review, proposes at most one change | [`ops/WEEKLY_REVIEW.md`](ops/WEEKLY_REVIEW.md) | `ops/weekly_reviews.md` |

- **Kill switch:** say "hold trading" (creates `ops/HOLD`) or "release the
  hold".
- **Risk rules R1–R5:** [`ops/RISK_RULES.md`](ops/RISK_RULES.md).
- **Verdicts:** decided by `ops/checks.py`, which CI tests on every PR.

## Standing rules (each one learned the hard way)

- **Never restart, edit or create the live alert during the session.** The
  script can take a late entry, and saving an edit can switch a paused alert
  back on ([2026-09-21](../../docs/incidents/2026-09-21_delayed-cme-data.md)).
- **One live alert per Ghost webhook, at qty 1**
  ([2026-09-30](../../docs/incidents/2026-09-30_qty2-and-reactivations.md)).
- **The TradingView MCP can't edit an alert that has a webhook.** Expiry
  changes and redeploys are manual.
- **Real-time CME data is a paid TradingView add-on** (non-professional).
  If it lapses, every alert fires about 10 min late. The 8:45 latency check
  and the script's guard both catch this.
