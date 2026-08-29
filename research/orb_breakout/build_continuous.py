#!/usr/bin/env python3
"""
build_continuous.py - turn the raw Databento GLBX.MDP3 pull (every individual
NQ and ES futures contract, 1-minute bars, 2021-08-19 to 2026-08-18) into one
continuous front-month minute series per instrument.

Why this exists
    The Databento request pulled EVERY contract month under the NQ and ES
    parent symbols (189 symbols total, including calendar-spread quotes like
    "ESH2-ESM2"), not a single ready-to-use series. This script picks, for
    each calendar day, whichever single contract traded the most volume that
    day, and stitches those bars together into one continuous series. This is
    the standard "volume roll" method for building a continuous futures
    series - an objective, mechanical rule, not a strategy design choice.

What this is NOT
    Back-adjusted. Like the existing Yahoo daily series in
    research/index_mean_reversion/, roll-date jumps sit in the series as
    ordinary price gaps. Same disclosed limitation, same reasoning: it
    inflates the size of returns that happen to fall on a roll day, it does
    not select for direction.

Day-bucketing caveat (disclosed, not hidden)
    Volume is bucketed by UTC calendar date for the purpose of picking the
    day's front contract. CME Globex's actual trading "day" runs roughly
    5pm-4pm CT and crosses midnight UTC, so a handful of minutes right at the
    UTC day boundary could in principle be attributed to the "wrong" day's
    volume count. This does not change which contract wins a given day
    (front-month volume dominance is not decided by a few boundary minutes),
    so it does not change the resulting continuous series, but it is a real
    simplification worth naming.

Output
    data/continuous/NQ.csv, data/continuous/ES.csv
    columns: ts_event (UTC),open,high,low,close,volume,symbol
    (symbol column kept so roll dates are visible/auditable, not hidden)
"""

import os
import databento as db
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "data/continuous")

# label -> (raw dbn.zst file, symbol-root prefix to filter on)
# NQ and ES came from one combined Databento pull; YM was a separate,
# later pull (needed to reach the propfirm-research-auditor skill's
# minimum-3-instrument replication standard), so it has its own raw file.
JOBS = {
    "NQ": (os.path.join(HERE, "data/raw/glbx-mdp3-20210819-20260818.ohlcv-1m.dbn.zst"), "NQ"),
    "ES": (os.path.join(HERE, "data/raw/glbx-mdp3-20210819-20260818.ohlcv-1m.dbn.zst"), "ES"),
    "YM": (os.path.join(HERE, "data/raw_ym/glbx-mdp3-20210819-20260818.ohlcv-1m.dbn.zst"), "YM"),
}


def build_one(label, raw_file, root):
    print(f"\nLoading {label} DBN file ({raw_file}) ...")
    store = db.DBNStore.from_file(raw_file)
    df = store.to_df()
    df = df.reset_index()
    print(f"  {len(df):,} raw rows, {df['symbol'].nunique()} symbols")

    # Drop calendar-spread quotes (symbol contains '-', e.g. "ESH2-ESM2").
    # Those are spread prices, not a single tradeable contract's bars.
    df = df[~df["symbol"].str.contains("-")]
    print(f"  {len(df):,} rows after dropping calendar-spread symbols")

    df["date"] = df["ts_event"].dt.date

    sub = df[df["symbol"].str.startswith(root)].copy()
    print(f"{label}: {len(sub):,} rows, {sub['symbol'].nunique()} contracts")

    # Volume-roll: for each UTC calendar date, the front contract is
    # whichever symbol traded the most total volume that day.
    daily_vol = sub.groupby(["date", "symbol"])["volume"].sum().reset_index()
    front = daily_vol.loc[daily_vol.groupby("date")["volume"].idxmax()]
    front_map = dict(zip(front["date"], front["symbol"]))

    sub["front_symbol"] = sub["date"].map(front_map)
    cont = sub[sub["symbol"] == sub["front_symbol"]].sort_values("ts_event")

    roll_dates = front.sort_values("date")
    roll_changes = (roll_dates["symbol"] != roll_dates["symbol"].shift()).sum()
    print(f"  continuous series: {len(cont):,} minute bars, "
          f"{roll_dates['date'].min()} -> {roll_dates['date'].max()}, "
          f"{roll_changes} roll segments")

    out_path = os.path.join(OUT_DIR, f"{label}.csv")
    cont[["ts_event", "open", "high", "low", "close", "volume", "symbol"]].to_csv(
        out_path, index=False
    )
    print(f"  -> {out_path}")


def main():
    import sys
    wanted = sys.argv[1:] or list(JOBS.keys())
    for label in wanted:
        raw_file, root = JOBS[label]
        build_one(label, raw_file, root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
