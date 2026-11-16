#!/usr/bin/env python3
"""
edge_search_test.py - runs the tests locked in EDGE_SEARCH_HYPOTHESIS.md.

S1 Noise Area momentum, S2 last-half-hour momentum, S3 ORB with an ATR stop,
S4 opening-range width gate on the live ORB, S5 cushion-scaled size.
Every signal uses only bars closed before the entry bar (no look-ahead;
ops/tests/test_edge_search.py checks S1 by truncating the day).

Needs the local data (gitignored): data/continuous/ES.csv. Run from this
folder:

    python3 edge_search_test.py > edge_search_report.md
"""
import argparse
import csv
import math
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ops"))
import shadow_day as sd  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402

ET = lrb.ET
PV, TICK = lrb.PV, lrb.TICK
BASE_COST, BASE_SLIP = 2.50, 1
STRESS_COST, STRESS_SLIP = 4.00, 2
OOS_AFTER = "2025-02-14"
P_BAR = 0.05 / 4
MIN_ANNUAL, MAX_DD = 3000.0, 2500.0
PERMS = 10000
SESSION_MIN = 390          # regular session 9:30-15:59 = minutes 0..389
NOISE_HIST, ATR_HIST, WIDTH_HIST = 14, 14, 20


# ---------- data ----------

def load(path):
    """ES.csv -> {ET date: [bars]}, each bar with m = minutes since 9:30 ET."""
    days = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            t = lrb.parse_ts(row["ts_event"])
            dt = datetime.fromtimestamp(t, ET)
            days[dt.date().isoformat()].append({
                "t": t, "o": float(row["open"]), "h": float(row["high"]),
                "l": float(row["low"]), "c": float(row["close"]),
                "v": float(row.get("volume") or 0), "m": dt.hour * 60 + dt.minute - 570})
    for d in days:
        days[d].sort(key=lambda b: b["t"])
    return days


def regular(bars):
    """{m: bar} for the regular session 9:30-15:59."""
    return {b["m"]: b for b in bars if 0 <= b["m"] < SESSION_MIN}


def session_table(days):
    """dates (sorted) that have a regular session, with reg dict and prior close."""
    out, prev = [], None
    for d in sorted(days):
        reg = regular(days[d])
        if len(reg) < 15 or 0 not in reg:
            continue
        out.append({"date": d, "reg": reg, "prev_close": prev,
                    "full": len(reg) >= 385,
                    "range": max(b["h"] for b in reg.values()) - min(b["l"] for b in reg.values())})
        prev = reg[max(reg)]["c"]
    return out


def trade(date, side, entry, exit_, mae, entry_m, exit_m, entry_t=0):
    return {"date": date, "side": side, "entry": entry, "exit": exit_, "entry_m": entry_m,
            "exit_m": exit_m, "entry_t": entry_t,
            "pts": (exit_ - entry) * side, "mae_pts": max(0.0, mae)}


# ---------- S1 Noise Area ----------

def noise_bands(sess, i):
    """sigma(m) for the session at index i: mean over the previous 14 full sessions."""
    hist = [s for s in sess[:i] if s["full"]][-NOISE_HIST:]
    if len(hist) < NOISE_HIST:
        return None
    sig = {}
    for m in range(SESSION_MIN):
        vals = [abs(h["reg"][m]["c"] / h["reg"][0]["o"] - 1) for h in hist if m in h["reg"]]
        if len(vals) >= 10:
            sig[m] = sum(vals) / len(vals)
    return sig


def s1_day(s, sig):
    reg, out = s["reg"], []
    if s["prev_close"] is None or 0 not in reg:
        return out
    o = reg[0]["o"]
    hi_ref, lo_ref = max(o, s["prev_close"]), min(o, s["prev_close"])
    last_m = max(reg)
    pos = None
    pv = vol = 0.0
    for m in sorted(reg):
        b = reg[m]
        typ = (b["h"] + b["l"] + b["c"]) / 3
        pv += typ * b["v"]
        vol += b["v"]
        vwap = pv / vol if vol > 0 else typ
        closed = False
        if pos:
            pos["lo"], pos["hi"] = min(pos["lo"], b["l"]), max(pos["hi"], b["h"])
            side = pos["side"]
            if m == last_m or (side > 0 and b["c"] < vwap) or (side < 0 and b["c"] > vwap):
                mae = pos["entry"] - pos["lo"] if side > 0 else pos["hi"] - pos["entry"]
                out.append(trade(s["date"], side, pos["entry"], b["c"], mae, pos["m"], m, pos["t"]))
                pos, closed = None, True
        if pos is None and not closed and 29 <= m <= 359 and (m + 1) % 30 == 0 and m in sig:
            up = hi_ref * (1 + sig[m])
            dn = lo_ref * (1 - sig[m])
            side = 1 if b["c"] > up else (-1 if b["c"] < dn else 0)
            if side:
                pos = {"side": side, "entry": b["c"], "m": m, "t": b["t"] + 60,
                       "lo": b["c"], "hi": b["c"]}
    return out


def s1_trades(sess):
    out = []
    for i, s in enumerate(sess):
        sig = noise_bands(sess, i)
        if sig:
            out += s1_day(s, sig)
    return out


# ---------- S2 last half hour ----------

def s2_trades(sess):
    out = []
    for s in sess:
        reg, pc = s["reg"], s["prev_close"]
        if pc is None or 29 not in reg or 359 not in reg or 389 not in reg:
            continue
        r = reg[29]["c"] / pc - 1
        side = 1 if r > 0 else (-1 if r < 0 else 0)
        if not side:
            continue
        entry, ex = reg[359]["c"], reg[389]["c"]
        held = [reg[m] for m in range(360, 390) if m in reg]
        mae = (entry - min(b["l"] for b in held)) if side > 0 else (max(b["h"] for b in held) - entry)
        out.append(trade(s["date"], side, entry, ex, mae, 359, 389, reg[359]["t"] + 60))
    return out


# ---------- live ORB, S3, S4 ----------

def orb_trades(days, stop_by_date=None):
    """The live ORB through the journal's replay_day. stop_by_date overrides
    the stop distance per date (None = the live 125 pts); dates missing from
    it are skipped."""
    live_stop = sd.STOP_PTS
    out = []
    try:
        for d in sorted(days):
            if stop_by_date is not None:
                if d not in stop_by_date:
                    continue
                sd.STOP_PTS = stop_by_date[d]
            r = sd.replay_day(days[d], d)
            if r["state"] == "no_range":
                continue
            if r["state"] == "open":
                r.update(exit=r["last_close"], exit_reason="catch_all_flatten",
                         pts=r["last_close"] - r["entry"], state="entry")
            if r["state"] == "entry":
                out.append({"date": d, "side": 1, "entry": r["entry"], "exit": r["exit"],
                            "entry_m": 0, "exit_m": 0, "entry_t": 0,
                            "pts": round(r["pts"], 2), "mae_pts": round(r["mae_pts"], 2),
                            "exit_reason": r["exit_reason"]})
    finally:
        sd.STOP_PTS = live_stop
    return out


def atr_stops(sess, mult):
    out = {}
    for i, s in enumerate(sess):
        hist = [h for h in sess[:i] if h["full"]][-ATR_HIST:]
        if len(hist) == ATR_HIST:
            out[s["date"]] = mult * sum(h["range"] for h in hist) / ATR_HIST
    return out


def narrow_dates(sess, window=WIDTH_HIST):
    """Dates whose 9:30-9:44 range is below the median of the previous `window`
    sessions' ranges, and the set of dates that have enough history."""
    rng = {}
    for s in sess:
        bars = [s["reg"][m] for m in range(15) if m in s["reg"]]
        if len(bars) == 15:
            rng[s["date"]] = max(b["h"] for b in bars) - min(b["l"] for b in bars)
    dates = [s["date"] for s in sess if s["date"] in rng]
    narrow, known = set(), set()
    for i, d in enumerate(dates):
        if i >= window:
            known.add(d)
            if rng[d] < median(rng[x] for x in dates[i - window:i]):
                narrow.add(d)
    return narrow, known


# ---------- statistics ----------

def net(t, cost=BASE_COST, slip=BASE_SLIP):
    return lrb.net(t, cost, slip)


def daily(trades, dates, cost=BASE_COST, slip=BASE_SLIP):
    d = defaultdict(float)
    for t in trades:
        d[t["date"]] += net(t, cost, slip)
    return [d.get(x, 0.0) for x in dates]


def block_p(series, block=5, n=PERMS, seed=11):
    """P(mean of a block-bootstrapped zero-mean copy >= observed mean)."""
    m = len(series)
    mean = sum(series) / m
    pref = [0.0]
    for x in series + series:
        pref.append(pref[-1] + x - mean)
    k = math.ceil(m / block)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n):
        tot = 0.0
        for _ in range(k):
            s = rng.randrange(m)
            tot += pref[s + block] - pref[s]
        hits += tot / (k * block) >= mean
    return hits / n


def perm_p(all_pnls, removed_total, m, n=PERMS, seed=7):
    if m == 0:
        return float("nan")
    rng = random.Random(seed)
    return sum(sum(rng.sample(all_pnls, m)) <= removed_total for _ in range(n)) / n


def max_dd(trades, cost=BASE_COST, slip=BASE_SLIP):
    eq = peak = dd = 0.0
    for t in sorted(trades, key=lambda x: (x["date"], x["entry_t"])):
        eq += net(t, cost, slip)
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def by_year(trades, cost=BASE_COST, slip=BASE_SLIP):
    y = defaultdict(float)
    for t in trades:
        y[t["date"][:4]] += net(t, cost, slip)
    return dict(sorted(y.items()))


def years_span(dates):
    a, b = datetime.fromisoformat(dates[0]), datetime.fromisoformat(dates[-1])
    return max((b - a).days / 365.25, 1e-9)


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else float("nan")


def day_trades(trades, cost=BASE_COST, slip=BASE_SLIP):
    """One pseudo-trade per day for the Lucid simulator (it takes one entry a
    day): points summed, extra round turns charged inside the points, and the
    worst intraday loss including earlier realised results."""
    by = defaultdict(list)
    for t in trades:
        by[t["date"]].append(t)
    out = []
    for d in sorted(by):
        ts = sorted(by[d], key=lambda x: x["entry_t"])
        cum, worst = 0.0, 0.0
        for t in ts:
            worst = max(worst, t["mae_pts"] - cum)
            cum += t["pts"]
        extra = (len(ts) - 1) * (slip * TICK + cost / PV)
        out.append({"date": d, "pts": cum - extra, "mae_pts": worst})
    return out


def lucid(trades, sims):
    return lrb.pass_rates(day_trades(trades), BASE_COST, BASE_SLIP, sims)


def evaluate(name, trades, dates, live_day, sims, perms):
    ser = daily(trades, dates)
    yrs = years_span(dates)
    tot = sum(ser)
    ys = by_year(trades)
    oos = sum(net(t) for t in trades if t["date"] > OOS_AFTER)
    stress = sum(net(t, STRESS_COST, STRESS_SLIP) for t in trades)
    res = dict(name=name, n=len(trades), per_year=len(trades) / yrs, total=tot, annual=tot / yrs,
               p=block_p(ser, n=perms), pos_years=sum(v > 0 for v in ys.values()), n_years=len(ys),
               years=ys, oos=oos, dd=max_dd(trades), stress=stress,
               corr=corr(ser, live_day), lucid=lucid(trades, sims),
               win=100 * sum(net(t) > 0 for t in trades) / max(len(trades), 1))
    res["checks"] = [res["annual"] >= MIN_ANNUAL, res["p"] < P_BAR, res["pos_years"] >= 4,
                     oos > 0, res["dd"] <= MAX_DD, stress > 0]
    res["ok"] = all(res["checks"])
    return res


# ---------- S5 cushion-scaled size ----------

def size_for(cushion, worst_loss_usd, cap=3):
    return max(1, min(cap, int(0.5 * cushion // (worst_loss_usd + BASE_COST))))


def size_run(seq, worst_loss_usd, dynamic):
    """Same walk as live_rules_backtest.lucid_run, with a size per trade."""
    bal = hwm = lrb.START_BAL
    floor = hwm - lrb.TRAIL
    for i, (pnl, mae) in enumerate(seq, 1):
        n = size_for(bal - floor, worst_loss_usd) if dynamic else 1
        if bal - n * mae <= floor:
            return "fail", i
        bal += n * pnl
        if bal <= floor:
            return "fail", i
        if bal >= lrb.TARGET:
            return "pass", i
        hwm = max(hwm, bal)
        floor = min(max(floor, hwm - lrb.TRAIL), lrb.LOCK_FLOOR)
    return "open", len(seq)


def sizing_table(trades, sims, seed=1):
    worst = sd.STOP_PTS * PV + (BASE_SLIP * TICK) * PV
    seq = [(net(t), (t["mae_pts"] + BASE_SLIP * TICK) * PV + BASE_COST)
           for t in sorted(trades, key=lambda x: x["date"])]
    out = {}
    for label, dyn in (("fixed 1 MES", False), ("cushion-scaled (max 3)", True)):
        res = [size_run(seq[i:], worst, dyn) for i in range(len(seq))]
        done = [r for r in res if r[0] != "open"]
        roll_pass = 100 * sum(r[0] == "pass" for r in done) / len(done) if done else float("nan")
        roll_fail = 100 * sum(r[0] == "fail" for r in done) / len(done) if done else float("nan")
        rng = random.Random(seed)
        outcomes, used = [], []
        for _ in range(sims):
            o, k = size_run([rng.choice(seq) for _ in range(2000)], worst, dyn)
            outcomes.append(o)
            if o == "pass":
                used.append(k)
        used.sort()
        out[label] = dict(roll_pass=roll_pass, roll_fail=roll_fail, n_done=len(done),
                          boot_pass=100 * outcomes.count("pass") / sims,
                          boot_fail=100 * outcomes.count("fail") / sims,
                          median=used[len(used) // 2] if used else None)
    return out


# ---------- report ----------

def f(x, nd=0):
    return "nan" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:,.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--perms", type=int, default=PERMS)
    a = ap.parse_args()
    P = print
    shown = os.path.relpath(a.data, HERE)
    if shown.startswith(".."):
        shown = a.data

    days = load(a.data)
    sess = session_table(days)
    dates = [s["date"] for s in sess]
    base = orb_trades(days)
    live_day = daily(base, dates)
    P("# Edge search: S1-S5 on the live ORB history\n")
    P(f"Data: `{shown}`, {dates[0]} to {dates[-1]}, {len(dates)} sessions. "
      f"Rules and bars: EDGE_SEARCH_HYPOTHESIS.md. Base costs ${BASE_COST:.2f}/RT + {BASE_SLIP} tick; "
      f"stress ${STRESS_COST:.2f} + {STRESS_SLIP} ticks. p bar {P_BAR:.4f}.\n")

    cands = [("S1 Noise Area (long+short)", s1_trades(sess)),
             ("S1 Noise Area (long only)", [t for t in s1_trades(sess) if t["side"] > 0]),
             ("S2 last half hour", s2_trades(sess)),
             ("S3 ORB, 1.0 x ATR stop", orb_trades(days, atr_stops(sess, 1.0)))]
    P("## S1-S3 against the six adoption criteria\n")
    P("| candidate | trades/yr | win % | annual $ | block p | + years | OOS $ | max DD $ | stress $ | corr live | pass rolling (n) / boot / median |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    results = []
    for name, tr in cands:
        r = evaluate(name, tr, dates, live_day, a.sims, a.perms)
        results.append(r)
        roll, nd, boot, med = r["lucid"]
        P(f"| {name} | {f(r['per_year'])} | {f(r['win'], 1)} | {f(r['annual'])} | {r['p']:.4f} | "
          f"{r['pos_years']}/{r['n_years']} | {f(r['oos'])} | {f(r['dd'])} | {f(r['stress'])} | "
          f"{f(r['corr'], 2)} | {f(roll, 1)} ({nd}) / {f(boot, 1)} / {f(med)} |")
    P("\nCriteria met (annual >= $3,000, p < bar, >= 4 positive years, OOS > 0, DD <= $2,500, stress > 0):\n")
    P("| candidate | annual | p | years | OOS | DD | stress | adopted |")
    P("|---|---|---|---|---|---|---|---|")
    for r in results:
        c = ["yes" if x else "NO" for x in r["checks"]]
        P(f"| {r['name']} | {c[0]} | {c[1]} | {c[2]} | {c[3]} | {c[4]} | {c[5]} | {'YES' if r['ok'] else 'no'} |")
    P("\nNet by year (base costs):\n")
    for r in results:
        P(f"- {r['name']}: " + ", ".join(f"{y} {v:,.0f}" for y, v in r["years"].items()))

    # S3 vs the live ORB on the same days
    s3_days = set(atr_stops(sess, 1.0))
    same = [t for t in base if t["date"] in s3_days]
    P(f"\nLive ORB on the same {len(s3_days)} days (S3 comparison): "
      f"{len(same)} trades, ${sum(net(t) for t in same):,.0f}; "
      f"S3: {results[3]['n']} trades, ${results[3]['total']:,.0f}.\n")
    P("S3 multiplier sensitivity (reported, not used to choose):\n")
    P("| ATR multiple | trades | net $ | win % |")
    P("|---|---|---|---|")
    for mult in (0.5, 1.0, 1.5, 2.0):
        tr = orb_trades(days, atr_stops(sess, mult))
        P(f"| {mult} | {len(tr)} | {f(sum(net(t) for t in tr))} | "
          f"{f(100 * sum(net(t) > 0 for t in tr) / max(len(tr), 1), 1)} |")

    # S4 gate
    P("\n## S4 opening-range width gate on the live ORB\n")
    P("| window | removed | removed $ | perm p | losing years | pass boot % (with / without) | adopted |")
    P("|---|---|---|---|---|---|---|")
    for window in (WIDTH_HIST, 10, 40):
        narrow, known = narrow_dates(sess, window)
        uni = [t for t in base if t["date"] in known]
        rem = [t for t in uni if t["date"] in narrow]
        kept = [t for t in uni if t["date"] not in narrow]
        tot = sum(net(t) for t in rem)
        p = perm_p([net(t) for t in uni], tot, len(rem), n=a.perms)
        ys = by_year(rem)
        losing = sum(v < 0 for v in ys.values())
        bk = lucid(kept, a.sims)
        bu = lucid(uni, a.sims)
        ok = tot < 0 and p < P_BAR and losing >= 4 and bk[2] >= bu[2]
        tag = f"{window}" + (" (primary)" if window == WIDTH_HIST else "")
        P(f"| {tag} | {len(rem)} | {f(tot)} | {p:.4f} | {losing}/{len(ys)} | "
          f"{f(bk[2], 1)} / {f(bu[2], 1)} | {'YES' if ok and window == WIDTH_HIST else 'no'} |")
    P("\nThe pass-rate check uses the bootstrap column because the rolling rate is "
      "undefined at base costs (no real-order start finishes), as in Phase 3.\n")

    # S5 sizing
    P("## S5 cushion-scaled size on the live ORB trades\n")
    tbl = sizing_table(base, a.sims)
    P("| sizing | rolling pass % | rolling breach % (n) | bootstrap pass % | bootstrap breach % | median trades to pass |")
    P("|---|---|---|---|---|---|")
    for k, v in tbl.items():
        P(f"| {k} | {f(v['roll_pass'], 1)} | {f(v['roll_fail'], 1)} ({v['n_done']}) | "
          f"{f(v['boot_pass'], 1)} | {f(v['boot_fail'], 1)} | {f(v['median'])} |")
    fx, dy = tbl["fixed 1 MES"], tbl["cushion-scaled (max 3)"]
    ok5 = (dy["boot_fail"] - fx["boot_fail"] <= 5
           and dy["median"] is not None and fx["median"] is not None
           and dy["median"] <= 0.75 * fx["median"])
    P(f"\nS5 adopted for further work: **{'YES' if ok5 else 'no'}** "
      "(breach up by at most 5 points and median trades to pass down by 25% or more).\n")

    P("## Verdict\n")
    for r in results:
        P(f"- {r['name']}: {'adopted for further work' if r['ok'] else 'not adopted'}")
    P("\n## Caveats\n")
    P("- ES bars as the MES proxy. VWAP uses the typical price (H+L+C)/3 weighted by 1m volume.")
    P("- The Lucid simulator takes one entry a day, so multi-trade days are folded into one "
      "pseudo-trade with the extra round turns charged inside its points.")
    P("- The stop fills exactly at its price plus slippage. Gaps and partial fills are not modelled.")
    P("- Four candidates were tested, so the p bar is 0.0125; one lucky pass among many is expected.")


if __name__ == "__main__":
    main()
