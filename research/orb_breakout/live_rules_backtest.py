#!/usr/bin/env python3
"""
live_rules_backtest.py - Phase 3 of the 2026-09-26 council review.

Backtests the rules the LIVE script actually runs
(orb_long_ghost_DRAFT_mes_v2_accessible.pine), using the exact same replay
code as the daily journal (ops/shadow_day.py replay_day), on the full
Databento ES history (MES proxy, same points, $5/pt):

  - range 9:30-9:44, entry on the first 1m close above the range high
  - 125-pt stop, 90-min underwater exit (close <= entry, re-checked every
    bar), session close on the 15:59 bar
  - NO down-break skip. The earlier research (mes_final_run.py
    build_mes_trades) dropped days where price closed below the range low
    before the long break. The live script trades them, so they were
    untested. This splits the results both ways.

It answers the Phase 3 questions:
  1. How do the down-break-first days perform? Are they worth trading?
  2. What does it look like with real MES commissions? Earlier runs applied
     ES's per-point cost to MES, about $0.58 a round turn, which is far
     below real micro commissions. Run as a sensitivity table, because the
     real figure is still to be confirmed from Tradovate fills.
  3. Max drawdown, longest losing streak, worst day, week and month.
  4. Pass rate against Lucid's actual rules: $6,000 target, $3,000 EOD
     trailing drawdown that locks at $100,100, and an intraday breach
     checked on each trade's worst point.

Needs the local data (gitignored): data/continuous/ES.csv, built by
build_continuous.py. Run from this folder:

    python3 live_rules_backtest.py > phase3_report.md

It also writes phase3_trades.csv (one row per trade, no raw market data),
so the results can be committed and re-analysed without the data.
"""
import argparse
import csv
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "ops"))
from shadow_day import replay_day  # noqa: E402

ET = ZoneInfo("America/New_York")
PV = 5.0
TICK = 0.25
START_BAL = 100000.0
TARGET = 106000.0
TRAIL = 3000.0
LOCK_FLOOR = 100100.0
COSTS = [0.0, 0.58, 1.50, 2.50, 4.00]  # $ per round turn, 1 MES; 0.58 = what earlier runs used
SLIPS = [0, 1, 2]                  # adverse ticks on every exit fill
BASE_COST, BASE_SLIP = 2.50, 1     # the "realistic" row used for the detail stats


def load_days(path):
    """ES.csv (Databento ohlcv-1m, ts_event = bar open) -> {date: [bars]}."""
    days = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            t = parse_ts(row["ts_event"])
            d = datetime.fromtimestamp(t, ET).date().isoformat()
            days[d].append({"t": t, "o": float(row["open"]), "h": float(row["high"]),
                            "l": float(row["low"]), "c": float(row["close"])})
    return days


def parse_ts(s):
    """Unix seconds from ISO-8601 UTC (any sub-second precision) or integer ns."""
    if s.isdigit():
        return int(s) // 10**9
    s = s.replace("Z", "+00:00")
    head, _, tail = s.partition(".")
    if tail:  # drop fractional seconds, keep the offset
        s = head + tail.lstrip("0123456789")
    return int(datetime.fromisoformat(s.replace(" ", "T")).timestamp())


def build_trades(days):
    trades, sessions = [], []
    for d in sorted(days):
        r = replay_day(days[d], d)
        if r["state"] == "no_range":
            continue
        sessions.append(d)
        if r["state"] == "open":
            # half-day / data ends before 15:59: the live catch-all flattens at the
            # first bar outside 9:45-16:00. Approximated as the last bar's close.
            r.update(exit=r["last_close"], exit_reason="catch_all_flatten",
                     pts=r["last_close"] - r["entry"], state="entry")
        if r["state"] == "entry":
            r["pts"], r["mae_pts"] = round(r["pts"], 2), round(r["mae_pts"], 2)
            trades.append({k: r[k] for k in ("date", "down_break_first", "entry", "exit",
                                             "exit_reason", "pts", "mae_pts")})
    return trades, sessions


def net(t, cost, slip):
    return (t["pts"] - slip * TICK) * PV - cost


def summarise(pnls):
    n = len(pnls)
    if not n:
        return dict(n=0, win=0, avg=0, total=0, pf=0)
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    return dict(n=n, win=100 * len(wins) / n, avg=sum(pnls) / n, total=sum(pnls),
                pf=(sum(wins) / sum(losses)) if losses else float("inf"))


def lucid_run(seq):
    """seq: list of (pnl, mae_usd) in time order, one per trading day with a
    trade. Returns ('pass'|'fail'|'open', trades_used)."""
    bal, hwm = START_BAL, START_BAL
    floor = hwm - TRAIL
    for i, (pnl, mae) in enumerate(seq, 1):
        if bal - mae <= floor:
            return "fail", i
        bal += pnl
        if bal <= floor:
            return "fail", i
        if bal >= TARGET:
            return "pass", i
        hwm = max(hwm, bal)
        floor = min(max(floor, hwm - TRAIL), LOCK_FLOOR)
    return "open", len(seq)


def pass_rates(trades, cost, slip, sims, seed=1):
    seq = [(net(t, cost, slip), (t["mae_pts"] + slip * TICK) * PV + cost) for t in trades]
    # rolling historical starts: begin at every trade, walk forward in real order
    res = [lucid_run(seq[i:]) for i in range(len(seq))]
    done = [r for r in res if r[0] != "open"]
    roll = 100 * sum(r[0] == "pass" for r in done) / len(done) if done else float("nan")
    # bootstrap: iid draws of trades (the way ruin.py simulates)
    rng = random.Random(seed)
    boots, used = 0, []
    for _ in range(sims):
        s = [rng.choice(seq) for _ in range(2000)]
        out, k = lucid_run(s)
        if out == "pass":
            boots += 1
            used.append(k)
    used.sort()
    med = used[len(used) // 2] if used else None
    return roll, len(done), 100 * boots / sims, med


def streaks_and_dd(trades, cost, slip):
    eq = peak = maxdd = 0.0
    run = worst_run = 0
    by_day, by_week, by_month = {}, defaultdict(float), defaultdict(float)
    for t in trades:
        p = net(t, cost, slip)
        eq += p
        peak = max(peak, eq)
        maxdd = max(maxdd, peak - eq)
        run = run + 1 if p < 0 else 0
        worst_run = max(worst_run, run)
        d = date.fromisoformat(t["date"])
        by_day[t["date"]] = p
        by_week["%d-W%02d" % d.isocalendar()[:2]] += p
        by_month[t["date"][:7]] += p
    wmin = lambda m: min(m.items(), key=lambda kv: kv[1])
    return dict(maxdd=maxdd, worst_run=worst_run, worst_day=wmin(by_day),
                worst_week=wmin(by_week), worst_month=wmin(by_month),
                losing_months=sum(v < 0 for v in by_month.values()), months=len(by_month))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    ap.add_argument("--sims", type=int, default=5000)
    ap.add_argument("--trades-out", default=os.path.join(HERE, "phase3_trades.csv"))
    a = ap.parse_args()

    days = load_days(a.data)
    trades, sessions = build_trades(days)
    with open(a.trades_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(trades)

    clean = [t for t in trades if not t["down_break_first"]]
    dbf = [t for t in trades if t["down_break_first"]]
    reasons = defaultdict(int)
    for t in trades:
        reasons[t["exit_reason"]] += 1

    P = print
    P("# Phase 3: live-rules backtest (MES v2)\n")
    P(f"Data: `{os.path.relpath(a.data, HERE)}`, {sessions[0]} to {sessions[-1]}, "
      f"{len(sessions)} sessions, {len(trades)} trades "
      f"({len(clean)} clean, {len(dbf)} down-break-first).")
    P("Exits: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items())) + ".\n")
    P("Costs are $/round turn for 1 MES; slippage is adverse ticks on every exit.\n")

    P("## 1. Down-break-first days vs clean days (per-trade)\n")
    P("| set | cost | slip | n | win % | avg $ | total $ | PF |")
    P("|---|---|---|---|---|---|---|---|")
    for name, ts in (("all (live rules)", trades), ("clean (research rule)", clean),
                     ("down-break-first only", dbf)):
        for cost in (0.0, BASE_COST):
            for slip in (0, BASE_SLIP):
                s = summarise([net(t, cost, slip) for t in ts])
                P(f"| {name} | {cost:.2f} | {slip} | {s['n']} | {s['win']:.1f} | "
                  f"{s['avg']:.2f} | {s['total']:.0f} | {s['pf']:.2f} |")

    P("\n## 2. Lucid pass rate by cost and slippage\n")
    P("Rolling = start the eval on every historical trade and walk forward in real "
      "order (keeps losing streaks as they happened). Bootstrap = random order, "
      f"{a.sims} sims. Median = trades to pass (bootstrap).\n")
    P("| set | cost | slip | rolling pass % (n starts) | bootstrap pass % | median trades |")
    P("|---|---|---|---|---|---|")
    for name, ts in (("all (live rules)", trades), ("clean only", clean)):
        for cost in COSTS:
            for slip in SLIPS:
                roll, n, boot, med = pass_rates(ts, cost, slip, a.sims)
                P(f"| {name} | {cost:.2f} | {slip} | {roll:.1f} ({n}) | {boot:.1f} | {med} |")

    P(f"\n## 3. Drawdown and streaks (cost ${BASE_COST:.2f}, {BASE_SLIP} tick)\n")
    P("| set | max DD $ | longest losing streak | worst day | worst week | worst month | losing months |")
    P("|---|---|---|---|---|---|---|")
    for name, ts in (("all (live rules)", trades), ("clean only", clean)):
        s = streaks_and_dd(ts, BASE_COST, BASE_SLIP)
        P(f"| {name} | {s['maxdd']:.0f} | {s['worst_run']} | "
          f"{s['worst_day'][1]:.0f} ({s['worst_day'][0]}) | "
          f"{s['worst_week'][1]:.0f} ({s['worst_week'][0]}) | "
          f"{s['worst_month'][1]:.0f} ({s['worst_month'][0]}) | "
          f"{s['losing_months']}/{s['months']} |")

    P("\n## Caveats\n")
    P("- ES bars as the MES proxy (same index points). The live chart is MES1!.")
    P("- Half-days are exited at the last bar's close. Live, the catch-all fires on the "
      "first bar after the session.")
    P("- The stop fills exactly at the stop price plus the slippage ticks. Gaps are not modelled.")
    P("- Research rule check: the 'clean only' rows at cost 0.58 would approximate the "
      "84.3/77.6/68.8% headline. Differences: that ran ruin.py's %-of-peak drawdown, not "
      "Lucid's EOD trail with lock, and netted the cost into the 90-min underwater test.")


if __name__ == "__main__":
    sys.exit(main() or 0)
