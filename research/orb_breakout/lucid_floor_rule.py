#!/usr/bin/env python3
"""
lucid_floor_rule.py

RESEARCH ONLY -- changes nothing live.

Question (2026-09-27): at 2 contracts one full stop costs $1,250. When the
cushion (balance minus trailing floor) falls below one full stop, is it better to
  A) stay at 2 contracts and accept a reset if it fails, or
  B) drop to 1 contract until the cushion is back above one full stop, or
  C) drop to 1 contract for the rest of that attempt?
After any reset, every policy starts again at 2 contracts.

Same engine and inputs as lucid_time_to_funded.py (live start state, 662 measured
trades resampled, lock rule, Ghost $828/yr), except the reset now costs $180
(Lucid pricing table, checked 2026-09-26). 1-contract-always is shown for reference.
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lucid_barrier_model as lbm
import lucid_time_to_funded as ttf

RESET_FEE = 180.00
FULL_STOP_2C = 1250.0
SIMS = 10000
SEED = 2709


def one_attempt(pnls1, rng, balance, peak, budget, policy):
    base = lbm.INITIAL_BALANCE
    locked = (peak - base) >= lbm.LOCK_TRIGGER_PROFIT
    stuck_at_1 = False
    dropped = False
    for tick in range(budget):
        floor = base + lbm.LOCKED_FLOOR_PROFIT if locked else peak - lbm.LOSS_LIMIT
        cushion = balance - floor
        if policy == "always1":
            size = 1
        elif policy == "always2":
            size = 2
        elif policy == "drop_and_return":
            size = 1 if cushion < FULL_STOP_2C else 2
        else:  # drop_and_stay
            if cushion < FULL_STOP_2C:
                stuck_at_1 = True
            size = 1 if stuck_at_1 else 2
        dropped |= size == 1 and policy != "always1"
        balance += rng.choice(pnls1) * size
        peak = max(peak, balance)
        if not locked and (peak - base) >= lbm.LOCK_TRIGGER_PROFIT:
            locked = True
        floor = base + lbm.LOCKED_FLOOR_PROFIT if locked else peak - lbm.LOSS_LIMIT
        if balance <= floor:
            return "fail", tick + 1, dropped
        if balance - base >= lbm.PROFIT_TARGET:
            return "pass", tick + 1, dropped
    return "timeout", budget, dropped


def road(pnls1, rng, policy):
    ticks, resets, first, a1 = 0, 0, True, False
    balance, peak = ttf.START_BALANCE, ttf.START_PEAK
    saved_by_drop = 0
    while ticks < ttf.MAX_TICKS_TOTAL:
        out, t, dropped = one_attempt(pnls1, rng, balance, peak, ttf.MAX_TICKS_TOTAL - ticks, policy)
        ticks += t
        if out == "pass":
            a1 |= first
            return True, ticks / lbm.TRADES_PER_YEAR, resets, a1
        if out == "timeout":
            break
        resets += 1
        first = False
        balance, peak = lbm.INITIAL_BALANCE, lbm.INITIAL_BALANCE
    return False, ticks / lbm.TRADES_PER_YEAR, resets, a1


def run(pnls1, policy):
    rng = random.Random(SEED)
    yrs, costs, rs = [], [], []
    a1 = unf = 0
    for _ in range(SIMS):
        f, y, r, a = road(pnls1, rng, policy)
        a1 += a
        if not f:
            unf += 1
            continue
        yrs.append(y); rs.append(r); costs.append(r * RESET_FEE + y * ttf.GHOST_PER_YEAR)
    yrs.sort(); costs.sort()
    return (100 * a1 / SIMS, sum(rs) / len(rs), sum(yrs) / len(yrs), ttf.pct(yrs, .5),
            ttf.pct(yrs, .8), sum(costs) / len(costs), ttf.pct(costs, .5), 100 * unf / SIMS)


def main():
    half_cost = lbm.smr.REAL_COST_POINTS[lbm.ES_LABEL]["free"] / 2.0
    live_1x = lbm.trade_dollars_1x(lbm.build_mes_trades(lbm.load(lbm.ES_PATH)), half_cost)
    edge = sum(live_1x) / len(live_1x)
    print(f"{len(live_1x)} trades, ${edge:+.2f}/trade/contract, reset ${RESET_FEE:.0f}, {SIMS} roads, seed {SEED}")
    for name, cut in (("FULL edge", 0.0), ("HALF edge", edge / 2), ("ZERO edge", edge)):
        pnls1 = [p - cut for p in live_1x]
        print(f"\n{name}")
        print(f"{'policy':<18}{'1st try':>8}{'resets':>8}{'yrs mean':>9}{'median':>8}{'80%':>7}"
              f"{'cost mean':>10}{'median':>8}{'>30y':>7}")
        for pol in ("always2", "drop_and_return", "drop_and_stay", "always1"):
            r = run(pnls1, pol)
            print(f"{pol:<18}{r[0]:7.1f}%{r[1]:8.2f}{r[2]:9.2f}{r[3]:8.2f}{r[4]:7.2f}"
                  f"{r[5]:10,.0f}{r[6]:8,.0f}{r[7]:6.1f}%")


if __name__ == "__main__":
    main()
