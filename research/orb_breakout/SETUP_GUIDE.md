# Setup guide — TradingView → QuantCrawler Ghost → Tradovate

What this covers: getting the validated ORB long strategy ([HYPOTHESIS.md](HYPOTHESIS.md),
[RESULTS.md](RESULTS.md)) running as a TradingView script that produces
correctly-formatted alerts.

**Status update (2026-08-27): all three steps this guide originally treated
as future, separately-approved decisions have since happened.** The system
is live and trading real money — Tradovate account LTE10089070250001 is
connected, the Lucid Trading LucidPro $100K evaluation is purchased and
active, and test mode is off (real trades with real P&L are executing daily;
account balance and per-trade P&L are visible on the Lucid dashboard). The
steps below are kept as an accurate record of how the live setup was built,
not as a still-pending plan — read "recommend paper/sim first" and "not
covered here" further down as the historical caution that was followed at
the time, not the current state.

**Correction (2026-09-25): the Lucid evaluation is simulated, not real
money.** Lucid's daily snapshot email for LTE10089070250001 states it
"reflects simulated performance for your LucidTest account". What's at risk
is the evaluation fee (failing means re-buying it), not trading capital.
Snapshot at the 2026-09-24 close: balance $100,099, total profit +$99,
minimum balance $97,178 (so $2,921 of drawdown room), profit target
$6,000, 9 days traded.

## Current live state and open issue (2026-09-25) — read this first

This supersedes the "Current live state (2026-08-28)" block in step 3 below.

**Only one strategy was live, and it is now PAUSED.**

| TradingView alert | Symbol | State |
|---|---|---|
| QuantC ORB Long MES v2 (validated) - Ghost (Accessible), id 5571966155 | MES1!, 1m | **Paused 2026-09-25 ~9:47 ET** (stopped, not deleted: settings and Ghost webhook kept). Expires 2026-10-05, extend on restart. |
| QC Trend DEMO test BUY / SELL (dry run), ids 5662901850 / 5662914432 | MNQ1!, 3m | Active, but every message carries `"test":true`, so no orders reach the broker. |
| QuantC ORB Long MNQ - OR-width stop DRAFT | MNQ1!, 1m | Inactive since 2026-08-28. **MNQ is not live**, whatever step 3 below says. |
| QuantC ORB Long (validated) - Ghost alerts, MES and MNQ | 1m | Inactive (last fired 2026-08-28 / 2026-09-02). |

**Why it was paused: every alert has fired ~10 minutes late since
2026-09-21.** From TradingView's alert log (54 alerts, 26 Aug to 25 Sep):

- Up to the 2026-09-18 close, every alert fired ~0-1 min after its signal
  bar closed.
- From the 2026-09-21 open on, every alert fires ~10 min after its signal
  bar closes. It's a constant delay across both symbols (MES 1m and MNQ 3m)
  and every script, and it started over the 19-20 Sep weekend.
- The delay is inside TradingView, before the webhook. The v2 script
  stamps each message with the signal bar's close time (`time_close`),
  e.g. `"time":"...13:48:00Z"`, while the log shows it `fired_at` 13:58.
  Ghost accepted every webhook immediately (HTTP 200).
- Confirmed on the chart 2026-09-25: the MES1! 1m chart shows TradingView's
  orange **"D" (delayed data)** badge, and the newest bar was ~10 min behind
  the chart clock (e.g. clock 13:46:10 UTC, newest bar ~13:36).
- Conclusion: the account's **real-time CME market data subscription
  lapsed** around 19-20 Sep. TradingView serves CME data 10 min delayed
  without it, and server-side alerts see the same delayed bars. No
  TradingView billing email was found in the connected Gmail, so the exact
  billing cause is unconfirmed.

**What it cost.** 2026-09-24 trade: signal entry 7746.75 → signal exit
7733.25 (−13.5pt, −$67.50 at signal prices). Lucid reported −$80 for the
session, so the delay plus commissions cost roughly $10-20 on that trade.
On 2026-09-21 the "session close" exit fired at 4:10pm ET, after the
regular session. For scale: RESULTS.md §2.7 shows just 2 ticks of adverse
exit slippage cuts evaluation survival from 77.8% to 64.3%. A 10-minute
delay is far outside what was tested, so the tested pass rates don't apply
while it persists.

**To resume (in this order):**

1. Renew TradingView real-time CME data: Profile → Settings and billing →
   Market data subscriptions → CME Group, **non-professional** (~$7/month
   as of Sep 2026; the professional rate is ~$548/month). Or click the
   orange "D" badge on the chart.
2. Reload the chart. Check the "D" badge is gone and the newest 1m bar
   matches the chart clock.
3. **Before 9:30 ET on a trading day** (never mid-session: the script can
   take a late entry, e.g. 2026-09-18 entered at 3:49pm ET), restart alert
   5571966155 (Alerts panel → Restart). Extend its expiry past 2026-10-05
   while you're there.
4. Check the fix with the first alert: `fired_at` should be within ~1 min
   of the `time` in its message. The DEMO MNQ alerts fire several times a
   day and give an earlier read.

**Restart plan (as of 2026-09-25):**

- Real-time CME data was renewed on 2026-09-25, mid-session. Not yet
  confirmed live: no alert had fired since the renewal (the last DEMO fire
  at 8:31 ET was still ~12 min late), and the alert stayed paused for the
  rest of that session.
- A Claude check-in is scheduled for **Mon 2026-09-28, 8:45 ET**. It reads
  the alert log for the DEMO fires since Sunday's 6pm ET reopen:
  - Lag ~1 min → restart 5571966155 and confirm `active=true`.
  - Lag still ~10 min → leave it paused and report; don't trade on
    delayed data.
- **Manual step:** the expiry (2026-10-05) has to be extended by hand on
  tradingview.com. The MCP can't edit alerts that have a webhook. The
  check-in reminds you.
- After the open, check the first MES alert's `fired_at` is within ~1 min
  of its message `time`.

## What the script does (and deliberately does not do)

File: [orb_long_ghost.pine](orb_long_ghost.pine)

- **Long side only.** 9:30am ET open, 15-minute opening range, enters on the
  first 1-minute close beyond the range high. The short side was tested and
  rejected (see RESULTS.md §1) — it is not in this script at all.
- **Exit = end of session (4:00pm ET), no stop-loss.** That's exactly what
  was tested. Nothing in this script exits early.
- **Position size defaults to 1 contract**, meant for a **micro** contract
  (MNQ or MES) — RESULTS.md §2.6 found full-size NQ/ES too large for a
  $100k account's real drawdown limit (44-45% pass rate vs. 89-99% for
  micros). You can raise this later, but re-check survivability first
  (a quick re-run of `ruin.py`, not a big task) before sizing up.
- **Ships with "Test mode" ON by default.** Every alert carries `"test":true`,
  which QuantCrawler Ghost's own docs describe as a full dry run — validated
  but nothing sent to the broker. You flip this off yourself, deliberately,
  when you're ready.

## 1. Add the script to TradingView

1. Open TradingView, open the Pine Editor (bottom panel → "Pine Editor").
2. Paste in the contents of `orb_long_ghost.pine`, click **Add to chart**.
3. Do this on **two separate chart tabs**: one showing the **MNQ** continuous
   futures symbol, one showing **MES**. Ghost routes by which webhook URL
   you use, so each instrument needs its own chart + alert (steps 2-3 below),
   not a shared one.
4. **Set the chart timeframe to 1 minute on both.** This is not optional —
   the opening range and signal detection were both computed on 1-minute
   bars. Any other timeframe is a different, untested rule, and the script
   will put a red warning label on the chart if you forget.

## 2. Create the TradingView alert (one per chart)

1. Right-click the chart → **Add alert**, or the alarm-clock icon.
2. **Condition**: pick the script ("QuantC ORB Long...") from the dropdown,
   then choose **"Any alert() function call"** — not a price/indicator
   condition. This matters: Ghost's own documentation is explicit that it
   wants alerts triggered this way, with the JSON already built into the
   message, not TradingView's `{{strategy.order.action}}`-style
   placeholders. This script builds the JSON itself, so "Any alert()
   function call" is the only correct choice here.
3. **Expiration**: open-ended (no expiration), so it keeps running.
4. **Webhook URL**: toggle "Webhook URL" on, paste the URL from Ghost (see
   step 3 below) — it looks like
   `https://quantcrawler.com/api/ghost/webhook/<ticker-id>?secret=<your-secret>`.
5. The **Message** box can be left as the default — this script sends its
   own JSON via `alert()`, so nothing needs to be typed here.
6. Save. Repeat for the second chart (MNQ and MES each get their own alert,
   pointed at their own Ghost ticker's webhook URL).

## 3. Set up the ticker in Ghost

For **each** instrument (MNQ, MES) in your QuantCrawler Ghost dashboard:

1. Create a ticker, connect it to your Tradovate account. **Recommend
   starting on Tradovate's paper/sim account**, not a live one — that's a
   separate decision from what this guide covers, but it's the obvious
   safer default while you watch this run for the first time. *(Historical
   note: this was the recommendation followed initially; the account has
   since moved to live, real-money trading — see the status update at the
   top of this file.)*
2. Copy that ticker's webhook URL (with the secret already embedded) into
   the matching TradingView alert from step 2.
3. If you want the script's `qty` field (currently 1) to actually control
   size, turn on **"Webhook Controls Contracts"** on the ticker. If you
   leave it off, Ghost uses whatever size is set on the ticker itself
   instead — set that to 1 there in that case.
4. Leave **"Use Stop Loss and Take Profit"** off. The script never sends
   `sl`/`tp` fields — the tested mechanism doesn't use a stop, so there's
   nothing to wire up here. **Confirmed live 2026-08-27**: checked directly
   in Ghost's ticker settings — MNQ's "Use Stop Loss & Take Profit" is
   unchecked, both distances show "(Disabled)," matching this instruction
   exactly. (An earlier note from this project's research had assumed MNQ
   was running a 10pt/20pt broker-side bracket; that is not what's
   configured now — either it was changed since, or the earlier note was
   inaccurate. Either way, the live ticker currently matches this guide.)

   ~~**This only applies to the current script (`orb_long_ghost.pine`).** The
   draft v2 script (`orb_long_ghost_DRAFT_mes_v2.pine` — MES only, still in
   review, not live) *does* send a stop-loss price on every entry, and Ghost
   needs **two** toggles on for that field to actually work, confirmed
   against QuantCrawler's own webhook docs:
     - **"Use Stop Loss and Take Profit"** — ON
     - **"Use Webhook SL/TP"** — ON

   Both are off/on together in Ghost's UI; missing either one means the
   `sl` price gets ignored and the position runs with no broker-side stop
   at all, silently. Only relevant if/when the v2 draft gets approved to
   replace this one — not something to change today.~~

   **Correction 2026-08-27 — this was not hypothetical, it was already
   happening.** The "MES(v2 Draft)" ticker turned out to already be live on
   the real account (LTE10089070250001), not a future decision — and its
   "Use Stop Loss and Take Profit" master toggle was OFF, meaning real
   trades were running with **zero broker-side stop**, silently, despite
   the v2 script being built around having one. Found and fixed the same
   day: the sub-toggles ("Use Webhook SL/TP" ON, "No Take Profit" ON) were
   already correctly configured, so only the master toggle needed enabling.

   **But that surfaced a second problem**: once enabled, Ghost warned that
   this ticker's actual TradingView alerts aren't sending `sl`/`tp` values
   at all (5 recent entries checked, none included them) — so "Use Webhook
   SL/TP" has nothing to use, and every trade silently runs on the
   **fallback fixed distance instead: 10pt stop / 20pt take-profit**. That
   is *not* the mechanism RESULTS.md §2.7 tested (a ~125pt price stop + a
   90-minute time exit, no take-profit target at all) — it's an untested,
   arbitrary bracket that happens to be better than no stop at all, kept in
   place for now as a bounded-risk interim measure. ~~**Still open**: the
   TradingView alert itself needs to be checked and fixed so it actually
   sends the script's real `sl` value — that hasn't been done yet.~~

   **Resolved 2026-08-28.** Root cause found: the TradingView alert feeding
   the "MES(v2 Draft)" ticker was condition-linked to the wrong script — the
   plain validated `orb_long_ghost.pine` (which never sends `sl`) — not to
   `orb_long_ghost_DRAFT_mes_v2.pine` (the actual draft, which was sitting
   on the chart correctly marked "NOT LIVE" and had never had an alert
   created for it at all). Fixed by:
   1. Creating a new TradingView alert directly on the draft script
      ("Any alert() function call"), pointed at the same "MES(v2 Draft)"
      Ghost webhook URL the old alert used.
   2. Repointing the old validated-script alert to the separate, unused
      "MES" (demo account) ticker instead of deleting it — so the plain
      mechanism is still available to watch/test, just not mixed in with
      the draft's signals.
   3. Confirmed via direct DOM inspection (not just the visible, truncated
      UI) that both webhook URLs match Ghost's actual ticker IDs exactly.

   **The same mis-wiring existed for MNQ**, discovered while fixing MES:
   `orb_long_ghost_DRAFT_mnq_orwidth.pine`-equivalent
   ("QuantC ORB Long MNQ - OR-width stop DRAFT, NOT LIVE" — the opposite-
   range stop from STOPLOSS_HYPOTHESIS.md) was also sitting correctly
   marked "NOT LIVE" with no alert of its own; the plain validated script
   was the only thing wired to the live MNQ ticker. Fixed the same way: new
   alert created directly on the MNQ draft script, pointed at the existing
   MNQ ticker's webhook URL; the old validated-script alert on MNQ1! was
   deleted (no second MNQ ticker existed to repoint it to, unlike MES).
   Ghost's MNQ ticker settings were updated to match MES's pattern — "Use
   Stop Loss & Take Profit" ON, "Use Webhook SL/TP" ON, "No Take Profit" ON
   (this mechanism has no take-profit target, only a stop) — so it now
   reads the per-trade `sl` value (the day's own opening-range low) the
   script sends, rather than a fixed distance.

   **Current live state (2026-08-28)** *(outdated: see "Current live state
   and open issue (2026-09-25)" at the top of this file; MNQ is no longer
   live and MES v2 is paused)*:
   - **MNQ** (ticker "MNQ", account LTE10089070250001): now running the
     OR-width-stop draft — entry unchanged, stop = opposite side of the
     day's opening range, no take-profit, exit at session close otherwise.
     This is STOPLOSS_HYPOTHESIS.md's tested mechanism (31.30%→54.30%
     survivability), still the weaker-tested of the two draft mechanisms
     (no slippage modeled on the stop fill) — see RESULTS.md §3's
     reconciliation for the full caveat.
   - **MES** (ticker "MES(v2 Draft)", account LTE10089070250001): now
     running the actual §2.7 mechanism — ~125pt price stop + 90-minute
     underwater time exit, no take-profit. This is the stronger-tested of
     the two (survived a realistic slippage haircut in testing).
   - **MES** (ticker "MES", demo account DEMO8790180): the plain validated
     no-stop mechanism, preserved here rather than deleted, not connected
     to real money.

   Chart hygiene also cleaned up the same day: each script had been
   accidentally left loaded on the wrong instrument's chart too (the MES
   draft was sitting on the MNQ1! chart and vice versa, each showing its
   own "wrong instrument, do not run" warning label — which is what
   surfaced this whole investigation), plus duplicate copies of each
   indicator on the same chart. Removed the wrong-instrument copies and one
   copy of each duplicate; the correctly-scoped instances (the ones the
   live alerts actually reference) were left untouched.

## 4. Watch it in test mode first

With the script's "Test mode" input left on (the default), every alert Ghost
receives is a dry run — logged, fully validated, nothing sent to the broker.
Check Ghost's **Logs** page over the next few trading days:

- Do the entry alerts show up around the expected times, with a sensible
  price?
- Does an exit alert show up every day a position was opened, right around
  4:00pm ET?

Only once that looks right — and only when you've decided you're ready —
would you go into the script's settings and switch **Test mode off**. That's
a deliberate, separate action for you to take when you choose to, not
something this guide does for you.

*(Historical note: this is the check that was done before going live. Test
mode is now off on the live tickers — see the status update at the top of
this file.)*

## What this guide originally deferred, and what's happened since

At the time this guide was written, three things were deliberately left as
separate, later decisions, each needing its own explicit go-ahead:

- ~~Purchasing the Lucid Trading LucidPro evaluation.~~ **Done** — purchased
  and active (account LTE10089070250001).
- ~~Connecting a live (non-paper) Tradovate account.~~ **Done** — connected
  and live.
- ~~Turning test mode off / letting this place real orders.~~ **Done** —
  test mode is off; real trades are executing with real money.

All three happened with the deliberate go-ahead this section originally
asked for, not silently. Nothing further is "not covered" at this point —
the system described in this guide is the one currently running live.
