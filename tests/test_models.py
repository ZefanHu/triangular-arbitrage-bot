#!/usr/bin/env python3
"""
models目录统一测试文件

使用真实的OKX API测试所有model类的功能

使用方法：
- python3 tests/test_models.py          # 运行基础测试
- python3 tests/test_models.py --full   # 运行完整测试
- python3 tests/test_models.py --coverage # 生成覆盖率报告
"""

import sys
import os
import argparse
import unittest
import time
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

# 添加项目根目录到path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config_manager import ConfigManager
from core.okx_client import OKXClient
from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity
from models.order_book import OrderBook
from models.portfolio import Portfolio
from models.trade import Trade, TradeStatus
from utils.logger import setup_logger


class TestArbitragePath(unittest.TestCase):
    """测试ArbitragePath类"""
    
    def test_valid_triangular_path(self):
        """测试有效的三角套利路径"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        self.assertTrue(path.is_triangular())
        self.assertEqual(path.get_step_count(), 3)
        self.assertEqual(path.get_start_asset(), "USDT")
        self.assertEqual(len(path.get_trading_pairs()), 3)
        self.assertEqual(len(path.get_trade_directions()), 3)
        
    def test_invalid_path_too_short(self):
        """测试路径过短的情况"""
        with self.assertRaisesRegex(ValueError, "套利路径至少需要3个资产"):
            ArbitragePath(path=["USDT", "BTC"])
    
    def test_invalid_path_not_closed(self):
        """测试路径未闭合的情况"""
        with self.assertRaisesRegex(ValueError, "套利路径必须形成闭环"):
            ArbitragePath(path=["USDT", "BTC", "ETH", "USDC"])
    
    def test_trading_pairs_generation(self):
        """测试交易对生成"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        pairs = path.get_trading_pairs()
        
        self.assertEqual(len(pairs), 3)
        # 验证交易对格式正确
        for pair in pairs:
            self.assertIn('-', pair)
            self.assertEqual(len(pair.split('-')), 2)
    
    def test_trade_directions(self):
        """测试交易方向"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        directions = path.get_trade_directions()
        
        self.assertEqual(len(directions), 3)
        for direction in directions:
            self.assertIn(direction, ['buy', 'sell'])
    
    def test_four_step_path(self):
        """测试四步套利路径"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDC", "USDT"])
        
        self.assertFalse(path.is_triangular())
        self.assertEqual(path.get_step_count(), 4)
        self.assertEqual(len(path.get_trading_pairs()), 4)
        self.assertEqual(len(path.get_trade_directions()), 4)
    
    def test_base_asset_priority(self):
        """测试基础资产优先级判断"""
        path = ArbitragePath(path=["USDT", "BTC", "USDT"])
        
        # 测试BTC vs USDT（BTC优先级更高）
        self.assertTrue(path._is_base_asset("BTC", "USDT"))
        self.assertFalse(path._is_base_asset("USDT", "BTC"))
        
        # 测试ETH vs USDC（ETH优先级更高）
        self.assertTrue(path._is_base_asset("ETH", "USDC"))
        self.assertFalse(path._is_base_asset("USDC", "ETH"))
        
        # 测试未知币种vs稳定币
        self.assertTrue(path._is_base_asset("DOGE", "USDT"))
        self.assertFalse(path._is_base_asset("USDT", "DOGE"))
    
    def test_complex_trading_directions(self):
        """测试复杂交易方向计算"""
        # 测试需要反向交易的情况
        path = ArbitragePath(path=["USDT", "ETH", "BTC", "USDT"])
        directions = path.get_trade_directions()
        pairs = path.get_trading_pairs()
        
        # 验证所有必要的信息都已生成
        self.assertEqual(len(directions), 3)
        self.assertEqual(len(pairs), 3)
        
        # 验证每个交易对都有对应的方向
        for i, (pair, direction) in enumerate(zip(pairs, directions)):
            self.assertIn(direction, ['buy', 'sell'])
            self.assertIn('-', pair)
    
    def test_path_string_representation(self):
        """测试路径字符串表示"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        path_str = str(path)
        
        self.assertIsInstance(path_str, str)
        self.assertIn("USDT", path_str)
        self.assertIn("BTC", path_str)
        self.assertIn("ETH", path_str)


class TestArbitrageOpportunity(unittest.TestCase):
    """测试ArbitrageOpportunity类"""
    
    def test_valid_opportunity(self):
        """测试有效的套利机会"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.02,
            min_profit_amount=100.0,
            max_profit_amount=500.0,
            optimal_amount=1000.0,
            expected_profit=20.0,
            timestamp=time.time()
        )
        
        self.assertTrue(opportunity.is_valid())
        self.assertTrue(opportunity.is_profitable(min_rate=0.01))
        self.assertFalse(opportunity.is_profitable(min_rate=0.03))
    
    def test_invalid_opportunity_negative_profit(self):
        """测试负利润的无效机会"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=-0.01,
            min_profit_amount=-10.0,
            max_profit_amount=-5.0,
            optimal_amount=1000.0,
            expected_profit=-10.0,
            timestamp=time.time()
        )
        
        self.assertFalse(opportunity.is_valid())
        self.assertFalse(opportunity.is_profitable())
    
    def test_opportunity_age(self):
        """测试机会时效性"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        old_timestamp = time.time() - 10  # 10秒前
        
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.02,
            min_profit_amount=100.0,
            max_profit_amount=500.0,
            optimal_amount=1000.0,
            expected_profit=20.0,
            timestamp=old_timestamp
        )
        
        age = opportunity.get_age_seconds()
        self.assertGreaterEqual(age, 10)
        self.assertLess(age, 15)  # 考虑执行时间
    
    def test_opportunity_comparison(self):
        """测试机会比较"""
        path1 = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        path2 = ArbitragePath(path=["USDT", "ETH", "USDC", "USDT"])
        
        opp1 = ArbitrageOpportunity(
            path=path1,
            profit_rate=0.02,
            min_profit_amount=100.0,
            max_profit_amount=500.0,
            optimal_amount=1000.0,
            expected_profit=20.0,
            timestamp=time.time()
        )
        
        opp2 = ArbitrageOpportunity(
            path=path2,
            profit_rate=0.03,
            min_profit_amount=150.0,
            max_profit_amount=600.0,
            optimal_amount=1000.0,
            expected_profit=30.0,
            timestamp=time.time()
        )
        
        # 比较利润率
        self.assertLess(opp1.profit_rate, opp2.profit_rate)
        self.assertGreater(opp2.expected_profit, opp1.expected_profit)
    
    def test_edge_cases(self):
        """测试边界情况"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        # 测试零利润
        zero_profit = ArbitrageOpportunity(
            path=path,
            profit_rate=0.0,
            min_profit_amount=0.0,
            max_profit_amount=0.0,
            optimal_amount=1000.0,
            expected_profit=0.0,
            timestamp=time.time()
        )
        self.assertFalse(zero_profit.is_profitable())
        
        # 测试极小利润率
        tiny_profit = ArbitrageOpportunity(
            path=path,
            profit_rate=0.0001,  # 0.01%
            min_profit_amount=0.1,
            max_profit_amount=1.0,
            optimal_amount=1000.0,
            expected_profit=0.1,
            timestamp=time.time()
        )
        self.assertTrue(tiny_profit.is_profitable(min_rate=0.00005))
        self.assertFalse(tiny_profit.is_profitable(min_rate=0.001))


class TestOrderBook(unittest.TestCase):
    """测试OrderBook类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建logger（但不创建OKXClient，避免API调用）
        self.logger = logging.getLogger(__name__)
    
    def test_valid_orderbook(self):
        """测试有效的订单簿"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            asks=[[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]],
            timestamp=time.time()
        )
        
        self.assertTrue(orderbook.is_valid())
        self.assertEqual(orderbook.get_best_bid(), 50000.0)
        self.assertEqual(orderbook.get_best_ask(), 50100.0)
        self.assertEqual(orderbook.get_spread(), 100.0)
        self.assertEqual(orderbook.get_spread_percentage(), 0.2)
    
    def test_empty_orderbook(self):
        """测试空订单簿"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[],
            asks=[],
            timestamp=time.time()
        )
        
        self.assertFalse(orderbook.is_valid())
        self.assertIsNone(orderbook.get_best_bid())
        self.assertIsNone(orderbook.get_best_ask())
        self.assertIsNone(orderbook.get_spread())
        self.assertIsNone(orderbook.get_spread_percentage())
    
    def test_orderbook_depth(self):
        """测试订单簿深度"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            asks=[[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]],
            timestamp=time.time()
        )
        
        depth = orderbook.get_depth(levels=2)
        self.assertEqual(len(depth['bids']), 2)
        self.assertEqual(len(depth['asks']), 2)
        self.assertEqual(depth['bids'][0][0], 50000.0)
        self.assertEqual(depth['asks'][0][0], 50100.0)
    
    def test_orderbook_age(self):
        """测试订单簿时效性"""
        old_timestamp = time.time() - 5
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=old_timestamp
        )
        
        age = orderbook.get_age_seconds()
        self.assertGreaterEqual(age, 5)
        self.assertLess(age, 10)
    
    def test_invalid_orderbook_crossed(self):
        """测试交叉的无效订单簿"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50200.0, 1.0]],  # 买价高于卖价
            asks=[[50100.0, 1.0]],
            timestamp=time.time()
        )
        
        self.assertFalse(orderbook.is_valid())
    
    def test_invalid_timestamp(self):
        """测试无效时间戳"""
        # 测试timestamp为0
        orderbook_zero = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=0
        )
        self.assertFalse(orderbook_zero.is_valid())
        
        # 测试负数timestamp
        orderbook_negative = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=-1
        )
        self.assertFalse(orderbook_negative.is_valid())
    
    def test_large_depth_request(self):
        """测试请求超出可用档位的深度"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0], [49900.0, 2.0]],  # 只有2档买单
            asks=[[50100.0, 1.0]],  # 只有1档卖单
            timestamp=time.time()
        )
        
        # 请求10档深度，但只有2档买单和1档卖单
        depth = orderbook.get_depth(levels=10)
        self.assertEqual(len(depth['bids']), 2)  # 只返回实际存在的2档
        self.assertEqual(len(depth['asks']), 1)   # 只返回实际存在的1档


class TestPortfolio(unittest.TestCase):
    """测试Portfolio类"""
    
    def test_valid_portfolio(self):
        """测试有效的投资组合"""
        portfolio = Portfolio(
            balances={
                "USDT": 10000.0,
                "BTC": 0.5,
                "ETH": 5.0,
                "USDC": 0.0
            },
            timestamp=time.time()
        )
        
        self.assertEqual(portfolio.get_asset_balance("USDT"), 10000.0)
        self.assertEqual(portfolio.get_asset_balance("BTC"), 0.5)
        self.assertEqual(portfolio.get_asset_balance("UNKNOWN"), 0.0)
        self.assertTrue(portfolio.has_sufficient_balance("USDT", 5000.0))
        self.assertFalse(portfolio.has_sufficient_balance("USDT", 15000.0))
    
    def test_empty_portfolio(self):
        """测试空投资组合"""
        portfolio = Portfolio(
            balances={},
            timestamp=time.time()
        )
        
        self.assertEqual(portfolio.get_asset_balance("USDT"), 0.0)
        self.assertFalse(portfolio.has_sufficient_balance("USDT", 1.0))
        self.assertEqual(len(portfolio.get_non_zero_assets()), 0)
    
    def test_portfolio_updates(self):
        """测试投资组合更新"""
        portfolio = Portfolio(
            balances={"USDT": 10000.0, "BTC": 0.5},
            timestamp=time.time()
        )
        
        # 更新余额
        portfolio.update_balance("USDT", 8000.0)
        portfolio.update_balance("ETH", 2.0)
        
        self.assertEqual(portfolio.get_asset_balance("USDT"), 8000.0)
        self.assertEqual(portfolio.get_asset_balance("ETH"), 2.0)
        
        # 获取非零资产
        non_zero = portfolio.get_non_zero_assets()
        self.assertIn("USDT", non_zero)
        self.assertIn("BTC", non_zero)
        self.assertIn("ETH", non_zero)
    
    def test_portfolio_value_calculation(self):
        """测试投资组合价值计算"""
        portfolio = Portfolio(
            balances={
                "USDT": 10000.0,
                "BTC": 0.5,
                "ETH": 5.0
            },
            timestamp=time.time()
        )
        
        # 模拟价格
        prices = {
            "BTC": 50000.0,
            "ETH": 3000.0
        }
        
        # 计算总价值
        total_value = portfolio.get_total_value_in_usdt(prices)
        expected_value = 10000.0 + (0.5 * 50000.0) + (5.0 * 3000.0)
        self.assertEqual(total_value, expected_value)
    
    def test_balance_precision(self):
        """测试余额精度处理"""
        portfolio = Portfolio(
            balances={
                "USDT": 10000.123456789,
                "BTC": 0.00000001,  # 1 satoshi
                "ETH": 0.000000000000000001  # 1 wei
            },
            timestamp=time.time()
        )
        
        # 验证小数精度保持
        self.assertGreater(portfolio.get_asset_balance("BTC"), 0)
        self.assertGreater(portfolio.get_asset_balance("ETH"), 0)
        
        # 验证充足余额检查对极小值的处理
        self.assertTrue(portfolio.has_sufficient_balance("BTC", 0.00000001))
        self.assertFalse(portfolio.has_sufficient_balance("BTC", 0.00000002))


class TestTrade(unittest.TestCase):
    """测试Trade类"""
    
    def setUp(self):
        """测试前准备"""
        # 尝试创建OKX客户端（用于真实数据测试）
        try:
            self.okx_client = OKXClient()
            self.has_okx_client = True
        except Exception:
            self.okx_client = None
            self.has_okx_client = False
            
        self.logger = logging.getLogger(__name__)
    
    def test_buy_trade(self):
        """测试买入交易"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.01,
            price=50000.0
        )
        
        self.assertTrue(trade.is_buy())
        self.assertFalse(trade.is_sell())
        self.assertEqual(trade.get_value(), 500.0)
        
        # 验证订单参数
        params = trade.to_order_params()
        self.assertEqual(params['instId'], "BTC-USDT")
        self.assertEqual(params['side'], "buy")
        self.assertEqual(params['sz'], "0.01")
        self.assertEqual(params['px'], "50000.0")
        self.assertEqual(params['ordType'], "limit")
    
    def test_sell_trade(self):
        """测试卖出交易"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="sell",
            size=0.01,
            price=51000.0
        )
        
        self.assertFalse(trade.is_buy())
        self.assertTrue(trade.is_sell())
        self.assertEqual(trade.get_value(), 510.0)
    
    def test_trade_status_updates(self):
        """测试交易状态更新"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.01,
            price=50000.0
        )
        
        # 初始状态
        self.assertEqual(trade.status, TradeStatus.PENDING)
        
        # 更新状态
        trade.update_status(TradeStatus.SUBMITTED)
        self.assertEqual(trade.status, TradeStatus.SUBMITTED)
        
        trade.update_status(TradeStatus.FILLED, filled_size=0.01, avg_price=49999.0)
        self.assertEqual(trade.status, TradeStatus.FILLED)
        self.assertEqual(trade.filled_size, 0.01)
        self.assertEqual(trade.avg_price, 49999.0)
    
    def test_partial_fill(self):
        """测试部分成交"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.1,
            price=50000.0
        )
        
        # 部分成交
        trade.update_status(TradeStatus.PARTIALLY_FILLED, filled_size=0.03, avg_price=49998.0)
        
        self.assertEqual(trade.status, TradeStatus.PARTIALLY_FILLED)
        self.assertEqual(trade.filled_size, 0.03)
        self.assertEqual(trade.get_fill_rate(), 0.3)  # 30%成交
    
    def test_trade_with_real_data(self):
        """使用真实数据测试交易（完整测试模式）"""
        if not RUN_FULL_TEST:
            self.skipTest("跳过真实数据测试（非完整测试模式）")
            
        if not self.has_okx_client:
            self.skipTest("OKX客户端未初始化")
        
        # 获取真实的交易对信息
        symbol = "BTC-USDT"
        orderbook = self.okx_client.get_orderbook(symbol)
        
        if orderbook and orderbook.is_valid():
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            
            if best_bid and best_ask:
                # 创建买卖交易（价格设置为不会成交）
                buy_trade = Trade(
                    inst_id=symbol,
                    side="buy",
                    size=0.001,
                    price=best_bid * 0.99  # 低于最优买价
                )
                
                sell_trade = Trade(
                    inst_id=symbol,
                    side="sell",
                    size=0.001,
                    price=best_ask * 1.01  # 高于最优卖价
                )
                
                # 验证交易参数
                self.assertTrue(buy_trade.is_buy())
                self.assertTrue(sell_trade.is_sell())
                
                # 验证订单参数格式
                buy_params = buy_trade.to_order_params()
                sell_params = sell_trade.to_order_params()
                
                self.assertEqual(buy_params['instId'], symbol)
                self.assertEqual(buy_params['side'], 'buy')
                self.assertEqual(buy_params['ordType'], 'limit')
                
                self.assertEqual(sell_params['instId'], symbol)
                self.assertEqual(sell_params['side'], 'sell')
                self.assertEqual(sell_params['ordType'], 'limit')
                
                self.logger.info(f"真实交易验证通过")
                self.logger.info(f"买单参数: {buy_params}")
                self.logger.info(f"卖单参数: {sell_params}")
            else:
                self.skipTest("订单簿数据不完整")
        else:
            self.skipTest("无法获取真实订单簿数据")


# 全局测试控制变量
RUN_FULL_TEST = False
GENERATE_COVERAGE = False


def run_tests():
    """运行测试主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Models模块测试脚本')
    parser.add_argument('--full', action='store_true', help='运行完整测试（包括真实API测试）')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    args = parser.parse_args()
    
    # 设置全局变量
    global RUN_FULL_TEST, GENERATE_COVERAGE
    RUN_FULL_TEST = args.full
    GENERATE_COVERAGE = args.coverage
    
    # 设置日志
    test_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(tests_dir, f"logs/test_models_{test_start_time}.log")
    
    # 确保日志目录存在
    os.makedirs(os.path.join(tests_dir, "logs"), exist_ok=True)
    
    # 配置日志
    logger = setup_logger("test_models", log_file, logging.INFO)
    logger.info(f"开始运行models测试 - 模式: {'完整测试' if RUN_FULL_TEST else '基础测试'}")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestArbitragePath,
        TestArbitrageOpportunity,
        TestOrderBook,
        TestPortfolio,
        TestTrade
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    
    if GENERATE_COVERAGE:
        # 使用coverage运行测试
        import coverage
        cov = coverage.Coverage(source=['models'])
        cov.start()
        
        result = runner.run(suite)
        
        cov.stop()
        cov.save()
        
        # 生成报告
        print("\n生成覆盖率报告...")
        cov.report()
        
        # 生成HTML报告
        html_report_dir = os.path.join(tests_dir, "reports/models_coverage_html")
        cov.html_report(directory=html_report_dir)
        print(f"HTML覆盖率报告已生成: {html_report_dir}/index.html")
        
        # 生成XML报告
        xml_report_path = os.path.join(tests_dir, "reports/models_coverage.xml")
        cov.xml_report(outfile=xml_report_path)
        print(f"XML覆盖率报告已生成: {xml_report_path}")
    else:
        result = runner.run(suite)
    
    # 记录测试结果
    logger.info(f"测试完成 - 运行: {result.testsRun}, 失败: {len(result.failures)}, 错误: {len(result.errors)}")
    
    # 返回是否成功
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)