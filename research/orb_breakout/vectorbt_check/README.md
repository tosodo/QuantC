# vectorbt cross-check of the MES v2 backtest

There are two rule sets:

- `--rules s27` (the default) is the published RESULTS.md §2.7 baseline.
- `--rules live` is what the live Pine script actually runs. That's the
  same rules as `ops/shadow_day.py` and `live_rules_backtest.py`:
  - it trades days where the range broke down first;
  - the 90-min exit is re-checked on every bar;
  - the stop is 125 pts;
  - it exits on the 15:59 bar, with a catch-all exit for half-days.

  P&L is gross of costs unless you pass `--rt-cost-usd`.

`vbt_mes_v2.py` re-runs the locked MES v2 rules (RESULTS.md §2.7,
`mes_final_run.py` config 4) on vectorbt's portfolio engine. The rules are
re-implemented from their written description, not by importing
`orb_test.py` or `mes_final_run.py`. If either implementation has a bug, the
two disagree. vectorbt handles the fills, the stop, fees and P&L; the script
only builds the signals.

## Setup

```bash
cd research/orb_breakout/vectorbt_check
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

- Everything in `requirements.txt` is pinned. vectorbt is pinned at 1.1.2.
- `pip-audit` reported no known vulnerabilities on 2026-10-14.
- Keep it in its own venv: vectorbt needs numpy ≥ 2.4 and pandas 3.
- Never load pickle/dill files from untrusted sources with vectorbt's
  `load()`.

## Run

Full 5-year re-run: this needs the gitignored Databento data, so run it on the
machine that has `data/continuous/ES.csv`.

```bash
.venv/bin/python vbt_mes_v2.py --csv ../data/continuous/ES.csv --compare
```

- **Configs:** it prints configs 1–4: no exit, stop only, 90-min exit only,
  and stop + 90-min.
- **ruin.py:** where `ruin.py` is installed, each config also gets its PASS
  rate. Compare these with RESULTS.md §2.7, for example 77.82% for config 4
  with no slippage.
- **Comparison:** `--compare` diffs every trade against `mes_final_run.py`
  and exits 1 on any mismatch.
- **Not modelled:** the slippage configs (6–7) are not reproduced here.

## Results so far (2026-10-14)

The full history isn't in this repo, so the first check used TradingView's
available 1-minute `CME_MINI:MES1!` bars, from 5 to 14 Oct 2026. That is
8 sessions and 5 trades; 7 Oct was skipped as down-break-first, as the
backtest does.

- **Locked v2, stop 124.75 pts:** 0 mismatches against `mes_final_run.py`.
  Net +$30.87 after costs, which agrees with the journal's shadow rows.
- **Stop path:** the stop never triggered in this window. To exercise it, the
  comparison was also run at 5, 10, 20 and 40 pts, with 0 mismatches each.
  These were plumbing tests, not results.

Eight days is far too few to say anything about the edge. This check confirms
that both implementations agree, not that the strategy works.

### Live rules (added 2026-10-14)

```bash
.venv/bin/python vbt_mes_v2.py --csv ../data/continuous/ES.csv --rules live --compare
.venv/bin/python vbt_mes_v2.py --csv ../data/continuous/ES.csv --rules live --rt-cost-usd 2.50
```

- **`--compare`:** diffs every trade against `ops/shadow_day.py`'s
  `replay_day`. That's the same replay the close routine and
  `live_rules_backtest.py` use. It passes the same stop to both sides.
- **Output:** it also splits the results by whether the range broke down
  first. That's the untested question from Phase 3.
- **`--rt-cost-usd`:** a sensitivity run, because the real MES round-turn
  cost isn't confirmed from Tradovate fills yet.

**On the TradingView bars for 5–14 Oct:**

- 6 trades and 0 mismatches against `shadow_day.py`. Gross +$73.75, which
  equals the journal's `signal_pnl` column exactly, 7 Oct included.
- The stop path was also exercised at 5, 10, 20 and 40 pts, with 0
  mismatches each.

## Known engine difference

When a bar opens beyond the stop, vectorbt's `StopLimit` fills at that bar's
open. `mes_final_run.py` always fills at the stop level. Within regular
trading hours a gap through a 125-pt stop is very rare. If the 5-year run
reports a mismatch on a stop day, check this first.
