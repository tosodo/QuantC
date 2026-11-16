# TradingView connector guide

How to use the TradingView MCP connector on this project. MCP is the
plug that lets Claude read and act on your TradingView account. This is a
**live** document: it states how things work now. Change it by PR.

Every routine in this project depends on this one connector. When it is
down, the routines still run, but blind.

## 1. The five rules

1. **Read freely, change rarely.** Reading alerts, prices and the calendar
   is safe at any time. Only the 8:45 ET go/no-go routine may switch an
   alert on or off, and only when `ops/checks.py` says so.
2. **Never touch an alert between 9:30 and 16:00 ET.** Stopping an alert
   with a trade open can leave the exit to the Ghost stop alone. The one
   exception is two live alerts active at once (doubled orders): stop them
   and tell the user.
3. **Anything with a webhook is yours to change, not Claude's.** A webhook
   is the link that sends the order to Ghost. The connector cannot create
   or edit a webhook alert. Redeploys, size changes and expiry extensions
   are done by you on tradingview.com.
4. **The checks only see alerts with the live name.** They look for names
   starting `QuantC ORB Long MES v2 (validated) - Ghost (Accessible)`. An
   order-sending alert under any other name is invisible to the 8:45 gate,
   the 9:50 watch and the risk pause. Keep the name, or change the
   checklists by PR first.
5. **No evidence means NO-GO.** If a call fails after retries, the answer
   is "unknown", and unknown counts as a fail.

## 2. When the connector stops working

**How you will know:** the 8:45 report says "NO-GO, MCP down", and the 9:50
watch sends a push saying it could not reach TradingView.

**The fix, which only you can do:** open claude.ai, go to Settings, then
Connectors, find TradingView and reconnect it. Claude cannot do this for
you.

**Do it the same day.** One-minute price history only goes back about a
week (see section 5). After that, the missed days cannot be replayed
through this connector, and the journal has a permanent gap.

**While it is down:** check Tradovate yourself after 16:15 ET and confirm
you are flat before 16:45 ET.

**To test it is back,** ask Claude: "Run the connector health check."
Claude runs the three read-only calls in section 3 and reports alert
state, data freshness and recent fires.

## 3. The calls the routines use

All tool names start `mcp-tv-`. Save each result as JSON in the scratchpad
and pass the file to `checks.py`. The script decides, not Claude.

| call | settings | used by | what it tells us |
|---|---|---|---|
| `list-alerts` | none | 8:45, 9:50, 4:15 | every alert, its id, name, `active`, `create_time`, `expiration`, `last_fire_time` |
| `get-ohlcv` | `CME_MINI:MES1!`, `interval` 1m, `count` 3 | 8:45 | data freshness: now minus the newest bar's `t`. 120 s or less passes |
| `get-ohlcv` | `CME_MINI:MES1!`, `interval` 1m, `date_from` and `date_to` set to the day | 4:15 | the session's bars for `shadow_day.py` (450 or more) |
| `get-alerts-log` | `days` 1 | 9:50, 4:15 | each fire: time, message, and whether the webhook was delivered |
| `get-economic-calendar` | `min_importance` 1 | 8:45 | today's high-impact US events. Reported, never blocks |
| `stop-alerts` / `restart-alerts` | the alert id | 8:45 only | switches the live alert off or on. Confirm afterwards with `list-alerts` |

Notes on getting clean results:

- **Always use the full symbol**, `CME_MINI:MES1!`. A bare ticker can
  resolve to the wrong listing. The response's `symbol` field shows which
  one was used.
- **Bar time `t` is the bar's open, in Unix seconds, UTC.** The alert
  message's `time` is the bar's close, one minute later.
- **The newest bar is still forming.** Do not use it as a finished bar.
- **`stop`, `restart` and `update` reply before they finish.** The reply
  says "starting". Always confirm the real state with `list-alerts`.
- **Retry a failed call two or three times** before logging it as failed.
  Handshake errors and timeouts are usually brief.
- **An empty calendar result is a real answer** (no high-impact events),
  not an error.

## 4. Capabilities worth using more

These work today and the routines do not use them yet. Each would need a
PR to a checklist before a routine relies on it.

| capability | call | why it helps |
|---|---|---|
| Webhook delivery status | `get-alerts-log`, the `webhook` field | Shows whether Ghost accepted each order. Anything other than `http_code` 200 means the order may not have reached the broker. The close routine reads the fire but not this field |
| Second freshness check | `get-symbol-data` with columns `close`, `change`, `update_mode` | `update_mode` reads `streaming` on a real-time feed. A cheap cross-check on the 8:45 latency gate |
| Full alert settings | `get-alerts` with the id | Shows the script behind an alert, its input values (size is the first input), whether it has a webhook, and its last error. The message and webhook address are hidden |
| Script drift check | `search-pine-scripts` (scope `mine`), then `get-pine-script-source` | Compares the script TradingView is running with the copy in this repo. Catches a deployed script that no longer matches what was tested |
| Check before redeploy | `validate-pine-script` | Finds compile errors before you paste a script into TradingView |
| Backtest cross-check | `run-pine-backtest` with `date_from` | Runs the Pine version over a set period. A second opinion on the Python backtests. Percent fields come back as fractions: 0.25 means 25% |
| Past events | `get-economic-calendar` with past dates | Fills the `events` column for days the morning check missed. Data goes back to 2003 |
| Longer alert history | `get-alerts-log` with `days` 30, `limit` up to 2000 | Rebuilds what fired during an outage, as long as the alert was not deleted |

## 5. Hard limits

- **One-minute history is about a week deep.** Older days return "no
  bars". A missed close routine must be backfilled within days. For older
  one-minute data, use the Databento download script on the research
  branch.
- **One call returns at most 5,000 bars as rows**, or 8,000 with `format`
  set to `columns`. For more, page back using `next_date_to`.
- **Deleting an alert deletes its fire history.** Save the alert log
  before any delete.
- **The connector cannot create or edit webhook alerts,** and cannot
  create alerts driven by a script. It can only create simple price
  alerts, which this project does not use.
- **Data quality follows your TradingView plan.** If the real-time CME
  add-on lapses, bars arrive about 10 minutes late and the 8:45 check
  fails on freshness.
- **The connector is the single point of failure** (gap G6.1 in
  [`PRODUCTION_READINESS.md`](../research/orb_breakout/ops/PRODUCTION_READINESS.md)).
  The failure mode is safe, because unknown means NO-GO, but it is manual.

## 6. What needs your say-so

| action | who |
|---|---|
| Reading alerts, bars, fire history, calendar, script source | Claude, any time |
| Stop or restart the live alert at 8:45 ET per `checks.py` | Claude, as the standing routine |
| Stop duplicate live alerts at any time | Claude, then tells you at once |
| Delete an alert | Claude, only when you ask. Fire history is saved first |
| Save or update a script in your TradingView account | Claude, only when you ask |
| Create, edit, resize or extend a webhook alert | You, on tradingview.com, outside the session |
| Reconnect the connector | You, in claude.ai settings |

## 7. Things you can ask Claude

- "Run the connector health check."
- "What alerts are live right now, and what size are they?"
- "Did anything fire today, and did Ghost accept it?"
- "Is my data real-time?"
- "Does the script on TradingView match the one in the repo?"
- "What high-impact US events are due this week?"
- "Hold trading" or "release the hold" (the kill switch, see
  [`GO_NO_GO.md`](../research/orb_breakout/ops/GO_NO_GO.md)).

## 8. Where the detail lives

- Morning check: [`GO_NO_GO.md`](../research/orb_breakout/ops/GO_NO_GO.md)
- 9:50 watch: [`WATCH.md`](../research/orb_breakout/ops/WATCH.md)
- Close routine: [`CLOSE_ROUTINE.md`](../research/orb_breakout/ops/CLOSE_ROUTINE.md)
- Risk rules: [`RISK_RULES.md`](../research/orb_breakout/ops/RISK_RULES.md)
- Standing rules and setup: [`SETUP_GUIDE.md`](../research/orb_breakout/SETUP_GUIDE.md)
