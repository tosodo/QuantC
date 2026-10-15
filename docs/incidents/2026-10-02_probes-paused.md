# 2026-10-02: latency probes stopped firing, 8 mornings of "FAIL (unknown)"

**Status:** closed 2026-10-14.

## What happened
- **The probes stopped:** the two DEMO probe alerts (5662901850,
  5662914432) stopped firing after 2 Oct.
- **The latency check failed:** at the time it relied only on probe fires,
  so from 5 to 14 Oct it scored "FAIL (unknown)" every morning.

## Impact
- **No trading impact:** trading was already paused by R5.
- **But the check had a single point of failure:** a GO would have been
  impossible for a reason that had nothing to do with the data feed.
  Meanwhile every real fire showed 0 s lag.

## How it was found
The 8:45 routine's notes, day after day. They were raised in the 14 Oct
latency review.

## Root cause
The latency check had a single source of evidence, the probes, and nothing
noticed when that source went quiet.

## What we changed
- **A second, independent measure** (PR #15): MES 1m bar freshness. It
  passes on its own when no probe fired.
- **The probes were restarted** on 14 Oct.

## Lessons
Every gate needs a second, independent source of evidence, or an alarm
when its only source goes quiet.

## Open items
The probes expire 21 Oct and only the user can extend them (G3.1).

## Evidence
- `ops/golive_log.csv`, 5 to 14 Oct.
- PR #15.
