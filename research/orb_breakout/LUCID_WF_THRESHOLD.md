# Lucid 100K: what trade profile passes 60% of attempts

**Unverified inputs (flag in every report):** Lucid eval price ($170, GUESS), trail lock (+$100, GUESS), funded payout cap (none, GUESS), funded cycle length (3 days, third-party). Target $6,000 and drawdown $3,000 EOD are from Lucid's help-center snippet. No rule number was changed by this study.

Rule engine: target $6,000, EOD trailing drawdown $3,000, floor locks at start + $100, no consistency rule, no minimum days. Per attempt, 600 paths of up to 2000 trades, results net of costs. Winners are a fixed size with no adverse excursion (optimistic); every loser loses exactly the 'risk' (the loss on a losing trade, not the stop distance: the live rules' typical loser is far smaller than the 125-point stop, see the profile table in the run report).

Risk $625 / $1,250 / $1,875 are the live 125-point stop at 1 / 2 / 3 MES; the share of the $3,000 floor one full stop uses is 21% / 42% / 62.5%.

| risk per trade $ | stop share of floor | win rate | winner $ | min expectancy $/trade | expectancy as % of risk | per MES in points (125-pt rows only) |
|---|---|---|---|---|---|---|
| 50 | 2% | 0.30 | 128 | 3.3 | 6.6% | - |
| 50 | 2% | 0.40 | 84 | 3.6 | 7.2% | - |
| 50 | 2% | 0.50 | 56 | 3.1 | 6.2% | - |
| 50 | 2% | 0.60 | 39 | 3.4 | 6.9% | - |
| 100 | 3% | 0.30 | 260 | 8.1 | 8.1% | - |
| 100 | 3% | 0.40 | 164 | 5.6 | 5.6% | - |
| 100 | 3% | 0.50 | 109 | 4.7 | 4.7% | - |
| 100 | 3% | 0.60 | 73 | 3.8 | 3.8% | - |
| 250 | 8% | 0.30 | 755 | 51.6 | 20.6% | - |
| 250 | 8% | 0.40 | 459 | 33.6 | 13.4% | - |
| 250 | 8% | 0.50 | 289 | 19.5 | 7.8% | - |
| 250 | 8% | 0.60 | 189 | 13.3 | 5.3% | - |
| 500 | 17% | 0.30 | 2,031 | 259.4 | 51.9% | - |
| 500 | 17% | 0.40 | 1,094 | 137.5 | 27.5% | - |
| 500 | 17% | 0.50 | 672 | 85.9 | 17.2% | - |
| 500 | 17% | 0.60 | 430 | 57.8 | 11.6% | - |
| 625 | 21% | 0.30 | 3,092 | 490.2 | 78.4% | 98.05 |
| 625 | 21% | 0.40 | 1,538 | 240.2 | 38.4% | 48.05 |
| 625 | 21% | 0.50 | 918 | 146.5 | 23.4% | 29.30 |
| 625 | 21% | 0.60 | 570 | 91.8 | 14.7% | 18.36 |
| 1,250 | 42% | 0.30 | 7,292 | 1,312.5 | 105.0% | 131.25 |
| 1,250 | 42% | 0.40 | 4,443 | 1,027.3 | 82.2% | 102.73 |
| 1,250 | 42% | 0.50 | 2,266 | 507.8 | 40.6% | 50.78 |
| 1,250 | 42% | 0.60 | 1,432 | 359.4 | 28.8% | 35.94 |
| 1,875 | 62% | 0.30 | not reached | n/a | n/a | n/a |
| 1,875 | 62% | 0.40 | 7,910 | 2,039.1 | 108.8% | 135.94 |
| 1,875 | 62% | 0.50 | 5,742 | 1,933.6 | 103.1% | 128.91 |
| 1,875 | 62% | 0.60 | 2,539 | 773.4 | 41.2% | 51.56 |

For scale, the live rules earn about $820 a year per MES over about 200 trades, which is about $4 a trade (Phase 3, 996 real ES trades, 29% win rate). Every row above needing more than that is an edge the live rules do not have.
