# Production readiness: MES v2 ORB

This is the gap register for every part of the system, from strategy
evidence to the broker. It holds one entry per subsystem: its status, the
gaps, the fix, who owns the fix, and when it counts as done. Keep it
current by PR: a gap is closed when its "done when" is met.

Opened 2026-10-14. Live trading has been paused (R5) since 30 Sep.

## Status at a glance

| # | subsystem | status | blocking live? |
|---|---|---|---|
| 1 | Live alert (Pine script on TradingView) | **not ready** | yes |
| 2 | Kill switch and alert control | **not ready** | yes |
| 3 | Market data feed and latency | partial | no |
| 4 | Execution: Ghost → Tradovate | **not ready** | yes |
| 5 | Risk engine (`risk_state.py`) | partial | no |
| 6 | Routines (8:45, 4:15, Friday) | partial | no |
| 7 | Strategy evidence (backtests) | partial | no |
| 8 | Engineering: tests, CI, reproducibility | partial | no |

Live trading should resume only when every **blocking** row is ready.

## 1. Live alert

**Gaps**
- **G1.1 Wrong build.** Alert 5571966155 is the 9 Sep build. It has no
  stale-data guard and qty 2, so each stop risks $1,250 instead of the
  tested $625. It caused R5 on 30 Sep and 2 Oct.
- **G1.2 Untested rule: down-break-first days.** The live script trades
  days where price broke below the range first. The 77.8% research
  skipped those days. `live_rules_backtest.py` answers this, but its
  report (`phase3_report.md`) was never committed.
- **G1.3 Missing evidence for the 90-min exit.** The live 90-min exit is
  re-checked on every bar (the "M1" variant, 84.27% pass rate). The
  scripts behind that figure, `mes_m1_m4_checks.py` and
  `mes_c1_stop_rerun.py`, aren't in the repo.

**Fixes**
- **G1.1 (user, outside market hours):** follow `SETUP_GUIDE.md` →
  "Deploying it". Create the guard alert at qty 1 with the same Ghost
  webhook and a far-out expiry, then delete 5571966155. `checks.py` now
  fails the go/no-go for any live-named alert that has qty ≠ 1 or predates
  the guard, so the old alert can't trade again.
- **G1.2 (user + Claude):** run `live_rules_backtest.py >
  phase3_report.md` on the machine with the data, then commit the report
  and `phase3_trades.csv`. Then decide on down-break-first days: keep
  trading them, or add the skip to the script. Either way it needs evidence
  first.
- **G1.3 (user):** commit the two missing scripts.

**Done when**
- the go/no-go alert audit passes: qty 1, guard version, exactly one live
  alert;
- `phase3_report.md` is in the repo and the down-break decision is
  recorded;
- the M1 evidence is reproducible from the repo.

## 2. Kill switch and alert control

**Gaps**
- **G2.1 Reactivations outside the routines.** The live alert was
  reactivated on 1 Oct and 2 Oct, and the 2 Oct trade went through during
  a risk pause. The cause is still unknown. Until it's known, a NO-GO or a
  HOLD can't be relied on.
- **G2.2 Nothing watches the alert between 8:45 and 4:15.** An alert
  switched on at 9:31 is only seen at the close.

**Fixes**
- **G2.1 (user):** find the cause. Check TradingView login history and
  devices, mobile app sessions, and anyone with access. Then change the
  TradingView password and turn on 2FA. Record the outcome here.
- **G2.2 (Claude, by PR when approved):** add a read-only 9:50 ET check.
  - If the live alert is active on a NO-GO day, it alerts the user with a
    push notification.
  - It never stops the alert mid-session: stopping it could orphan the exit
    of an open position.
  - The user decides what to do.

**Done when** the cause of G2.1 is known and closed, and the 9:50 watch is
running.

## 3. Market data feed and latency

**Gaps**
- **G3.1 Paused probes.** The DEMO probes were paused 2–14 Oct, which gave
  8 mornings of "FAIL (unknown)". They were restarted 14 Oct, but they
  expire **21 Oct**.

**Done so far**
- The latency check has two independent measures, probe lag and MES bar
  freshness (PR #15).
- The verdict is coded and tested (`checks.py latency`).

**Fixes**
- **G3.1 (user):** recreate both probes with a far-out expiry when you
  deploy the guard alert.
- **Backstop:** the stale guard (G1.1) blocks any late entry on each trade.

**Done when** the probes have more than 30 days to expiry and the guard
alert is live.

## 4. Execution: Ghost → Tradovate

**Gaps**
- **G4.1 Flat-account exit untested (Phase 1 D).** After the Ghost stop
  fills, the script still sends its exit alert. If Ghost treats that as a
  sell on a flat account, it could open a short.
- **G4.2 Real costs unknown.** The research charged MES ES's per-point cost,
  about $0.58 a round turn. Real micro commission plus fees is higher.
  R4's $5 limit assumes about $2.50.
- **G4.3 Fills never reconciled.** No live fill has been reconciled. The
  only broker figures are user-supplied daily P&L, and the last account
  snapshot is from 24 Sep, so the buffer is an estimate.

**Fixes**
- **G4.1 (user + Claude):** on the Lucid sim, send a test buy, let the
  bracket stop fill, then send the exit alert. Record what Ghost does.
  - If it would open a short, either turn on a Ghost "close only" or flat
    check, or have the script not send exits after its own stop price is
    hit.
- **G4.2 (user):** get the per-side commission and exchange fees from one
  Tradovate fill statement. Then:
  - re-run the live-rules vectorbt check with `--rt-cost-usd` set to that
    figure;
  - correct R4 in `RISK_RULES.md` if needed.
- **G4.3 (user):** send Lucid P&L for 21 Sep, 30 Sep and 2 Oct, plus a
  current balance and minimum balance. After that, send a daily figure for
  each live day.

**Done when** the Phase 1 D result is recorded and handled, the real
round-turn cost is in `RISK_RULES.md`, and the account snapshot is less
than 7 days old.

## 5. Risk engine

**Done so far**
- `risk_state.evaluate()` is covered by `ops/tests/test_risk_state.py`:
  R1–R5, resumes, the trailing floor and the floor lock.
- It now reports `buffer_anchor_age_days`.

**Gaps**
- **G5.1 Stale buffer.** The buffer is estimated from a 24 Sep snapshot
  (see G4.3).

**Done when** G4.3 is done.

## 6. Routines

**Done so far**
- The go/no-go verdict and the close reconcile are code, not judgement
  (`ops/checks.py`, 28 tests; 47 across `ops/tests/`).
- Two new pre-trade gates: qty must be 1, and the stale guard must be
  present.
- A disagreement between the script and Claude's own reading is reported
  as a bug.

**Gaps**
- **G6.1 Single dependency on the TradingView MCP.** If it's down at 8:45
  the verdict is NO-GO. If it's down at 4:15, the user is asked to confirm
  they're flat. That's safe but manual.
- **G6.2 Fragile state branch.** State lives on a working branch that is
  reset after each merge.

**Fixes**
- **G6.1:** accept as is for now. The failure mode is safe.
- **G6.2 (Claude):** always merge before resetting, as now. Move state to
  `main` via a dedicated PR if it becomes a problem.

## 7. Strategy evidence

**Done so far**
- Independent re-implementation on vectorbt (`vectorbt_check/`).
  - It matches `mes_final_run.py` (§2.7 rules) and `shadow_day.py` (live
    rules) trade-for-trade on the TradingView bars available.

**Gaps**
- **G7.1 5-year cross-check not run.** The full 5-year cross-check hasn't
  been run: the data is only on the user's machine.

**Fixes**
- **G7.1 (user):** run
  `vectorbt_check/vbt_mes_v2.py --csv ../data/continuous/ES.csv --compare`,
  once without `--rules` (§2.7 rules) and once with `--rules live`. Commit
  the printed summaries.

**Done when** both runs show 0 mismatches over 5 years.

## 8. Engineering

**Done so far**
- CI (`.github/workflows/ci.yml`) byte-compiles everything and runs the ops
  tests on every PR and on every push to main.
- `vectorbt_check/requirements.txt` is pinned and pip-audit clean.

**Gaps**
- **G8.1 Unpinned dependencies.** The research scripts have no pinned
  dependency file, beyond pandas and databento being needed.
- **G8.2 Untested research code.** The research code itself has no tests.
  The vectorbt cross-check is the safety net for it.

**Done when** CI is green on main and a `requirements.txt` exists for the
research scripts.
