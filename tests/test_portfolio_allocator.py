import _testdb  # noqa: F401
"""
Unit tests for ATR risk parity portfolio allocation and sector cap constraints.
"""
import unittest

from backend.db import ensure_db
from backend.services.portfolio_allocator import (
    calculate_portfolio_allocation,
    estimate_atr,
    generate_derivative_hedge,
    inspect_existing_holdings,
)


class TestPortfolioAllocator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_db()

    def test_inspect_existing_holdings(self):
        holdings = [
            {"symbol": "NVDA.US", "shares": 100, "current_price": 130.0},
            {"symbol": "AMD.US", "shares": 500, "current_price": 160.0},
            {"symbol": "AAPL.US", "shares": 50, "current_price": 220.0},
        ]
        report = inspect_existing_holdings(holdings, max_sector_exposure_pct=30.0)
        self.assertTrue(report["ok"])
        positions = report["positions"]
        self.assertEqual(len(positions), 3)
        for item in positions:
            self.assertIn("symbol", item)
            self.assertIn("price", item)
            self.assertIn("stop_loss_2atr", item)
            self.assertIn("dist_to_stop_pct", item)
            self.assertIn("is_broken_stop", item)
            self.assertIn("is_sector_overweight", item)
            self.assertGreater(item["price"], 0)
            self.assertGreater(item["stop_loss_2atr"], 0)
            self.assertLess(item["stop_loss_2atr"], item["price"])

    def test_estimate_atr(self):
        # Fallback ATR when technical is empty (2.8% of price)
        atr_fallback = estimate_atr(100.0, {})
        self.assertAlmostEqual(atr_fallback, 2.8, places=2)

        # Estimate from volatility
        atr_from_vol = estimate_atr(200.0, {"volatility_20d": 32.0})
        self.assertGreater(atr_from_vol, 0.5)

    def test_derivative_hedge_genuine_spot_discipline(self):
        hedge = generate_derivative_hedge(
            symbol="NVDA.US",
            last_price=200.0,
            beta=1.8,
            iv_rank=45,
            atr=5.0,
            stop_price=190.0,
            stop_loss_pct=5.0,
        )
        self.assertEqual(hedge["strategy"], "现货动态 2xATR 跟踪防守")
        self.assertIsNone(hedge["recommended_strike"])
        self.assertEqual(hedge["est_cost_per_share"], 0.0)
        self.assertIn("真实 2×ATR 跟踪止损", hedge["risk_notice"])

    def test_risk_parity_and_sector_cap_enforcement(self):
        # Total capital = 100,000, risk per trade = 1.5% ($1,500)
        # Sector cap = 30% ($30,000), single stock cap = 25% ($25,000)
        candidates = [
            # Candidate 1: Tech/Semis
            {
                "symbol": "NVDA.US",
                "last": 200.0,
                "atr14": 5.0,  # 2*ATR = 10.0 -> raw shares = 1500 / 10 = 150 -> $30,000 capital (hits single stock cap 25k -> 125 shares)
            },
            # Candidate 2: Same sector (Semis)
            {
                "symbol": "AMD.US",
                "last": 100.0,
                "atr14": 3.0,  # 2*ATR = 6.0 -> raw shares = 1500 / 6 = 250 -> $25,000 capital
                # Sector capacity remaining: $30,000 - $25,000 = $5,000 -> 50 shares -> triggers sector cap!
            },
            # Candidate 3: Software
            {
                "symbol": "MSFT.US",
                "last": 400.0,
                "atr14": 6.0,  # 2*ATR = 12.0 -> raw shares = 1500 / 12 = 125 -> $50,000 (hits single cap 25k -> 62 shares = $24,800)
            },
        ]

        result = calculate_portfolio_allocation(
            candidates=candidates,
            total_capital=100000.0,
            risk_per_trade_pct=1.5,
            max_sector_exposure_pct=30.0,
            max_single_stock_pct=25.0,
            macro_exposure_limit_pct=80.0,
        )

        self.assertEqual(result["total_capital"], 100000.0)
        allocations = result["allocations"]
        self.assertEqual(len(allocations), 3)

        nvda_alloc = next(a for a in allocations if "NVDA" in a["symbol"])
        amd_alloc = next(a for a in allocations if "AMD" in a["symbol"])
        msft_alloc = next(a for a in allocations if "MSFT" in a["symbol"])

        # NVDA single stock cap check: invested amount <= 25,000
        self.assertLessEqual(nvda_alloc["invested_amount"], 25000.0)
        self.assertFalse(nvda_alloc["sector_cap_triggered"])

        # AMD shares the same semiconductor sector as NVDA.
        # Combined capital must not exceed sector limit $30,000!
        semis_total = nvda_alloc["invested_amount"] + amd_alloc["invested_amount"]
        self.assertLessEqual(semis_total, 30000.0)
        self.assertTrue(amd_alloc["sector_cap_triggered"])

        # Cash reserve check
        self.assertGreater(result["cash_reserve"], 0)
        self.assertAlmostEqual(
            result["total_invested"] + result["cash_reserve"],
            result["total_capital"],
            places=1,
        )


if __name__ == "__main__":
    unittest.main()
