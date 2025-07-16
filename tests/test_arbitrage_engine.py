"""
测试套利计算引擎

使用OKX模拟盘真实数据测试套利计算准确性
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch
from typing import Dict, List

from core.arbitrage_engine import ArbitrageEngine, ArbitrageOpportunity
from core.data_collector import DataCollector
from config.config_manager import ConfigManager
from models.order_book import OrderBook


class TestArbitrageEngine:
    """套利引擎测试类"""
    
    @pytest.fixture
    def config_manager(self):
        """配置管理器fixture"""
        config_manager = ConfigManager()
        # 使用测试配置
        config_manager.config_file = "/home/huzefan/triangular-arbitrage-bot/tests/test_settings.ini"
        return config_manager
    
    @pytest.fixture
    def mock_data_collector(self):
        """模拟数据采集器fixture"""
        mock_collector = Mock(spec=DataCollector)
        return mock_collector
    
    @pytest.fixture
    def arbitrage_engine(self, mock_data_collector):
        """套利引擎fixture"""
        engine = ArbitrageEngine(mock_data_collector)
        return engine
    
    @pytest.fixture
    def real_data_collector(self):
        """真实数据采集器fixture（用于集成测试）"""
        collector = DataCollector()
        return collector
    
    @pytest.fixture
    def real_arbitrage_engine(self, real_data_collector):
        """使用真实数据的套利引擎fixture"""
        engine = ArbitrageEngine(real_data_collector)
        return engine
    
    def create_mock_orderbook(self, symbol: str, bids: List[List[float]], asks: List[List[float]]) -> OrderBook:
        """创建模拟订单簿"""
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=time.time()
        )
    
    def test_trading_pair_generation(self, arbitrage_engine):
        """测试交易对生成逻辑"""
        # 测试BTC-USDT交易对
        pair, direction = arbitrage_engine._get_trading_pair("BTC", "USDT")
        assert pair == "BTC-USDT"
        assert direction == "sell"  # 卖出BTC获得USDT
        
        # 测试USDT-BTC交易对
        pair, direction = arbitrage_engine._get_trading_pair("USDT", "BTC")
        assert pair == "BTC-USDT"
        assert direction == "buy"  # 买入BTC用USDT
        
        # 测试ETH-USDT交易对
        pair, direction = arbitrage_engine._get_trading_pair("ETH", "USDT")
        assert pair == "ETH-USDT"
        assert direction == "sell"
        
        # 测试USDT-ETH交易对
        pair, direction = arbitrage_engine._get_trading_pair("USDT", "ETH")
        assert pair == "ETH-USDT"
        assert direction == "buy"
        
        # 测试USDT-USDC交易对（特殊处理）
        pair, direction = arbitrage_engine._get_trading_pair("USDT", "USDC")
        assert pair == "USDT-USDC"
        assert direction == "sell"  # 卖出USDT换USDC
        
        # 测试USDC-USDT交易对（特殊处理）
        pair, direction = arbitrage_engine._get_trading_pair("USDC", "USDT")
        assert pair == "USDT-USDC"
        assert direction == "buy"   # 买入USDT用USDC
    
    def test_path_profit_calculation_simple(self, arbitrage_engine):
        """测试简单路径利润计算"""
        # 创建模拟订单簿数据
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 1.0], [49900.0, 2.0]],
                "asks": [[50100.0, 1.0], [50200.0, 2.0]]
            },
            "ETH-USDT": {
                "bids": [[3000.0, 10.0], [2950.0, 20.0]],
                "asks": [[3050.0, 10.0], [3100.0, 20.0]]
            },
            "ETH-BTC": {
                "bids": [[0.058, 10.0], [0.057, 20.0]],
                "asks": [[0.062, 10.0], [0.063, 20.0]]
            }
        }
        
        # 设置模拟数据采集器返回值
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 测试路径: USDT -> BTC -> ETH -> USDT
        path = ["USDT", "BTC", "ETH", "USDT"]
        final_amount, profit_rate = arbitrage_engine.calculate_path_profit(path, 1000.0)
        
        # 验证计算结果
        assert isinstance(final_amount, float)
        assert isinstance(profit_rate, float)
        assert final_amount > 0
        
        # 计算预期结果（手动验证）
        # 1. USDT -> BTC: 1000 / 50100 = 0.01996 BTC (扣除手续费)
        # 2. BTC -> ETH: 0.01996 * 0.058 = 0.00116 ETH (扣除手续费)
        # 3. ETH -> USDT: 0.00116 * 3000 = 3.48 USDT (扣除手续费)
        # 预期利润率应该是负数（因为价差和手续费）
        
        logging.info(f"路径利润计算结果: 最终金额={final_amount:.6f}, 利润率={profit_rate:.6f}")
    
    def test_path_profit_calculation_with_fees(self, arbitrage_engine):
        """测试包含手续费的路径利润计算"""
        # 设置手续费率
        arbitrage_engine.fee_rate = 0.001  # 0.1%
        
        # 创建会导致亏损的模拟订单簿（价格设置不利于套利）
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 1.0]],
                "asks": [[50100.0, 1.0]]  # 高价买入
            },
            "ETH-USDT": {
                "bids": [[3000.0, 10.0]],  # 低价卖出
                "asks": [[3100.0, 10.0]]
            },
            "ETH-BTC": {
                "bids": [[0.060, 10.0]],  # 低价卖出
                "asks": [[0.061, 10.0]]
            }
        }
        
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 测试路径
        path = ["USDT", "BTC", "ETH", "USDT"]
        final_amount, profit_rate = arbitrage_engine.calculate_path_profit(path, 1000.0)
        
        # 验证手续费被正确计算
        assert final_amount < 1000.0  # 由于手续费和不利价格，最终金额应该小于初始金额
        
        logging.info(f"包含手续费的计算结果: 最终金额={final_amount:.6f}, 利润率={profit_rate:.6f}")
    
    def test_arbitrage_opportunity_detection(self, arbitrage_engine):
        """测试套利机会检测"""
        # 创建有套利机会的模拟数据
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 1.0]],
                "asks": [[48000.0, 1.0]]  # 异常低价
            },
            "ETH-USDT": {
                "bids": [[3200.0, 10.0]],  # 异常高价
                "asks": [[3000.0, 10.0]]
            },
            "ETH-BTC": {
                "bids": [[0.070, 10.0]],  # 异常高价
                "asks": [[0.060, 10.0]]
            }
        }
        
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 设置较低的利润阈值以便检测到机会
        arbitrage_engine.min_profit_threshold = 0.001  # 0.1%
        
        # 测试套利机会检测
        opportunities = arbitrage_engine.find_opportunities()
        
        # 验证结果
        assert isinstance(opportunities, list)
        logging.info(f"检测到套利机会数量: {len(opportunities)}")
        
        for opp in opportunities:
            assert 'path_name' in opp
            assert 'path' in opp
            assert 'profit_rate' in opp
            assert 'min_trade_amount' in opp
            assert 'max_trade_amount' in opp
            assert 'estimated_profit' in opp
            assert 'timestamp' in opp
            
            logging.info(f"套利机会: {opp['path_name']}, 利润率: {opp['profit_rate']:.4%}")
    
    def test_max_trade_amount_calculation(self, arbitrage_engine):
        """测试最大交易金额计算"""
        # 创建有限深度的订单簿
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 0.5], [49900.0, 0.3]],  # 有限深度
                "asks": [[50100.0, 0.5], [50200.0, 0.3]]
            },
            "ETH-USDT": {
                "bids": [[3000.0, 5.0], [2950.0, 3.0]],
                "asks": [[3050.0, 5.0], [3100.0, 3.0]]
            },
            "ETH-BTC": {
                "bids": [[0.058, 5.0], [0.057, 3.0]],
                "asks": [[0.062, 5.0], [0.063, 3.0]]
            }
        }
        
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 创建交易步骤
        trade_steps = []
        path = ["USDT", "BTC", "ETH", "USDT"]
        
        for i in range(len(path) - 1):
            from_asset = path[i]
            to_asset = path[i + 1]
            pair, direction = arbitrage_engine._get_trading_pair(from_asset, to_asset)
            order_book = mock_orderbooks.get(pair)
            
            trade_steps.append({
                'from': from_asset,
                'to': to_asset,
                'pair': pair,
                'direction': direction,
                'order_book': order_book
            })
        
        # 测试最大交易金额计算
        max_amount = arbitrage_engine._calculate_max_trade_amount(trade_steps)
        
        # 验证结果
        assert isinstance(max_amount, float)
        assert max_amount > 0
        assert max_amount <= 10000.0  # 应该受到限制
        
        logging.info(f"最大交易金额: {max_amount:.6f}")
    
    def test_invalid_path_handling(self, arbitrage_engine):
        """测试无效路径处理"""
        # 测试无效路径（不是闭环）
        invalid_path = ["USDT", "BTC", "ETH"]
        result = arbitrage_engine.calculate_arbitrage(invalid_path)
        assert result is None
        
        # 测试太短的路径
        short_path = ["USDT", "BTC"]
        result = arbitrage_engine.calculate_arbitrage(short_path)
        assert result is None
        
        # 测试空路径
        empty_path = []
        result = arbitrage_engine.calculate_arbitrage(empty_path)
        assert result is None
    
    def test_missing_orderbook_handling(self, arbitrage_engine):
        """测试缺失订单簿处理"""
        # 设置数据采集器返回None（订单簿不存在）
        arbitrage_engine.data_collector.get_orderbook = Mock(return_value=None)
        
        # 测试正常路径
        path = ["USDT", "BTC", "ETH", "USDT"]
        result = arbitrage_engine.calculate_arbitrage(path)
        
        # 应该返回None（由于订单簿不存在）
        assert result is None
    
    @pytest.mark.integration
    def test_real_market_data_integration(self, real_arbitrage_engine):
        """集成测试：使用真实市场数据"""
        # 启动数据采集器
        import asyncio
        
        async def run_integration_test():
            # 启动数据采集器
            trading_pairs = ["BTC-USDT", "ETH-USDT", "ETH-BTC"]
            success = await real_arbitrage_engine.data_collector.start(trading_pairs)
            
            if not success:
                pytest.skip("无法连接到OKX API")
            
            # 等待数据稳定
            await asyncio.sleep(5)
            
            try:
                # 测试套利机会发现
                opportunities = real_arbitrage_engine.find_opportunities()
                
                # 验证结果
                assert isinstance(opportunities, list)
                logging.info(f"真实市场数据检测到套利机会: {len(opportunities)}")
                
                for opp in opportunities:
                    # 验证数据结构
                    assert 'path_name' in opp
                    assert 'profit_rate' in opp
                    assert isinstance(opp['profit_rate'], float)
                    
                    # 记录真实市场机会
                    logging.info(f"真实套利机会: {opp['path_name']}, 利润率: {opp['profit_rate']:.4%}")
                
                # 测试单个路径计算
                path = ["USDT", "BTC", "ETH", "USDT"]
                final_amount, profit_rate = real_arbitrage_engine.calculate_path_profit(path, 1000.0)
                
                assert isinstance(final_amount, float)
                assert isinstance(profit_rate, float)
                
                logging.info(f"真实市场路径计算: 最终金额={final_amount:.6f}, 利润率={profit_rate:.6f}")
                
            finally:
                # 停止数据采集器
                await real_arbitrage_engine.data_collector.stop()
        
        # 运行异步测试
        asyncio.run(run_integration_test())
    
    def test_statistics_tracking(self, arbitrage_engine):
        """测试统计信息跟踪"""
        # 模拟一些机会检测
        arbitrage_engine.data_collector.get_orderbook = Mock(return_value=None)
        
        # 调用几次find_opportunities
        for _ in range(5):
            arbitrage_engine.find_opportunities()
        
        # 获取统计信息
        stats = arbitrage_engine.get_statistics()
        
        # 验证统计数据
        assert isinstance(stats, dict)
        assert 'check_count' in stats
        assert 'opportunity_count' in stats
        assert 'average_profit_rate' in stats
        assert 'runtime_seconds' in stats
        
        assert stats['check_count'] == 5
        assert stats['opportunity_count'] == 0  # 由于订单簿为None
        
        logging.info(f"统计信息: {stats}")
    
    def test_profit_threshold_filtering(self, arbitrage_engine):
        """测试利润阈值过滤"""
        # 设置较高的利润阈值
        arbitrage_engine.min_profit_threshold = 0.01  # 1%
        
        # 创建低利润的模拟订单簿
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 1.0]],
                "asks": [[49900.0, 1.0]]  # 很小的价差
            },
            "ETH-USDT": {
                "bids": [[3000.0, 10.0]],
                "asks": [[2990.0, 10.0]]
            },
            "ETH-BTC": {
                "bids": [[0.060, 10.0]],
                "asks": [[0.0599, 10.0]]
            }
        }
        
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 测试机会检测
        opportunities = arbitrage_engine.find_opportunities()
        
        # 由于利润率低于阈值，应该没有机会
        assert len(opportunities) == 0
        
        logging.info(f"利润阈值过滤测试: 检测到{len(opportunities)}个机会")
    
    def test_concurrent_opportunity_detection(self, arbitrage_engine):
        """测试并发机会检测"""
        import threading
        
        # 创建稳定的模拟订单簿
        mock_orderbooks = {
            "BTC-USDT": {
                "bids": [[50000.0, 1.0]],
                "asks": [[50100.0, 1.0]]
            },
            "ETH-USDT": {
                "bids": [[3000.0, 10.0]],
                "asks": [[3050.0, 10.0]]
            },
            "ETH-BTC": {
                "bids": [[0.058, 10.0]],
                "asks": [[0.062, 10.0]]
            }
        }
        
        def mock_get_orderbook(pair):
            return mock_orderbooks.get(pair)
        
        arbitrage_engine.data_collector.get_orderbook = mock_get_orderbook
        
        # 并发检测机会
        results = []
        
        def detect_opportunities():
            opportunities = arbitrage_engine.find_opportunities()
            results.append(opportunities)
        
        # 创建多个线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=detect_opportunities)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == 5
        for result in results:
            assert isinstance(result, list)
        
        logging.info(f"并发检测结果: {len(results)}个线程完成")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])