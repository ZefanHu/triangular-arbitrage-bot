"""
端到端集成测试

使用真实市场数据测试完整的套利发现→风险检查→执行流程
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch
from typing import Dict, List

from core.trading_controller import TradingController
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.trade_executor import TradeExecutor
from core.risk_manager import RiskManager
from core.okx_client import OKXClient
from config.config_manager import ConfigManager
from models.order_book import OrderBook


class TestIntegration:
    """集成测试类"""
    
    @pytest.fixture
    def config_manager(self):
        """配置管理器fixture"""
        config_manager = ConfigManager()
        # 使用测试配置
        config_manager.config_file = "/home/huzefan/triangular-arbitrage-bot/tests/test_settings.ini"
        return config_manager
    
    @pytest.fixture
    def okx_client(self):
        """OKX客户端fixture"""
        return OKXClient()
    
    @pytest.fixture
    def data_collector(self):
        """数据采集器fixture"""
        return DataCollector()
    
    @pytest.fixture
    def arbitrage_engine(self, data_collector):
        """套利引擎fixture"""
        return ArbitrageEngine(data_collector)
    
    @pytest.fixture
    def trade_executor(self, okx_client):
        """交易执行器fixture"""
        return TradeExecutor(okx_client)
    
    @pytest.fixture
    def risk_manager(self, config_manager, okx_client):
        """风险管理器fixture"""
        return RiskManager(config_manager, okx_client)
    
    @pytest.fixture
    def trading_controller(self, config_manager):
        """交易控制器fixture"""
        return TradingController(config_manager)
    
    @pytest.fixture
    def test_trading_pairs(self):
        """测试交易对fixture"""
        return ["BTC-USDT", "ETH-USDT", "ETH-BTC"]
    
    @pytest.mark.integration
    async def test_data_collector_startup_shutdown(self, data_collector, test_trading_pairs):
        """测试数据采集器启动和关闭"""
        # 启动数据采集器
        success = await data_collector.start(test_trading_pairs)
        
        if not success:
            pytest.skip("无法启动数据采集器")
        
        # 验证启动状态
        assert data_collector.is_running
        assert len(data_collector.subscribed_pairs) > 0
        
        # 等待数据稳定
        await asyncio.sleep(3)
        
        # 测试数据获取
        for pair in test_trading_pairs:
            orderbook = data_collector.get_orderbook(pair)
            if orderbook:
                assert orderbook.symbol == pair
                assert len(orderbook.bids) > 0
                assert len(orderbook.asks) > 0
                logging.info(f"{pair} 订单簿数据正常")
        
        # 测试余额获取
        balance = data_collector.get_balance()
        if balance:
            assert isinstance(balance.balances, dict)
            logging.info(f"余额数据: {balance.balances}")
        
        # 关闭数据采集器
        success = await data_collector.stop()
        assert success
        assert not data_collector.is_running
    
    @pytest.mark.integration
    async def test_arbitrage_engine_with_real_data(self, data_collector, arbitrage_engine, test_trading_pairs):
        """测试套利引擎使用真实数据"""
        # 启动数据采集器
        success = await data_collector.start(test_trading_pairs)
        
        if not success:
            pytest.skip("无法启动数据采集器")
        
        try:
            # 等待数据稳定
            await asyncio.sleep(5)
            
            # 测试套利机会发现
            opportunities = arbitrage_engine.find_opportunities()
            
            assert isinstance(opportunities, list)
            logging.info(f"发现套利机会: {len(opportunities)}")
            
            # 验证机会数据结构
            for opp in opportunities:
                assert 'path_name' in opp
                assert 'path' in opp
                assert 'profit_rate' in opp
                assert 'min_trade_amount' in opp
                assert 'max_trade_amount' in opp
                assert isinstance(opp['profit_rate'], float)
                
                logging.info(f"机会: {opp['path_name']}, 利润率: {opp['profit_rate']:.4%}")
            
            # 测试路径利润计算
            test_paths = [
                ["USDT", "BTC", "ETH", "USDT"],
                ["USDT", "ETH", "BTC", "USDT"]
            ]
            
            for path in test_paths:
                final_amount, profit_rate = arbitrage_engine.calculate_path_profit(path, 1000.0)
                
                assert isinstance(final_amount, float)
                assert isinstance(profit_rate, float)
                
                logging.info(f"路径 {' -> '.join(path)}: 最终金额={final_amount:.6f}, 利润率={profit_rate:.6f}")
            
            # 获取统计信息
            stats = arbitrage_engine.get_statistics()
            assert isinstance(stats, dict)
            assert stats['check_count'] > 0
            
            logging.info(f"引擎统计: {stats}")
            
        finally:
            # 关闭数据采集器
            await data_collector.stop()
    
    @pytest.mark.integration
    def test_risk_manager_with_real_balance(self, risk_manager):
        """测试风险管理器使用真实余额"""
        # 获取真实余额
        balance = risk_manager.get_current_balance()
        
        if not balance:
            pytest.skip("无法获取真实余额")
        
        logging.info(f"真实余额: {balance}")
        
        # 计算总资产价值
        total_usdt = risk_manager._calculate_total_balance_usdt(balance)
        assert total_usdt > 0
        
        logging.info(f"总资产价值: {total_usdt} USDT")
        
        # 测试仓位限制检查
        for asset in balance:
            if balance[asset] > 0:
                # 测试小额交易
                small_amount = min(balance[asset] * 0.05, 100.0)
                result = risk_manager.check_position_limit(asset, small_amount)
                
                logging.info(f"{asset} 小额交易检查: {result.passed}, {result.message}")
                
                if result.passed:
                    assert result.suggested_amount > 0
        
        # 测试频率检查
        frequency_result = risk_manager.check_arbitrage_frequency()
        assert frequency_result.passed  # 初始状态应该通过
        
        logging.info(f"频率检查: {frequency_result.passed}, {frequency_result.message}")
        
        # 获取风险统计
        stats = risk_manager.get_risk_statistics()
        assert isinstance(stats, dict)
        
        logging.info(f"风险统计: {stats}")
    
    @pytest.mark.integration
    def test_trade_executor_with_real_client(self, trade_executor):
        """测试交易执行器使用真实客户端"""
        # 测试余额查询
        balance = trade_executor.balance_cache.get_balance()
        
        if balance:
            assert isinstance(balance, dict)
            logging.info(f"交易执行器余额: {balance}")
        else:
            pytest.skip("无法获取余额数据")
        
        # 测试市场数据查询
        test_pairs = ["BTC-USDT", "ETH-USDT", "ETH-BTC"]
        
        for pair in test_pairs:
            ticker = trade_executor.okx_client.get_ticker(pair)
            
            if ticker:
                assert "best_bid" in ticker
                assert "best_ask" in ticker
                assert ticker["best_bid"] > 0
                assert ticker["best_ask"] > 0
                assert ticker["best_ask"] > ticker["best_bid"]
                
                logging.info(f"{pair} 行情: 买一={ticker['best_bid']}, 卖一={ticker['best_ask']}")
        
        # 测试订单簿数据
        for pair in test_pairs:
            orderbook = trade_executor.okx_client.get_orderbook(pair)
            
            if orderbook and isinstance(orderbook, OrderBook):
                # orderbook 现在是 OrderBook 对象
                assert orderbook.symbol == pair
                assert len(orderbook.bids) > 0
                assert len(orderbook.asks) > 0
                
                logging.info(f"{pair} 订单簿: {len(orderbook.bids)}档买单, {len(orderbook.asks)}档卖单")
    
    @pytest.mark.integration
    async def test_full_arbitrage_flow_simulation(self, data_collector, arbitrage_engine, risk_manager, test_trading_pairs):
        """测试完整套利流程模拟（不实际下单）"""
        # 启动数据采集器
        success = await data_collector.start(test_trading_pairs)
        
        if not success:
            pytest.skip("无法启动数据采集器")
        
        try:
            # 等待数据稳定
            await asyncio.sleep(5)
            
            # 1. 发现套利机会
            opportunities = arbitrage_engine.find_opportunities()
            
            logging.info(f"=== 套利流程测试 ===")
            logging.info(f"发现机会数量: {len(opportunities)}")
            
            if not opportunities:
                logging.info("未发现套利机会，跳过后续测试")
                return
            
            # 2. 处理每个机会
            for i, opp in enumerate(opportunities):
                logging.info(f"--- 处理机会 {i+1}: {opp['path_name']} ---")
                logging.info(f"路径: {' -> '.join(opp['path'])}")
                logging.info(f"利润率: {opp['profit_rate']:.4%}")
                
                # 创建ArbitrageOpportunity对象
                from models.arbitrage_path import ArbitrageOpportunity, ArbitragePath
                
                path = ArbitragePath(
                    path=opp['path']
                )
                
                opportunity = ArbitrageOpportunity(
                    path=path,
                    profit_rate=opp['profit_rate'],
                    min_amount=opp['min_trade_amount'],
                    timestamp=opp['timestamp']
                )
                
                # 3. 风险检查
                balance = risk_manager.get_current_balance()
                if not balance:
                    logging.warning("无法获取余额，跳过风险检查")
                    continue
                
                total_usdt = risk_manager._calculate_total_balance_usdt(balance)
                
                # 频率检查
                frequency_result = risk_manager.check_arbitrage_frequency()
                logging.info(f"频率检查: {frequency_result.passed}, {frequency_result.message}")
                
                if not frequency_result.passed:
                    continue
                
                # 机会验证
                validation_result = risk_manager.validate_opportunity(opportunity, total_usdt)
                logging.info(f"机会验证: {validation_result.passed}, {validation_result.message}")
                
                if not validation_result.passed:
                    continue
                
                # 4. 计算交易量
                position_size = risk_manager.calculate_position_size(opportunity, balance)
                logging.info(f"建议交易量: {position_size:.6f}")
                
                if position_size <= 0:
                    logging.warning("交易量为0，跳过执行")
                    continue
                
                # 5. 模拟交易执行（生成交易计划）
                from core.trade_executor import TradeExecutor
                
                executor = TradeExecutor(risk_manager.okx_client)
                trades = executor._generate_trades(opportunity, position_size)
                
                if trades:
                    logging.info(f"生成交易计划: {len(trades)}笔交易")
                    for j, trade in enumerate(trades):
                        logging.info(f"  第{j+1}笔: {trade.inst_id} {trade.side} {trade.size:.6f} @ {trade.price:.6f}")
                else:
                    logging.warning("无法生成交易计划")
                
                # 6. 记录尝试（模拟）
                risk_manager.record_arbitrage_attempt(True, 0)  # 模拟成功，0利润
                
                logging.info(f"机会 {i+1} 处理完成")
            
            # 获取最终统计
            engine_stats = arbitrage_engine.get_statistics()
            risk_stats = risk_manager.get_risk_statistics()
            
            logging.info(f"=== 最终统计 ===")
            logging.info(f"引擎统计: {engine_stats}")
            logging.info(f"风险统计: {risk_stats}")
            
        finally:
            # 关闭数据采集器
            await data_collector.stop()
    
    @pytest.mark.integration
    async def test_trading_controller_lifecycle(self, trading_controller):
        """测试交易控制器生命周期"""
        # 测试启动
        logging.info("=== 测试交易控制器启动 ===")
        success = await trading_controller.start()
        
        if not success:
            pytest.skip("无法启动交易控制器")
        
        # 验证启动状态
        status = trading_controller.get_status()
        assert status['is_running']
        assert status['data_collector_running']
        
        logging.info(f"控制器状态: {status}")
        
        # 运行一段时间
        logging.info("运行控制器30秒...")
        await asyncio.sleep(30)
        
        # 获取统计信息
        stats = trading_controller.get_stats()
        risk_stats = trading_controller.get_risk_stats()
        
        logging.info(f"交易统计: {stats}")
        logging.info(f"风险统计: {risk_stats}")
        
        # 测试停止
        logging.info("=== 测试交易控制器停止 ===")
        success = await trading_controller.stop()
        assert success
        
        # 验证停止状态
        status = trading_controller.get_status()
        assert not status['is_running']
        
        logging.info("交易控制器生命周期测试完成")
    
    @pytest.mark.integration
    async def test_error_handling_integration(self, trading_controller):
        """测试错误处理集成"""
        # 测试重复启动
        await trading_controller.start()
        
        # 重复启动应该返回True但不会重复初始化
        success = await trading_controller.start()
        assert success
        
        # 测试异常情况下的停止
        await trading_controller.stop()
        
        # 重复停止应该返回True
        success = await trading_controller.stop()
        assert success
    
    @pytest.mark.integration
    def test_configuration_integration(self, config_manager):
        """测试配置集成"""
        # 测试交易配置
        trading_config = config_manager.get_trading_config()
        assert isinstance(trading_config, dict)
        assert 'paths' in trading_config
        assert 'parameters' in trading_config
        
        logging.info(f"交易配置: {trading_config}")
        
        # 测试风险配置
        risk_config = config_manager.get_risk_config()
        assert isinstance(risk_config, dict)
        
        logging.info(f"风险配置: {risk_config}")
        
        # 测试API配置
        api_config = config_manager.get_api_config()
        assert isinstance(api_config, dict)
        
        logging.info(f"API配置: {api_config}")
    
    @pytest.mark.integration
    async def test_performance_under_load(self, data_collector, arbitrage_engine, test_trading_pairs):
        """测试负载下的性能"""
        # 启动数据采集器
        success = await data_collector.start(test_trading_pairs)
        
        if not success:
            pytest.skip("无法启动数据采集器")
        
        try:
            # 等待数据稳定
            await asyncio.sleep(5)
            
            # 执行多次机会检测
            start_time = time.time()
            iterations = 50
            
            for i in range(iterations):
                opportunities = arbitrage_engine.find_opportunities()
                
                if i % 10 == 0:
                    logging.info(f"第{i+1}次检测，发现机会: {len(opportunities)}")
                
                # 短暂延迟
                await asyncio.sleep(0.1)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # 获取统计信息
            stats = arbitrage_engine.get_statistics()
            
            logging.info(f"=== 性能测试结果 ===")
            logging.info(f"总时间: {total_time:.2f}秒")
            logging.info(f"平均每次检测时间: {total_time/iterations:.3f}秒")
            logging.info(f"总检测次数: {stats['check_count']}")
            logging.info(f"发现机会总数: {stats['opportunity_count']}")
            logging.info(f"检测频率: {stats['checks_per_minute']:.1f}次/分钟")
            
            # 验证性能指标
            assert total_time < 60  # 50次检测应该在60秒内完成
            assert stats['check_count'] >= iterations
            
        finally:
            # 关闭数据采集器
            await data_collector.stop()
    
    @pytest.mark.integration
    async def test_concurrent_operations(self, data_collector, arbitrage_engine, test_trading_pairs):
        """测试并发操作"""
        # 启动数据采集器
        success = await data_collector.start(test_trading_pairs)
        
        if not success:
            pytest.skip("无法启动数据采集器")
        
        try:
            # 等待数据稳定
            await asyncio.sleep(5)
            
            # 并发执行多个操作
            async def find_opportunities_task():
                results = []
                for _ in range(10):
                    opportunities = arbitrage_engine.find_opportunities()
                    results.append(opportunities)
                    await asyncio.sleep(0.1)
                return results
            
            async def get_orderbook_task():
                results = []
                for _ in range(10):
                    for pair in test_trading_pairs:
                        orderbook = data_collector.get_orderbook(pair)
                        results.append(orderbook)
                    await asyncio.sleep(0.1)
                return results
            
            async def get_balance_task():
                results = []
                for _ in range(10):
                    balance = data_collector.get_balance()
                    results.append(balance)
                    await asyncio.sleep(0.1)
                return results
            
            # 并发运行任务
            logging.info("开始并发测试...")
            tasks = [
                find_opportunities_task(),
                get_orderbook_task(),
                get_balance_task()
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 验证结果
            opportunities_results, orderbook_results, balance_results = results
            
            assert len(opportunities_results) == 10
            assert len(orderbook_results) == 10 * len(test_trading_pairs)
            assert len(balance_results) == 10
            
            logging.info("并发测试完成")
            
        finally:
            # 关闭数据采集器
            await data_collector.stop()
    
    @pytest.mark.integration
    def test_logging_integration(self, trading_controller):
        """测试日志集成"""
        # 配置测试日志
        test_logger = logging.getLogger("test_integration")
        test_logger.setLevel(logging.INFO)
        
        # 测试各个模块的日志
        test_logger.info("开始日志集成测试")
        
        # 验证日志配置
        assert test_logger.level == logging.INFO
        
        # 测试组件日志
        components = [
            trading_controller.data_collector,
            trading_controller.arbitrage_engine,
            trading_controller.trade_executor,
            trading_controller.risk_manager
        ]
        
        for component in components:
            logger = component.logger
            assert logger is not None
            logger.info(f"{component.__class__.__name__} 日志测试")
        
        test_logger.info("日志集成测试完成")
    
    @pytest.mark.integration
    async def test_graceful_shutdown(self, trading_controller):
        """测试优雅关闭"""
        # 启动控制器
        success = await trading_controller.start()
        
        if not success:
            pytest.skip("无法启动交易控制器")
        
        # 运行一段时间
        await asyncio.sleep(5)
        
        # 测试优雅关闭
        logging.info("开始优雅关闭测试...")
        
        start_time = time.time()
        success = await trading_controller.stop()
        end_time = time.time()
        
        shutdown_time = end_time - start_time
        
        assert success
        assert shutdown_time < 30  # 关闭应该在30秒内完成
        
        logging.info(f"优雅关闭完成，用时: {shutdown_time:.2f}秒")
        
        # 验证关闭状态
        status = trading_controller.get_status()
        assert not status['is_running']


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])