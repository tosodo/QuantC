#!/usr/bin/env python3
"""
orb_vwap_correlation.py - is the VWAP-fade draft a genuinely DIFFERENT bet
from the live ORB strategy, or the same bet wearing a different hat?

This is the identical question RESULTS.md section 2.8 asked about MNQ-vs-MES,
run with the identical method, against the only candidate that could raise
this account's return WITHOUT costing pass-probability (RESULTS.md 2.10's
"lever (a)"). MNQ failed that test at r = 0.963. This measures the fade.

WHAT IS AND IS NOT BEING CLAIMED
--------------------------------
The VWAP-fade rule is ported VERBATIM from vwap_fade_ghost_DRAFT.pine - every
parameter (RSI 14 @ 30/70, 2 SD entry, 3 SD stop, 5-bar volume average, 30-bar
warm-up, 3 trades/day, 15-min entry cutoff) is that file's, not this script's.
That Pine file states plainly in its own header that those numbers are
"a reasonable industry-standard starting point, NOT a measured result."

So: the CORRELATION result below is a real measurement and answers the
question asked. Any PROFITABILITY figure printed alongside it is an
unregistered, in-sample, first-look number on parameters chosen by eye. It is
NOT a validated edge and must not be treated as one - that is precisely the
trap this project's pre-registration discipline exists to prevent. It is
printed only because correlation is uninterpretable without knowing whether
the second series is even worth owning.

ORB side uses the LIVE deployed mechanism (125pt stop, 90-min underwater time
exit, 1 tick slippage, real costs) - not the retired no-stop version.
Both series are priced on MES ($5/pt) with the same cost and slippage model,
so the two are directly comparable in dollars.

Usage
    ../orb_breakout/venv/bin/python orb_vwap_correlation.py
"""

import math
import os
import statistics
import sys

import pandas as pd
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ORB_DIR = os.path.join(os.path.dirname(HERE), "orb_breakout")
MEAN_REV_DIR = os.path.join(os.path.dirname(HERE), "index_mean_reversion")
sys.path.insert(0, ORB_DIR)
sys.path.insert(0, MEAN_REV_DIR)

import screen_mean_reversion as smr
from orb_test import INSTRUMENTS, RANGE_START, SESSION_CLOSE
from mes_final_run import build_mes_trades, resolve_exit, PV_MES, TIME_EXIT_MINUTES

ET = ZoneInfo("America/New_York")
ES_LABEL = "ES (S&P500, repl.)"
ES_PATH = dict(INSTRUMENTS)[ES_LABEL]

# --- ORB live parameters (from orb_long_ghost_DRAFT_mes_v2_accessible.pine) ---
ORB_STOP_POINTS = 625.0 / PV_MES        # 125 pts
ES_TICK = 0.25
SLIPPAGE = 1 * ES_TICK

# --- VWAP-fade parameters: VERBATIM from vwap_fade_ghost_DRAFT.pine ---
RSI_LENGTH = 14
OVERSOLD = 30
OVERBOUGHT = 70
ENTRY_BAND_MULT = 2.0
STOP_BAND_MULT = 3.0
VOL_AVG_LENGTH = 5
WARMUP_BARS = 30
MAX_TRADES_PER_DAY = 3
ENTRY_CUTOFF_MINS = 15
ENABLE_SHORT = True


def load_with_volume(path):
    """Same as orb_test.load() but keeps the volume column (VWAP needs it)."""
    df = pd.read_csv(path, usecols=["ts_event", "open", "high", "low", "close", "volume"])
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = df["ts_event"].dt.tz_convert(ET)
    df["date_et"] = ts_et.dt.date
    df["time_et"] = ts_et.dt.strftime("%H:%M")
    df["mins_to_close"] = (16 * 60) - (ts_et.dt.hour * 60 + ts_et.dt.minute)
    df = df[(df["time_et"] >= RANGE_START) & (df["time_et"] < SESSION_CLOSE)]
    return df.sort_values("ts_event").reset_index(drop=True)


def rsi_wilder(close, length):
    """Pine ta.rsi = Wilder's RMA smoothing (alpha = 1/length)."""
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    rma_up = up.ewm(alpha=1.0 / length, adjust=False).mean()
    rma_dn = down.ewm(alpha=1.0 / length, adjust=False).mean()
    rs = rma_up / rma_dn.replace(0.0, float("nan"))
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(100.0).where(rma_dn != 0, 100.0)


def build_vwap_fade_trades(df, half_cost):
    """Faithful port of vwap_fade_ghost_DRAFT.pine's signal + exit logic.

    Session-anchored VWAP with running price/price^2/volume sums, exactly as
    the Pine computes its bands (not a simple moving stdev).
    """
    df = df.copy()
    df["rsi"] = rsi_wilder(df["close"], RSI_LENGTH)
    df["vol_avg"] = df["volume"].rolling(VOL_AVG_LENGTH).mean()

    trades = []
    for date, day in df.groupby("date_et", sort=True):
        day = day.reset_index(drop=True)
        cum_pv = cum_pv2 = cum_vol = 0.0
        trades_today = 0
        in_pos = False
        side = None
        entry_px = stop_px = None
        entry_idx = None

        for i, b in day.iterrows():
            tp = (b["high"] + b["low"] + b["close"]) / 3.0      # hlc3
            cum_pv += tp * b["volume"]
            cum_pv2 += tp * tp * b["volume"]
            cum_vol += b["volume"]
            bars_in_session = i + 1

            if cum_vol <= 0:
                continue
            vwap = cum_pv / cum_vol
            variance = max(cum_pv2 / cum_vol - vwap * vwap, 0.0)
            sd = math.sqrt(variance)
            have_bands = bars_in_session >= WARMUP_BARS and sd > 0
            is_last_bar = (i == len(day) - 1)

            # ---------- manage an open position first ----------
            if in_pos:
                exit_px = exit_reason = None
                if side == "long":
                    if b["low"] <= stop_px:
                        exit_px, exit_reason = stop_px - SLIPPAGE, "stop"
                    elif b["close"] >= vwap:
                        exit_px, exit_reason = b["close"] - SLIPPAGE, "vwap_revert"
                    elif is_last_bar:
                        exit_px, exit_reason = b["close"] - SLIPPAGE, "session_close"
                else:
                    if b["high"] >= stop_px:
                        exit_px, exit_reason = stop_px + SLIPPAGE, "stop"
                    elif b["close"] <= vwap:
                        exit_px, exit_reason = b["close"] + SLIPPAGE, "vwap_revert"
                    elif is_last_bar:
                        exit_px, exit_reason = b["close"] + SLIPPAGE, "session_close"

                if exit_px is not None:
                    if side == "long":
                        pnl = ((exit_px - half_cost) - (entry_px + half_cost)) * PV_MES
                    else:
                        pnl = ((entry_px - half_cost) - (exit_px + half_cost)) * PV_MES
                    trades.append({"date": str(date), "side": side, "pnl": pnl,
                                   "reason": exit_reason})
                    in_pos = False
                    side = entry_px = stop_px = entry_idx = None
                continue     # Pine cannot enter on the same bar it exits

            # ---------- look for a new entry ----------
            within_cutoff = b["mins_to_close"] <= ENTRY_CUTOFF_MINS
            can_enter = (have_bands and trades_today < MAX_TRADES_PER_DAY
                         and not within_cutoff and not pd.isna(b["vol_avg"]))
            if not can_enter:
                continue
            vol_exhaustion = b["volume"] < b["vol_avg"]
            if not vol_exhaustion:
                continue

            lower_entry = vwap - ENTRY_BAND_MULT * sd
            upper_entry = vwap + ENTRY_BAND_MULT * sd

            if b["close"] < lower_entry and b["rsi"] < OVERSOLD:
                in_pos, side = True, "long"
                entry_px = b["close"]
                stop_px = vwap - STOP_BAND_MULT * sd
                trades_today += 1
                entry_idx = i
            elif (ENABLE_SHORT and b["close"] > upper_entry
                  and b["rsi"] > OVERBOUGHT):
                in_pos, side = True, "short"
                entry_px = b["close"]
                stop_px = vwap + STOP_BAND_MULT * sd
                trades_today += 1
                entry_idx = i

        # a position still open at the end of a day's bars is force-closed above
        # by is_last_bar; nothing can leak into the next session.
    return trades


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    return num / (dx * dy) if dx and dy else float("nan")


def main():
    half_cost = smr.REAL_COST_POINTS[ES_LABEL]["free"] / 2.0
    df = load_with_volume(ES_PATH)

    # --- ORB daily P&L, LIVE mechanism ---
    orb_trades = build_mes_trades(df)
    orb_daily = {}
    for t in orb_trades:
        exit_px, _ = resolve_exit(t, half_cost, stop_points=ORB_STOP_POINTS,
                                  time_exit_minutes=TIME_EXIT_MINUTES,
                                  slippage_points=SLIPPAGE)
        pnl = ((exit_px - half_cost) - (t["entry_price"] + half_cost)) * PV_MES
        orb_daily[t["date"]] = orb_daily.get(t["date"], 0.0) + pnl

    # --- VWAP-fade daily P&L ---
    fade_trades = build_vwap_fade_trades(df, half_cost)
    fade_daily = {}
    for t in fade_trades:
        fade_daily[t["date"]] = fade_daily.get(t["date"], 0.0) + t["pnl"]

    all_days = sorted({str(d) for d in df["date_et"].unique()})
    n_sessions = len(all_days)
    years = n_sessions / 252.0

    print("=" * 78)
    print("  ORB vs VWAP-FADE - diversification, or the same bet again?")
    print("=" * 78)
    print(f"\n  Sessions in dataset : {n_sessions} ({years:.1f} years)")
    print(f"  ORB trading days    : {len(orb_daily)}")
    print(f"  Fade trading days   : {len(fade_daily)}  "
          f"({len(fade_trades)} trades, up to {MAX_TRADES_PER_DAY}/day)")

    both = sorted(set(orb_daily) & set(fade_daily))
    orb_only = sorted(set(orb_daily) - set(fade_daily))
    fade_only = sorted(set(fade_daily) - set(orb_daily))
    print(f"\n  Days BOTH fired     : {len(both)}")
    print(f"  ORB-only days       : {len(orb_only)}")
    print(f"  Fade-only days      : {len(fade_only)}  "
          f"<- additional trading days ORB never sees")

    print("\n" + "-" * 78)
    print("  1. THE CORRELATION TEST (the question actually asked)")
    print("-" * 78)
    if len(both) < 20:
        print(f"  Only {len(both)} overlapping days - too few to correlate. STOP.")
    else:
        x = [orb_daily[d] for d in both]
        y = [fade_daily[d] for d in both]
        r = pearson(x, y)
        both_same = sum(1 for a, b in zip(x, y) if (a > 0) == (b > 0))
        print(f"  Correlation of same-day $ P&L (n={len(both)}) : r = {r:+.3f}")
        print(f"  Shared variance                              : {r*r*100:.1f}%")
        print(f"  Both won or both lost                        : "
              f"{both_same/len(both)*100:.1f}%")
        print(f"  One won, one lost                            : "
              f"{(len(both)-both_same)/len(both)*100:.1f}%")
        print(f"\n  For reference, RESULTS.md 2.8 measured MNQ vs MES at r = +0.963")
        print(f"  and ruled it out as 'the same bet twice'.")

    print("\n" + "-" * 78)
    print("  2. PORTFOLIO EFFECT (daily $ volatility, all sessions)")
    print("-" * 78)
    orb_series = [orb_daily.get(d, 0.0) for d in all_days]
    fade_series = [fade_daily.get(d, 0.0) for d in all_days]
    comb_series = [a + b for a, b in zip(orb_series, fade_series)]
    sd_orb = statistics.pstdev(orb_series)
    sd_fade = statistics.pstdev(fade_series)
    sd_comb = statistics.pstdev(comb_series)
    print(f"  ORB alone      : sd ${sd_orb:,.2f}/day   "
          f"mean ${statistics.mean(orb_series):+,.2f}/day")
    print(f"  Fade alone     : sd ${sd_fade:,.2f}/day   "
          f"mean ${statistics.mean(fade_series):+,.2f}/day")
    print(f"  ORB + Fade     : sd ${sd_comb:,.2f}/day   "
          f"mean ${statistics.mean(comb_series):+,.2f}/day")
    naive = math.sqrt(sd_orb ** 2 + sd_fade ** 2)
    print(f"\n  Combined sd if perfectly uncorrelated would be ${naive:,.2f}")
    print(f"  Actual combined sd                              ${sd_comb:,.2f}")
    print(f"  vs ORB alone: {(sd_comb/sd_orb-1)*100:+.1f}% volatility, "
          f"{(statistics.mean(comb_series)/statistics.mean(orb_series)-1)*100:+.1f}% return")

    print("\n" + "-" * 78)
    print("  3. THE FADE'S OWN NUMBERS - *** IN-SAMPLE, UNREGISTERED ***")
    print("-" * 78)
    print("  NOT a validated edge. Parameters were chosen by eye in the Pine")
    print("  draft and this is their first look at the data. Shown only so the")
    print("  correlation above is interpretable.")
    if fade_trades:
        pnls = [t["pnl"] for t in fade_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        exp = sum(pnls) / len(pnls)
        print(f"\n  Trades              : {len(pnls)} ({len(pnls)/years:.0f}/year)")
        print(f"  Win rate            : {len(wins)/len(pnls)*100:.1f}%")
        if wins and losses:
            aw, al = sum(wins)/len(wins), sum(losses)/len(losses)
            rr = abs(aw/al)
            print(f"  Average winner      : ${aw:+,.2f}")
            print(f"  Average loser       : ${al:+,.2f}")
            print(f"  Reward:risk         : {rr:.2f} : 1")
            print(f"  Break-even win rate : {100/(1+rr):.1f}%")
        print(f"  EXPECTANCY / trade  : ${exp:+,.2f}")
        print(f"  Total over {years:.1f}yr   : ${sum(pnls):+,.0f}  "
              f"(${sum(pnls)/years:+,.0f}/year)")
        longs = [t for t in fade_trades if t["side"] == "long"]
        shorts = [t for t in fade_trades if t["side"] == "short"]
        for label, grp in (("long", longs), ("short", shorts)):
            if grp:
                g = [t["pnl"] for t in grp]
                print(f"    {label:5s}: n={len(g):4d}  "
                      f"WR={sum(1 for p in g if p>0)/len(g)*100:4.1f}%  "
                      f"exp=${sum(g)/len(g):+7.2f}")
        reasons = {}
        for t in fade_trades:
            reasons[t["reason"]] = reasons.get(t["reason"], 0) + 1
        print(f"  Exit mix            : " +
              ", ".join(f"{k}={v}" for k, v in sorted(reasons.items())))

    print("\n" + "=" * 78)
    print("  ASSUMPTIONS / NOT MEASURED")
    print("=" * 78)
    print("  - Fade parameters are vwap_fade_ghost_DRAFT.pine's own, unchanged.")
    print("    No parameter was tuned here and no out-of-sample split was used,")
    print("    so section 3 is in-sample by construction and is NOT evidence the")
    print("    fade has an edge. A real verdict needs the same pre-registered")
    print("    in/out-of-sample treatment ORB got in section 1 of RESULTS.md.")
    print("  - RSI and the 5-bar volume average are computed on the RTH-only")
    print("    series (09:30-16:00 ET), matching an RTH TradingView chart. An")
    print("    ETH chart would seed both differently and shift marginal signals.")
    print("  - Stops are assumed to fill at the stop price plus 1 tick adverse.")
    print("    A gap through the stop would fill worse; not modelled.")
    print("  - No survivability/ruin simulation is run here. This measures")
    print("    whether the two are the same bet, NOT what running both would do")
    print("    to the pass rate - same boundary RESULTS.md 2.8 drew.")


if __name__ == "__main__":
    main()
