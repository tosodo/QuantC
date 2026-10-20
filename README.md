# QuantC

Research and live operation of a 9:30 ET opening-range-breakout strategy on
MES futures. Orders flow TradingView alert → QuantCrawler Ghost webhook →
Tradovate, on a **simulated** Lucid LucidPro $100K evaluation. Claude runs
the daily routines. The user decides anything that changes risk.

## Start here

| question | read |
|---|---|
| What's running right now, and how is it set up? | [`research/orb_breakout/SETUP_GUIDE.md`](research/orb_breakout/SETUP_GUIDE.md) |
| What blocks it from going live again? | [`research/orb_breakout/ops/PRODUCTION_READINESS.md`](research/orb_breakout/ops/PRODUCTION_READINESS.md) |
| Why are the rules what they are? | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| What went wrong before, and what did we change? | [`docs/incidents/`](docs/incidents/README.md) |
| What changed, when? | [`CHANGELOG.md`](CHANGELOG.md) |
| What did a document say before it was replaced? | [`archive/`](archive/README.md) |

## How documents work

Every file in this repo is one of three kinds. The rules keep current
documents free of stale content, without losing any history.

**1. Live:** describes how things are now. Edited in place, by PR. It holds
no history: no struck-through text, no "outdated" or "superseded" blocks, no
dated status updates piling up.

- `README.md`, `research/orb_breakout/SETUP_GUIDE.md`
- `research/orb_breakout/ops/*.md` (checklists, rules, readiness register),
  except `weekly_reviews.md`
- code: `ops/*.py`, `orb_long_mes_v2.pine`, `vectorbt_check/`, `tools/`

**2. Records:** append-only history. Rows are added, never rewritten.

- `CHANGELOG.md`: every merged change
- `docs/DECISIONS.md`: every decision, why, and the evidence
- `docs/incidents/`: one file per incident, with its lessons
- ops logs: `golive_log.csv`, `watch_log.csv`, `journal.csv`,
  `alert_actions.csv`, `resumes.csv`, `account.csv`, `weekly_reviews.md`
- research evidence: each `HYPOTHESIS.md` / `RESULTS*.md` is frozen once
  its test has run

**3. Archive:** live documents and code that have been superseded, kept
verbatim under [`archive/`](archive/README.md) as evidence. Never edited.

### When something changes

1. **Update the live document** so it states only the current truth.
2. **If the old text is evidence** of what we believed or ran, keep it:
   either `git mv` the whole file into `archive/`, mirroring its path, or
   copy a verbatim snapshot there. Then add a row to `archive/README.md`.
3. **Record it:**
   - a line in `CHANGELOG.md`, every PR;
   - a `docs/DECISIONS.md` entry if a rule or practice changed;
   - an incident record if something went wrong.
4. **New research findings** go in a new dated file, never as edits to a
   finished `RESULTS*.md`.

CI runs `tools/check_docs.py` on every PR. It fails when:

- a relative link outside `archive/` is broken;
- an archived file has no index row;
- a live document contains struck-through text or an "outdated" marker;
- `CHANGELOG.md` has no entry for a merged PR number.

### Known legacy

`research/orb_breakout/RESULTS.md`, `HYPOTHESIS.md` and
`STOPLOSS_HYPOTHESIS.md` were corrected in place before this policy existed,
so they contain struck-through text and superseded verdicts. They are
research evidence, so they stay as they are: read the newest dated "Verdict"
or "Correction" section first.

## Research lines

| folder | what | status |
|---|---|---|
| `research/orb_breakout/` | 9:30 ET ORB, long side, MES v2 | **live** (paused, R5) |
| `research/orb_breakout/` (London) | London-session ORB | tested, see LONDON_RESULTS.md |
| `research/orb_breakout/` (divergence) | RSI divergence filter on the ORB | tested, not adopted, see DIVERGENCE_RESULTS.md |
| `research/index_mean_reversion/` | 20-day quintile mean reversion | `promising_but_unproven`; forward-tracked (`forward_log.csv`) |
| `research/nq_es_relative_value/` | NQ vs ES relative value | plan only |
| `research/gold_fix_breakout/` | LBMA fix-window breakout on metals | plan only |
| `research/mnq_session_open/` | MNQ session-open screen | scripts only, no write-up |
