"""
Regression test suite for the SPY Day-Trading Analyst skill.

Pure standard-library `unittest` (no pytest, no new dependencies) so it runs
anywhere the skill runs. Covers the invariants that actually matter:

  * indicator correctness on known inputs and alignment/length guarantees,
  * the NO-LOOKAHEAD guarantee (the load-bearing property of the backtester),
  * resample integrity + rejection of upsampling to finer-than-source bars,
  * backtester behavior (threshold gating, direction filter, sane metrics),
  * Monte-Carlo outcome spread, CSV round-trip, deterministic synthetic data.

Run:  python3 -m unittest test_skill -v      (from the skill folder)
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import indicators as ind
from indicators import Bar
import data_provider as dp
from reversals import ReversalEngine
from backtester import Backtester, BacktestConfig, monte_carlo


class TestIndicators(unittest.TestCase):
    def test_sma_known_values(self):
        self.assertEqual(ind.sma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_ema_length_and_warmup(self):
        vals = list(range(1, 21))
        out = ind.ema(vals, 5)
        self.assertEqual(len(out), len(vals))
        self.assertTrue(all(v is None for v in out[:4]))
        self.assertIsNotNone(out[4])

    def test_rsi_bounds_and_uptrend(self):
        rising = [float(i) for i in range(1, 40)]
        r = ind.rsi(rising, 14)
        defined = [v for v in r if v is not None]
        self.assertTrue(all(0.0 <= v <= 100.0 for v in defined))
        self.assertAlmostEqual(r[-1], 100.0)  # no losses -> RSI 100

    def test_atr_non_negative(self):
        bars = dp.generate_synthetic(days=3, seed=1)
        a = ind.atr(bars, 14)
        self.assertTrue(all(v >= 0 for v in a if v is not None))

    def test_vwap_first_equals_typical(self):
        bars = dp.generate_synthetic(days=1, seed=1)
        v = ind.session_vwap(bars)
        self.assertAlmostEqual(v[0], bars[0].typical, places=6)

    def test_pivots_monotonic(self):
        p = ind.classic_pivots(110.0, 90.0, 100.0)
        ordered = [p.s3, p.s2, p.s1, p.pp, p.r1, p.r2, p.r3]
        self.assertEqual(ordered, sorted(ordered))

    def test_swing_points_detect(self):
        # highs make a clear peak at index 1 and 3; low trough at index 2
        ts = dp.generate_synthetic(days=1, seed=1)[:5]
        highs = [1.0, 3.0, 2.0, 5.0, 1.0]
        lows = [0.0, 2.0, 1.0, 4.0, 0.0]
        bars = [Bar(ts[i].timestamp, lows[i], highs[i], lows[i], highs[i]) for i in range(5)]
        sw = ind.swing_points(bars, left=1, right=1)
        kinds = {(s.index, s.kind) for s in sw}
        self.assertIn((1, "high"), kinds)
        self.assertIn((3, "high"), kinds)
        self.assertIn((2, "low"), kinds)


class TestDataProvider(unittest.TestCase):
    def test_synthetic_deterministic(self):
        a = dp.generate_synthetic(days=5, seed=99)
        b = dp.generate_synthetic(days=5, seed=99)
        self.assertEqual([x.close for x in a], [x.close for x in b])

    def test_resample_ohlc_integrity(self):
        base = dp.generate_synthetic(days=5, seed=2)
        r = dp.resample(base, "15m")
        self.assertLess(len(r), len(base))
        for b in r:
            self.assertGreaterEqual(b.high, b.low)
            self.assertGreaterEqual(b.high, b.open)
            self.assertGreaterEqual(b.high, b.close)
            self.assertLessEqual(b.low, b.open)
            self.assertLessEqual(b.low, b.close)

    def test_resample_daily_one_per_session(self):
        base = dp.generate_synthetic(days=4, seed=2)
        daily = dp.resample(base, "1D")
        dates = {b.timestamp.date() for b in base}
        self.assertEqual(len(daily), len(dates))

    def test_valid_timeframes_rejects_finer(self):
        base = dp.generate_synthetic(days=2, interval_minutes=5, seed=2)
        vt = dp.valid_timeframes(base, ["1m", "5m", "15m", "1D"])
        self.assertNotIn("1m", vt)
        self.assertIn("5m", vt)
        self.assertIn("15m", vt)
        self.assertIn("1D", vt)

    def test_csv_roundtrip(self):
        base = dp.generate_synthetic(days=2, seed=3)
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            path = fh.name
        try:
            dp.save_csv(base, path)
            loaded = dp.load_csv(path)
            self.assertEqual(len(loaded), len(base))
            for a, b in zip(base, loaded):
                self.assertAlmostEqual(a.close, b.close, places=2)
        finally:
            os.unlink(path)


class TestNoLookahead(unittest.TestCase):
    """The single most important guarantee: evaluate(i) must not see the future."""

    def test_evaluate_invariant(self):
        bars = dp.resample(dp.generate_synthetic(days=20, seed=5), "15m")
        full = ReversalEngine(bars)
        for i in (120, 160, 200, 240, 280):
            truncated = ReversalEngine(bars[: i + 1])  # no bars beyond i exist
            a, b = full.evaluate(i), truncated.evaluate(i)
            sa = (a.direction, a.confluence) if a else None
            sb = (b.direction, b.confluence) if b else None
            self.assertEqual(sa, sb, f"lookahead leak at bar {i}: {sa} != {sb}")

    def test_confluence_bounded(self):
        bars = dp.generate_synthetic(days=15, seed=7)
        eng = ReversalEngine(bars)
        for s in eng.scan(min_confluence=0):
            self.assertGreaterEqual(s.confluence, 0.0)
            self.assertLessEqual(s.confluence, 100.0)
            self.assertIn(s.direction, ("long", "short"))


class TestBacktester(unittest.TestCase):
    def setUp(self):
        self.bars = dp.generate_synthetic(days=25, seed=42)

    def test_impossible_threshold_yields_no_trades(self):
        res = Backtester(self.bars, BacktestConfig(min_confluence=200)).run()
        self.assertEqual(res.metrics.get("num_trades", 0), 0)
        self.assertTrue(res.is_empty())

    def test_direction_filter_long_only(self):
        res = Backtester(self.bars, BacktestConfig(min_confluence=55, direction="long")).run()
        self.assertTrue(all(t.direction == "long" for t in res.trades))

    def test_metrics_present_and_sane(self):
        res = Backtester(self.bars, BacktestConfig(min_confluence=55)).run()
        self.assertGreater(res.metrics["num_trades"], 0)
        m = res.metrics
        self.assertEqual(m["wins"] + m["losses"], m["num_trades"])
        self.assertTrue(0.0 <= m["win_rate"] <= 1.0)
        self.assertIsInstance(m["expectancy_R"], float)

    def test_no_overnight_holds_when_flat_by_close(self):
        res = Backtester(self.bars, BacktestConfig(min_confluence=55, flat_by_close=True)).run()
        for t in res.trades:
            self.assertEqual(t.entry_time.date(), t.exit_time.date())

    def test_costs_reduce_pnl(self):
        cheap = Backtester(self.bars, BacktestConfig(min_confluence=55, commission_per_trade=0, slippage_bps=0)).run()
        pricey = Backtester(self.bars, BacktestConfig(min_confluence=55, commission_per_trade=2, slippage_bps=5)).run()
        # Same signals, higher costs => no better net pnl.
        self.assertLessEqual(pricey.metrics["net_pnl_$"], cheap.metrics["net_pnl_$"])

    def test_monte_carlo_spread_ordered(self):
        res = Backtester(self.bars, BacktestConfig(min_confluence=55)).run()
        mc = monte_carlo(res.trades, res.config, runs=500)
        self.assertLessEqual(mc["return_p05_pct"], mc["return_p50_pct"])
        self.assertLessEqual(mc["return_p50_pct"], mc["return_p95_pct"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
