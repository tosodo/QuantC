# Production readiness: MES v2 ORB

This is the gap register for every part of the system, from strategy
evidence to the broker. It holds one entry per subsystem: its status, what
is in place, the open gaps, the fix, who owns the fix, and when it counts as
done.

It's a live document, edited by PR. When a gap's "done when" is met:
- delete the gap here, and add what's now in place to "In place";
- record the closure in `CHANGELOG.md`;
- add a `docs/DECISIONS.md` entry if it changed a rule.

Opened 2026-10-14. Live trading has been paused (R5) since 30 Sep.

## Status at a glance

| # | subsystem | status | blocking live? |
|---|---|---|---|
| 1 | Live alert (Pine script on TradingView) | **not ready** | yes |
| 2 | Kill switch and alert control | **not ready** | yes |
| 3 | Market data feed and latency | partial | no |
| 4 | Execution: Ghost → Tradovate | **not ready** | yes |
| 5 | Risk engine (`risk_state.py`) | partial | no |
| 6 | Routines (8:45, 9:50, 4:15, Friday) | partial | no |
| 7 | Strategy evidence (backtests) | partial | no |
| 8 | Engineering: tests, CI, reproducibility | partial | no |

Live trading should resume only when every **blocking** row is ready.

## 1. Live alert

**In place**
- Alert 5849779220, created 15 Oct 2026 01:30Z from the repo's
  `orb_long_mes_v2.pine`: qty 1, test mode off, $625, 90 min, stale guard
  on at 90 s, Ghost webhook, expires 14 Dec. Left stopped; the 8:45 check
  starts it on a GO day. The 9 Sep qty-2 build (5571966155) is deleted.
  The go/no-go alert audit passes (closes G1.1).

**Gaps**
- **G1.2 Untested rule: down-break-first days.** The live script trades
  days where price broke below the range first. The 77.8% research
  skipped those days. `live_rules_backtest.py` answers this, but its
  report (`phase3_report.md`) was never committed.
- **G1.3 Missing evidence for the 90-min exit.** The live 90-min exit is
  re-checked on every bar (the "M1" variant, 84.27% pass rate). The
  scripts behind that figure, `mes_m1_m4_checks.py` and
  `mes_c1_stop_rerun.py`, aren't in the repo.

**Fixes**
- **G1.2 (user + Claude):** run `live_rules_backtest.py >
  phase3_report.md` on the machine with the data, then commit the report
  and `phase3_trades.csv`. Then decide on down-break-first days: keep
  trading them, or add the skip to the script. Either way it needs evidence
  first.
- **G1.3 (user):** commit the two missing scripts.

**Done when**
- `phase3_report.md` is in the repo and the down-break decision is
  recorded;
- the M1 evidence is reproducible from the repo.

## 2. Kill switch and alert control

**In place**
- 9:50 ET read-only watch (`WATCH.md`, `checks.py watch`). It sends a push
  notification if the live alert is active on a day that isn't GO, during a
  HOLD or risk pause, at qty ≠ 1 or without the guard, or if a live entry
  fired on such a day. It never stops the alert (PR
  #17).

**Gaps**
- **G2.1 Reactivations outside the routines.** The live alert was
  reactivated on 1 Oct and 2 Oct, and the 2 Oct trade went through during
  a risk pause. The cause is still unknown. Until it's known, a NO-GO or a
  HOLD can't be relied on.

**Fixes**
- **G2.1 (user):** find the cause. Check TradingView login history and
  devices, mobile app sessions, and anyone with access. Then change the
  TradingView password and turn on 2FA.

**Done when** the cause of G2.1 is known and closed. Record it in
`docs/incidents/2026-09-30_qty2-and-reactivations.md`.

## 3. Market data feed and latency

**Gaps**
- **G3.1 Unreliable probes.** Both DEMO probes (5662901850, 5662914432)
  showed active but fired nothing from 2 to 14 Oct; before that they fired
  several times a day. BUY fired again on 15 Oct at 00:36Z; SELL is still
  silent. While they're silent, check 2A has no evidence and the latency
  verdict rests on B (bar freshness) alone.
  They expire **21 Oct**. They carry a webhook, so only the user can
  recreate them: the MCP can't create webhook alerts, and restarting them
  from a routine isn't permitted.

**In place**
- The latency check has two independent measures, probe lag and MES bar
  freshness (PR #15).
- The verdict is coded and tested (`checks.py latency`).
- The 8:45 check reports silent, inactive or expiring probes as a `warn`
  (`probe_silent_<id>`, `probe_inactive_<id>`, `probe_expires_<date>_<id>`).
  These never block the verdict.

**Fixes**
- **G3.1 (user):** recreate both probes with a far-out expiry when you
  deploy the guard alert.
- **Backstop:** the live alert's stale guard blocks any late entry on each trade.

**Done when** the probes have more than 30 days to expiry and the 8:45 check
shows no `probe_` warn.

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

**In place**
- `risk_state.evaluate()` is covered by `ops/tests/test_risk_state.py`:
  R1–R5, resumes, the trailing floor and the floor lock.
- It now reports `buffer_anchor_age_days`.

**Gaps**
- **G5.1 Stale buffer.** The buffer is estimated from a 24 Sep snapshot
  (see G4.3).

**Done when** G4.3 is done.

## 6. Routines

**In place**
- The go/no-go verdict and the close reconcile are code, not judgement
  (`ops/checks.py`, tested in `ops/tests/`, which CI runs on every PR).
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

**In place**
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

**In place**
- CI (`.github/workflows/ci.yml`) runs on every PR and every push to main:
  - byte-compiles everything;
  - runs the ops tests;
  - runs `tools/check_docs.py`, the documentation policy check: links,
    archive index, no stale content in live documents, a changelog entry
    for every PR.
- Records of every change, decision and incident: `CHANGELOG.md`,
  `docs/DECISIONS.md`, `docs/incidents/`.
- Pinned, pip-audit clean dependencies: `requirements.txt` for the research
  scripts (pandas 3, databento) and `vectorbt_check/requirements.txt`.

**Gaps**
- **G8.2 Untested research code.** The research code itself has no tests.
  The vectorbt cross-check is the safety net for it.

**Done when** the research code has tests, or the 5-year vectorbt
cross-check (G7.1) passes with 0 mismatches as its stand-in.
