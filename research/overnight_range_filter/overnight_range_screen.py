#!/usr/bin/env python3
"""
overnight_range_screen.py - runs the plan in HYPOTHESIS.md (this folder) verbatim.
Read-only on local files; sends nothing out.

Reuses the existing ORB trade list (orb_breakout/orb_test.py build_signals, long side,
real Tradovate 'free' cost, same 70/30 split) and tags each long trade with the 09:30 open's
position inside the 01:00-09:29 ET overnight range. TOP (P >= 2/3) vs everything else.

  python3 overnight_range_screen.py                # in-sample only (default)
  python3 overnight_range_screen.py --sample out   # held-out slice, look ONCE
"""
import argparse, math, os, sys
from statistics import NormalDist
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ORB = os.path.join(os.path.dirname(HERE), "orb_breakout")
sys.path.insert(0, ORB)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "index_mean_reversion"))
import orb_test as ot            # noqa: E402
import screen_mean_reversion as smr  # noqa: E402

ND = NormalDist()
THRESH = 0.025  # 0.05 / 2


def overnight_position(path):
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    t = df["ts_event"].dt.tz_convert(ot.ET)
    df["date_et"] = t.dt.date
    df["time_et"] = t.dt.strftime("%H:%M")
    on = df[(df["time_et"] >= "01:00") & (df["time_et"] < "09:30")]
    g = on.groupby("date_et").agg(hi=("high", "max"), lo=("low", "min"), n=("high", "size"))
    opens = df[df["time_et"] == "09:30"].groupby("date_et")["open"].first()
    g["open"] = opens
    g = g.dropna()
    g = g[(g["hi"] > g["lo"]) & (g["n"] >= 400)]   # skip zero range / gappy overnight (of 509 min)
    g["P"] = (g["open"] - g["lo"]) / (g["hi"] - g["lo"])
    return {str(d): p for d, p in g["P"].items()}


def welch(a, b):
    a, b = np.asarray(a), np.asarray(b)
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = (a.mean() - b.mean()) / se
    return z, 1 - ND.cdf(z)   # one-sided, predicted direction (TOP > rest); normal approx, n large


def run(label, path, sample, cutoff):
    df = ot.load(path)
    sig, _ = ot.build_signals(df, cost_points=smr.REAL_COST_POINTS[label]["free"])
    sig = smr.filter_sample(sig, cutoff, sample)
    P = overnight_position(path)
    rows = [(s["date"], s["Rc"], P[s["date"]]) for s in sig if s["side"] == "long" and s["date"] in P]
    d = pd.DataFrame(rows, columns=["date", "R", "P"]).sort_values("date").reset_index(drop=True)
    d["top"] = d["P"] >= 2 / 3
    top, rest = d[d.top], d[~d.top]
    z, p = welch(top["R"], rest["R"])
    print(f"\n--- {label} ({sample}) ---")
    print(f"  long trades with overnight data: {len(d)}  | TOP {len(top)} ({len(top)/len(d):.0%})  other {len(rest)}"
          f"  | bottom-third (descriptive) {(d.P <= 1/3).sum()}")
    print(f"  mean R: TOP {top.R.mean():+.3f}   other {rest.R.mean():+.3f}   all {d.R.mean():+.3f}"
          f"   diff {top.R.mean()-rest.R.mean():+.3f}")
    print(f"  Welch z = {z:+.2f}, one-sided p = {p:.4f}  (bar {THRESH}) -> {'CLEARS' if p < THRESH else 'fails'}")
    # top-3 check: drop the 3 best TOP trades
    t3 = top.sort_values("R", ascending=False).iloc[3:]
    z3, p3 = welch(t3["R"], rest["R"])
    print(f"  drop best 3 TOP trades: TOP mean {t3.R.mean():+.3f}, diff {t3.R.mean()-rest.R.mean():+.3f}, p = {p3:.4f}")
    # split halves (by date) of the diff
    h = len(d) // 2
    for nm, part in (("first half", d.iloc[:h]), ("second half", d.iloc[h:])):
        a, b = part[part.top]["R"], part[~part.top]["R"]
        print(f"  {nm}: TOP {a.mean():+.3f} (n={len(a)}) vs other {b.mean():+.3f} (n={len(b)})  diff {a.mean()-b.mean():+.3f}")
    # economic bar: trades/yr x mean R. TOP-only must be >= unfiltered
    econ_top = len(top) * top.R.mean()
    econ_all = len(d) * d.R.mean()
    print(f"  economic bar (sum of R, TOP-only vs unfiltered): {econ_top:+.1f} vs {econ_all:+.1f} -> "
          f"{'MET' if econ_top >= econ_all else 'NOT met'}")
    return p, top.R.mean() - rest.R.mean(), econ_top >= econ_all


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", choices=("in", "out"), default="in")
    a = ap.parse_args()
    labels = {"NQ (Nasdaq, primary)": "NQ", "ES (S&P500, repl.)": "ES"}
    paths = dict(ot.INSTRUMENTS)
    prim = ot.load(paths["NQ (Nasdaq, primary)"])
    s0, _ = ot.build_signals(prim)
    cutoff = smr.split_dates([s["date"] for s in s0])   # same cut as the existing ORB tests
    print(f"cutoff (same as ORB tests): {cutoff}   sample: {a.sample}")
    res = {l: run(l, paths[l], a.sample, cutoff) for l in labels}
    print("\nVERDICT INPUTS:")
    for l, (p, diff, econ) in res.items():
        print(f"  {labels[l]}: p={p:.4f} diff={diff:+.3f} economic={'met' if econ else 'not met'}")
    ok = all(p < THRESH for p, _, _ in res.values())
    print(f"  Pass bar 1 (both p < {THRESH}): {'YES' if ok else 'NO'}")


if __name__ == "__main__":
    main()
