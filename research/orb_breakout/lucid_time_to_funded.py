#!/usr/bin/env python3
"""
lucid_time_to_funded.py

RESEARCH ONLY -- changes nothing live.

lucid_barrier_model.py answers "what is the chance a single attempt passes, at
1/2/3/4 contracts?" and found 1 contract best (77/53/44/40%). That is the
right answer if the goal is the highest single-attempt pass rate. It is not
necessarily the right answer if the goal is the shortest, cheapest road to a
funded account, because:

  - a failed attempt is not the end: Lucid sells a reset for $225, and
  - time is not free: Ghost costs ~$828/year for as long as the grind lasts.

Villahermosa (2026, SSRN 7445798, Section 5 "The repeated purchase") prices an
evaluation exactly this way -- as a repeated purchase, not a one-shot bet.
This script applies that framing to Lucid's exact rules and this project's
measured edge, and asks, for each size:

    how long, and how much money, until the account is funded --
    counting every reset and every month of Ghost along the way?

Model
  - Attempt 1 starts from the REAL account as of 2026-09-26 (balance $100,099,
    trailing floor $97,178, i.e. peak $100,178, lock not yet triggered).
    If the size changes, it changes on this live account from here on.
  - Every later attempt starts fresh at $100,000 and costs a $225 reset.
  - Same barrier rules as lucid_barrier_model.py (trailing $3,000 floor that
    locks at $100,100 once the peak clears $103,100; target +$6,000).
  - Same per-trade P&L source: the 662 measured live-mechanism trades,
    resampled with replacement, scaled by contract count.
  - Time: 132.8 trades/year (measured). Ghost: $828/year, pro rata.
  - Edge-erosion sensitivity: the live edge is only +4.1 points of win rate
    above break-even, so every size is also run with that edge cut in half
    (a flat -$4.55/contract/trade haircut).

Usage
    ./venv/bin/python lucid_time_to_funded.py
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lucid_barrier_model as lbm

# --- STARTING STATE, LIVE (Lucid dashboard, reconciled 2026-09-26) ---
START_BALANCE = 100099.0
START_PEAK = 100178.0          # floor $97,178 + $3,000 trail

# --- COSTS ---
RESET_FEE = 225.00             # venture_economics.py / RESULTS.md, verified 2026-09-11
GHOST_PER_YEAR = 828.00        # QuantCrawler Ghost Unlimited, verified 2026-09-17

SIMS = 5000
SEED = 4242
MAX_YEARS = 30.0               # a run still unfunded after 30 years is reported, not averaged
MAX_TICKS_TOTAL = int(MAX_YEARS * lbm.TRADES_PER_YEAR)


def one_attempt(pnls, rng, balance, peak, budget):
    """One attempt from a given state. Returns (outcome, ticks_used)."""
    base = lbm.INITIAL_BALANCE
    locked = (peak - base) >= lbm.LOCK_TRIGGER_PROFIT
    for tick in range(budget):
        balance += rng.choice(pnls)
        peak = max(peak, balance)
        if not locked and (peak - base) >= lbm.LOCK_TRIGGER_PROFIT:
            locked = True
        floor = base + lbm.LOCKED_FLOOR_PROFIT if locked else peak - lbm.LOSS_LIMIT
        if balance <= floor:
            return "fail", tick + 1
        if balance - base >= lbm.PROFIT_TARGET:
            return "pass", tick + 1
    return "timeout", budget


def road_to_funded(pnls, rng):
    """Keep attempting (resetting after each failure) until funded or MAX_YEARS.
    Returns (funded, years, resets, attempt1_passed)."""
    ticks_used = 0
    resets = 0
    balance, peak = START_BALANCE, START_PEAK
    first = True
    attempt1_passed = False
    while ticks_used < MAX_TICKS_TOTAL:
        outcome, t = one_attempt(pnls, rng, balance, peak, MAX_TICKS_TOTAL - ticks_used)
        ticks_used += t
        if outcome == "pass":
            if first:
                attempt1_passed = True
            return True, ticks_used / lbm.TRADES_PER_YEAR, resets, attempt1_passed
        if outcome == "timeout":
            break
        resets += 1
        first = False
        balance, peak = lbm.INITIAL_BALANCE, lbm.INITIAL_BALANCE
    return False, ticks_used / lbm.TRADES_PER_YEAR, resets, attempt1_passed


def pct(sorted_vals, q):
    return sorted_vals[min(len(sorted_vals) - 1, int(q * len(sorted_vals)))]


def run(pnls, seed=SEED):
    rng = random.Random(seed)
    years, costs, resets_list = [], [], []
    unfunded = 0
    a1 = 0
    for _ in range(SIMS):
        funded, yrs, resets, a1p = road_to_funded(pnls, rng)
        a1 += a1p
        if not funded:
            unfunded += 1
            continue
        years.append(yrs)
        resets_list.append(resets)
        costs.append(resets * RESET_FEE + yrs * GHOST_PER_YEAR)
    years.sort()
    costs.sort()
    return {
        "attempt1_pct": 100.0 * a1 / SIMS,
        "unfunded_pct": 100.0 * unfunded / SIMS,
        "mean_years": sum(years) / len(years),
        "median_years": pct(years, 0.5),
        "p80_years": pct(years, 0.8),
        "mean_resets": sum(resets_list) / len(resets_list),
        "mean_cost": sum(costs) / len(costs),
        "median_cost": pct(costs, 0.5),
        "p80_cost": pct(costs, 0.8),
    }


def main():
    half_cost = lbm.smr.REAL_COST_POINTS[lbm.ES_LABEL]["free"] / 2.0
    trades = lbm.build_mes_trades(lbm.load(lbm.ES_PATH))
    live_1x = lbm.trade_dollars_1x(trades, half_cost)
    edge = sum(live_1x) / len(live_1x)

    print("=" * 100)
    print("  LUCID TIME-TO-FUNDED -- counting resets ($225) and Ghost ($828/yr) until funded")
    print("=" * 100)
    print(f"  {len(live_1x)} measured trades, expectancy ${edge:+.2f}/trade at 1 contract, "
          f"{lbm.TRADES_PER_YEAR} trades/yr")
    print(f"  Start: live account ${START_BALANCE:,.0f}, peak ${START_PEAK:,.0f}, "
          f"${lbm.INITIAL_BALANCE + lbm.PROFIT_TARGET - START_BALANCE:,.0f} to target. "
          f"{SIMS:,} simulated roads per row, seed {SEED}.")

    scenarios = (("FULL measured edge", 0.0), ("HALF the edge (execution erosion)", edge / 2.0))
    for name, haircut in scenarios:
        print(f"\n  {'-' * 96}")
        print(f"  {name}: ${edge - haircut:+.2f}/trade per contract")
        print(f"  {'-' * 96}")
        print(f"  {'Size':<6}{'1st try':>9}{'Resets':>8}{'Years: mean':>13}{'median':>8}{'80%':>7}"
              f"{'Cost: mean':>12}{'median':>9}{'80%':>8}{'>30yr':>8}")
        for c in (1, 2, 3, 4):
            pnls = [(p - haircut) * c for p in live_1x]
            r = run(pnls)
            print(f"  {c:<6}{r['attempt1_pct']:8.1f}%{r['mean_resets']:8.2f}"
                  f"{r['mean_years']:13.2f}{r['median_years']:8.2f}{r['p80_years']:7.2f}"
                  f"{r['mean_cost']:12,.0f}{r['median_cost']:9,.0f}{r['p80_cost']:8,.0f}"
                  f"{r['unfunded_pct']:7.1f}%")

    print()
    print("  Columns: '1st try' = chance the CURRENT account passes without a reset. 'Resets' = average")
    print("  resets bought. Years/Cost are for roads that reach funded; Cost = resets + Ghost, excluding")
    print("  the $307 already paid. '>30yr' = roads still unfunded after 30 years (excluded from averages).")
    print()
    print("  NOT MODELLED: Lucid's review of 'excessive' single-day profits at larger sizes; the funded")
    print("  stage itself; TradingView subscription; the $1,800 daily limit (soft, Ghost-side); any change")
    print("  in trade frequency. Past trades are resampled, so regime change is not represented.")


if __name__ == "__main__":
    sys.exit(main() or 0)
