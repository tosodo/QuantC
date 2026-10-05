# Backup-strategy screen: outcomes (5 Oct 2026)

Purpose: find a fast-trading backup if the Nasdaq noise-area paper test fails at the 30 Oct review. Each script was run once, as written, on the in-sample slice only. The out-of-sample data was NOT used. Nothing was tuned.

| Idea | Folder | Outcome | Why |
|---|---|---|---|
| Index mean-reversion | index_mean_reversion | DROPPED | Looked good on long cash-index history, but 0 of 6 cells cleared the bar on tradable futures (one reversed). Only ~18 trades in the out-of-sample window; too slow for a 30-day eval. |
| Nasdaq vs S&P/Dow relative value | nq_es_relative_value | DROPPED | Older data: long side mildly positive (p~0.04-0.07), short side inconsistent across the two pairs. Only ~2-5 independent trades a year, same slowness as mean-reversion. Out-of-sample slice left unused. |
| MNQ 9:30 session open | mnq_session_open | NO EDGE | 408 days: continuation +0.03R, reversal -0.04R, both p>0.3. S&P and Dow flat, signs disagree. Out-of-sample slice left unused. |
| Gold fix breakout | gold_fix_breakout | PARKED | Plan only. Needs a data purchase and a check of Lucid's rules on scheduled events first. |

| London-open breakout | orb_breakout (London files) | PARKED (maybe) | Long side positive on all three indexes in both data slices (+0.07 to +0.17R), but no instrument cleared the bar in both; sample can only detect ~0.3R+. Out-of-sample data already used once, so no re-test. Our 5 Oct European-open test also failed. Only clean next step is a forward paper test on new days; revisit after the 30 Oct review if noise-area fails. |

Note: the rest of orb_breakout is the research behind the live MES v2 rule, not a separate backup.

Do not re-run the dropped ideas. Old files in these folders use out-of-date Lucid numbers ($6,000 target, $1,800 limit); current figures are $6,258 to target and $2,564 cushion.
