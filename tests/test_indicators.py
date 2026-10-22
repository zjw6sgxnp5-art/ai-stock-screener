"""
Unit tests for technical indicators in backend/core/indicators.py.
"""
import math
import unittest

from backend.core.indicators import (
    annualized_volatility,
    average_true_range,
    bollinger_bands,
    compute_technical_summary,
    max_drawdown,
    moving_average,
    pct_change,
    rsi,
)


class TestIndicators(unittest.TestCase):
    def test_moving_average(self):
        # Window larger than data
        self.assertIsNone(moving_average([1.0, 2.0], 5))
        # Exact window
        self.assertEqual(moving_average([10.0, 20.0, 30.0], 3), 20.0)
        # Sliding window takes the last N items
        self.assertEqual(moving_average([100.0, 10.0, 20.0, 30.0], 3), 20.0)

    def test_pct_change(self):
        values = [100.0, 105.0, 110.0]
        # 1-period change from 105 to 110: (110 / 105 - 1) * 100
        change = pct_change(values, 1)
        self.assertAlmostEqual(change, (110.0 / 105.0 - 1) * 100, places=4)
        # 2-period change from 100 to 110: (110 / 100 - 1) * 100 = 10%
        self.assertAlmostEqual(pct_change(values, 2), 10.0, places=4)

    def test_rsi_bounds_and_calculation(self):
        # Monotonically increasing closes should yield RSI = 100.0
        up_closes = [float(i) for i in range(1, 30)]
        self.assertEqual(rsi(up_closes, 14), 100.0)

        # Monotonically decreasing closes should yield RSI close to 0.0
        down_closes = [float(100 - i) for i in range(30)]
        val = rsi(down_closes, 14)
        self.assertIsNotNone(val)
        self.assertAlmostEqual(val, 0.0, places=1)

        # Alternating series
        alt_closes = [100.0 if i % 2 == 0 else 102.0 for i in range(40)]
        alt_rsi = rsi(alt_closes, 14)
        self.assertIsNotNone(alt_rsi)
        self.assertTrue(0 <= alt_rsi <= 100)

    def test_average_true_range(self):
        # Constant bar with high-low=2.0, close=100
        highs = [102.0] * 20
        lows = [100.0] * 20
        closes = [101.0] * 20
        atr = average_true_range(highs, lows, closes, 14)
        self.assertIsNotNone(atr)
        self.assertAlmostEqual(atr, 2.0, places=2)

    def test_max_drawdown(self):
        # Peak at 100, drops to 80 -> -20%
        series = [50.0, 100.0, 90.0, 80.0, 85.0]
        mdd = max_drawdown(series, 5)
        self.assertIsNotNone(mdd)
        self.assertAlmostEqual(mdd, -20.0, places=2)

    def test_bollinger_bands(self):
        # Constant series
        series = [50.0] * 30
        bb = bollinger_bands(series, 20, 2.0)
        self.assertIsNotNone(bb)
        self.assertEqual(bb["middle"], 50.0)
        self.assertEqual(bb["upper"], 50.0)
        self.assertEqual(bb["lower"], 50.0)
        self.assertEqual(bb["bandwidth"], 0.0)

    def test_compute_technical_summary(self):
        # Generate 65 synthetic daily bars
        klines = []
        for i in range(1, 70):
            p = 100.0 + i * 0.5
            klines.append({
                "timestamp": 1700000000 + i * 86400,
                "open": p - 0.2,
                "high": p + 1.0,
                "low": p - 1.0,
                "close": p,
                "volume": 1000000.0 + i * 1000,
            })
        summary = compute_technical_summary(klines)
        self.assertEqual(summary["candles"], 69)
        self.assertIsNotNone(summary["last_close"])
        self.assertIsNotNone(summary["ma20"])
        self.assertIsNotNone(summary["ma60"])
        self.assertTrue(summary["above_ma20"])
        self.assertTrue(summary["above_ma60"])
        self.assertIsNotNone(summary["atr14"])
        self.assertIsNotNone(summary["trailing_stop_2atr"])
        # Trailing stop must be strictly below current last close
        self.assertLess(summary["trailing_stop_2atr"], summary["last_close"])


if __name__ == "__main__":
    unittest.main()
