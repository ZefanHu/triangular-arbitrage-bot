#!/usr/bin/env python3
"""
交易数量与资产流转逻辑测试
"""

import os
import sys
import unittest

# 添加项目根目录到path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.trade_executor import TradeExecutor
from models.trade import TradeResult


class TestTradeAmountFlow(unittest.TestCase):
    def test_input_output_assets_buy_sell(self):
        self.assertEqual(
            TradeExecutor._input_output_assets("BTC-USDT", "buy"),
            ("USDT", "BTC")
        )
        self.assertEqual(
            TradeExecutor._input_output_assets("BTC-USDT", "sell"),
            ("BTC", "USDT")
        )

    def test_calc_output_amount_buy(self):
        result = TradeResult(success=True, filled_size=0.5, avg_price=20000)
        asset, amount = TradeExecutor._calc_output_amount("BTC-USDT", "buy", result)
        self.assertEqual(asset, "BTC")
        self.assertEqual(amount, 0.5)

    def test_calc_output_amount_sell(self):
        result = TradeResult(success=True, filled_size=0.5, avg_price=20000)
        asset, amount = TradeExecutor._calc_output_amount("BTC-USDT", "sell", result)
        self.assertEqual(asset, "USDT")
        self.assertEqual(amount, 10000)

    def test_calc_output_amount_invalid(self):
        result = TradeResult(success=True, filled_size=0.0, avg_price=20000)
        with self.assertRaises(ValueError):
            TradeExecutor._calc_output_amount("BTC-USDT", "buy", result)

        result = TradeResult(success=True, filled_size=0.5, avg_price=0.0)
        with self.assertRaises(ValueError):
            TradeExecutor._calc_output_amount("BTC-USDT", "sell", result)

    def test_calc_order_size(self):
        size = TradeExecutor._calc_order_size("BTC-USDT", "buy", 20000, 1000)
        self.assertAlmostEqual(size, 0.05)
        size = TradeExecutor._calc_order_size("BTC-USDT", "sell", 20000, 0.5)
        self.assertEqual(size, 0.5)


if __name__ == "__main__":
    unittest.main()
