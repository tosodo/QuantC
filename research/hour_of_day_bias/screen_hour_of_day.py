#!/usr/bin/env python3
"""Hour-of-day bias screen on NQ and ES. Implements HYPOTHESIS.md (7 Oct 2026) exactly.

    python3 screen_hour_of_day.py                # in-sample (default)
    python3 screen_hour_of_day.py --sample out   # held-out, look ONCE

Interpretation choices made before any result was seen:
  - Window date = New York calendar date of the window start.
  - Cutoff: 70% of NQ valid dates by position, same date applied to ES.
  - Cost check: sign * mean points - cost >= 2 x cost (net reading).
  - Top-3 check: drop the 3 best sign-adjusted days; mean must keep the sign.
  - Halves: first/second half of in-sample days must both have the sign.
  - p-value: two-sided normal approximation.
"""
import argparse, math, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "orb_breakout", "data", "continuous")
ET = "America/New_York"
COST = {"NQ": 0.288, "ES": 0.1152}
HOURS = [h for h in range(24) if h not in (16, 17)]
BONF = 0.05 / 22


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def load(label):
    df = pd.read_csv(os.path.join(DATA, f"{label}.csv"), usecols=["ts_event", "open", "close", "symbol"])
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    df["date"] = ts.dt.date
    df["hour"] = ts.dt.hour
    df = df[df["hour"].isin(HOURS)]
    g = df.groupby(["date", "hour"], sort=True)
    agg = g.agg(n=("open", "size"), nsym=("symbol", "nunique"), o=("open", "first"), c=("close", "last"))
    tot = len(agg)
    ok = agg[(agg["n"] == 60) & (agg["nsym"] == 1)].reset_index()
    ok["r"] = np.log(ok["c"] / ok["o"])
    ok["pts"] = ok["c"] - ok["o"]
    return ok, tot - len(ok), tot


def stats(a):
    a = np.asarray(a, float); n = len(a); m = a.mean(); sd = a.std(ddof=1)
    z = m / (sd / math.sqrt(n))
    return n, m, z, 2 * (1 - phi(abs(z)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", choices=["in", "out"], default="in")
    args = ap.parse_args()
    data = {}
    for L in ("NQ", "ES"):
        d, skipped, tot = load(L); data[L] = d
        print(f"{L}: day-windows {tot}, skipped (missing bar or roll) {skipped}")
    dates = sorted(data["NQ"]["date"].unique())
    cutoff = dates[int(len(dates) * 0.70) - 1]
    print(f"cutoff (NQ dates, position only): in-sample through {cutoff}")
    note = "IN-SAMPLE" if args.sample == "in" else "HELD-OUT (LOOK ONCE)"
    res = {}
    for L in ("NQ", "ES"):
        d = data[L]
        d = d[d["date"] <= cutoff] if args.sample == "in" else d[d["date"] > cutoff]
        means = {h: d[d["hour"] == h]["r"].mean() for h in HOURS}
        avg = np.mean(list(means.values()))
        print(f"\n{'=' * 78}\n{L} {note}  average of the 22 window means: {avg * 1e4:+.3f} bp\n{'=' * 78}")
        print("hour  n     mean_bp   z      p(two)    beatsAvg top3  halves  net>=2xcost")
        for h in HOURS:
            s = d[d["hour"] == h].sort_values("date")
            n, m, z, p = stats(s["r"])
            sg = 1 if m > 0 else -1
            sr = sg * s["r"].values
            beats = sg * (m - avg) > 0
            top3 = np.sort(sr)[:-3].mean() > 0
            half = n // 2
            halves = sr[:half].mean() > 0 and sr[half:].mean() > 0
            net = sg * s["pts"].mean() - COST[L]
            cost_ok = net >= 2 * COST[L]
            c1 = p < BONF
            res[(L, h)] = dict(p=p, sg=sg, c1=c1, rest=beats and top3 and halves and cost_ok, m=m)
            print(f"{h:02d}   {n:4d}  {m * 1e4:+8.3f}  {z:+6.2f}  {p:8.5f}   {str(beats):5}  {str(top3):5}  {str(halves):5}  {cost_ok}")
    print(f"\n{'=' * 78}\nVERDICT ({note}), bar p < {BONF:.5f} on both with same sign\n{'=' * 78}")
    cands = []
    for h in HOURS:
        a, b = res[("NQ", h)], res[("ES", h)]
        p_ok = a["c1"] and b["c1"] and a["sg"] == b["sg"]
        cand = p_ok and a["rest"] and b["rest"]
        if p_ok or cand:
            print(f"hour {h:02d}: p-bar both={p_ok}, other checks NQ={a['rest']} ES={b['rest']} => CANDIDATE: {cand}")
        cands.append(cand)
    print(f"candidates: {sum(cands)}   nearest p (min over hours of max(NQ,ES)): "
          f"{min((max(res[('NQ', h)]['p'], res[('ES', h)]['p']), h) for h in HOURS)}")


if __name__ == "__main__":
    main()
