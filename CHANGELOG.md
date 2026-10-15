# Changelog

This is a **record**: one entry for every change merged to `main`, newest
first. Each PR adds its own entry in the same PR. Routine log rows
(journal, go/no-go, watch) aren't listed here: the CSVs are their record.

Format: `date · PR · what changed, and why`. Link the decision or incident
it implements.

## 2026-10-15
- **#20** Retired the latency probes (D-018, supersedes D-013). The 8:45
  latency check is MES bar freshness alone; the live script's stale guard
  stays the per-trade check. Removed the probe code and `probe_` warns from
  `checks.py`, dropped `--log` from `checks.py gonogo`, renamed the close
  check's `--morning-lag-s` to `--morning-fresh-s`. Deleted the two DEMO
  probe alerts (5662901850, 5662914432). Closes G3.1.
- **#19** Alignment pass. The 8:45 check warns on silent, inactive or
  expiring latency probes (the DEMO probes show active but haven't fired
  since 2 Oct). Pinned `research/orb_breakout/requirements.txt` (closes
  G8.1). Readiness register, GO_NO_GO and SETUP_GUIDE brought in line.
  Deleted the three expired v1/MNQ alerts (5461765534, 5490124255,
  5478843448) at the user's request. They were inactive; their scripts
  are kept in `archive/research/orb_breakout/pine/`.
  **Closes G1.1:** the user redeployed `orb_long_mes_v2.pine` as alert
  5849779220 (qty 1, stale guard on, expires 14 Dec), Claude stopped it
  and deleted the 9 Sep qty-2 alert 5571966155.
- **#18** Documentation policy (D-016). Root README with a map of live
  documents; `archive/` with the old SETUP_GUIDE (verbatim) and the 5
  retired Pine scripts; changelog, decision log and incident records;
  SETUP_GUIDE rewritten to current state only; live script renamed
  `orb_long_mes_v2.pine` (it was still called DRAFT); `tools/check_docs.py`
  in CI.
- **#17** Read-only 9:50 ET watch (`checks.py watch`, WATCH.md,
  watch_log.csv) (D-015). Closes G2.2.
- **#16** Production hardening: `ops/checks.py` decides the go/no-go and
  close verdicts; pre-trade qty and guard gates; 47 tests; GitHub Actions
  CI; PRODUCTION_READINESS.md gap register (D-014).

## 2026-10-14
- **#15** Latency check measures probe lag and MES bar freshness (D-013);
  vectorbt `--rules live` mode.
- **#14** vectorbt cross-check of the MES v2 backtest: 0 mismatches against
  `mes_final_run.py` (D-012). Ops state 29 Sep–14 Oct.

## 2026-09-28
- **#13** Logged the user's manual restart of alert 5571966155.
- **#12** After-close note: second on-time probe fire after the data
  renewal.
- **#11** 28 Sep close check (shadow −92.50) and the morning NO-GO row.

## 2026-09-26
- **#10** Journal: Friday close check; probe lag still ~600 s after the
  data renewal.
- **#9** Phase 3: live-rules backtest, weekly review, guide fixes (D-010).
- **#8** Phase 2 risk rules R1–R5, wired into the daily checks (D-009).
- **#7** 4:15 ET close routine, shadow replay and trade journal (D-008).
- **#6** Daily 8:45 ET go/no-go checklist and log (D-008).
- **#5** Stale-data entry guard in the live MES v2 script (D-008).

## 2026-09-25
- **#1–#4** Recorded the alert-delay incident, the MES v2 pause, the restart
  plan, the expiry-extension steps and the Friday after-close check in the
  setup guide (D-007).

## Before pull requests
- **2026-09-10** `a33b548`: synced the repo's MES v2 script with the
  deployed one and renamed it out of "DRAFT" (D-006).
- **2026-09-04** `3bc9f43`: MES v2 risk and exit rework per the QC report
  (D-005).
- **2026-08-29** `86fa4c9`: fixed warning-label spam in the MNQ
  OR-width-stop script.
- **2026-08-29** `0d859ec`: initial commit of the research and Pine
  scripts.
