#!/usr/bin/env python3
"""First-half-hour predicts last-half-hour (Gao et al. 2018) on NQ and ES futures.

Implements HYPOTHESIS.md exactly (locked 8 Oct 2026). Read-only on local files.

    python3 screen_intraday_momentum.py                # in-sample (default, safe to re-run)
    python3 screen_intraday_momentum.py --sample out   # held-out slice, look ONCE

Interpretation choices made BEFORE any result was seen (HYPOTHESIS.md wording
was loose on these):
  - Cost check (Section 5, item 4): "mean after real costs is positive and at
    least about twice the cost per trade" is implemented as NET mean (points,
    after the real round-trip cost) >= 2 x cost. The weaker reading (GROSS mean
    >= 2 x cost) is printed alongside but not used for the verdict.
  - Cutoff: the 70/30 split is decided on NQ's cash-session dates (dates having
    a 15:59 bar) by position alone, and the same cutoff date is applied to ES.
  - Normal-approximation one-sided p = 1 - Phi(mean / (sd / sqrt(n))).
  - Slope check: OLS of R_last on Pi, t-statistic of the slope.
"""
import argparse
import math
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "orb_breakout", "data", "continuous")
ET = "America/New_York"
COST_POINTS = {"NQ": 0.288, "ES": 0.1152}  # REAL_COST_POINTS 'free' tier
BONF = 0.05 / 3
NEEDED = {(9, 30), (9, 59), (14, 59), (15, 29), (15, 30), (15, 59)}


def phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def load(path):
    df = pd.read_csv(path, usecols=["ts_event", "open", "close", "symbol"])
    ts = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(ET)
    df["date"] = ts.dt.date
    hm = ts.dt.hour * 100 + ts.dt.minute
    keep = hm.isin([hh * 100 + mm for hh, mm in NEEDED])
    df = df[keep].copy()
    df["hm"] = hm[keep]
    return df


def build_days(df):
    """One dict per date with the bars the plan needs (None if missing)."""
    days = {}
    for date, g in df.groupby("date", sort=True):
        rec = {}
        for _, r in g.iterrows():
            rec[int(r["hm"])] = (r["open"], r["close"], r["symbol"])
        days[date] = rec
    return days


def compute(days):
    """Returns (rows, skips) where rows = list of per-day dicts."""
    dates = sorted(days)
    rows, skips = [], {"P1": 0, "P2": 0, "P3": 0, "no_1530_1559": 0}
    prev_close = None  # (price, symbol) of the previous cash day's 15:59 close
    for d in dates:
        rec = days[d]
        b1530, b1559 = rec.get(1530), rec.get(1559)
        if b1530 is None or b1559 is None or b1530[2] != b1559[2]:
            skips["no_1530_1559"] += 1
            if b1559 is not None:
                prev_close = (b1559[1], b1559[2])
            continue
        o_last, c_last, sym_last = b1530[0], b1559[1], b1559[2]
        r_last = math.log(c_last / o_last)
        pts_last = c_last - o_last
        row = {"date": d, "R_last": r_last, "pts_last": pts_last, "entry": o_last}
        # P1: previous 15:59 close -> 09:59 close
        b959 = rec.get(959)
        if prev_close is not None and b959 is not None and prev_close[1] == b959[2] == sym_last:
            row["P1"] = math.log(b959[1] / prev_close[0])
        else:
            skips["P1"] += 1
        # P2: 14:59 close -> 15:29 close
        b1459, b1529 = rec.get(1459), rec.get(1529)
        if b1459 is not None and b1529 is not None and b1459[2] == b1529[2] == sym_last:
            row["P2"] = math.log(b1529[1] / b1459[1])
        else:
            skips["P2"] += 1
        # P3: 09:30 open -> 09:59 close
        b930 = rec.get(930)
        if b930 is not None and b959 is not None and b930[2] == b959[2] == sym_last:
            row["P3"] = math.log(b959[1] / b930[0])
        else:
            skips["P3"] += 1
        rows.append(row)
        prev_close = (c_last, sym_last)
    return rows, skips


def split_cutoff(dates, frac=0.70):
    dates = sorted(set(dates))
    cut = int(len(dates) * frac)
    return dates[cut - 1]


def stats(vals):
    a = np.asarray(vals, float)
    n = len(a)
    m = a.mean()
    sd = a.std(ddof=1)
    z = m / (sd / math.sqrt(n))
    return n, m, sd, z, 1.0 - phi(z)


def slope_t(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    b = ((x - xm) * (y - ym)).sum() / sxx
    resid = y - ym - b * (x - xm)
    se = math.sqrt((resid ** 2).sum() / (len(x) - 2) / sxx)
    return b, b / se


def analyse(label, rows, sample_note):
    cost = COST_POINTS[label]
    out = {}
    print(f"\n{'=' * 78}\n{label}  {sample_note}\n{'=' * 78}")
    allR = [r["R_last"] for r in rows]
    print(f"days with a valid 15:30-15:59 target: {len(rows)}   "
          f"always-long mean R_last: {np.mean(allR) * 1e4:+.2f} bp "
          f"({np.mean([r['pts_last'] for r in rows]):+.2f} pts)")
    for p in ("P1", "P2", "P3"):
        sub = [r for r in rows if p in r]
        if len(sub) < 30:
            print(f"{p}: too few days ({len(sub)})")
            out[p] = None
            continue
        sgn = np.array([1.0 if r[p] > 0 else -1.0 for r in sub if r[p] != 0])
        sub = [r for r in sub if r[p] != 0]
        R = np.array([r["R_last"] for r in sub])
        pts = np.array([r["pts_last"] for r in sub])
        sR = sgn * R
        sP = sgn * pts
        n, m, sd, z, pval = stats(sR)
        long_mean = R.mean()
        b, tb = slope_t([r[p] for r in sub], R)
        net_mean_pts = sP.mean() - cost
        # top-3-days check and halves
        order = np.sort(sR)
        no_top3 = order[:-3].mean()
        h = n // 2
        h1, h2 = sR[:h].mean(), sR[h:].mean()
        c1 = pval < BONF
        c2 = (m > long_mean) and (tb > 2.0)
        c3 = (no_top3 > 0) and (h1 > 0) and (h2 > 0)
        c4 = net_mean_pts >= 2.0 * cost
        print(f"\n{p}: n={n}  mean sign*R = {m * 1e4:+.3f} bp  z={z:+.2f}  one-sided p={pval:.4f}  (bar {BONF:.4f})")
        print(f"    always-long mean {long_mean * 1e4:+.3f} bp; slope t={tb:+.2f}; "
              f"hit rate {(sR > 0).mean() * 100:.1f}%")
        print(f"    mean without top 3 days {no_top3 * 1e4:+.3f} bp; first half {h1 * 1e4:+.3f} bp, second half {h2 * 1e4:+.3f} bp")
        print(f"    points per trade: gross {sP.mean():+.3f}, cost {cost:.4f}, net {net_mean_pts:+.3f}  "
              f"(net >= 2x cost: {c4}; gross >= 2x cost: {sP.mean() >= 2 * cost})")
        print(f"    checks: p<bar {c1} | beats drift & slope t>2 {c2} | top3/halves {c3} | cost {c4}")
        out[p] = {"p": pval, "m": m, "mean_pts_gross": sP.mean(), "c1": c1, "c2": c2, "c3": c3, "c4": c4}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", choices=["in", "out"], default="in")
    args = ap.parse_args()

    per = {}
    for label in ("NQ", "ES"):
        df = load(os.path.join(DATA, f"{label}.csv"))
        days = build_days(df)
        rows, skips = compute(days)
        per[label] = (rows, skips, sorted(days))
        print(f"{label}: cash-session days seen {len(days)}; skips {skips}")

    cutoff = split_cutoff([r["date"] for r in per["NQ"][0]])
    print(f"70/30 cutoff (decided on NQ valid-target dates, position only): in-sample through {cutoff}")
    note = f"IN-SAMPLE (through {cutoff})" if args.sample == "in" else f"*** HELD-OUT (after {cutoff}) - LOOK ONCE ***"

    res = {}
    for label in ("NQ", "ES"):
        rows = per[label][0]
        rows = [r for r in rows if (r["date"] <= cutoff)] if args.sample == "in" else [r for r in rows if r["date"] > cutoff]
        res[label] = analyse(label, rows, note)

    print(f"\n{'=' * 78}\nVERDICT ({note})\n{'=' * 78}")
    for p in ("P1", "P2", "P3"):
        a, b = res["NQ"].get(p), res["ES"].get(p)
        if a is None or b is None:
            print(f"{p}: not evaluable")
            continue
        both_p = a["c1"] and b["c1"] and a["m"] > 0 and b["m"] > 0
        cand = both_p and a["c2"] and b["c2"] and a["c3"] and b["c3"] and a["c4"] and b["c4"]
        print(f"{p}: p-bar both={both_p}  | drift+slope {a['c2'] and b['c2']} | robust {a['c3'] and b['c3']} "
              f"| cost {a['c4'] and b['c4']}  => CANDIDATE: {cand}")


if __name__ == "__main__":
    main()
