"""Honesty checks for the daily gate, missing scores, and non-preset dossiers."""
import _testdb  # noqa: F401  (must precede backend imports)
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.services.company_kb import infer_dynamic_institutional_dossier
from backend.services.screener import get_daily_screener_recommendations, verdict_for_score


def _candidate(symbol, score, status="LIVE"):
    return {
        "symbol": symbol,
        "name": symbol,
        "last": 100.0,
        "change_pct": 0.4,
        "score": score,
        "verdict": "数据不足，不能评级" if score is None else "可加入观察",
        "technical": {
            "above_ma20": True,
            "returns": {"20d": 1.2},
            "trend_label": "均线上方",
            "atr14": 2.0,
            "trailing_stop_2atr": 96.0,
            "volume_ratio_20d": 1.1,
        },
        "turnover": 1_000_000_000,
        "volume": 2_000_000,
        "liquidity_passed": True,
        "fetch_failed": False,
        "data_status": status,
        "tags": [],
        "rating": {},
        "factor_breakdown": {
            "factors": [
                {"key": "quality", "name": "财务质量", "score": score, "evidence": ["单期利润表"]},
                {"key": "catalyst", "name": "催化", "score": None, "evidence": []},
            ]
        },
    }


class TestDailyHonesty(unittest.TestCase):
    def test_missing_score_is_not_a_rating(self):
        self.assertEqual(verdict_for_score(None), "数据不足，不能评级")
        self.assertEqual(verdict_for_score(58), "中性观察")
        self.assertEqual(verdict_for_score(65), "可加入观察")
        self.assertEqual(verdict_for_score(80), "值得重点研究")

    def _run(self, rows):
        saved = {}

        def fake_set(key, payload, ttl):
            saved["key"] = key
            saved["payload"] = payload
            saved["ttl"] = ttl

        screen = {"all": rows, "errors": []}
        macro = {
            "regime": {
                "code": "NEUTRAL",
                "level": "常态分化期",
                "suggested_exposure": "50% - 70%",
                "strategy_style": "精选绩优白马",
                "action_advice": "精选绩优白马",
                "factor_matrix": {
                    "weights": {
                        "momentum": 15,
                        "catalyst": 15,
                        "quality": 35,
                        "liquidity": 10,
                        "valuation": 25,
                    },
                    "risk_multiplier": 1.0,
                },
            }
        }
        with patch("backend.services.screener.run_screener", return_value=screen), \
             patch("backend.services.screener.get_macro_climate", return_value=macro), \
             patch("backend.services.screener.get_active_factor_config", return_value=(macro["regime"]["factor_matrix"]["weights"], 1.0)), \
             patch("backend.services.screener.list_watchlist", return_value=[{"symbol": "JPM.US"}]), \
             patch("backend.services.screener.get_cache", return_value=None), \
             patch("backend.services.screener.set_cache", side_effect=fake_set):
            result = get_daily_screener_recommendations(force=True)
        return result, saved

    def test_daily_gate_keeps_none_and_drops_58(self):
        result, saved = self._run([
            _candidate("MSFT.US", 70.0, "LIVE"),
            _candidate("KO.US", 58.0, "LIVE"),
            _candidate("JPM.US", None, "LIVE"),
        ])
        symbols = [row["symbol"] for row in result["picks"]]
        self.assertEqual(symbols, ["MSFT.US"])
        self.assertIsNotNone(result["picks"][0]["score"])
        near = {row["symbol"]: row for row in result["near_misses"]}
        self.assertEqual(near["KO.US"]["category"], "NEAR_SCORE")
        self.assertEqual(near["KO.US"]["score"], 58.0)
        self.assertNotIn("KO.US", symbols)
        self.assertEqual(near["JPM.US"]["category"], "UNSCORED")
        self.assertIsNone(near["JPM.US"]["score"])
        self.assertEqual(near["JPM.US"]["verdict"], "数据不足，不能评级")
        self.assertNotEqual(near["JPM.US"]["verdict"], "扫描异常")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertIn(today, saved["key"])
        self.assertIn("JPM.US", saved["key"])
        self.assertEqual(saved["ttl"], 86400)
        self.assertIn("picks", saved["payload"])

    def test_empty_top_is_cached_and_snapshot_only_is_not(self):
        empty, saved_empty = self._run([_candidate("KO.US", 58.0, "LIVE")])
        self.assertEqual(empty["picks"], [])
        self.assertIn("picks", saved_empty["payload"])

        _snapshot, saved_snapshot = self._run([_candidate("MSFT.US", 80.0, "SNAPSHOT")])
        self.assertEqual(saved_snapshot, {})

    def test_non_preset_dossier_does_not_invent_cash_generation(self):
        dossier = infer_dynamic_institutional_dossier(
            "JPM.US",
            {"name": "摩根大通", "profile": "摩根大通是美国大型银行。"},
            {"indicators": [{"name": "营业收入", "yoy": -0.12}]},
        )
        blob = str(dossier)
        self.assertNotIn("经营造血能力良好", blob)
        self.assertNotIn("主营产品销售与服务网络", blob)
        self.assertNotIn("标普500 核心同业集群", blob)
        self.assertEqual(dossier["industry"]["competitors"], [])
        self.assertEqual(dossier["essence"]["profit_engine"], "")
        self.assertEqual(dossier["essence"]["flywheel"], "")
        self.assertIn("-12.0%", dossier["industry"]["lifecycle"]["current_stage"])
        self.assertIn("不据此判断经营质量", dossier["industry"]["lifecycle"]["characteristics"])
        self.assertEqual(dossier["industry"]["lifecycle"]["long_term_strategy"], "单期快照不足以给出配置建议。")
        self.assertFalse(dossier["is_preset"])

        unnamed = infer_dynamic_institutional_dossier("XYZ.US", {"name": "XYZ", "profile": ""}, None)
        self.assertEqual(unnamed["essence"]["summary"], "长桥未返回公司简介")
        self.assertIn("未披露营收同比", unnamed["industry"]["lifecycle"]["current_stage"])
        self.assertEqual(unnamed["industry"]["sector"], "未从公司简介归类")

        chip = infer_dynamic_institutional_dossier(
            "AVGO.US",
            {"name": "Broadcom", "profile": "Broadcom is a semiconductor company."},
            {"indicators": [{"name": "revenue", "yoy": 0.05}]},
        )
        self.assertEqual(chip["industry"]["competitors"], [])
        self.assertNotIn("NVIDIA", str(chip))
        self.assertNotIn("自由现金流", str(chip))


if __name__ == "__main__":
    unittest.main()
