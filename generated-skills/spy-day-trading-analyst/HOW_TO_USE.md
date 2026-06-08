# How to Use the SPY Day-Trading Analyst

Worked examples for every command. All commands run from inside the
`spy-day-trading-analyst/` folder. None of them require any pip install — the
engine is pure standard library. A bundled `sample_data_spy_5m.csv` lets you try
everything immediately and offline.

> Before anything else, skim `SKILL.md` for the honest framing and
> `REVERSAL_PLAYBOOK.md` for the trading logic.

---

## 0. Prove it works (offline, 5 seconds)

```bash
python3 analyze.py demo
```

Runs reversal scanning, multi-timeframe backtesting, and the news module on
deterministic synthetic data. Expect *negative* expectancy — that's correct and
intentional (no edge exists in random data; costs make it slightly negative).

---

## 1. Backtest — always do this first

The backtester is the heart of the skill. It is the only honest way to know
whether a setup has an edge.

### On the bundled sample data, every timeframe:

```bash
python3 analyze.py backtest --csv sample_data_spy_5m.csv --timeframe all
```

You get a per-timeframe table:

```
   TF  trades   win%   exp_R     PF     ret%  maxDD%  sharpe  maxLossStreak
   5m      41  31.7%  -0.223   0.72   -4.50%   5.70%   -1.9              7
  15m      11  54.5%  -0.192   ...
```

Then a detailed breakdown of the best timeframe by expectancy, plus a
**Monte-Carlo** section showing the spread of outcomes and the 95th-percentile
drawdown if those same trades had come in a different order.

### How to read it (the only numbers that matter):

- **`expectancy_R`** — average profit per trade in units of risk. **Must be
  positive after costs.** Negative = the strategy loses money. Full stop.
- **`profit_factor`** — gross profit ÷ gross loss. > 1.3 is the minimum to
  survive real-world friction; < 1.3 is too thin.
- **`max_drawdown_pct`** and **Monte-Carlo `max_drawdown_p95_pct`** — can you
  emotionally and financially survive this? If not, the strategy is unusable
  *for you* regardless of its return.
- **`win_rate`** — note how far from "90%" reality is. Edges come from win *size*
  × frequency, not from being right often.

### Tune the strategy and re-test:

```bash
# Only long reversals, stricter setups, wider target, more realistic costs:
python3 analyze.py backtest --csv sample_data_spy_5m.csv --timeframe 5m \
    --direction long --min-confluence 70 --target-r 2.5 \
    --commission 1.0 --slippage 1.5 --risk 0.5
```

| Flag | Meaning | Default |
|---|---|---|
| `--timeframe` | `all` or `5m`/`15m`/`30m`/`1h`/`1D` | `all` |
| `--equity` | Starting account size | `30000` |
| `--risk` | % of equity risked per trade | `0.5` |
| `--stop-atr` | Stop distance = N × ATR | `1.5` |
| `--target-r` | Take-profit in R multiples | `2.0` |
| `--min-confluence` | Only trade setups ≥ this score | `60` |
| `--direction` | `both` / `long` / `short` | `both` |
| `--commission` | Round-trip $ per trade | `1.0` |
| `--slippage` | Basis points per market fill | `1.0` |
| `--mc-runs` | Monte-Carlo iterations | `1000` |
| `--json PATH` | Save per-timeframe metrics to JSON | — |

**Cost sensitivity test:** run once with `--commission 0 --slippage 0`, then with
realistic costs. The gap is exactly how much the costs were eating. If a
"profitable" strategy dies when you add real costs, it was never real.

---

## 2. Scan — rank the current reversal setups

```bash
python3 analyze.py scan --csv sample_data_spy_5m.csv --timeframe 5m --min-confluence 60
```

Lists qualifying setups newest-last, then prints a **pre-trade gate** for the
most recent one: direction, suggested stop/targets (ATR-based), the exact
signals that fired, and a checklist you must clear before risking money.

If nothing qualifies, it says so — and the default action is **no trade**. The
absence of a setup is itself a position.

```bash
# Higher bar (premium setups only):
python3 analyze.py scan --csv sample_data_spy_5m.csv --timeframe 15m --min-confluence 75
```

Scoring guide: ~25 = one signal, ~50 = two aligned, 60–80 = strong confluence,
80+ = rare. **The score is setup quality, never a win probability.**

---

## 3. Levels — your map for the day

```bash
python3 analyze.py levels --csv sample_data_spy_5m.csv
```

Prints last price, session VWAP, prior-session high/low, daily ATR (the typical
day's range), and the full floor-trader pivot set (PP, R1–R3, S1–S3) — the
levels the reversal engine watches for rejections.

---

## 4. News — catalysts that move SPY

```bash
python3 analyze.py news
```

Best-effort live RSS headlines (with a transparent risk-on/risk-off keyword
tone), **always** followed by the recurring macro calendar — FOMC, CPI, PCE,
NFP, jobless claims, PPI, retail sales, ISM, GDP, witching — each with its time
of day and why it moves SPY. In locked-down environments the live feeds are
blocked; the calendar still works offline.

**Use it as a "don't get caught" filter:** never hold a reversal into a release
in the next 30 minutes. The first move after CPI/FOMC/NFP is a coin flip that
frequently reverses.

---

## 5. Using your own TradingView data

1. In TradingView Desktop/web: right-click the chart → **Export chart data** →
   CSV.
2. Run any command with `--csv path/to/export.csv`.

Column names are auto-detected. For the most timeframe coverage, export **1m or
5m** bars — the engine resamples upward to 15m/30m/1h/1D for you.

For *live* chart reading (not just exports), see the **TradingView MCP bridge**
section in `README.md` — it runs on your own machine and complements this
skill's analysis.

---

## 6. A sane daily routine

```bash
# Pre-market: know the catalysts and your levels
python3 analyze.py news
python3 analyze.py levels --csv today.csv

# Validate your plan has an edge BEFORE the open
python3 analyze.py backtest --csv recent_60d.csv --timeframe all

# During the session: scan your edge timeframe, respect the gate
python3 analyze.py scan --csv today.csv --timeframe 5m --min-confluence 65
```

Then — and only then — make your own decision. The tool informs; you decide; you
own the risk.
