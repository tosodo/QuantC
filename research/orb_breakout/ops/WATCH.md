# 9:50 ET watch: MES v2 ORB

Runs every weekday at **9:50 ET** as a Claude routine. It closes gap G2.2 in
`PRODUCTION_READINESS.md`: without it, an alert switched on after 8:45 is
only seen at the 4:15 close. Change the checks here, by PR.

It is **read-only**. It never starts, stops or edits an alert, because
stopping the alert mid-session can orphan the exit of an open trade. Its only
action is a push notification. The user decides what to do.

9:50 is four minutes after the earliest possible entry (the 9:45 bar closes
at 9:46), so a wrong-day or wrong-size entry is already visible.

## 0. Skip days

On a US market holiday (no 9:30–16:00 ET session) do nothing and log
nothing.

## 1. Gather

1. `git pull origin claude/beautiful-cray-9vkxjd`: the state (HOLD,
   RISK_PAUSE, `golive_log.csv`) lives on that branch.
2. `mcp-tv-list-alerts` → save as `$S/alerts.json`.
3. `mcp-tv-get-alerts-log` (today) → save as `$S/log.json`.

**If the TradingView MCP is down** after retries: send a push notification
right away: "9:50 watch could not reach TradingView. Check the MES v2 alert
and Tradovate yourself." Log `MCP_DOWN` and stop.

## 2. Run the script: it decides

    git show origin/main:research/orb_breakout/ops/checks.py > $S/checks.py
    git show origin/main:research/orb_breakout/ops/risk_state.py > $S/risk_state.py
    python3 -I $S/checks.py watch --alerts $S/alerts.json --log $S/log.json \
        --ops-dir research/orb_breakout/ops

It compares the live alert and today's live fires with the 8:45 verdict
(today's `golive_log.csv` row). The output's `action.do` is always `none`.

**URGENT** (`notify: true`), any of:

| flag | meaning |
|---|---|
| `alert_active_on_nogo_day` | the alert was switched on after a NO-GO (as on 1–2 Oct) |
| `alert_active_on_no_verdict_day` | the alert is active and 8:45 logged no verdict |
| `alert_active_during_hold` / `_risk_pause` | active while HOLD or RISK_PAUSE exists |
| `active_alert_qty_N` | the active alert's qty input isn't 1 |
| `active_alert_has_no_stale_guard` | the active alert predates the guard (26 Sep) |
| `live_entry_on_..._day` | a live `buy` fired on a day that wasn't GO |
| `live_entry_qty_N` | a live `buy` fired with qty ≠ 1 |
| `duplicate_orders_possible` | more than one active live alert, fire source or buy |

**WARN** (logged, no push): `alert_inactive_on_go_day` (it was stopped
after 8:45, so today's entry is missed), `live_alert_in_test_mode`.

If the script disagrees with your own reading, follow the script and report
the disagreement as a bug to fix by PR.

## 3. Notify and log

- **URGENT:** send one push notification. Lead with the flags in plain
  words, then: "Nothing was changed. If you didn't switch it on, check
  Tradovate for a position and decide whether to stop the alert. Stopping it
  with a trade open leaves the exit to the Ghost stop bracket only."
- **OK / WARN:** no push.

Append one line to `research/orb_breakout/ops/watch_log.csv`, commit and
push to the working branch:

    date,checked_at,verdict_845,status,flags,active_ids,live_buys

(`flags` = the urgent then warn flags, `;`-separated.) Report to the user in
1–3 lines.
