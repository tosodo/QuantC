"""Tests for ../../edge_search_test.py: the signals, and above all that nothing
after the decision bar can change an entry."""
import os
import random
import sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import edge_search_test as es  # noqa: E402


def make_session(day, o, rng, drift=0.0, vol=0.4, prev=None):
    """390 regular 1m bars as the loader would give them."""
    t0 = int(datetime.fromisoformat(f"{day}T09:30:00").replace(tzinfo=es.ET).timestamp())
    bars, p = [], o
    for m in range(390):
        c = p + drift + rng.gauss(0, vol)
        bars.append({"t": t0 + 60 * m, "o": p, "h": max(p, c) + 0.25, "l": min(p, c) - 0.25,
                     "c": c, "v": 100.0, "m": m})
        p = c
    return bars


def make_days(n=40, seed=5, vol=0.4):
    rng = random.Random(seed)
    days, px = {}, 4000.0
    for k in range(n):
        d = (date(2024, 3, 4) + timedelta(days=k)).isoformat()
        bars = make_session(d, px + rng.gauss(0, 5), rng, drift=rng.choice([-0.05, 0.05]), vol=vol)
        days[d] = bars
        px = bars[-1]["c"]
    return days


def test_s2_side_and_prices():
    days = make_days(3)
    sess = es.session_table(days)
    t = es.s2_trades(sess)
    assert len(t) == 2                      # first day has no prior close
    s = sess[1]
    r = s["reg"][29]["c"] / s["prev_close"] - 1
    assert t[0]["side"] == (1 if r > 0 else -1)
    assert t[0]["entry"] == s["reg"][359]["c"] and t[0]["exit"] == s["reg"][389]["c"]
    assert t[0]["pts"] == (t[0]["exit"] - t[0]["entry"]) * t[0]["side"]


def test_s2_signal_uses_only_morning_data():
    days = make_days(3)
    a = es.s2_trades(es.session_table(days))
    d = sorted(days)[1]
    for b in days[d]:
        if b["m"] > 29:                     # wreck everything after the signal bar
            b["c"] += 50
            b["h"] += 50
    b2 = es.s2_trades(es.session_table(days))
    assert a[0]["side"] == b2[0]["side"]


def test_s1_no_lookahead_truncation():
    days = make_days(30, vol=1.2)
    sess = es.session_table(days)
    full = es.s1_trades(sess)
    last = sess[-1]["date"]
    cut = 200
    days2 = dict(days)
    days2[last] = [b for b in days[last] if b["m"] <= cut]
    part = es.s1_trades(es.session_table(days2))
    # every entry decision at or before the cut is identical
    key = lambda t: (t["date"], t["entry_m"], t["side"], round(t["entry"], 6))
    f_last = {key(t) for t in full if t["date"] == last and t["entry_m"] <= cut}
    p_last = {key(t) for t in part if t["date"] == last and t["entry_m"] <= cut}
    assert f_last == p_last
    assert f_last, "no last-day entries before the cut: test would be vacuous"
    # earlier days are untouched
    assert [key(t) for t in full if t["date"] != last] == [key(t) for t in part if t["date"] != last]
    # and at least some entries exist overall, so the test is not vacuous
    assert len(full) > 5


def test_s1_exits_flat_by_close_and_one_position_at_a_time():
    sess = es.session_table(make_days(30, vol=1.2))
    tr = es.s1_trades(sess)
    assert tr
    by = {}
    for t in tr:
        by.setdefault(t["date"], []).append(t)
    for ts in by.values():
        ts.sort(key=lambda x: x["entry_m"])
        for a, b in zip(ts, ts[1:]):
            assert b["entry_m"] > a["exit_m"]
        assert ts[-1]["exit_m"] <= 389


def test_orb_stop_override_restored_and_matches_live_at_125():
    days = make_days(25, vol=1.5)
    live = es.orb_trades(days)
    stops = {d: 125.0 for d in days}
    same = es.orb_trades(days, stops)
    assert [(t["date"], t["pts"]) for t in live] == [(t["date"], t["pts"]) for t in same]
    es.orb_trades(days, {d: 3.0 for d in days})
    assert es.sd.STOP_PTS == 125.0


def test_tighter_stop_caps_the_loss():
    days = make_days(25, vol=1.5)
    for t in es.orb_trades(days, {d: 3.0 for d in days}):
        assert t["pts"] >= -3.0 - 1e-9 or t["exit_reason"] != "stop"


def test_narrow_dates_uses_only_prior_sessions():
    sess = es.session_table(make_days(40, vol=1.0))
    n1, k1 = es.narrow_dates(sess, 20)
    assert k1 and n1 <= k1
    # change today's and later bars: earlier days' verdicts must not move
    cut = sess[30]["date"]
    days = make_days(40, vol=1.0)
    for d in days:
        if d >= cut:
            for b in days[d]:
                b["h"] += 100
    n2, _ = es.narrow_dates(es.session_table(days), 20)
    assert {d for d in n1 if d < cut} == {d for d in n2 if d < cut}


def test_block_p_detects_edge_and_not_noise():
    rng = random.Random(1)
    edge = [rng.gauss(30, 50) for _ in range(500)]
    noise = [rng.gauss(0, 50) for _ in range(500)]
    assert es.block_p(edge, n=2000) < 0.01
    assert es.block_p(noise, n=2000) > 0.05


def test_size_for_steps_with_cushion():
    worst = 625 + 1.25
    assert es.size_for(1200, worst) == 1
    assert es.size_for(3000, worst) == 2
    assert es.size_for(6000, worst) == 3
    assert es.size_for(100, worst) == 1


def test_size_run_fixed_matches_lucid_run():
    rng = random.Random(2)
    seq = [(rng.gauss(4, 60), abs(rng.gauss(30, 20))) for _ in range(800)]
    for i in range(0, 700, 50):
        assert es.size_run(seq[i:], 626.25, False) == es.lrb.lucid_run(seq[i:])


def test_day_trades_folds_multiple_entries():
    t1 = {"date": "2024-01-02", "pts": -2.0, "mae_pts": 3.0, "entry_t": 1}
    t2 = {"date": "2024-01-02", "pts": 5.0, "mae_pts": 1.0, "entry_t": 2}
    d = es.day_trades([t1, t2])[0]
    one_net = es.lrb.net({"pts": 3.0}, es.BASE_COST, es.BASE_SLIP)
    # net of the folded trade = both trades' nets (two round turns)
    two_net = es.net(t1) + es.net(t2)
    assert abs(es.lrb.net(d, es.BASE_COST, es.BASE_SLIP) - two_net) < 1e-9
    assert one_net != two_net
    assert d["mae_pts"] == 3.0
