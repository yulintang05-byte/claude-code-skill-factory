# SPY Day-Trading Analyst

A cold, honest toolkit for analyzing **SPY** intraday behavior — specialized in
**reversals** — with an event-driven backtester that reports the *real* edge
after costs, a multi-signal reversal engine, a SPY behavior playbook, and a
news/macro-catalyst module.

> **Read `SKILL.md` first.** It contains the honest framing: no "90% accuracy,"
> no trade execution, and why the confluence score is setup quality, not a win
> probability. SPY day trading carries a real risk of loss. This is
> analysis/education tooling, **not financial advice.**

## Requirements

- **Python 3.8+** — that's it. The entire engine is pure standard library.
- **Optional:** `yfinance` and `pandas` for live/historical auto-download
  (`pip install -r requirements.txt`). When the network blocks the data
  endpoints (common in sandboxes), the tool falls back to CSV or a clearly
  labeled synthetic series automatically.

## Installation

```bash
# Personal (all projects):
cp -r spy-day-trading-analyst ~/.claude/skills/

# Or project-level:
cp -r spy-day-trading-analyst .claude/skills/

# Restart Claude Code; the skill loads when SPY/day-trading topics come up.
```

You can also just run it directly as a CLI from inside the folder.

## 30-second proof it works

```bash
cd spy-day-trading-analyst
python3 analyze.py demo
```

Runs the whole pipeline offline on deterministic synthetic data. (It will show
*negative* expectancy after costs — correctly, because random data has no
reversal edge. That's the backtester being honest, not broken.)

## Commands

| Command | What it does |
|---|---|
| `python3 analyze.py demo` | Self-contained offline demo of every component |
| `python3 analyze.py backtest --csv F --timeframe all` | Honest backtest across all timeframes + Monte Carlo |
| `python3 analyze.py scan --csv F --timeframe 5m` | Rank current reversal setups + pre-trade gate |
| `python3 analyze.py levels --csv F` | Today's pivots, VWAP, ATR, key levels |
| `python3 analyze.py news` | Live headlines (best-effort) + macro catalyst calendar |

See **HOW_TO_USE.md** for worked examples and every flag.

## Getting real SPY data in

The engine consumes OHLCV bars. Three ways, in order of preference:

1. **CSV export (most reliable).** From TradingView: right-click chart → *Export
   chart data* → CSV. From your broker: any OHLCV export. Then
   `--csv your_file.csv`. Flexible column names are auto-detected
   (Date/Datetime, Open/High/Low/Close, Volume).
2. **yfinance** (`pip install -r requirements.txt`, omit `--csv`). Needs outbound
   network to Yahoo; blocked in many locked-down environments.
3. **Synthetic** (automatic fallback) — for validating the engine only, never
   real history.

---

## Live charts: pairing with the TradingView MCP bridge

This skill analyzes *bars you give it*. If you want an agent to read your **live
TradingView Desktop chart** — symbol, timeframe, indicator values, drawn levels,
Pine output, screenshots — use the community **TradingView MCP bridge**
(`tradesdontlie/tradingview-mcp`). It connects Claude Code to the TradingView
Desktop app on your machine via Chrome DevTools Protocol.

**Crucial limitation — where it can and cannot run:**

- ✅ It works on **your own computer**, where TradingView Desktop is installed
  and running with the debug port enabled. The MCP server talks to
  `localhost:9222` on *that machine*.
- ❌ It **cannot** work from a remote/cloud Claude Code session (e.g.,
  claude.ai/code web sessions or CI). Those run in an ephemeral container that
  has no TradingView Desktop and no access to your machine's `localhost`.
  Installing it there does nothing.

**Install it locally (on the machine running TradingView Desktop):**

```bash
git clone https://github.com/tradesdontlie/tradingview-mcp.git
cd tradingview-mcp
npm install          # only 2 deps: @modelcontextprotocol/sdk + chrome-remote-interface
```

Add to your **local** Claude Code MCP config (`~/.claude/.mcp.json`):

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/absolute/path/to/tradingview-mcp/src/server.js"]
    }
  }
}
```

Launch TradingView Desktop with the debug port, then verify:

```bash
# macOS example (see the repo's scripts/ for Windows/Linux):
/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222
# In Claude Code:  "Use tv_health_check to verify TradingView is connected"
```

**Suggested division of labor:**

- **TradingView MCP** = the eyes/hands on the live chart (current price, levels,
  indicator values, screenshots, drawing, replay practice).
- **This skill** = the cold analytical brain (multi-timeframe reversal scoring,
  honest backtests with costs, the reversal playbook, macro calendar). Feed a
  CSV export from TradingView into `analyze.py backtest` to validate any setup
  the live chart suggests *before* you act on it.

**Caveats you should know (from the tool's own disclaimer):**

- Requires a **valid TradingView subscription**; it does not bypass any paywall.
- It uses **undocumented internal APIs** that can break on any TradingView
  update.
- TradingView's Terms of Use restrict automated/programmatic data access, so
  there is **account risk**; the tool explicitly says not to use it for
  automated trading or algorithmic decision-making on extracted data. Review the
  repo's DISCLAIMER and decide for yourself. **This skill never automates
  execution** — it analyzes and reports.

---

## Project layout

```
spy-day-trading-analyst/
├── SKILL.md                 # honest framing + capability overview (read first)
├── README.md                # this file
├── HOW_TO_USE.md            # worked examples for every command
├── REVERSAL_PLAYBOOK.md     # SPY intraday behavior, session by session
├── analyze.py               # CLI orchestrator
├── indicators.py            # indicator/signal toolkit (pure stdlib)
├── reversals.py             # reversal detection + confluence scoring
├── backtester.py            # event-driven backtester + Monte Carlo
├── data_provider.py         # yfinance / CSV / synthetic + resampling
├── news_fetcher.py          # RSS headlines + macro catalyst calendar
├── sample_data_spy_5m.csv   # offline sample dataset
├── sample_input.json        # example config
├── expected_output.json     # validation reference
├── test_skill.py            # stdlib unittest regression suite (20 tests)
└── requirements.txt         # optional accelerators
```

## Running the tests

```bash
python3 -m unittest test_skill -v   # 20 tests, ~5s, no dependencies
```

They assert the load-bearing guarantees: no-lookahead, resample integrity,
cost-sensitivity, and Monte-Carlo spread.

## License / disclaimer

Provided for educational and research purposes. Not financial advice. No
warranty. You are solely responsible for your trading decisions and for
complying with the terms of any data provider or third-party tool you use.
