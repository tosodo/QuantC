"""Tests for ../../divergence_filter_test.py: zone detection and, above all,
that nothing after the entry decision can affect it."""
import os
import random
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import divergence_filter_test as dv  # noqa: E402

T0 = 1_700_000_100 - 1_700_000_100 % 300


def bars_from(closes, spread=1.0):
    out, prev = [], closes[0]
    for k, c in enumerate(closes):
        t = T0 + 300 * k
        out.append({"t": t, "close_t": t + 300, "o": prev, "c": c,
                    "h": max(prev, c) + spread, "l": min(prev, c) - spread})
        prev = c
    return out


def bearish_divergence_closes():
    """Strong rally, pullback, then a slower grind to a higher high:
    price makes a higher high while RSI makes a lower high."""
    p, out = 100.0, []
    steps = ([-1.0 if k % 3 == 2 else 1.0 for k in range(30)]      # warm-up chop
             + [3.0] * 12                                          # strong rally -> high RSI
             + [-2.0] * 8                                          # pullback
             + [1.5 if k % 2 == 0 else 0.5 for k in range(26)]     # weaker grind, higher high
             + [-2.5] * 12)                                        # fall confirms the pivot
    for s in steps:
        p += s
        out.append(p)
    return out


def run(bars, **kw):
    zt = dv.ZoneTracker(**kw)
    for b in bars:
        zt.update(b)
    return zt


def test_bearish_divergence_found_and_confirmed_late():
    bars = bars_from(bearish_divergence_closes())
    zt = run(bars, rsi_len=14, piv=5)
    assert zt.bear, "expected a bearish divergence zone"
    z = zt.bear[-1]
    peak_i = max(range(len(bars)), key=lambda i: bars[i]["h"])
    assert z["i"] == peak_i
    # usable only from the close of the bar 5 after the pivot
    assert z["conf_t"] == bars[peak_i + 5]["close_t"]
    assert z["top"] == bars[peak_i]["h"]
    assert z["bot"] == max(bars[peak_i]["o"], bars[peak_i]["c"])


def test_zone_not_visible_before_confirmation():
    bars = bars_from(bearish_divergence_closes())
    peak_i = max(range(len(bars)), key=lambda i: bars[i]["h"])
    zt = run(bars[:peak_i + 5], rsi_len=14, piv=5)   # one bar short of confirming
    assert all(z["i"] != peak_i for z in zt.bear)


def test_zone_broken_by_close_above_top():
    closes = bearish_divergence_closes()
    bars = bars_from(closes + [closes[-1] + 15 * k for k in range(1, 8)])
    zt = run(bars, rsi_len=14, piv=5)
    assert zt.bear[-1]["broken_t"] is not None
    assert not zt.bear_overhead(bars[-1]["c"] - 30, 10)


def test_overhead_check_window():
    zt = dv.ZoneTracker()
    zt.bear.append({"i": 0, "conf_t": 0, "top": 110.0, "bot": 105.0, "broken_t": None})
    assert zt.bear_overhead(100.0, 10)        # 105 <= 110
    assert not zt.bear_overhead(100.0, 4)     # 105 > 104
    assert zt.bear_overhead(107.0, 10)        # entry inside the zone
    assert not zt.bear_overhead(111.0, 10)    # zone wholly below the entry


def test_no_lookahead_truncation():
    """Tags at each decision time must be identical whether the tracker
    sees the whole history or only the bars complete by then."""
    rng = random.Random(3)
    closes, p = [], 4000.0
    for _ in range(3000):
        p += rng.gauss(0, 3)
        closes.append(p)
    bars = bars_from(closes)
    trades = [{"date": (date(2020, 1, 1) + timedelta(days=n)).isoformat(), "entry": bars[k]["c"],
               "dec_t": bars[k]["close_t"] + 30, "pts": 0.0, "mae_pts": 0.0}
              for n, k in enumerate(range(200, 3000, 13))]
    full = dv.tag_trades(trades, bars, 14, 5, 10.0)
    for t in trades:
        cut = [b for b in bars if b["close_t"] <= t["dec_t"]]
        part = dv.tag_trades([t], cut, 14, 5, 10.0)
        assert part[t["date"]]["bear_overhead"] == full[t["date"]]["bear_overhead"]
    assert any(v["bear_overhead"] for v in full.values())
    assert not all(v["bear_overhead"] for v in full.values())


def test_to_5m_groups_and_close_time():
    one = [{"t": T0 + 60 * k, "o": k, "h": k + 1, "l": k - 1, "c": k + 0.5} for k in range(10)]
    five = dv.to_5m(one)
    assert len(five) == 2
    assert five[0]["o"] == 0 and five[0]["c"] == 4.5 and five[0]["h"] == 5 and five[0]["l"] == -1
    assert five[0]["close_t"] == T0 + 300


def test_decision_time_is_signal_bar_close():
    t = dv.decision_t("2026-10-19", "10:14")
    from datetime import datetime
    assert datetime.fromtimestamp(t, dv.ET).strftime("%H:%M") == "10:15"
