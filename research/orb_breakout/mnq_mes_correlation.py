"""MNQ/MES co-movement check - RESULTS.md section 2.8.

Closes the gap mes_final_run.py prints in its own NOT MEASURED block:
"No test in this project has ever combined MNQ+MES trades into one shared
account equity curve."

Question answered: if the same ORB-long mechanism were run on BOTH instruments
against the one shared $3,000 drawdown budget, would that be diversification
or just the same bet twice?

Deliberately ASSUMPTION-FREE. Uses the identical entry rule on both instruments
(build_mes_trades is instrument-agnostic despite its name) and measures the raw
hold-to-session-close percentage return. Percentage return is used so the two
price levels are comparable, and the raw close exit is used so that NO stop
distance has to be invented for NQ - none has ever been validated there, and
inventing one would make this a guess wearing a lab coat rather than a
measurement.

What this does NOT measure is stated in RESULTS.md 2.8's own caveat block.
"""
import statistics

from mes_final_run import build_mes_trades
from orb_test import load, INSTRUMENTS


def returns_by_date(path):
    """{date: hold-to-close pct return} for every ORB-long day."""
    return {
        t["date"]: (t["close_exit_price"] - t["entry_price"]) / t["entry_price"]
        for t in build_mes_trades(load(path))
    }


def main():
    paths = dict(INSTRUMENTS)
    es = returns_by_date(paths["ES (S&P500, repl.)"])
    nq = returns_by_date(paths["NQ (Nasdaq, primary)"])

    print("=" * 78)
    print("  MNQ / MES CO-MOVEMENT - do two tickers diversify, or double one bet?")
    print("=" * 78)
    print(f"\n  ES ORB-long days : {len(es)}")
    print(f"  NQ ORB-long days : {len(nq)}")

    both = sorted(set(es) & set(nq))
    x = [es[d] for d in both]
    y = [nq[d] for d in both]

    print(f"\n  Days BOTH fired  : {len(both)}")
    print(f"  Days only ES     : {len(set(es) - set(nq))}")
    print(f"  Days only NQ     : {len(set(nq) - set(es))}")
    print(f"  Of ES's {len(es)} signal days, NQ also fired on "
          f"{100 * len(both) / len(es):.1f}%")

    r = statistics.correlation(x, y)
    print(f"\n  Correlation of same-day returns (n={len(both)}): r = {r:.3f}")
    print(f"  Shared variance r^2 = {r * r:.1%}")

    agree = sum(1 for a, b in zip(x, y) if (a >= 0) == (b >= 0))
    both_win = sum(1 for a, b in zip(x, y) if a >= 0 and b >= 0)
    both_lose = sum(1 for a, b in zip(x, y) if a < 0 and b < 0)
    print(f"\n  Same outcome (both win or both lose): "
          f"{agree}/{len(both)} = {100 * agree / len(both):.1f}%")
    print(f"    both winners : {both_win:3d} ({100 * both_win / len(both):4.1f}%)")
    print(f"    both losers  : {both_lose:3d} ({100 * both_lose / len(both):4.1f}%)")
    print(f"    split        : {len(both) - agree:3d} "
          f"({100 * (len(both) - agree) / len(both):4.1f}%)")

    sd_es = statistics.stdev(x)
    sd_nq = statistics.stdev(y)
    sd_blend = statistics.stdev([(a + b) / 2 for a, b in zip(x, y)])
    ideal = sd_es / (2 ** 0.5)
    print("\n  Volatility of an equal-weight blend vs one leg alone:")
    print(f"    ES alone        sd = {sd_es * 100:.3f}%")
    print(f"    NQ alone        sd = {sd_nq * 100:.3f}%")
    print(f"    50/50 blend     sd = {sd_blend * 100:.3f}%")
    print(f"    change vs ES       = {100 * (sd_blend / sd_es - 1):+.1f}%")
    print(f"    if UNcorrelated it would be "
          f"{100 * (ideal / sd_es - 1):+.1f}% - the diversification NOT obtained")

    print("\n  NOT MEASURED / caveats:")
    print("   - This is the raw ENTRY signal's co-movement (hold to session")
    print("     close). It is NOT the deployed mechanism's dollar-P&L")
    print("     correlation - that would need a 99th-pctile MAE stop distance")
    print("     for NQ, which has never been measured or validated.")
    print("   - No combined equity curve was simulated and no combined")
    print("     survivability/ruin number is produced here. This measures")
    print("     whether the two legs are the same bet, not what running both")
    print("     would do to the pass rate.")
    print("   - Equal-weight blend. In contracts, 1 MNQ carries ~1.5x the")
    print("     notional of 1 MES (~$58k vs ~$38k), so a 1-and-1 position")
    print("     would tilt further toward NQ's higher volatility than the")
    print("     blend figure above shows.")
    print("=" * 78)


if __name__ == "__main__":
    main()
