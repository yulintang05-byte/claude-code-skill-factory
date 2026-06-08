#!/usr/bin/env python3
"""
SPY Day-Trading Analyst -- command-line orchestrator.

Ties the four modules together behind one CLI:

    python3 analyze.py demo                      # full self-contained demo (offline)
    python3 analyze.py scan      [--csv F]       # rank current reversal setups
    python3 analyze.py backtest  [--csv F] --timeframe all
    python3 analyze.py levels    [--csv F]       # today's key levels (pivots/VWAP)
    python3 analyze.py news                       # headlines + macro catalysts

Data source resolution for every command: --csv if given, else yfinance, else a
deterministic synthetic series so nothing ever hard-fails for lack of data. The
banner always tells you which source was used.

This tool reports edges; it does not place trades and it does not promise wins.
See the pre-trade gate printed by ``scan``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

import indicators as ind
from data_provider import ALL_TIMEFRAMES, infer_interval_minutes, load, resample, valid_timeframes
from backtester import Backtester, BacktestConfig, monte_carlo
from reversals import ReversalEngine
from news_fetcher import fetch_news, render_report


DISCLAIMER = (
    "This is analysis/education tooling, NOT financial advice and NOT a trade "
    "signal service. SPY day trading carries a real risk of loss. No setup score "
    "is a probability of profit. You are responsible for every trade you take."
)


def _banner(title: str) -> None:
    print("=" * 72)
    print(f" {title}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------

def cmd_scan(args) -> None:
    bars = load(csv_path=args.csv, interval=args.interval, period=args.period)
    if args.timeframe and args.timeframe != "base":
        bars = resample(bars, args.timeframe)
    engine = ReversalEngine(bars)
    setups = engine.scan(min_confluence=args.min_confluence)

    _banner(f"REVERSAL SCAN  |  {len(bars)} bars  |  min score {args.min_confluence}")
    if not setups:
        print(f"\nNo setups at or above score {args.min_confluence}. "
              "Default action: NO TRADE. The absence of a setup is a position.")
    else:
        recent = setups[-args.limit:]
        print(f"\n{len(setups)} qualifying setups. Most recent {len(recent)}:\n")
        for s in recent:
            print("  " + s.summary())

        latest = setups[-1]
        print("\n" + "-" * 72)
        print("MOST RECENT SETUP -- PRE-TRADE GATE")
        print("-" * 72)
        _print_pretrade_gate(latest, bars)

    print("\n" + DISCLAIMER)


def _print_pretrade_gate(setup, bars) -> None:
    atr = setup.atr or 0.0
    entry = setup.price
    if setup.direction == "long":
        stop = entry - 1.5 * atr
        t1 = entry + 1.5 * atr
        t2 = entry + 3.0 * atr
    else:
        stop = entry + 1.5 * atr
        t1 = entry - 1.5 * atr
        t2 = entry - 3.0 * atr

    print(f"  Direction      : {setup.direction.upper()}")
    print(f"  Confluence     : {setup.confluence}/100   (setup QUALITY, not win probability)")
    print(f"  Reference px   : {entry:.2f}")
    print(f"  Suggested stop : {stop:.2f}   (1.5x ATR = {1.5*atr:.2f})")
    print(f"  Target 1 (1R)  : {t1:.2f}")
    print(f"  Target 2 (2R)  : {t2:.2f}")
    print("  Signals        :")
    for c in setup.components:
        print(f"     - {c.source}: {c.detail} (strength {c.strength:.2f})")
    print("\n  CHECKLIST before risking a cent:")
    print("   [ ] Did you BACKTEST this config? (python3 analyze.py backtest --timeframe all)")
    print("   [ ] Is there a macro release in the next 30 min? (python3 analyze.py news)")
    print("   [ ] Is your risk per trade <= 1% of account?")
    print("   [ ] Is the stop at a level you'll actually honor?")
    print("   [ ] Are you trading WITH the higher-timeframe context, not against it?")


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

def cmd_backtest(args) -> None:
    base = load(csv_path=args.csv, interval=args.interval, period=args.period)
    requested: List[str] = ALL_TIMEFRAMES if args.timeframe == "all" else [args.timeframe]
    base_min = infer_interval_minutes(base)
    timeframes = valid_timeframes(base, requested)
    dropped = [tf for tf in requested if tf not in timeframes]
    if dropped:
        print(f"[note] Source bars are ~{base_min}m; cannot resample UP to a finer "
              f"timeframe. Skipping: {', '.join(dropped)}.")

    cfg = BacktestConfig(
        starting_equity=args.equity,
        risk_per_trade_pct=args.risk,
        stop_atr_mult=args.stop_atr,
        target_r_multiple=args.target_r,
        min_confluence=args.min_confluence,
        direction=args.direction,
        commission_per_trade=args.commission,
        slippage_bps=args.slippage,
    )

    _banner(f"BACKTEST  |  cost: ${cfg.commission_per_trade}/trade + {cfg.slippage_bps}bps "
            f"slippage  |  risk {cfg.risk_per_trade_pct}%/trade")
    print("\nNo-lookahead, next-bar-open fills, stop-priority on conflicting bars.\n")

    header = (f"{'TF':>5} {'trades':>7} {'win%':>6} {'exp_R':>7} {'PF':>6} "
              f"{'ret%':>8} {'maxDD%':>7} {'sharpe':>7} {'maxLossStreak':>13}")
    print(header)
    print("-" * len(header))

    results = {}
    for tf in timeframes:
        bars = resample(base, tf) if tf not in ("base",) else base
        if len(bars) < 50:
            print(f"{tf:>5}  (skipped: only {len(bars)} bars after resampling)")
            continue
        bt = Backtester(bars, cfg)
        res = bt.run(timeframe=tf)
        results[tf] = res
        m = res.metrics
        if m.get("num_trades", 0) == 0:
            print(f"{tf:>5} {0:>7}  (no qualifying trades)")
            continue
        pf = m["profit_factor"]
        pf_str = "inf" if pf == float("inf") else f"{pf:.2f}"
        print(f"{tf:>5} {m['num_trades']:>7} {m['win_rate']*100:>5.1f}% "
              f"{m['expectancy_R']:>7.3f} {pf_str:>6} {m['total_return_pct']:>7.2f}% "
              f"{m['max_drawdown_pct']:>6.2f}% {m['sharpe']:>7.2f} {m['max_consecutive_losses']:>13}")

    # Detailed view + Monte Carlo for the best timeframe by expectancy.
    traded = {tf: r for tf, r in results.items() if r.metrics.get("num_trades", 0) >= 5}
    if traded:
        best_tf = max(traded, key=lambda tf: traded[tf].metrics["expectancy_R"])
        best = traded[best_tf]
        print("\n" + "-" * 72)
        print(f"DETAIL -- best timeframe by expectancy: {best_tf}")
        print("-" * 72)
        for k, v in best.metrics.items():
            print(f"  {k:24s}: {v}")
        mc = monte_carlo(best.trades, best.config, runs=args.mc_runs)
        print("\n  MONTE CARLO (bootstrap resample with replacement, "
              f"{mc.get('runs', 0)} runs) -- outcome & drawdown spread:")
        for k, v in mc.items():
            if k != "runs":
                print(f"    {k:24s}: {v}")
        print("\n  How to read this: a positive expectancy_R AND a 5th-percentile")
        print("  Monte-Carlo return that you can stomach is the bar. A great headline")
        print("  return with a brutal p05 drawdown means the edge is fragile.")
        _honesty_verdict(best.metrics)
    else:
        print("\nNot enough trades on any timeframe to judge. That itself is a finding:")
        print("this config trades too rarely to build statistical confidence.")

    if args.json:
        out = {tf: r.metrics for tf, r in results.items()}
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"\n[saved metrics -> {args.json}]")

    print("\n" + DISCLAIMER)


def _honesty_verdict(m: dict) -> None:
    print("\n  VERDICT (cold read):")
    exp = m.get("expectancy_R", 0)
    pf = m.get("profit_factor", 0)
    wr = m.get("win_rate", 0)
    if exp <= 0:
        print("   -> NEGATIVE expectancy after costs. This config loses money. Do not trade it.")
    elif pf != float("inf") and pf < 1.3:
        print("   -> Marginal edge (PF < 1.3). Too thin to survive real-world friction. Keep iterating.")
    else:
        print(f"   -> Positive expectancy ({exp:+.3f}R) with PF {pf}. Worth paper-trading next.")
    print(f"   -> Reality check: win rate is {wr*100:.0f}%. If you expected 90%, this is why")
    print("      90% is a myth -- edges come from WIN SIZE x frequency, not from being right often.")


# ---------------------------------------------------------------------------
# levels
# ---------------------------------------------------------------------------

def cmd_levels(args) -> None:
    bars = load(csv_path=args.csv, interval=args.interval, period=args.period)
    daily = resample(bars, "1D")
    _banner("KEY LEVELS")
    if len(daily) < 2:
        print("Need at least two sessions of data to compute pivots.")
        return
    prev = daily[-2]
    piv = ind.classic_pivots(prev.high, prev.low, prev.close)
    last = bars[-1]
    vwap = ind.session_vwap(bars)[-1]
    atr_d = ind.atr(daily, 14)[-1]

    print(f"\n  Last price        : {last.close:.2f}  ({last.timestamp:%Y-%m-%d %H:%M})")
    print(f"  Session VWAP      : {vwap:.2f}" if vwap else "  Session VWAP      : n/a")
    print(f"  Prior session H/L : {prev.high:.2f} / {prev.low:.2f}")
    if atr_d:
        print(f"  Daily ATR(14)     : {atr_d:.2f}  (typical day's range)")
    print("\n  Floor-trader pivots (from prior session):")
    for name, level in piv.as_dict().items():
        marker = "  <-- price here" if abs(level - last.close) < (atr_d or 1) * 0.1 else ""
        print(f"     {name:3s} : {level:.2f}{marker}")
    print("\n  Use these as decision points: reactions (rejection/reclaim) at these")
    print("  levels are where the reversal engine looks for key-level signals.")
    print("\n" + DISCLAIMER)


# ---------------------------------------------------------------------------
# news
# ---------------------------------------------------------------------------

def cmd_news(args) -> None:
    report = fetch_news(max_headlines=args.limit)
    print(render_report(report))


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

def cmd_demo(args) -> None:
    _banner("SPY DAY-TRADING ANALYST -- SELF-CONTAINED DEMO (synthetic data)")
    print("\nThis runs the entire pipeline offline on a deterministic synthetic\n"
          "series so you can verify every component works. Synthetic != real SPY.\n")

    bars = load(csv_path=None, allow_synthetic=True)
    print(f"\n[1/4] Loaded {len(bars)} base bars.")

    print("\n[2/4] Multi-timeframe reversal scan (count of setups >= score 60):")
    for tf in ["5m", "15m", "1h", "1D"]:
        tf_bars = resample(bars, tf)
        if len(tf_bars) < 30:
            continue
        eng = ReversalEngine(tf_bars)
        setups = eng.scan(min_confluence=60)
        print(f"     {tf:>4}: {len(setups):>4} setups  ({len(tf_bars)} bars)")

    print("\n[3/4] Backtest across timeframes:")
    cfg = BacktestConfig(min_confluence=60)
    header = f"     {'TF':>5} {'trades':>7} {'win%':>6} {'exp_R':>7} {'ret%':>8} {'maxDD%':>7}"
    print(header)
    for tf in ["5m", "15m", "1h"]:
        tf_bars = resample(bars, tf)
        if len(tf_bars) < 50:
            continue
        res = Backtester(tf_bars, cfg).run(tf)
        m = res.metrics
        if m.get("num_trades", 0) == 0:
            print(f"     {tf:>5} {0:>7}  (no trades)")
            continue
        print(f"     {tf:>5} {m['num_trades']:>7} {m['win_rate']*100:>5.1f}% "
              f"{m['expectancy_R']:>7.3f} {m['total_return_pct']:>7.2f}% {m['max_drawdown_pct']:>6.2f}%")

    print("\n[4/4] News / macro catalysts:")
    report = fetch_news()
    print(f"     Live headlines: {'available' if report.online else 'blocked (offline calendar shown)'}")
    print(f"     Tracked recurring catalysts: {len(report.macro_calendar)}")

    print("\nDemo complete. Everything ran with zero external dependencies.")
    print("\n" + DISCLAIMER)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SPY Day-Trading Analyst")
    sub = p.add_subparsers(dest="command", required=True)

    def add_data_args(sp):
        sp.add_argument("--csv", help="Path to OHLCV CSV (overrides yfinance/synthetic)")
        sp.add_argument("--interval", default="5m", help="yfinance interval (default 5m)")
        sp.add_argument("--period", default="60d", help="yfinance period (default 60d)")

    sp = sub.add_parser("scan", help="Rank current reversal setups")
    add_data_args(sp)
    sp.add_argument("--timeframe", default="base", help="base|5m|15m|1h|1D")
    sp.add_argument("--min-confluence", dest="min_confluence", type=float, default=60.0)
    sp.add_argument("--limit", type=int, default=10)
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("backtest", help="Backtest the reversal strategy")
    add_data_args(sp)
    sp.add_argument("--timeframe", default="all", help="all|5m|15m|1h|1D ...")
    sp.add_argument("--equity", type=float, default=30_000.0)
    sp.add_argument("--risk", type=float, default=0.5, help="%% equity risked per trade")
    sp.add_argument("--stop-atr", dest="stop_atr", type=float, default=1.5)
    sp.add_argument("--target-r", dest="target_r", type=float, default=2.0)
    sp.add_argument("--min-confluence", dest="min_confluence", type=float, default=60.0)
    sp.add_argument("--direction", default="both", choices=["both", "long", "short"])
    sp.add_argument("--commission", type=float, default=1.0)
    sp.add_argument("--slippage", type=float, default=1.0, help="bps per market fill")
    sp.add_argument("--mc-runs", dest="mc_runs", type=int, default=1000)
    sp.add_argument("--json", help="Write per-timeframe metrics to this JSON path")
    sp.set_defaults(func=cmd_backtest)

    sp = sub.add_parser("levels", help="Show key levels (pivots, VWAP, ATR)")
    add_data_args(sp)
    sp.set_defaults(func=cmd_levels)

    sp = sub.add_parser("news", help="Headlines + recurring macro catalysts")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_news)

    sp = sub.add_parser("demo", help="Self-contained offline demo of everything")
    sp.set_defaults(func=cmd_demo)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
