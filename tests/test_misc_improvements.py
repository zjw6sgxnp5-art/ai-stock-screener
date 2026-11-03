import os
import tempfile

os.environ.setdefault("AI_STOCK_DB", os.path.join(tempfile.mkdtemp(prefix="ai_stock_test_"), "test.sqlite"))
import time
import unittest
from unittest import mock

from backend.services import market_data
from backend.config import AppError


class LongbridgeFastFailTest(unittest.TestCase):
    def setUp(self):
        market_data._LB_BIN_CHECK.update({"at": 0.0, "ok": None})

    def tearDown(self):
        market_data._LB_BIN_CHECK.update({"at": 0.0, "ok": None})

    def test_missing_binary_fails_fast_without_pacing_or_subprocess(self):
        with mock.patch.object(market_data.shutil, "which", return_value=None), \
             mock.patch.object(market_data.os.path, "isfile", return_value=False), \
             mock.patch.object(market_data.subprocess, "run") as run:
            t = time.time()
            for _ in range(5):
                with self.assertRaises(AppError) as ctx:
                    market_data.run_longbridge(["quote", "ZZZZ.US", "--format", "json"], ttl_seconds=0)
                self.assertEqual(ctx.exception.status, 503)
            self.assertLess(time.time() - t, 0.4)  # previously ~0.45s pacing per call
            run.assert_not_called()

    def test_binary_check_is_cached(self):
        with mock.patch.object(market_data.shutil, "which", return_value="/usr/bin/longbridge") as which:
            self.assertTrue(market_data.longbridge_binary_available())
            self.assertTrue(market_data.longbridge_binary_available())
            self.assertEqual(which.call_count, 1)




class FrontendYahooModeNoticeTest(unittest.TestCase):
    def test_app_js_checks_longbridge_status_and_shows_notice(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parent.parent / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("/api/datasources/longbridge/status", js)
        self.assertIn("yahooModeNoticeHtml()", js)
        self.assertIn("applyYahooModeNotice();", js)


class CliTimeoutMessageTest(unittest.TestCase):
    def test_timeout_message_reports_actual_timeout(self):
        import subprocess
        from backend.services import ai_engine
        with mock.patch.object(ai_engine, "get_cache", return_value=None), \
             mock.patch.object(ai_engine, "set_cache", create=True), \
             mock.patch.object(ai_engine.subprocess, "run", side_effect=subprocess.TimeoutExpired("gemini", 7)):
            res = ai_engine.run_cli_model("gemini", "hi", timeout=7)
        self.assertIn("7 秒内", str(res))


if __name__ == "__main__":
    unittest.main()
