# One-page review templates (DRAFT, 13 Oct 2026)

Status: process aid only. Changes no trading rule, no alert, no live setting.
Source of the ideas: the TradingAgents paper (arXiv 2412.20138). We borrow
the *process* only. Their performance claims are not evidence (3-month bull
window, Sharpe 8.21 which the authors themselves call above the plausible
range, no costs, no live test).

Fits the existing rules: pre-registered tests, held-out data untouched until
the plan is frozen, no strategy hopping without good evidence.

---

## Part 1: Challenge review (for any new idea or proposed change)

Use before an idea gets any test time. Keep every answer to a few lines.

**Idea in one sentence:**

**Frozen test plan exists and is dated?** (yes / no. If no, stop here.)

| Role | Job | Output |
|---|---|---|
| FOR | Best honest case for the idea. Must cite data we already hold, not hopes. | 3 bullets max |
| AGAINST | Best case it is noise, a repeat of something already dropped, or too slow/costly. Must check the dropped-ideas list in the research folder. | 3 bullets max |
| REFEREE | Does not argue. Records which side's points are backed by evidence and which are opinion. | Verdict below |

**Verdict (pick one):**
- DROP: against side wins, or the idea repeats a dropped one.
- TEST: freeze the plan first, then run it once on the agreed data.
- PARK: interesting but not now; write the reason and a revisit date.

**Checks the referee must tick:**
- [ ] Held-out data still untouched
- [ ] Trading costs and slippage included
- [ ] Enough trades to mean something (state the number)
- [ ] Result is not "too good" (a very high Sharpe or win rate over a short window is a warning sign, not a win)
- [ ] Not a hop away from the live setup without good evidence

**Reviewer notes are filled in on a fixed form (above), not as free chat.**
Free discussion is allowed only inside the FOR vs AGAINST step.

---

## Part 2: Decision log (for the 40 / 100-trade checkpoints)

One row per decision or change considered. Review the whole log at each
checkpoint. Never edit an old row; add a new one.

| Date | Decision | Why (evidence used) | What we expected | What happened | Right / wrong / too early |
|---|---|---|---|---|---|
| | | | | | |

**At each checkpoint, answer:**
1. Which past decisions turned out wrong, and was the evidence at the time weak or did we ignore it?
2. Did any "too early" rows become answerable?
3. Any lesson that should change the Part 1 checks?

---

## Out of scope on purpose
- No AI debate or news filter inside live trading.
- No install of the TradingAgents code.
- A news/event "stand-aside" idea, if ever wanted, goes through Part 1 and
  needs a pre-registered forward paper test. A plain CPI/FOMC calendar filter
  is the cheaper first thing to test.
