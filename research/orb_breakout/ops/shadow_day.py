"""Replay one session of the live MES v2 ORB script from 1m bars.

Used by the 4:15 ET close routine (ops/CLOSE_ROUTINE.md) to get the
"shadow" trade: what the script's rules did on today's bars, whether or not
the alert was live. Mirrors orb_long_ghost_DRAFT_mes_v2_accessible.pine:

- range = high/low of the 15 bars opening 9:30-9:44 ET
- entry = close of the first bar from 9:45 that closes above the range high
  (one attempt per day)
- stop  = entry - 125 pts, a Ghost bracket, so it can only fill from the bar
  after the entry bar; filled at the stop price
- 90-min exit = first bar whose open is >= 90 min after the entry bar's open
  and whose close <= entry (re-checked every bar), exits at that close
- session close = the 15:59 bar's close; catch-all = first bar after entry
  outside 9:45-16:00 (half-days)

Input: the JSON saved from mcp-tv-get-ohlcv (CME_MINI:MES1!, 1m), which has
{"bars":[{"t":<open unix s>,"o","h","l","c","v"}, ...]}.

    python3 ops/shadow_day.py <ohlcv.json> 2026-09-28

Prints one JSON object. Also reports down_break_first: price closed below
the range low before the long break. The backtest skipped those days
(mes_final_run.py), the live script does not, so they are untested.
"""
import json
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
STOP_PTS = 125.0
TIME_EXIT_MIN = 90
POINT_VALUE = 5.0  # MES $/pt, 1 contract


def et(ts):
    return datetime.fromtimestamp(ts, ET)


def in_window(dt, start, end):
    return start <= dt.time() < end


def replay(bars, day):
    today = [b for b in bars if et(b["t"]).date().isoformat() == day]
    today.sort(key=lambda b: b["t"])
    out = {"date": day, "bars": len(today)}

    rng = [b for b in today if in_window(et(b["t"]), time(9, 30), time(9, 45))]
    if len(rng) < 15:
        out["state"] = "no_range"
        out["note"] = f"only {len(rng)} of 15 range bars"
        return out
    hi = max(b["h"] for b in rng)
    lo = min(b["l"] for b in rng)
    out.update(range_high=hi, range_low=lo)

    after = [b for b in today if et(b["t"]).time() >= time(9, 45)]
    session = [b for b in after if in_window(et(b["t"]), time(9, 45), time(16, 0))]

    entry_i = None
    down_first = False
    for i, b in enumerate(session):
        if b["c"] > hi:
            entry_i = i
            break
        if b["c"] < lo:
            down_first = True
    out["down_break_first"] = down_first if entry_i is not None else None
    if entry_i is None:
        out["state"] = "no_breakout"
        return out

    eb = session[entry_i]
    entry = eb["c"]
    stop = entry - STOP_PTS
    out.update(state="entry", entry_bar_open_et=et(eb["t"]).strftime("%H:%M"),
               entry=entry, stop=stop)

    exit_px = exit_bar = reason = None
    for b in after[after.index(eb) + 1:]:
        d = et(b["t"])
        if b["l"] <= stop:
            exit_px, exit_bar, reason = stop, b, "stop"
            break
        if not in_window(d, time(9, 45), time(16, 0)):
            exit_px, exit_bar, reason = b["c"], b, "catch_all_flatten"
            break
        if (b["t"] - eb["t"]) / 60 >= TIME_EXIT_MIN and b["c"] <= entry:
            exit_px, exit_bar, reason = b["c"], b, "time_exit_90min"
            break
        if d.time() == time(15, 59):
            exit_px, exit_bar, reason = b["c"], b, "session_close"
            break

    if exit_px is None:
        out["state"] = "open"  # bars end before an exit (data gap, or run too early)
        out["last_close"] = after[-1]["c"]
        return out
    pts = exit_px - entry
    out.update(exit=exit_px, exit_bar_open_et=et(exit_bar["t"]).strftime("%H:%M"),
               exit_reason=reason, pts=pts, pnl_usd=round(pts * POINT_VALUE, 2))
    if reason == "stop":
        out["note"] = ("script still thinks it is long and will send an exit "
                       "alert later (flat-account exit, see Phase 1 D)")
    return out


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        data = json.load(f)
    print(json.dumps(replay(data["bars"], sys.argv[2])))
