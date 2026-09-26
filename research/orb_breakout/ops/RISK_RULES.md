# Risk rules: MES v2 ORB (Phase 2)

These rules were approved by the user on 2026-09-26 (Phase 2 of the council
review). They decide when the strategy stops trading for its own safety,
separately from the data and alert checks in `GO_NO_GO.md`.

`ops/risk_state.py` evaluates them from `ops/journal.csv`,
`ops/account.csv` and `ops/resumes.csv`. The 4:15 close routine runs it after writing the day's
row. The 8:45 go/no-go check runs it again before deciding.

## The rules

All figures are for live trades only (journal `status` = `live`). Shadow
trades don't count.

| rule | trips when | clears |
|---|---|---|
| **R1: consecutive stops** | the last 2 live trades both hit the full 125-pt stop | only when the user says "resume" |
| **R2: weekly loss** | live P&L for this Mon-Fri week is **−$900 or worse** | automatically at the start of the next week (Monday's go/no-go) |
| **R3: buffer** | the room above Lucid's minimum balance falls **below $1,950** (about 3 full stops) | only when the user says "resume", after reassessing |
| **R4: slippage** | the average of `slippage` over the last 10 live trades (from 2026-09-28, the first day with the stale guard) is **worse than −$5.00 per trade**. That is 2 ticks ($2.50) plus about $2.50 for commission. Only checked once 10 trades have Lucid P&L | only when the user says "resume" |
| **R5: size** | any live buy was sent with `qty` other than 1 (the journal's `qty` column, from the buy message) | only when the user says "resume" |

**Stay at 1 MES.** There is no size increase, including after the floor
locks at $100,100. Changing size is a separate decision for the user.

**What counts as a live trade's P&L:**
- The day's `lucid_pnl`, when the user has supplied it.
- Otherwise `signal_pnl − $5.00`, an estimate that is marked as such.

**The buffer** starts from the latest row in `ops/account.csv`, a Lucid
balance and minimum balance. From there it adds each later live day's P&L,
modelling Lucid's rule: the minimum balance trails the end-of-day
high-water mark minus $3,000, and locks at $100,100. When the user gives a
new Lucid balance, add a row to `account.csv`. That resets the estimate.

The $5.00 slippage limit assumes about $2.50 commission per round turn.
Confirm it from the Tradovate fills (Phase 1 D) and correct it here if it
is wrong.

## The pause file

When a rule trips, the close routine creates
`research/orb_breakout/ops/RISK_PAUSE` if it doesn't already exist, and
commits it:

    rule: R1_consecutive_stops
    tripped: 2026-09-29
    figures: consecutive_stops=2 week_live_pnl=-1270 buffer=1651
    clears: user says "resume"

If a second rule trips while paused, add its lines to the same file.

- **While `RISK_PAUSE` exists, the go/no-go verdict is NO-GO (risk pause).**
- **R2 alone:** Monday's go/no-go deletes the file and proceeds normally,
  provided no other rule is still tripped.
- **"resume":** Claude deletes the file only when the user asks, like
  `HOLD`. First show the current `risk_state.py` figures. Then append a
  row to `ops/resumes.csv`:
  - `date`: today
  - `rules`: the resumed rules, `;`-separated, e.g. `R1;R3`
  - `buffer_at_resume`: the current buffer
  - `note`: the user's reason

  After a resume, each rule only looks forward:
  - **R1** counts stops after the resume date.
  - **R3** trips again only if the buffer falls a further $625 (one full
    stop) below its level at resume.
  - **R4** and **R5** only look at trades after the resume date.
  - **R2** can't be resumed. It clears at the start of the next week.

  Delete `RISK_PAUSE`, commit both files, and report.

## Where the state lives

The checklists (`*.md`) and scripts are read from `main`. The state is
committed by the routines to the working branch
(`claude/beautiful-cray-9vkxjd`): `journal.csv`, `golive_log.csv`,
`account.csv`, `resumes.csv`, `RISK_PAUSE` and `HOLD`. So both routines
read the state from the local checkout of that branch, after
`git pull origin claude/beautiful-cray-9vkxjd`, not from `main`. It reaches
`main` with the next PR.
