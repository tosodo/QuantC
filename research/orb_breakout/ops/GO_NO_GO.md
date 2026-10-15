# Daily go/no-go check: MES v2 ORB

Runs every weekday at **8:45 ET** as a Claude routine. It is Phase 1,
item B of the 2026-09-26 council review. This file is the checklist the
routine follows. Change the criteria here, by PR, and the routine picks up
the change the next morning.

The live alert is found **by name**, not by id, because redeploying the
script creates a new id:
`QuantC ORB Long MES v2 (validated) - Ghost (Accessible)`.

## 0. Skip days

If CME equity futures have no regular 9:30–16:00 ET session today (a US
market holiday), log `SKIP` and stop. Half-days are not skipped; see check 5.

## 1. Manual hold (the user's kill switch)

State files are read from the working branch, not `main` (see "Where the
state lives" in `RISK_RULES.md`). Run `git pull origin
claude/beautiful-cray-9vkxjd` first.

If `research/orb_breakout/ops/HOLD` exists, the verdict is
**NO-GO (hold)**, whatever the other checks say. The file's text says why.
Only the user creates or removes it. Claude does that only when asked,
e.g. "hold trading" / "release the hold".

## 1b. Risk pause: must PASS (Phase 2, see `RISK_RULES.md`)

Run `python3 research/orb_breakout/ops/risk_state.py`.

- **On a Monday:** if `ops/RISK_PAUSE` exists and its only rule is
  `R2_weekly_loss`, and R2 is no longer in `tripped`, delete it and commit.
  The new week has started.
- **FAIL (risk pause):** `ops/RISK_PAUSE` exists.
- **FAIL (risk pause):** `tripped` is not empty, e.g. a Lucid P&L supplied
  since the close pushed the buffer under the limit. Create or extend
  `RISK_PAUSE` as `RISK_RULES.md` describes.
- Report the rule and figures, and that the pause needs the user to say
  "resume" (R2: that it clears next Monday).

## 2. Data latency: must PASS

Run `mcp-tv-get-ohlcv` on `CME_MINI:MES1!`, 1m, `count` 3. Compare the
newest bar's open time `t` with the current time:

    freshness = now − t   (the newest bar is still forming)

- This measures the account's own CME data entitlement, which is the
  subscription that lapsed in Sep 2026. On a live feed it's 0–60 s. On the
  10-min delayed feed it's about 600 s or more.
- Globex trades at 8:45 ET, so this works every weekday morning, including
  Monday.

**Verdict.**

- **PASS**: freshness ≤ 120 s.
- **FAIL**: freshness > 120 s. The data is delayed and the tested pass
  rates don't apply.
- **FAIL (unknown)**: the ohlcv call failed after retries. No evidence
  counts as a fail.

Put the figure in `notes`, e.g. `fresh 5s`.

The stale-data guard in the live script (see `SETUP_GUIDE.md`) is the
per-trade check: it measures the lag inside TradingView's alert engine on
the breakout bar itself and blocks an entry more than 90 s late. This
check is the daily one: it keeps the alert off on mornings when the feed is
already known to be delayed. There are no separate latency probe alerts
(D-018).

## 3. Alert state: must PASS

Use `mcp-tv-list-alerts` and find every alert whose name starts with the
live name above.

- **FAIL (urgent)**: more than one of them is active. Two alerts on the
  same Ghost webhook double every order. Stop all of them and tell the
  user.
- **FAIL**: none exists (it was deleted or expired without being recreated).
- **FAIL (size)**: the alert's inputs aren't qty 1. TradingView appends the
  script's inputs to the alert name, and the first one is qty, e.g.
  `(2, 625, 90, ...)` means 2 contracts. Without this check, R5 only catches
  a wrong size after a trade has gone through, as it did on 30 Sep and 2 Oct.
- **FAIL (no guard)**: it isn't the stale-guard version, meaning it was
  created before 2026-09-26, when the guard was deployed. A pre-guard build
  would trade on a delayed feed with nothing to stop it.
- Otherwise note its id, `active` and `create_time`.

## 4. Expiry: PASS, or WARN

- **FAIL**: it expires before 16:00 ET today.
- **WARN**: it expires in 10 days or less. Remind the user to recreate or
  extend it this evening or at the weekend, never mid-session.
- **PASS**: more than 10 days left.

## 5. Calendar: information only, never blocks

Use `mcp-tv-get-economic-calendar` for today's high-impact US events
(CPI, NFP, FOMC, PCE, GDP) and note any early close or half-day.

These are **reported, not a NO-GO**. The backtest traded through event
days, and skipping them would be an untested filter. Changing that is a
separate decision for the user. On a half-day the script's
`catchAllFlatten` exits the trade at the early close.

## 6. Account figures: reported

From the `risk_state.py` output, report:
- `buffer`: say "estimated" if `buffer_estimated`, and give its anchor
  date.
- `week_live_pnl`.
- `consecutive_stops`.

R3 (buffer) is gated in check 1b.

## Run the checks script: this decides the verdict

Checks 1–4 are coded in `ops/checks.py` and covered by `ops/tests/`, which
CI runs on every PR. Save each MCP result as JSON in the scratchpad (`$S`)
and run main's copy of the script against the working-branch state:

    git show origin/main:research/orb_breakout/ops/checks.py > $S/checks.py
    git show origin/main:research/orb_breakout/ops/risk_state.py > $S/risk_state.py
    python3 -I $S/checks.py gonogo --alerts $S/alerts.json \
        --ohlcv $S/mes.json --ops-dir research/orb_breakout/ops

- **What you save:**
  - `alerts.json` = `mcp-tv-list-alerts`
  - `mes.json` = `mcp-tv-get-ohlcv`, `CME_MINI:MES1!`, 1m, `count` 3

  If the ohlcv call fails after retries, leave out `--ohlcv` (the verdict
  is then NO-GO, latency unknown) and say so.
- **Use the output:** `verdict`, `fails` and `action` are the decision.
  `warn` is reported, never acted on. Do
  what `action.do` says:
  - `ensure_active` / `ensure_stopped`: make the alert ids active or
    stopped, then confirm with `mcp-tv-list-alerts`;
  - `stop` + `urgent`: stop them now, at any time, and tell the user;
  - `none`: touch nothing.
- **If the script disagrees with your own reading of the checks,** follow
  the script and report the disagreement. That is a bug to fix by PR.
- **Still done by hand:** check 0 (holidays) and check 5 (calendar). On a
  holiday, don't run the script.

## Verdict and action

- **GO** = checks 1, 1b, 2 and 3 pass and check 4 is not FAIL (as computed
  by `checks.py`). Make sure the live
  alert is active; restart it if it's paused. It's 8:45 ET, before the
  session, so a restart is safe. Confirm `active=true`.
- **NO-GO** = any of checks 1, 1b, 2, 3 or 4 fails. Stop the live alert if it's active
  and confirm `active=false`.
- **Never** restart or edit an alert after 9:30 ET. If this check runs late
  (after 9:30), treat GO as "leave as is" and report.

## Log and report

Append one line to `research/orb_breakout/ops/golive_log.csv`, commit and
push to the working branch. It gets merged with the next PR.

    date,verdict,median_lag_s,probe_fires,alert_id,alert_active_after,guard_version,expiry,events,risk,notes

(`risk` = `ok`, or the tripped rules, `;`-separated. Leave `median_lag_s`
and `probe_fires` blank: they hold the retired probe figures (D-018).
The freshness figure goes in `notes` as `fresh Ns`.)

Then tell the user in 3–5 lines: the verdict, why, the action taken, and
any WARN.
