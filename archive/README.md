# Archive

Documents and code that were **live once and have been superseded**. They
are kept as evidence, so we can always see what we believed or ran at the
time.

**Rules**
- **Never edit** an archived file. Moved files keep their git history
  (`git log --follow <path>`).
- **Mirror the original path** under `archive/`, e.g. `research/orb_breakout/x.md`
  → `archive/research/orb_breakout/x.md`.
- **Name verbatim snapshots of a still-live file with the dates they
  cover**, e.g. `SETUP_GUIDE_2026-08-27_to_2026-10-15.md`.
- **Add a row below** in the same PR. CI (`tools/check_docs.py`) fails if an
  archived file has no row.
- **Links inside archived files aren't maintained.** Use the "original
  path" column to read them in context:
  `git show <commit>:<original path>`.

| file | original path | archived | why | replaced by | last live commit |
|---|---|---|---|---|---|
| `research/orb_breakout/SETUP_GUIDE_2026-08-27_to_2026-10-15.md` | `research/orb_breakout/SETUP_GUIDE.md` | 2026-10-15 | History and current state were mixed together: v1 instructions, struck-through notes, "outdated" blocks, a stale 25 Sep status. Verbatim copy. | `research/orb_breakout/SETUP_GUIDE.md` (current state only), `docs/incidents/` | `9325594` |
| `research/orb_breakout/pine/orb_long_ghost.pine` | `research/orb_breakout/orb_long_ghost.pine` | 2026-10-15 | v1 script (MNQ + MES, no stop). Its alerts expired in Sep 2026. | `research/orb_breakout/orb_long_mes_v2.pine` | `9325594` |
| `research/orb_breakout/pine/orb_long_ghost_accessible.pine` | `research/orb_breakout/orb_long_ghost_accessible.pine` | 2026-10-15 | Accessible variant of v1. | `research/orb_breakout/orb_long_mes_v2.pine` | `9325594` |
| `research/orb_breakout/pine/orb_long_ghost_DRAFT_mes_v2.pine` | `research/orb_breakout/orb_long_ghost_DRAFT_mes_v2.pine` | 2026-10-15 | Non-accessible v2 draft. It stopped being kept in sync (no stale-data guard). Never deployed. | `research/orb_breakout/orb_long_mes_v2.pine` | `9325594` |
| `research/orb_breakout/pine/orb_long_ghost_DRAFT_mnq_orwidth_stop.pine` | `research/orb_breakout/orb_long_ghost_DRAFT_mnq_orwidth_stop.pine` | 2026-10-15 | MNQ opening-range-width stop (STOPLOSS_HYPOTHESIS.md). MNQ not traded since early Sep (D-006). | none | `9325594` |
| `research/orb_breakout/pine/orb_long_ghost_DRAFT_mnq_orwidth_stop_accessible.pine` | `research/orb_breakout/orb_long_ghost_DRAFT_mnq_orwidth_stop_accessible.pine` | 2026-10-15 | Accessible variant of the above. | none | `9325594` |

**Renamed, not archived:** the live script
`research/orb_breakout/orb_long_ghost_DRAFT_mes_v2_accessible.pine` is now
`research/orb_breakout/orb_long_mes_v2.pine` (2026-10-15).
