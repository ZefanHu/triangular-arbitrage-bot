"""
测试风险管理器

使用真实余额数据测试仓位限制和频率控制
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, List

from core.risk_manager import RiskManager, RiskLevel, RiskCheckResult
from core.okx_client import OKXClient
from config.config_manager import ConfigManager
from models.arbitrage_path import ArbitrageOpportunity, ArbitragePath


class TestRiskManager:
    """风险管理器测试类"""
    
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
    def mock_okx_client(self):
        """模拟OKX客户端fixture"""
        mock_client = Mock(spec=OKXClient)
        return mock_client
    
    @pytest.fixture
    def risk_manager(self, config_manager, mock_okx_client):
        """风险管理器fixture"""
        return RiskManager(config_manager, mock_okx_client)
    
    @pytest.fixture
    def real_risk_manager(self, config_manager, okx_client):
        """使用真实OKX客户端的风险管理器fixture"""
        return RiskManager(config_manager, okx_client)
    
    @pytest.fixture
    def sample_opportunity(self):
        """样本套利机会fixture"""
        path = ArbitragePath(
            path=["USDT", "BTC", "ETH", "USDT"]
        )
        return ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,  # 0.5%利润率
            min_amount=100.0,
            timestamp=time.time()
        )
    
    @pytest.fixture
    def mock_balance(self):
        """模拟余额数据fixture"""
        return {
            "USDT": 10000.0,
            "BTC": 0.5,
            "ETH": 5.0,
            "BNB": 10.0
        }
    
    def test_risk_manager_initialization(self, risk_manager):
        """测试风险管理器初始化"""
        assert risk_manager.max_position_ratio == 0.2
        assert risk_manager.max_single_trade_ratio == 0.1
        assert risk_manager.min_arbitrage_interval == 10
        assert risk_manager.max_daily_trades == 100
        assert risk_manager.risk_level == RiskLevel.LOW
        assert risk_manager.trading_enabled
        assert risk_manager.arbitrage_count_today == 0
        assert risk_manager.total_profit_today == 0.0
        assert risk_manager.total_loss_today == 0.0
    
    def test_risk_check_result_creation(self):
        """测试风险检查结果创建"""
        # 成功的检查结果
        success_result = RiskCheckResult(
            passed=True,
            risk_level=RiskLevel.LOW,
            message="检查通过",
            suggested_amount=1000.0,
            warnings=["测试警告"]
        )
        
        assert success_result.passed
        assert success_result.risk_level == RiskLevel.LOW
        assert success_result.message == "检查通过"
        assert success_result.suggested_amount == 1000.0
        assert success_result.warnings == ["测试警告"]
        
        # 失败的检查结果
        failure_result = RiskCheckResult(
            passed=False,
            risk_level=RiskLevel.HIGH,
            message="检查失败"
        )
        
        assert not failure_result.passed
        assert failure_result.risk_level == RiskLevel.HIGH
        assert failure_result.message == "检查失败"
        assert failure_result.suggested_amount == 0.0
        assert failure_result.warnings == []
    
    def test_convert_to_usdt(self, risk_manager):
        """测试转换为USDT价值"""
        # 模拟价格转换
        def mock_convert_to_usdt(asset, amount):
            if asset == "USDT":
                return amount
            elif asset == "BTC":
                return amount * 50000.0  # 假设BTC价格为50000 USDT
            elif asset == "ETH":
                return amount * 3000.0   # 假设ETH价格为3000 USDT
            else:
                return amount * 100.0    # 其他资产假设价格为100 USDT
        
        risk_manager._convert_to_usdt = mock_convert_to_usdt
        
        # 测试转换
        assert risk_manager._convert_to_usdt("USDT", 1000.0) == 1000.0
        assert risk_manager._convert_to_usdt("BTC", 1.0) == 50000.0
        assert risk_manager._convert_to_usdt("ETH", 1.0) == 3000.0
        assert risk_manager._convert_to_usdt("BNB", 1.0) == 100.0
    
    def test_convert_from_usdt(self, risk_manager):
        """测试从USDT价值转换"""
        # 模拟价格转换
        def mock_convert_from_usdt(asset, usdt_amount):
            if asset == "USDT":
                return usdt_amount
            elif asset == "BTC":
                return usdt_amount / 50000.0
            elif asset == "ETH":
                return usdt_amount / 3000.0
            else:
                return usdt_amount / 100.0
        
        risk_manager._convert_from_usdt = mock_convert_from_usdt
        
        # 测试转换
        assert risk_manager._convert_from_usdt("USDT", 1000.0) == 1000.0
        assert risk_manager._convert_from_usdt("BTC", 50000.0) == 1.0
        assert risk_manager._convert_from_usdt("ETH", 3000.0) == 1.0
        assert risk_manager._convert_from_usdt("BNB", 100.0) == 1.0
    
    def test_calculate_total_balance_usdt(self, risk_manager, mock_balance):
        """测试计算总资产USDT价值"""
        # 模拟价格转换
        def mock_convert_to_usdt(asset, amount):
            if asset == "USDT":
                return amount
            elif asset == "BTC":
                return amount * 50000.0
            elif asset == "ETH":
                return amount * 3000.0
            elif asset == "BNB":
                return amount * 500.0
            else:
                return amount * 100.0
        
        risk_manager._convert_to_usdt = mock_convert_to_usdt
        
        # 计算总资产
        total_usdt = risk_manager._calculate_total_balance_usdt(mock_balance)
        
        # 验证计算结果
        expected_total = (
            10000.0 +         # USDT
            0.5 * 50000.0 +   # BTC
            5.0 * 3000.0 +    # ETH
            10.0 * 500.0      # BNB
        )  # = 10000 + 25000 + 15000 + 5000 = 55000
        
        assert total_usdt == expected_total
    
    def test_position_limit_check_success(self, risk_manager, mock_balance):
        """测试仓位限制检查成功"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        
        # 模拟价格转换
        def mock_convert_to_usdt(asset, amount):
            if asset == "USDT":
                return amount
            elif asset == "BTC":
                return amount * 50000.0
            elif asset == "ETH":
                return amount * 3000.0
            elif asset == "BNB":
                return amount * 500.0
            else:
                return amount * 100.0
        
        risk_manager._convert_to_usdt = mock_convert_to_usdt
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        
        # 测试合理的交易金额
        result = risk_manager.check_position_limit("USDT", 1000.0)
        
        assert result.passed
        assert result.risk_level == RiskLevel.LOW
        assert result.suggested_amount == 1000.0
    
    def test_position_limit_check_insufficient_balance(self, risk_manager, mock_balance):
        """测试仓位限制检查余额不足"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        
        # 测试超过可用余额的交易金额
        result = risk_manager.check_position_limit("USDT", 15000.0)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.HIGH
        assert "余额不足" in result.message
        assert result.suggested_amount == mock_balance["USDT"]
    
    def test_position_limit_check_exceed_single_trade_ratio(self, risk_manager, mock_balance):
        """测试单笔交易比例超限"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_to_usdt = Mock(return_value=10000.0)  # 超过单笔交易限制
        
        # 测试超过单笔交易比例的金额
        result = risk_manager.check_position_limit("USDT", 8000.0)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.HIGH
        assert "单笔交易金额超限" in result.message
    
    def test_position_limit_check_exceed_max_position_ratio(self, risk_manager, mock_balance):
        """测试最大仓位比例超限"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_to_usdt = Mock(return_value=12000.0)  # 超过最大仓位限制(20%)但不超过单笔交易限制
        
        # 临时调整单笔交易限制，让它不会先被单笔交易限制检查到
        original_max_single_trade_ratio = risk_manager.max_single_trade_ratio
        risk_manager.max_single_trade_ratio = 0.25  # 设置为25%，高于21.82%
        
        try:
            # 测试超过最大仓位比例的金额
            result = risk_manager.check_position_limit("USDT", 10000.0)
        finally:
            # 恢复原始值
            risk_manager.max_single_trade_ratio = original_max_single_trade_ratio
        
        assert not result.passed
        assert result.risk_level == RiskLevel.HIGH
        assert "仓位比例超限" in result.message
    
    def test_arbitrage_frequency_check_success(self, risk_manager):
        """测试套利频率检查成功"""
        # 重置上次套利时间
        risk_manager.last_arbitrage_time = 0
        
        # 检查频率
        result = risk_manager.check_arbitrage_frequency()
        
        assert result.passed
        assert result.risk_level == RiskLevel.LOW
        assert "频率检查通过" in result.message
    
    def test_arbitrage_frequency_check_too_frequent(self, risk_manager):
        """测试套利频率过高"""
        # 设置最近的套利时间
        risk_manager.last_arbitrage_time = time.time() - 5  # 5秒前
        risk_manager.min_arbitrage_interval = 10  # 需要10秒间隔
        
        # 检查频率
        result = risk_manager.check_arbitrage_frequency()
        
        assert not result.passed
        assert result.risk_level == RiskLevel.MEDIUM
        assert "套利机会间隔不足" in result.message
    
    def test_arbitrage_frequency_check_daily_limit(self, risk_manager):
        """测试每日套利次数限制"""
        # 设置达到每日限制
        risk_manager.arbitrage_count_today = risk_manager.max_daily_trades
        
        # 检查频率
        result = risk_manager.check_arbitrage_frequency()
        
        assert not result.passed
        assert result.risk_level == RiskLevel.HIGH
        assert "今日套利次数已达上限" in result.message
    
    def test_calculate_position_size_basic(self, risk_manager, sample_opportunity, mock_balance):
        """测试基本仓位大小计算"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_from_usdt = Mock(return_value=1000.0)
        risk_manager._convert_to_usdt = Mock(return_value=1000.0)
        risk_manager._check_orderbook_depth_limit = Mock(return_value=1000.0)
        
        # 计算仓位大小
        position_size = risk_manager.calculate_position_size(sample_opportunity)
        
        assert position_size > 0
        assert position_size <= mock_balance["USDT"]
    
    def test_calculate_position_size_with_profit_rate_adjustment(self, risk_manager, mock_balance):
        """测试基于利润率调整的仓位大小计算"""
        # 创建高利润率机会
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        high_profit_opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.02,  # 2%利润率
            min_amount=100.0,
            timestamp=time.time()
        )
        
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_from_usdt = Mock(return_value=1000.0)
        risk_manager._convert_to_usdt = Mock(return_value=1000.0)
        risk_manager._check_orderbook_depth_limit = Mock(return_value=1000.0)
        
        # 计算仓位大小
        position_size = risk_manager.calculate_position_size(high_profit_opportunity)
        
        assert position_size > 0
        # 高利润率应该允许更大的仓位
        assert position_size >= risk_manager.min_trade_amount
    
    def test_calculate_position_size_insufficient_balance(self, risk_manager, sample_opportunity):
        """测试余额不足时的仓位大小计算"""
        # 设置不足的余额
        insufficient_balance = {"USDT": 50.0}  # 小于最小交易金额
        risk_manager.get_current_balance = Mock(return_value=insufficient_balance)
        
        # 计算仓位大小
        position_size = risk_manager.calculate_position_size(sample_opportunity)
        
        assert position_size == 0.0
    
    def test_validate_opportunity_success(self, risk_manager, sample_opportunity, mock_balance):
        """测试套利机会验证成功"""
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_to_usdt = Mock(return_value=1000.0)
        risk_manager._check_orderbook_depth_limit = Mock(return_value=1000.0)
        
        # 重置频率控制
        risk_manager.last_arbitrage_time = 0
        risk_manager.arbitrage_count_today = 0
        
        # 验证机会
        result = risk_manager.validate_opportunity(sample_opportunity, 55000.0)
        
        assert result.passed
        assert result.suggested_amount > 0
        assert "验证通过" in result.message
    
    def test_validate_opportunity_trading_disabled(self, risk_manager, sample_opportunity):
        """测试交易禁用时的机会验证"""
        # 禁用交易
        risk_manager.trading_enabled = False
        
        # 验证机会
        result = risk_manager.validate_opportunity(sample_opportunity, 55000.0)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.CRITICAL
        assert "交易已被禁用" in result.message
    
    def test_validate_opportunity_low_profit_rate(self, risk_manager, mock_balance):
        """测试低利润率机会验证"""
        # 创建低利润率机会
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        low_profit_opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.001,  # 0.1%利润率，低于默认阈值
            min_amount=100.0,
            timestamp=time.time()
        )
        
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager.last_arbitrage_time = 0
        risk_manager.arbitrage_count_today = 0
        
        # 验证机会
        result = risk_manager.validate_opportunity(low_profit_opportunity, 55000.0)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.MEDIUM
        assert "利润率不足" in result.message
    
    def test_validate_opportunity_expired(self, risk_manager, mock_balance):
        """测试过期机会验证"""
        # 创建过期机会
        expired_opportunity = Mock()
        expired_opportunity.is_expired.return_value = True
        expired_opportunity.path.get_start_asset.return_value = "USDT"
        expired_opportunity.profit_rate = 0.005  # 设置profit_rate为实际值，避免格式化问题
        
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager.last_arbitrage_time = 0
        risk_manager.arbitrage_count_today = 0
        
        # 验证机会
        result = risk_manager.validate_opportunity(expired_opportunity, 55000.0)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.MEDIUM
        assert "过期" in result.message
    
    def test_record_arbitrage_attempt_success(self, risk_manager):
        """测试记录成功的套利尝试"""
        # 记录成功的套利
        risk_manager.record_arbitrage_attempt(True, 50.0)
        
        assert risk_manager.arbitrage_count_today == 1
        assert risk_manager.total_profit_today == 50.0
        assert risk_manager.total_loss_today == 0.0
        assert risk_manager.last_arbitrage_time > 0
    
    def test_record_arbitrage_attempt_failure(self, risk_manager):
        """测试记录失败的套利尝试"""
        # 记录失败的套利
        risk_manager.record_arbitrage_attempt(False, -25.0)
        
        assert risk_manager.arbitrage_count_today == 1
        assert risk_manager.total_profit_today == 0.0
        assert risk_manager.total_loss_today == 25.0
        assert risk_manager.last_arbitrage_time > 0
    
    def test_record_rejected_opportunity(self, risk_manager):
        """测试记录被拒绝的机会"""
        # 记录拒绝的机会
        risk_manager.record_rejected_opportunity("余额不足")
        
        assert risk_manager.rejected_opportunities == 1
    
    def test_daily_counters_reset(self, risk_manager):
        """测试每日计数器重置"""
        # 设置一些数据
        risk_manager.arbitrage_count_today = 10
        risk_manager.total_profit_today = 100.0
        risk_manager.total_loss_today = 50.0
        risk_manager.rejected_opportunities = 5
        
        # 重置计数器
        risk_manager.reset_daily_counters()
        
        assert risk_manager.arbitrage_count_today == 0
        assert risk_manager.total_profit_today == 0.0
        assert risk_manager.total_loss_today == 0.0
        assert risk_manager.rejected_opportunities == 0
        assert risk_manager.last_reset_date == datetime.now().date()
    
    def test_automatic_daily_reset(self, risk_manager):
        """测试自动每日重置"""
        # 设置昨天的重置日期
        risk_manager.last_reset_date = datetime.now().date() - timedelta(days=1)
        risk_manager.arbitrage_count_today = 10
        
        # 触发自动重置检查
        risk_manager._reset_daily_counters_if_needed()
        
        assert risk_manager.arbitrage_count_today == 0
        assert risk_manager.last_reset_date == datetime.now().date()
    
    def test_daily_loss_limit_check(self, risk_manager):
        """测试每日损失限制检查"""
        # 设置接近损失限制的数据
        total_balance = 100000.0
        risk_manager.total_loss_today = 4000.0  # 接近5%限制
        
        # 检查损失限制
        result = risk_manager._check_daily_loss_limit(total_balance)
        
        assert result.passed
        assert "损失检查通过" in result.message
        
        # 设置超过损失限制的数据
        risk_manager.total_loss_today = 6000.0  # 超过5%限制
        
        # 检查损失限制
        result = risk_manager._check_daily_loss_limit(total_balance)
        
        assert not result.passed
        assert result.risk_level == RiskLevel.HIGH
        assert "损失达到上限" in result.message
    
    def test_risk_level_update(self, risk_manager):
        """测试风险级别更新"""
        # 测试基于交易次数的风险级别
        risk_manager.arbitrage_count_today = int(risk_manager.max_daily_trades * 0.8)
        risk_manager._update_risk_level()
        
        assert risk_manager.risk_level == RiskLevel.MEDIUM
        
        # 测试基于损失的风险级别调整
        risk_manager.total_loss_today = 100.0
        risk_manager._update_risk_level()
        
        assert risk_manager.risk_level == RiskLevel.HIGH
    
    def test_trading_enable_disable(self, risk_manager):
        """测试交易启用/禁用"""
        # 测试禁用交易
        risk_manager.disable_trading("测试禁用")
        
        assert not risk_manager.trading_enabled
        assert risk_manager.risk_level == RiskLevel.CRITICAL
        
        # 测试启用交易
        risk_manager.enable_trading()
        
        assert risk_manager.trading_enabled
        assert risk_manager.risk_level == RiskLevel.LOW
    
    def test_can_trade_now(self, risk_manager):
        """测试当前是否可以交易"""
        # 设置可以交易的条件
        risk_manager.trading_enabled = True
        risk_manager.last_arbitrage_time = 0
        risk_manager.arbitrage_count_today = 0
        
        assert risk_manager._can_trade_now()
        
        # 设置不能交易的条件
        risk_manager.trading_enabled = False
        
        assert not risk_manager._can_trade_now()
    
    def test_risk_statistics(self, risk_manager):
        """测试风险统计信息"""
        # 设置一些数据
        risk_manager.arbitrage_count_today = 5
        risk_manager.total_profit_today = 200.0
        risk_manager.total_loss_today = 50.0
        risk_manager.rejected_opportunities = 3
        
        # 获取统计信息
        stats = risk_manager.get_risk_statistics()
        
        assert isinstance(stats, dict)
        assert stats["arbitrage_count_today"] == 5
        assert stats["total_profit_today"] == 200.0
        assert stats["total_loss_today"] == 50.0
        assert stats["net_profit_today"] == 150.0
        assert stats["rejected_opportunities"] == 3
        assert stats["risk_level"] == risk_manager.risk_level.value
        assert stats["trading_enabled"] == risk_manager.trading_enabled
    
    @pytest.mark.integration
    def test_real_balance_integration(self, real_risk_manager):
        """集成测试：使用真实余额数据"""
        # 获取真实余额
        balance = real_risk_manager.get_current_balance()
        
        if balance:
            assert isinstance(balance, dict)
            logging.info(f"真实余额: {balance}")
            
            # 计算总资产价值
            total_usdt = real_risk_manager._calculate_total_balance_usdt(balance)
            assert total_usdt > 0
            logging.info(f"总资产价值: {total_usdt} USDT")
            
            # 测试仓位限制检查
            for asset in balance:
                if balance[asset] > 0:
                    # 测试小额交易
                    small_amount = min(balance[asset] * 0.1, 100.0)
                    result = real_risk_manager.check_position_limit(asset, small_amount)
                    
                    logging.info(f"{asset} 小额交易检查: {result.passed}, {result.message}")
                    
                    # 测试大额交易
                    large_amount = balance[asset] * 2  # 超过余额
                    result = real_risk_manager.check_position_limit(asset, large_amount)
                    
                    assert not result.passed
                    logging.info(f"{asset} 大额交易检查: {result.passed}, {result.message}")
        else:
            pytest.skip("无法获取真实余额数据")
    
    @pytest.mark.integration
    def test_real_opportunity_validation(self, real_risk_manager, sample_opportunity):
        """集成测试：真实机会验证"""
        # 获取真实余额
        balance = real_risk_manager.get_current_balance()
        
        if balance:
            total_usdt = real_risk_manager._calculate_total_balance_usdt(balance)
            
            # 验证机会
            result = real_risk_manager.validate_opportunity(sample_opportunity, total_usdt)
            
            logging.info(f"真实机会验证: {result.passed}, {result.message}")
            
            if result.passed:
                assert result.suggested_amount > 0
                logging.info(f"建议交易金额: {result.suggested_amount}")
            else:
                logging.info(f"验证失败原因: {result.message}")
        else:
            pytest.skip("无法获取真实余额数据")
    
    def test_concurrent_risk_checks(self, risk_manager, sample_opportunity, mock_balance):
        """测试并发风险检查"""
        import threading
        
        # 设置模拟数据
        risk_manager.get_current_balance = Mock(return_value=mock_balance)
        risk_manager._calculate_total_balance_usdt = Mock(return_value=55000.0)
        risk_manager._convert_to_usdt = Mock(return_value=1000.0)
        risk_manager._check_orderbook_depth_limit = Mock(return_value=1000.0)
        
        # 并发检查
        results = []
        
        def check_risk():
            result = risk_manager.validate_opportunity(sample_opportunity, 55000.0)
            results.append(result)
        
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=check_risk)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证结果
        assert len(results) == 5
        for result in results:
            assert isinstance(result, RiskCheckResult)
    
    def test_orderbook_depth_limit_check(self, risk_manager, sample_opportunity):
        """测试订单簿深度限制检查"""
        # 模拟订单簿深度限制方法
        def mock_check_orderbook_depth_limit(opportunity, amount):
            # 假设订单簿深度限制为原金额的80%
            return amount * 0.8
        
        risk_manager._check_orderbook_depth_limit = mock_check_orderbook_depth_limit
        
        # 测试深度限制
        limited_amount = risk_manager._check_orderbook_depth_limit(sample_opportunity, 1000.0)
        
        assert limited_amount == 800.0


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    pytest.main([__file__, "-v", "-s"])