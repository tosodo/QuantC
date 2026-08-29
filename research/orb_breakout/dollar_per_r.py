import pandas as pd, math, os, sys
HERE = "/Users/osodo.t/QuantC/research/orb_breakout"
sys.path.insert(0, HERE)
from orb_test import load, RANGE_START, RANGE_END_EXCL

MULT = {"NQ": 20.0, "ES": 50.0}

for label, sym in [("NQ (Nasdaq, primary)", "NQ"), ("ES (S&P500, repl.)", "ES")]:
    path = os.path.join(HERE, f"data/continuous/{sym}.csv")
    df = load(path)

    out = []
    for date, day in df.groupby("date_et", sort=True):
        rng = day[(day["time_et"] >= RANGE_START) & (day["time_et"] < RANGE_END_EXCL)]
        if len(rng) < 15:
            continue
        range_high = rng["high"].max(); range_low = rng["low"].min()
        scan = day[day["time_et"] >= RANGE_END_EXCL]
        if scan.empty:
            continue
        long_hit = scan[scan["close"] > range_high]
        if long_hit.empty:
            continue
        short_hit = scan[scan["close"] < range_low]
        first_long_ts = long_hit["ts_event"].min()
        first_short_ts = short_hit["ts_event"].min() if not short_hit.empty else None
        if first_short_ts is not None and first_short_ts < first_long_ts:
            continue
        sig_ts = first_long_ts
        entry_price = float(day.loc[day["ts_event"] == sig_ts, "close"].iloc[0])
        exit_row = day.iloc[-1]
        window = day[(day["ts_event"] >= sig_ts) & (day["ts_event"] <= exit_row["ts_event"])]
        closes = window["close"].to_numpy()
        if len(closes) < 3:
            continue
        log_closes = [math.log(c) for c in closes]
        rets = [log_closes[i+1]-log_closes[i] for i in range(len(log_closes)-1)]
        m = sum(rets)/len(rets)
        var = sum((x-m)**2 for x in rets)/(len(rets)-1)
        sd = math.sqrt(var)
        horizon_vol = sd*math.sqrt(len(rets))
        if horizon_vol <= 0:
            continue
        dollar_per_1R_1contract = horizon_vol * entry_price * MULT[sym]
        out.append(dollar_per_1R_1contract)

    out_sorted = sorted(out)
    n = len(out_sorted)
    def pct(p):
        return out_sorted[min(int(p*(n-1)), n-1)]
    mean = sum(out)/n
    print(f"{label}: n={n}  $/1R/contract  mean=${mean:,.0f}  median=${pct(0.5):,.0f}  "
          f"p10=${pct(0.10):,.0f}  p90=${pct(0.90):,.0f}")
