# Daily close routine and trade journal: MES v2 ORB

Runs every weekday at **4:15 ET** as a Claude routine. It is Phase 1, item C
of the 2026-09-26 council review. This file is the checklist the routine
follows; change it here, by PR.

It's **read-only towards TradingView and the broker**: it never starts,
stops, or edits an alert. The only action it takes is to warn you. Its
record is one row per trading day in `ops/journal.csv`.

The live alert is found by name, as in `GO_NO_GO.md`:
`QuantC ORB Long MES v2 (validated) - Ghost (Accessible)`.

## 0. Skip days

If there was no regular session today (a US market holiday), don't write a
row. Stop.

## 1. Gather

- **Alert log:** `mcp-tv-get-alerts-log`, today's fires.
  - The live alert's messages are
    `{"action":"buy","price":..,"sl":..,"time":..}` and
    `{"action":"exit","reason":..,"time":..}`, where `time` is the signal
    bar's close (UTC).
  - lag = `fired_at − time`, in seconds.
  - Also note any fire whose message has `"test":true` (test mode is on:
    no order was sent).
- **Alert state:** `mcp-tv-list-alerts`. Record the live alert's id and
  `active`.
- **Bars:** `mcp-tv-get-ohlcv` for `CME_MINI:MES1!`, 1m, covering today's
  9:30-16:00 ET session (≥ 450 bars).
- **Shadow trade:** save the OHLCV result as JSON and run
  `python3 research/orb_breakout/ops/shadow_day.py <file> <YYYY-MM-DD>`.
  This replays the script's rules on today's bars: range, entry, 125-pt
  stop, 90-min exit, session close. Bar times in its output are bar
  **open** times in ET; the alert's `time` is the bar close, one minute
  later.
- **Morning verdict:** today's row in `ops/golive_log.csv`, if there is one.

## 2. Reconcile: flag anything that doesn't line up

Check these in order. An **URGENT** item goes at the top of the report.

1. **URGENT, possibly still in a position.** A `buy` fired today and no
   `exit` fired after it. The Ghost stop bracket may still be working and
   the position may be open. Tell the user to check Tradovate now and be
   flat by **4:45 ET** (a Lucid rule).
   Exception: if the shadow shows `exit_reason` `stop`, say the position
   was probably stopped out, but still ask them to confirm it's flat.
2. **URGENT, duplicate orders.** More than one `buy` today, or fires from
   more than one alert with the live name.
3. **Missed entry.** The shadow shows an entry, but no `buy` fired.
   - The alert was active and the morning lag was high → the stale guard
     most likely blocked the entry. That is expected; say so.
   - Otherwise → flag it as an alert or TradingView problem.
4. **Unexpected entry.** A `buy` fired but the shadow shows no entry, or
   the entry price differs by more than 1 tick. Flag it.
5. **Exit mismatch.** The fired exit's reason, bar or price doesn't match
   the shadow's. A shadow `stop` followed by a later `exit` alert is
   expected: the script doesn't know about the Ghost stop. Note that exit
   as "flat-account exit" (see Phase 1 D).
6. **Late fires.** Any live buy/exit with lag > 90 s. Record the lag.
7. **Test mode.** Any live fire has `"test":true`. Flag it: no order went
   to Tradovate.

## 3. Write the journal row

Append one row to `research/orb_breakout/ops/journal.csv`. Leave a field
blank when it doesn't apply.

| column | meaning |
|---|---|
| `date` | ET trading date |
| `gonogo` | this morning's verdict (`GO` / `NO-GO` / `none`) |
| `alert_active` | live alert `active` at 4:15 (`true`/`false`/`missing`) |
| `status` | `live` (a buy was sent), `shadow` (the rules traded, the alert was off), `stale_skip`, `no_breakout`, `no_range`, `missed` (item 3, not stale) |
| `range_high`, `range_low` | 9:30-9:44 range |
| `down_break_first` | `true` when price closed below the range low before the long break. The backtest skipped these days, so they are untested |
| `entry`, `entry_time` | shadow entry price, and the signal bar close in ET (HH:MM) |
| `exit`, `exit_time`, `exit_reason` | shadow exit (`stop`, `time_exit_90min`, `session_close`, `catch_all_flatten`) |
| `signal_pnl` | shadow P&L in $, 1 MES, before costs |
| `buy_lag_s`, `exit_lag_s` | lag of the live fires |
| `lucid_pnl` | the day's P&L reported by Lucid/Tradovate, supplied by the user. Blank until then |
| `slippage` | `lucid_pnl − signal_pnl`, once `lucid_pnl` is known (includes commissions) |
| `flags` | the reconcile items raised, `;`-separated, e.g. `exit_mismatch;late_fire` |
| `notes` | anything else, briefly, without commas |

**User-supplied P&L:** when a day was `live`, ask the user once in the
report for Lucid's P&L for the day. When they give it, fill in `lucid_pnl`
and `slippage` for that date. You can also fill in earlier blank days the
same way.

## 4. Running figures (information only until Phase 2)

Compute these from `journal.csv` and report them:

- **Week to date:** the sum of `lucid_pnl` for live days. Add the sum of
  `signal_pnl` for all days that had an entry.
- **Consecutive full stops** (`exit_reason` = `stop`) across entries,
  counting back from today.
- **Average `slippage`** over the last 10 live trades that have
  `lucid_pnl`.

Phase 2 would turn these into pause rules: 2 stops in a row, −$900 in a
week, or average slippage worse than 2 ticks ($2.50) plus commissions.
Until then they're only reported.

## 5. Commit and report

Commit `journal.csv` and push to the working branch; it's merged with the
next PR. Then tell the user in 3-6 lines:
- Any **URGENT** item first.
- Today's status and P&L (signal, and live lag).
- Other flags.
- The running figures.
- The Lucid P&L request, if the day was live.

Don't message the user about a quiet `no_breakout` day beyond a single
line.
