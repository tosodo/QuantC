#!/usr/bin/env python3
"""
fetch_data.py - download the raw Databento file that build_continuous.py
reads: every ES and NQ futures contract, 1-minute OHLCV, GLBX.MDP3,
2021-08-19 to 2026-08-18 (the window all the ORB research used).

It prints Databento's cost estimate and downloads nothing unless you pass
--yes. The API key is read from the DATABENTO_API_KEY environment variable;
never put it in a file in this repo or paste it into a chat.

    export DATABENTO_API_KEY=...        # in your own terminal
    python3 fetch_data.py               # shows size and cost only
    python3 fetch_data.py --yes         # downloads to data/raw/
    python3 build_continuous.py ES NQ   # -> data/continuous/ES.csv, NQ.csv
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data/raw/glbx-mdp3-20210819-20260818.ohlcv-1m.dbn.zst")
REQ = dict(dataset="GLBX.MDP3", schema="ohlcv-1m", symbols=["ES.FUT", "NQ.FUT"],
           stype_in="parent", start="2021-08-19", end="2026-08-19")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="download after showing the cost")
    a = ap.parse_args()
    if not os.environ.get("DATABENTO_API_KEY"):
        print("Set DATABENTO_API_KEY in this terminal first.", file=sys.stderr)
        return 1
    import databento as db
    client = db.Historical()
    size = client.metadata.get_billable_size(**REQ)
    cost = client.metadata.get_cost(**REQ)
    print(f"Request: {REQ['symbols']} {REQ['schema']} {REQ['start']} to {REQ['end']}")
    print(f"Billable size: {size / 1e6:,.1f} MB   Cost: ${cost:,.2f}")
    if not a.yes:
        print("Nothing downloaded. Re-run with --yes to buy and download.")
        return 0
    if os.path.exists(OUT):
        print(f"{OUT} already exists; move it away first.", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    client.timeseries.get_range(path=OUT, **REQ)
    print(f"Saved {OUT} ({os.path.getsize(OUT) / 1e6:,.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
