"""Edge calculator: measure an edge with an honest interval and convert it into funding odds,
instead of searching variations. Pure Python, no market data needed beyond a trade list.

  python3 edge_calculator.py measure --trades FILE [--sequence LIVE] [--trials 12]
  python3 edge_calculator.py plan [--sigma 84]

`measure` reads a CSV with a `pnl` column (net $ per trade at 1 contract) or a `pts` column
(gross points; costs from --cost/--slip as in live_rules_backtest). `--sequence NAME` keeps
the rows of that `sequence` column (the file `lucid_wf_test.py run --trades-out` writes).
It reports mean, sd, t, a block-bootstrap interval on the mean, the Deflated Sharpe
probability for --trials looks, trades and years needed for t = 3 (Harvey, Liu and Zhu), and
the funding odds at the point estimate and at the interval ends, from the closed form below
and (--sims > 0) a bootstrap through the unchanged rule engine.

`plan` runs the same conversion over a grid of edges, so the edge a target pass rate needs is
read off, not searched for.

Closed-form pass probability (Brownian approximation, independent trades, unlimited time),
k = 2*mu/sigma^2, D = trailing drawdown, L = lock, T = target:
  stage 1 (floor trails the peak until balance = D + L): p1 = exp(-lambda*(D+L)),
          lambda = k / (exp(k*D) - 1)  (zero drift: 1/D)
  stage 2 (floor fixed; barriers +A = T-(D+L) above, -B = D below): p2 = (1-exp(k*B)) /
          (exp(-k*A) - exp(k*B))  (zero drift: B/(A+B));  pass = p1 * p2.
It overstates real odds (no time limit, no fat tails); the bootstrap includes both.

UNVERIFIED inputs of the Lucid rule set (price, trail lock, payout cap, cycle length) are
used as they stand in firm_fit_test.py and stay unverified in every report.
"""
import argparse
import csv
import math
import os
import random
import sys
from statistics import NormalDist, mean, pstdev

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import firm_fit_test as ff  # noqa: E402
import live_rules_backtest as lrb  # noqa: E402

N = NormalDist()
EULER = 0.5772156649015329
T_NEW = 3.0                      # Harvey, Liu and Zhu: t for a newly claimed edge
LUCID = "Lucid 100K LucidPro (price GUESS)"
UNVERIFIED = ("UNVERIFIED (not changed here): Lucid eval price, trail lock, funded payout cap "
              "and cycle length.")


# ---------- statistics ----------

def moments(x):
    n = len(x)
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / (n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return dict(n=n, mean=m, sd=0.0, skew=0.0, kurt=3.0)
    s = math.sqrt(sum((v - m) ** 2 for v in x) / n)
    return dict(n=n, mean=m, sd=sd,
                skew=sum(((v - m) / s) ** 3 for v in x) / n,
                kurt=sum(((v - m) / s) ** 4 for v in x) / n)


def t_stat(m, sd, n):
    return m / (sd / math.sqrt(n)) if sd > 0 else 0.0


def trades_for_t(mu, sigma, t=T_NEW):
    """n with mu/(sigma/sqrt(n)) = t, i.e. (t*sigma/mu)^2; None when mu <= 0."""
    return None if mu <= 0 else (t * sigma / mu) ** 2


def block_boot_means(x, sims, block=5, seed=7):
    rng = random.Random(seed)
    n, out = len(x), []
    for _ in range(sims):
        s, got = 0.0, 0
        while got < n:
            i = rng.randrange(n)
            for k in range(block):
                if got >= n:
                    break
                s += x[(i + k) % n]
                got += 1
        out.append(s / n)
    out.sort()
    return out


def boot_ci(x, sims=2000, block=5, level=0.95):
    b = block_boot_means(x, sims, block)
    lo = b[int((1 - level) / 2 * sims)]
    hi = b[min(sims - 1, int((1 + level) / 2 * sims))]
    return lo, hi


def expected_max_z(trials):
    """Expected maximum of `trials` independent standard normals (Bailey and Lopez de Prado)."""
    if trials <= 1:
        return 0.0
    return ((1 - EULER) * N.inv_cdf(1 - 1 / trials)
            + EULER * N.inv_cdf(1 - 1 / (trials * math.e)))


def deflated_sharpe(m, trials):
    """Probability that the true per-trade Sharpe is above what the best of `trials` null
    looks would show, given skew and kurtosis (Bailey and Lopez de Prado 2014)."""
    if m["sd"] == 0 or m["n"] < 3:
        return None
    sr = m["mean"] / m["sd"]
    se = math.sqrt(max(1e-12, (1 - m["skew"] * sr + (m["kurt"] - 1) / 4 * sr * sr)
                       / (m["n"] - 1)))
    sr0 = expected_max_z(trials) * se       # null looks all have this standard error
    return N.cdf((sr - sr0) / se)


# ---------- funding odds ----------

def pass_prob(mu, sigma, rule):
    """Closed-form per-attempt pass probability, see the module docstring."""
    d, lock, tgt = rule["dd"], rule["lock"], rule["target"]
    a1 = d + lock                    # balance at which the floor stops trailing
    up, down = tgt - a1, d
    if sigma <= 0:
        return 1.0 if mu > 0 else 0.0
    k = 2 * mu / sigma ** 2
    if abs(k * d) < 1e-9:
        lam, p2 = 1 / d, down / (up + down)
    elif k > 0:
        lam = k * math.exp(-k * d) / (-math.expm1(-k * d))
        p2 = -math.expm1(-k * down) / -math.expm1(-k * (up + down))
    else:
        lam = k / math.expm1(k * d)
        p2 = (math.exp(k * up) - math.exp(k * (up + down))) / -math.expm1(k * (up + down))
    p1 = math.exp(-lam * a1)
    return max(0.0, min(1.0, p1 * p2))


def trades_to_target(mu, rule):
    return None if mu <= 0 else rule["target"] / mu


def fmt_pct(x):
    return "n/a" if x is None else f"{100 * x:.0f}%"


def fmt_n(x):
    return "never" if x is None else f"{x:,.0f}"


def funding_rows(mu_list, sigma, rule, tpy):
    rows = []
    for mu in mu_list:
        p = pass_prob(mu, sigma, rule)
        n = trades_to_target(mu, rule)
        t3 = trades_for_t(mu, sigma)
        rows.append((mu, p, n, None if n is None else n / tpy, t3, None if t3 is None else t3 / tpy))
    return rows


def print_rows(rows):
    print(f"{'edge $/trade':>13} {'pass (closed)':>14} {'trades to $target':>18} "
          f"{'years':>6} {'trades for t=3':>15} {'years':>6}")
    for mu, p, n, ny, t3, ty in rows:
        yr = lambda v: "never" if v is None else f"{v:.1f}"
        print(f"{mu:>13.2f} {fmt_pct(p):>14} {fmt_n(n):>18} {yr(ny):>6} {fmt_n(t3):>15} {yr(ty):>6}")


# ---------- commands ----------

def load_pnls(path, pnl_col, sequence, cost, slip):
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if sequence and row.get("sequence") != sequence:
                continue
            if row.get(pnl_col) not in (None, ""):
                out.append(float(row[pnl_col]))
            elif row.get("pts") not in (None, ""):
                out.append(lrb.net({"pts": float(row["pts"])}, cost, slip))
    return out


def measure(a):
    rule = ff.RULE_SETS[LUCID]
    x = load_pnls(a.trades, a.pnl_col, a.sequence, a.cost, a.slip)
    if len(x) < 30:
        sys.exit(f"only {len(x)} trades; need at least 30")
    m = moments(x)
    years = m["n"] / a.tpy
    lo, hi = boot_ci(x, a.boot, a.block)
    t = t_stat(m["mean"], m["sd"], m["n"])
    dsr = deflated_sharpe(m, a.trials)
    print(f"EDGE CALCULATOR  {a.trades}" + (f"  [{a.sequence}]" if a.sequence else ""))
    print(UNVERIFIED)
    print(f"\ntrades {m['n']} (~{years:.1f} yrs at {a.tpy}/yr), net per trade at 1 contract")
    print(f"mean ${m['mean']:.2f}   sd ${m['sd']:.2f}   skew {m['skew']:.2f}   kurtosis {m['kurt']:.1f}")
    print(f"t-stat {t:.2f}  (new-edge bar is {T_NEW:.1f}; Bonferroni for {a.trials} looks needs "
          f"z {N.inv_cdf(1 - 0.05 / 2 / max(1, a.trials)):.2f})")
    print(f"95% block-bootstrap interval for the mean: ${lo:.2f} to ${hi:.2f}"
          + ("   <- includes zero: not distinguishable from no edge" if lo <= 0 <= hi else ""))
    print(f"Deflated Sharpe probability after {a.trials} looks: "
          + ("n/a" if dsr is None else f"{100 * dsr:.0f}%  (want 95%+)"))
    need = trades_for_t(m["mean"], m["sd"])
    if need is None:
        print("trades for t = 3 at this mean: never (mean is not positive)")
    else:
        print(f"trades for t = 3 at this mean: {need:,.0f}  (~{need / a.tpy:.1f} yrs at {a.tpy}/yr); "
              f"you have {m['n']}")
    print("\nFunding odds by contracts (closed form, per attempt; upper bounds). "
          "Rows: interval low / point / interval high.")
    for c in a.sizes:
        print(f"\n{c} contract(s)")
        print_rows(funding_rows([c * lo, c * m["mean"], c * hi], c * m["sd"], rule, a.tpy))
    if a.sims > 0:
        seq = [(p, max(0.0, -p), 1) for p in x]      # excursion unknown: taken as the loss
        for c in a.sizes:
            sc = [(c * p, c * e, g) for p, e, g in seq]
            runs = ff.bootstrap_runs(sc, {LUCID: rule}, a.sims)[LUCID]
            s = ff.summarise(runs)
            cm = ff.cost_model(s["pass_"] / 100, s["breach"] / 100, rule, s["mean_trades"], tpy=a.tpy)
            cost = "n/a" if cm["cost"] is None else f"${cm['cost']:,.0f}"
            print(f"bootstrap {c} contract(s): pass {s['pass_']:.1f}%  breach {s['breach']:.1f}%  "
                  f"open {s['open_']:.1f}%  cost per pass {cost}")
        print("(bootstrap uses the loss as the intratrade excursion: optimistic for winners "
              "that dipped first)")
    print("\nReading it: act only if the interval's low end still gives odds worth the fee, "
          "the deflated probability clears 95% and the trades-for-t=3 is near what you have.")


def plan(a):
    rule = ff.RULE_SETS[LUCID]
    print("EDGE PLAN: what edge a target pass rate needs")
    print(UNVERIFIED)
    print(f"sigma ${a.sigma:.0f} per trade at 1 contract, {a.tpy} trades/yr, "
          f"target ${rule['target']:.0f}, drawdown ${rule['dd']:.0f}, lock ${rule['lock']:.0f}\n")
    mus = [0, 1, 2, 4, 6, 8, 12, 20, 40]
    print_rows(funding_rows(mus, a.sigma, rule, a.tpy))
    print("\nedge needed for a target pass rate (closed form):")
    for tgt in (0.5, 0.6, 0.7, 0.8, 0.9):
        lo, hi = 0.0, 10 * a.sigma
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if pass_prob(mid, a.sigma, rule) < tgt else (lo, mid)
        mu = (lo + hi) / 2
        print(f"  {int(tgt * 100)}%: ${mu:.2f} per trade -> {fmt_n(trades_for_t(mu, a.sigma))} "
              f"trades to show it at t = 3 (~{trades_for_t(mu, a.sigma) / a.tpy:.1f} yrs)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--trades", required=True)
    m.add_argument("--sequence", default="")
    m.add_argument("--pnl-col", default="pnl")
    m.add_argument("--cost", type=float, default=lrb.BASE_COST)
    m.add_argument("--slip", type=int, default=lrb.BASE_SLIP)
    m.add_argument("--trials", type=int, default=1)
    m.add_argument("--tpy", type=int, default=ff.TRADES_PER_YEAR)
    m.add_argument("--boot", type=int, default=2000)
    m.add_argument("--block", type=int, default=5)
    m.add_argument("--sims", type=int, default=0)
    m.add_argument("--sizes", type=int, nargs="+", default=[1, 2])
    p = sub.add_parser("plan")
    p.add_argument("--sigma", type=float, default=84.0)
    p.add_argument("--tpy", type=int, default=ff.TRADES_PER_YEAR)
    a = ap.parse_args()
    measure(a) if a.cmd == "measure" else plan(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
