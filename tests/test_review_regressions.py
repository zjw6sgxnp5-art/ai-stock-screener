"""Regression tests for review bugs: report export / CLI memo None-safety and Calmar sign."""
import _testdb  # noqa: F401
import unittest
from unittest import mock

from backend.services import ai_engine, backtester, market_data


def _fallback_bundle(symbol="NVDA.US"):
    # Mirrors the Yahoo-fallback shape: None-valued score sub-keys, list short_positions
    return {
        "symbol": symbol,
        "generated_at": "2026-11-03T00:00:00+00:00",
        "quote": {"symbol": symbol, "last": 200.0, "change_pct": -1.0},
        "technical": {"trailing_stop_2atr": 190.0},
        "valuation": None,
        "financials": None,
        "rating": None,
        "company": None,
        "risk_radar": {"controversies": [], "thesis_breakers": [], "short_positions": []},
        "score": {"score": None, "verdict": "数据不足，不能评级", "factor_breakdown": None,
                  "positives": [], "risks": []},
    }


class TestReviewRegressions(unittest.TestCase):
    def test_report_export_with_null_factor_breakdown(self):
        with mock.patch.object(market_data, "latest_analysis_payload", return_value=_fallback_bundle()):
            res = market_data.export_markdown_report("NVDA")
        self.assertTrue(res["ok"])
        self.assertIn("NVDA.US", res["content"])

    def test_cli_analysis_without_llm_returns_pending_review(self):
        fake_macro = {"spy": None, "vix": None, "regime": None}
        with mock.patch.object(ai_engine, "fetch_stock_bundle", return_value=_fallback_bundle()), \
             mock.patch.object(ai_engine, "get_macro_climate", return_value=fake_macro), \
             mock.patch.object(ai_engine, "run_cli_model",
                               return_value={"ok": False, "text": "【GROK CLI 未生成有效研判】", "error": True}):
            res = ai_engine.run_cli_analysis_for_symbol("NVDA.US", model_name="grok")
        self.assertFalse(res["ok"])
        self.assertEqual(res["review_status"], "PENDING_REVIEW")
        self.assertIn("待人工复核", res["rating_label"])
        self.assertIsNone(res["snapshot_id"])

    def test_calmar_sign_matches_cagr(self):
        # Deterministic synthetic market: steady decline => negative CAGR => negative Calmar
        dates = [f"2025-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(200)]

        def series(start, step):
            out = {}
            for i, d in enumerate(dates):
                c = start * (1 + step) ** i
                out[d] = {"open": c, "high": c * 1.01, "low": c * 0.995, "close": c}
            return out

        def fake_hist(sym, range_str, force_refresh=False):
            if sym == "^VIX":
                return {d: {"open": 15, "high": 15, "low": 15, "close": 15} for d in dates}
            if sym == "SPY":
                return series(100, 0.0005)
            return series(100, -0.002 if sym == "AAA" else 0.001)

        with mock.patch.object(backtester, "fetch_yahoo_history", side_effect=fake_hist), \
             mock.patch.object(backtester, "get_cache", return_value=None), \
             mock.patch.object(backtester, "set_cache", return_value=None):
            res = backtester.run_quantitative_backtest(
                symbols=["AAA", "BBB"], benchmark_symbol="SPY", range_str="1y",
                rebalance_freq=10, top_n=1, atr_mult=2.0, force_refresh=True)
        perf = res["backtest"]["performance"]
        cagr, calmar = perf["strategy_cagr_pct"], perf["calmar_ratio"]
        if cagr != 0 and perf["max_drawdown_pct"] < 0:
            self.assertEqual(cagr > 0, calmar > 0, f"cagr={cagr} calmar={calmar}")
        if perf["max_drawdown_pct"] < 0:
            self.assertAlmostEqual(calmar, cagr / abs(perf["max_drawdown_pct"]), delta=max(0.02, abs(calmar) * 0.01))

    def test_calmar_ratio_formula(self):
        # The exact case seen in review: CAGR -6.64%, MDD -15.93% used to report +0.42
        self.assertAlmostEqual(backtester.calmar_ratio(-6.64, -15.93), -0.4168, places=3)
        self.assertAlmostEqual(backtester.calmar_ratio(12.0, -10.0), 1.2)
        self.assertEqual(backtester.calmar_ratio(5.0, 0.0), 0.0)
        self.assertEqual(backtester.calmar_ratio(5.0, None), 0.0)


if __name__ == "__main__":
    unittest.main()
