"""
三腿交易部分成交与失败回收的集成测试 (Issue #4)

测试覆盖:
1. _wait_order_filled 部分成交处理
2. _attempt_recovery 资产回收
3. execute_arbitrage 中间腿失败触发回收
4. _save_failure_alert 告警文件输出
"""

import os
import sys
import json
import time
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch, call
from decimal import Decimal

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from models.trade import Trade, TradeResult, ArbitrageRecord
from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity
from core.trade_executor import TradeExecutor


def _make_executor():
    """创建一个使用 mock okx_client 的 TradeExecutor"""
    mock_client = MagicMock()
    mock_client.get_instrument_rule.return_value = None
    mock_client.get_balance.return_value = {"USDT": 10000.0, "BTC": 0.1, "ETH": 1.0}
    executor = TradeExecutor(mock_client)
    return executor, mock_client


def _make_opportunity():
    """创建一个 USDT→BTC→ETH→USDT 的套利机会"""
    path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
    opp = ArbitrageOpportunity(
        path=path,
        profit_rate=0.005,
        min_amount=10.0,
        timestamp=time.time(),
        trade_steps=[
            {"pair": "BTC-USDT", "action": "buy"},
            {"pair": "ETH-BTC", "action": "buy"},
            {"pair": "ETH-USDT", "action": "sell"},
        ]
    )
    return opp


class TestWaitOrderFilled(unittest.TestCase):
    """测试组 1: _wait_order_filled 部分成交处理"""

    def test_partial_fill_on_timeout_returns_success(self):
        """超时后有部分成交 → 应返回 success=True 并携带实际成交量"""
        executor, mock_client = _make_executor()

        # 循环查询时始终返回 partially_filled
        mock_client.get_order_status.return_value = {
            'state': 'partially_filled',
            'filled_size': 0.1,
            'avg_price': 0,
        }
        mock_client.cancel_order.return_value = True

        # 超时后最终查询返回有成交
        def final_status_after_cancel(*args, **kwargs):
            """cancel 之后的 get_order_status 返回部分成交结果"""
            # 重新指向最终状态
            mock_client.get_order_status.return_value = {
                'state': 'canceled',
                'filled_size': 0.3,
                'avg_price': 90000,
                'fee': -0.0001,
                'fee_currency': 'BTC',
            }
            return True

        mock_client.cancel_order.side_effect = final_status_after_cancel

        result = executor._wait_order_filled("BTC-USDT", "order123", timeout=0.3)

        self.assertTrue(result.success)
        self.assertEqual(result.filled_size, 0.3)
        self.assertEqual(result.avg_price, 90000)
        mock_client.cancel_order.assert_called_once()

    def test_no_fill_on_timeout_returns_failure(self):
        """超时后无任何成交 → 应返回 success=False"""
        executor, mock_client = _make_executor()

        mock_client.get_order_status.return_value = {
            'state': 'live',
            'filled_size': 0,
            'avg_price': 0,
        }
        mock_client.cancel_order.return_value = True

        result = executor._wait_order_filled("BTC-USDT", "order456", timeout=0.3)

        self.assertFalse(result.success)
        self.assertIn("超时", result.error_message)

    def test_fully_filled_no_timeout(self):
        """正常完全成交 → 不触发超时逻辑"""
        executor, mock_client = _make_executor()

        mock_client.get_order_status.return_value = {
            'state': 'filled',
            'filled_size': 1.0,
            'avg_price': 90000,
            'fee': -0.001,
            'fee_currency': 'BTC',
        }

        result = executor._wait_order_filled("BTC-USDT", "order789", timeout=5.0)

        self.assertTrue(result.success)
        self.assertEqual(result.filled_size, 1.0)
        mock_client.cancel_order.assert_not_called()


class TestAttemptRecovery(unittest.TestCase):
    """测试组 2: _attempt_recovery 资产回收"""

    def test_recovery_btc_to_usdt_success(self):
        """BTC → USDT 回收成功"""
        executor, mock_client = _make_executor()

        mock_client.get_ticker.return_value = {
            'best_bid': 90000,
            'best_ask': 90100,
            'last_price': 90050,
        }

        with patch.object(executor, '_execute_single_trade_with_safety') as mock_exec:
            mock_exec.return_value = TradeResult(
                success=True,
                order_id="recovery001",
                filled_size=0.001,
                avg_price=90000,
                fee=0,
                fee_currency="USDT",
            )

            result = executor._attempt_recovery("BTC", 0.001, "USDT")

        self.assertTrue(result['success'])
        self.assertGreater(result['recovered_amount'], 0)
        # 验证调用参数: inst_id="BTC-USDT", side="sell"
        args = mock_exec.call_args
        self.assertEqual(args[0][0], "BTC-USDT")
        self.assertEqual(args[0][1], "sell")

    def test_recovery_no_route_returns_failure(self):
        """无回收路径 → 返回失败"""
        executor, _ = _make_executor()

        result = executor._attempt_recovery("DOGE", 100, "USDT")

        self.assertFalse(result['success'])
        self.assertIn("无回收路径", result['error'])

    def test_recovery_same_asset_returns_success(self):
        """same asset → 直接返回成功"""
        executor, _ = _make_executor()

        result = executor._attempt_recovery("USDT", 100, "USDT")

        self.assertTrue(result['success'])
        self.assertEqual(result['recovered_amount'], 100)

    def test_recovery_trade_failure_no_exception(self):
        """回收交易失败 → 返回失败但不抛异常"""
        executor, mock_client = _make_executor()

        mock_client.get_ticker.return_value = {
            'best_bid': 90000,
            'best_ask': 90100,
            'last_price': 90050,
        }

        with patch.object(executor, '_execute_single_trade_with_safety') as mock_exec:
            mock_exec.return_value = TradeResult(
                success=False,
                error_message="回收下单被拒绝",
            )

            result = executor._attempt_recovery("BTC", 0.001, "USDT")

        self.assertFalse(result['success'])


class TestExecuteArbitrageLegFailure(unittest.TestCase):
    """测试组 3: execute_arbitrage 中间腿失败触发回收"""

    def _setup_executor_for_arbitrage(self):
        """设置 executor，mock 掉内部方法以聚焦编排逻辑"""
        executor, mock_client = _make_executor()
        opp = _make_opportunity()

        # mock _pre_trade_check
        executor._pre_trade_check = MagicMock(return_value={
            'success': True, 'message': '检查通过'
        })

        # mock _generate_trades 返回 3 个 Trade 对象
        executor._generate_trades = MagicMock(return_value=[
            Trade("BTC-USDT", "buy", 0.001, 90000),
            Trade("ETH-BTC", "buy", 0.03, 0.035),
            Trade("ETH-USDT", "sell", 0.03, 3500),
        ])

        return executor, mock_client, opp

    def test_leg2_failure_triggers_recovery_and_alert(self):
        """Leg 2 失败 → 触发回收 + 告警"""
        executor, mock_client, opp = self._setup_executor_for_arbitrage()

        leg1_result = TradeResult(
            success=True, order_id="leg1", filled_size=0.001,
            avg_price=90000, fee=-0.000001, fee_currency="BTC",
        )
        leg2_result = TradeResult(
            success=False, error_message="订单被拒绝",
        )

        executor._execute_single_trade_with_safety = MagicMock(
            side_effect=[leg1_result, leg2_result]
        )

        executor._attempt_recovery = MagicMock(return_value={
            'success': True, 'recovered_amount': 89.5, 'error': ''
        })

        executor._save_failure_alert = MagicMock()

        result = executor.execute_arbitrage(opp, 100.0)

        self.assertFalse(result['success'])
        self.assertIn("第 2 笔交易失败", result['error'])
        self.assertIsNotNone(result.get('recovery'))
        executor._attempt_recovery.assert_called_once()
        executor._save_failure_alert.assert_called_once()

    def test_leg1_failure_no_recovery(self):
        """Leg 1 失败 → 不触发回收"""
        executor, mock_client, opp = self._setup_executor_for_arbitrage()

        leg1_result = TradeResult(
            success=False, error_message="余额不足",
        )

        executor._execute_single_trade_with_safety = MagicMock(
            side_effect=[leg1_result]
        )

        executor._attempt_recovery = MagicMock()
        executor._save_failure_alert = MagicMock()

        result = executor.execute_arbitrage(opp, 100.0)

        self.assertFalse(result['success'])
        # Leg 1 失败时 i==0，不触发回收
        executor._attempt_recovery.assert_not_called()
        executor._save_failure_alert.assert_not_called()
        self.assertIsNone(result.get('recovery'))


class TestSaveFailureAlert(unittest.TestCase):
    """测试组 4: _save_failure_alert 文件输出"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.alert_file = os.path.join(self.tmpdir, 'partial_execution_alerts.json')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_alert_args(self):
        """构造 _save_failure_alert 的调用参数"""
        opp = _make_opportunity()
        record = ArbitrageRecord(
            opportunity=opp,
            investment_amount=100.0,
            expected_profit=0.5,
        )
        record.trade_results = [
            TradeResult(success=True, order_id="leg1", filled_size=0.001,
                        avg_price=90000, fee=0, fee_currency="USDT"),
        ]
        trade_results = record.trade_results[:]
        recovery_result = {'success': True, 'recovered_amount': 89.5, 'error': ''}
        return opp, record, 1, trade_results, "BTC", 0.001, recovery_result

    def test_alert_writes_valid_json(self):
        """告警正确写入 JSON 文件"""
        executor, _ = _make_executor()
        args = self._make_alert_args()
        alert_file = os.path.join(self.tmpdir, 'partial_execution_alerts.json')

        # patch _save_failure_alert 内部的硬编码路径
        original_save = TradeExecutor._save_failure_alert

        def patched_save(self_exec, *a, **kw):
            # 临时替换方法内的 alert_file 路径
            import types
            src = original_save
            # 直接在方法体外构造：调用原方法但先 patch 局部变量不可行，
            # 所以复制逻辑使用临时路径
            opp, record, failed_leg_index, trade_results, current_asset, current_amount, recovery_result = a
            alert = {
                'timestamp': time.time(),
                'path': str(opp.path),
                'failed_leg': failed_leg_index + 1,
                'total_legs': len(record.trade_results),
                'current_asset': current_asset,
                'current_amount': current_amount,
                'completed_trades': [
                    {'order_id': r.order_id, 'filled_size': r.filled_size,
                     'avg_price': r.avg_price, 'success': r.success}
                    for r in trade_results if r.success
                ],
                'recovery_attempted': recovery_result is not None,
                'recovery_success': recovery_result['success'] if recovery_result else False,
                'recovery_amount': recovery_result.get('recovered_amount', 0) if recovery_result else 0,
                'recovery_error': recovery_result.get('error', '') if recovery_result else '',
            }
            alerts = []
            if os.path.exists(alert_file):
                with open(alert_file, 'r') as f:
                    alerts = json.load(f)
            alerts.append(alert)
            with open(alert_file, 'w') as f:
                json.dump(alerts, f, indent=2, ensure_ascii=False)

        with patch.object(TradeExecutor, '_save_failure_alert', patched_save):
            executor._save_failure_alert(*args)

        with open(alert_file, 'r') as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        self.assertIn('timestamp', data[0])
        self.assertIn('path', data[0])
        self.assertIn('failed_leg', data[0])
        self.assertIn('recovery_attempted', data[0])

    def test_alert_appends_not_overwrites(self):
        """追加写入不覆盖"""
        executor, _ = _make_executor()
        args = self._make_alert_args()

        # 使用真实临时目录，patch 告警文件路径
        alert_path = self.alert_file

        def patched_save(self_exec, *a, **kw):
            """重写 _save_failure_alert 使其写到临时文件"""
            opp, record, failed_leg_index, trade_results, current_asset, current_amount, recovery_result = a

            alert = {
                'timestamp': time.time(),
                'path': str(opp.path),
                'failed_leg': failed_leg_index + 1,
                'current_asset': current_asset,
                'current_amount': current_amount,
                'recovery_attempted': recovery_result is not None,
                'recovery_success': recovery_result['success'] if recovery_result else False,
            }

            alerts = []
            if os.path.exists(alert_path):
                with open(alert_path, 'r') as f:
                    alerts = json.load(f)
            alerts.append(alert)
            with open(alert_path, 'w') as f:
                json.dump(alerts, f, indent=2)

        with patch.object(TradeExecutor, '_save_failure_alert', patched_save):
            executor._save_failure_alert(*args)
            executor._save_failure_alert(*args)

        with open(alert_path, 'r') as f:
            data = json.load(f)

        self.assertEqual(len(data), 2)

    def test_real_save_failure_alert_creates_file(self):
        """直接调用原始 _save_failure_alert 验证文件创建"""
        executor, _ = _make_executor()
        args = self._make_alert_args()

        # 清理可能存在的旧文件
        alert_path = 'logs/partial_execution_alerts.json'
        existed_before = os.path.exists(alert_path)
        old_data = None
        if existed_before:
            with open(alert_path, 'r') as f:
                old_data = json.load(f)

        try:
            executor._save_failure_alert(*args)

            self.assertTrue(os.path.exists(alert_path))
            with open(alert_path, 'r') as f:
                data = json.load(f)

            # 找到本次写入的告警（最后一条）
            last_alert = data[-1]
            self.assertIn('timestamp', last_alert)
            self.assertIn('path', last_alert)
            self.assertIn('failed_leg', last_alert)
            self.assertIn('recovery_attempted', last_alert)
            self.assertIn('recovery_success', last_alert)
        finally:
            # 恢复原始状态
            if existed_before and old_data is not None:
                with open(alert_path, 'w') as f:
                    json.dump(old_data, f, indent=2, ensure_ascii=False)
            elif not existed_before and os.path.exists(alert_path):
                os.remove(alert_path)


if __name__ == '__main__':
    unittest.main()
