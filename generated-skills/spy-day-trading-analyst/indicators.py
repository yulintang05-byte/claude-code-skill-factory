"""
Indicator / Signal Toolkit for SPY Day-Trading Analysis.

Pure standard-library implementations (no numpy / pandas required) of the
technical indicators used across the reversal engine and backtester. Every
function returns a list the same length as its input, padded at the front with
``None`` during the warm-up period so values stay aligned with their bars.

Design notes
------------
* Wilder smoothing is used for RSI and ATR (the convention TradingView uses for
  the default RSI(14) and ATR(14)), so numbers line up with what a trader sees
  on the chart.
* Nothing here looks into the future. Index ``i`` of any output is computed only
  from inputs at indices ``<= i``. The backtester depends on this guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence, Tuple


@dataclass
class Bar:
    """A single OHLCV price bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    @property
    def typical(self) -> float:
        """Typical price (HLC/3) used for VWAP and pivots."""
        return (self.high + self.low + self.close) / 3.0

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def is_bull(self) -> bool:
        return self.close >= self.open

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _closes(bars: Sequence[Bar]) -> List[float]:
    return [b.close for b in bars]


def _pad(n: int) -> List[Optional[float]]:
    return [None] * n


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------

def sma(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Simple moving average."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: List[Optional[float]] = _pad(min(period - 1, len(values)))
    if len(values) < period:
        return out + [None] * (len(values) - len(out))
    window_sum = sum(values[:period])
    out.append(window_sum / period)
    for i in range(period, len(values)):
        window_sum += values[i] - values[i - period]
        out.append(window_sum / period)
    return out


def ema(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Exponential moving average, seeded with an SMA of the first ``period``."""
    if period <= 0:
        raise ValueError("period must be positive")
    out: List[Optional[float]] = []
    if len(values) < period:
        return _pad(len(values))
    mult = 2.0 / (period + 1.0)
    out.extend(_pad(period - 1))
    prev = sum(values[:period]) / period
    out.append(prev)
    for i in range(period, len(values)):
        prev = (values[i] - prev) * mult + prev
        out.append(prev)
    return out


# ---------------------------------------------------------------------------
# Momentum
# ---------------------------------------------------------------------------

def rsi(values: Sequence[float], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index using Wilder smoothing (TradingView default)."""
    n = len(values)
    out: List[Optional[float]] = _pad(n)
    if n <= period:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = _rsi_from_avg(avg_gain, avg_loss)
    for i in range(period + 1, n):
        change = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = _rsi_from_avg(avg_gain, avg_loss)
    return out


def _rsi_from_avg(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """MACD line, signal line and histogram."""
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    line: List[Optional[float]] = []
    for f, s in zip(ema_fast, ema_slow):
        line.append(f - s if (f is not None and s is not None) else None)

    # Signal line is an EMA of the (defined portion of the) MACD line.
    defined = [v for v in line if v is not None]
    sig_defined = ema(defined, signal)
    sig: List[Optional[float]] = [None] * (len(line) - len(sig_defined)) + sig_defined

    hist: List[Optional[float]] = []
    for m, s in zip(line, sig):
        hist.append(m - s if (m is not None and s is not None) else None)
    return line, sig, hist


def stochastic(
    bars: Sequence[Bar], k_period: int = 14, d_period: int = 3
) -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """Stochastic oscillator %K and %D."""
    n = len(bars)
    k: List[Optional[float]] = _pad(n)
    for i in range(k_period - 1, n):
        window = bars[i - k_period + 1 : i + 1]
        hh = max(b.high for b in window)
        ll = min(b.low for b in window)
        rng = hh - ll
        k[i] = 100.0 * (bars[i].close - ll) / rng if rng else 50.0
    defined = [v for v in k if v is not None]
    d_defined = sma(defined, d_period)
    d: List[Optional[float]] = [None] * (n - len(d_defined)) + d_defined
    return k, d


# ---------------------------------------------------------------------------
# Volatility
# ---------------------------------------------------------------------------

def true_range(bars: Sequence[Bar]) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for i, b in enumerate(bars):
        if i == 0:
            out.append(b.high - b.low)
        else:
            prev_close = bars[i - 1].close
            out.append(max(b.high - b.low, abs(b.high - prev_close), abs(b.low - prev_close)))
    return out


def atr(bars: Sequence[Bar], period: int = 14) -> List[Optional[float]]:
    """Average True Range with Wilder smoothing."""
    tr = true_range(bars)
    n = len(bars)
    out: List[Optional[float]] = _pad(n)
    if n <= period:
        return out
    first = sum(tr[1 : period + 1]) / period  # type: ignore[arg-type]
    out[period] = first
    prev = first
    for i in range(period + 1, n):
        prev = (prev * (period - 1) + tr[i]) / period  # type: ignore[operator]
        out[i] = prev
    return out


def bollinger(
    values: Sequence[float], period: int = 20, num_std: float = 2.0
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Bollinger Bands -> (middle, upper, lower)."""
    mid = sma(values, period)
    upper: List[Optional[float]] = [None] * len(values)
    lower: List[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = mid[i]
        if mean is None:
            continue
        var = sum((v - mean) ** 2 for v in window) / period
        sd = var ** 0.5
        upper[i] = mean + num_std * sd
        lower[i] = mean - num_std * sd
    return mid, upper, lower


# ---------------------------------------------------------------------------
# Volume / session
# ---------------------------------------------------------------------------

def session_vwap(bars: Sequence[Bar]) -> List[Optional[float]]:
    """Anchored VWAP that resets at the start of each calendar session (day)."""
    out: List[Optional[float]] = []
    cum_pv = 0.0
    cum_v = 0.0
    current_day = None
    for b in bars:
        day = b.timestamp.date()
        if day != current_day:
            current_day = day
            cum_pv = 0.0
            cum_v = 0.0
        vol = b.volume if b.volume else 1.0  # guard zero-volume feeds
        cum_pv += b.typical * vol
        cum_v += vol
        out.append(cum_pv / cum_v if cum_v else None)
    return out


# ---------------------------------------------------------------------------
# Key levels
# ---------------------------------------------------------------------------

@dataclass
class PivotLevels:
    """Classic floor-trader pivot levels derived from a prior period."""

    pp: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float

    def as_dict(self) -> dict:
        return {
            "PP": self.pp,
            "R1": self.r1, "R2": self.r2, "R3": self.r3,
            "S1": self.s1, "S2": self.s2, "S3": self.s3,
        }


def classic_pivots(prev_high: float, prev_low: float, prev_close: float) -> PivotLevels:
    """Classic pivot points from a prior session's H/L/C."""
    pp = (prev_high + prev_low + prev_close) / 3.0
    r1 = 2 * pp - prev_low
    s1 = 2 * pp - prev_high
    r2 = pp + (prev_high - prev_low)
    s2 = pp - (prev_high - prev_low)
    r3 = prev_high + 2 * (pp - prev_low)
    s3 = prev_low - 2 * (prev_high - pp)
    return PivotLevels(pp, r1, r2, r3, s1, s2, s3)


# ---------------------------------------------------------------------------
# Swing-point detection (fractals) -- foundation for divergence & double tops
# ---------------------------------------------------------------------------

@dataclass
class Swing:
    index: int
    price: float
    kind: str  # "high" or "low"


def swing_points(bars: Sequence[Bar], left: int = 2, right: int = 2) -> List[Swing]:
    """Detect confirmed swing highs/lows using a simple fractal rule.

    A swing high at ``i`` requires ``left`` lower highs before it and ``right``
    lower highs after it (mirror for lows). Because confirmation needs ``right``
    future bars, callers using this live must treat the most recent ``right``
    bars as unconfirmed.
    """
    swings: List[Swing] = []
    n = len(bars)
    for i in range(left, n - right):
        h = bars[i].high
        l = bars[i].low
        is_high = all(bars[j].high < h for j in range(i - left, i)) and all(
            bars[j].high < h for j in range(i + 1, i + right + 1)
        )
        is_low = all(bars[j].low > l for j in range(i - left, i)) and all(
            bars[j].low > l for j in range(i + 1, i + right + 1)
        )
        if is_high:
            swings.append(Swing(i, h, "high"))
        if is_low:
            swings.append(Swing(i, l, "low"))
    return swings


def rolling_high(bars: Sequence[Bar], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(bars)
    for i in range(period - 1, len(bars)):
        out[i] = max(b.high for b in bars[i - period + 1 : i + 1])
    return out


def rolling_low(bars: Sequence[Bar], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(bars)
    for i in range(period - 1, len(bars)):
        out[i] = min(b.low for b in bars[i - period + 1 : i + 1])
    return out
