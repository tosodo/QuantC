"""Bar-by-bar replay of the Pine paper-test state machine (variants A and B)
compared with the original research builders. Read-only."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, "/Users/osodo.t/QuantC/research/orb_breakout")
import orb_test as o, stoploss_test as st
import pandas as pd

SKIP = {"2026-11-27", "2026-12-24"}

def replay(df, use_stop):
    trades = []; no_exit_days = []
    for date, day in df.groupby("date_et", sort=True):
        d = str(date)
        if d in SKIP: continue
        rangeHigh = rangeLow = None; rangeBars = 0
        traded = blocked = inPos = False
        entryPx = entryIdx = None
        rows = list(day.itertuples(index=False))
        for i, b in enumerate(rows):
            t = b.time_et
            rangeWin = "09:30" <= t < "09:45"
            inSession = "09:45" <= t < "16:00"
            lastBar = "15:59" <= t < "16:00"
            if rangeWin:
                if rangeBars == 0 or t == "09:30":
                    if t == "09:30":
                        rangeHigh, rangeLow, rangeBars = b.high, b.low, 1
                        traded = blocked = False
                    else:
                        rangeHigh = max(rangeHigh or b.high, b.high); rangeLow = min(rangeLow or b.low, b.low); rangeBars += 1
                else:
                    rangeHigh = max(rangeHigh, b.high); rangeLow = min(rangeLow, b.low); rangeBars += 1
            complete = rangeBars >= 15
            exitPx = None; reason = None
            if inPos and i > entryIdx:
                if use_stop and b.low <= rangeLow:
                    exitPx, reason = rangeLow, "stop"
                elif lastBar:
                    exitPx, reason = b.close, "close"
                if exitPx is not None:
                    trades.append(dict(date=d, entry=entryPx, exit=exitPx, reason=reason, r=rangeHigh-rangeLow))
                    inPos = False
            if (not inPos) and (not traded) and (not blocked) and inSession and complete and exitPx is None and not lastBar:
                if b.close < rangeLow: blocked = True
                elif b.close > rangeHigh:
                    inPos = traded = True; entryPx = b.close; entryIdx = i
        if inPos:
            no_exit_days.append(d)   # Pine would only flatten when an evening bar arrived
    return pd.DataFrame(trades), no_exit_days

for label, path in o.INSTRUMENTS[:2]:
    df = o.load(path)
    ref, _ = st.build_stop_trades(df)
    ref = pd.DataFrame(ref).set_index("date")
    print("\n=====", label, "| reference long trades:", len(ref), "| stopped (ref):", int(ref.stopped.sum()))
    for name, use_stop, col in (("A hold-to-close", False, "R0_close"), ("B range stop", True, "R0_stop")):
        rp, noexit = replay(df, use_stop)
        rp = rp.set_index("date"); rp["R"] = (rp.exit - rp.entry) / rp.r
        both = rp.index.intersection(ref.index)
        only_pine = rp.index.difference(ref.index); only_ref = ref.index.difference(rp.index)
        diff = (rp.loc[both, "R"] - ref.loc[both, col]).abs()
        print(f"  {name}: replay trades={len(rp)} | common={len(both)} | only replay={len(only_pine)} | only reference={len(only_ref)} | days left open (no 15:59 bar)={len(noexit)}")
        print(f"     R match on common days: max abs diff={diff.max():.6f}, days differing >1e-6: {(diff>1e-6).sum()}")
        if use_stop: print(f"     stopped replay={int((rp.reason=='stop').sum())} vs ref={int(ref.stopped.sum())}")
        if len(only_pine): print("     only-replay dates:", list(only_pine)[:8])
        if len(only_ref): print("     only-ref dates:", list(only_ref)[:8])
        if (diff>1e-6).sum(): print("     differing dates:", list(diff[diff>1e-6].index)[:8])

print("\n--- the days the research counted but Pine would leave open (NQ, variant A) ---")
df = o.load(o.INSTRUMENTS[0][1])
rp, noexit = replay(df, False)
import datetime
for d in noexit:
    day = df[df.date_et.astype(str)==d]
    print(d, datetime.date.fromisoformat(d).strftime("%a"), "last bar", day.time_et.max(), "bars", len(day))
