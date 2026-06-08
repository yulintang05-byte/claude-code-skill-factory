"""
Event-driven backtester for the reversal strategy.

The whole point of this module is to be *honest*. The ways backtests usually lie
are well known, and each is defended against here:

* **Lookahead bias** -- signals at bar ``i`` use only data ``<= i`` (guaranteed by
  ``ReversalEngine``), and every entry fills at the *next* bar's open, never at
  the signal bar's close.
* **Ignored costs** -- commission and slippage are charged on every fill. Turn
  them to zero only if you want to see how much the costs were flattering you.
* **Optimistic intrabar fills** -- when a bar's range contains both the stop and
  the target, the **stop is assumed to fill first** (worst case).
* **Survivorship / curve-fitting** -- the strategy is rule-based with no fitted
  parameters, and the runner reports an in-sample / out-of-sample split plus a
  Monte-Carlo trade-shuffle so you can see sequence risk and drawdown spread.

Metrics are reported in R-multiples (profit measured in units of initial risk),
which is the only sane way to compare setups across timeframes and price levels.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from indicators import Bar
from reversals import ReversalEngine


@dataclass
class BacktestConfig:
    starting_equity: float = 30_000.0
    risk_per_trade_pct: float = 0.5        # % of equity risked to the stop
    stop_atr_mult: float = 1.5             # stop distance = mult * ATR
    target_r_multiple: float = 2.0         # take-profit at this many R
    min_confluence: float = 60.0           # only trade setups >= this score
    direction: str = "both"                # "both" | "long" | "short"
    commission_per_trade: float = 1.00     # round-trip $ per trade
    slippage_bps: float = 1.0              # per market fill, in basis points
    max_notional_pct: float = 1.0          # 1.0 == no leverage
    flat_by_close: bool = True             # day-trading: no overnight holds
    max_hold_bars: int = 0                 # 0 == disabled
    seed: int = 7


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    direction: str
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    shares: int
    pnl: float
    r_multiple: float
    return_on_equity: float
    exit_reason: str
    confluence: float
    mae_r: float                # worst excursion in R while open
    mfe_r: float                # best excursion in R while open
    hold_bars: int


@dataclass
class BacktestResult:
    trades: List[Trade]
    equity_curve: List[tuple]            # (datetime, equity) at each session end
    metrics: Dict[str, float]
    config: BacktestConfig
    timeframe: str = ""

    def is_empty(self) -> bool:
        return not self.trades


class Backtester:
    def __init__(self, bars: Sequence[Bar], config: Optional[BacktestConfig] = None):
        self.bars = list(bars)
        self.cfg = config or BacktestConfig()
        self.engine = ReversalEngine(self.bars)

    # --------------------------------------------------------------- internals
    def _is_session_end(self, j: int) -> bool:
        if j >= len(self.bars) - 1:
            return True
        return self.bars[j + 1].timestamp.date() != self.bars[j].timestamp.date()

    def _slip(self, price: float, adverse_for: str) -> float:
        s = self.cfg.slippage_bps / 10_000.0
        # adverse_for: "buy" pays up, "sell" receives less
        return price * (1 + s) if adverse_for == "buy" else price * (1 - s)

    # --------------------------------------------------------------------- run
    def run(self, timeframe: str = "") -> BacktestResult:
        cfg = self.cfg
        equity = cfg.starting_equity
        trades: List[Trade] = []
        equity_curve: List[tuple] = []

        position: Optional[dict] = None
        pending: Optional[dict] = None

        for j, bar in enumerate(self.bars):
            session_end = self._is_session_end(j)

            # 1) Fill a pending entry at THIS bar's open.
            if position is None and pending is not None:
                direction = pending["direction"]
                atr = pending["atr"]
                raw_entry = bar.open
                entry = self._slip(raw_entry, "buy" if direction == "long" else "sell")
                stop_dist = cfg.stop_atr_mult * atr
                if direction == "long":
                    stop = entry - stop_dist
                    target = entry + cfg.target_r_multiple * stop_dist
                else:
                    stop = entry + stop_dist
                    target = entry - cfg.target_r_multiple * stop_dist

                risk_dollars = equity * (cfg.risk_per_trade_pct / 100.0)
                per_share_risk = abs(entry - stop)
                shares = int(risk_dollars / per_share_risk) if per_share_risk > 0 else 0
                max_shares = int((equity * cfg.max_notional_pct) / entry)
                shares = max(0, min(shares, max_shares))
                if shares > 0:
                    position = {
                        "direction": direction, "entry": entry, "stop": stop,
                        "target": target, "shares": shares, "entry_time": bar.timestamp,
                        "entry_idx": j, "confluence": pending["confluence"],
                        "mae": 0.0, "mfe": 0.0, "risk_per_share": per_share_risk,
                    }
                pending = None

            # 2) Manage an open position on THIS bar (stop priority on conflict).
            if position is not None:
                pos = position
                d = pos["direction"]
                # update excursions in R
                if d == "long":
                    fav = (bar.high - pos["entry"]) / pos["risk_per_share"]
                    adv = (bar.low - pos["entry"]) / pos["risk_per_share"]
                else:
                    fav = (pos["entry"] - bar.low) / pos["risk_per_share"]
                    adv = (pos["entry"] - bar.high) / pos["risk_per_share"]
                pos["mfe"] = max(pos["mfe"], fav)
                pos["mae"] = min(pos["mae"], adv)

                exit_price = None
                exit_reason = ""
                hit_stop = bar.low <= pos["stop"] if d == "long" else bar.high >= pos["stop"]
                hit_tgt = bar.high >= pos["target"] if d == "long" else bar.low <= pos["target"]

                if hit_stop:  # worst-case: stop checked first
                    raw = pos["stop"]
                    # gap-through: if the open is already worse than the stop, fill at open
                    if d == "long":
                        raw = min(raw, bar.open)
                        exit_price = self._slip(raw, "sell")
                    else:
                        raw = max(raw, bar.open)
                        exit_price = self._slip(raw, "buy")
                    exit_reason = "stop"
                elif hit_tgt:  # limit order, no adverse slippage
                    exit_price = pos["target"]
                    exit_reason = "target"

                # time-based exits
                if exit_price is None and cfg.max_hold_bars > 0:
                    if j - pos["entry_idx"] >= cfg.max_hold_bars:
                        exit_price = self._slip(bar.close, "sell" if d == "long" else "buy")
                        exit_reason = "time"
                if exit_price is None and cfg.flat_by_close and session_end:
                    exit_price = self._slip(bar.close, "sell" if d == "long" else "buy")
                    exit_reason = "session_close"

                if exit_price is not None:
                    trade, equity = self._close(pos, exit_price, bar.timestamp, j, exit_reason, equity)
                    trades.append(trade)
                    position = None

            # 3) Look for a new setup -> pending for the NEXT bar.
            if position is None and not session_end:
                setup = self.engine.evaluate(j)
                if setup and setup.confluence >= cfg.min_confluence and setup.atr:
                    allowed = (cfg.direction == "both") or (cfg.direction == setup.direction)
                    if allowed:
                        pending = {
                            "direction": setup.direction, "atr": setup.atr,
                            "confluence": setup.confluence,
                        }

            if session_end:
                equity_curve.append((bar.timestamp, equity))

        metrics = compute_metrics(trades, equity_curve, cfg)
        return BacktestResult(trades, equity_curve, metrics, cfg, timeframe)

    def _close(self, pos, exit_price, exit_time, j, reason, equity):
        d = pos["direction"]
        gross = (exit_price - pos["entry"]) * pos["shares"]
        if d == "short":
            gross = -gross
        pnl = gross - self.cfg.commission_per_trade
        equity_before = equity
        equity += pnl
        r = pnl / (pos["risk_per_share"] * pos["shares"]) if pos["shares"] else 0.0
        trade = Trade(
            entry_time=pos["entry_time"], exit_time=exit_time, direction=d,
            entry_price=round(pos["entry"], 4), exit_price=round(exit_price, 4),
            stop_price=round(pos["stop"], 4), target_price=round(pos["target"], 4),
            shares=pos["shares"], pnl=round(pnl, 2), r_multiple=round(r, 3),
            return_on_equity=pnl / equity_before if equity_before else 0.0,
            exit_reason=reason, confluence=pos["confluence"],
            mae_r=round(pos["mae"], 2), mfe_r=round(pos["mfe"], 2),
            hold_bars=j - pos["entry_idx"],
        )
        return trade, equity


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _max_drawdown(equity_series: Sequence[float]) -> float:
    peak = -math.inf
    max_dd = 0.0
    for v in equity_series:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
    return max_dd


def compute_metrics(trades: Sequence[Trade], equity_curve: Sequence[tuple], cfg: BacktestConfig) -> Dict[str, float]:
    if not trades:
        return {"num_trades": 0}

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    rs = [t.r_multiple for t in trades]
    net = sum(t.pnl for t in trades)
    start = cfg.starting_equity
    end = start + net

    equities = [e for _, e in equity_curve]
    max_dd = _max_drawdown([start] + equities)

    # Daily returns from session-end equity for Sharpe/Sortino.
    daily_returns: List[float] = []
    prev = start
    for e in equities:
        if prev > 0:
            daily_returns.append((e - prev) / prev)
        prev = e
    sharpe = sortino = 0.0
    if len(daily_returns) > 1:
        mean = sum(daily_returns) / len(daily_returns)
        var = sum((r - mean) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        sd = var ** 0.5
        if sd > 0:
            sharpe = (mean / sd) * math.sqrt(252)
        downside = [r for r in daily_returns if r < 0]
        if downside:
            dvar = sum(r ** 2 for r in downside) / len(downside)
            dsd = dvar ** 0.5
            if dsd > 0:
                sortino = (mean / dsd) * math.sqrt(252)

    # Max consecutive losses
    max_consec = consec = 0
    for t in trades:
        if t.pnl <= 0:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 0

    n = len(trades)
    win_rate = len(wins) / n
    avg_win_r = (sum(t.r_multiple for t in wins) / len(wins)) if wins else 0.0
    avg_loss_r = (sum(t.r_multiple for t in losses) / len(losses)) if losses else 0.0
    expectancy_r = sum(rs) / n

    return {
        "num_trades": n,
        "win_rate": round(win_rate, 4),
        "wins": len(wins),
        "losses": len(losses),
        "avg_win_R": round(avg_win_r, 3),
        "avg_loss_R": round(avg_loss_r, 3),
        "expectancy_R": round(expectancy_r, 3),
        "expectancy_$": round(net / n, 2),
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss > 0 else float("inf"),
        "net_pnl_$": round(net, 2),
        "total_return_pct": round(100 * net / start, 2),
        "max_drawdown_pct": round(100 * max_dd, 2),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_consecutive_losses": max_consec,
        "avg_hold_bars": round(sum(t.hold_bars for t in trades) / n, 1),
        "best_R": round(max(rs), 2),
        "worst_R": round(min(rs), 2),
    }


# ---------------------------------------------------------------------------
# Monte Carlo robustness
# ---------------------------------------------------------------------------

def monte_carlo(trades: Sequence[Trade], cfg: BacktestConfig, runs: int = 1000) -> Dict[str, float]:
    """Bootstrap-resample the trades (WITH replacement) to expose fragility.

    This does NOT predict the future. Each run draws ``len(trades)`` trades at
    random *with replacement* from the realized set and recompounds them, giving
    a distribution of plausible outcomes and drawdowns from the same underlying
    edge. (A plain order-reshuffle is useless for the return spread, because
    recompounding the identical returns in any order yields the identical
    product -- only the drawdown path changes. Sampling with replacement is what
    produces a real outcome distribution.)

    Read the 5th percentile, not the median: a strategy whose p05 outcome is a
    loss or a brutal drawdown is fragile no matter how good its headline number.
    """
    if len(trades) < 5:
        return {"runs": 0, "note": "not enough trades for Monte Carlo"}

    rets = [t.return_on_equity for t in trades]
    n = len(rets)
    rng = random.Random(cfg.seed)
    final_returns: List[float] = []
    max_dds: List[float] = []
    for _ in range(runs):
        sample = [rng.choice(rets) for _ in range(n)]
        eq = 1.0
        curve = [eq]
        for r in sample:
            eq *= (1 + r)
            curve.append(eq)
        final_returns.append((eq - 1) * 100)
        max_dds.append(_max_drawdown(curve) * 100)

    final_returns.sort()
    max_dds.sort()

    def pct(series: List[float], p: float) -> float:
        idx = min(len(series) - 1, max(0, int(p * len(series))))
        return round(series[idx], 2)

    return {
        "runs": runs,
        "return_p05_pct": pct(final_returns, 0.05),
        "return_p50_pct": pct(final_returns, 0.50),
        "return_p95_pct": pct(final_returns, 0.95),
        "max_drawdown_p50_pct": pct(max_dds, 0.50),
        "max_drawdown_p95_pct": pct(max_dds, 0.95),
        "worst_drawdown_pct": round(max_dds[-1], 2),
    }
