"""
交易精度截断函数的单元测试
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from core.trade_executor import truncate_size, truncate_price, TradeExecutor
from models.trade import TradeResult


class TestTruncateSize(unittest.TestCase):
    """测试 truncate_size 向下截断"""

    def test_basic_truncation(self):
        result = truncate_size(0.0012345678, Decimal('0.0001'))
        self.assertEqual(result, Decimal('0.0012'))

    def test_truncation_coarser_step(self):
        result = truncate_size(0.00999, Decimal('0.001'))
        self.assertEqual(result, Decimal('0.009'))

    def test_exact_multiple(self):
        result = truncate_size(0.003, Decimal('0.001'))
        self.assertEqual(result, Decimal('0.003'))

    def test_zero_value(self):
        result = truncate_size(0.0, Decimal('0.001'))
        self.assertEqual(result, Decimal('0'))

    def test_large_value(self):
        result = truncate_size(12345.6789, Decimal('0.01'))
        self.assertEqual(result, Decimal('12345.67'))


class TestTruncatePrice(unittest.TestCase):
    """测试 truncate_price 价格截断"""

    def test_buy_rounds_up(self):
        result = truncate_price(89123.45, Decimal('0.1'), 'buy')
        self.assertEqual(result, Decimal('89123.5'))

    def test_sell_rounds_down(self):
        result = truncate_price(89123.45, Decimal('0.1'), 'sell')
        self.assertEqual(result, Decimal('89123.4'))

    def test_buy_exact_multiple(self):
        result = truncate_price(89123.4, Decimal('0.1'), 'buy')
        self.assertEqual(result, Decimal('89123.4'))

    def test_sell_exact_multiple(self):
        result = truncate_price(89123.4, Decimal('0.1'), 'sell')
        self.assertEqual(result, Decimal('89123.4'))

    def test_buy_integer_tick(self):
        result = truncate_price(100.3, Decimal('1'), 'buy')
        self.assertEqual(result, Decimal('101'))

    def test_sell_integer_tick(self):
        result = truncate_price(100.9, Decimal('1'), 'sell')
        self.assertEqual(result, Decimal('100'))


class TestMinSizeCheck(unittest.TestCase):
    """测试下单数量低于 minSz 时返回失败"""

    @patch('core.trade_executor.OKXClient')
    def test_size_below_min_returns_failure(self, MockOKXClient):
        mock_client = MockOKXClient.return_value
        mock_client.get_instrument_rule.return_value = {
            'lotSz': Decimal('0.001'),
            'minSz': Decimal('0.01'),
            'tickSz': Decimal('0.01'),
        }
        mock_client.get_ticker.return_value = {
            'best_bid': 100.0,
            'best_ask': 100.0,
        }

        executor = TradeExecutor.__new__(TradeExecutor)
        executor.okx_client = mock_client
        executor.logger = MagicMock()
        executor.slippage_tolerance = 0.0
        executor.max_retries = 1
        executor.order_timeout = 5.0

        result = executor._execute_single_trade('BTC-USDT', 'buy', 0.001, 100.0)
        self.assertFalse(result.success)
        self.assertIn('小于最小要求', result.error_message)


if __name__ == '__main__':
    unittest.main()
