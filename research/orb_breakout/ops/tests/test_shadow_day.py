"""shadow_day.replay_day on synthetic sessions - one per exit path."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import shadow_day as sd

ET = ZoneInfo("America/New_York")
DAY = "2026-10-19"
BASE = 5000.0


def session(overrides=None, start="09:30", end="16:30", skip=()):
    """1m bars flat at BASE; overrides = {"HH:MM": (o, h, l, c)}."""
    overrides = overrides or {}
    t = datetime.fromisoformat(f"{DAY}T{start}").replace(tzinfo=ET)
    stop = datetime.fromisoformat(f"{DAY}T{end}").replace(tzinfo=ET)
    bars = []
    while t < stop:
        k = t.strftime("%H:%M")
        if k not in skip:
            o, h, l, c = overrides.get(k, (BASE, BASE, BASE, BASE))
            bars.append({"t": int(t.timestamp()), "o": o, "h": h, "l": l, "c": c})
        t += timedelta(minutes=1)
    return bars


RANGE = {"09:30": (BASE, BASE + 10, BASE - 10, BASE)}      # range 4990-5010
BREAK = {"09:50": (BASE, BASE + 12, BASE, BASE + 12)}      # first close > 5010 -> entry 5012


def above(start="09:51", end="16:30", level=BASE + 20):
    """Hold every bar above the 5012 entry so the 90-min exit never fires."""
    out = {}
    t = datetime.fromisoformat(f"{DAY}T{start}")
    stop = datetime.fromisoformat(f"{DAY}T{end}")
    while t < stop:
        out[t.strftime("%H:%M")] = (level,) * 4
        t += timedelta(minutes=1)
    return out


def run(extra=None, **kw):
    return sd.replay_day(session({**RANGE, **BREAK, **(extra or {})}, **kw), DAY)


def test_no_range_when_range_bars_missing():
    r = sd.replay_day(session(RANGE, skip=("09:31", "09:32")), DAY)
    assert r["state"] == "no_range"


def test_no_breakout():
    assert sd.replay_day(session(RANGE), DAY)["state"] == "no_breakout"


def test_entry_and_session_close():
    r = run({**above(), "15:59": (BASE + 30, BASE + 30, BASE + 30, BASE + 30)})
    assert (r["entry"], r["entry_bar_open_et"]) == (5012, "09:50")
    assert (r["exit_reason"], r["exit"], r["exit_bar_open_et"]) == ("session_close", 5030, "15:59")
    assert r["pnl_usd"] == 90.0 and r["down_break_first"] is False


def test_stop_fills_at_stop_price():
    r = run({"10:30": (BASE, BASE, BASE - 200, BASE - 150)})
    assert r["exit_reason"] == "stop" and r["exit"] == 5012 - 125
    assert r["pnl_usd"] == -625.0 and "Phase 1 D" in r["note"]


def test_stop_not_checked_on_entry_bar():
    r = run({**above(), "09:50": (BASE, BASE + 12, BASE - 200, BASE + 12)})
    assert r["exit_reason"] == "session_close"


def test_time_exit_rechecked_every_bar():
    # above entry at the 90-min mark (11:20), first close <= entry at 11:40
    ups = {f"{h}:{m:02d}": (BASE + 20,) * 4 for h in ("10", "11") for m in range(60)}
    r = run({**ups, "11:40": (BASE + 12, BASE + 12, BASE + 5, BASE + 5)})
    assert (r["exit_reason"], r["exit_bar_open_et"], r["exit"]) == ("time_exit_90min", "11:40", 5005)


def test_catch_all_on_half_day():
    # session ends 13:00 ET, next bar is the 18:00 reopen on the same date
    bars = (session({**RANGE, **BREAK, **above(end="13:00")}, end="13:00")
            + session(above(start="18:00", end="18:05"), start="18:00", end="18:05"))
    r = sd.replay_day(bars, DAY)
    assert r["exit_reason"] == "catch_all_flatten" and r["exit_bar_open_et"] == "18:00"


def test_down_break_first_is_flagged_and_still_traded():
    r = run({"09:46": (BASE, BASE, BASE - 15, BASE - 15)})
    assert r["state"] == "entry" and r["down_break_first"] is True


def test_open_when_bars_end_before_exit():
    r = sd.replay_day(session({**RANGE, **BREAK}, end="10:00"), DAY)
    assert r["state"] == "open"
