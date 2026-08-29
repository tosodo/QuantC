# London-session Opening Range Breakout — Results

Pre-registration: [LONDON_HYPOTHESIS.md](LONDON_HYPOTHESIS.md) (locked
before this data was inspected, itself gated through the
propfirm-research-auditor methodology check — verdict `needs_testing`,
2026-08-20). This file records what was actually MEASURED by
`london_orb_test.py` — nothing here is invented or estimated.

## 1. Entry-predicts-direction test (MEASURED)

In-sample (through 2025-02-14) then the held-out out-of-sample slice
(after 2025-02-14), looked at once, reusing the identical cutoff date
already locked by the NY test (not a fresh split — see
LONDON_HYPOTHESIS.md #3).

### Long side (close above the 08:00–08:14 London-time opening range)

| Instrument | In-sample meanR (n) | p | Out-of-sample meanR (n) | p |
|---|---|---|---|---|
| NQ | +0.109R (470) | 0.0246 | +0.146R (201) | 0.0289 |
| ES | +0.159R (467) | 0.0009 | +0.131R (196) | 0.0529 |
| YM | +0.071R (463) | 0.1155 | +0.173R (189) | 0.0182 |

Sign agreement across all three instruments: **AGREE**, both slices — every
point estimate stayed positive, in-sample and out-of-sample, magnitude
consistently in a **0.07R–0.17R band** with no sign flip anywhere.

**But this is meaningfully weaker than the NY result.** No single
instrument independently clears the pre-registered 0.025 threshold in
*both* slices — the set that clears shuffles: {NQ, ES} clear in-sample,
{YM} clears out-of-sample, and NQ/ES both miss out-of-sample (NQ by a
hair, 0.0289 vs 0.025; ES more clearly, 0.0529). Compare to the NY test,
where NQ and ES *both* cleared *both* slices with the edge size essentially
unchanged (RESULTS.md §1). That clean pattern does not repeat here — this
looks like a real but small, noisy positive signal, consistent with the
weaker structural rationale already flagged in the domain check
(LONDON_HYPOTHESIS.md #1): London's 08:00 isn't a discrete price-discovery
event for a CME-listed US index future the way NYSE's 9:30 open is.

Real Tradovate cost (free-plan tier) barely moves any of these numbers, as
with the NY test — cost was never close to the binding constraint here
either way.

### Short side (close below the range) — not established

Sign agreement across all three instruments: **AGREE** (all negative, both
slices) — an improvement on the NY test's short side, which disagreed in
sign out-of-sample (YM flipped). But nothing here is close to significant:
best case is YM in-sample at p=0.0403, which still misses the 0.025
threshold; every out-of-sample short p-value is 0.15–0.86. This side stays
in "no evidence either way" territory — not rejected on a sign flip like
NY's short side, just never shows a signal strong enough to trust.

## 2. Sample size reality check (MEASURED)

Same instruments/window produced fewer eligible days than the NY test
(~1,291 vs ~1,558 total, due to the ~17% of days with incomplete
pre-market data — see LONDON_HYPOTHESIS.md #3), and the out-of-sample slice
in particular is thin (n≈190–200 per instrument). At that sample size and
the observed σ≈0.94–1.05R, this run can resolve roughly a 0.3–0.4R true
edge at 80% power (per the project's standard reference table) — an edge
in the 0.1–0.15R range, which is what's actually observed, sits close to
the noise floor this sample can distinguish from zero. That is the direct,
measured explanation for why significance flickers between slices and
instruments rather than holding steady.

## 3. NOT MEASURED / still open

- **Survivability** — no ruin.py run in this pass. The signal did not
  clear the bar cleanly enough (§1) to warrant it yet, and even if it had,
  the required next step per the audit is a **joint** simulation combining
  this signal's trade dates with the existing NY signal's — not a reuse of
  RESULTS.md's single-signal numbers.
- **Tail / outlier check** (RESULTS.md §2.5's equivalent) — not run here;
  would only be worth doing if a decision to proceed is actually made.
- **A fresh out-of-sample look** — not possible. The held-out slice has
  now been inspected once, per the pre-registered design; per this
  project's own standing rule (test_design.md #8/#10), it cannot be
  re-examined, and no filter or window adjustment should be tried now to
  chase significance on data that's already been seen — that would be
  exactly the post-hoc-filtering red flag this discipline exists to catch.

## Verdict

**promising_but_unproven** — same category as the NY result at this same
stage, but on weaker footing. The long side never flips sign across three
instruments and two independently-drawn slices, and the point estimates
sit in a plausible, non-trivial range (0.07–0.17R) — this is not the flat
zero the FX version of this mechanism measured (domain_priors.md H1). But
unlike the NY result, no single instrument clears the pre-registered
significance bar in both slices, and the set that does clear changes
between in-sample and out-of-sample — consistent with a small, real-but-
noisy effect sitting near what this sample size can actually resolve,
though a fluke that happens to keep the same sign twice by chance cannot
be ruled out either.

**Recommendation: do not proceed to a joint survivability simulation or
any Ghost/Pine work on this yet.** The honest options from here are (a)
park it — the evidence is a genuine maybe, not a genuine yes, and the
already-running NY strategy doesn't need a second, less-proven signal
riding on the same drawdown budget — or (b) wait for more data (real
calendar time passing adds fresh, never-before-seen out-of-sample days,
which is the only clean way to get more evidence here — re-slicing this
same 5 years again is not). No live-money decision was ever on the table
for this test regardless of the outcome.
