#!/usr/bin/env python3
"""
divergence_filter_test.py - tests the rules in DIVERGENCE_HYPOTHESIS.md.

Rule A: skip the ORB entry when an active bearish RSI divergence zone sits
within 10 pts above it. Rule B: on down-break-first days, only trade if a
bullish divergence was confirmed during the morning dip.

Zones come from 5m bars built from the full Globex 1m stream. A pivot at
bar i is only used from the close of bar i+right, and the tracker is fed bar
by bar in time order, so nothing after the entry decision can leak in
(ops/tests/test_divergence.py checks this by truncating the data).

Needs the local data (gitignored): data/continuous/ES.csv, as for
live_rules_backtest.py. Run from this folder:

    python3 divergence_filter_test.py > divergence_report.md
"""
import argparse
import csv
import os
import random
import sys
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ops"))
from shadow_day import replay_day  # noqa: E402

ET = ZoneInfo("America/New_York")
BAR_S = 300           # 5m signal bars
KEEP = 10             # zones of each kind kept, as the indicator shows
RANGE_MIN, RANGE_MAX = 5, 60   # bars between the two pivots of a divergence
PRIMARY = dict(rsi_len=14, piv=5, dist=10.0)
GRID = [dict(rsi_len=r, piv=p, dist=d) for r in (9, 14) for p in (3, 5) for d in (5.0, 10.0, 20.0)]
BASE_COST, BASE_SLIP = 2.50, 1
PERMS = 10000


# ---------- data ----------

def load_bars(path):
    """ES.csv (Databento ohlcv-1m, ts_event = bar open) -> time-sorted 1m bars."""
    from live_rules_backtest import parse_ts
    out = []
    with open(path) as f:
        for row in csv.DictReader(f):
            out.append({"t": parse_ts(row["ts_event"]), "o": float(row["open"]),
                        "h": float(row["high"]), "l": float(row["low"]),
                        "c": float(row["close"])})
    out.sort(key=lambda b: b["t"])
    return out


def to_5m(bars):
    """1m bars -> 5m bars with 'close_t' = the time the 5m bar is complete."""
    out, cur = [], None
    for b in bars:
        k = b["t"] - b["t"] % BAR_S
        if cur is None or cur["t"] != k:
            cur = {"t": k, "close_t": k + BAR_S, "o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]}
            out.append(cur)
        else:
            cur["h"] = max(cur["h"], b["h"])
            cur["l"] = min(cur["l"], b["l"])
            cur["c"] = b["c"]
    return out


def days_from(bars):
    days = defaultdict(list)
    for b in bars:
        days[datetime.fromtimestamp(b["t"], ET).date().isoformat()].append(b)
    return days


# ---------- zones ----------

class ZoneTracker:
    """Feed 5m bars in time order with update(). After each call the state
    only reflects bars already fed, so it can be queried at any moment."""

    def __init__(self, rsi_len=14, piv=5):
        self.n, self.piv = rsi_len, piv
        self.bars, self.rsi = [], []
        self.avg_g = self.avg_l = None
        self.prev_c = None
        self.ph = self.pl = None          # last RSI pivot (index) of each kind
        self.bear = deque(maxlen=KEEP)    # zone dicts, newest last
        self.bull = deque(maxlen=KEEP)
        self.bull_conf = []               # confirm times of every bullish divergence

    def _rsi_step(self, c):
        if self.prev_c is None:
            self.prev_c = c
            return None
        ch = c - self.prev_c
        self.prev_c = c
        g, l = max(ch, 0.0), max(-ch, 0.0)
        if self.avg_g is None:
            self._seed = getattr(self, "_seed", []) + [(g, l)]
            if len(self._seed) < self.n:
                return None
            self.avg_g = sum(x for x, _ in self._seed) / self.n
            self.avg_l = sum(y for _, y in self._seed) / self.n
        else:
            self.avg_g = (self.avg_g * (self.n - 1) + g) / self.n
            self.avg_l = (self.avg_l * (self.n - 1) + l) / self.n
        if self.avg_l == 0:
            return 100.0
        return 100 - 100 / (1 + self.avg_g / self.avg_l)

    def update(self, bar):
        # 1. existing zones: invalidated by this bar's close
        for z in self.bear:
            if z["broken_t"] is None and bar["c"] > z["top"]:
                z["broken_t"] = bar["close_t"]
        for z in self.bull:
            if z["broken_t"] is None and bar["c"] < z["bot"]:
                z["broken_t"] = bar["close_t"]
        # 2. append the bar and its RSI
        self.bars.append(bar)
        self.rsi.append(self._rsi_step(bar["c"]))
        # 3. the bar `piv` back can now be confirmed as a pivot
        i = len(self.bars) - 1 - self.piv
        if i - self.piv < 0:
            return
        win = self.rsi[i - self.piv:i + self.piv + 1]
        if any(v is None for v in win):
            return
        r = self.rsi[i]
        left, right = win[:self.piv], win[self.piv + 1:]
        conf_t = bar["close_t"]
        if r > max(left) and r >= max(right):
            p = self.ph
            if p is not None and RANGE_MIN <= i - p <= RANGE_MAX \
                    and r < self.rsi[p] and self.bars[i]["h"] > self.bars[p]["h"]:
                b = self.bars[i]
                self.bear.append({"i": i, "conf_t": conf_t, "top": b["h"],
                                  "bot": max(b["o"], b["c"]), "broken_t": None})
            self.ph = i
        if r < min(left) and r <= min(right):
            p = self.pl
            if p is not None and RANGE_MIN <= i - p <= RANGE_MAX \
                    and r > self.rsi[p] and self.bars[i]["l"] < self.bars[p]["l"]:
                b = self.bars[i]
                self.bull.append({"i": i, "conf_t": conf_t, "top": min(b["o"], b["c"]),
                                  "bot": b["l"], "broken_t": None})
                self.bull_conf.append(conf_t)
            self.pl = i

    def bear_overhead(self, entry, dist):
        """An unbroken bearish zone overlapping [entry, entry + dist]."""
        return any(z["broken_t"] is None and z["top"] >= entry and z["bot"] <= entry + dist
                   for z in self.bear)

    def bull_since(self, t0):
        return any(t >= t0 for t in self.bull_conf)


# ---------- trades ----------

def decision_t(day, hhmm):
    """Entry decision = close of the 1m signal bar (bar open + 60 s), in UTC s."""
    d = datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=ET)
    return int(d.timestamp()) + 60


def session_open_t(day):
    return int(datetime.fromisoformat(f"{day}T09:30:00").replace(tzinfo=ET).timestamp())


def build_trades(days):
    out = []
    for d in sorted(days):
        r = replay_day(days[d], d)
        if r.get("state") == "open":
            r.update(exit=r["last_close"], exit_reason="catch_all_flatten",
                     pts=r["last_close"] - r["entry"], state="entry")
        if r.get("state") != "entry":
            continue
        out.append({"date": d, "dbf": bool(r["down_break_first"]), "entry": r["entry"],
                    "pts": r["pts"], "mae_pts": r["mae_pts"],
                    "dec_t": decision_t(d, r["entry_bar_open_et"])})
    return out


def tag_trades(trades, bars5, rsi_len, piv, dist):
    """For each trade: bear_overhead (rule A) and bull_dip (rule B), using
    only 5m bars complete at the decision time."""
    zt = ZoneTracker(rsi_len, piv)
    k, tags = 0, []
    for t in sorted(trades, key=lambda x: x["dec_t"]):
        while k < len(bars5) and bars5[k]["close_t"] <= t["dec_t"]:
            zt.update(bars5[k])
            k += 1
        tags.append({"date": t["date"], "bear_overhead": zt.bear_overhead(t["entry"], dist),
                     "bull_dip": zt.bull_since(session_open_t(t["date"]))})
    return {x["date"]: x for x in tags}


# ---------- evaluation ----------

def net(t, cost=BASE_COST, slip=BASE_SLIP):
    from live_rules_backtest import net as lr_net
    return lr_net({"pts": t["pts"]}, cost, slip)


def perm_p(all_pnls, removed_total, m, n=PERMS, seed=7):
    """Share of random m-trade removals whose total is <= the actual removed total."""
    if m == 0:
        return float("nan")
    rng = random.Random(seed)
    hits = sum(sum(rng.sample(all_pnls, m)) <= removed_total for _ in range(n))
    return hits / n


def judge(kept, removed, universe):
    """Pre-registered checks 1-3 (4 is the pass-rate table)."""
    rem = [net(t) for t in removed]
    tot = sum(rem)
    p = perm_p([net(t) for t in universe], tot, len(rem))
    years = defaultdict(float)
    for t in removed:
        years[t["date"][:4]] += net(t)
    losing_years = sum(v < 0 for v in years.values())
    return dict(n_removed=len(rem), removed_total=tot, p=p, years=dict(sorted(years.items())),
                losing_years=losing_years,
                ok=(tot < 0 and p < 0.05 and losing_years >= 4))


def main():
    from live_rules_backtest import summarise, pass_rates
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    ap.add_argument("--sims", type=int, default=2000)
    a = ap.parse_args()

    bars = load_bars(a.data)
    bars5 = to_5m(bars)
    trades = build_trades(days_from(bars))
    P = print
    P("# RSI divergence filter on the live ORB rules\n")
    P(f"Data: `{os.path.relpath(a.data, HERE)}`, {trades[0]['date']} to {trades[-1]['date']}, "
      f"{len(trades)} trades. Rules and pass criteria: DIVERGENCE_HYPOTHESIS.md. "
      f"Costs ${BASE_COST:.2f}/RT, {BASE_SLIP} tick exit slippage.\n")

    tags = tag_trades(trades, bars5, PRIMARY["rsi_len"], PRIMARY["piv"], PRIMARY["dist"])

    # Rule A
    keepA = [t for t in trades if not tags[t["date"]]["bear_overhead"]]
    remA = [t for t in trades if tags[t["date"]]["bear_overhead"]]
    jA = judge(keepA, remA, trades)
    # Rule B (down-break-first trades only)
    dbf = [t for t in trades if t["dbf"]]
    remB = [t for t in dbf if not tags[t["date"]]["bull_dip"]]
    keepB = [t for t in trades if t not in remB]
    jB = judge(keepB, remB, dbf)

    P("## Primary spec (RSI 14, pivots 5/5, 10 pts)\n")
    P("| set | n | win % | avg $ | total $ | PF |")
    P("|---|---|---|---|---|---|")
    for name, ts in (("baseline (live rules)", trades), ("A: kept", keepA), ("A: removed", remA),
                     ("B: kept", keepB), ("B: removed (dbf, no bull dip)", remB)):
        s = summarise([net(t) for t in ts])
        P(f"| {name} | {s['n']} | {s['win']:.1f} | {s['avg']:.2f} | {s['total']:.0f} | {s['pf']:.2f} |")

    P("\n## Pre-registered checks\n")
    P("| rule | removed | removed total $ | perm p | losing years | 1-3 pass |")
    P("|---|---|---|---|---|---|")
    for name, j in (("A", jA), ("B", jB)):
        P(f"| {name} | {j['n_removed']} | {j['removed_total']:.0f} | {j['p']:.4f} | "
          f"{j['losing_years']}/{len(j['years'])} | {'yes' if j['ok'] else 'no'} |")
    P("\nRemoved P&L by year: A " + ", ".join(f"{y} {v:.0f}" for y, v in jA["years"].items())
      + "; B " + ", ".join(f"{y} {v:.0f}" for y, v in jB["years"].items()) + ".\n")

    P("## Check 4: Lucid pass rate\n")
    P("| set | rolling pass % (starts) | bootstrap pass % | median trades |")
    P("|---|---|---|---|")
    rates = {}
    for name, ts in (("baseline", trades), ("A", keepA), ("B", keepB)):
        roll, n, boot, med = pass_rates([{"pts": t["pts"], "mae_pts": t["mae_pts"]} for t in ts],
                                        BASE_COST, BASE_SLIP, a.sims)
        rates[name] = roll
        P(f"| {name} | {roll:.1f} ({n}) | {boot:.1f} | {med} |")

    adoptA = jA["ok"] and rates["A"] >= rates["baseline"]
    adoptB = jB["ok"] and rates["B"] >= rates["baseline"]
    P(f"\n**Verdict:** rule A {'PASSES' if adoptA else 'is not adopted'}; "
      f"rule B {'PASSES' if adoptB else 'is not adopted'}.\n")

    P("## Sensitivity grid (rule A; reported, not used to choose)\n")
    P("| RSI | pivots | dist | removed | removed total $ | perm p | losing years |")
    P("|---|---|---|---|---|---|---|")
    for g in GRID:
        tg = tag_trades(trades, bars5, g["rsi_len"], g["piv"], g["dist"])
        rem = [t for t in trades if tg[t["date"]]["bear_overhead"]]
        j = judge([], rem, trades)
        P(f"| {g['rsi_len']} | {g['piv']} | {g['dist']:.0f} | {j['n_removed']} | "
          f"{j['removed_total']:.0f} | {j['p']:.4f} | {j['losing_years']}/{len(j['years'])} |")

    P("\n## Caveats\n")
    P("- ES bars as the MES proxy; plain RSI stands in for the indicator's momentum RSI.")
    P("- Zones use completed 5m bars only, so a divergence confirmed inside the "
      "current 5m bar is not seen until that bar closes.")


if __name__ == "__main__":
    sys.exit(main() or 0)
