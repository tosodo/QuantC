# 2026-08-27: Ghost stop not wired; alerts linked to the wrong script

**Status:** closed 2026-08-28.

## What happened
- **No stop at all:** the live "MES(v2 Draft)" Ghost ticker had its "Use
  Stop Loss and Take Profit" master toggle OFF, so trades ran with no
  broker-side stop.
- **A fallback bracket instead:** once the toggle was turned on, Ghost
  reported that the alerts sent no `sl`/`tp` values (5 recent entries
  checked). Every trade therefore used Ghost's fallback fixed bracket, a
  10-pt stop and 20-pt target. That rule was never tested.

## Impact
For an unknown number of sessions, the account traded a different strategy
from the one tested: first with no stop, then on an arbitrary 10/20
bracket instead of the ~125-pt stop and 90-min exit (RESULTS.md §2.7).

## How it was found
While cleaning up the charts: scripts had been loaded on the wrong
instrument's chart and were showing their "wrong instrument" warning labels.

## Root cause
- **Wrong script behind the alert:** the TradingView alert feeding the
  ticker was linked to the plain v1 script (`orb_long_ghost.pine`, which
  never sends `sl`), not to the v2 draft.
- **The draft had no alert:** it sat on the chart marked "NOT LIVE" with no
  alert of its own.
- **MNQ had the same mis-wiring.**

## What we changed
- Created alerts directly on the draft scripts, pointed at the existing
  Ghost webhooks. Re-pointed the old MES v1 alert to the demo-account "MES"
  ticker, and deleted the old MNQ v1 alert.
- Turned on Ghost "Use Stop Loss and Take Profit", "Use Webhook SL/TP" and
  "No Take Profit" for both tickers.
- Checked the webhook URLs against Ghost's ticker ids in the page source,
  not the truncated UI.
- Removed the scripts loaded on the wrong instrument and the duplicate
  indicators.

## Lessons
- **Check settings from both ends:** verify which script an alert is
  linked to, and the broker-side settings, on both TradingView and Ghost.
  Never infer them from file names.
- **Ghost fails silently:** a missing `sl` falls back without an error.
  The close routine's reconcile (entry price, `sl` and exit vs the shadow
  replay) is the ongoing check.
- **Keep the repo in step with what's deployed.** This led to the 10 Sep
  rename and, later, to the live/archive split in `README.md`.

## Open items
None.

## Evidence
- The archived guide, section 3:
  [`SETUP_GUIDE_2026-08-27_to_2026-10-15.md`](../../archive/research/orb_breakout/SETUP_GUIDE_2026-08-27_to_2026-10-15.md).
- RESULTS.md §2.7, "Resolved 2026-08-28".
