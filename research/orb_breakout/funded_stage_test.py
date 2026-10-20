#!/usr/bin/env python3
"""
funded_stage_test.py - what a funded account pays the live ORB, per firm rule set.

firm_fit_test.py stops at the evaluation pass. This takes the same trade list and
walks it through a funded (sim-funded) account: drawdown floor, payout rules,
profit split. It then joins the evaluation cost per funded account (firm_fit_test's
cost model) to the payouts, so the answer is a net dollar figure per funded account.

Run from this folder (needs data/continuous/ES.csv, built by build_continuous.py):

    python3 funded_stage_test.py --size 2 > funded_stage_2mes.md
    python3 funded_stage_test.py --data PATH --sims 3000 --size 1

Rule numbers come from FIRM_RULES_SURVEY.md (search snippets, not verified on the
firms' pages). Fields tagged GUESS are stand-ins; edit FUNDED_RULES as pages are
checked. Not modelled: scaling plans, daily loss limits in funded, the Topstep
consistency path, the live-capital stage, re-purchase after a breach, tax.
"""
import argparse
import os
import random
import sys
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import firm_fit_test as ff  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402

# ---------- FUNDED RULE SETS ----------
#   start, dd, lock     drawdown as in firm_fit_test (EOD trailing, floor capped at start + lock)
#   reset_floor         True: after a payout the floor is fixed at the start balance
#   qual_pnl, qual_days a payout needs qual_days days since the last payout with pnl >= qual_pnl
#   min_cycle_days      days since the last payout before one is allowed
#   min_cycle_profit    profit since the last payout needed to request
#   consistency         best day since the last payout <= this share of that profit (None = off)
#   reserve             balance must stay at start + reserve after a payout
#   frac, cap, min_req  request = min(cap, frac * (balance - start - reserve)), at least min_req
#   split               trader's share of a payout
#   activation_fee      one-off cost when the funded account starts
FUNDED_RULES = {
    # XFA 50K: MLL 2,000 EOD, locks at the start balance; MLL resets to 0 after each
    # payout; 5 winning days of $150+; min request $125; 90/10: all OFF.
    # cap 2,000 is UNCERTAIN (help page shows 2,000 to 5,000); frac 0.5 is a GUESS.
    "Topstep XFA 50K (standard path)": dict(
        eval="Topstep 50K Combine (standard)", start=50000.0, dd=2000.0, lock=0.0,
        reset_floor=True, qual_pnl=150.0, qual_days=5, min_cycle_days=0, min_cycle_profit=0.0,
        consistency=None, reserve=0.0, frac=0.5, cap=2000.0, min_req=125.0, split=0.90,
        activation_fee=0.0),   # the $149 is already in the Combine rule set's activation_fee
    # LucidPro 100K funded: MLL 3,000 EOD, locks at start + 100; consistency 40% of cycle
    # profit; min cycle profit 750; min request 500; buffer = MLL + 100; 90/10: all OFF.
    # 3 cycle days is 3P; cap per payout is unknown, taken as none (kind to the trader).
    "Lucid 100K funded": dict(
        eval="Lucid 100K LucidPro (price GUESS)", start=100000.0, dd=3000.0, lock=100.0,
        reset_floor=False, qual_pnl=-1e9, qual_days=0, min_cycle_days=3, min_cycle_profit=750.0,
        consistency=0.40, reserve=3100.0, frac=1.0, cap=None, min_req=500.0, split=0.90,
        activation_fee=0.0),
}


# ---------- the funded engine ----------

def funded_run(seq, fr, horizon=None):
    """seq: (pnl, mae_usd, gap) per trade. Returns dict(payouts=[(trade_no, trader_$)],
    breach=trade_no or None, n=trades walked, trader_total=$). The account ends at the first
    breach (floor touched on a trade's worst point)."""
    start, bal, hwm = fr["start"], fr["start"], fr["start"]
    floor_cap = start + fr["lock"]
    reset = False
    cyc_days = cyc_q = 0
    cyc_profit = cyc_best = 0.0
    pays, total = [], 0.0
    n = len(seq) if horizon is None else min(horizon, len(seq))
    for i in range(1, n + 1):
        pnl, mae, _ = seq[i - 1]
        floor = start if reset else min(max(start - fr["dd"], hwm - fr["dd"]), floor_cap)
        if bal - mae <= floor or bal + pnl <= floor:
            return dict(payouts=pays, breach=i, n=i, trader_total=total)
        bal += pnl
        hwm = max(hwm, bal)
        cyc_days += 1
        cyc_profit += pnl
        cyc_best = max(cyc_best, pnl)
        cyc_q += pnl >= fr["qual_pnl"]
        avail = bal - start - fr["reserve"]
        if (cyc_days >= fr["min_cycle_days"] and cyc_q >= fr["qual_days"]
                and cyc_profit >= fr["min_cycle_profit"] and avail > 0
                and (fr["consistency"] is None or cyc_best <= fr["consistency"] * cyc_profit)):
            req = fr["frac"] * avail
            if fr["cap"] is not None:
                req = min(req, fr["cap"])
            if req >= fr["min_req"]:
                bal -= req
                total += fr["split"] * req
                pays.append((i, fr["split"] * req))
                reset = reset or fr["reset_floor"]
                cyc_days = cyc_q = 0
                cyc_profit = cyc_best = 0.0
    return dict(payouts=pays, breach=None, n=n, trader_total=total)


def paid_by(run, h):
    return sum(a for t, a in run["payouts"] if t <= h)


def first_by(run, h):
    return next((t for t, _ in run["payouts"] if t <= h), None)


def breached_by(run, h):
    return run["breach"] is not None and run["breach"] <= h


# ---------- sampling ----------

def boot_paths(seq, sims, horizon, seed=7):
    rng = random.Random(seed)
    return [ff.block_path(seq, rng, horizon) for _ in range(sims)]


def rolling_paths(seq, horizon):
    """Real-order starts with the full horizon still in the data."""
    return [seq[i:i + horizon] for i in range(0, len(seq) - horizon + 1)]


def summarise_funded(runs, horizons):
    n = len(runs)
    out = dict(n=n)
    for h in horizons:
        firsts = [first_by(r, h) for r in runs]
        got = [t for t in firsts if t is not None]
        out[h] = dict(
            p_first=100 * len(got) / n,
            p_breach=100 * sum(breached_by(r, h) for r in runs) / n,
            med_first=median(got) if got else None,
            mean_paid=sum(paid_by(r, h) for r in runs) / n,
            mean_n_pay=sum(sum(1 for t, _ in r["payouts"] if t <= h) for r in runs) / n)
    return out


# ---------- report ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--cost", type=float, default=lrb.BASE_COST)
    ap.add_argument("--slip", type=int, default=lrb.BASE_SLIP)
    ap.add_argument("--size", type=int, default=2, help="MES contracts per trade")
    ap.add_argument("--trades-per-year", type=float, default=ff.TRADES_PER_YEAR)
    a = ap.parse_args()
    tpy = a.trades_per_year
    horizons = [int(tpy / 2), int(tpy), int(2 * tpy), int(5 * tpy)]

    trades, sessions = lrb.build_trades(lrb.load_days(a.data))
    trades.sort(key=lambda t: t["date"])
    seq = ff.make_seq(trades, a.cost, a.slip, a.size)
    P = print
    P("# Funded stage: what a funded account pays the live ORB\n")
    P(f"Data: {sessions[0]} to {sessions[-1]}, {len(trades)} trades. Cost ${a.cost:.2f}/RT + "
      f"{a.slip} tick, {a.size} MES. {tpy:.0f} trades a year, so horizons "
      f"{', '.join(f'{h} trades' for h in horizons)} are about 0.5, 1, 2 and 5 years of funded trading.\n")
    P("Payouts are to the trader after the profit split. Rule numbers: FIRM_RULES_SURVEY.md "
      "(snippets, unverified); see FUNDED_RULES for the GUESS fields.\n")

    paths = boot_paths(seq, a.sims, horizons[-1])
    rh = min(horizons[-1], len(seq) // 2)          # real history is short: cap the rolling horizon
    rolling = rolling_paths(seq, rh)
    rhs = [h for h in horizons if h <= rh]
    for name, fr in FUNDED_RULES.items():
        # evaluation stage for the same firm, same size, to get cost per funded account
        er = ff.RULE_SETS[fr["eval"]]
        ev = ff.summarise(ff.bootstrap_runs(seq, {fr["eval"]: er}, a.sims)[fr["eval"]])
        p, b = ff.rates_for_cost(ev, False)
        cm = ff.cost_model(p, b, er, ev["mean_trades"], tpy=tpy)
        bs = summarise_funded([funded_run(x, fr) for x in paths], horizons)
        rs = summarise_funded([funded_run(x, fr) for x in rolling], rhs)

        P(f"\n## {name}\n")
        P(f"Evaluation first: P(pass within {ff.MAX_ATTEMPTS} tries) {100 * cm['p_any']:.0f}%, "
          f"cost per funded account ${ff.f(cm['cost'])}, about {ff.f(cm['years'], 1)} years of trading to get there "
          f"(bootstrap, same size).\n")
        for label, s, hs in (("Bootstrap", bs, horizons), (f"Real-order starts (history allows {rh} trades)", rs, rhs)):
            P(f"**{label}** ({s['n']} funded accounts)\n")
            P("| trades funded | P(first payout) % | P(breached) % | median trades to first | "
              "mean payouts made | mean paid to trader $ | mean paid minus cost per funded $ |")
            P("|---|---|---|---|---|---|---|")
            for h in hs:
                x = s[h]
                net = None if cm["cost"] is None else x["mean_paid"] - cm["cost"]
                P(f"| {h} | {x['p_first']:.1f} | {x['p_breach']:.1f} | {ff.f(x['med_first'])} | "
                  f"{x['mean_n_pay']:.2f} | {ff.f(x['mean_paid'])} | {ff.f(net)} |")
            P("")

    P("\n## How to read this\n")
    P("- 'mean paid' averages over every funded account including the ones that never paid. "
      "'minus cost per funded' subtracts the evaluation cost per funded account from firm_fit_test's "
      "cost model, so a negative number means the account has not yet earned back what it cost.")
    P("- The account ends at its first breach; buying a new one is not modelled, so nothing here "
      "counts a second funded account.")
    P("- Real-order starts overlap heavily and are few at this horizon; read them as a check on "
      "the bootstrap, not as independent samples.")
    P("- Not modelled: scaling plans, the funded daily loss limit, the Topstep consistency path, "
      "any cap lower than the one in FUNDED_RULES, the live-capital stage, tax. ES bars are the "
      "MES proxy, as in firm_fit_test.py.")


if __name__ == "__main__":
    sys.exit(main() or 0)
