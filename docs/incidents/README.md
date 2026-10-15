# Incident records

One file per incident, named `YYYY-MM-DD_<slug>.md` after the day it
started. These are **records**: once an incident is closed, its file isn't
rewritten. A later finding goes under a dated "Update" heading at the
bottom.

Each record has the same sections, so incidents can be compared:

- **What happened**
- **Impact**
- **How it was found**
- **Root cause**
- **What we changed**
- **Lessons:** what the process should do differently
- **Open items**
- **Evidence:** links to the logs, commits and PRs

| date | incident | status |
|---|---|---|
| 2026-08-27 | [Ghost stop not wired; alerts linked to the wrong script](2026-08-27_ghost-stop-miswiring.md) | closed |
| 2026-09-21 | [CME real-time data lapsed: every alert ~10 min late](2026-09-21_delayed-cme-data.md) | closed |
| 2026-09-30 | [Buys at qty 2; alert reactivated outside the routines](2026-09-30_qty2-and-reactivations.md) | **open** (G2.1) |
| 2026-10-02 | [Latency probes stopped firing: 8 mornings of "FAIL (unknown)"](2026-10-02_probes-paused.md) | closed |
