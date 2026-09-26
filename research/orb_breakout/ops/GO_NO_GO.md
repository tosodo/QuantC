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

Use `mcp-tv-get-alerts-log` (last 2 days) and look at the DEMO probe alerts
("QC Trend DEMO test BUY/SELL (dry run)", MNQ1! 3m). They are 3m bars, so:

    lag = fired_at − (bar_time + 3 min)

- Use the probe fires from the last 16 hours. On Monday, use the fires
  since Sunday's 6pm ET reopen.
- **PASS**: the median lag is ≤ 2 min.
- **FAIL**: the median lag is > 2 min. The data is delayed and the tested
  pass rates don't apply.
- **FAIL (unknown)**: there are no probe fires in the window. No evidence
  counts as a fail. Also check whether the probe alerts are still active or
  have expired.

## 3. Alert state: must PASS

Use `mcp-tv-list-alerts` and find every alert whose name starts with the
live name above.

- **FAIL (urgent)**: more than one of them is active. Two alerts on the
  same Ghost webhook double every order. Stop all of them and tell the
  user.
- **FAIL**: none exists (it was deleted or expired without being recreated).
- Otherwise note its id, `active`, `create_time`, and whether it is the
  stale-guard version. It is the guard version if it was created on or
  after 2026-09-26, when the guard was deployed.

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

## Verdict and action

- **GO** = checks 1, 1b, 2 and 3 pass and check 4 is not FAIL. Make sure the live
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

(`risk` = `ok`, or the tripped rules, `;`-separated.)

Then tell the user in 3–5 lines: the verdict, why, the action taken, and
any WARN.
