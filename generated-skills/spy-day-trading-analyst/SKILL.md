---
name: spy-day-trading-analyst
description: A cold, honest SPY/SPX day-trading analysis toolkit specialized in intraday reversals. Detects multi-signal reversal setups across timeframes (1m-1D), scores them by confluence, and backtests them with realistic costs and no lookahead so you see the REAL edge after slippage and commissions. Includes a reversal behavior playbook and a news/macro-catalyst module. Use when analyzing SPY intraday structure, validating a reversal idea with an honest backtest, ranking current setups, or planning around macro events. Reports edges and probabilities from data; it does not place trades and never promises win rates.
---

# SPY Day-Trading Analyst

A focused, no-nonsense toolkit for studying **SPY** (and SPX/ES) intraday
behavior, specialized in **reversals** — the thing you asked to master. It is
built to be *cold and calculating*: it tells you what the data says, including
when the answer is "this has no edge."

## The honest framing (read this first)

This skill will not lie to you, because lying is how traders go broke. So, up
front:

- **No "90% accuracy."** No real system hits 90% directional accuracy on SPY
  intraday. The confluence score (0–100) this tool produces is **setup quality**
  — how many independent reversal signals line up — **not** a probability of
  profit. The only honest estimate of your edge is the *backtested win rate and
  expectancy after costs*, which is usually a far more modest (and far more
  real) 40–55% win rate with positive expectancy from good risk/reward.
- **It does not place trades.** There is no broker connection and there never
  will be. Your hand is on the button.
- **It can't watch a live chart by itself.** It analyzes historical bars (CSV or
  yfinance) and on-demand news. For live chart access, pair it with the
  TradingView MCP bridge running on *your own machine* (see README).
- **Backtests can still fool you.** This engine is built to avoid the classic
  traps (lookahead, ignored costs, optimistic fills), but past performance never
  guarantees future results. Treat every result as a hypothesis, not a promise.

SPY day trading carries a **real risk of loss**. This is analysis/education
tooling, **not financial advice**.

## What's in the box

| Component | File | What it does |
|---|---|---|
| Indicator toolkit | `indicators.py` | Pure-stdlib RSI, MACD, ATR, Bollinger, VWAP, stochastic, pivots, swing detection |
| Reversal engine | `reversals.py` | 8 independent reversal detectors → confluence score, no lookahead |
| Backtester | `backtester.py` | Event-driven, realistic costs, honest metrics, Monte-Carlo robustness |
| Data provider | `data_provider.py` | yfinance → CSV → deterministic synthetic fallback; timeframe resampling |
| News + catalysts | `news_fetcher.py` | Best-effort live RSS + always-available macro calendar (FOMC/CPI/NFP…) |
| Orchestrator CLI | `analyze.py` | `scan` / `backtest` / `levels` / `news` / `demo` |
| Reversal playbook | `REVERSAL_PLAYBOOK.md` | How SPY actually behaves intraday, written cold |

Everything runs on the **Python standard library** — no numpy/pandas required —
so it works in any environment, online or offline. `yfinance` is an optional
accelerator; when it's blocked (as in many locked-down sessions), the tool falls
back to CSV or a clearly-labeled synthetic series and tells you which it used.

## Quick start

```bash
# 1. Prove everything works, fully offline, in 5 seconds:
python3 analyze.py demo

# 2. Backtest the reversal strategy on your data, every timeframe, honestly:
python3 analyze.py backtest --csv your_spy.csv --timeframe all

# 3. Rank the current reversal setups on the 5-minute chart:
python3 analyze.py scan --csv your_spy.csv --timeframe 5m --min-confluence 60

# 4. Today's key levels (pivots, VWAP, ATR):
python3 analyze.py levels --csv your_spy.csv

# 5. News + the macro catalysts that move SPY:
python3 analyze.py news
```

No CSV? Omit `--csv`; it will try yfinance, then synthetic. Synthetic results
are for validating the engine, **not** real SPY history.

## The core workflow (how to actually use it)

1. **Get data.** Export SPY OHLCV from TradingView/your broker to CSV, or rely
   on yfinance where allowed. 1m or 5m bars give you the most timeframes to
   resample from.
2. **Backtest first, always.** `backtest --timeframe all`. Read **expectancy_R**
   and **profit_factor** *after costs*, and the **Monte-Carlo p05** drawdown.
   If expectancy is negative, the setup loses money — stop here and iterate.
3. **Find your edge timeframe.** The backtest compares every timeframe. Trade
   the one with a genuine, robust edge — not the one with the prettiest single
   number.
4. **Scan for live setups** on that timeframe, filtered by your confluence
   threshold. The default action when nothing qualifies is **no trade**.
5. **Check the gate.** Every `scan` prints a pre-trade checklist: backtested?
   macro event imminent? risk ≤ 1%? stop you'll honor? with higher-timeframe
   context?
6. **Mind the calendar.** `news` lists the recurring catalysts. The first move
   after CPI/FOMC/NFP frequently reverses — that's a feature you can study, and
   a trap if you're careless.

## Reversal signals it detects (the confluence stack)

RSI divergence · double tops/bottoms · key-level (pivot/PDH/PDL) rejection ·
candlestick reversals (engulfing, hammer, shooting star, pin bars) · VWAP-stretch
mean reversion · Bollinger-band reversion · RSI extreme turns · stochastic crosses.

Each fires independently with a strength; the engine combines whichever agree on
direction into one score with documented weights (see `reversals.WEIGHTS`).

## Why the backtester can be trusted

- **No lookahead:** signals at bar *i* use only bars ≤ *i*; entries fill at the
  *next* bar's open.
- **Real costs:** commission + slippage on every fill (set them to zero to see
  how much they were flattering you).
- **Worst-case fills:** when a bar contains both stop and target, the **stop**
  fills first.
- **Robustness:** Monte-Carlo trade-shuffle exposes sequence/drawdown risk; an
  in-sample/out-of-sample split is reported by the runner.

## Honesty self-test

Run the backtest on the bundled synthetic data. It shows **negative expectancy
after costs** — correctly, because random-walk data has no reversal edge to
find. A backtester that showed a big "edge" there would be broken. This one
isn't.

## Files

```
spy-day-trading-analyst/
├── SKILL.md                  # this file
├── README.md                 # install + the TradingView live-chart bridge
├── HOW_TO_USE.md             # worked examples for every command
├── REVERSAL_PLAYBOOK.md      # SPY intraday behavior, session by session
├── analyze.py                # CLI orchestrator
├── indicators.py             # indicator/signal toolkit
├── reversals.py              # reversal detection + confluence scoring
├── backtester.py             # honest event-driven backtester + Monte Carlo
├── data_provider.py          # yfinance / CSV / synthetic + resampling
├── news_fetcher.py           # live RSS + macro catalyst calendar
├── sample_data_spy_5m.csv    # offline sample dataset
├── sample_input.json         # example config
├── expected_output.json      # validation reference
└── requirements.txt          # optional accelerators (yfinance, pandas)
```

---

**Version**: 1.0.0
**Last Updated**: June 7, 2026
**Compatibility**: Claude.ai, Claude Code, Claude API (Code Execution). Pure
standard library; `yfinance` optional.
