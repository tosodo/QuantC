"""Tests for ../../audit_repaint.py on small synthetic sessions with known fills."""
import csv
import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import audit_repaint as au  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402

ET = lrb.ET


def session(day, base, spec=None, sym="ESH4", minutes=range(9 * 60 + 30, 16 * 60 + 1)):
    """One-minute bars 9:30-16:00 ET flat at `base`, with `spec` {HH:MM: (o,h,l,c)} overrides."""
    spec = spec or {}
    rows = []
    for m in minutes:
        hhmm = f"{m // 60:02d}:{m % 60:02d}"
        t = int(datetime.fromisoformat(f"{day}T{hhmm}:00").replace(tzinfo=ET).timestamp())
        o, h, l, c = spec.get(hhmm, (base,) * 4)
        rows.append({"t": t, "o": o, "h": h, "l": l, "c": c, "sym": sym})
    return rows


def breakout_spec(base, tail):
    # range bars flat at base with a +1 high; 9:45 closes +2 (entry); `tail` overrides after
    spec = {"09:44": (base, base + 1, base, base), "09:45": (base, base + 2, base, base + 2)}
    spec.update(tail)
    return spec


def test_integrity_flags_problems():
    rows = session("2024-03-04", 100.0)
    clean = au.check_integrity(rows)
    assert clean["duplicates"] == clean["bad_ohlc"] == clean["out_of_order"] == 0
    bad = rows + [dict(rows[0]), dict(rows[1], h=50.0)]
    r = au.check_integrity(bad)
    assert r["duplicates"] == 2 and r["bad_ohlc"] >= 1 and r["out_of_order"] >= 1


def test_sessions_first_bar_and_half_day():
    ok = session("2024-03-04", 100.0)
    late = session("2024-03-05", 100.0, minutes=range(9 * 60 + 31, 16 * 60))
    half = session("2024-03-06", 100.0, minutes=range(9 * 60 + 30, 13 * 60))
    s = au.check_sessions(au.group_days(ok + late + half))
    assert s["first_bar_not_0930"] == [("2024-03-05", "09:31")]
    assert s["half_days"] == ["2024-03-06"]


def test_dst_session_starts_at_0930_et():
    spring = session("2024-03-12", 100.0)          # after the US change
    s = au.check_sessions(au.group_days(spring))
    assert s["first_bar_not_0930"] == []


def test_rolls_detect_mixed_session():
    a = session("2024-03-04", 100.0, sym="ESH4")
    b = session("2024-03-05", 100.0, sym="ESH4")
    b[200]["sym"] = "ESM4"
    r = au.check_rolls(au.group_days(a + b))
    assert len(r["mixed_symbol_sessions"]) == 1


def test_entry_and_market_exit_slippage():
    tail = {f"{m // 60:02d}:{m % 60:02d}": (102.5,) * 4 for m in range(9 * 60 + 46, 16 * 60)}
    tail["16:00"] = (102.0,) * 4
    spec = breakout_spec(100.0, tail)
    days = au.group_days(session("2024-03-04", 100.0, spec))
    fr = au.fill_rows(days)
    assert len(fr) == 1
    x = fr[0]
    assert x["reason"] == "session_close" and x["exit_kind"] == "market"
    assert abs(x["entry_slip"] - 0.5) < 1e-9          # 102.5 next open vs 102 signal close
    assert abs(x["exit_slip"] - 0.5) < 1e-9           # 102.5 close vs 102.0 next open


def test_stop_gap_through():
    base = 5000.0
    spec = breakout_spec(base, {"10:00": (4870.0, 4875.0, 4860.0, 4865.0)})
    days = au.group_days(session("2024-03-04", base, spec))
    fr = au.fill_rows(days)
    x = fr[0]
    assert x["reason"] == "stop" and x["exit_kind"] == "stop"
    assert abs(x["exit_slip"] - 7.0) < 1e-9           # stop 4877, bar opened 4870


def test_summary_equals_baseline_when_fills_match_assumption():
    rows = [dict(date="d", pts=2.0, entry_slip=0.0, exit_slip=lrb.BASE_SLIP * lrb.TICK,
                 exit_kind="market", reason="session_close"),
            dict(date="e", pts=-125.0, entry_slip=0.0, exit_slip=0.0, exit_kind="stop",
                 reason="stop")]
    base, adj = au.summarise_fills(rows)
    assert all(abs(a - b) < 1e-9 for a, b in zip(base, adj))


def test_report_runs_end_to_end(tmp_path, capsys):
    spec = breakout_spec(100.0, {"09:46": (100.5, 102.5, 100.5, 102.5)})
    rows = []
    d0 = datetime(2024, 3, 11)
    for k in range(40):
        d = (d0 + timedelta(days=k)).date()
        if d.weekday() < 5:
            rows += session(d.isoformat(), 100.0, spec)
    p = tmp_path / "ES.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_event", "open", "high", "low", "close", "volume", "symbol"])
        for r in rows:
            w.writerow([r["t"] * 10**9, r["o"], r["h"], r["l"], r["c"], 1, r["sym"]])

    class A:
        data, tv_csv = str(p), ""
    au.report(A)
    out = capsys.readouterr().out
    assert "A. Bar integrity" in out and "D. Fill realism" in out and "UNVERIFIED" in out
