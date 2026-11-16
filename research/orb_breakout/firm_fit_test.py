#!/usr/bin/env python3
"""
firm_fit_test.py - which prop-firm rule set suits the live ORB's small edge.

Takes the SAME trade list as live_rules_backtest.py (its loader and trade
generator, ES bars as the MES proxy) and walks it through a table of rule
sets (RULE_SETS below). For each one it reports, from rolling real-order
starts and from a 5-trade block bootstrap: pass, breach and still-open
rates, median trades and calendar days to pass, expected attempts, expected
fees per pass and expected years of trading per pass.

Needs the local data (gitignored): data/continuous/ES.csv, built by
build_continuous.py. Run from this folder:

    python3 firm_fit_test.py > firm_fit_report.md
    python3 firm_fit_test.py --data PATH --sims 3000

The rule sets come from FIRM_RULES_SURVEY.md and are unverified (search
snippets); edit RULE_SETS as the firms' own pages are checked.
"""
import argparse
import os
import random
import sys
from datetime import date
from statistics import median

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_rules_backtest as lrb  # noqa: E402

# ---------- RULE SETS ----------
# Numbers come from FIRM_RULES_SURVEY.md (2026-10-20, search snippets, no page read
# in full). Tags: OFF = firm's own help-center snippet, 3P = third party, GUESS =
# not found, a stand-in. Dollar amounts are for 1 MES on the stated account size.
#   start         starting balance
#   target        profit target, $ above start
#   dd            max drawdown size, $
#   dd_type       "static" | "eod_trailing" | "intraday_trailing"
#   lock          trailing types only: the floor stops rising once it reaches
#                 start + lock (None = never locks)
#   daily_loss    $ loss limit in one day, breach if hit (None = no limit)
#   consistency   best single day must be <= this share of total profit at the
#                 moment of passing (None = no rule)
#   min_days      minimum trading days before a pass counts
#   eval_fee      one-off cost of attempt 1
#   monthly_fee   subscription per month while an attempt is running (0 = one-time)
#   reset_fee     cost of each retry after a breach
#   activation_fee  one-off cost on a pass
# Only the evaluation is modelled. Funded-stage rules (Lucid 40% consistency and
# $750 cycle minimum, Topstep MLL reset to 0 after each payout) are not.
RULE_SETS = {
    # target 6000, MLL 3000 EOD OFF; lock +100 and eval price are GUESS (reset ~170 OFF)
    "Lucid 100K LucidPro (price GUESS)": dict(
        start=100000.0, target=6000.0, dd=3000.0, dd_type="eod_trailing", lock=100.0,
        daily_loss=None, consistency=None, min_days=0,
        eval_fee=170.0, monthly_fee=0.0, reset_fee=170.0, activation_fee=0.0),
    # target 6000, MLL 3000 EOD, stops at start balance, 55% consistency, $99/mo, $149 activation: OFF
    "Topstep 100K Combine (standard)": dict(
        start=100000.0, target=6000.0, dd=3000.0, dd_type="eod_trailing", lock=0.0,
        daily_loss=None, consistency=0.55, min_days=0,
        eval_fee=0.0, monthly_fee=99.0, reset_fee=99.0, activation_fee=149.0),
    # same rules, no-activation-fee path: $149/mo OFF
    "Topstep 100K Combine (no activation fee)": dict(
        start=100000.0, target=6000.0, dd=3000.0, dd_type="eod_trailing", lock=0.0,
        daily_loss=None, consistency=0.55, min_days=0,
        eval_fee=0.0, monthly_fee=149.0, reset_fee=149.0, activation_fee=0.0),
    # 50K: target 3000, MLL 2000, 55% OFF; $49/mo + $149 activation OFF
    "Topstep 50K Combine (standard)": dict(
        start=50000.0, target=3000.0, dd=2000.0, dd_type="eod_trailing", lock=0.0,
        daily_loss=None, consistency=0.55, min_days=0,
        eval_fee=0.0, monthly_fee=49.0, reset_fee=49.0, activation_fee=149.0),
    # 50K Select: target 3000, MLL 2000 EOD, 40% consistency, 3 min days, $165 / reset $109: OFF;
    # eval one-time vs monthly unknown; where the trail locks unknown
    "Tradeify Select 50K (40% consistency)": dict(
        start=50000.0, target=3000.0, dd=2000.0, dd_type="eod_trailing", lock=None,
        daily_loss=None, consistency=0.40, min_days=3,
        eval_fee=165.0, monthly_fee=0.0, reset_fee=109.0, activation_fee=0.0),
    # 100K Select: target 6000, MLL 3000 are 3P only; price GUESS (2x the 50K)
    "Tradeify Select 100K (3P figures)": dict(
        start=100000.0, target=6000.0, dd=3000.0, dd_type="eod_trailing", lock=None,
        daily_loss=None, consistency=0.40, min_days=3,
        eval_fee=330.0, monthly_fee=0.0, reset_fee=218.0, activation_fee=0.0),
    # MFFU Rapid EOD 50K: 3000 / 2000 EOD, 30% consistency, 4 min days OFF; price GUESS, no reset
    "MFFU Rapid EOD 50K (price GUESS)": dict(
        start=50000.0, target=3000.0, dd=2000.0, dd_type="eod_trailing", lock=None,
        daily_loss=None, consistency=0.30, min_days=4,
        eval_fee=125.0, monthly_fee=0.0, reset_fee=125.0, activation_fee=0.0),
}

HORIZON = 2000        # trades per bootstrap path, as lucid_run's bootstrap
BLOCK = 5             # trades per bootstrap block (about one trading week)
MAX_ATTEMPTS = 5      # the trader retries after each breach up to this many
TRADES_PER_YEAR = 200


# ---------- the rule engine ----------

def floor_for(rule, peak):
    """Drawdown floor given the balance peak. Static: never moves. Trailing:
    peak - dd, capped at start + lock once the lock level is set."""
    if rule["dd_type"] == "static":
        return rule["start"] - rule["dd"]
    f = max(rule["start"] - rule["dd"], peak - rule["dd"])
    return f if rule["lock"] is None else min(f, rule["start"] + rule["lock"])


def day_peak(rule, hwm, bal, pnl):
    """Highest equity the floor sees after this trade. EOD trailing only sees
    the closing balance. Intraday trailing sees the running intraday peak; the
    trade list has only the adverse excursion (mae), not the favourable one,
    so the peak is approximated by the trade's close when it won (a lower
    bound on the true peak) and assumed to come BEFORE the adverse excursion
    (the unlucky order). Thus the intraday floor is never below the EOD floor."""
    if rule["dd_type"] == "intraday_trailing":
        return max(hwm, bal + max(pnl, 0.0))
    return hwm


def can_pass(rule, bal, days, best_day):
    """Target reached, minimum days done, and the best day not too big a
    share of the profit."""
    profit = bal - rule["start"]
    if profit < rule["target"] or days < rule["min_days"]:
        return False
    return rule["consistency"] is None or best_day <= rule["consistency"] * profit


def run_rules(seq, rule):
    """seq: list of (pnl, mae_usd, gap_days) in time order, one per trading day
    with a trade. Returns ('pass'|'fail'|'open', trades_used, calendar_days).
    With a one-line Lucid rule set this equals live_rules_backtest.lucid_run."""
    bal = hwm = rule["start"]
    best, cal = 0.0, 0
    for i, (pnl, mae, gap) in enumerate(seq, 1):
        cal += gap
        peak = day_peak(rule, hwm, bal, pnl)
        floor = floor_for(rule, peak)
        if bal - mae <= floor:
            return "fail", i, cal
        if rule["daily_loss"] is not None and max(mae, -pnl) >= rule["daily_loss"]:
            return "fail", i, cal
        bal += pnl
        if bal <= floor:
            return "fail", i, cal
        best = max(best, pnl)
        if can_pass(rule, bal, i, best):
            return "pass", i, cal
        hwm = max(peak, bal)
    return "open", len(seq), cal


# ---------- sequences ----------

def make_seq(trades, cost, slip, size=1):
    """(pnl, mae_usd, gap_days) per trade, as lucid pass_rates builds it, plus
    the calendar days since the previous trade (1 for the first). `size` MES
    contracts: P&L, excursion and costs all scale with it."""
    out, prev = [], None
    for t in trades:
        d = date.fromisoformat(t["date"])
        gap = 1 if prev is None else max(1, (d - prev).days)
        prev = d
        out.append((size * lrb.net(t, cost, slip),
                    size * ((t["mae_pts"] + slip * lrb.TICK) * lrb.PV + cost), gap))
    return out


def block_path(seq, rng, horizon=HORIZON, block=BLOCK):
    """iid block bootstrap: random start, BLOCK consecutive trades (wrapping
    around the end), blocks joined until the path is `horizon` long."""
    n, out = len(seq), []
    while len(out) < horizon:
        s = rng.randrange(n)
        out.extend(seq[(s + k) % n] for k in range(block))
    return out[:horizon]


def rolling_runs(seq, rule):
    """Start at every trade and walk forward in real order."""
    return [run_rules([(seq[i][0], seq[i][1], 1)] + seq[i + 1:], rule) for i in range(len(seq))]


def bootstrap_runs(seq, rules, sims, seed=1):
    """{rule name: [runs]}; every rule set sees the same random paths."""
    rng = random.Random(seed)
    res = {k: [] for k in rules}
    for _ in range(sims):
        path = block_path(seq, rng)
        for k, rule in rules.items():
            res[k].append(run_rules(path, rule))
    return res


# ---------- statistics ----------

def summarise(runs):
    """Rates in % of all runs, medians over passing runs, mean trades used."""
    n = len(runs)
    out = {o: [r for r in runs if r[0] == o] for o in ("pass", "fail", "open")}
    med = lambda xs: median(xs) if xs else None
    return dict(n=n, pass_=100 * len(out["pass"]) / n, breach=100 * len(out["fail"]) / n,
                open_=100 * len(out["open"]) / n,
                med_trades=med([r[1] for r in out["pass"]]),
                med_days=med([r[2] for r in out["pass"]]),
                mean_trades=sum(r[1] for r in runs) / n)


def cost_model(p, b, rule, mean_trades, max_attempts=MAX_ATTEMPTS, tpy=TRADES_PER_YEAR):
    """p, b = per-attempt pass and breach probabilities (0..1); anything else
    (still open) ends the effort. The trader retries after each breach, so
    attempt k happens with probability b^(k-1). Cost per pass = expected fees
    / P(a pass within max_attempts). Years = expected trades / P / tpy."""
    reach = [b ** k for k in range(max_attempts)]        # P(attempt k+1 is made)
    attempts = sum(reach)
    p_any = p * attempts
    months = mean_trades / tpy * 12 * attempts           # subscription months paid
    fees = (rule["eval_fee"] + rule["reset_fee"] * (attempts - 1)
            + rule.get("monthly_fee", 0.0) * months + rule["activation_fee"] * p_any)
    if p_any <= 0:
        return dict(attempts=attempts, p_any=0.0, cost=None, years=None)
    return dict(attempts=attempts, p_any=p_any, cost=fees / p_any,
                years=mean_trades * attempts / p_any / tpy)


def rates_for_cost(s, rolling):
    """Rolling starts near the data's end are still open only because the data
    ran out, so their rates are taken over resolved starts. Bootstrap paths
    are long enough that open is a real outcome and stays in."""
    if not rolling:
        return s["pass_"] / 100, s["breach"] / 100
    done = s["pass_"] + s["breach"]
    return (s["pass_"] / done, s["breach"] / done) if done else (0.0, 0.0)


# ---------- report ----------

def f(x, nd=0):
    return "n/a" if x is None else f"{x:,.{nd}f}"


def rule_text(r):
    lock = "" if r["lock"] is None else f", lock +{r['lock']:.0f}"
    cons = "-" if r["consistency"] is None else f"{100 * r['consistency']:.0f}%"
    dl = "-" if r["daily_loss"] is None else f"{r['daily_loss']:,.0f}"
    return (f"| {r['start']:,.0f} | {r['target']:,.0f} | {r['dd']:,.0f} {r['dd_type']}{lock} | "
            f"{dl} | {cons} | {r['min_days']} | {r['eval_fee']:,.0f} / {r.get('monthly_fee', 0):,.0f} / "
            f"{r['reset_fee']:,.0f} / {r['activation_fee']:,.0f} |")


def table(title, rules, sums, rolling, tpy):
    P = print
    P(f"\n## {title}\n")
    P("| rule set | pass % | breach % | open % | median trades | median cal days | "
      "attempts | P(pass in 5) % | $ per pass | years per pass |")
    P("|---|---|---|---|---|---|---|---|---|---|")
    for k, rule in rules.items():
        s = sums[k]
        p, b = rates_for_cost(s, rolling)
        c = cost_model(p, b, rule, s["mean_trades"], tpy=tpy)
        P(f"| {k} | {s['pass_']:.1f} | {s['breach']:.1f} | {s['open_']:.1f} | "
          f"{f(s['med_trades'])} | {f(s['med_days'])} | {c['attempts']:.2f} | "
          f"{100 * c['p_any']:.1f} | {f(c['cost'])} | {f(c['years'], 1)} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data/continuous/ES.csv"))
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--cost", type=float, default=lrb.BASE_COST)
    ap.add_argument("--slip", type=int, default=lrb.BASE_SLIP)
    ap.add_argument("--size", type=int, default=1, help="MES contracts per trade")
    ap.add_argument("--trades-per-year", type=float, default=TRADES_PER_YEAR)
    a = ap.parse_args()

    trades, sessions = lrb.build_trades(lrb.load_days(a.data))
    trades.sort(key=lambda t: t["date"])
    seq = make_seq(trades, a.cost, a.slip, a.size)
    shown = os.path.relpath(a.data, HERE)
    if shown.startswith(".."):
        shown = a.data

    P = print
    P("# Firm fit: the live ORB trades against a table of rule sets\n")
    P(f"Data: `{shown}`, {sessions[0]} to {sessions[-1]}, {len(sessions)} sessions, "
      f"{len(trades)} trades. Cost ${a.cost:.2f}/RT + {a.slip} tick, {a.size} MES.\n")
    P("Rule sets come from `RULE_SETS` in firm_fit_test.py, taken from FIRM_RULES_SURVEY.md "
      "(search snippets, not verified on the firms' pages). Prices tagged GUESS are stand-ins. "
      "Evaluation stage only: funded-stage rules and payouts are not modelled.\n")
    P("| rule set | start $ | target $ | drawdown $ | daily loss $ | consistency | min days | "
      "eval / monthly / reset / activation fee $ |")
    P("|---|---|---|---|---|---|---|---|")
    for k, r in RULE_SETS.items():
        P(f"| {k} " + rule_text(r))

    roll = {k: summarise(rolling_runs(seq, r)) for k, r in RULE_SETS.items()}
    boot = {k: summarise(v) for k, v in bootstrap_runs(seq, RULE_SETS, a.sims).items()}
    table("Rolling real-order starts (a start on every trade)", RULE_SETS, roll, True,
          a.trades_per_year)
    table(f"Block bootstrap ({a.sims} paths of {HORIZON} trades, {BLOCK}-trade blocks)",
          RULE_SETS, boot, False, a.trades_per_year)

    ranked = sorted(RULE_SETS, key=lambda k: (cost_model(*rates_for_cost(boot[k], False),
                    RULE_SETS[k], boot[k]["mean_trades"])["cost"] or float("inf")))
    P("\nCheapest per pass first (bootstrap): " + "; ".join(ranked) + ".")

    P("\n## How to read this\n")
    P("- Pass % and breach % are shares of all runs. A breach is the floor or the daily loss "
      "limit touched, tested on each trade's worst point (mae). Open = neither happened.")
    P(f"- Attempts: the trader retries after each breach, up to {MAX_ATTEMPTS}. Attempt 1 costs "
      "the eval fee, each retry the reset fee, a pass the activation fee. $ per pass = expected "
      f"fees / P(a pass within {MAX_ATTEMPTS}). Years per pass = expected trades / P / "
      f"{a.trades_per_year:.0f} trades a year (a ratio of expectations).")
    P("- Rolling rates use resolved starts only (starts near the data's end are open because the "
      "data stopped); the cost columns use the same resolved shares.")
    P("- Static floor never moves. EOD trailing raises the floor from closing balances. "
      "Intraday trailing raises it from the running intraday peak; the trade list has no "
      "favourable excursion, so the peak is taken as the trade's close when it won and assumed "
      "to come before the adverse excursion. That is harsher than EOD by construction; the "
      "close understates the true peak (kinder) and the ordering overstates the risk (harsher).")
    P("- Consistency blocks a pass until the best day is within its share of total profit. "
      "A daily loss breach is treated as a failed attempt (some firms only pause the day).")
    P("- Days are calendar days between trades as they happened; bootstrap blocks keep their "
      "real gaps. Payout rules, profit splits and scaling plans are not modelled.")
    P("- ES bars as the MES proxy, stop fills exactly at the stop price plus slippage; see "
      "live_rules_backtest.py for the full list of caveats.")


if __name__ == "__main__":
    sys.exit(main() or 0)
