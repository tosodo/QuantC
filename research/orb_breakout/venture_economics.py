#!/usr/bin/env python3
"""
venture_economics.py - RESULTS.md section 2.10.

Closes the one hole no file in this project has ever filled: the whole
programme has been optimised for "will this account PASS", and never once
for "will this venture PAY". Those are different questions, and a
configuration can win the first while losing the second.

It answers three, in order:

  1. PER-TRADE ECONOMICS of the mechanism that is ACTUALLY DEPLOYED
     (MES, 1 contract, 125pt stop, 90-min underwater time exit, 1 tick
     adverse slippage on every exit, real Tradovate free-tier costs).
     Win rate, average winner, average loser, and expectancy per trade --
     the standard expectancy identity. No file in this repo has ever
     printed these for the live mechanism; the often-quoted 57.2% / +0.173R
     belongs to the RETIRED no-stop, NQ+ES-pooled mechanism and is not
     what runs.

  2. TIME TO TARGET at the measured trade frequency.

  3. VENTURE RETURN against Lucid's REAL fee structure.

Fee structure VERIFIED 2026-09-11 directly from lucidtrading.com's own
pricing table and FAQ (read live, not inferred, not from a third-party
tracker):
    LucidPro 100K EVAL  one-time fee  $307 ($225.40 with coupon VAULT)
    Reset fee                          $225
    Account activation fee             FREE
    FAQ, verbatim: "Do I have to pay monthly for my accounts? No. All of
    our accounts are a one-time fee, we do not have monthly subscriptions
    for trading accounts."
    Funded split 90/10; payout target $750/cycle.

That last fact is load-bearing and corrects an assumption that was briefly
entertained in this project on 2026-09-11: there is NO recurring cost of
holding this evaluation open. Time spent grinding is not money bleeding.
The cost of the attempt is sunk and bounded; the thing actually at risk is
the opportunity cost of the years, not the fee.

Every number below is either MEASURED here from the same 5-year 1-minute
dataset every other file in this folder uses, VERIFIED against a named
external source, or flagged ASSUMPTION. Nothing is estimated.

Usage
    python3 venture_economics.py
    python3 venture_economics.py --remaining 6083 --contracts 1
"""

import argparse
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, MEAN_REV_DIR)
import screen_mean_reversion as smr
from orb_test import load, INSTRUMENTS
from mes_final_run import (build_mes_trades, resolve_exit, ES_LABEL, ES_PATH,
                           PV_MES, TIME_EXIT_MINUTES)

# --- LIVE DEPLOYED PARAMETERS (read from orb_long_ghost_DRAFT_mes_v2_accessible.pine) ---
RISK_PER_CONTRACT = 625.0          # input "Max $ risk per CONTRACT"
STOP_POINTS = RISK_PER_CONTRACT / PV_MES   # = 125.0 pts on MES ($5/pt)
ES_TICK = 0.25
SLIPPAGE_POINTS = 1 * ES_TICK      # 1 tick, the realistic case per RESULTS.md 2.7

# --- VERIFIED 2026-09-11 from lucidtrading.com pricing table + FAQ ---
EVAL_FEE_LIST = 307.00
EVAL_FEE_COUPON = 225.40
RESET_FEE = 225.00
ACTIVATION_FEE = 0.00
RECURRING_FEE_PER_MONTH = 0.00     # FAQ: "one-time fee, no monthly subscriptions"
FUNDED_SPLIT_TO_TRADER = 0.90
PAYOUT_TARGET_PER_CYCLE = 750.00


def trade_dollars(trades, half_cost, contracts):
    """Realised $ P&L per trade under the LIVE mechanism, net of cost+slippage."""
    out = []
    for t in trades:
        exit_px, reason = resolve_exit(
            t, half_cost,
            stop_points=STOP_POINTS,
            time_exit_minutes=TIME_EXIT_MINUTES,
            slippage_points=SLIPPAGE_POINTS)
        entry_c = t["entry_price"] + half_cost
        exit_c = exit_px - half_cost
        out.append(((exit_c - entry_c) * PV_MES * contracts, reason, t["date"]))
    return out


def longest_losing_streak(pnls):
    worst = cur = 0
    for p in pnls:
        cur = cur + 1 if p < 0 else 0
        worst = max(worst, cur)
    return worst


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remaining", type=float, default=6083.0,
                    help="dollars still needed to hit the $6,000 target "
                         "(default 6083, the figure recorded 2026-09-10; "
                         "CONFIRM against dash.lucidtrading.com before "
                         "leaning on it)")
    ap.add_argument("--contracts", type=int, default=1,
                    help="contracts per signal (live value is 1, hard-locked)")
    a = ap.parse_args()

    half_cost = smr.REAL_COST_POINTS[ES_LABEL]["free"] / 2.0
    trades = build_mes_trades(load(ES_PATH))
    rows = trade_dollars(trades, half_cost, a.contracts)
    pnls = [r[0] for r in rows]
    dates = sorted(r[2] for r in rows)

    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / n
    avg_win = sum(wins) / len(wins)
    avg_loss = sum(losses) / len(losses)          # negative
    expectancy = sum(pnls) / n
    # identity check: WR*avgWin + (1-WR)*avgLoss == mean
    identity = win_rate * avg_win + (1 - win_rate) * avg_loss

    span_days = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[0])).days
    years = span_days / 365.25
    trades_per_year = n / years

    print("=" * 78)
    print("  VENTURE ECONOMICS - the deployed MES v2 mechanism, end to end")
    print("=" * 78)
    print(f"\n  Mechanism (LIVE, from the .pine source):")
    print(f"    MES, {a.contracts} contract(s) | stop {STOP_POINTS:.0f} pts "
          f"(= ${RISK_PER_CONTRACT:.0f}/contract) | {TIME_EXIT_MINUTES}-min underwater exit")
    print(f"    costs: Tradovate free tier | slippage: {SLIPPAGE_POINTS} pt "
          f"({int(SLIPPAGE_POINTS/ES_TICK)} tick) on EVERY exit")

    print(f"\n  1. PER-TRADE ECONOMICS (MEASURED, {n} trades, "
          f"{dates[0]} to {dates[-1]})")
    print(f"     Win rate            : {win_rate*100:.1f}%")
    print(f"     Average WINNER      : ${avg_win:+,.2f}")
    print(f"     Average LOSER       : ${avg_loss:+,.2f}")
    print(f"     Reward:risk (avg)   : {abs(avg_win/avg_loss):.2f} : 1")
    print(f"     EXPECTANCY / trade  : ${expectancy:+,.2f}")
    print(f"       check  WR*win + (1-WR)*loss = ${identity:+,.2f}  (matches mean)")
    print(f"     Worst single trade  : ${min(pnls):,.2f}")
    print(f"     Best single trade   : ${max(pnls):,.2f}")
    streak = longest_losing_streak(pnls)
    print(f"     Longest losing run  : {streak} trades "
          f"(MEASURED, actual historical order)")

    # --- the margin of safety: how far above break-even does this actually sit? ---
    rr = abs(avg_win / avg_loss)
    breakeven_wr = 1.0 / (1.0 + rr)
    margin_pts = (win_rate - breakeven_wr) * 100
    print(f"\n     MARGIN OF SAFETY (the number that decides everything)")
    print(f"       At {rr:.2f}:1 reward:risk, break-even win rate is "
          f"{breakeven_wr*100:.1f}%")
    print(f"       Measured win rate is                      {win_rate*100:.1f}%")
    print(f"       MARGIN                                    {margin_pts:+.1f} "
          f"percentage points")
    wr_lo = breakeven_wr
    print(f"       Read plainly: lose {margin_pts:.1f} points of win rate to real-world")
    print(f"       execution -- worse fills, Ghost latency, a missed alert -- and the")
    print(f"       edge is GONE. This is a thin, real edge, not a comfortable one.")

    print(f"\n  2. TIME TO TARGET (MEASURED frequency, mean-path arithmetic)")
    print(f"     Trade frequency     : {trades_per_year:.1f} trades/year "
          f"({n} over {years:.1f} years)")
    per_year = expectancy * trades_per_year
    trades_needed = a.remaining / expectancy
    years_needed = trades_needed / trades_per_year
    print(f"     Gross P&L / year    : ${per_year:+,.0f}")
    print(f"     Still needed        : ${a.remaining:,.0f}")
    print(f"     Trades to target    : {trades_needed:,.0f}")
    print(f"     Years to target     : {years_needed:.1f}  (mean path, "
          f"ignores variance)")
    print(f"     NOTE: ruin.py's 77% pass / ~3.7yr median-if-passing is the")
    print(f"           variance-aware figure and is CONDITIONAL on passing;")
    print(f"           this line is the simple average pace. Both belong.")

    print(f"\n  3. VENTURE RETURN (fees VERIFIED 2026-09-11 @ lucidtrading.com)")
    print(f"     Eval fee (one-time) : ${EVAL_FEE_LIST:,.2f} list / "
          f"${EVAL_FEE_COUPON:,.2f} w/ coupon  [SUNK - already paid]")
    print(f"     Reset fee           : ${RESET_FEE:,.2f} per reset")
    print(f"     Activation fee      : ${ACTIVATION_FEE:,.2f} (FREE)")
    print(f"     RECURRING cost      : ${RECURRING_FEE_PER_MONTH:,.2f}/month "
          f"-- there is NO monthly fee")
    print(f"       => holding the eval open costs NOTHING. Time is not bleeding money.")
    funded_year = per_year * FUNDED_SPLIT_TO_TRADER
    print(f"\n     Once funded, at this same size and frequency:")
    print(f"       gross/year        : ${per_year:+,.0f}")
    print(f"       your 90% share    : ${funded_year:+,.0f} per year")
    print(f"       payout cycles/yr  : {per_year/PAYOUT_TARGET_PER_CYCLE:.1f} "
          f"(at ${PAYOUT_TARGET_PER_CYCLE:,.0f}/cycle)")

    print(f"\n  THE BINDING CONSTRAINT")
    print(f"     Expectancy is ${expectancy:+,.2f} per trade and the mechanism")
    print(f"     fires {trades_per_year:.0f} times a year. That is ${per_year:,.0f}/year of")
    print(f"     raw material. No sizing choice changes it -- raising contracts")
    print(f"     multiplies BOTH the ${expectancy:,.2f} and the ${RISK_PER_CONTRACT:,.0f} risk in")
    print(f"     lockstep, sliding along the 77/52/43/39 curve without ever")
    print(f"     improving the ratio. The only two levers that raise return")
    print(f"     WITHOUT paying for it in pass-probability are:")
    print(f"       (a) more trades per year that are NOT correlated with this one")
    print(f"           (RESULTS.md 2.8 already ruled MNQ out: r = 0.963), or")
    print(f"       (b) a higher expectancy per trade from the SAME risk.")
    print(f"     Everything else is a speed-vs-certainty trade, not an improvement.")
    print()
    print("=" * 78)
    print("  ASSUMPTIONS / NOT MEASURED")
    print("=" * 78)
    print("  - --remaining defaults to $6,083 (recorded 2026-09-10). The live")
    print("    balance moves; re-check dash.lucidtrading.com before deciding.")
    print("  - Section 2 is mean-path arithmetic. It deliberately does NOT model")
    print("    the trailing drawdown, so it is NOT a pass-probability. ruin.py")
    print("    owns that question; this file owns the money question.")
    print("  - Funded-phase figures assume the eval mechanism carries over")
    print("    unchanged. The funded stage has a different DLL (60% of peak EOD)")
    print("    and a 40% consistency rule; neither is modelled here and NO test")
    print("    in this project has ever simulated the funded stage.")
    print("  - Trade frequency is the historical MES ORB-long rate. It assumes")
    print("    the alert is RUNNING; it was paused 2026-09-11 and a paused alert")
    print("    trades zero times a year.")


if __name__ == "__main__":
    main()
