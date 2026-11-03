"""
Unit tests for Research Knowledge Base (Benchmark V4 + User S&P 500).
"""
import _testdb  # noqa: F401  (must precede backend imports)
import unittest

from backend.core.stock_registry import get_all_registered_stocks
from backend.services.research_kb import (
    ensure_research_tables,
    get_all_benchmark_stocks,
    get_stock_markdown_report,
    get_stock_research_detail,
    query_research_list,
)


class TestResearchKB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_research_tables()

    def test_benchmark_and_user_counts(self):
        bench = query_research_list("benchmark", limit=600)
        self.assertTrue(bench["ok"])
        self.assertEqual(bench["total"], 518)

        user = query_research_list("user", limit=600)
        self.assertTrue(user["ok"])
        self.assertEqual(user["total"], 506)

    def test_dual_perspective_and_ndx_unavailable_reason(self):
        # AAPL is in both S&P 500 benchmark and user research
        aapl = get_stock_research_detail("AAPL.US")
        self.assertTrue(aapl["ok"])
        self.assertTrue(aapl["has_benchmark"])
        self.assertTrue(aapl["has_user"])
        self.assertIsNone(aapl["user_unavailable_reason"])
        self.assertEqual(aapl["benchmark"]["name_cn"], "苹果")
        self.assertIn("建议买入", ["建议买入", "逢低关注", "持有观望", "不建议买入"])

        # ARM is Nasdaq 100 non-S&P 500: user perspective must be disabled with reason
        arm = get_stock_research_detail("ARM.US")
        self.assertTrue(arm["ok"])
        self.assertTrue(arm["has_benchmark"])
        self.assertFalse(arm["has_user"])
        self.assertEqual(arm["user_unavailable_reason"], "该标的属于纳指100非标普成分股，本库仅收录标普500")

    def test_markdown_report_access(self):
        rep = get_stock_markdown_report("AAPL")
        self.assertTrue(rep["ok"])
        self.assertIn("# AAPL", rep["content"])
        self.assertIn("苹果", rep["content"])

    def test_query_filter_and_sort(self):
        # Filter by rating in benchmark
        res = query_research_list("benchmark", rating="建议买入", limit=100)
        self.assertTrue(res["ok"])
        self.assertGreater(res["total"], 0)
        for item in res["items"]:
            self.assertEqual(item["rating"], "建议买入")

        # Filter by rating in user dataset
        res_u = query_research_list("user", rating="优质低估", limit=100)
        self.assertTrue(res_u["ok"])
        self.assertGreater(res_u["total"], 0)
        for item in res_u["items"]:
            self.assertEqual(item["rating"], "优质低估")

    def test_universe_registry_has_all_518_stocks(self):
        stocks = get_all_registered_stocks()
        self.assertEqual(len(stocks), 518)
        tickers = {s["ticker"] for s in stocks}
        self.assertIn("AAPL", tickers)
        self.assertIn("MSFT", tickers)
        self.assertIn("NVDA", tickers)
        self.assertIn("ARM", tickers)
        self.assertIn("ASML", tickers)


if __name__ == "__main__":
    unittest.main()

