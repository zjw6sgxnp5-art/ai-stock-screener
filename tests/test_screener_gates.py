import _testdb  # noqa: F401
"""
Unit tests for multi-factor screener gates and scoring attribution.
"""
import unittest

from backend.core.financial import build_factor_breakdown
from backend.db import ensure_db
from backend.services.screener import is_liquidity_passed, is_trend_passed


class TestScreenerGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_db()

    def test_liquidity_gate_rules(self):
        # Criteria: turnover >= $300M or volume >= 800k
        liquid_cases = [
            {"turnover": 350_000_000, "volume": 500_000},   # Turnover passes
            {"turnover": 100_000_000, "volume": 1_200_000}, # Volume passes
            {"turnover": 400_000_000, "volume": 900_000},   # Both pass
        ]
        for c in liquid_cases:
            self.assertTrue(is_liquidity_passed(c["turnover"], c["volume"]), f"Expected {c} to pass liquidity gate")

        illiquid_cases = [
            {"turnover": 50_000_000, "volume": 200_000},
            {"turnover": 290_000_000, "volume": 790_000},
            {"turnover": 0, "volume": 0},
        ]
        for c in illiquid_cases:
            self.assertFalse(is_liquidity_passed(c["turnover"], c["volume"]), f"Expected {c} to fail liquidity gate")

    def test_trend_gate_rules(self):
        # Criteria: above_ma20 == True or 20d return > 0
        pass_cases = [
            {"above_ma20": True, "returns": {"20d": -2.5}},
            {"above_ma20": False, "returns": {"20d": 4.2}},
            {"above_ma20": True, "returns": {"20d": 5.0}},
        ]
        for c in pass_cases:
            self.assertTrue(is_trend_passed(c))

        fail_cases = [
            {"above_ma20": False, "returns": {"20d": -0.1}},
            {"above_ma20": False, "returns": {"20d": -15.0}},
            {"above_ma20": False, "returns": {"20d": 0.0}},
            None,
            {},
        ]
        for c in fail_cases:
            self.assertFalse(is_trend_passed(c))

    def test_factor_breakdown_composite_score(self):
        quote = {
            "symbol": "NVDA.US",
            "last": 210.0,
            "turnover": 25_000_000_000,
            "volume": 120_000_000,
            "change_pct": 2.5,
        }
        technical = {
            "last_close": 210.0,
            "ma20": 200.0,
            "ma60": 190.0,
            "above_ma20": True,
            "above_ma60": True,
            "returns": {"5d": 3.0, "20d": 8.0, "60d": 25.0},
            "rsi14": 55.0,
            "atr14": 5.0,
            "atr_pct": 2.38,
            "trailing_stop_2atr": 200.0,
        }
        valuation = {
            "pe": 35.0,
            "industry_median": 30.0,
        }
        rating = {
            "rating": "买入",
            "target_price": 240.0,
            "buy_count": 30,
        }
        financials = {
            "revenue_growth": 25.0,
            "net_margin": 30.0,
        }
        risk_radar = {
            "short_positions": [],
            "controversies": [],
        }

        breakdown = build_factor_breakdown(
            quote=quote,
            technical=technical,
            news=[],
            valuation=valuation,
            rating=rating,
            financials=financials,
            risk_radar=risk_radar,
        )

        composite = breakdown["composite"]
        self.assertGreaterEqual(composite, 0.0)
        self.assertLessEqual(composite, 100.0)
        self.assertIn("factors", breakdown)
        self.assertEqual(len(breakdown["factors"]), 6)  # momentum, liquidity, quality, valuation, catalyst, risk

    def test_screener_verdict_and_numeric_score(self):
        from backend.services.screener import verdict_for_score, _numeric_score, _weakest_factor_text

        self.assertEqual(verdict_for_score(None), "数据不足，不能评级")
        self.assertEqual(verdict_for_score(75.0), "值得重点研究")
        self.assertEqual(verdict_for_score(80.0), "值得重点研究")
        self.assertEqual(verdict_for_score(65.0), "可加入观察")
        self.assertEqual(verdict_for_score(60.0), "可加入观察")
        self.assertEqual(verdict_for_score(59.9), "中性观察")

        self.assertIsNone(_numeric_score(None))
        self.assertIsNone(_numeric_score(False))
        self.assertIsNone(_numeric_score(True))
        self.assertIsNone(_numeric_score("invalid"))
        self.assertEqual(_numeric_score(70), 70.0)
        self.assertEqual(_numeric_score(65.5), 65.5)

        fb = {
            "factors": [
                {"key": "quality", "name": "财务质量", "score": 75.0, "evidence": ["ROE 25%"]},
                {"key": "valuation", "name": "估值合理", "score": 45.0, "evidence": ["PE偏高"]},
                {"key": "catalyst", "name": "催化事件", "score": 10.0, "evidence": ["无催化"]},
                {"key": "risk", "name": "风控惩罚", "score": 0.0}
            ]
        }
        weakest = _weakest_factor_text(fb)
        self.assertIn("估值合理", weakest)
        self.assertIn("45.0", weakest)
        self.assertNotIn("催化事件", weakest)

    def test_non_preset_company_kb_honesty(self):
        from backend.services.company_kb import build_company_and_product_dossier

        company = {
            "name": "Uber Technologies",
            "profile": "Uber Technologies, Inc. 运营出行、外卖及货运技术平台。该公司通过专有技术应用连接消费者与各类出行及物流服务提供商。",
        }
        financials = {
            "indicators": [{"revenue_growth_yoy": 0.159}]
        }

        d = build_company_and_product_dossier("UBER.US", company, financials, force_refresh=True)
        self.assertFalse(d["is_preset"])
        self.assertEqual(d["industry"]["competitors"], [])
        self.assertIn("非预置库标的", d["source_tag"])
        self.assertNotIn("经营造血能力良好", d["industry"]["lifecycle"]["characteristics"])
        self.assertNotIn("主营产品销售与服务网络", d["essence"]["profit_engine"])
        self.assertEqual(d["products"][0]["strategic_role"], "未做人工笔记")


if __name__ == "__main__":
    unittest.main()

