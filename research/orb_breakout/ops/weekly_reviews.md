# Weekly reviews: MES v2 ORB

Written every Friday at 4:40 ET by the routine in [WEEKLY_REVIEW.md](WEEKLY_REVIEW.md). Newest at the bottom.

## Week of 2026-09-28 (written 2026-10-02)

**Days:** 2 live (30 Sep, 2 Oct), 1 shadow (28 Sep), 2 no-breakout (29 Sep, 1 Oct), 0 stale-skip, 0 missed.
Go/no-go: 2 GO (29, 30 Sep), 3 NO-GO (28 Sep: data delay 600 s and tool error; 1-2 Oct: R5 risk pause). Median probe lag by day: 600, 0, 0, 0, 0 s.

| date | status | entry | exit (reason) | signal P&L (1 MES) | qty sent | Lucid P&L |
|---|---|---|---|---|---|---|
| 28 Sep | shadow, down-break-first | 7781.25 12:27 | 7762.75 13:57 (90 min) | -92.50 | - | - |
| 30 Sep | live | 7761 09:57 | 7759.25 13:16 (90 min) | -8.75 | 2 | blank |
| 02 Oct | live, during risk pause | 7801.75 09:46 | 7769 11:16 (90 min) | -163.75 | 2 | blank |

**Totals:** signal P&L for all entries -265.00 (1 MES). Live: -172.50 at 1 MES; at the 2 contracts actually sent about -345 before costs. risk_state.py (1-lot estimate) says -182.50.
**Execution:** buy and exit lag 0 s on both live trades (avg 0 / 0). Slippage unknown (no Lucid P&L). Flags: size_qty2 x2, alert_reactivated x2, traded_during_risk_pause x1.
**Down-break-first:** 1 entry (28 Sep shadow, -92.50).
**Risk:** buffer 2738.50 estimated (anchor 24 Sep; about 2566 at qty 2), consecutive stops 0, R5_size tripped 30 Sep and again 2 Oct; RISK_PAUSE in place.

**Against expectations:** 3 signal entries vs about 2.6 a week; average -88 a trade vs about +11. All three exits were 90-minute time exits for small-to-moderate losses and no full stop, which fits the expected loss pattern. One week is noise; no conclusions.

**Open items (user):** set the alert's qty input to 1 and find what keeps restarting alert 5571966155 (restarted after the 1 Oct and 2 Oct morning stops); Lucid P&L for 21 Sep, 30 Sep and 2 Oct; Phase 1 D (Ghost SL/TP toggles and flat-account exit, Tradovate fills and commission, alert redeploy with stale guard); a fresh Lucid balance next week (anchor 24 Sep); phase3_report.md not committed. Alert expiry 25 Nov (54 days).

**Proposed change (operational, not strategy):** redeploy the stale-guard script as a new alert with qty 1, and delete 5571966155. Evidence: both live trades this week were sent at qty 2 by the 9 Sep build, and that alert was restarted twice during a risk pause.

## Week of 2026-10-05 (written 2026-10-09)

**Days:** 0 live, 5 shadow, 0 no-breakout, 0 stale-skip, 0 missed. Go/no-go: 0 GO, 5 NO-GO, every day for the R5 risk pause; the latency check also failed as unknown every day because both DEMO probe alerts have been paused since 2 Oct (no probe lag measured all week).

| date | entry | exit (reason) | signal P&L (1 MES) |
|---|---|---|---|
| 05 Oct | 7794.5 10:06 | 7831.5 16:00 (session close) | +185.00 |
| 06 Oct | 7869.5 09:47 | 7873 16:00 (session close) | +17.50 |
| 07 Oct | 7843.25 11:49 | 7851.25 16:00 (session close), down-break-first | +40.00 |
| 08 Oct | 7832.75 09:50 | 7823.5 11:20 (90 min) | -46.25 |
| 09 Oct | 7846 10:52 | 7861 16:00 (session close) | +75.00 |

**Totals:** shadow signal P&L +271.25 (1 MES) over 5 entries. Live P&L 0 (alert off all week).
**Execution:** no live fires, so no lag or slippage data. Flags: 7 Oct close check not run (TradingView MCP timeout), backfilled 8 Oct; OHLCV handshake errors needed retries on 6 and 8 Oct.
**Down-break-first:** 1 entry (7 Oct, +40.00).
**Risk:** buffer 2738.50 estimated (anchor 24 Sep; about 2566 if the 30 Sep and 2 Oct trades are counted at qty 2), consecutive stops 0, R5_size still tripped and RISK_PAUSE in place. The live alert was not restarted outside the routines this week.

**Against expectations:** 5 signal entries vs about 2.6 a week; average +54 a trade vs about +11. No full stop; the one loser was cut by the 90-minute exit. One week, all shadow, is noise; no conclusions.

**Open items (user):** set the live alert's qty input to 1 and say "resume" (R5); restart the DEMO probe alerts, which also expire 21 Oct; Lucid P&L for 21 Sep, 30 Sep and 2 Oct; a fresh Lucid balance (anchor 24 Sep is now over 2 weeks old); Phase 1 D (Ghost SL/TP toggles and flat-account exit, Tradovate fills and commission, alert redeploy with stale guard); phase3_report.md not committed. Live alert expiry 25 Nov (47 days).

**Proposed change (operational, not strategy):** before resuming, redeploy the stale-guard script as a new alert with qty 1 and delete 5571966155. Evidence: R5 has blocked trading all week, and the redeploy fixes the size and the missing guard in one step.
