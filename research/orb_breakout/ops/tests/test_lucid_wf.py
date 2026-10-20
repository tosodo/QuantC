"""Tests for ../../lucid_wf_test.py: the variant replay equals the live replay with the
default parameters, each variant does what it says, the walk-forward never lets test
data into a selection, the fast eval equals the rule engine, and the criteria."""
import os
import random
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
import firm_fit_test as ff  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402
import lucid_wf_test as wf  # noqa: E402
import shadow_day  # noqa: E402

T0 = int(datetime(2024, 3, 4, 9, 30, tzinfo=wf.ET).timestamp())


def flat_day(spec, fill, n=390):
    """spec: {minute index: (o, h, l, c)}; every other minute is flat at `fill`."""
    bars = []
    for k in range(n):
        o, h, l, c = spec.get(k, (fill,) * 4)
        bars.append({"t": T0 + 60 * k, "o": o, "h": h, "l": l, "c": c})
    return bars


def range_then_break(extra, fill=150.0):
    """15 flat range bars at 100 with a 101 high, entry bar 9:45 closing 102."""
    spec = {k: (100, 100, 100, 100) for k in range(15)}
    spec[3] = (100, 101, 100, 100)
    spec[15] = (101, 102, 101, 102)
    spec.update(extra)
    return flat_day(spec, fill)


def replay(bars, **kw):
    return wf.replay_variant(wf.prep_day(bars), "2024-03-04", **kw)


def test_default_replay_equals_live_replay_day():
    for stop in (125.0, 4.0):                      # 4 pts makes the stop path common
        shadow_day.STOP_PTS = stop
        try:
            for d, bars in wf.synth_days(80, seed=2).items():
                live = shadow_day.replay_day(bars, d)
                mine = wf.replay_variant(wf.prep_day(bars), d, stop=stop)
                assert live["state"] == mine["state"]
                if live["state"] in ("entry", "open"):
                    assert live["entry"] == mine["entry"]
                    assert abs(live["mae_pts"] - mine["mae_pts"]) < 1e-9
                    if live["state"] == "entry":
                        assert live["exit_reason"] == mine["exit_reason"]
                        assert abs(live["pts"] - mine["pts"]) < 1e-9
        finally:
            shadow_day.STOP_PTS = 125.0


def test_default_build_equals_live_build():
    days = wf.synth_days(120, seed=4)
    live, _ = lrb.build_trades(days)
    mine, _ = wf.build_variant_trades(wf.prep_days(days), wf.CANDIDATES["LIVE"])
    assert [(t["date"], t["pts"], t["mae_pts"], t["exit_reason"]) for t in live] == \
        [(t["date"], t["pts"], t["mae_pts"], t["exit_reason"]) for t in mine]


def test_range_window_changes_the_range_and_the_first_entry_bar():
    # 5-minute range: bars 0-4 only, so the 101 high at minute 3 is the high and the
    # 9:35 bar onward may enter; a close above 101 at minute 5 enters there
    spec = {k: (100, 100, 100, 100) for k in range(15)}
    spec[3] = (100, 101, 100, 100)
    spec[5] = (101, 103, 101, 102)
    bars = flat_day(spec, 102)
    assert replay(bars, range_min=5)["entry"] == 102
    assert replay(bars, range_min=15)["state"] == "no_breakout"      # 15-min high is 103
    # a 30-minute range needs 30 bars before 10:00
    assert replay(bars[:20], range_min=30)["state"] == "no_range"


def test_last_entry_blocks_late_breakouts():
    bars = flat_day({k: (100, 100, 100, 100) for k in range(15)} | {61: (100, 105, 100, 104)}, 100)
    assert replay(bars)["state"] == "entry"                               # live: enters at 10:31
    assert replay(bars, last_entry=10 * 60 + 30)["state"] == "no_breakout"
    assert replay(bars, last_entry=10 * 60 + 32)["state"] == "entry"


def test_stop_size_sets_the_stop():
    bars = range_then_break({20: (102, 102, 40, 50)})
    assert replay(bars, stop=125.0)["exit_reason"] != "stop"
    r = replay(bars, stop=60.0)                                           # stop at 42; low 40
    assert r["exit_reason"] == "stop" and r["pts"] == -60.0


def test_no_partial_matches_hand_numbers():
    r = replay(range_then_break({16: (102, 165, 101, 150)}))
    assert r["exit_reason"] == "session_close" and r["pts"] == 48.0 and r["mae_pts"] == 1.0


def test_partial_fill_blends_the_points():
    r = replay(range_then_break({16: (102, 165, 101, 150)}), partial=60.0)
    assert r["partial_filled"] and r["pts"] == 0.5 * 60 + 0.5 * 48 and r["mae_pts"] == 1.0


def test_partial_not_reached_changes_nothing():
    a = replay(range_then_break({16: (102, 150, 101, 150)}), partial=60.0)   # high 150 < 162? no
    # target is 102 + 60 = 162; a 150 high does not reach it
    b = replay(range_then_break({16: (102, 150, 101, 150)}))
    assert not a["partial_filled"] and a["pts"] == b["pts"] and a["mae_pts"] == b["mae_pts"]


def test_stop_taken_before_partial_in_the_same_bar():
    r = replay(range_then_break({16: (102, 165, -30, 120)}), partial=60.0)
    assert r["exit_reason"] == "stop" and not r["partial_filled"]
    assert r["pts"] == -125.0 and r["mae_pts"] == 132.0


def test_partial_then_time_exit_halves_the_remaining_excursion():
    r = replay(range_then_break({16: (102, 165, 101, 120), 17: (120, 120, 100, 100)}, fill=100.0),
               partial=60.0)
    assert r["partial_filled"] and r["exit_reason"] == "time_exit_90min"
    assert r["pts"] == 0.5 * 60 + 0.5 * (100 - 102)
    assert r["mae_pts"] == 1.0                      # 1.0 before the fill; 0.5 x 2 after it


def test_stop_share_numbers():
    assert wf.stop_share(1, 125) == 625 / 3000
    assert round(wf.stop_share(2, 125), 4) == 0.4167 and wf.stop_share(2, 120) == 0.4
    assert wf.stop_share(3, 75) == 0.375


def test_candidates_capped_and_stops_not_larger_than_live():
    assert len(wf.CANDIDATES) == 12 and "LIVE" in wf.CANDIDATES
    assert max(c["stop"] for c in wf.CANDIDATES.values()) == 125.0
    assert abs(wf.Z_BONF - 2.87) < 0.01


def test_fast_pass_equals_rule_engine():
    rule = ff.RULE_SETS[wf.LUCID_EVAL]
    rng = random.Random(8)
    for _ in range(300):
        seq = []
        for _ in range(rng.randrange(1, 400)):
            win = rng.random() < 0.3
            pnl = rng.uniform(50, 700) if win else -rng.uniform(100, 700)
            seq.append((pnl, rng.uniform(0, 900) if not win else rng.uniform(0, 100), 1))
        assert wf.fast_pass(seq, rule) == (ff.run_rules(seq, rule)[0] == "pass")


def trades_over(months, pts=1.0, per_month=22):
    out = []
    for m in months:
        y, mo = divmod(m, 12)
        for d in range(per_month):
            out.append(dict(date=f"{y:04d}-{mo + 1:02d}-{d + 1:02d}", pts=pts, mae_pts=3.0,
                            exit_reason="session_close"))
    return out


def test_folds_are_24_train_6_test_and_end_before_the_last_month():
    # Aug 2021 .. Aug 2026 inclusive is 61 month indexes, the real data's span
    dates = [t["date"] for t in trades_over(range(2021 * 12 + 7, 2021 * 12 + 7 + 61))]
    folds = wf.make_folds(dates)
    assert len(folds) == 6
    first = 2021 * 12 + 7
    assert folds[0] == (first, first + 24, first + 30)
    assert folds[-1][2] == first + 60          # the last test month is Jul 2026; Aug is left out
    # test windows are contiguous and never overlap training of the same fold
    assert all(f[0] + 24 == f[1] for f in folds)
    assert all(folds[i][2] == folds[i + 1][1] for i in range(len(folds) - 1))


def test_selection_never_sees_test_data():
    months = list(range(2021 * 12 + 7, 2021 * 12 + 67))
    a = {"LIVE": trades_over(months, 0.5), "S100": trades_over(months, 0.7)}
    log1, oos1 = wf.walk_forward(a, 2.5, 1)
    # make every TEST-window trade of S100 terrible: picks must not change, because the
    # selection looked only at the training months
    b = {"LIVE": a["LIVE"], "S100": []}
    for t in a["S100"]:
        in_test = any(lo <= wf.month_idx(t["date"]) < hi for _, lo, hi in wf.make_folds(
            [x["date"] for x in a["LIVE"]]))
        b["S100"].append({**t, "pts": -50.0} if in_test else t)
    log2, _ = wf.walk_forward(b, 2.5, 1)
    # fold 1's training months precede every test window, so its pick is the same
    assert log1[0]["pick"] == log2[0]["pick"]
    # out-of-sample trades are exactly the test-window trades, each date once
    dates = [t["date"] for t in oos1["WF"]]
    assert len(dates) == len(set(dates))
    assert all(any(lo <= wf.month_idx(d) < hi for _, lo, hi in wf.make_folds(
        [x["date"] for x in a["LIVE"]])) for d in dates)


def meta(**kw):
    return {**dict(n=600, per_year=200, partial=False, stop_mean=100, stop_max=100), **kw}


def test_deciding_sizes():
    assert wf.deciding_sizes(meta()) == [1, 2]
    assert wf.deciding_sizes(meta(stop_mean=125, stop_max=125)) == [1]        # 41.7% at 2 MES
    assert wf.deciding_sizes(meta(partial=True)) == [2]
    assert wf.deciding_sizes(meta(stop_max=125, partial=True)) == []


def res_row(pass_, cost, net):
    return dict(pass_=pass_, cost=cost, net=net)


def test_judge_needs_all_six():
    live_m = meta(stop_mean=125, stop_max=125)
    res = {"LIVE": {1: res_row(60, 300, 100), 2: res_row(41, 400, 200)},
           "X": {1: res_row(66, 250, 150), 2: res_row(47, 330, 250)}}
    ci = {"X": {1: (6.0, 1.0), 2: (6.0, 1.0)}}
    flags, beats = wf.judge("X", res, ci, meta(), live_m)
    assert beats and set(flags) == {1, 2}
    # each criterion on its own breaks it
    for key, bad in (("pass", dict(res={"X": {1: res_row(63, 250, 150), 2: res_row(47, 330, 250)}})),
                     ("cost", dict(res={"X": {1: res_row(66, 270, 150), 2: res_row(47, 330, 250)}})),
                     ("net", dict(res={"X": {1: res_row(66, 250, 90), 2: res_row(47, 330, 250)}})),
                     ("ci", dict(ci={"X": {1: (6.0, 3.0), 2: (6.0, 1.0)}})),
                     ("meta", dict(m=meta(per_year=150))),
                     ("trades", dict(m=meta(n=300)))):
        r = {"LIVE": res["LIVE"], **bad.get("res", res)}
        _, b = wf.judge("X", r, bad.get("ci", ci), bad.get("m", meta()), live_m)
        assert not b, key
    # no interval computed -> cannot beat the live rules
    assert not wf.judge("X", res, {}, meta(), live_m)[1]


def test_paired_ci_of_a_sequence_with_itself_is_zero():
    t = trades_over(range(2023 * 12, 2023 * 12 + 12), pts=1.0)
    m, sd = wf.paired_ci(t, t, 1, 2.5, 1, outer=4, inner=6, weeks=60)
    assert m == 0.0 and sd == 0.0


def test_threshold_solver_brackets_the_goal():
    rule = ff.RULE_SETS[wf.LUCID_EVAL]
    rng = random.Random(1)
    us = [[rng.random() for _ in range(600)] for _ in range(120)]
    w = wf.min_win_for(rule, us, 0.4, 500.0)
    assert w is not None
    assert wf.pass_prob(rule, us, 0.4, w, 500.0) >= 0.6
    assert wf.pass_prob(rule, us, 0.4, w * 0.8, 500.0) < 0.6
    assert wf.pass_prob(rule, us, 0.4, 50.0, 1875.0) < 0.6


def test_small_end_to_end_run_on_synthetic_data(capsys, tmp_path):
    class A:
        synthetic, data, sims, fsims, ci_outer, ci_inner = 1300, "", 20, 20, 2, 3
        cost, slip = 2.5, 1
        trades_out = str(tmp_path / "t.csv")
    wf.run_report(A)
    out = capsys.readouterr().out
    for s in ("Unverified inputs", "Verdict", "SYNTHETIC", "## 1 MES", "## 3 MES", "Criteria"):
        assert s in out
    assert os.path.exists(A.trades_out)
