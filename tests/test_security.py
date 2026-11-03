import os
import sys
import tempfile

# Isolated temp DB (must be set before importing backend.*)
os.environ.setdefault("AI_STOCK_DB", os.path.join(tempfile.mkdtemp(prefix="ai_stock_sec_"), "t.sqlite"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.db import ensure_db  # noqa: E402
ensure_db()
import http.client
import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer

from backend.api.router import RequestHandler
from backend.api import security
from backend.config import AppError


class SymbolValidationTest(unittest.TestCase):
    def test_sanitize(self):
        from backend.api.router import sanitize_symbol
        self.assertEqual(sanitize_symbol("aapl"), "AAPL.US")
        self.assertEqual(sanitize_symbol("BRK.B.US"), "BRK.B.US")
        self.assertEqual(sanitize_symbol("", "NVDA.US"), "NVDA.US")
        for bad in ("A;rm -rf", "../etc", "<script>", "A" * 25, 123):
            with self.assertRaises(AppError) as ctx:
                sanitize_symbol(bad, "NVDA.US")
            self.assertEqual(ctx.exception.status, 400)

    def test_list(self):
        from backend.core.utils import is_valid_symbol
        self.assertEqual(security.validate_symbol_list("AAPL, MSFT;NVDA", is_valid_symbol), "AAPL, MSFT;NVDA")
        with self.assertRaises(AppError):
            security.validate_symbol_list("AAPL,BAD|X", is_valid_symbol)


class HostOriginUnitTest(unittest.TestCase):
    def test_hosts(self):
        self.assertTrue(security.host_ok("127.0.0.1:8765"))
        self.assertTrue(security.host_ok("localhost"))
        self.assertTrue(security.host_ok("[::1]:8765"))
        self.assertFalse(security.host_ok("evil.com:8765"))
        self.assertFalse(security.host_ok(None))

    def test_origin(self):
        h = "127.0.0.1:8765"
        self.assertTrue(security.origin_matches("http://127.0.0.1:8765", h))
        self.assertFalse(security.origin_matches("http://evil.com", h))
        self.assertFalse(security.origin_matches("null", h))
        self.assertFalse(security.origin_matches("file://", h))
        # other local port (e.g. a malicious local dev server) is not same-origin
        self.assertFalse(security.origin_matches("http://localhost:3000", h))


class ServerSecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
        cls.port = cls.server.server_address[1]
        RequestHandler.log_message = lambda *a, **k: None
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json"}
        h.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        out = (r.status, dict(r.getheaders()), r.read())
        c.close()
        return out

    def test_no_wildcard_cors(self):
        st, hd, _ = self.req("GET", "/api/health", headers={"Origin": "http://evil.com"})
        self.assertEqual(st, 200)
        self.assertNotIn("Access-Control-Allow-Origin", hd)

    def test_same_origin_write_ok(self):
        origin = f"http://127.0.0.1:{self.port}"
        st, _, b = self.req("POST", "/api/watchlist/add", {"symbol": "AAPL"}, {"Origin": origin})
        self.assertEqual(st, 200, b)
        st, _, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"}, {"Referer": origin + "/"})
        self.assertEqual(st, 200)

    def test_cross_origin_write_rejected(self):
        st, _, _ = self.req("POST", "/api/watchlist/add", {"symbol": "AAPL"}, {"Origin": "http://evil.com"})
        self.assertEqual(st, 403)
        st, _, _ = self.req("POST", "/api/watchlist/add", {"symbol": "AAPL"}, {"Referer": "http://evil.com/x"})
        self.assertEqual(st, 403)
        st, _, _ = self.req("POST", "/api/watchlist/add", {"symbol": "AAPL"}, {"Origin": "null"})
        self.assertEqual(st, 403)

    def test_preflight_rejected_for_foreign_origin(self):
        st, _, _ = self.req("OPTIONS", "/api/watchlist/add", headers={"Origin": "http://evil.com"})
        self.assertEqual(st, 403)

    def test_allowlisted_origin(self):
        os.environ["AI_STOCK_ALLOWED_ORIGINS"] = "http://trusted.example:9000"
        try:
            st, hd, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"},
                                 {"Origin": "http://trusted.example:9000"})
            self.assertEqual(st, 200)
            self.assertEqual(hd.get("Access-Control-Allow-Origin"), "http://trusted.example:9000")
        finally:
            del os.environ["AI_STOCK_ALLOWED_ORIGINS"]

    def test_forged_host_rejected(self):
        st, _, _ = self.req("GET", "/api/watchlist", headers={"Host": "attacker.com"})
        self.assertEqual(st, 403)
        st, _, _ = self.req("GET", "/", headers={"Host": "attacker.com:8765"})
        self.assertEqual(st, 403)

    def test_invalid_symbol_400(self):
        st, _, _ = self.req("GET", "/api/report/export?symbol=AAPL%3Bls")
        self.assertEqual(st, 400)
        st, _, _ = self.req("GET", "/api/compare?symbols=AAPL,%3Cx%3E")
        self.assertEqual(st, 400)
        origin = f"http://127.0.0.1:{self.port}"
        st, _, _ = self.req("POST", "/api/watchlist/add", {"symbol": "../../x"}, {"Origin": origin})
        self.assertEqual(st, 400)

    def test_token(self):
        os.environ["AI_STOCK_API_TOKEN"] = "s3cret"
        try:
            st, _, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"})
            self.assertEqual(st, 401)
            st, _, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"}, {"X-API-Token": "bad"})
            self.assertEqual(st, 401)
            st, _, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"}, {"X-API-Token": "s3cret"})
            self.assertEqual(st, 200)
            st, _, _ = self.req("POST", "/api/watchlist/remove", {"symbol": "AAPL"},
                                {"Authorization": "Bearer s3cret"})
            self.assertEqual(st, 200)
        finally:
            del os.environ["AI_STOCK_API_TOKEN"]


if __name__ == "__main__":
    unittest.main()
