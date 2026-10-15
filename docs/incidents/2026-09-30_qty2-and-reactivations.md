# 2026-09-30: buys at qty 2; alert reactivated outside the routines

**Status:** open. The cause of the reactivations is still unknown
(PRODUCTION_READINESS.md G2.1).

## What happened
- **30 Sep:** a GO day. The live buy went out at **qty 2**: the alert's
  inputs read `(2, 625, 90, …)`. Risk rule R5 tripped at the close.
- **1 Oct:** the 8:45 routine stopped the alert at 8:46 ET (NO-GO, R5). It
  was found active again at 4:15. Nobody in the routines restarted it.
- **2 Oct:** stopped again at 8:46 ET, then restarted outside the routines
  before 9:46. It bought **qty 2 during the risk pause**, and R5 tripped
  again.
- **Later:** the alert was stopped again at some point after 2 Oct, also
  outside the routines.

## Impact
- **30 Sep:** signal −$8.75 per contract, about −$17.50 at qty 2, before
  costs.
- **2 Oct:** signal −$163.75 per contract, about −$327.50 at qty 2.
- **The controls failed:** a NO-GO and a risk pause both failed to stop a
  trade.
- **Lucid P&L for these days hasn't been supplied** (G4.3).

## How it was found
At the 4:15 close routine, after the trades. Nothing was watching between
8:45 and 4:15, and the qty was only checked after a trade (R5).

## Root cause
- **Size:** the 9 Sep alert was created with qty 2 in the script's inputs,
  and TradingView keeps the inputs an alert was created with. The repo's
  copy of the script has had `maxval=1` on qty since the first commit (29
  Aug), so it could never be set to 2. **The script deployed on TradingView
  was therefore not the same code as the repo's**, and nothing checked that
  the two matched.
- **Reactivations:** unknown. Someone or something with access to the
  TradingView account restarted it. Candidates: another device or session,
  the mobile app, another person with access.

## What we changed
- **Pre-trade size and guard gates** (PR #16): the 8:45 check fails any
  live-named alert with qty ≠ 1, or created before the stale guard. The old
  alert can't pass.
- **The alert name is audited:** TradingView appends the inputs to the
  alert name, and the 8:45 check reads qty from it. That catches the
  deployed inputs whatever the repo says.
- **9:50 ET read-only watch** (PR #17): it sends a push to the phone if the
  alert is active on a day that isn't GO, or a live entry fired on one.
  It's tested against a replay of 2 Oct.
- **Checks are code:** the go/no-go and close verdicts come from
  `ops/checks.py`, with tests in CI.

## Lessons
- **Gate before the trade:** a rule that fires after a trade (R5) is a
  report, not a control.
- **Assume state can change between checks:** a control that only acts at
  8:45 assumes nothing changes until the close.
- **Audit the deployed object, not the repo:** the alert's own name and
  `create_time` are the evidence of what's running.

## Open items
- **G2.1:** find the cause. Check TradingView login history and devices,
  then change the password and turn on 2FA.
- **G1.1:** replace 5571966155 with a guarded alert at qty 1.
- **G4.3:** Lucid P&L for 30 Sep and 2 Oct.

## Evidence
- `ops/golive_log.csv` and `ops/journal.csv`, 30 Sep to 2 Oct.
- `ops/RISK_PAUSE`.
- PRs #14, #16, #17.
