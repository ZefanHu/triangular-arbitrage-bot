"""
测试交易执行器

使用OKX模拟盘进行真实交易执行测试
"""

import pytest
import time
import logging
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, List

from core.trade_executor import TradeExecutor, TradeResult, ArbitrageRecord, BalanceCache
from core.okx_client import OKXClient
from models.arbitrage_path import ArbitrageOpportunity, ArbitragePath
from models.trade import Trade, TradeStatus


class TestTradeExecutor:
    """交易执行器测试类"""
    
    @pytest.fixture
    def okx_client(self):
        """OKX客户端fixture"""
        return OKXClient()
    
    @pytest.fixture
    def mock_okx_client(self):
        """模拟OKX客户端fixture"""
        mock_client = Mock(spec=OKXClient)
        return mock_client
    
    @pytest.fixture
    def trade_executor(self, okx_client):
        """交易执行器fixture"""
        return TradeExecutor(okx_client)
    
    @pytest.fixture
    def mock_trade_executor(self, mock_okx_client):
        """模拟交易执行器fixture"""
        return TradeExecutor(mock_okx_client)
    
    @pytest.fixture
    def sample_opportunity(self):
        """样本套利机会fixture"""
        path = ArbitragePath(
            path=["USDT", "USDC", "BTC", "USDT"]
        )
        return ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,  # 0.5%利润率
            min_amount=100.0,
            timestamp=time.time()
        )
    
    @pytest.fixture
    def small_opportunity(self):
        """小额套利机会fixture"""
        path = ArbitragePath(
            path=["USDT", "BTC", "USDC", "USDT"]
        )
        return ArbitrageOpportunity(
            path=path,
            profit_rate=0.003,  # 0.3%利润率
            min_amount=50.0,
            timestamp=time.time()
        )
    
    def test_balance_cache_initialization(self, okx_client):
        """测试余额缓存初始化"""
        cache = BalanceCache(okx_client)
        
        assert cache.okx_client == okx_client
        assert cache.cache == {}
        assert cache.last_update == 0
        assert cache.cache_ttl == 30.0
    
    def test_balance_cache_update(self, mock_okx_client):
        """测试余额缓存更新"""
        # 设置模拟返回值
        mock_balance = {
            "USDT": 10000.0,
            "BTC": 0.5,
            "ETH": 5.0
        }
        mock_okx_client.get_balance.return_value = mock_balance
        
        cache = BalanceCache(mock_okx_client)
        
        # 测试获取余额
        balance = cache.get_balance()
        
        assert balance == mock_balance
        assert cache.cache == mock_balance
        assert cache.last_update > 0
        
        # 测试缓存命中
        mock_okx_client.get_balance.reset_mock()
        balance2 = cache.get_balance()
        
        assert balance2 == mock_balance
        assert not mock_okx_client.get_balance.called  # 不应该调用API
    
    def test_balance_cache_ttl(self, mock_okx_client):
        """测试余额缓存TTL"""
        mock_balance = {"USDT": 10000.0}
        mock_okx_client.get_balance.return_value = mock_balance
        
        cache = BalanceCache(mock_okx_client)
        cache.cache_ttl = 0.1  # 设置很短的TTL
        
        # 第一次获取
        balance1 = cache.get_balance()
        assert balance1 == mock_balance
        
        # 等待TTL过期
        time.sleep(0.2)
        
        # 再次获取，应该重新调用API
        balance2 = cache.get_balance()
        assert balance2 == mock_balance
        assert mock_okx_client.get_balance.call_count == 2
    
    def test_trade_executor_initialization(self, okx_client):
        """测试交易执行器初始化"""
        executor = TradeExecutor(okx_client)
        
        assert executor.okx_client == okx_client
        assert executor.order_timeout == 10.0
        assert executor.max_retries == 3
        assert isinstance(executor.balance_cache, BalanceCache)
        assert executor.trade_records == []
    
    def test_trade_result_creation(self):
        """测试交易结果创建"""
        # 成功的交易结果
        success_result = TradeResult(
            success=True,
            order_id="test_order_123",
            filled_size=0.01,
            avg_price=50000.0
        )
        
        assert success_result.success
        assert success_result.order_id == "test_order_123"
        assert success_result.filled_size == 0.01
        assert success_result.avg_price == 50000.0
        assert success_result.error_message is None
        
        # 失败的交易结果
        failure_result = TradeResult(
            success=False,
            error_message="Insufficient balance"
        )
        
        assert not failure_result.success
        assert failure_result.error_message == "Insufficient balance"
        assert failure_result.order_id is None
    
    def test_price_optimization(self, mock_trade_executor):
        """测试价格优化"""
        # 模拟市场行情
        mock_ticker = {
            "best_bid": 50000.0,
            "best_ask": 50100.0
        }
        
        # 测试买入价格优化
        buy_price = mock_trade_executor._optimize_price_for_trade(
            "BTC-USDT", "buy", 50050.0, mock_ticker
        )
        # 买入价格应该略高于买一价
        assert buy_price > mock_ticker["best_bid"]
        assert buy_price <= mock_ticker["best_ask"] * 1.005
        
        # 测试卖出价格优化
        sell_price = mock_trade_executor._optimize_price_for_trade(
            "BTC-USDT", "sell", 50050.0, mock_ticker
        )
        # 卖出价格应该略低于卖一价
        assert sell_price < mock_ticker["best_ask"]
        assert sell_price >= mock_ticker["best_bid"] * 0.995
    
    def test_trade_generation(self, trade_executor, sample_opportunity):
        """测试交易生成"""
        # 使用真实的OKX API生成交易
        trades = trade_executor._generate_trades(sample_opportunity, 1000.0)
        
        assert isinstance(trades, list)
        assert len(trades) == 3  # 三笔交易
        
        # 验证每笔交易
        for trade in trades:
            assert isinstance(trade, Trade)
            assert trade.inst_id in ["USDT-USDC", "BTC-USDC", "BTC-USDT"]
            assert trade.side in ["buy", "sell"]
            assert trade.size > 0
            assert trade.price > 0
    
    def test_balance_check(self, mock_trade_executor, sample_opportunity):
        """测试余额检查"""
        # 设置模拟余额
        mock_balance = {
            "USDT": 10000.0,
            "BTC": 0.5,
            "ETH": 5.0
        }
        mock_trade_executor.okx_client.get_balance.return_value = mock_balance
        
        # 测试充足余额
        result = mock_trade_executor.get_balance_check(sample_opportunity, 1000.0)
        
        assert result["success"]
        assert result["start_asset"] == "USDT"
        assert result["required_balance"] == 1000.0
        assert result["available_balance"] == 10000.0
        
        # 测试不足余额
        result = mock_trade_executor.get_balance_check(sample_opportunity, 15000.0)
        
        assert not result["success"]
        assert "余额不足" in result["error"]
    
    def test_pre_trade_check(self, mock_trade_executor, sample_opportunity):
        """测试交易前检查"""
        # 设置模拟数据
        mock_balance = {"USDT": 10000.0, "BTC": 0.5, "ETH": 5.0}
        mock_trade_executor.okx_client.get_balance.return_value = mock_balance
        
        # 模拟_pre_trade_check方法
        def mock_pre_trade_check(opportunity, amount):
            # 检查机会是否过期
            if opportunity.is_expired():
                return {"success": False, "error": "机会已过期"}
            
            # 检查余额
            balance_check = mock_trade_executor.get_balance_check(opportunity, amount)
            if not balance_check["success"]:
                return {"success": False, "error": balance_check["error"]}
            
            return {"success": True, "message": "交易前检查通过"}
        
        mock_trade_executor._pre_trade_check = mock_pre_trade_check
        
        # 测试正常情况
        result = mock_trade_executor._pre_trade_check(sample_opportunity, 1000.0)
        assert result["success"]
        assert result["message"] == "交易前检查通过"
    
    def test_single_trade_execution_mock(self, mock_trade_executor):
        """测试单笔交易执行（模拟）"""
        # 设置模拟返回值
        mock_ticker = {
            "best_bid": 50000.0,
            "best_ask": 50100.0
        }
        mock_trade_executor.okx_client.get_ticker.return_value = mock_ticker
        mock_trade_executor.okx_client.place_order.return_value = "test_order_123"
        
        # 模拟订单状态查询
        order_status = {
            "state": "filled",
            "filled_size": 0.01,
            "avg_price": 50050.0
        }
        mock_trade_executor.okx_client.get_order_status.return_value = order_status
        
        # 执行单笔交易
        result = mock_trade_executor._execute_single_trade(
            "BTC-USDT", "buy", 0.01, 50050.0
        )
        
        assert result.success
        assert result.order_id == "test_order_123"
        assert result.filled_size == 0.01
        assert result.avg_price == 50050.0
    
    def test_single_trade_timeout(self, mock_trade_executor):
        """测试单笔交易超时"""
        # 设置模拟返回值
        mock_ticker = {
            "best_bid": 50000.0,
            "best_ask": 50100.0
        }
        mock_trade_executor.okx_client.get_ticker.return_value = mock_ticker
        mock_trade_executor.okx_client.place_order.return_value = "test_order_123"
        
        # 模拟订单一直处于等待状态
        order_status = {
            "state": "live",
            "filled_size": 0,
            "avg_price": 0
        }
        mock_trade_executor.okx_client.get_order_status.return_value = order_status
        mock_trade_executor.okx_client.cancel_order.return_value = True
        
        # 设置很短的超时时间
        mock_trade_executor.order_timeout = 0.1
        
        # 执行单笔交易
        result = mock_trade_executor._execute_single_trade(
            "BTC-USDT", "buy", 0.01, 50050.0
        )
        
        assert not result.success
        assert "经过 3 次尝试后仍未成交" in result.error_message
    
    def test_order_status_monitoring(self, mock_trade_executor):
        """测试订单状态监控"""
        # 模拟订单状态变化
        status_sequence = [
            {"state": "live", "filled_size": 0, "avg_price": 0},
            {"state": "partially_filled", "filled_size": 0.005, "avg_price": 50000.0},
            {"state": "filled", "filled_size": 0.01, "avg_price": 50050.0}
        ]
        
        call_count = 0
        def mock_get_order_status(inst_id, order_id):
            nonlocal call_count
            if call_count < len(status_sequence):
                result = status_sequence[call_count]
                call_count += 1
                return result
            return status_sequence[-1]
        
        mock_trade_executor.okx_client.get_order_status = mock_get_order_status
        
        # 监控订单状态
        result = mock_trade_executor._wait_order_filled("BTC-USDT", "test_order_123", 5.0)
        
        assert result.success
        assert result.filled_size == 0.01
        assert result.avg_price == 50050.0
    
    def test_arbitrage_execution_mock(self, trade_executor, sample_opportunity):
        """测试套利执行（使用真实OKX API）"""
        # 执行套利交易检查（不实际执行订单）
        # 首先测试交易前检查
        pre_check_result = trade_executor._pre_trade_check(sample_opportunity, 1000.0)
        
        if not pre_check_result["success"]:
            # 如果余额不足，跳过此测试
            import pytest
            pytest.skip(f"交易前检查失败: {pre_check_result['error']}")
        
        # 测试交易生成
        trades = trade_executor._generate_trades(sample_opportunity, 1000.0)
        
        # 验证交易生成结果
        assert isinstance(trades, list)
        assert len(trades) == 3  # 三笔交易
        
        # 验证每笔交易的基本信息
        for trade in trades:
            assert isinstance(trade, Trade)
            assert trade.inst_id in ["USDT-USDC", "BTC-USDC", "BTC-USDT"]
            assert trade.side in ["buy", "sell"]
            assert trade.size > 0
            assert trade.price > 0
    
    @pytest.mark.integration
    def test_real_balance_query(self, okx_client):
        """集成测试：查询真实余额"""
        executor = TradeExecutor(okx_client)
        
        # 获取真实余额
        balance = executor.balance_cache.get_balance()
        
        if balance:
            assert isinstance(balance, dict)
            logging.info(f"真实余额: {balance}")
            
            # 验证余额格式
            for asset, amount in balance.items():
                assert isinstance(asset, str)
                assert isinstance(amount, (int, float))
                assert amount >= 0
        else:
            pytest.skip("无法获取真实余额数据")
    
    @pytest.mark.integration
    def test_real_market_data_query(self, okx_client):
        """集成测试：查询真实市场数据"""
        executor = TradeExecutor(okx_client)
        
        # 测试交易对（基于USDT/USDC/BTC三币种配置）
        test_pairs = ["BTC-USDT", "USDT-USDC", "BTC-USDC"]
        
        for pair in test_pairs:
            # 使用支持合成价格的方法
            price_info = executor._get_trading_pair_price(pair)
            
            if price_info:
                assert "best_bid" in price_info
                assert "best_ask" in price_info
                assert price_info["best_bid"] > 0
                assert price_info["best_ask"] > 0
                assert price_info["best_ask"] > price_info["best_bid"]
                
                logging.info(f"{pair} 行情: 买一={price_info['best_bid']}, 卖一={price_info['best_ask']}")
            else:
                logging.warning(f"无法获取{pair}行情数据")
    
    @pytest.mark.integration
    def test_small_amount_trade_simulation(self, okx_client, small_opportunity):
        """集成测试：小额交易模拟"""
        executor = TradeExecutor(okx_client)
        
        # 检查余额
        balance = executor.balance_cache.get_balance()
        if not balance or balance.get("USDT", 0) < 100:
            pytest.skip("余额不足，无法进行小额交易测试")
        
        # 生成交易计划（不实际执行）
        trades = executor._generate_trades(small_opportunity, 100.0)
        
        if trades:
            assert len(trades) == 3
            logging.info("小额交易计划生成成功:")
            
            for i, trade in enumerate(trades):
                logging.info(f"第{i+1}笔: {trade.inst_id} {trade.side} {trade.size:.6f} @ {trade.price:.6f}")
                
                # 验证交易参数
                assert trade.size > 0
                assert trade.price > 0
                assert trade.side in ["buy", "sell"]
        else:
            pytest.skip("无法生成交易计划")
    
    def test_error_handling_insufficient_balance(self, trade_executor, sample_opportunity):
        """测试余额不足错误处理"""
        # 使用一个很大的金额来测试余额不足情况
        result = trade_executor.execute_arbitrage(sample_opportunity, 100000.0)
        
        assert not result["success"]
        assert "余额不足" in result["error"] or "insufficient" in result["error"].lower()
    
    def test_error_handling_expired_opportunity(self, mock_trade_executor):
        """测试过期机会错误处理"""
        # 创建过期的机会
        expired_opportunity = Mock()
        expired_opportunity.is_expired.return_value = True
        
        # 执行套利
        result = mock_trade_executor.execute_arbitrage(expired_opportunity, 1000.0)
        
        assert not result["success"]
        assert "过期" in result["error"]
    
    def test_trade_records_management(self, mock_trade_executor, sample_opportunity):
        """测试交易记录管理"""
        # 设置模拟数据
        mock_balance = {"USDT": 10000.0}
        mock_trade_executor.okx_client.get_balance.return_value = mock_balance
        
        # 模拟交易前检查失败
        def mock_pre_trade_check(opportunity, amount):
            return {"success": False, "error": "测试错误"}
        
        mock_trade_executor._pre_trade_check = mock_pre_trade_check
        
        # 执行套利
        result = mock_trade_executor.execute_arbitrage(sample_opportunity, 1000.0)
        
        assert not result["success"]
        assert len(mock_trade_executor.trade_records) == 1
        
        # 验证记录内容
        record = mock_trade_executor.trade_records[0]
        assert isinstance(record, ArbitrageRecord)
        assert record.opportunity == sample_opportunity
        assert record.investment_amount == 1000.0
        assert not record.success
    
    def test_concurrent_execution_safety(self, mock_trade_executor, sample_opportunity):
        """测试并发执行安全性"""
        import threading
        
        # 设置模拟数据
        mock_balance = {"USDT": 10000.0}
        mock_trade_executor.okx_client.get_balance.return_value = mock_balance
        
        def mock_pre_trade_check(opportunity, amount):
            time.sleep(0.1)  # 模拟处理时间
            return {"success": True, "message": "检查通过"}
        
        mock_trade_executor._pre_trade_check = mock_pre_trade_check
        
        # 模拟交易生成失败
        mock_trade_executor._generate_trades = Mock(return_value=[])
        
        # 并发执行
        results = []
        
        def execute_arbitrage():
            result = mock_trade_executor.execute_arbitrage(sample_opportunity, 1000.0)
            results.append(result)
        
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=execute_arbitrage)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == 3
        for result in results:
            assert not result["success"]  # 由于_generate_trades返回空列表
            assert "无法生成交易列表" in result["error"]


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])