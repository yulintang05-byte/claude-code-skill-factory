"""
Reversal detection engine for SPY.

This module turns raw bars into ranked *reversal setups*. It detects a panel of
independent reversal signals (candlestick patterns, RSI/MACD/stochastic turns,
divergence, Bollinger reversion, VWAP stretch, key-level rejection, double
tops/bottoms) and combines whichever ones agree on direction into a single
**confluence score (0-100)**.

READ THIS, IT MATTERS
---------------------
The confluence score is a measure of *how many independent reversal signals line
up* -- in other words, setup quality. It is **NOT** a probability of profit and
**NOT** a win rate. A 90/100 setup is not "90% likely to work." The only way to
estimate a real edge is to run the backtester (``backtester.py``) over many
trades and read the empirical win rate / expectancy *after costs*. The score
exists to rank and filter setups consistently, nothing more.

No detector looks into the future. Every signal at bar ``i`` is computed using
only bars at index ``<= i`` (swing/divergence logic only uses swings already
confirmed as of bar ``i``), so the engine can be driven bar-by-bar by the
backtester without lookahead leakage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

import indicators as ind
from indicators import Bar


# Documented confluence weights. They sum to 1.0; the score is a weighted blend
# of the strengths of the signals that agree on the dominant direction.
#
# SCORE_NORMALIZER maps the raw weighted sum onto a usable 0-100 scale. It is the
# raw confluence value that corresponds to a "100" -- i.e. a near-perfect stack
# of aligned signals. With it, roughly: ~25 = a single decent signal, ~50 = two
# aligned signals, ~75+ = three or more aligned. It rescales the axis only; it
# does NOT change the ranking of one setup vs. another and does NOT turn the
# score into a probability of profit.
SCORE_NORMALIZER: float = 0.60

WEIGHTS: Dict[str, float] = {
    "rsi_divergence": 0.20,
    "double_extreme": 0.18,
    "key_level_rejection": 0.16,
    "candlestick": 0.14,
    "vwap_stretch": 0.12,
    "bollinger_reversion": 0.10,
    "rsi_turn": 0.06,
    "stochastic_cross": 0.04,
}


@dataclass
class Signal:
    source: str
    direction: str          # "long" or "short"
    strength: float         # 0..1
    detail: str = ""


@dataclass
class ReversalSetup:
    index: int
    timestamp: datetime
    direction: str
    confluence: float                       # 0..100
    price: float
    atr: Optional[float]
    components: List[Signal] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def summary(self) -> str:
        comp = ", ".join(f"{s.source}({s.strength:.2f})" for s in self.components)
        return (
            f"{self.timestamp:%Y-%m-%d %H:%M} | {self.direction.upper():5s} "
            f"| score {self.confluence:5.1f} | px {self.price:.2f} | {comp}"
        )


class ReversalEngine:
    """Precompute indicators once, then evaluate reversal confluence per bar."""

    def __init__(
        self,
        bars: Sequence[Bar],
        rsi_period: int = 14,
        atr_period: int = 14,
        vwap_stretch_atr: float = 2.0,
        swing_left: int = 2,
        swing_right: int = 2,
        level_tolerance_atr: float = 0.15,
    ):
        self.bars = list(bars)
        self.n = len(self.bars)
        self.vwap_stretch_atr = vwap_stretch_atr
        self.swing_right = swing_right
        self.level_tol_atr = level_tolerance_atr

        closes = [b.close for b in self.bars]
        self.rsi = ind.rsi(closes, rsi_period)
        self.atr = ind.atr(self.bars, atr_period)
        self.macd_line, self.macd_sig, self.macd_hist = ind.macd(closes)
        self.bb_mid, self.bb_up, self.bb_lo = ind.bollinger(closes, 20, 2.0)
        self.vwap = ind.session_vwap(self.bars)
        self.stoch_k, self.stoch_d = ind.stochastic(self.bars, 14, 3)
        self.sma_fast = ind.sma(closes, 9)
        self.swings = ind.swing_points(self.bars, swing_left, swing_right)

        # Pre-index swings by confirmation bar (swing.index + right) for fast,
        # lookahead-safe retrieval.
        self._swings_by_confirm: Dict[int, List[ind.Swing]] = {}
        for s in self.swings:
            confirm = s.index + swing_right
            self._swings_by_confirm.setdefault(confirm, []).append(s)

        # Daily pivots keyed by session date (computed from prior session H/L/C).
        self._pivots = self._compute_session_pivots()

    # ------------------------------------------------------------------ pivots
    def _compute_session_pivots(self) -> Dict[object, ind.PivotLevels]:
        by_day: Dict[object, List[Bar]] = {}
        order: List[object] = []
        for b in self.bars:
            d = b.timestamp.date()
            if d not in by_day:
                by_day[d] = []
                order.append(d)
            by_day[d].append(b)
        pivots: Dict[object, ind.PivotLevels] = {}
        for i in range(1, len(order)):
            prev = by_day[order[i - 1]]
            ph = max(b.high for b in prev)
            pl = min(b.low for b in prev)
            pc = prev[-1].close
            pivots[order[i]] = ind.classic_pivots(ph, pl, pc)
        return pivots

    def _confirmed_swings(self, i: int, kind: str) -> List[ind.Swing]:
        """Swings of ``kind`` confirmed at or before bar ``i`` (no lookahead)."""
        out: List[ind.Swing] = []
        for confirm_idx, swings in self._swings_by_confirm.items():
            if confirm_idx <= i:
                out.extend(s for s in swings if s.kind == kind)
        out.sort(key=lambda s: s.index)
        return out

    # --------------------------------------------------------------- detectors
    def _candlestick(self, i: int) -> Optional[Signal]:
        if i < 1:
            return None
        b, p = self.bars[i], self.bars[i - 1]
        rng = b.range or 1e-9
        body_ratio = b.body / rng

        # Bullish / bearish engulfing
        if b.is_bull and not p.is_bull and b.close >= p.open and b.open <= p.close:
            strength = min(1.0, 0.5 + (b.body / (p.body + 1e-9)) * 0.25)
            return Signal("candlestick", "long", strength, "bullish engulfing")
        if not b.is_bull and p.is_bull and b.close <= p.open and b.open >= p.close:
            strength = min(1.0, 0.5 + (b.body / (p.body + 1e-9)) * 0.25)
            return Signal("candlestick", "short", strength, "bearish engulfing")

        # Hammer / shooting star (pin bars)
        if body_ratio < 0.35 and b.lower_wick > 2 * b.body and b.upper_wick < b.body:
            return Signal("candlestick", "long", 0.6, "hammer / bullish pin")
        if body_ratio < 0.35 and b.upper_wick > 2 * b.body and b.lower_wick < b.body:
            return Signal("candlestick", "short", 0.6, "shooting star / bearish pin")
        return None

    def _rsi_turn(self, i: int) -> Optional[Signal]:
        if i < 1 or self.rsi[i] is None or self.rsi[i - 1] is None:
            return None
        prev, cur = self.rsi[i - 1], self.rsi[i]
        if prev < 30 and cur > prev:
            return Signal("rsi_turn", "long", min(1.0, (30 - prev) / 15 + 0.4), f"RSI up from {prev:.0f}")
        if prev > 70 and cur < prev:
            return Signal("rsi_turn", "short", min(1.0, (prev - 70) / 15 + 0.4), f"RSI down from {prev:.0f}")
        return None

    def _rsi_divergence(self, i: int) -> Optional[Signal]:
        if self.rsi[i] is None:
            return None
        lows = self._confirmed_swings(i, "low")
        if len(lows) >= 2:
            a, b = lows[-2], lows[-1]
            ra, rb = self.rsi[a.index], self.rsi[b.index]
            if ra is not None and rb is not None and b.price < a.price and rb > ra:
                return Signal("rsi_divergence", "long", 0.85, "bullish RSI divergence")
        highs = self._confirmed_swings(i, "high")
        if len(highs) >= 2:
            a, b = highs[-2], highs[-1]
            ra, rb = self.rsi[a.index], self.rsi[b.index]
            if ra is not None and rb is not None and b.price > a.price and rb < ra:
                return Signal("rsi_divergence", "short", 0.85, "bearish RSI divergence")
        return None

    def _double_extreme(self, i: int) -> Optional[Signal]:
        a_tol = self.atr[i] if self.atr[i] else None
        if a_tol is None:
            return None
        tol = a_tol * 0.5
        highs = self._confirmed_swings(i, "high")
        if len(highs) >= 2 and abs(highs[-1].price - highs[-2].price) <= tol:
            return Signal("double_extreme", "short", 0.8, "double top")
        lows = self._confirmed_swings(i, "low")
        if len(lows) >= 2 and abs(lows[-1].price - lows[-2].price) <= tol:
            return Signal("double_extreme", "long", 0.8, "double bottom")
        return None

    def _bollinger_reversion(self, i: int) -> Optional[Signal]:
        if self.bb_lo[i] is None or self.bb_up[i] is None:
            return None
        b = self.bars[i]
        if b.low < self.bb_lo[i] and b.close > self.bb_lo[i]:
            return Signal("bollinger_reversion", "long", 0.6, "tagged & reclaimed lower band")
        if b.high > self.bb_up[i] and b.close < self.bb_up[i]:
            return Signal("bollinger_reversion", "short", 0.6, "tagged & rejected upper band")
        return None

    def _vwap_stretch(self, i: int) -> Optional[Signal]:
        if self.vwap[i] is None or self.atr[i] is None or self.atr[i] == 0:
            return None
        stretch = (self.bars[i].close - self.vwap[i]) / self.atr[i]
        if stretch <= -self.vwap_stretch_atr:
            return Signal("vwap_stretch", "long", min(1.0, abs(stretch) / 4), f"{stretch:.1f} ATR below VWAP")
        if stretch >= self.vwap_stretch_atr:
            return Signal("vwap_stretch", "short", min(1.0, abs(stretch) / 4), f"{stretch:.1f} ATR above VWAP")
        return None

    def _stochastic_cross(self, i: int) -> Optional[Signal]:
        if i < 1 or self.stoch_k[i] is None or self.stoch_d[i] is None:
            return None
        if self.stoch_k[i - 1] is None or self.stoch_d[i - 1] is None:
            return None
        k0, d0, k1, d1 = self.stoch_k[i - 1], self.stoch_d[i - 1], self.stoch_k[i], self.stoch_d[i]
        if k0 <= d0 and k1 > d1 and k1 < 25:
            return Signal("stochastic_cross", "long", 0.5, "bullish stoch cross < 25")
        if k0 >= d0 and k1 < d1 and k1 > 75:
            return Signal("stochastic_cross", "short", 0.5, "bearish stoch cross > 75")
        return None

    def _key_level_rejection(self, i: int) -> Optional[Signal]:
        piv = self._pivots.get(self.bars[i].timestamp.date())
        if piv is None or self.atr[i] is None:
            return None
        tol = self.atr[i] * self.level_tol_atr
        b = self.bars[i]
        for name, level in piv.as_dict().items():
            near_low = abs(b.low - level) <= tol
            near_high = abs(b.high - level) <= tol
            if name.startswith("S") and near_low and b.close > level and b.lower_wick > b.body:
                return Signal("key_level_rejection", "long", 0.7, f"rejection of support {name}")
            if name.startswith("R") and near_high and b.close < level and b.upper_wick > b.body:
                return Signal("key_level_rejection", "short", 0.7, f"rejection of resistance {name}")
        return None

    # ----------------------------------------------------------------- combine
    def evaluate(self, i: int) -> Optional[ReversalSetup]:
        """Return the reversal setup at bar ``i`` (or ``None`` if nothing fires)."""
        detectors = [
            self._candlestick, self._rsi_turn, self._rsi_divergence,
            self._double_extreme, self._bollinger_reversion, self._vwap_stretch,
            self._stochastic_cross, self._key_level_rejection,
        ]
        signals: List[Signal] = []
        for det in detectors:
            sig = det(i)
            if sig is not None:
                signals.append(sig)
        if not signals:
            return None

        long_total = sum(WEIGHTS[s.source] * s.strength for s in signals if s.direction == "long")
        short_total = sum(WEIGHTS[s.source] * s.strength for s in signals if s.direction == "short")
        if long_total == short_total:
            return None
        direction = "long" if long_total > short_total else "short"
        dominant, other = max(long_total, short_total), min(long_total, short_total)
        # Penalize conflicting signals, then normalize onto a usable 0..100 axis.
        raw = dominant - 0.5 * other
        score = max(0.0, min(100.0, 100.0 * raw / SCORE_NORMALIZER))
        components = [s for s in signals if s.direction == direction]

        return ReversalSetup(
            index=i,
            timestamp=self.bars[i].timestamp,
            direction=direction,
            confluence=round(score, 1),
            price=self.bars[i].close,
            atr=self.atr[i],
            components=components,
        )

    def scan(self, min_confluence: float = 0.0, start: int = 0) -> List[ReversalSetup]:
        """All reversal setups at or above ``min_confluence``, oldest first."""
        out: List[ReversalSetup] = []
        for i in range(max(start, 1), self.n):
            setup = self.evaluate(i)
            if setup and setup.confluence >= min_confluence:
                out.append(setup)
        return out

    def latest(self, min_confluence: float = 0.0, lookback: int = 10) -> Optional[ReversalSetup]:
        """Most recent setup within the last ``lookback`` bars, if any."""
        for i in range(self.n - 1, max(self.n - 1 - lookback, 0), -1):
            setup = self.evaluate(i)
            if setup and setup.confluence >= min_confluence:
                return setup
        return None
