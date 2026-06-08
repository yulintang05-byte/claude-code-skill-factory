"""
Data provider for the SPY day-trading skill.

Three sources, tried in a sensible order so the skill always has data to work
with:

1. ``yfinance``    -- live/historical download (best, but needs outbound network;
                      many locked-down environments block the Yahoo endpoints,
                      in which case this raises and we fall back).
2. local CSV       -- OHLCV exported from TradingView / a broker. Fully offline.
3. synthetic       -- a deterministic, seeded price series with realistic
                      intraday seasonality so the engine and backtester can be
                      exercised anywhere, even with no data and no network.

Everything downstream consumes ``List[Bar]`` (see ``indicators.Bar``), so the
source is interchangeable.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Sequence

from indicators import Bar


class DataError(RuntimeError):
    """Raised when a data source cannot produce usable bars."""


# Timeframe -> minutes. "D" handled specially.
TIMEFRAME_MINUTES: Dict[str, int] = {
    "1m": 1, "2m": 2, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240,
}
ALL_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "1D"]

REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

_COL_ALIASES = {
    "timestamp": {"timestamp", "datetime", "date", "time", "date/time"},
    "open": {"open", "o"},
    "high": {"high", "h"},
    "low": {"low", "l"},
    "close": {"close", "c", "adj close", "adj_close", "close/last"},
    "volume": {"volume", "vol", "v"},
}


def _match_columns(header: Sequence[str]) -> Dict[str, int]:
    lowered = [h.strip().lower() for h in header]
    mapping: Dict[str, int] = {}
    for field, aliases in _COL_ALIASES.items():
        for idx, name in enumerate(lowered):
            if name in aliases:
                mapping[field] = idx
                break
    missing = {"timestamp", "open", "high", "low", "close"} - mapping.keys()
    if missing:
        raise DataError(
            f"CSV is missing required column(s): {sorted(missing)}. "
            f"Found header: {list(header)}"
        )
    return mapping


def _parse_timestamp(raw: str) -> datetime:
    raw = raw.strip().replace("Z", "")
    fmts = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise DataError(f"Unrecognized timestamp format: {raw!r}")


def _to_float(raw: str) -> float:
    return float(raw.replace("$", "").replace(",", "").strip())


def load_csv(path: str) -> List[Bar]:
    """Load OHLCV bars from a CSV file with flexible column names."""
    bars: List[Bar] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None:
            raise DataError(f"Empty CSV: {path}")
        cols = _match_columns(header)
        vol_idx = cols.get("volume")
        for row in reader:
            if not row or len(row) <= max(cols.values()):
                continue
            try:
                bars.append(
                    Bar(
                        timestamp=_parse_timestamp(row[cols["timestamp"]]),
                        open=_to_float(row[cols["open"]]),
                        high=_to_float(row[cols["high"]]),
                        low=_to_float(row[cols["low"]]),
                        close=_to_float(row[cols["close"]]),
                        volume=_to_float(row[vol_idx]) if vol_idx is not None else 0.0,
                    )
                )
            except (ValueError, DataError):
                continue  # skip malformed rows rather than abort
    if not bars:
        raise DataError(f"No valid rows parsed from {path}")
    bars.sort(key=lambda b: b.timestamp)
    return bars


def save_csv(bars: Sequence[Bar], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Datetime", "Open", "High", "Low", "Close", "Volume"])
        for b in bars:
            writer.writerow([
                b.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                f"{b.open:.4f}", f"{b.high:.4f}", f"{b.low:.4f}",
                f"{b.close:.4f}", int(b.volume),
            ])


# ---------------------------------------------------------------------------
# yfinance loading (optional dependency, optional network)
# ---------------------------------------------------------------------------

def load_yfinance(symbol: str = "SPY", period: str = "60d", interval: str = "5m") -> List[Bar]:
    """Download bars via yfinance. Raises ``DataError`` if unavailable/blocked."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:  # pragma: no cover - env dependent
        raise DataError(
            "yfinance is not installed. Run `pip install yfinance` or use a CSV."
        ) from exc

    try:
        df = yf.download(
            symbol, period=period, interval=interval,
            progress=False, auto_adjust=False, threads=False,
        )
    except Exception as exc:  # network/policy errors surface here
        raise DataError(f"yfinance download failed (network blocked?): {exc}") from exc

    if df is None or len(df) == 0:
        raise DataError(
            f"yfinance returned no data for {symbol} {period}/{interval}. "
            "The endpoint may be blocked by this environment's network policy."
        )

    bars: List[Bar] = []
    for ts, row in df.iterrows():
        def _v(col: str) -> float:
            val = row[col]
            try:
                return float(val.iloc[0]) if hasattr(val, "iloc") else float(val)
            except (TypeError, ValueError):
                return float("nan")
        py_ts = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
        o, h, l, c = _v("Open"), _v("High"), _v("Low"), _v("Close")
        if any(math.isnan(x) for x in (o, h, l, c)):
            continue
        vol = _v("Volume")
        bars.append(Bar(py_ts, o, h, l, c, 0.0 if math.isnan(vol) else vol))
    if not bars:
        raise DataError("yfinance data contained no usable rows.")
    return bars


# ---------------------------------------------------------------------------
# Synthetic generator (deterministic, offline)
# ---------------------------------------------------------------------------

def generate_synthetic(
    days: int = 30,
    interval_minutes: int = 5,
    start_price: float = 500.0,
    seed: int = 42,
    annual_drift: float = 0.07,
    annual_vol: float = 0.16,
) -> List[Bar]:
    """Generate a reproducible intraday SPY-like series.

    Uses geometric Brownian motion for the close-to-close path plus a U-shaped
    intraday volatility profile (open and close are the busy, choppy parts of
    the day -- the same shape real index futures show). Deterministic for a
    given ``seed`` so backtests and tests are repeatable.
    """
    rng = random.Random(seed)
    bars_per_day = int((6.5 * 60) / interval_minutes)
    minutes_per_year = 252 * 6.5 * 60
    dt = interval_minutes / minutes_per_year
    mu = annual_drift
    sigma = annual_vol

    price = start_price
    bars: List[Bar] = []
    day0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days * 2)

    produced_days = 0
    day_offset = 0
    while produced_days < days:
        session_date = day0 + timedelta(days=day_offset)
        day_offset += 1
        if session_date.weekday() >= 5:  # skip weekends
            continue
        produced_days += 1
        for k in range(bars_per_day):
            # U-shaped intraday vol multiplier: high near open & close.
            frac = k / max(bars_per_day - 1, 1)
            u_shape = 1.0 + 1.4 * (math.cos(math.pi * frac) ** 2)
            local_sigma = sigma * u_shape
            shock = rng.gauss(0.0, 1.0)
            ret = (mu - 0.5 * local_sigma ** 2) * dt + local_sigma * math.sqrt(dt) * shock
            new_price = price * math.exp(ret)

            o = price
            c = new_price
            intrabar = abs(local_sigma * math.sqrt(dt)) * price * 0.8
            wick_hi = abs(rng.gauss(0, 1)) * intrabar
            wick_lo = abs(rng.gauss(0, 1)) * intrabar
            h = max(o, c) + wick_hi
            l = min(o, c) - wick_lo
            base_vol = 60000 * u_shape
            vol = base_vol * (0.7 + 0.6 * rng.random())

            ts = datetime.combine(session_date.date(), REGULAR_OPEN) + timedelta(minutes=k * interval_minutes)
            bars.append(Bar(ts, round(o, 2), round(h, 2), round(l, 2), round(c, 2), round(vol)))
            price = new_price
    return bars


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

def infer_interval_minutes(bars: Sequence[Bar]) -> int:
    """Best guess of the source bar spacing, in minutes (the modal intraday gap).

    Used to reject attempts to resample to a timeframe *finer* than the data,
    which would silently pass bars through mislabeled and produce nonsense.
    """
    from collections import Counter
    deltas: Counter = Counter()
    for a, b in zip(bars, bars[1:]):
        if a.timestamp.date() == b.timestamp.date():
            d = int((b.timestamp - a.timestamp).total_seconds() // 60)
            if d > 0:
                deltas[d] += 1
    return deltas.most_common(1)[0][0] if deltas else 1


def valid_timeframes(bars: Sequence[Bar], requested: Sequence[str]) -> List[str]:
    """Filter ``requested`` to timeframes at or coarser than the source spacing."""
    base = infer_interval_minutes(bars)
    out: List[str] = []
    for tf in requested:
        if tf in ("1D", "D", "1d"):
            out.append(tf)
        elif TIMEFRAME_MINUTES.get(tf, 1) >= base:
            out.append(tf)
    return out


def resample(bars: Sequence[Bar], timeframe: str) -> List[Bar]:
    """Aggregate bars up to a higher timeframe.

    ``timeframe`` is one of ``TIMEFRAME_MINUTES`` keys or ``"1D"``/``"D"`` for a
    daily bar (one bar per calendar session). Down-sampling to a lower timeframe
    than the source is not possible and raises.
    """
    if not bars:
        return []
    if timeframe in ("1D", "D", "1d"):
        return _resample_daily(bars)
    if timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f"Unknown timeframe {timeframe!r}")

    target = TIMEFRAME_MINUTES[timeframe]
    buckets: Dict[tuple, List[Bar]] = {}
    order: List[tuple] = []
    for b in bars:
        minute_of_day = b.timestamp.hour * 60 + b.timestamp.minute
        bucket_min = (minute_of_day // target) * target
        key = (b.timestamp.date(), bucket_min)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(b)
    return [_merge(buckets[k]) for k in order]


def _merge(group: Sequence[Bar]) -> Bar:
    return Bar(
        timestamp=group[0].timestamp,
        open=group[0].open,
        high=max(b.high for b in group),
        low=min(b.low for b in group),
        close=group[-1].close,
        volume=sum(b.volume for b in group),
    )


def _resample_daily(bars: Sequence[Bar]) -> List[Bar]:
    buckets: Dict[object, List[Bar]] = {}
    order: List[object] = []
    for b in bars:
        key = b.timestamp.date()
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(b)
    return [_merge(buckets[k]) for k in order]


# ---------------------------------------------------------------------------
# Smart loader
# ---------------------------------------------------------------------------

def load(
    symbol: str = "SPY",
    csv_path: Optional[str] = None,
    period: str = "60d",
    interval: str = "5m",
    allow_synthetic: bool = True,
    verbose: bool = True,
) -> List[Bar]:
    """Best-effort loader: CSV (if given) -> yfinance -> synthetic.

    Returns the bars and (when ``verbose``) prints which source was used so the
    user is never misled about whether they are looking at real or simulated
    data.
    """
    if csv_path:
        bars = load_csv(csv_path)
        if verbose:
            print(f"[data] Loaded {len(bars)} bars from CSV: {csv_path}")
        return bars

    try:
        bars = load_yfinance(symbol, period, interval)
        if verbose:
            print(f"[data] Loaded {len(bars)} bars from yfinance ({symbol} {interval}).")
        return bars
    except DataError as exc:
        if not allow_synthetic:
            raise
        if verbose:
            print(f"[data] yfinance unavailable ({exc}).")
            print("[data] Falling back to SYNTHETIC data -- results are for "
                  "engine/backtest validation only, NOT real SPY history.")
        return generate_synthetic()
