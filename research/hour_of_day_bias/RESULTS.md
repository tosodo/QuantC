# Hour-of-Day Bias Screen: Result (9 Oct 2026)

Verdict: **NO HOUR-OF-DAY BIAS. DROPPED.** Run once, in-sample only (through
2025-02-17, 70% cutoff decided on NQ dates by position). Held-out slice NOT
used. Plan: `HYPOTHESIS.md` (7 Oct), unchanged. Script:
`screen_hour_of_day.py`. Raw output: `RESULTS_in_sample_raw.txt`.

Bar: two-sided p < 0.00227 (0.05 / 22) on NQ AND ES with the same sign, plus
the drift, top-3-days, halves and cost checks.

- Windows clearing the bar on either instrument: **none**.
- Smallest p-values: 23:00-24:00 (NQ p = 0.022, ES p = 0.015, both positive,
  about +0.8 bp); NQ 11:00 (p = 0.033, but ES p = 0.16). With 22 windows
  tested, a p near 0.02 is expected by chance about once, so these are noise.
- 10:00-11:00 (data-release hour) was negative on both (NQ p = 0.12, ES p = 0.23)
  and also failed the bar.
- Average of all 22 window means was about +0.07 to +0.09 bp: drift is tiny.
- Skipped day-windows (missing bar or contract roll): NQ 164, ES 446 of 28,271.

Interpretation choices (made before running): window date = NY calendar date
of the window start; cost check = net of cost at least 2x cost; top-3 check =
drop the 3 best sign-adjusted days; p-value = normal approximation.
Not proof of no effect smaller than about 6 NQ points per window (Section 6
of the plan). Do not re-run or retune.
