# Noise-area breakout on MNQ: paper test (from 3 Oct 2026)

**Status: PAPER ONLY.** `noise_area_mnq_PAPER.pine` hard-codes `"test":true` on every alert. Nothing here touches the live MES v2 setup or the Lucid account.

## Files
- `noise_area_mnq_PAPER.pine`: TradingView indicator for the **MNQ 30-minute** chart (1-min loads too little history for the 14-session lookback; 30-min gives identical results). It sends `buy` / `sell` / `exit` alerts to Ghost and shows a paper P&L table on the chart.
- `paper_check.py`: an independent Python copy of the same rule.
  - `validate`: reproduces the 3 Oct research exactly (732 days, 1,155 trades, +10,338.2 pts on 5-yr NQ).
  - `yahoo`: what the script *should* have done over the last ~5 weeks (Yahoo MNQ=F 2-min bars).

## The rule (Zarattini, Barbon & Aziz 2024, paper settings, no tuning)
1. Band = max/min(09:30 open, yesterday's 16:00 close) × (1 ± average 14-session move from the open at that time of day).
2. At each half-hour check from 10:00 to 15:30 ET:
   - exit a long below max(upper band, VWAP), and exit a short above min(lower band, VWAP);
   - when flat, buy above the upper band or sell below the lower band.
3. Flat at 16:00. No fixed stop. 1 MNQ.

## Research basis and caveats
The research files are in `~/qc-demo-test/research-2026-10-03/`.
- Over 5 years, the rule was positive every year on NQ, at about +$51 per trading day per MNQ.
- **Not proven:** the newer-period gain rests on about 3 big days, the rule failed on ES and YM, and it was the best of about 8 combinations tried.
- Worst day was about −$1,300 and worst drawdown about −$4,900 at 1 MNQ. Both are larger than the Lucid cushion.

## Set-up steps (each needs the user's yes)
1. Paste the script into TradingView's Pine Editor and add it to an **MNQ1! 30-minute** chart. Check that it compiles and that the table says "chart OK".
2. Compare the chart's trades over its loaded history with `python paper_check.py yahoo` for the same dates.
3. In Ghost, create a **separate MNQ test ticker** with these settings:
   - test mode;
   - buy and sell allowed;
   - more than 1 trade a day;
   - "Use Stop Loss and Take Profit" OFF.

   Do **not** reuse the live MES v2 ticker.
4. Create a TradingView alert on that chart using "Any alert() function call", with the webhook pointing at the new Ghost ticker.
5. Pause on CME half-days (27 Nov, 24 Dec). The session-close exit may not fire on those days.

## Paper-test question for the 30 Oct review
The question is not "did it make money in 4 weeks?". It is: do Ghost's test signals match `paper_check.py` on the same days, and did the pipeline run cleanly?
