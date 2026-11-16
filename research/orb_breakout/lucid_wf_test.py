#!/usr/bin/env python3
"""
lucid_wf_test.py - walk-forward search for a better ORB rule set, scored on the
LucidPro $100K evaluation. Pre-registered in LUCID_WF_HYPOTHESIS.md (read it first).

Nothing here changes the live rules or any rule number: it uses the rule sets
`Lucid 100K LucidPro (price GUESS)` (firm_fit_test.py) and `Lucid 100K funded`
(funded_stage_test.py) as they stand.

  python3 lucid_wf_test.py threshold            # Step 1: edge needed for 60% pass
  python3 lucid_wf_test.py run                  # Steps 2-5 on data/continuous/ES.csv
  python3 lucid_wf_test.py run --synthetic 1300 # smoke test on random data (numbers meaningless)

`run` options: --data PATH --sims 3000 --fsims 1000 --ci-outer 60 --ci-inner 100
--trades-out lucid_wf_trades.csv (one row per out-of-sample trade, no market data).

UNVERIFIED inputs, repeated in every report: Lucid eval price, trail lock, funded
payout cap, funded cycle length (see UNVERIFIED below).
"""
import argparse
import csv
import os
import random
import sys
from datetime import date, datetime, timedelta
from statistics import NormalDist
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import firm_fit_test as ff  # noqa: E402
import funded_stage_test as fs  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402

ET = ZoneInfo("America/New_York")
LUCID_EVAL = "Lucid 100K LucidPro (price GUESS)"
LUCID_FUNDED = "Lucid 100K funded"
UNVERIFIED = (
    "**Unverified inputs (flag in every report):** Lucid eval price ($170, GUESS), trail "
    "lock (+$100, GUESS), funded payout cap (none, GUESS), funded cycle length (3 days, "
    "third-party). Target $6,000 and drawdown $3,000 EOD are from Lucid's help-center "
    "snippet. No rule number was changed by this study.")

# ---------- pre-registered constants (LUCID_WF_HYPOTHESIS.md) ----------
RANGE_START = 9 * 60 + 30          # minute of day, ET
SESSION_END = 16 * 60
STOP_CAP_SHARE = 0.40              # one full stop <= 40% of the floor
FLOOR_USD = 3000.0
MARGIN_PASS = 5.0                  # percentage points over LIVE
COST_RATIO = 0.85                  # cost per pass <= 85% of LIVE
FREQ_RATIO = 0.80                  # trades a year >= 80% of LIVE
MIN_TRADES = 400
MIN_PER_YEAR = 150
N_COMPARISONS = 12
Z_BONF = NormalDist().inv_cdf(1 - 0.05 / N_COMPARISONS / 2)    # 2.87
TRAIN_M, TEST_M, STEP_M = 24, 6, 6
SELECT_SIZE, SELECT_SIMS, SELECT_H = 2, 400, 600
FUND_H = 400                       # trades funded (about 2 years)
CI_WEEKS = 520                     # path length for the paired interval (about 10 years)

# id -> params. last_entry is the first minute of day at which NO entry is allowed.
CANDIDATES = {
    "LIVE":      dict(stop=125.0, range_min=15, last_entry=None, partial=None),
    "S100":      dict(stop=100.0, range_min=15, last_entry=None, partial=None),
    "S75":       dict(stop=75.0,  range_min=15, last_entry=None, partial=None),
    "E1030":     dict(stop=125.0, range_min=15, last_entry=10 * 60 + 30, partial=None),
    "E1130":     dict(stop=125.0, range_min=15, last_entry=11 * 60 + 30, partial=None),
    "R5":        dict(stop=125.0, range_min=5,  last_entry=None, partial=None),
    "R30":       dict(stop=125.0, range_min=30, last_entry=None, partial=None),
    "P60":       dict(stop=125.0, range_min=15, last_entry=None, partial=60.0),
    "S100E1130": dict(stop=100.0, range_min=15, last_entry=11 * 60 + 30, partial=None),
    "S100P60":   dict(stop=100.0, range_min=15, last_entry=None, partial=60.0),
    "S100R30":   dict(stop=100.0, range_min=30, last_entry=None, partial=None),
    "E1030P60":  dict(stop=125.0, range_min=15, last_entry=10 * 60 + 30, partial=60.0),
}
assert len(CANDIDATES) == N_COMPARISONS            # the cap, recorded in code too
TIME_EXIT_MIN = 90


# ---------- bars ----------

def prep_day(bars):
    """Sorted bars from 9:30 ET on, each with `mod` = minute of day (ET)."""
    out = []
    for b in sorted(bars, key=lambda b: b["t"]):
        d = datetime.fromtimestamp(b["t"], ET)
        m = d.hour * 60 + d.minute
        if m >= RANGE_START:
            out.append({**b, "mod": m})
    return out


def prep_days(days):
    return {d: prep_day(bars) for d, bars in days.items()}


def synth_days(n_days, seed=5, start=date(2021, 8, 19)):
    """Random-walk 1m bars, 9:30-15:59 ET on weekdays. For tests and smoke runs only."""
    rng = random.Random(seed)
    days, d, px = {}, start, 4500.0
    while len(days) < n_days:
        if d.weekday() < 5:
            t0 = int(datetime(d.year, d.month, d.day, 9, 30, tzinfo=ET).timestamp())
            drift = rng.gauss(0, 0.05)
            bars = []
            for k in range(390):
                o = px
                px += rng.gauss(drift, 1.4)
                bars.append({"t": t0 + 60 * k, "o": o, "h": max(o, px) + rng.random(),
                             "l": min(o, px) - rng.random(), "c": px})
            days[d.isoformat()] = bars
        d += timedelta(days=1)
    return days


# ---------- the variant replay ----------

def replay_variant(bars, day, stop=125.0, range_min=15, last_entry=None, partial=None):
    """bars: prep_day output. With the defaults this is ops/shadow_day.replay_day
    (checked by a test). Variants: stop size, range-build minutes, no entry from
    `last_entry` on, and `partial` = half the position off at entry + partial pts
    (stop taken first if one bar touches both; the rest follows the live exits)."""
    r1 = RANGE_START + range_min
    out = {"date": day}
    rng = [b for b in bars if RANGE_START <= b["mod"] < r1]
    if len(rng) < range_min:
        out["state"] = "no_range"
        return out
    hi = max(b["h"] for b in rng)
    lo = min(b["l"] for b in rng)
    after = [b for b in bars if b["mod"] >= r1]

    entry_i, down_first = None, False
    for i, b in enumerate(after):
        if b["mod"] >= SESSION_END or (last_entry is not None and b["mod"] >= last_entry):
            break
        if b["c"] > hi:
            entry_i = i
            break
        if b["c"] < lo:
            down_first = True
    out["down_break_first"] = down_first if entry_i is not None else None
    if entry_i is None:
        out["state"] = "no_breakout"
        return out

    eb = after[entry_i]
    entry = eb["c"]
    stop_px = entry - stop
    target = None if partial is None else entry + partial
    filled = False
    mae = 0.0
    exit_px = reason = None
    for b in after[entry_i + 1:]:
        mae = max(mae, (entry - b["l"]) * (0.5 if filled else 1.0))
        if b["l"] <= stop_px:
            exit_px, reason = stop_px, "stop"
            break
        if target is not None and not filled and b["h"] >= target:
            filled = True
        if b["mod"] >= SESSION_END:
            exit_px, reason = b["c"], "catch_all_flatten"
            break
        if (b["t"] - eb["t"]) / 60 >= TIME_EXIT_MIN and b["c"] <= entry:
            exit_px, reason = b["c"], "time_exit_90min"
            break
        if b["mod"] == SESSION_END - 1:
            exit_px, reason = b["c"], "session_close"
            break

    def points(px):
        return 0.5 * partial + 0.5 * (px - entry) if filled else px - entry

    out.update(entry=entry, mae_pts=max(0.0, mae), partial_filled=filled)
    if exit_px is None:
        out.update(state="open", last_close=after[-1]["c"], pts=points(after[-1]["c"]))
        return out
    out.update(state="entry", exit=exit_px, exit_reason=reason, pts=points(exit_px))
    return out


def build_variant_trades(pdays, params):
    """Same shape as live_rules_backtest.build_trades (an unfinished day is flattened at
    the last bar's close), plus `partial_filled`. Returns (trades, sessions)."""
    trades, sessions = [], []
    for d in sorted(pdays):
        r = replay_variant(pdays[d], d, **params)
        if r["state"] == "no_range":
            continue
        sessions.append(d)
        if r["state"] == "open":
            r.update(exit=r["last_close"], exit_reason="catch_all_flatten", state="entry")
        if r["state"] == "entry":
            trades.append(dict(date=d, down_break_first=r["down_break_first"], entry=r["entry"],
                               exit=r["exit"], exit_reason=r["exit_reason"],
                               pts=round(r["pts"], 2), mae_pts=round(r["mae_pts"], 2),
                               partial_filled=r["partial_filled"]))
    return trades, sessions


def stop_share(size, stop_pts):
    return size * stop_pts * lrb.PV / FLOOR_USD


# ---------- walk-forward ----------

def month_label(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def month_idx(d):
    return int(d[:4]) * 12 + int(d[5:7]) - 1


def make_folds(dates, train_m=TRAIN_M, test_m=TEST_M, step_m=STEP_M):
    """(train_start, test_start, test_end) month indexes, test_end exclusive. A test
    window must end before the data's final month (which may be partial)."""
    ms = [month_idx(d) for d in dates]
    first, last = min(ms), max(ms)
    out, k = [], 0
    while True:
        a = first + train_m + step_m * k
        if a + test_m > last:
            break
        out.append((first + step_m * k, a, a + test_m))
        k += 1
    return out


def in_months(trades, lo, hi):
    return [t for t in trades if lo <= month_idx(t["date"]) < hi]


def select_candidate(train_by_cand, cost, slip, seed=3):
    """Best candidate on the training trades: per-attempt Lucid pass rate at SELECT_SIZE
    MES from a block bootstrap, ties by mean net per trade. Uses training data only."""
    rule = ff.RULE_SETS[LUCID_EVAL]
    best, best_key = None, None
    for cid, trades in train_by_cand.items():
        if len(trades) < 20:
            continue
        seq = ff.make_seq(trades, cost, slip, SELECT_SIZE)
        rng = random.Random(seed)
        wins = sum(ff.run_rules(ff.block_path(seq, rng, SELECT_H), rule)[0] == "pass"
                   for _ in range(SELECT_SIMS))
        key = (wins / SELECT_SIMS, sum(p for p, _, _ in seq) / len(seq))
        if best_key is None or key > best_key:
            best, best_key = cid, key
    return best, best_key


def walk_forward(all_trades, cost, slip, train_m=TRAIN_M, test_m=TEST_M, step_m=STEP_M):
    """all_trades: {cand id: full-history trades}. Returns (folds, oos) where oos maps
    'WF' and every candidate id to its out-of-sample trades (test windows only), and
    folds lists each fold's choice."""
    dates = [t["date"] for ts in all_trades.values() for t in ts]
    folds = make_folds(dates, train_m, test_m, step_m)
    oos = {cid: [] for cid in all_trades}
    oos["WF"] = []
    log = []
    for tr0, a, b in folds:
        train = {cid: in_months(ts, tr0, a) for cid, ts in all_trades.items()}
        pick, key = select_candidate(train, cost, slip)
        for cid, ts in all_trades.items():
            oos[cid].extend(in_months(ts, a, b))
        wf = in_months(all_trades[pick], a, b)
        oos["WF"].extend({**t, "picked": pick} for t in wf)
        log.append(dict(train=(tr0, a), test=(a, b), pick=pick, score=key, n_test=len(wf)))
    return log, oos


# ---------- scoring ----------

def eval_seq(trades, size, sims, fsims, cost, slip, seed=1):
    """firm_fit_test + funded_stage_test on one sequence at one size."""
    seq = ff.make_seq(trades, cost, slip, size)
    er = ff.RULE_SETS[LUCID_EVAL]
    ev = ff.summarise(ff.bootstrap_runs(seq, {LUCID_EVAL: er}, sims, seed)[LUCID_EVAL])
    p, b = ff.rates_for_cost(ev, False)
    cm = ff.cost_model(p, b, er, ev["mean_trades"])
    roll = ff.summarise(ff.rolling_runs(seq, er)) if seq else None
    roll_pass = None if roll is None else 100 * ff.rates_for_cost(roll, True)[0]
    roll_n = 0 if roll is None else round(roll["n"] * (roll["pass_"] + roll["breach"]) / 100)
    fr = fs.FUNDED_RULES[LUCID_FUNDED]
    runs = [fs.funded_run(x, fr) for x in fs.boot_paths(seq, fsims, FUND_H)]
    fsum = fs.summarise_funded(runs, [FUND_H])[FUND_H]
    net = None if cm["cost"] is None else fsum["mean_paid"] - cm["cost"]
    return dict(pass_=ev["pass_"], breach=ev["breach"], med_days=ev["med_days"],
                cost=cm["cost"], years=cm["years"], p_first=fsum["p_first"], roll_pass=roll_pass, roll_n=roll_n,
                paid=fsum["mean_paid"], net=net,
                mean_net=sum(p for p, _, _ in seq) / len(seq) if seq else 0.0)


def fast_pass(seq, rule):
    """1 if the sequence passes the Lucid eval (EOD trailing with lock, no consistency,
    no minimum days, no daily limit), else 0. Same logic as ff.run_rules for that rule
    type, inlined for the paired interval (a test checks the two agree)."""
    assert (rule["dd_type"] == "eod_trailing" and rule["consistency"] is None
            and rule["daily_loss"] is None and rule["min_days"] == 0)
    start, dd = rule["start"], rule["dd"]
    cap = start + rule["lock"]
    tgt = start + rule["target"]
    bal = hwm = start
    for pnl, mae, _ in seq:
        floor = min(max(start - dd, hwm - dd), cap)
        if bal - mae <= floor:
            return 0
        bal += pnl
        if bal <= floor:
            return 0
        if bal - start >= rule["target"]:
            return 1
        if bal > hwm:
            hwm = bal
    return 0


def week_key(d):
    y, w, _ = date.fromisoformat(d).isocalendar()
    return y * 100 + w


def paired_ci(trades_a, trades_b, size, cost, slip, outer, inner, weeks=CI_WEEKS, seed=17):
    """Paired difference (A minus B) in per-attempt pass probability. Outer: resample
    whole weeks of the out-of-sample period (data uncertainty). Inner: bootstrap paths
    of `weeks` resampled weeks, the same weeks for A and B. Returns (mean, sd) over the
    outer resamples, in percentage points."""
    rule = ff.RULE_SETS[LUCID_EVAL]
    sa = ff.make_seq(trades_a, cost, slip, size)
    sb = ff.make_seq(trades_b, cost, slip, size)
    unit = {}
    for ts, seq, slot in ((trades_a, sa, 0), (trades_b, sb, 1)):
        for t, row in zip(ts, seq):
            unit.setdefault(week_key(t["date"]), ([], []))[slot].append(row)
    keys = sorted(unit)
    rng = random.Random(seed)
    diffs = []
    for _ in range(outer):
        pool = [rng.choice(keys) for _ in keys]
        tot = 0
        for _ in range(inner):
            pa, pb = [], []
            for k in rng.choices(pool, k=weeks):
                pa.extend(unit[k][0])
                pb.extend(unit[k][1])
            tot += fast_pass(pa, rule) - fast_pass(pb, rule)
        diffs.append(100.0 * tot / inner)
    m = sum(diffs) / len(diffs)
    sd = (sum((x - m) ** 2 for x in diffs) / max(1, len(diffs) - 1)) ** 0.5
    return m, sd


# ---------- criteria ----------

def seq_meta(cid, trades, log, oos_years):
    if cid == "WF":
        picks = {x["pick"] for x in log}
        stops = [CANDIDATES[t["picked"]]["stop"] for t in trades]
        partial = any(CANDIDATES[p]["partial"] is not None for p in picks)
        stop_mean = sum(stops) / len(stops) if stops else 0.0
        stop_max = max((CANDIDATES[p]["stop"] for p in picks), default=0.0)
    else:
        c = CANDIDATES[cid]
        partial, stop_mean, stop_max = c["partial"] is not None, c["stop"], c["stop"]
    return dict(n=len(trades), per_year=len(trades) / oos_years, partial=partial,
                stop_mean=stop_mean, stop_max=stop_max)


def deciding_sizes(meta):
    """1 and 2 MES; 2 only with a partial exit (needs two contracts); only sizes where
    the largest stop is within the 40% cap. 3 MES never decides."""
    return [s for s in (1, 2) if stop_share(s, meta["stop_max"]) <= STOP_CAP_SHARE + 1e-9
            and not (meta["partial"] and s == 1)]


def judge(cid, res, ci, meta, live_meta):
    """res/ci: {size: ...}. Returns {size: {criterion: bool}} and the overall verdict."""
    sizes = deciding_sizes(meta)
    out = {}
    for s in sizes:
        r, l = res[cid][s], res["LIVE"][s]   # sizes only holds sizes both were scored at
        m, sd = ci[cid][s] if ci.get(cid, {}).get(s) else (None, None)
        lower = None if m is None else m - Z_BONF * sd
        cost_ok = (r["cost"] is not None and l["cost"] is not None
                   and r["cost"] <= COST_RATIO * l["cost"])
        net_ok = r["net"] is not None and l["net"] is not None and r["net"] >= l["net"]
        out[s] = {
            "1 pass rate +5 pts": r["pass_"] >= l["pass_"] + MARGIN_PASS,
            "2 cost per pass <= 85%": cost_ok,
            "3 interval above zero": lower is not None and lower > 0,
            "4 not fewer/bigger": (meta["per_year"] >= FREQ_RATIO * live_meta["per_year"]
                                   and meta["stop_mean"] <= live_meta["stop_mean"]),
            "5 enough trades": meta["n"] >= MIN_TRADES and meta["per_year"] >= MIN_PER_YEAR,
            "6 funded not worse": net_ok,
        }
    beats = bool(sizes) and all(all(v.values()) for v in out.values())
    return out, beats


# ---------- Step 1: the edge needed ----------

WINRATES = (0.30, 0.40, 0.50, 0.60)
RISKS = (50.0, 100.0, 250.0, 500.0, 625.0, 1250.0, 1875.0)


def pass_prob(rule, us, wr, win, risk):
    start, dd = rule["start"], rule["dd"]
    cap, tgt = start + rule["lock"], rule["target"]
    n = 0
    for path in us:
        bal = hwm = start
        for u in path:
            floor = min(max(start - dd, hwm - dd), cap)
            if u < wr:
                bal += win
            else:
                if bal - risk <= floor:
                    break
                bal -= risk
            if bal <= floor:
                break
            if bal - start >= tgt:
                n += 1
                break
            if bal > hwm:
                hwm = bal
    return n / len(us)


def min_win_for(rule, us, wr, risk, goal=0.60):
    """Smallest winner size (net $) with pass probability >= goal; None if not reached."""
    hi = 8.0 * risk / wr
    if pass_prob(rule, us, wr, hi, risk) < goal:
        return None
    lo = 0.0
    for _ in range(9):
        mid = (lo + hi) / 2
        if pass_prob(rule, us, wr, mid, risk) >= goal:
            hi = mid
        else:
            lo = mid
    return hi


def threshold_report(sims=600, horizon=2000, seed=11):
    rule = ff.RULE_SETS[LUCID_EVAL]
    rng = random.Random(seed)
    us = [[rng.random() for _ in range(horizon)] for _ in range(sims)]
    P = print
    P("# Lucid 100K: what trade profile passes 60% of attempts\n")
    P(UNVERIFIED + "\n")
    P(f"Rule engine: target ${rule['target']:,.0f}, EOD trailing drawdown ${rule['dd']:,.0f}, "
      f"floor locks at start + ${rule['lock']:,.0f}, no consistency rule, no minimum days. "
      f"Per attempt, {sims} paths of up to {horizon} trades, results net of costs. Winners are "
      "a fixed size with no adverse excursion (optimistic); every loser loses exactly the 'risk' "
      "(the loss on a losing trade, not the stop distance: the live rules' typical loser is far "
      "smaller than the 125-point stop, see the profile table in the run report).\n")
    P("Risk $625 / $1,250 / $1,875 are the live 125-point stop at 1 / 2 / 3 MES; the share of "
      "the $3,000 floor one full stop uses is 21% / 42% / 62.5%.\n")
    P("| risk per trade $ | stop share of floor | win rate | winner $ | min expectancy $/trade | "
      "expectancy as % of risk | per MES in points (125-pt rows only) |")
    P("|---|---|---|---|---|---|---|")
    for risk in RISKS:
        for wr in WINRATES:
            w = min_win_for(rule, us, wr, risk)
            share = f"{100 * risk / FLOOR_USD:.0f}%"
            if w is None:
                P(f"| {risk:,.0f} | {share} | {wr:.2f} | not reached | n/a | n/a | n/a |")
                continue
            e = wr * w - (1 - wr) * risk
            size = risk / 625.0
            pts = f"{e / (size * lrb.PV):.2f}" if risk in (625.0, 1250.0, 1875.0) else "-"
            P(f"| {risk:,.0f} | {share} | {wr:.2f} | {w:,.0f} | {e:,.1f} | "
              f"{100 * e / risk:.1f}% | {pts} |")
    P("\nFor scale, the live rules earn about $820 a year per MES over about 200 trades, "
      "which is about $4 a trade (Phase 3, 996 real ES trades, 29% win rate). Every row "
      "above needing more than that is an edge the live rules do not have.")


# ---------- Step 2-5: the run ----------

def profile(trades, size, cost, slip):
    """Win rate, average win and loss ($), mean net per trade, worst trade."""
    pnl = [p for p, _, _ in ff.make_seq(trades, cost, slip, size)]
    w = [p for p in pnl if p > 0]
    l = [p for p in pnl if p <= 0]
    return dict(win=100 * len(w) / len(pnl) if pnl else 0.0,
                avg_win=sum(w) / len(w) if w else 0.0, avg_loss=sum(l) / len(l) if l else 0.0,
                mean=sum(pnl) / len(pnl) if pnl else 0.0, worst=min(pnl) if pnl else 0.0)


def fmt(x, nd=0):
    return "n/a" if x is None else f"{x:,.{nd}f}"


def run_report(a):
    P = print
    cost, slip = a.cost, a.slip
    if a.synthetic:
        raw = synth_days(a.synthetic)
        src = f"SYNTHETIC random data, {a.synthetic} days (numbers are meaningless)"
    else:
        raw = lrb.load_days(a.data)
        src = os.path.basename(a.data)
    pdays = prep_days(raw)
    all_trades = {}
    for cid, params in CANDIDATES.items():
        all_trades[cid], sessions = build_variant_trades(pdays, params)
    log, oos = walk_forward(all_trades, cost, slip)
    if not log:
        sys.exit("not enough history for a 24-month train and 6-month test window")
    oos_years = len(log) * TEST_M / 12.0
    meta = {cid: seq_meta(cid, ts, log, oos_years) for cid, ts in oos.items()}
    names = ["LIVE", "WF"] + [c for c in CANDIDATES if c != "LIVE"]
    sizes = (1, 2, 3)

    P("# Lucid walk-forward: out-of-sample results\n")
    P(UNVERIFIED + "\n")
    P(f"Data: {src}, {sessions[0]} to {sessions[-1]}. Costs ${cost:.2f}/RT + {slip} tick. "
      f"Pre-registration: LUCID_WF_HYPOTHESIS.md. {len(CANDIDATES)} candidates (incl. LIVE); "
      f"{N_COMPARISONS} comparisons counted, significance z = {Z_BONF:.2f}.\n")
    P(f"Walk-forward: fit {TRAIN_M} months, trade the next {TEST_M} blind, step {STEP_M}; "
      f"{len(log)} folds, {oos_years:.1f} years and {meta['LIVE']['n']} LIVE trades out of sample. "
      "Selection (WF) uses training trades only: per-attempt Lucid pass rate at 2 MES.\n")
    P("| fold | test months | picked | train score (pass, mean $/trade) | OOS trades |")
    P("|---|---|---|---|---|")
    for i, f_ in enumerate(log, 1):
        sc = f_["score"]
        P(f"| {i} | {month_label(f_['test'][0])} to {month_label(f_['test'][1] - 1)} | {f_['pick']} | "
          f"{'n/a' if sc is None else f'{100 * sc[0]:.0f}% , {sc[1]:.1f}'} | {f_['n_test']} |")
    P("")

    P("Trade profile out of sample, 1 MES (net of costs): the loss on a losing trade here is "
      "what step 1's 'risk per trade' means; the stop distance is only the tail.\n")
    P("| sequence | win % | avg win $ | avg loss $ | mean $/trade | worst trade $ |")
    P("|---|---|---|---|---|---|")
    for n in names:
        if oos[n]:
            q = profile(oos[n], 1, cost, slip)
            P(f"| {n} | {q['win']:.1f} | {q['avg_win']:.0f} | {q['avg_loss']:.0f} | "
              f"{q['mean']:.1f} | {q['worst']:.0f} |")
    P("")

    res = {n: {} for n in names}
    for n in names:
        if not oos[n]:
            continue
        for s in sizes:
            print(f"  scoring {n} at {s} MES", file=sys.stderr)
            res[n][s] = eval_seq(oos[n], s, a.sims, a.fsims, cost, slip)
    ci = {n: {} for n in names}
    if a.ci_outer > 0:
        for n in names:
            if n == "LIVE" or not oos[n]:
                continue
            for s in deciding_sizes(meta[n]):
                print(f"  interval {n} at {s} MES", file=sys.stderr)
                ci[n][s] = paired_ci(oos[n], oos["LIVE"], s, cost, slip, a.ci_outer, a.ci_inner)
    verdicts = {n: (judge(n, res, ci, meta[n], meta["LIVE"]) if res[n] else ({}, False))
                for n in names if n != "LIVE"}

    for s in sizes:
        P(f"\n## {s} MES\n")
        P("| sequence | OOS trades | trades/yr | stop pts | stop share of floor | pass % | breach % | "
          "median cal days | cost per pass $ | funded P(payout) % | net paid - cost $ | "
          "mean net $/trade | real-order starts pass % (check) | deciding? |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for n in names:
            if s not in res[n]:
                continue
            r, m = res[n][s], meta[n]
            dec = "baseline" if n == "LIVE" else ("yes" if s in deciding_sizes(m) else
                                                   "no (report only)")
            P(f"| {n} | {m['n']} | {m['per_year']:.0f} | {m['stop_mean']:.0f} | "
              f"{100 * stop_share(s, m['stop_max']):.0f}% | {r['pass_']:.1f} | {r['breach']:.1f} | "
              f"{fmt(r['med_days'])} | {fmt(r['cost'])} | {r['p_first']:.1f} | {fmt(r['net'])} | "
              f"{r['mean_net']:.1f} | {fmt(r['roll_pass'])}% of {r['roll_n']} resolved | {dec} |")
        P("")
    P("Median cal days and cost per pass are per attempt/per pass from firm_fit_test.py "
      "(bootstrap, 5 attempts, eval price GUESS). Net paid - cost is funded_stage_test.py: mean "
      f"paid to the trader over {FUND_H} funded trades minus the evaluation cost per funded "
      "account (payout cap and cycle length UNVERIFIED).\n")

    P("\n## Criteria (pre-registered)\n")
    P("| sequence | size | " + " | ".join(
        ["1 pass rate +5 pts", "2 cost per pass <= 85%", "3 interval above zero",
         "4 not fewer/bigger", "5 enough trades", "6 funded not worse"]) +
      " | paired diff pts (mean, lower) | beats LIVE? |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for n in names:
        if n == "LIVE":
            continue
        out, beats = verdicts[n]
        if not out:
            P(f"| {n} | none | no deciding size (stop over the 40% cap, or partial exit with 1 MES "
              "only) | | | | | | | no |")
            continue
        for s, flags in out.items():
            mm = ci[n].get(s)
            d = "n/a" if not mm else f"{mm[0]:.1f}, {mm[0] - Z_BONF * mm[1]:.1f}"
            P(f"| {n} | {s} MES | " + " | ".join("yes" if v else "no" for v in flags.values()) +
              f" | {d} | {'**YES**' if beats else 'no'} |")
    P("")

    winners = [n for n, (_, b) in verdicts.items() if b]
    P("\n## Verdict\n")
    if winners:
        P(f"Sequences meeting all six criteria at every deciding size: **{', '.join(winners)}**. "
          "This is a lead only: it needs a fresh, separately pre-registered forward test before "
          "any change. Nothing was adopted and the live alert was not touched.")
    else:
        P("**No candidate beat the live rules out of sample**, on the criteria set before the run. "
          "Recommendation: keep the live rules as they are. Nothing was adopted and the live alert "
          "was not touched.")
    live_over = [s for s in (2, 3) if stop_share(s, CANDIDATES["LIVE"]["stop"]) > STOP_CAP_SHARE]
    P(f"\nThe live 125-point stop is over the 40% cap at {', '.join(f'{s} MES' for s in live_over)} "
      f"({', '.join(f'{100 * stop_share(s, 125.0):.1f}%' for s in live_over)} of the floor); "
      "that is a sizing finding for the live rules, separate from this search.")
    P("\nLimits: about 3 years out of sample; ES is the MES proxy; fits on 24 months are rough; "
      "earlier searches on the same data raise the true number of looks above 12; the eval "
      "price, trail lock, payout cap and cycle length are unverified.")

    if a.trades_out:
        with open(a.trades_out, "w", newline="") as f_:
            w = csv.writer(f_)
            w.writerow(["sequence", "date", "picked", "pts", "mae_pts", "exit_reason"])
            for n in names:
                for t in oos[n]:
                    w.writerow([n, t["date"], t.get("picked", n), t["pts"], t["mae_pts"],
                                t["exit_reason"]])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("threshold")
    t.add_argument("--sims", type=int, default=600)
    r = sub.add_parser("run")
    r.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    r.add_argument("--synthetic", type=int, default=0, help="N random days instead of --data")
    r.add_argument("--sims", type=int, default=3000)
    r.add_argument("--fsims", type=int, default=1000)
    r.add_argument("--ci-outer", type=int, default=60)
    r.add_argument("--ci-inner", type=int, default=100)
    r.add_argument("--cost", type=float, default=lrb.BASE_COST)
    r.add_argument("--slip", type=int, default=lrb.BASE_SLIP)
    r.add_argument("--trades-out", default="")
    a = ap.parse_args()
    if a.cmd == "threshold":
        threshold_report(a.sims)
    else:
        run_report(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
