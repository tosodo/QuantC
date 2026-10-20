# Futures prop firm rules survey ($50K / $100K tiers)

**Retrieval date:** 2026-10-20. Research only, no code changes.

## How this was gathered (read first)

- Direct page fetching (WebFetch, curl) was blocked in this environment (DNS failure / sandbox denial). **No firm page was opened directly.**
- All facts below come from **search-engine result summaries**. Searches restricted to each firm's own domain (help centers, product pages) returned the official article titles and snippets, so tagged OFFICIAL rows rest on a snippet of the firm's own page, not on a full read. Source ages shown by the search tool were typically 0 to 90 days. Exact publish dates are not visible, so no row has a firm date.
- Tags:
  - **OFFICIAL**: snippet from the firm's own help center or product page.
  - **THIRD-PARTY**: review sites and affiliate blogs.
  - **UNCERTAIN**: sources conflict, or the page may be legacy.
- Anything not found is written `unknown`.
- Third-party pages conflict heavily with each other and with official pages. Treat every number as "verify before paying".

## Context check on the strategy (important)

The brief gives about $820/yr per 1 MES. Every target below ($3,000 at 50K, $6,000 at 100K) would take roughly 4 to 7 years at 1 MES. Passing in any reasonable time needs about 8 to 10+ MES. The drawdown scales with size too: the $2,066 worst closed-trade drawdown at 1 MES would be about $16K to $20K at 8 to 10 MES, far above a $2,000 to $3,000 limit.

If the $2,066 figure is already at the intended trading size, ignore this. If not, **the binding constraint is size versus drawdown, not any firm's rule set.** This survey does not resolve that.

## Rules table

Abbreviations:
- EOD = end-of-day trailing drawdown (DD).
- MLL = max loss limit.
- DLL = daily loss limit.
- Fee-to-first-payout is my rough arithmetic from listed fees, assuming a first-attempt pass in about 1 month. Treat it as an estimate.

### Lucid Trading

| Field | LucidPro 100K (50K where different) | Source / confidence |
|---|---|---|
| Fee | One-time purchase, no subscription. Exact eval price: unknown. Reset about $170 for a 100K LucidPro reset (promos $99 to $132 seen). | [Simulated Account Fees](https://support.lucidtrading.com/en/articles/11404620-simulated-account-fees), [reset category](https://lucidtrading.com/product-category/reset/) / OFFICIAL (reset price UNCERTAIN) |
| Target | $6,000 (50K: $3,000) | [Product page](https://lucidtrading.com/product/lucidtest-100k/) / OFFICIAL. Matches the user's figure. |
| Drawdown | EOD trailing from the highest closing balance. MLL $3,000 (50K: $2,000). Locks once the balance passes the "trail balance" (50K: $52,100). In funded, the live-stage MLL locks at $100. Exact lock level for the 100K eval: unknown. | [LucidPro Drawdown](https://support.lucidtrading.com/en/articles/12890136-lucidpro-drawdown), [LucidPro Funded](https://support.lucidtrading.com/en/articles/12890069-lucidpro-funded-account) / OFFICIAL |
| Daily loss limit | Optional, chosen at purchase, cannot be changed later. Fixed DLL is $1,800 at 100K and $1,200 at 50K, and is a soft breach (pauses the day only). Funded switches to a scaling DLL of 60% of peak EOD profit after the trail balance. DLL off costs more. | [LucidPro DLL](https://support.lucidtrading.com/en/articles/12890122-lucidpro-daily-loss-limit), [Customization](https://support.lucidtrading.com/en/articles/16226068-lucidpro-customization) / OFFICIAL |
| Consistency | Eval: none. Funded: 40% (35% for accounts bought before 2025-11-28), best day ≤ 40% of cycle profit. Not applied after promotion to live. | [LucidPro Consistency](https://support.lucidtrading.com/en/articles/12890109-lucidpro-consistency-percentage) / OFFICIAL |
| Min days / time limit | Unknown (third parties say no minimum days and no time limit, UNCERTAIN) | / UNCERTAIN |
| Contracts | 6 mini or 60 micro at 100K (50K: 4 mini or 40 micro). No scaling plan. | Product page / OFFICIAL |
| Overnight / news | Unknown | / unknown |
| Payout split | 90/10 | [LucidPro Payouts](https://support.lucidtrading.com/en/articles/12890092-lucidpro-payouts) / OFFICIAL |
| Payout min / frequency / cap | Min request $500. Min cycle profit $750 at 100K ($500 at 50K). Buffer = initial MLL + $100. Caps by size and payout number: unknown. Cycle length: unknown (third parties say 3-day cycles). | Same page / OFFICIAL (cycle length UNCERTAIN) |
| Simulated funded? | Yes (sim funded, then a "live" structure with real capital). Pages: [New Live Structure](https://support.lucidtrading.com/en/articles/16558826-new-live-structure), [Legacy Live](https://support.lucidtrading.com/en/articles/13425130-legacy-live-structure). | OFFICIAL |
| Fee to first payout (est.) | Unknown eval price, so cannot compute. Reset $99 to $170. | UNCERTAIN |
| Automation | Help center "Other Trading Activities" says automated systems and trade copiers are permitted, with the trader responsible for errors. HFT and microscalping (more than 50% of profit from trades held 5 seconds or less) are prohibited. **Conflict:** the LucidDirect account agreement says custom or algorithmic software needs written approval. Webhook-specific rule: unknown. | [Other Trading Activities](https://support.lucidtrading.com/en/articles/11404728-other-trading-activities), [LucidDirect agreement 2025-05-19](https://lucidtrading.com/wp-content/uploads/2025/05/LucidDirect-Account-Agreement-5-19.pdf) / OFFICIAL, conflicting |
| Multi-account / copy | Max 10 eval+funded accounts per household, at most 5 funded. Copiers allowed. Cross-account hedging is prohibited. | [Max accounts](https://support.lucidtrading.com/en/articles/11404617-maximum-number-of-accounts) / OFFICIAL |

**Other Lucid products** ([LucidFlex funded](https://support.lucidtrading.com/en/articles/12945795-lucidflex-funded-account), [LucidDaily](https://support.lucidtrading.com/en/articles/15996664-luciddaily-evaluation), LucidBlack, LucidDirect), all OFFICIAL titles with UNCERTAIN details:
- LucidFlex: EOD, MLL $2,000 (50K) and $3,000 (100K), target $6,000 at 100K. Eval consistency 40% by default, 50% as a paid add-on. DLL optional, which changes price and payout schedule. One product page showed a $1,800 DLL against the help page's "optional".
- LucidDaily: exists, details unknown.

### Topstep

| Field | Trading Combine (Standard / No-Activation-Fee path) | Source / confidence |
|---|---|---|
| Fee | Monthly subscription. Standard: $49 (50K) and $99 (100K) per month plus a **$149 activation fee** per XFA. No-Activation-Fee path: $95 (50K) and $149 (100K) per month, no activation fee. A marketing page showed different numbers ($85 and $129). | [Pricing and Payment Questions](https://help.topstep.com/en/articles/14289835-topstep-pricing-and-payment-questions) / OFFICIAL (checkout may differ) |
| Reset | Equals the monthly price (e.g. $99 for 100K Standard). Max 2 resets per account per day. Back2Funded reactivation after losing an XFA: $599 (50K) and $699 (100K). | Same page / OFFICIAL |
| Target | $3,000 (50K), $6,000 (100K) | [Combine Parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters) / OFFICIAL |
| Drawdown | EOD trailing MLL: $2,000 (50K), $3,000 (100K). Trails until it reaches the starting balance, then stops. | [What is the MLL](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit) / OFFICIAL |
| Daily loss limit | Optional: $1,000 (50K), $2,000 (100K). Breach flattens positions and pauses until the next session. | [DLL page](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account) / OFFICIAL |
| Consistency | Combine: best day below 55% of total profit, a hard line. If exceeded, you keep trading until it is met. XFA: Standard path needs 5 winning days of $150+. Consistency path needs 3 trading days and best day ≤ 40% of net profit. | [Consistency](https://help.topstep.com/en/articles/8284208-consistency-at-topstep), [Payout Policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy) / OFFICIAL (a 50% figure appears in third-party pages) |
| Min days / time limit | No minimum days stated in the sources. No time limit while subscribed. | THIRD-PARTY / UNCERTAIN |
| Contracts | 10 mini or 100 micro (100K), 5 mini or 50 micro (50K) | Combine Parameters / OFFICIAL |
| Overnight / news | Unknown from sources (the account must be flat at the session end, a general Topstep rule not verified here) | unknown |
| Funded DD / buffer | XFA MLL starts at -$2,000 (50K) and trails up; locks at $0 once the balance reaches +$2,000. **Each payout resets the MLL to $0 and restarts the day count.** | [XFA Parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters) / OFFICIAL |
| Payout | 90/10. Min request $125. Cap shown as $2,000 to $5,000 depending on size on the current help page; older pages said $5,000 to $6,000. | [Payout Policy](https://help.topstep.com/en/articles/8284233-topstep-payout-policy) / OFFICIAL (cap UNCERTAIN) |
| Simulated funded? | Yes: the XFA is simulated. Live Funded Account comes after 30 winning days of $150+ on the XFA, per the Payout Policy snippet. | Payout Policy / OFFICIAL |
| Fee to first payout (est., 100K Standard, 1 month) | $99 + $149 = about $248. No-Activation-Fee path: about $149. Each extra month adds $99 to $149. | Estimate |
| Automation | **Allowed with conditions in the Combine and XFA** (no Topstep support, no exceptions for malfunctions). **Not allowed on the Live Funded Account** (API Gateway unavailable there). Bans software or ultra-high-speed systems that abuse the platform and algorithms built to exploit sim fills. | [Prohibited Strategies](https://help.topstep.com/en/articles/10305426-prohibited-trading-strategies-at-topstep), [Combine Parameters](https://help.topstep.com/en/articles/8284197-trading-combine-parameters), [XFA Parameters](https://help.topstep.com/en/articles/8284215-express-funded-account-parameters) / OFFICIAL (via snippet) |
| Multi-account / copy | All accounts must sit under one Topstep profile. Account stacking (repeatedly blowing one account then switching) is prohibited. | Prohibited Strategies / OFFICIAL |

Topstep Labs (a newer product: one-time $75 or $499 fee, static or trailing MLL, mandatory DLL, $8,000 payout cap on 50K static) is described on [one help page](https://help.topstep.com/en/articles/15520357-topstep-labs). Full terms: unknown. OFFICIAL, thin.

### Apex Trader Funding

| Field | EOD evaluation (post-March 2026 products) | Source / confidence |
|---|---|---|
| Fee | One-time evaluation fee with 30 days of access. Current 50K and 100K prices: unknown (shown only in the checkout selector). PA activation fee within 7 days of passing, or $0 on "No Activation Fee" evaluations (50K EOD qualifies; 100K qualifies only as a single purchase). | [Evaluation Plan Fees](https://apextraderfunding.com/help-center/billing/evaluation-plan-fees-and-access-explained/), [No Activation Fee](https://apextraderfunding.com/help-center/uncategorized/no-activation-fee-evaluations/) / OFFICIAL |
| Reset | None. A failed evaluation means buying a new one. | Evaluation Plan Fees / OFFICIAL |
| Target | 50K: $3,000. 100K: unknown. | [Apex homepage](https://apextraderfunding.com/) / OFFICIAL (50K only) |
| Drawdown | EOD trailing: $2,000 (50K), $3,000 (100K). On Rithmic and Wealthcharts evals it stops at the profit-target level; on Tradovate evals it keeps trailing indefinitely. | [EOD Drawdown Explained](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-drawdown-explained/) / OFFICIAL |
| Daily loss limit | 50K: $1,000 shown on the homepage. 100K: unknown. | Homepage / OFFICIAL |
| Consistency | Payout stage: no single profitable day may be 50% or more of profit since the last payout. Legacy accounts: 30%. | [EOD Payouts](https://apextraderfunding.com/help-center/eod-trailing-drawdown-accounts/eod-payouts/) / OFFICIAL |
| Payout | Min 5 qualifying days at ≥$250 (50K), min payout $500, 50K caps from $1,500 for the first payout. Split shown as 100%. | EOD Payouts / OFFICIAL (split UNCERTAIN) |
| Min days / time limit | Min days: unknown. Time: 30-day access per purchase. | OFFICIAL / partly unknown |
| Overnight / news | Unknown | unknown |
| Simulated funded? | Unknown (PA is commonly described as sim, unverified). | unknown |
| **Automation** | **Strictly prohibited on PA and live accounts**: AI, bots, algorithms, fully automated systems, set-and-forget. Violations: closure and forfeiture. Older article allowed semi-automated software if actively monitored. Webhook-driven execution should be treated as prohibited. | [PA and Compliance](https://support.apextraderfunding.com/hc/en-us/articles/31519788944411-Performance-Account-PA-and-Compliance), [Prohibited Activities](https://support.apextraderfunding.com/hc/en-us/articles/40463668243099-Prohibited-Activities) / OFFICIAL |
| Copy / multi | No copy trading service or trade mirroring may manage PA or Live accounts, per the older consistency article. | [Consistency article](https://support.apextraderfunding.com/hc/en-us/articles/4404875002139-What-are-the-Consistency-Rules-for-PA-and-Funded-Accounts) / OFFICIAL (older page) |

**Verdict for this strategy: effectively excluded because of the automation ban.**

### Tradeify

| Field | Select 50K (100K by analogy, unconfirmed) | Source / confidence |
|---|---|---|
| Fee | Select 50K $165 (40% consistency) or $205 (50% add-on). One-time vs monthly: unknown (third parties vary). 100K price: unknown. | [Pricing Reference](https://help.tradeify.co/en/articles/14369021-tradeify-pricing-reference) / OFFICIAL |
| Reset | 50K: $109 (40% version), $135 (50% add-on). Up to 10 resets in a 30-day window. | Pricing Reference / OFFICIAL |
| Target | 50K: $3,000. 100K: $6,000 per third parties. | [Select Eval](https://help.tradeify.co/en/articles/12853921-select-evaluation-accounts) / OFFICIAL (50K), THIRD-PARTY (100K) |
| Drawdown | EOD trailing, $2,000 (50K). 100K: unknown (third parties imply $3,000). Where it stops in eval: unknown. | Select Eval / OFFICIAL (50K) |
| Daily loss limit | None in eval. Funded depends on the payout path (Flex vs Daily). | [Select Flex and Daily](https://help.tradeify.co/en/articles/12853966-select-flex-and-select-daily-payout-policies) / OFFICIAL, thin |
| Consistency | Eval: 40% (50% add-on). Funded Select: none. (Third parties cite 35% for Growth funded and 20 to 30% for Lightning.) | [Consistency Rule](https://help.tradeify.co/en/articles/10468320-rules-consistency-rule) / OFFICIAL |
| Min days | 3 (2 with the 50% add-on). Growth: 1. Time limit: unknown. | OFFICIAL (Select), `unknown` (time) |
| Contracts | Unknown from sources. A Flex one-contract cap while funded appears in third-party text. | THIRD-PARTY |
| Payout | 90/10. Funded Flex (5 profitable days of ≥$100, 7-day cycle) or Daily (up to 2x cycle profit, cap $1,000/$1,500/$2,500 for 50K/100K/150K per a Tradeify blog). Choice is permanent per account. Caps differ across sources. | Tradeify blog, [Tradeify tradeify.co posts](https://tradeify.co/post/prop-firm-payout-rules-every-funded-trader-should-know) / OFFICIAL blog, UNCERTAIN |
| Simulated funded? | Unknown from the sources (sim is standard in the industry; unverified). | unknown |
| Fee to first payout (est., 50K) | $165 + 5 to 7 days = about $165 for a first-attempt pass. | Estimate |
| Automation | **Personal bots allowed with conditions.** Trader must prove sole ownership. The same bot must not run across multiple firms. No HFT. More than 50% of profit must come from trades held over 10 seconds. Tradeify may request documentation or a live video of the bot being enabled. Webhook specifically: unknown. | [Guidelines for Traders](https://help.tradeify.co/en/articles/10468318-guidelines-for-traders), [Funded Trader Agreement](https://tradeify.co/funded-trader-agreement), [Risk and Compliance FAQ](https://help.tradeify.co/en/articles/17069653-risk-compliance-guidelines-faq) / OFFICIAL via snippet |
| Copy / multi | Copy trading limited to accounts you personally own. | Same / OFFICIAL |

### Take Profit Trader (TPT)

| Field | PRO 50K (100K: mostly unknown) | Source / confidence |
|---|---|---|
| Fee | About $170/month list, around $102 with common promos, billing stops once passed. Activation fee: $130 (or $0 on promos; conflicting). | [TPT vs Topstep](https://takeprofittrader.com/blog/take-profit-trader-vs-topstep) / OFFICIAL blog, UNCERTAIN |
| Reset | 50K $99, 100K $169 (one post). Another post shows $100 and a $649 PRO reset. Up to 3 PRO resets. | [Reset pricing post](https://takeprofittrader.com/blog/test-reset-pricing-update-our-biggest-flash-sale-ever-nofee-50) / UNCERTAIN |
| Target / DD | 50K: $3,000 target, about $2,000 EOD trailing in eval. 100K: unknown. | TPT blog / OFFICIAL blog |
| Daily loss limit | None | TPT blog / OFFICIAL blog |
| Consistency | Eval: 50% best-day rule, which is not a fail (keep trading until met). Funded: none. (One review table shows none at any stage, which conflicts.) | [FAQ](https://try.takeprofittrader.com/TPT-FAQs-nf40-4-0725) / OFFICIAL blog, UNCERTAIN |
| Min days | 3 (cut from 5). Time limit: none stated. | [3-day evals](https://takeprofittrader.com/blog/3-day-evals) / OFFICIAL blog |
| Funded DD | PRO: **intraday trailing** per TPT's payout-rules post. PRO+: EOD. A buffer must be exceeded before standard withdrawals. | [Prop Firm Rules post](https://takeprofittrader.com/blog/prop-firm-rules) / OFFICIAL blog |
| Payout | PRO 80/20, day-1 and daily withdrawals, no minimum profitable days. Payouts under $250 carry a $50 fee. PRO+ (live) 90/10. | Same / OFFICIAL blog, THIRD-PARTY (fee) |
| Simulated funded? | PRO is simulated; PRO+ is live capital per marketing. | OFFICIAL blog |
| Automation | **Unclear.** The Terms of Service bar access to resources by "automated, unethical or unconventional means" and put full responsibility for copiers and third-party automation on the trader. No explicit bot ban or permission found. Ask in writing. | [Terms](https://takeprofittrader.com/terms) / OFFICIAL, UNCERTAIN |
| Copy / multi | Copying across up to 5 PRO accounts per the FAQ (3 per a promo page). | FAQ / OFFICIAL, conflicting |

### MyFundedFutures (MFFU)

| Field | Rapid / Rapid EOD / Pro | Source / confidence |
|---|---|---|
| Fee | Rapid 50K about $125 (promo), standard price unclear ($159 appears). Pro price: unknown. Monthly vs one-time: unknown. | [Rapid](https://myfundedfutures.com/plans/rapid), [How it works](https://myfundedfutures.com/how-it-works) / OFFICIAL, UNCERTAIN |
| Reset | Rapid: no reset (new evaluation required). | [Rapid 50K](https://help.myfundedfutures.com/en/articles/13134709-rapid-plan-50k-a-comprehensive-look) / OFFICIAL |
| Target / DD | 50K: $3,000 / $2,000 EOD. 100K: $6,000 / $3,000. Max contracts: Rapid 5 mini (50K), 8 mini (100K); Pro 3 mini (50K), 6 mini (100K). | [Rapid](https://myfundedfutures.com/plans/rapid), [Pro](https://myfundedfutures.com/plans/pro) / OFFICIAL, with conflicts |
| Daily loss limit | None | Plan pages / OFFICIAL |
| Consistency | Rapid eval 50% (Rapid EOD eval 30%, 4-day min); none once funded. Pro: none funded. | Rapid 50K help page / OFFICIAL |
| Funded DD | **Rapid funded: intraday trailing**, which stops moving once the buffer is built (starting balance + $100). Buffers $2,100 (50K) and $3,100 (100K). Pro: EOD. Rapid EOD variant exists. | Rapid 50K help page / OFFICIAL |
| Payout | Rapid: 90/10, as often as every 24 hours. Pro: 14 days from first trade, $1,000 min, up to $100K total sim payouts per user, live-capital path after 3 consecutive payouts. | [Payout overview](https://help.myfundedfutures.com/en/articles/13745661-payout-policy-overview-best-and-fastest-prop-firm-payouts) / OFFICIAL |
| Simulated funded? | Yes ("sim funded") | OFFICIAL |
| Automation | **Allowed with conditions**: tailored settings, must not exploit sim fills, HFT not allowed. Live-capital automation must follow CME rules. | [Fair Play](https://help.myfundedfutures.com/en/articles/8444599-fair-play-and-prohibited-trading-practices) / OFFICIAL |
| Copy / multi | Copy trading allowed across your own accounts per the help article. The Fair Play article bars copying other traders. Older Terms bar coordinated multi-account hedging or mirroring that gives an unfair advantage. | [Copy trading](https://help.myfundedfutures.com/en/articles/10771500-copy-trading-at-myfundedfutures) / OFFICIAL, partly conflicting |
| Fee to first payout | Unknown | unknown |

### Bulenox

| Field | Fast Track / Master | Source / confidence |
|---|---|---|
| Fee | Unknown from sources. See [Accounts and Pricing](https://bulenox.com/accounts-pricing). | unknown |
| Drawdown | 50K Option 1: $2,250 trailing, 7 mini. Option 2: $2,250 EOD + $1,200 DLL, 4 mini, no scaling. 100K Option 1: $4,000 trailing, 12 mini. Option 2: $4,000 EOD + $2,500 DLL, 8 mini. Both options: drawdown stops at starting balance + $100. DLL on Option 2 stays for the account's life. | [Fast Track](https://bulenox.com/help-center/fast-track) / OFFICIAL |
| Target / consistency / days | Unknown. A consistency rule exists at the payout stage (figure not captured; 40% unconfirmed). | [FAQ](https://bulenox.com/faq) / OFFICIAL, number unknown |
| Payout | 90/10. Fast Track and Momentum: processed daily. Master: Wednesdays. Min and caps: unknown. | FAQ / OFFICIAL |
| Automation | **Allowed with conditions**: user-built tools for personal use only. Third-party API or composite connections add a fee of about $100/month. Sign-up terms say third-party algorithms need management review and approval before use. Scalping algorithms and rapid-fire algorithmic trades prohibited. | [FAQ](https://bulenox.com/faq), sign-up terms / OFFICIAL via snippet |

### Alpha Futures

| Field | Zero / Standard / Advanced | Source / confidence |
|---|---|---|
| Fee | Standard 50K about $129/month, no activation fee. Others: unknown. | [Alpha blog](https://alpha-futures.com/posts/best-futures-prop-firms-2026-a-traders-guide) / OFFICIAL blog |
| Drawdown | EOD trailing MLL on all plans. Zero MLL: $2,000 (50K), $3,000 (100K). Standard opening limit $2,000 (50K) and $3,000 (100K). Advanced $1,750 (50K) and $3,500 (100K). | [Alpha homepage](https://alpha-futures.com/) / OFFICIAL blog, UNCERTAIN |
| Consistency | Eval: Zero none, Standard 50%, Advanced 40%. Qualified: Zero and Standard 40% between payout requests, Advanced none, Direct 20%. | Alpha blog / OFFICIAL blog |
| Payout | 90/10. Up to 4 requests per month after 5 winning days of ≥$200. Qualified caps about $1,500 (50K Zero), $3,000 (50K Standard), $15,000 (Advanced). | [Payout Policy](https://help.alpha-futures.com/en/articles/9492051-payout-policy) / OFFICIAL |
| Automation | **Mixed.** Prohibited Trading Practices restrict high-frequency systems (over 100 trades per day) and exploiting no-slippage fills. Terms allow "semi-automated" trading if actively monitored. The Copy Trading help article says "Automated, Group, and Reverse Trading are strictly prohibited". Treat full automation as **not permitted** until Alpha confirms in writing. | [Prohibited Practices](https://help.alpha-futures.com/en/articles/9508585-prohibited-trading-practices), [Copy Trading](https://help.alpha-futures.com/en/articles/10573989-copy-trading) / OFFICIAL, conflicting |
| Targets, min days, time | Unknown | unknown |

### FundedNext Futures

| Field | Rapid Pro / Rapid Daily / Legacy | Source / confidence |
|---|---|---|
| Fee | Rapid 50K about $149.99 to $169.99 (sources differ), $109.99 with the DLL add-on. One page says Rapid and Bolt stopped being sold or reset from 2026-07-10, so **availability is UNCERTAIN**. | [Rapid Pro rules](https://helpfutures.fundednext.com/en/articles/17229677-fundednext-futures-rapid-pro-challenge-all-rules), [Prices](https://helpfutures.fundednext.com/en/articles/15053874-what-are-the-available-account-sizes-and-their-prices-in-fundednext-futures) / OFFICIAL, UNCERTAIN |
| Target / DD | 50K: $3,000 / $2,000 EOD trailing. 100K: unknown. | [Trading objectives](https://fundednext.com/general-rules/futures/trading-objectives) / OFFICIAL |
| Daily loss limit | Rapid Pro: none by default (add-on $1,000 at 50K). Rapid Daily: $1,000 at 50K (soft). | OFFICIAL |
| Consistency | Legacy and Flex challenge: 40% rule (target gets recalculated). Legacy funded: none, uses Benchmark Days. | [Consistency](https://helpfutures.fundednext.com/en/articles/17230245-is-there-any-consistency-rule-to-be-followed-in-the-fundednext-futures-challenge-fundednext-account) / OFFICIAL, partly conflicting |
| Payout (Legacy) | 5 Benchmark Days and ≥$500 profit; min request $250; capped at 50% of profit and $6,000 until 30 Benchmark Days. | [Legacy rules](https://helpfutures.fundednext.com/en/articles/17229581-fundednext-futures-legacy-fundednext-account-all-rules) / OFFICIAL |
| Automation | **Allowed** in challenge and funded futures accounts (no setup support; latency abuse and order flooding prohibited; the firm may request the system for review). The general EA page limits EAs on MT4/MT5 and cTrader, unclear whether it applies to futures. | [Futures automated systems FAQ](https://helpfutures.fundednext.com/en/articles/14298560-is-the-usage-of-automated-trading-systems-eas-and-bots-allowed-in-fundednext-futures), [Challenge terms](https://fundednext.com/futures-challenge-terms) / OFFICIAL |
| Everything else | Unknown | unknown |

### Elite Trader Funding (ETF)

| Field | Static / EOD / others | Source / confidence |
|---|---|---|
| Fee / reset | Auto-renews every 30 days until passed or cancelled. Reset $47 on most evals (not Fast Track). A $297 figure appears for one Static product. Elite Sim-Funded activation $87/month or one-time. | [Static](https://elitetraderfunding.com/static/), [Products](https://elitetraderfunding.com/products/) / OFFICIAL, UNCERTAIN |
| Static drawdown | The floor never moves. Example given: **100K with only a $625 max loss** and a $2,000 target. Static 50K terms: unknown. | Static page / OFFICIAL |
| Requirements | Min 5 trading days. Hit target. Flatten 1 minute before close. No max time. No DLL on static. | Static page / OFFICIAL |
| Payout | Safety net = max DD + $100 realized profit. Up to 100% sim split, total sim payouts capped at $25,000 per trader (another page mentions $150K lifetime). Live Elite 80/20. 35% give-back rule after 20% profit. | [Elite Sim-Funded](https://elitetraderfunding.com/elite/?type=static) / OFFICIAL, UNCERTAIN |
| Automation | **Unknown** (not found) | unknown |

## Ranked answer: structurally easiest to pass and get paid

This is based on structure only. None of these rule sets fixes the size-versus-drawdown issue noted at the top. Roughly 29% win rate and 1 trade per day means P&L is lumpy: a few big winners and many small losers.

**1. Topstep (Combine, then XFA)**
- Evidence quality is the best of the group: official help-center pages, with figures mostly agreeing.
- The 100K target-to-MLL ratio is 2:1 ($6,000 / $3,000), the same as everyone else. The edge is in the surrounding rules.
- The Combine consistency rule (55%) is the most lenient of the eval consistency rules found. It is a delay, not a fail.
- No time limit, no minimum days.
- Automation is explicitly allowed in Combine and XFA. The catch is that it is not allowed on the Live Funded Account, so the ceiling is the XFA (sim) payouts.
- The XFA MLL trails then locks at $0, which is good. But **each payout resets the MLL to $0**, so the buffer after a payout is zero. A low-variance strategy must keep a profit cushion by choosing payout size.
- A Standard-path payout needs 5 winning days of $150+, which a 29%-win-rate strategy at 1 trade per day will take a while to produce.
- Cost is low (about $150 to $250 to first payout), but monthly billing accrues while you grind a slow edge.

**2. Lucid (LucidPro, DLL setting chosen deliberately)**
- No consistency rule in evaluation, which suits a lumpy strategy best.
- Explicit help-center permission for automated systems. Fee is one-time, so there is no bleed while the edge accumulates.
- Funded stage: EOD trailing with a soft DLL, 90/10 split. The funded 40% consistency rule per payout cycle, with a $750 minimum cycle profit at 100K, is the hardest payout hurdle in this shortlist for a strategy whose profits come from a few days.
- Weak evidence: much of the funded and payout detail is stale or conflicting. The LucidDirect agreement requires written approval for algorithmic software, which conflicts with the help-center wording. Get approval in writing.

**3. Tradeify Select**
- Funded stage has no consistency rule.
- Automation is allowed for personal bots, with sole-ownership proof, a single-firm requirement, no HFT, and a hold-time test (more than 50% of profit from trades held over 10 seconds, easy for an opening-range strategy).
- Evaluation has a 40% (or 50% add-on) consistency rule, which is the main risk for lumpy returns, so the 50% add-on costs a little more but matters.
- 100K details are thin: target, drawdown and price are THIRD-PARTY only.

**Honorable mention: Take Profit Trader.** Best funded-stage payout structure (no funded consistency, daily payouts), but PRO is intraday trailing and the automation stance is unclear. **MyFundedFutures Pro** (EOD, no funded consistency, but a 14-day cycle and $1,000 minimum) and **Rapid** (intraday trailing in funded) are weaker fits.

**Excluded or poor fits**
- Apex: automation is prohibited.
- Alpha: automation likely prohibited.
- Bulenox: automation allowed, but approval is required, fees are unknown, and the plan details are incomplete.
- Elite Trader Funding: static drawdown is attractive in principle, but the one visible 100K static example has a $625 max loss, and automation policy is unknown.

**Where the evidence is weak**
- No page was read in full.
- Many 100K numbers are inferred from 50K plus a 1.5x pattern.
- Prices change often.
- No firm's rules were found that name TradingView webhooks to Tradovate specifically.
- Static-drawdown products for the large tier were not found at all.

## Verify yourself (highest-value checks)

1. **Automation, in writing from support, naming your exact route (TradingView alert, webhook, Tradovate)**, for Topstep, Lucid and Tradeify. Check Lucid's LucidPro terms versus the LucidDirect agreement; Topstep's Live exclusion; Tradeify's sole-ownership and one-firm limits.
2. **Lucid LucidPro 100K**: evaluation price, whether the DLL is on or off in your account, the trail-lock balance, current funded consistency (35% vs 40% by purchase date), payout cycle length and caps.
3. **Topstep**: Combine consistency (55% vs 50%), XFA payout cap table, and that the MLL resets to $0 after each payout.
4. **Tradeify Select 100K**: target, MLL, price, contract cap, whether the eval is monthly or one-time, and the funded payout path choice (Flex vs Daily), which is permanent.
5. **Whether each firm's sim-funded account is truly simulated** and what share of payouts is actually paid (not stated clearly in any source).
6. **Position-size arithmetic**: confirm the contract count needed to hit a $3,000 to $6,000 target in your time window, and that your worst drawdown at that size is below the MLL (and below any soft DLL, if enabled).
