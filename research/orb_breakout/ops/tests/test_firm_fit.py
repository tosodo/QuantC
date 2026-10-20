"""Tests for ../../firm_fit_test.py: each drawdown type, the consistency rule,
the cost model, and that the Lucid rule set equals live_rules_backtest.lucid_run."""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import firm_fit_test as ff  # noqa: E402

LUCID = dict(start=100000.0, target=6000.0, dd=3000.0, dd_type="eod_trailing", lock=100.0,
             daily_loss=None, consistency=None, min_days=0,
             eval_fee=100.0, reset_fee=80.0, activation_fee=0.0)


def rule(**kw):
    return {**LUCID, **kw}


def seq(*pairs):
    """(pnl, mae) pairs -> run_rules input with a 1-day gap."""
    return [(p, m, 1) for p, m in pairs]


def test_static_floor_never_moves():
    r = rule(dd_type="static", lock=None, dd=2000.0, target=50000.0)
    for peak in (100000.0, 103000.0, 150000.0):
        assert ff.floor_for(r, peak) == 98000.0
    # +5000 banked, then a -2500 day: a trailing floor would be at 103000 and
    # breach; the static floor at 98000 is far away
    out = ff.run_rules(seq((5000, 0), (-2500, 2500)) + seq((10, 0)), r)
    assert out[0] == "open"
    # and it does breach at the fixed floor
    assert ff.run_rules(seq((5000, 0), (-7000, 7000)), r)[:2] == ("fail", 2)


def test_eod_trailing_moves_at_day_end_and_locks():
    r = rule(target=50000.0)
    assert ff.floor_for(r, 100000.0) == 97000.0
    assert ff.floor_for(r, 101000.0) == 98000.0          # trails the closing peak
    assert ff.floor_for(r, 120000.0) == 100100.0         # locked at start + lock
    # an intraday spike does not lift an EOD floor: win 1000 with a -2500 mae
    # is fine on day 2 only because the floor was set from the day-1 close
    assert ff.run_rules(seq((1000, 0), (0, 2900)), r)[0] == "open"      # floor 98000, low 98100
    assert ff.run_rules(seq((1000, 0), (0, 3000)), r)[:2] == ("fail", 2)  # low 98000 <= floor
    no_lock = rule(target=50000.0, lock=None)
    assert ff.floor_for(no_lock, 120000.0) == 117000.0   # without a lock it keeps trailing


def test_intraday_trailing_strictly_harsher_than_eod():
    eod = rule(target=50000.0, lock=None, dd=2000.0)
    intra = {**eod, "dd_type": "intraday_trailing"}
    # day 1 closes +1500; day 2 wins 500 after a 1900 dip from 101500 (low 99600).
    # EOD floor is 98000 -> survives. Intraday sees the day-2 close peak (102000),
    # floor 100000 -> the 99600 low breaches
    s = seq((1500, 0), (500, 1900))
    assert ff.run_rules(s, eod)[0] == "open"
    assert ff.run_rules(s, intra)[:2] == ("fail", 2)
    # never the other way round (EOD fails -> intraday fails no later), on random paths
    rng = random.Random(3)
    for _ in range(300):
        path = [(rng.gauss(40, 250), abs(rng.gauss(100, 100)), 1) for _ in range(60)]
        e, i = ff.run_rules(path, eod), ff.run_rules(path, intra)
        if e[0] == "fail":
            assert i[0] == "fail" and i[1] <= e[1]


def test_intraday_floor_is_never_below_eod_floor():
    eod = rule(lock=None)
    intra = {**eod, "dd_type": "intraday_trailing"}
    for hwm, bal, pnl in ((100000, 100000, 500), (103000, 101000, 2000), (100000, 99000, -300)):
        pk = ff.day_peak(intra, hwm, bal, pnl)
        assert ff.floor_for(intra, pk) >= ff.floor_for(eod, ff.day_peak(eod, hwm, bal, pnl))


def test_consistency_blocks_a_pass_a_bigger_day_would_allow():
    r = rule(target=3000.0, dd=5000.0, lock=None, consistency=0.5)
    # profit 3000 on day 3 but the best day is 2000 > 50% of profit: blocked
    blocked = ff.run_rules(seq((2000, 0), (500, 0), (500, 0), (500, 0)), r)
    assert blocked[0] == "open"
    # same profit spread out: passes on day 3
    assert ff.run_rules(seq((1000, 0), (1000, 0), (1000, 0)), r)[:2] == ("pass", 3)
    # without the rule the big-day path would have passed on day 3
    assert ff.run_rules(seq((2000, 0), (500, 0), (500, 0)), {**r, "consistency": None})[:2] == ("pass", 3)
    # a later pass appears once the best day is a small enough share
    later = ff.run_rules(seq((2000, 0), (500, 0), (500, 0)) + seq(*[(500, 0)] * 10), r)
    assert later[0] == "pass" and later[1] > 3


def test_min_days_and_daily_loss():
    r = rule(target=1000.0, min_days=3, lock=None)
    assert ff.run_rules(seq((1500, 0), (0, 0), (0, 0)), r)[:2] == ("pass", 3)
    d = rule(daily_loss=500.0, target=50000.0)
    assert ff.run_rules(seq((-100, 600)), d)[:2] == ("fail", 1)    # intraday limit
    assert ff.run_rules(seq((-100, 400)), d)[0] == "open"


def test_lucid_rule_set_reproduces_lucid_run_exactly():
    rng = random.Random(4)
    pairs = [(rng.gauss(4, 90), abs(rng.gauss(40, 40))) for _ in range(1500)]
    assert ff.RULE_SETS["Lucid 100K LucidPro (price GUESS)"]["dd_type"] == "eod_trailing"
    r = {k: v for k, v in LUCID.items()}
    for i in range(0, 1400, 37):
        mine = ff.run_rules([(p, m, 1) for p, m in pairs[i:]], r)
        assert mine[:2] == ff.lrb.lucid_run(pairs[i:])
    # and the table's own Lucid entry agrees on the numbers that matter
    t = ff.RULE_SETS["Lucid 100K LucidPro (price GUESS)"]
    assert (t["start"], t["target"], t["dd"], t["lock"]) == (
        ff.lrb.START_BAL, ff.lrb.TARGET - ff.lrb.START_BAL, ff.lrb.TRAIL,
        ff.lrb.LOCK_FLOOR - ff.lrb.START_BAL)


def test_calendar_days_accumulate_gaps():
    r = rule(target=1000.0, lock=None)
    out = ff.run_rules([(400, 0, 1), (400, 0, 3), (400, 0, 4)], r)
    assert out == ("pass", 3, 8)


def test_cost_model_geometric_attempts():
    r = rule(eval_fee=100.0, reset_fee=50.0, activation_fee=0.0)
    c = ff.cost_model(0.5, 0.5, r, 100.0, max_attempts=2, tpy=200)
    assert abs(c["attempts"] - 1.5) < 1e-12
    assert abs(c["p_any"] - 0.75) < 1e-12                 # 0.5 + 0.5 * 0.5
    assert abs(c["cost"] - (100 + 50 * 0.5) / 0.75) < 1e-9
    assert abs(c["years"] - 100 * 1.5 / 0.75 / 200) < 1e-9
    assert ff.cost_model(0.0, 1.0, r, 10.0)["cost"] is None


def test_rolling_and_bootstrap_agree_on_a_trivial_edge():
    # every trade +100 with no adverse move: every run passes in 60 trades
    s = [(100.0, 0.0, 1)] * 100
    r = rule(target=6000.0, lock=None)
    roll = ff.summarise(ff.rolling_runs(s, r))
    assert roll["pass_"] == 100 * 41 / 100                # starts 0..40 have 60 trades left
    boot = ff.summarise(ff.bootstrap_runs(s, {"x": r}, 20)["x"])
    assert boot["pass_"] == 100.0 and boot["med_trades"] == 60


def test_block_path_length_and_blocks():
    s = [(float(i), 0.0, 1) for i in range(50)]
    p = ff.block_path(s, random.Random(1), horizon=23, block=5)
    assert len(p) == 23
    # consecutive within a block (mod 50)
    assert all((p[k + 1][0] - p[k][0]) % 50 == 1 for k in range(4))


def test_make_seq_gaps():
    ts = [{"date": "2024-01-02", "pts": 1.0, "mae_pts": 0.5},
          {"date": "2024-01-05", "pts": -1.0, "mae_pts": 2.0}]
    out = ff.make_seq(ts, 0.0, 0)
    assert [g for _, _, g in out] == [1, 3]
    assert out[1][0] == -5.0 and out[1][1] == 10.0


def test_monthly_fee_scales_with_time_in_attempt():
    r = dict(ff.RULE_SETS["Topstep 100K Combine (standard)"])
    fast = ff.cost_model(0.5, 0.2, r, 100)["cost"]
    slow = ff.cost_model(0.5, 0.2, r, 800)["cost"]
    assert slow > fast
    r["monthly_fee"] = 0.0
    assert ff.cost_model(0.5, 0.2, r, 800)["cost"] < slow
