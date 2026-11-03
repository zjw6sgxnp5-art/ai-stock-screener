"""Backtest engine correctness: Wilder ATR, T+1 open fills, gap-down stops, costs, IS/OOS, survivorship."""
import _testdb  # noqa: F401

import math
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from backend import config
from backend.core.indicators import average_true_range
from backend.services import backtester


def _series(n=200, seed=1.0, drift=0.002, gap_day=None, gap_pct=0.0):
    out, d, px = {}, date(2025, 1, 1), 100.0 * seed
    i = 0
    while len(out) < n:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue
        o = px * (1 + 0.003 * math.sin(i))
        if gap_day is not None and i == gap_day:
            o = px * (1 - gap_pct)
        c = o * (1 + drift + 0.01 * math.sin(i * 0.7))
        h, l = max(o, c) * 1.01, min(o, c) * 0.99
        out[d.isoformat()] = {"open": o, "close": c, "high": h, "low": l, "volume": 1e6}
        px = c
        i += 1
    return out


def _fake_fetch(data):
    def f(symbol, range_str="2y", force_refresh=False):
        if symbol == "^VIX":
            return {k: {"open": 15, "close": 15, "high": 15, "low": 15, "volume": 0} for k in data["SPY"]}
        return data.get(symbol, {})
    return f


class TestBacktestEngine(unittest.TestCase):
    def setUp(self):
        self.data = {
            "SPY": _series(seed=1.0, drift=0.0005),
            "AAA": _series(seed=1.0, drift=0.004),
            "BBB": _series(seed=2.0, drift=0.003),
            "CCC": _series(seed=0.5, drift=-0.001),
        }

    def run_bt(self, **kw):
        kw.setdefault("symbols", ["AAA", "BBB", "CCC"])
        kw.setdefault("force_refresh", True)
        with patch.object(backtester, "fetch_yahoo_history", _fake_fetch(self.data)), \
             patch.object(backtester, "set_cache", lambda *a, **k: None):
            return backtester.run_quantitative_backtest(top_n=2, rebalance_freq=10, **kw)

    def test_wilder_atr_matches_live(self):
        bars = list(self.data["AAA"].values())[:61]
        live = average_true_range([b["high"] for b in bars], [b["low"] for b in bars], [b["close"] for b in bars], 14)
        self.assertAlmostEqual(backtester.wilder_atr_from_bars(bars), live, places=6)

    def test_default_atr_mult_from_config(self):
        res = self.run_bt()
        self.assertTrue(res["ok"])
        self.assertEqual(res["assumptions"]["atr_mult"], config.ATR_STOP_MULTIPLIER)

    def test_fills_next_open(self):
        res = self.run_bt()
        buys = [t for t in res["trade_log"] if t["side"] == "BUY"]
        self.assertTrue(buys)
        for t in buys:
            self.assertLess(t["signal_date"], t["date"])
            self.assertAlmostEqual(t["price"], self.data[t["symbol"]][t["date"]]["open"], places=3)

    def test_gap_down_stop_fills_at_open(self):
        res = self.run_bt()
        buy = next(t for t in res["trade_log"] if t["side"] == "BUY" and t["symbol"] == "AAA")
        dates = sorted(self.data["AAA"])
        gap_idx = dates.index(buy["date"]) + 2
        gd = dates[gap_idx]
        bar = self.data["AAA"][gd]
        bar["open"] = buy["stop"] * 0.9
        bar["low"] = bar["open"] * 0.99
        bar["close"] = bar["open"]
        res2 = self.run_bt()
        stops = [t for t in res2["trade_log"] if t["symbol"] == "AAA" and t["date"] == gd and t["reason"].startswith("stop")]
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["reason"], "stop_gap")
        self.assertAlmostEqual(stops[0]["price"], round(bar["open"], 4), places=3)
        self.assertLessEqual(stops[0]["price"], stops[0]["stop"])

    def test_costs_reduce_returns(self):
        free = self.run_bt(cost_bps=0, slippage_bps=0)["performance"]["strategy_total_return_pct"]
        costly = self.run_bt(cost_bps=50, slippage_bps=50)["performance"]["strategy_total_return_pct"]
        self.assertLess(costly, free)
        default = self.run_bt()
        self.assertEqual(default["assumptions"]["cost_bps_per_side"] + default["assumptions"]["slippage_bps_per_side"],
                         config.BACKTEST_COST_BPS + config.BACKTEST_SLIPPAGE_BPS)

    def test_survivorship_warning(self):
        res = self.run_bt()
        w = res["survivorship_warning"]
        self.assertTrue(w["has_bias"])
        self.assertFalse(w["is_default_universe"])
        self.assertIn("幸存者偏差", w["message"])
        self.assertEqual(res["assumptions"]["universe"], ["AAA", "BBB", "CCC"])

    def test_window_split(self):
        full = self.run_bt()
        ins = self.run_bt(window=(0.0, 0.6))
        oos = self.run_bt(window=(0.6, 1.0))
        self.assertEqual(ins["period"]["start_date"], full["period"]["start_date"])
        self.assertEqual(oos["period"]["end_date"], full["period"]["end_date"])
        self.assertLess(ins["period"]["end_date"], oos["period"]["start_date"])

    def test_sensitivity_is_oos(self):
        with patch.object(backtester, "fetch_yahoo_history", _fake_fetch(self.data)), \
             patch.object(backtester, "set_cache", lambda *a, **k: None), \
             patch.object(backtester, "get_cache", lambda *a, **k: None):
            sens = backtester.run_sensitivity_analysis(symbols=["AAA", "BBB", "CCC"], frequencies=[5, 10],
                                                       atr_multipliers=[2.0, 3.0], force_refresh=True)
        self.assertEqual(sens["optimal"]["selected_on"], "in_sample")
        self.assertIn("out_of_sample", sens["optimal"])
        for cell in sens["grid"].values():
            self.assertEqual(cell["sample"], "in_sample")
            self.assertIn("sharpe", cell["oos"])
        self.assertLess(sens["sample_split"]["in_sample_period"]["end_date"],
                        sens["sample_split"]["out_of_sample_period"]["start_date"])


if __name__ == "__main__":
    unittest.main()
