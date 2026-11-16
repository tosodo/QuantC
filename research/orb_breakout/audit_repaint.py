"""Read-only realism audit of the ES minute data and the live ORB replay. Nothing is
written except the report on stdout; no rule, alert or data file is touched.

    python3 audit_repaint.py [--data data/continuous/ES.csv] [--tv-csv MES_1m_export.csv]

What it checks
  A. bar integrity: duplicates, order, bad OHLC, non-positive prices.
  B. session completeness: first RTH bar at 9:30 ET (timestamp/DST convention), RTH bars
     per session, missing bars inside the 9:30-15:59 window, half days.
  C. contract rolls: sessions that mix two contracts, and the price jump on roll days.
  D. fill realism of the replay's assumptions, per trade:
       entry   replay fills at the signal bar's close; a live order sent after that bar
               closes fills about the next bar's open (adverse = next open - close);
       stop    replay fills exactly at the stop; a bar that opens below it fills lower;
       exit    time/close exits fill at the bar close; a live order fills about the next
               bar's open.
     Then the mean net per trade at the base costs ($2.50 + 1 tick on exits) is recomputed
     with those measured fills, with its t-stat. Both numbers are shown side by side.
  E. optional --tv-csv: a TradingView MES 1m export (time, open, high, low, close). Closes
     are compared bar by bar with ES and the replay is run on both to compare entries.

Repaint: the Pine alert fires once per bar close and state commits at bar close (static
audit of orb_long_mes_v2.pine; the replay's windows match it), so a signal cannot change
after it is sent. This script measures what is left: data and fill realism.

UNVERIFIED (not changed here): Lucid eval price, trail lock, funded payout cap and cycle
length.
"""
import argparse
import csv
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, time
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ops"))
import live_rules_backtest as lrb  # noqa: E402
import edge_calculator as ec  # noqa: E402
from shadow_day import replay_day  # noqa: E402

ET = lrb.ET
TICK, PV = lrb.TICK, lrb.PV
RTH_BARS = 390
ROLL_JUMP_X = 3.0       # a roll-day jump this many times the median overnight gap is noted


def load_raw(path):
    """Rows in file order: {t, o, h, l, c, sym}. ts_event is the bar open."""
    out = []
    with open(path) as f:
        for row in csv.DictReader(f):
            out.append({"t": lrb.parse_ts(row["ts_event"]), "o": float(row["open"]),
                        "h": float(row["high"]), "l": float(row["low"]),
                        "c": float(row["close"]), "sym": row.get("symbol", "")})
    return out


def et_date(t):
    return datetime.fromtimestamp(t, ET).date().isoformat()


def et_time(t):
    return datetime.fromtimestamp(t, ET).time()


def group_days(rows):
    days = defaultdict(list)
    for r in rows:
        days[et_date(r["t"])].append(r)
    return {d: sorted(v, key=lambda b: b["t"]) for d, v in days.items()}


# ---------- A, B, C ----------

def check_integrity(rows):
    seen, dup, back, bad, nonpos = set(), 0, 0, 0, 0
    prev = None
    for r in rows:
        dup += r["t"] in seen
        seen.add(r["t"])
        back += prev is not None and r["t"] < prev
        prev = r["t"]
        if r["h"] < max(r["o"], r["c"], r["l"]) or r["l"] > min(r["o"], r["c"], r["h"]):
            bad += 1
        nonpos += min(r["o"], r["h"], r["l"], r["c"]) <= 0
    return dict(rows=len(rows), duplicates=dup, out_of_order=back, bad_ohlc=bad, nonpositive=nonpos)


def check_sessions(days):
    first_off, short, gaps, half, missing_total, n = [], [], [], [], 0, 0
    for d, bars in sorted(days.items()):
        rth = [b for b in bars if time(9, 30) <= et_time(b["t"]) < time(16, 0)]
        if not rth:
            continue
        n += 1
        if et_time(rth[0]["t"]) != time(9, 30):
            first_off.append((d, et_time(rth[0]["t"]).strftime("%H:%M")))
        have = {et_time(b["t"]).hour * 60 + et_time(b["t"]).minute for b in rth}
        if max(have) < 15 * 60 + 59 and max(have) <= 13 * 60 + 1:
            half.append(d)
            continue
        miss = [m for m in range(9 * 60 + 30, 16 * 60) if m not in have]
        missing_total += len(miss)
        if len(rth) < RTH_BARS - 5:
            short.append((d, len(rth)))
        inside = [m for m in miss if m >= 9 * 60 + 30]
        if inside:
            gaps.append((d, len(inside)))
    return dict(sessions=n, first_bar_not_0930=first_off, half_days=half,
                sessions_missing_over_5=short, sessions_with_missing=gaps,
                missing_bars=missing_total)


def check_rolls(days):
    mixed, jumps, overnight = [], [], []
    prev_close, prev_sym = None, None
    ordered = sorted(days)
    for d in ordered:
        rth = [b for b in days[d] if time(9, 30) <= et_time(b["t"]) < time(16, 0)]
        if not rth:
            continue
        syms = {b["sym"] for b in rth if b["sym"]}
        if len(syms) > 1:
            mixed.append((d, sorted(syms)))
        sym = rth[0]["sym"]
        if prev_close is not None:
            gap = abs(rth[0]["o"] - prev_close)
            overnight.append(gap)
            if sym != prev_sym:
                jumps.append((d, prev_sym, sym, gap))
        prev_close, prev_sym = rth[-1]["c"], rth[-1]["sym"]
    med = median(overnight) if overnight else 0.0
    big = [j for j in jumps if med > 0 and j[3] > ROLL_JUMP_X * med]
    return dict(mixed_symbol_sessions=mixed, roll_days=len(jumps), median_overnight_gap=med,
                roll_days_with_big_jump=len(big), big_jumps=big[:10])


# ---------- D ----------

def bar_at(bars, hhmm):
    for i, b in enumerate(bars):
        if et_time(b["t"]).strftime("%H:%M") == hhmm:
            return i
    return None


def fill_rows(days):
    """One dict per replayed trade with the measured fill differences, in points
    (positive = worse for a long)."""
    out = []
    for d in sorted(days):
        bars = days[d]
        r = replay_day(bars, d)
        if r.get("state") != "entry" or "exit" not in r:
            continue
        i = bar_at(bars, r["entry_bar_open_et"])
        j = bar_at(bars, r["exit_bar_open_et"])
        if i is None or j is None:
            continue
        entry_slip = bars[i + 1]["o"] - bars[i]["c"] if i + 1 < len(bars) else None
        reason = r["exit_reason"]
        if reason == "stop":
            exit_slip = max(0.0, r["exit"] - bars[j]["o"])      # opens below the stop
            kind = "stop"
        else:
            exit_slip = (bars[j]["c"] - bars[j + 1]["o"]) if j + 1 < len(bars) else None
            kind = "market"
        out.append(dict(date=d, pts=r["pts"], entry_slip=entry_slip, exit_slip=exit_slip,
                        exit_kind=kind, reason=reason))
    return out


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


def summarise_fills(rows, cost=lrb.BASE_COST, slip=lrb.BASE_SLIP):
    base, adj = [], []
    for r in rows:
        b = (r["pts"] - slip * TICK) * PV - cost
        base.append(b)
        es = r["entry_slip"] if r["entry_slip"] is not None else 0.0
        xs = r["exit_slip"] if r["exit_slip"] is not None else 0.0
        # measured fills replace the assumed 1 tick on the exit; entry slip is added
        a = (r["pts"] - es - xs) * PV - cost
        if r["exit_kind"] == "stop":
            a = (r["pts"] - es - xs - slip * TICK) * PV - cost   # stop keeps its 1 tick plus any gap
        adj.append(a)
    return base, adj


# ---------- E ----------

def load_tv(path):
    rows = []
    with open(path, newline="") as f:
        rd = csv.DictReader(f)
        rd.fieldnames = [x.strip().lower() for x in rd.fieldnames]
        for row in rd:
            ts = row["time"].strip()
            t = int(float(ts)) if ts.replace(".", "", 1).isdigit() else lrb.parse_ts(ts)
            rows.append({"t": t, "o": float(row["open"]), "h": float(row["high"]),
                         "l": float(row["low"]), "c": float(row["close"]), "sym": "TV"})
    return rows


def compare_tv(es_rows, tv_rows):
    es = {r["t"]: r for r in es_rows}
    diffs = [abs(es[r["t"]]["c"] - r["c"]) for r in tv_rows if r["t"] in es]
    es_days, tv_days = group_days(es_rows), group_days(tv_rows)
    common = sorted(set(es_days) & set(tv_days))
    ent_es = {r["date"]: r for r in fill_rows({d: es_days[d] for d in common})}
    ent_tv = {r["date"]: r for r in fill_rows({d: tv_days[d] for d in common})}
    same = sum(1 for d in ent_es if d in ent_tv)
    return dict(matched=len(diffs), median_abs=median(diffs) if diffs else None,
                p95_abs=pct(diffs, 0.95), within_tick=sum(x <= TICK for x in diffs) / max(1, len(diffs)),
                common_days=len(common), es_trades=len(ent_es), tv_trades=len(ent_tv),
                both_trade=same)


# ---------- report ----------

def report(a):
    rows = load_raw(a.data)
    days = group_days(rows)
    print("# Realism audit (read-only)")
    print(f"data {a.data}: {len(rows):,} bars, {len(days)} ET dates")
    print("UNVERIFIED (not changed here): Lucid eval price, trail lock, funded payout cap and "
          "cycle length.\n")

    i = check_integrity(rows)
    print("## A. Bar integrity")
    print(f"duplicates {i['duplicates']}, out of order {i['out_of_order']}, bad OHLC "
          f"{i['bad_ohlc']}, non-positive {i['nonpositive']}  -> "
          + ("clean" if not (i['duplicates'] or i['out_of_order'] or i['bad_ohlc'] or i['nonpositive'])
             else "REVIEW"))

    s = check_sessions(days)
    print("\n## B. Sessions and timestamps")
    print(f"RTH sessions {s['sessions']}; half days {len(s['half_days'])}; first bar not 09:30 ET: "
          f"{len(s['first_bar_not_0930'])} {s['first_bar_not_0930'][:5]}")
    print(f"sessions missing more than 5 RTH bars: {len(s['sessions_missing_over_5'])} "
          f"{s['sessions_missing_over_5'][:5]}; missing RTH bars in total {s['missing_bars']}")

    r = check_rolls(days)
    print("\n## C. Contract rolls")
    if not any(b["sym"] for b in rows[:1000]):
        print("no symbol column: not checked")
    else:
        print(f"sessions mixing two contracts: {len(r['mixed_symbol_sessions'])} "
              f"{r['mixed_symbol_sessions'][:3]}")
        print(f"roll days {r['roll_days']}; median overnight gap {r['median_overnight_gap']:.2f} pts; "
              f"roll days with a jump over {ROLL_JUMP_X:.0f}x that: {r['roll_days_with_big_jump']} "
              f"{r['big_jumps'][:3]}")
        print("A roll jump lands overnight, outside the 9:30-15:59 window, so it cannot enter a "
              "trade; a mixed session could.")

    fr = fill_rows(days)
    print(f"\n## D. Fill realism ({len(fr)} replayed trades, base costs $"
          f"{lrb.BASE_COST:.2f} + {lrb.BASE_SLIP} tick on exits)")
    es_ = [x["entry_slip"] for x in fr if x["entry_slip"] is not None]
    if es_:
        print(f"entry (next open minus signal close): mean {sum(es_) / len(es_):+.3f} pts "
              f"(${sum(es_) / len(es_) * PV:+.2f} per MES), median {median(es_):+.2f}, "
              f"p90 {pct(es_, 0.9):+.2f}, worse than 1 tick {100 * sum(x > TICK for x in es_) / len(es_):.0f}%")
    stops = [x for x in fr if x["exit_kind"] == "stop"]
    if stops:
        g = [x["exit_slip"] for x in stops]
        print(f"stop exits {len(stops)}: bars opening below the stop {sum(v > 0 for v in g)} "
              f"({100 * sum(v > 0 for v in g) / len(g):.0f}%), mean extra loss {sum(g) / len(g):.3f} pts")
    mk = [x["exit_slip"] for x in fr if x["exit_kind"] == "market" and x["exit_slip"] is not None]
    if mk:
        print(f"time/close exits {len(mk)}: close minus next open mean {sum(mk) / len(mk):+.3f} pts, "
              f"p90 {pct(mk, 0.9):+.2f}")
    base, adj = summarise_fills(fr)
    if len(base) > 30:
        for name, x in (("replay as modelled", base), ("with measured fills", adj)):
            m = ec.moments(x)
            lo, hi = ec.boot_ci(x, 1000)
            print(f"{name:>22}: mean ${m['mean']:+.2f}/trade  sd ${m['sd']:.1f}  "
                  f"t {ec.t_stat(m['mean'], m['sd'], m['n']):+.2f}  95% [{lo:+.2f}, {hi:+.2f}]")
        print("Measured fills use one-minute bars: the next open is a proxy for a market order "
              "sent after the bar closes, not a recorded fill. Real Tradovate fills are the "
              "check that matters (journal lucid_pnl/slippage are mostly blank).")

    if a.tv_csv:
        c = compare_tv(rows, load_tv(a.tv_csv))
        print(f"\n## E. TradingView MES versus Databento ES ({a.tv_csv})")
        if c["matched"]:
            print(f"matched bars {c['matched']:,}; close difference median {c['median_abs']:.2f} pts, "
                  f"p95 {c['p95_abs']:.2f}, within 1 tick {100 * c['within_tick']:.0f}%")
            print(f"common days {c['common_days']}; ES trades {c['es_trades']}, TV trades "
                  f"{c['tv_trades']}, days both trade {c['both_trade']}")
            print("Different contract months differ by a basis; compare same-month data if the "
                  "median is large.")
        else:
            print("no timestamps matched: check the export's time column and range")
    print("\nStatic findings (Pine audit): alert is once per bar close, state commits at bar "
          "close, no request.security lookahead, windows match the replay. Open items: "
          "flat-account exit after a stop-out, Tradovate fills and commission unmeasured.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data", "continuous", "ES.csv"))
    ap.add_argument("--tv-csv", default="")
    report(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main() or 0)
