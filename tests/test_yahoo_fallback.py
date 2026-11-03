"""
Unit tests for Yahoo Finance resilient data fallback service.
"""
import unittest

from backend.db import ensure_db
from backend.services.market_data import (
    fetch_yahoo_klines,
    fetch_yahoo_quotes_batch,
    fetch_yahoo_stock_bundle,
)


class TestYahooFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_db()

    def test_fetch_yahoo_quotes_batch(self):
        # Batch fetch for 2 mainstream symbols
        symbols = ["AAPL.US", "MSFT.US"]
        quotes = fetch_yahoo_quotes_batch(symbols, timeout=8)
        self.assertIn("AAPL.US", quotes)
        self.assertIn("MSFT.US", quotes)

        aapl = quotes["AAPL.US"]
        self.assertIsNotNone(aapl.get("last"))
        self.assertGreater(aapl["last"], 0)
        self.assertEqual(aapl["source"], "yahoo_finance")
        self.assertEqual(aapl["data_status"], "YAHOO_FALLBACK")

    def test_fetch_yahoo_klines(self):
        # Fetch 30 daily bars for NVDA
        klines = fetch_yahoo_klines("NVDA.US", count=30)
        self.assertGreaterEqual(len(klines), 20)
        sample = klines[-1]
        for key in ("timestamp", "open", "high", "low", "close", "volume"):
            self.assertIn(key, sample)
            self.assertIsNotNone(sample[key])
        self.assertGreater(sample["close"], 0)

    def test_fetch_yahoo_stock_bundle(self):
        # Full bundle assembly test
        bundle = fetch_yahoo_stock_bundle("AAPL.US")
        self.assertEqual(bundle["symbol"], "AAPL.US")
        self.assertEqual(bundle["data_status"], "YAHOO_FALLBACK")
        self.assertIn("仅行情", bundle["data_source_badge"])

        # Check required sub-dictionaries
        self.assertIn("quote", bundle)
        self.assertIn("technical", bundle)
        self.assertIn("company", bundle)
        self.assertIn("score", bundle)

        # Technical indicators must be computed from real Yahoo bars
        tech = bundle["technical"]
        self.assertIsNotNone(tech.get("last_close"))
        self.assertIsNotNone(tech.get("ma20"))
        self.assertIsNotNone(tech.get("atr14"))

        # Valuation, rating, financials must be None (no fake numbers)
        self.assertIsNone(bundle.get("valuation"))
        self.assertIsNone(bundle.get("rating"))
        self.assertIsNone(bundle.get("financials"))

        # Score must be None and verdict '数据不足，不能评级'
        score = bundle["score"]
        self.assertIsNone(score.get("score"))
        self.assertEqual(score.get("verdict"), "数据不足，不能评级")


if __name__ == "__main__":
    unittest.main()
