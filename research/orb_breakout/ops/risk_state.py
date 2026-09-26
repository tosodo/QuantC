"""Evaluate the Phase 2 risk rules (ops/RISK_RULES.md) from the journal.

Reads ops/journal.csv, ops/account.csv and ops/resumes.csv and prints one JSON object with
the running figures and which rules are tripped. Used by the 4:15 ET close
routine and the 8:45 ET go/no-go check.

    python3 ops/risk_state.py [YYYY-MM-DD]   # "as of" date, default today (ET)
"""
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))

MAX_CONSEC_STOPS = 2          # R1
WEEKLY_LOSS_LIMIT = -900.0    # R2
MIN_BUFFER = 1950.0           # R3
SLIPPAGE_LIMIT = -5.00        # R4: avg $/trade over the last 10 (2 ticks + ~$2.50 commission)
SLIPPAGE_N = 10
SLIPPAGE_FROM = "2026-09-28"  # first day with the stale-data guard; earlier fills were on delayed data
EST_COST = 5.00               # used for live days whose Lucid P&L isn't in yet
TRAIL = 3000.0
LOCK_FLOOR = 100100.0


def num(s):
    return float(s) if s not in (None, "") else None


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return list(csv.DictReader(f))


def main(asof):
    rows = sorted(load("journal.csv"), key=lambda r: r["date"])
    rows = [r for r in rows if r["date"] <= asof]
    live = [r for r in rows if r["status"] == "live"]

    # After a "resume", a rule only looks at trades after that date (R3: at a
    # new low one full stop below the buffer at resume) - see RISK_RULES.md
    resumes = [x for x in load("resumes.csv") if x["date"] <= asof]

    def resumed(rule):
        hits = [x for x in resumes if rule in x["rules"].split(";")]
        return hits[-1] if hits else None

    def since(rule, trades):
        x = resumed(rule)
        return [r for r in trades if r["date"] > x["date"]] if x else trades

    def live_pnl(r):
        lp = num(r["lucid_pnl"])
        if lp is not None:
            return lp, False
        sp = num(r["signal_pnl"])
        return (sp - EST_COST if sp is not None else 0.0), True

    # R1: consecutive full stops across live trades, most recent first
    consec = 0
    for r in reversed(since("R1", live)):
        if r["exit_reason"] == "stop":
            consec += 1
        else:
            break

    # R2: live P&L this ISO week (Mon-Fri)
    d = date.fromisoformat(asof)
    monday = (d - timedelta(days=d.weekday())).isoformat()
    week = [live_pnl(r) for r in live if r["date"] >= monday]
    week_pnl = round(sum(p for p, _ in week), 2)
    week_est = any(e for _, e in week)

    # R3: buffer above Lucid's minimum balance, from the latest snapshot
    snaps = sorted(load("account.csv"), key=lambda r: r["date"])
    snaps = [s for s in snaps if s["date"] <= asof]
    snap = snaps[-1]
    bal = float(snap["balance"])
    floor = float(snap["min_balance"])
    hwm = floor + TRAIL if floor < LOCK_FLOOR else None
    buf_est = False
    for r in live:
        if r["date"] <= snap["date"]:
            continue
        p, e = live_pnl(r)
        buf_est |= e
        bal += p
        if hwm is not None:  # EOD trailing until the floor locks at $100,100
            hwm = max(hwm, bal)
            floor = min(hwm - TRAIL, LOCK_FLOOR)
            if floor >= LOCK_FLOOR:
                hwm = None
    buffer = round(bal - floor, 2)

    # R4: average slippage over the last 10 live trades with Lucid P&L
    slips = [num(r["slippage"]) for r in since("R4", live)
             if r["date"] >= SLIPPAGE_FROM and num(r["slippage"]) is not None]
    slips = slips[-SLIPPAGE_N:]
    avg_slip = round(sum(slips) / len(slips), 2) if slips else None

    tripped = []
    if consec >= MAX_CONSEC_STOPS:
        tripped.append("R1_consecutive_stops")
    if week_pnl <= WEEKLY_LOSS_LIMIT:
        tripped.append("R2_weekly_loss")
    r3 = resumed("R3")
    min_buffer = min(MIN_BUFFER, float(r3["buffer_at_resume"]) - 625) if r3 else MIN_BUFFER
    if buffer < min_buffer:
        tripped.append("R3_buffer")
    if len(slips) >= SLIPPAGE_N and avg_slip < SLIPPAGE_LIMIT:
        tripped.append("R4_slippage")
    bad_qty = [r["date"] for r in since("R5", live) if r.get("qty") not in (None, "", "1")]
    if bad_qty:
        tripped.append("R5_size")

    print(json.dumps({
        "asof": asof,
        "consecutive_stops": consec,
        "week_start": monday,
        "week_live_pnl": week_pnl,
        "week_pnl_estimated": week_est,
        "balance": round(bal, 2),
        "min_balance": round(floor, 2),
        "floor_locked": floor >= LOCK_FLOOR,
        "buffer": buffer,
        "buffer_estimated": buf_est,
        "buffer_anchor": snap["date"],
        "buffer_trip_level": min_buffer,
        "avg_slippage": avg_slip,
        "slippage_trades": len(slips),
        "tripped": tripped,
    }))


if __name__ == "__main__":
    asof = sys.argv[1] if len(sys.argv) > 1 else datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    main(asof)
