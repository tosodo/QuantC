# Decision log

This is a **record**. Every decision that changes how the system trades or
operates gets one entry: what was decided, why, and the evidence. Entries
are never edited or deleted. When a decision is reversed, add a new entry
and set the old one's status to "superseded by D-0xx"; that status field is
the only thing ever edited. Newest at the bottom.

Status values: **active**, **superseded by D-0xx**, **pending** (proposed,
not yet approved).

| id | date | decision | why / evidence | status |
|---|---|---|---|---|
| D-001 | 2026-08-19 | Trade the 9:30 ET opening-range breakout **long side only**. | Long side significant in- and out-of-sample; short side rejected. RESULTS.md §1. | active |
| D-002 | by 2026-08-21 | Trade **micro** contracts (MES/MNQ), never full-size. | Full-size NQ/ES too large for the $100K drawdown limit: 44–45% pass rate vs 89–99% for micros. RESULTS.md §2.6. | active |
| D-003 | 2026-08-27 | Go live on the Lucid evaluation (simulated) with test mode off. | User go-ahead after the test-mode dry run. Archived SETUP_GUIDE, "what this guide originally deferred". | active |
| D-004 | 2026-08-28 | Ghost bracket: use the script's `sl` ("Use Webhook SL/TP" ON, no take profit), never Ghost's fallback distance. | [Incident 2026-08-27](incidents/2026-08-27_ghost-stop-miswiring.md). | active |
| D-005 | 2026-09-04 | MES v2 rules: $625 stop cap (125 pts), 90-min underwater exit re-checked every bar (M1), catch-all flatten on half-days, hard symbol/timeframe gates. | M1 raised the pass rate from 77.80% to 84.27% over 5 years (mes_m1_m4_checks.py, not yet in the repo, G1.3). Commit 3bc9f43. | active |
| D-006 | 2026-09-09 | MES v2 (Accessible) becomes the only live strategy; MNQ is not traded. | Commit a33b548. Last MNQ alert fire: 2 Sep. | active |
| D-007 | 2026-09-25 | Pause trading while data is delayed; never restart or edit an alert mid-session. | [Incident 2026-09-21](incidents/2026-09-21_delayed-cme-data.md). | active |
| D-008 | 2026-09-26 | Council review Phase 1: stale-data guard (90 s, entries only), 8:45 go/no-go, 4:15 close routine with shadow replay. | PRs #5–#7. | active |
| D-009 | 2026-09-26 | Phase 2 risk rules R1–R5; size stays at 1 MES. | Approved by the user. ops/RISK_RULES.md, PR #8. | active |
| D-010 | 2026-09-26 | Phase 3: Friday weekly review proposes at most one change, never an untested rule; live-rules backtest. | PR #9. | active |
| D-011 | 2026-09-26 | Economic event days are reported, **not** skipped. | Skipping them would be an untested filter. GO_NO_GO.md check 5. | active |
| D-012 | 2026-10-14 | Adopt vectorbt as an independent research cross-check (pinned, in its own venv). LEAN: safe, not now. ruflo: do not install. | Tooling security review (artifact "QuantC Tooling Review"). PR #14. | active |
| D-013 | 2026-10-14 | Latency gate uses two independent measures: probe lag (≤ 2 min) and MES bar freshness (≤ 120 s). | [Incident 2026-10-02](incidents/2026-10-02_probes-paused.md). PR #15. | active |
| D-014 | 2026-10-15 | Pre-trade gates: qty must be 1 and the alert must be the guard version. Routine verdicts come from tested code (`ops/checks.py`), with CI on every PR. | [Incident 2026-09-30](incidents/2026-09-30_qty2-and-reactivations.md). PR #16. | active |
| D-015 | 2026-10-15 | 9:50 ET watch is **read-only**: push notification only, never stops an alert mid-session. | Stopping mid-session can orphan an open trade's exit. PR #17. | active |
| D-016 | 2026-10-15 | Documentation policy: live documents hold only current truth; history goes to `archive/` (verbatim) or to records (changelog, decisions, incidents). Enforced in CI. | README.md, "How documents work". | active |
| D-017 | open | Down-break-first days: keep trading them (live script) or skip them (as the research did)? | Needs `phase3_report.md` first (G1.2). | pending |
