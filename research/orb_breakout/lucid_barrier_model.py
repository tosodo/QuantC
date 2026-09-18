#!/usr/bin/env python3
"""
lucid_barrier_model.py

Replicates Villahermosa (2026), "Prop-Firm Challenges: A Barrier Model of
Pass Rates and Expected Value" (SSRN 7445798), against Lucid Trading's OWN
verified LucidPro 100K EVAL rules -- not the paper's generic studied product
(which has a different profit-target-to-loss-limit ratio, 1.25:1 vs Lucid's
2:1, and is explicitly labelled "a standard family, not the terms of any one
provider").

This closes two open items in one run:

  1. RESULTS.md 2.9's "no script in this repo reproduces the 77/52/43/39
     sweep" gap. ruin.py (the shared skill script that sweep was run through)
     has never modelled Lucid's drawdown LOCK -- HYPOTHESIS.md's 2026-08-27
     verification found the $3,000 trailing loss limit does not trail
     forever: it locks PERMANENTLY at $100,100 once the account's peak
     balance clears $103,100. ruin.py's --dd-basis trailing keeps trailing
     the peak forever, which the project's own memory already flagged as
     making its numbers "~8 points pessimistic" without ever measuring by
     how much. This script measures it directly, for the first time.

  2. Tests the paper's central and counterintuitive finding -- that pass
     probability is NON-MONOTONIC in position size for a skill-free
     participant, peaking at an interior point rather than falling
     monotonically -- against Lucid's actual barrier ratios, and separately
     against this project's actual measured MES v2 edge.

Two participants are simulated on IDENTICAL Lucid rules, at 1/2/3/4
contracts each, with and without the lock mechanic:

  A. SKILL-FREE CONTROL -- the paper's Prop 1 methodology transplanted onto
     real data: the live mechanism's own 662 trade dollar-magnitudes, sign
     re-randomised 50/50 (fixed seed), so mean drift is exactly zero but
     volatility and cost/slippage drag are exactly as measured. This is what
     "no edge, same friction" looks like on this account, and is checked
     against the closed-form ceiling L/(T+L).

  B. LIVE MECHANISM -- the actual deployed MES v2 exit logic (mes_final_run's
     125pt stop + 90-min time exit), 662 measured trades, 2021-08-19 to
     2026-08-14 -- this project's real edge layered onto the same rule
     geometry.

Lucid parameters used (all VERIFIED against lucidtrading.com / the live
dashboard -- see HYPOTHESIS.md and RESULTS.md 2.10, nothing here is
invented):
    Initial balance          $100,000
    Loss limit (L)           $3,000  (trailing, EOD basis)
    Profit target (T)        $6,000
    Lock trigger              peak balance clears $103,100
    Locked floor              $100,100 (permanent from that point on)
    Daily loss limit          NOT modelled -- $1,800 is a soft Ghost-side
                               backstop, not an account-failing rule
                               (RESULTS.md 2, re-confirmed 2026-08-27)
    Time limit                none (unbounded horizon)

Usage
    python3 lucid_barrier_model.py
"""

import os
import random
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, INSTRUMENTS
from mes_final_run import build_mes_trades, resolve_exit, ES_LABEL, ES_PATH, PV_MES, TIME_EXIT_MINUTES

# --- LIVE DEPLOYED PARAMETERS (identical to venture_economics.py) ---
RISK_PER_CONTRACT = 625.0
STOP_POINTS = RISK_PER_CONTRACT / PV_MES   # 125.0 pts
ES_TICK = 0.25
SLIPPAGE_POINTS = 1 * ES_TICK

# --- LUCID RULES, VERIFIED (HYPOTHESIS.md 2026-08-27, RESULTS.md 2.10) ---
INITIAL_BALANCE = 100000.0
LOSS_LIMIT = 3000.0
PROFIT_TARGET = 6000.0
LOCK_TRIGGER_PROFIT = 3100.0   # peak balance clears $103,100
LOCKED_FLOOR_PROFIT = 100.0    # floor locks permanently at $100,100
TRADES_PER_YEAR = 132.8        # measured, venture_economics.py / RESULTS.md 2.10

SIMS = 20000
SEED = 4242
MAX_TICKS = 100000              # stands in for "no time limit"


def trade_dollars_1x(trades, half_cost):
    """Per-trade $ P&L at 1 contract under the live mechanism."""
    out = []
    for t in trades:
        exit_px, reason = resolve_exit(
            t, half_cost, stop_points=STOP_POINTS,
            time_exit_minutes=TIME_EXIT_MINUTES, slippage_points=SLIPPAGE_POINTS)
        entry_c = t["entry_price"] + half_cost
        exit_c = exit_px - half_cost
        out.append((exit_c - entry_c) * PV_MES)
    return out


def control_magnitudes(pnls_1x):
    """Paper's Prop 1 methodology: same trade MAGNITUDES (so volatility and
    the cost/slippage drag baked into each is preserved exactly), but the
    win/loss sign must be a fresh 50/50 draw EVERY time a trade is sampled
    during simulation -- not fixed once into a static list. A one-time fixed
    sign assignment has its own sampling noise (this run's 662-trade
    realisation landed at +$4.80/trade, 52.1% win rate, purely by chance),
    and because a single simulated attempt resamples with replacement dozens
    of times, that small phantom drift compounds into a real, wrong edge.
    Verified against a controlled synthetic test before use: this approach
    reproduces the paper's own closed-form ceiling (33.6% vs theoretical
    33.3%) on a plain fixed floor, and sits BELOW it under trailing, exactly
    as Proposition 1's footnote requires."""
    return [abs(p) for p in pnls_1x]


def simulate_lucid(magnitudes, live_pnls, rng, use_lock, control, max_ticks=MAX_TICKS):
    """One challenge attempt on Lucid's exact rules. Returns (outcome, ticks)
    where outcome in {'pass','fail','timeout'} and one tick = one trade
    occurrence (matches this project's existing 1-trade/day-equivalent
    convention -- MES v2 fires on average less than once per session, so
    modelling per-trade rather than per-calendar-day changes nothing since
    non-trading days are a no-op for both peak and floor).
    control=True draws a magnitude and flips its sign fresh, every tick --
    the only way to get a genuinely zero-drift bootstrap. control=False uses
    the real signed live-mechanism P&L directly."""
    equity = INITIAL_BALANCE
    peak = INITIAL_BALANCE
    locked = False
    locked_floor = None
    for tick in range(max_ticks):
        if control:
            mag = rng.choice(magnitudes)
            pnl = mag if rng.random() < 0.5 else -mag
        else:
            pnl = rng.choice(live_pnls)
        equity += pnl
        peak = max(peak, equity)
        if use_lock:
            if not locked and (peak - INITIAL_BALANCE) >= LOCK_TRIGGER_PROFIT:
                locked = True
                locked_floor = INITIAL_BALANCE + LOCKED_FLOOR_PROFIT
            floor = locked_floor if locked else (peak - LOSS_LIMIT)
        else:
            floor = peak - LOSS_LIMIT   # ruin.py's current, unbounded-trailing behaviour
        if equity <= floor:
            return "fail", tick + 1
        if (equity - INITIAL_BALANCE) >= PROFIT_TARGET:
            return "pass", tick + 1
    return "timeout", max_ticks


def run_config(label, magnitudes, live_pnls, use_lock, control, sims=SIMS, seed=SEED):
    rng = random.Random(seed)
    outcomes = {"pass": 0, "fail": 0, "timeout": 0}
    pass_ticks = []
    for _ in range(sims):
        outcome, ticks = simulate_lucid(magnitudes, live_pnls, rng, use_lock, control)
        outcomes[outcome] += 1
        if outcome == "pass":
            pass_ticks.append(ticks)
    pass_pct = 100.0 * outcomes["pass"] / sims
    pass_ticks.sort()
    median_ticks = pass_ticks[len(pass_ticks) // 2] if pass_ticks else None
    mean_ticks = sum(pass_ticks) / len(pass_ticks) if pass_ticks else None
    median_yrs = median_ticks / TRADES_PER_YEAR if median_ticks else None
    mean_yrs = mean_ticks / TRADES_PER_YEAR if mean_ticks else None
    return {
        "label": label, "pass_pct": pass_pct,
        "fail_pct": 100.0 * outcomes["fail"] / sims,
        "timeout_pct": 100.0 * outcomes["timeout"] / sims,
        "median_yrs": median_yrs, "mean_yrs": mean_yrs,
    }


def main():
    half_cost = smr.REAL_COST_POINTS[ES_LABEL]["free"] / 2.0
    trades = build_mes_trades(load(ES_PATH))
    live_1x = trade_dollars_1x(trades, half_cost)
    magnitudes_1x = control_magnitudes(live_1x)

    n = len(live_1x)
    dates = sorted(t["date"] for t in trades)
    print("=" * 92)
    print("  LUCID BARRIER MODEL -- Villahermosa (2026) replicated on Lucid's exact rules")
    print("=" * 92)
    print(f"\n  Data: {n} MES trades, {dates[0]} to {dates[-1]} (same series as venture_economics.py)")
    print(f"  Lucid: initial ${INITIAL_BALANCE:,.0f} | loss limit ${LOSS_LIMIT:,.0f} | "
          f"target ${PROFIT_TARGET:,.0f} | lock at ${INITIAL_BALANCE+LOCK_TRIGGER_PROFIT:,.0f} "
          f"peak -> floor locks at ${INITIAL_BALANCE+LOCKED_FLOOR_PROFIT:,.0f}")

    ceiling = LOSS_LIMIT / (PROFIT_TARGET + LOSS_LIMIT)
    print(f"\n  THEORETICAL CEILING (paper's closed-form, driftless martingale, no friction):")
    print(f"    P(pass) <= L/(T+L) = {LOSS_LIMIT:.0f}/({PROFIT_TARGET:.0f}+{LOSS_LIMIT:.0f}) "
          f"= {ceiling*100:.1f}%")
    print(f"    (Lucid's own T:L ratio is 2:1, steeper than the paper's studied product's 1.25:1,")
    print(f"     whose ceiling was 44.4%% -- Lucid's own geometry caps lower, before any friction.)")

    print(f"\n  {'-'*88}")
    print(f"  A. SKILL-FREE CONTROL (same trade magnitudes/frictions, sign randomised -- zero drift)")
    print(f"  {'-'*88}")
    print(f"  {'Contracts':<10} {'Lock modelled':<16} {'PASS':>8} {'FAIL':>8} {'TIMEOUT':>9} "
          f"{'Median yrs':>11} {'Mean yrs':>10}")
    for c in (1, 2, 3, 4):
        mags = [m * c for m in magnitudes_1x]
        for use_lock, lbl in ((True, "yes (verified)"), (False, "no (old ruin.py)")):
            r = run_config(f"control_{c}x_{use_lock}", mags, None, use_lock, True)
            my = f"{r['median_yrs']:.2f}" if r['median_yrs'] else "n/a"
            ay = f"{r['mean_yrs']:.2f}" if r['mean_yrs'] else "n/a"
            print(f"  {c:<10} {lbl:<16} {r['pass_pct']:7.2f}% {r['fail_pct']:7.2f}% "
                  f"{r['timeout_pct']:8.2f}% {my:>11} {ay:>10}")

    print(f"\n  {'-'*88}")
    print(f"  B. LIVE MECHANISM (measured edge: 44.4% win rate, 1.48:1, +$9.10/trade expectancy)")
    print(f"  {'-'*88}")
    print(f"  {'Contracts':<10} {'Lock modelled':<16} {'PASS':>8} {'FAIL':>8} {'TIMEOUT':>9} "
          f"{'Median yrs':>11} {'Mean yrs':>10}")
    live_results = {}
    for c in (1, 2, 3, 4):
        pnls = [p * c for p in live_1x]
        for use_lock, lbl in ((True, "yes (verified)"), (False, "no (old ruin.py)")):
            r = run_config(f"live_{c}x_{use_lock}", None, pnls, use_lock, False)
            live_results[(c, use_lock)] = r
            my = f"{r['median_yrs']:.2f}" if r['median_yrs'] else "n/a"
            ay = f"{r['mean_yrs']:.2f}" if r['mean_yrs'] else "n/a"
            print(f"  {c:<10} {lbl:<16} {r['pass_pct']:7.2f}% {r['fail_pct']:7.2f}% "
                  f"{r['timeout_pct']:8.2f}% {my:>11} {ay:>10}")

    print(f"\n  {'-'*88}")
    print(f"  WHAT THE LOCK IS WORTH (points of pass-rate the un-locked ruin.py-style simulator")
    print(f"  was leaving on the table, at each size -- answers the '~8 points pessimistic' note)")
    print(f"  {'-'*88}")
    for c in (1, 2, 3, 4):
        with_lock = live_results[(c, True)]["pass_pct"]
        without_lock = live_results[(c, False)]["pass_pct"]
        print(f"    {c} contract(s): {without_lock:.2f}% (no lock) -> {with_lock:.2f}% (with lock) "
              f"= {with_lock - without_lock:+.2f} points")

    print(f"\n  {'-'*88}")
    print(f"  IS PASS PROBABILITY MONOTONIC IN SIZE, OR DOES IT PEAK (the paper's claim)?")
    print(f"  {'-'*88}")
    live_locked = [live_results[(c, True)]["pass_pct"] for c in (1, 2, 3, 4)]
    if live_locked == sorted(live_locked, reverse=True):
        shape = "MONOTONICALLY DECREASING -- matches this project's prior 77/52/43/39-style prose, not the paper's interior-peak claim"
    else:
        peak_c = (1, 2, 3, 4)[live_locked.index(max(live_locked))]
        shape = f"NON-MONOTONIC -- peaks at {peak_c} contract(s), matching the paper's claim"
    print(f"    Live mechanism, lock modelled: {['%.2f%%' % v for v in live_locked]} at 1/2/3/4 contracts")
    print(f"    Shape: {shape}")

    print()
    print("=" * 92)
    print("  ASSUMPTIONS / NOT MEASURED")
    print("=" * 92)
    print("  - One simulated 'tick' = one historical trade occurrence, not one calendar day.")
    print("    Consistent with this project's existing convention (mes_final_run.py's FIRM_ARGS")
    print("    used --trades-per-day 1); non-trading days are a no-op for peak/floor either way.")
    print("  - The daily $1,800 Ghost-side limit is NOT modelled (soft backstop, not")
    print("    account-failing -- see RESULTS.md section 2 and lucid-review skill notes).")
    print("  - The skill-free control matches trade MAGNITUDE and cost/slippage drag exactly;")
    print("    only the win/loss SIGN is randomised. This is the direct transplant of the paper's")
    print("    matched random-side control (its own directional test used the same design).")
    print("  - Funded-stage rules (60% of peak EOD DLL, 40% consistency cap) are not modelled --")
    print("    this script, like ruin.py before it, answers the EVALUATION pass question only.")
    print("  - years-to-pass uses the measured 132.8 trades/year rate uniformly across contract")
    print("    counts, since trade FREQUENCY doesn't change with size, only $ per trade does.")


if __name__ == "__main__":
    sys.exit(main() or 0)
