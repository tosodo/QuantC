#!/usr/bin/env python3
"""Local overfitting checks on the noise-area 5-yr NQ backtest (daily $ at 1 MNQ). Read-only, sends nothing out.
Deflated Sharpe (Bailey & Lopez de Prado), stationary-bootstrap CI on Sharpe, and a split-half check."""
import numpy as np, pandas as pd
from statistics import NormalDist
ND=NormalDist()
s = pd.read_csv("/Users/osodo.t/qc-demo-test/research-2026-10-03/nq_b_daily_usd_1mnq.csv", index_col=0).iloc[:,0]
s.index = pd.to_datetime(s.index); r = s.values; n = len(r)
sr = r.mean()/r.std(ddof=1); m=r-r.mean(); g3=(m**3).mean()/(m**2).mean()**1.5; g4=(m**4).mean()/(m**2).mean()**2
print(f"days {n}  mean ${r.mean():.1f}/day  daily Sharpe {sr:.4f}  annualised {sr*np.sqrt(252):.2f}  skew {g3:.2f} kurt {g4:.1f}")
def psr(sr_hat, sr0):
    return ND.cdf((sr_hat-sr0)*np.sqrt(n-1)/np.sqrt(1-g3*sr_hat+(g4-1)/4*sr_hat**2))
print(f"PSR vs zero (is Sharpe >0?): {psr(sr,0):.3f}")
# DSR: expected best Sharpe among N trials of pure noise; cross-trial Sharpe sd ~ 1/sqrt(n)
eg = 0.5772156649
for N in (1, 8, 15, 50):
    sd = 1/np.sqrt(n)
    sr0 = 0 if N==1 else sd*((1-eg)*ND.inv_cdf(1-1/N)+eg*ND.inv_cdf(1-1/(N*np.e)))
    print(f"DSR with {N:>2} trials tried: noise-best annual Sharpe {sr0*np.sqrt(252):.2f}  -> probability edge is real {psr(sr,sr0):.3f}")
# stationary bootstrap, mean block 10 days
rng = np.random.default_rng(1); B=5000; p=1/10; out=[]
for _ in range(B):
    idx = np.empty(n,int); idx[0]=rng.integers(n)
    jump = rng.random(n)<p; new = rng.integers(0,n,n)
    for i in range(1,n): idx[i] = new[i] if jump[i] else (idx[i-1]+1)%n
    x=r[idx]; out.append(x.mean()/x.std(ddof=1)*np.sqrt(252))
lo,hi=np.percentile(out,[2.5,97.5]); print(f"bootstrap annual Sharpe 95% CI: {lo:.2f} to {hi:.2f}; share of resamples <=0: {(np.array(out)<=0).mean():.3f}")
# remove top 3 days and split halves / years
print(f"mean without top 3 days: ${np.sort(r)[:-3].mean():.1f}/day  (top3 sum ${np.sort(r)[-3:].sum():.0f} of total ${r.sum():.0f})")
h=n//2
for nm,x in (("first half",r[:h]),("second half",r[h:])):
    print(f"{nm}: mean ${x.mean():.1f}/day t={x.mean()/(x.std(ddof=1)/np.sqrt(len(x))):.2f}")
print(s.groupby(s.index.year).agg(['sum','mean']).round(1).to_string())
