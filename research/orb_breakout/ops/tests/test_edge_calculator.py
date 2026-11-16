"""Tests for ../../edge_calculator.py: the closed form against the rule engine, the
t-stat arithmetic, the Deflated Sharpe direction, and the CSV reader."""
import csv
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import edge_calculator as ec  # noqa: E402
import firm_fit_test as ff  # noqa: E402

RULE = ff.RULE_SETS[ec.LUCID]


def test_pass_prob_known_values():
    # verified against a Monte Carlo of the rule engine (upper bounds: no time limit)
    for mu, want in ((0, 0.181), (1, 0.366), (2, 0.572), (4.1, 0.866), (8, 0.991)):
        assert abs(ec.pass_prob(mu, 84, RULE) - want) < 0.002


def test_pass_prob_monotone_and_bounded():
    ps = [ec.pass_prob(m, 84, RULE) for m in (-5, -1, 0, 1, 5, 50, 5000)]
    assert ps == sorted(ps) and 0 <= ps[0] and ps[-1] <= 1


def test_pass_prob_continuous_at_zero_drift():
    assert abs(ec.pass_prob(1e-7, 84, RULE) - ec.pass_prob(0, 84, RULE)) < 1e-4


def test_trades_for_t():
    assert abs(ec.trades_for_t(4.1, 84) - (3 * 84 / 4.1) ** 2) < 1e-9
    assert ec.trades_for_t(0, 84) is None and ec.trades_for_t(-1, 84) is None


def test_t_stat():
    assert abs(ec.t_stat(4.0, 84.0, 996) - 4.0 / (84.0 / math.sqrt(996))) < 1e-12


def test_expected_max_grows_with_trials():
    assert ec.expected_max_z(1) == 0.0
    assert ec.expected_max_z(10) < ec.expected_max_z(100) < ec.expected_max_z(1000)


def test_deflated_sharpe_falls_with_more_trials():
    rng = random.Random(3)
    x = [rng.gauss(10, 84) for _ in range(500)]
    m = ec.moments(x)
    assert ec.deflated_sharpe(m, 1) > ec.deflated_sharpe(m, 12) > ec.deflated_sharpe(m, 500)


def test_pure_noise_not_significant():
    rng = random.Random(5)
    x = [rng.gauss(0, 84) for _ in range(400)]
    m = ec.moments(x)
    lo, hi = ec.boot_ci(x, 500)
    assert lo < 0 < hi and ec.deflated_sharpe(m, 12) < 0.95


def test_load_pnls_columns(tmp_path):
    p = tmp_path / "t.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sequence", "date", "pnl", "pts"])
        w.writerow(["A", "2024-01-02", "10.5", ""])
        w.writerow(["B", "2024-01-03", "", "2"])
        w.writerow(["A", "2024-01-04", "-3", ""])
    assert ec.load_pnls(str(p), "pnl", "A", 2.5, 1) == [10.5, -3.0]
    got = ec.load_pnls(str(p), "pnl", "B", 2.5, 1)
    assert len(got) == 1 and abs(got[0] - ((2 - 1 * 0.25) * 5 - 2.5)) < 1e-9
