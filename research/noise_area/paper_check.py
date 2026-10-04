#!/usr/bin/env python3
"""Reference implementation of noise_area_mnq_PAPER.pine, for checking the paper test.

READ-ONLY. Works on any bar size (1-min research CSV or Yahoo 2-min MNQ=F). The price "at" a
half-hour check time m is the close of the bar that ENDS at m, exactly as the Pine script reads it.

  python paper_check.py validate        # must match the 3 Oct research on 5-yr NQ 1-min data
  python paper_check.py yahoo           # expected signals for the last ~5 weeks (Yahoo MNQ=F 2-min)

Points are NQ/MNQ index points; MNQ = $2 per point per contract. No costs (Pine tally has none).
"""
import json, sys, urllib.request
import numpy as np, pandas as pd

ET = "America/New_York"
LOOKBACK = 14
CHECKS = list(range(600, 960, 30))          # 10:00 ... 15:30 ET, minutes of day


def load_research_nq():
    df = pd.read_csv("/Users/osodo.t/QuantC/research/orb_breakout/data/continuous/NQ.csv",
                     usecols=["ts_event", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    return df.drop(columns="ts_event"), 1


def load_yahoo():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/MNQ%3DF?interval=2m&range=60d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    r = json.load(urllib.request.urlopen(req))["chart"]["result"][0]
    df = pd.DataFrame(r["indicators"]["quote"][0])
    df["ts"] = pd.Series(pd.to_datetime(r["timestamp"], unit="s", utc=True)).dt.tz_convert(ET)
    return df.dropna(subset=["close"]), 2


def run(df, barmin, full_sessions_only):
    df = df.copy()
    df["d"] = df.ts.dt.date
    df["mn"] = df.ts.dt.hour * 60 + df.ts.dt.minute
    df = df[(df.mn >= 570) & (df.mn < 960)]
    days = {}
    for d, g in df.groupby("d"):
        if g.mn.iloc[0] != 570:
            continue
        if full_sessions_only and len(g) * barmin < 360:
            continue
        g = g.reset_index(drop=True)
        g["end"] = g.mn + barmin                 # minute at which each bar's close is known
        days[d] = g
    dl = sorted(days)
    # move-from-open at each check time, per day
    mv = pd.DataFrame({d: {m: abs(days[d].close[days[d].end == m].iloc[0] / days[d].open.iloc[0] - 1)
                           for m in CHECKS if (days[d].end == m).any()} for d in dl}).T.reindex(columns=CHECKS)
    sig = mv.rolling(LOOKBACK).mean().shift(1)
    rows = []
    for i, d in enumerate(dl):
        if i == 0:
            continue
        g = days[d]; o = g.open.iloc[0]; pc = days[dl[i - 1]].close.iloc[-1]
        tp = (g.high + g.low + g.close) / 3
        vw = ((tp * g.volume).cumsum() / g.volume.cumsum()).values
        pos, ep, pnl, n = 0, 0.0, 0.0, 0
        acts = []
        for m in CHECKS:
            k = np.flatnonzero(g.end.values == m)
            s = sig.at[d, m]
            if not len(k) or np.isnan(s):
                continue
            k = k[0]; c = g.close.iloc[k]
            ub, lb = max(o, pc) * (1 + s), min(o, pc) * (1 - s)
            before = pos
            if pos == 1 and c < max(ub, vw[k]):
                pnl += c - ep; pos = 0
            elif pos == -1 and c > min(lb, vw[k]):
                pnl += ep - c; pos = 0
            if pos == 0:
                if c > ub: pos, ep = 1, c
                elif c < lb: pos, ep = -1, c
            if pos != before:
                n += pos != 0
                acts.append(f"{m // 60:02d}:{m % 60:02d} {'BUY' if pos == 1 else 'SELL' if pos == -1 else 'EXIT'} @{c:.2f}")
        if pos:
            c = g.close.iloc[-1]; pnl += pos * (c - ep)
            acts.append(f"16:00 EXIT @{c:.2f}")
        if acts:
            rows.append(dict(date=d, trades=n, pnl_pts=round(pnl, 2), actions="; ".join(acts)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "yahoo"
    if mode == "validate":
        df, bm = load_research_nq()
        r = run(df, bm, full_sessions_only=True)
        print(f"NQ 1-min: {len(r)} trading days, {r.trades.sum()} trades, total {r.pnl_pts.sum():+.1f} pts, "
              f"win days {(r.pnl_pts > 0).mean():.0%}")
        r.to_csv("validate_nq.csv", index=False)
    else:
        df, bm = load_yahoo()
        r = run(df, bm, full_sessions_only=False)
        pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 120)
        print(r.to_string(index=False) if len(r) else "no trades in range")
        if len(r):
            print(f"\nTotal {r.pnl_pts.sum():+.2f} pts = ${r.pnl_pts.sum() * 2:+,.0f} at 1 MNQ (no costs)")
        r.to_csv("expected_yahoo.csv", index=False)
