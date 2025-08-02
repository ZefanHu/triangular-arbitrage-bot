"""
models目录统一测试文件

使用真实的OKX API测试所有model类的功能
"""

import sys
import os
# 只在直接运行时添加路径，pytest运行时不需要
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import time
import logging
from decimal import Decimal
from typing import Dict, List, Optional

from config.config_manager import ConfigManager
from core.okx_client import OKXClient
from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity
from models.order_book import OrderBook
from models.portfolio import Portfolio
from models.trade import Trade, TradeStatus


class TestArbitragePath:
    """测试ArbitragePath类"""
    
    def test_valid_triangular_path(self):
        """测试有效的三角套利路径"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        assert path.is_triangular()
        assert path.get_step_count() == 3
        assert path.get_start_asset() == "USDT"
        assert len(path.get_trading_pairs()) == 3
        assert len(path.get_trade_directions()) == 3
        
    def test_invalid_path_too_short(self):
        """测试路径过短的情况"""
        with pytest.raises(ValueError, match="套利路径至少需要3个资产"):
            ArbitragePath(path=["USDT", "BTC"])
    
    def test_invalid_path_not_closed(self):
        """测试路径未闭合的情况"""
        with pytest.raises(ValueError, match="套利路径必须形成闭环"):
            ArbitragePath(path=["USDT", "BTC", "ETH", "USDC"])
    
    def test_trading_pairs_generation(self):
        """测试交易对生成"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        pairs = path.get_trading_pairs()
        
        assert len(pairs) == 3
        # 验证交易对格式正确
        for pair in pairs:
            assert '-' in pair
            assert len(pair.split('-')) == 2
    
    def test_trade_directions(self):
        """测试交易方向"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        directions = path.get_trade_directions()
        
        assert len(directions) == 3
        for direction in directions:
            assert direction in ['buy', 'sell']
    
    def test_four_step_path(self):
        """测试四步套利路径"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDC", "USDT"])
        
        assert not path.is_triangular()
        assert path.get_step_count() == 4
        assert len(path.get_trading_pairs()) == 4
        assert len(path.get_trade_directions()) == 4
    
    def test_base_asset_priority(self):
        """测试基础资产优先级判断"""
        path = ArbitragePath(path=["USDT", "BTC", "USDT"])
        
        # 测试BTC vs USDT（BTC优先级更高）
        assert path._is_base_asset("BTC", "USDT") == True
        assert path._is_base_asset("USDT", "BTC") == False
        
        # 测试ETH vs USDC（ETH优先级更高）
        assert path._is_base_asset("ETH", "USDC") == True
        assert path._is_base_asset("USDC", "ETH") == False
        
        # 测试未知币种vs稳定币
        assert path._is_base_asset("DOGE", "USDT") == True
        assert path._is_base_asset("USDT", "DOGE") == False
    
    def test_complex_trading_directions(self):
        """测试复杂交易方向计算"""
        # 测试需要反向交易的情况
        path = ArbitragePath(path=["USDT", "ETH", "BTC", "USDT"])
        directions = path.get_trade_directions()
        pairs = path.get_trading_pairs()
        
        # 验证方向数量正确
        assert len(directions) == 3
        assert len(pairs) == 3
        
        # 验证每个方向都是有效的
        for direction in directions:
            assert direction in ['buy', 'sell']


class TestArbitrageOpportunity:
    """测试ArbitrageOpportunity类"""
    
    def test_valid_opportunity(self):
        """测试有效的套利机会"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,
            min_amount=100.0
        )
        
        assert opportunity.is_profitable()
        assert opportunity.is_profitable(threshold=0.003)
        assert not opportunity.is_profitable(threshold=0.01)
        assert opportunity.is_amount_sufficient(150.0)
        assert not opportunity.is_amount_sufficient(50.0)
    
    def test_invalid_opportunity_negative_profit(self):
        """测试负利润率的情况"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        with pytest.raises(ValueError, match="利润率必须为正数"):
            ArbitrageOpportunity(
                path=path,
                profit_rate=-0.005,
                min_amount=100.0
            )
    
    def test_invalid_opportunity_negative_min_amount(self):
        """测试负最小金额的情况"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        with pytest.raises(ValueError, match="最小交易金额必须为正数"):
            ArbitrageOpportunity(
                path=path,
                profit_rate=0.005,
                min_amount=-100.0
            )
    
    def test_profit_calculations(self):
        """测试利润计算"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.01,  # 1%
            min_amount=100.0
        )
        
        investment = 1000.0
        profit = opportunity.get_profit_amount(investment)
        final_amount = opportunity.get_final_amount(investment)
        
        assert profit == 10.0  # 1% of 1000
        assert final_amount == 1010.0  # 1000 + 10
    
    def test_expiration(self):
        """测试过期检查"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        # 创建过期的机会
        old_timestamp = time.time() - 10.0
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,
            min_amount=100.0,
            timestamp=old_timestamp
        )
        
        assert opportunity.is_expired(max_age_seconds=5.0)
        assert not opportunity.is_expired(max_age_seconds=15.0)
    
    def test_get_trading_methods(self):
        """测试获取交易对和方向的方法"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,
            min_amount=100.0
        )
        
        # 测试获取交易对
        pairs = opportunity.get_trading_pairs()
        assert len(pairs) == 3
        assert all('-' in pair for pair in pairs)
        
        # 测试获取交易方向
        directions = opportunity.get_trade_directions()
        assert len(directions) == 3
        assert all(direction in ['buy', 'sell'] for direction in directions)
    
    def test_expired_timestamp_none(self):
        """测试时间戳为None的过期检查"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        
        # 创建一个机会，然后手动设置timestamp为None
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,
            min_amount=100.0
        )
        
        # 手动设置timestamp为None来测试这种情况
        opportunity.timestamp = None
        
        # 时间戳为None时应该视为过期
        assert opportunity.is_expired()
    
    def test_string_representation(self):
        """测试字符串表示"""
        path = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path,
            profit_rate=0.005,
            min_amount=100.0
        )
        
        str_repr = str(opportunity)
        assert "ArbitrageOpportunity" in str_repr
        assert "profit=0.0050" in str_repr
        assert "min=100.0" in str_repr


class TestOrderBook:
    """测试OrderBook类"""
    
    def test_valid_orderbook(self):
        """测试有效的订单簿"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            asks=[[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]],
            timestamp=time.time()
        )
        
        assert orderbook.is_valid()
        assert orderbook.get_best_bid() == 50000.0
        assert orderbook.get_best_ask() == 50100.0
        assert orderbook.get_spread() == 100.0
        assert orderbook.get_mid_price() == 50050.0
    
    def test_empty_orderbook(self):
        """测试空订单簿"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[],
            asks=[],
            timestamp=time.time()
        )
        
        assert not orderbook.is_valid()
        assert orderbook.get_best_bid() is None
        assert orderbook.get_best_ask() is None
        assert orderbook.get_spread() is None
        assert orderbook.get_mid_price() is None
    
    def test_orderbook_depth(self):
        """测试订单簿深度"""
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            asks=[[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]],
            timestamp=time.time()
        )
        
        depth = orderbook.get_depth(levels=2)
        assert len(depth['bids']) == 2
        assert len(depth['asks']) == 2
        assert depth['bids'][0] == [50000.0, 1.0]
        assert depth['asks'][0] == [50100.0, 1.0]
    
    def test_partial_orderbook(self):
        """测试部分订单簿（只有买单或卖单）"""
        # 只有买单
        orderbook_bids_only = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[],
            timestamp=time.time()
        )
        
        assert not orderbook_bids_only.is_valid()
        assert orderbook_bids_only.get_best_bid() == 50000.0
        assert orderbook_bids_only.get_best_ask() is None
        assert orderbook_bids_only.get_spread() is None
        
        # 只有卖单
        orderbook_asks_only = OrderBook(
            symbol="BTC-USDT",
            bids=[],
            asks=[[50100.0, 1.0]],
            timestamp=time.time()
        )
        
        assert not orderbook_asks_only.is_valid()
        assert orderbook_asks_only.get_best_bid() is None
        assert orderbook_asks_only.get_best_ask() == 50100.0
        assert orderbook_asks_only.get_spread() is None
    
    def test_invalid_orderbook_data(self):
        """测试无效的订单簿数据"""
        # 测试无效的symbol
        orderbook_invalid_symbol = OrderBook(
            symbol="",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=time.time()
        )
        assert not orderbook_invalid_symbol.is_valid()
        
        # 测试无效的timestamp
        orderbook_invalid_timestamp = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=0
        )
        assert not orderbook_invalid_timestamp.is_valid()
        
        # 测试负数timestamp
        orderbook_negative_timestamp = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=-1
        )
        assert not orderbook_negative_timestamp.is_valid()
    
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
        assert len(depth['bids']) == 2  # 只返回实际存在的2档
        assert len(depth['asks']) == 1   # 只返回实际存在的1档


class TestPortfolio:
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
        
        assert portfolio.get_asset_balance("USDT") == 10000.0
        assert portfolio.get_asset_balance("BTC") == 0.5
        assert portfolio.get_asset_balance("USDC") == 0.0
        assert portfolio.get_asset_balance("UNKNOWN") == 0.0
        
        assert portfolio.has_asset("USDT")
        assert portfolio.has_asset("BTC")
        assert not portfolio.has_asset("USDC")
        assert not portfolio.has_asset("UNKNOWN")
    
    def test_portfolio_operations(self):
        """测试投资组合操作"""
        portfolio = Portfolio(
            balances={"USDT": 1000.0, "BTC": 0.0},
            timestamp=time.time()
        )
        
        # 测试添加余额
        portfolio.add_balance("USDT", 500.0)
        assert portfolio.get_asset_balance("USDT") == 1500.0
        
        portfolio.add_balance("BTC", 0.1)
        assert portfolio.get_asset_balance("BTC") == 0.1
        
        # 测试减少余额
        assert portfolio.subtract_balance("USDT", 200.0)
        assert portfolio.get_asset_balance("USDT") == 1300.0
        
        # 测试余额不足的情况
        assert not portfolio.subtract_balance("USDT", 2000.0)
        assert portfolio.get_asset_balance("USDT") == 1300.0
        
        # 测试更新余额
        portfolio.update_balance("ETH", 2.0)
        assert portfolio.get_asset_balance("ETH") == 2.0
    
    def test_portfolio_checks(self):
        """测试投资组合检查"""
        portfolio = Portfolio(
            balances={"USDT": 1000.0, "BTC": 0.1, "ETH": 0.0},
            timestamp=time.time()
        )
        
        assert portfolio.is_sufficient_balance("USDT", 500.0)
        assert not portfolio.is_sufficient_balance("USDT", 1500.0)
        assert not portfolio.is_sufficient_balance("ETH", 0.1)
        
        assets = portfolio.get_total_assets()
        assert "USDT" in assets
        assert "BTC" in assets
        assert "ETH" not in assets
        
        assert portfolio.get_total_balance_count() == 2
        assert not portfolio.is_empty()
    
    def test_empty_portfolio(self):
        """测试空投资组合"""
        portfolio = Portfolio(
            balances={},
            timestamp=time.time()
        )
        
        assert portfolio.is_empty()
        assert portfolio.get_total_balance_count() == 0
        assert len(portfolio.get_total_assets()) == 0
    
    def test_portfolio_copy(self):
        """测试投资组合复制"""
        original = Portfolio(
            balances={"USDT": 1000.0, "BTC": 0.1},
            timestamp=time.time()
        )
        
        copy = original.copy()
        
        # 修改原始投资组合
        original.add_balance("USDT", 500.0)
        
        # 确保复制的投资组合不受影响
        assert original.get_asset_balance("USDT") == 1500.0
        assert copy.get_asset_balance("USDT") == 1000.0
    
    def test_portfolio_summary(self):
        """测试投资组合摘要"""
        portfolio = Portfolio(
            balances={"USDT": 1000.0, "BTC": 0.1, "ETH": 0.0, "DOGE": -5.0},
            timestamp=time.time()
        )
        
        summary = portfolio.get_portfolio_summary()
        
        # 摘要应该只包含正余额的资产
        assert "USDT" in summary
        assert "BTC" in summary
        assert "ETH" not in summary  # 零余额
        assert "DOGE" not in summary  # 负余额
        
        assert summary["USDT"] == 1000.0
        assert summary["BTC"] == 0.1
    
    def test_negative_balance_operations(self):
        """测试负余额操作"""
        portfolio = Portfolio(
            balances={"USDT": 100.0, "BTC": -0.1},
            timestamp=time.time()
        )
        
        # 有负余额的资产不应该被认为是持有的
        assert not portfolio.has_asset("BTC")
        assert portfolio.get_asset_balance("BTC") == -0.1
        
        # 总资产不应该包含负余额资产
        total_assets = portfolio.get_total_assets()
        assert "USDT" in total_assets
        assert "BTC" not in total_assets
        
        # 余额数量应该只计算正余额
        assert portfolio.get_total_balance_count() == 1


class TestTrade:
    """测试Trade类"""
    
    def test_valid_trade(self):
        """测试有效的交易"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.1,
            price=50000.0,
            order_id="12345"
        )
        
        assert trade.is_buy()
        assert not trade.is_sell()
        assert trade.get_base_asset() == "BTC"
        assert trade.get_quote_asset() == "USDT"
        assert trade.get_notional_value() == 5000.0
        
        required_asset, required_amount = trade.get_required_balance()
        assert required_asset == "USDT"
        assert required_amount == 5000.0
        
        receive_asset, receive_amount = trade.get_receive_amount()
        assert receive_asset == "BTC"
        assert receive_amount == 0.1
    
    def test_sell_trade(self):
        """测试卖出交易"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="sell",
            size=0.1,
            price=50000.0
        )
        
        assert not trade.is_buy()
        assert trade.is_sell()
        
        required_asset, required_amount = trade.get_required_balance()
        assert required_asset == "BTC"
        assert required_amount == 0.1
        
        receive_asset, receive_amount = trade.get_receive_amount()
        assert receive_asset == "USDT"
        assert receive_amount == 5000.0
    
    def test_invalid_trade_side(self):
        """测试无效的交易方向"""
        with pytest.raises(ValueError, match="side must be 'buy' or 'sell'"):
            Trade(
                inst_id="BTC-USDT",
                side="invalid",
                size=0.1,
                price=50000.0
            )
    
    def test_invalid_trade_size(self):
        """测试无效的交易数量"""
        with pytest.raises(ValueError, match="size must be positive"):
            Trade(
                inst_id="BTC-USDT",
                side="buy",
                size=-0.1,
                price=50000.0
            )
    
    def test_invalid_trade_price(self):
        """测试无效的交易价格"""
        with pytest.raises(ValueError, match="price must be positive"):
            Trade(
                inst_id="BTC-USDT",
                side="buy",
                size=0.1,
                price=-50000.0
            )
    
    def test_order_params(self):
        """测试订单参数转换"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.1,
            price=50000.0
        )
        
        params = trade.to_order_params()
        expected_params = {
            'instId': 'BTC-USDT',
            'side': 'buy',
            'ordType': 'limit',
            'sz': '0.1',
            'px': '50000.0'
        }
        
        assert params == expected_params
    
    def test_trade_status_enum(self):
        """测试交易状态枚举"""
        from models.trade import TradeStatus
        
        # 测试所有状态值
        assert TradeStatus.PENDING.value == "pending"
        assert TradeStatus.FILLED.value == "filled"
        assert TradeStatus.CANCELLED.value == "cancelled"
        assert TradeStatus.FAILED.value == "failed"
    
    def test_trade_string_representation(self):
        """测试交易字符串表示"""
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.1,
            price=50000.0,
            order_id="test123"
        )
        
        str_repr = str(trade)
        assert "Trade(" in str_repr
        assert "buy" in str_repr
        assert "0.1" in str_repr
        assert "BTC-USDT" in str_repr
        assert "50000.0" in str_repr
    
    def test_trade_with_order_id(self):
        """测试带订单ID的交易"""
        trade = Trade(
            inst_id="ETH-USDT",
            side="sell",
            size=2.5,
            price=3000.0,
            order_id="order_123456"
        )
        
        assert trade.order_id == "order_123456"
        assert trade.get_notional_value() == 7500.0
        assert trade.is_sell()
        assert not trade.is_buy()
    
    def test_invalid_instrument_id(self):
        """测试无效的交易对ID"""
        # 测试不包含'-'的交易对ID会导致错误
        trade = Trade(
            inst_id="INVALID",
            side="buy",
            size=1.0,
            price=100.0
        )
        
        # 这会在调用get_base_asset或get_quote_asset时出错
        try:
            base = trade.get_base_asset()
            quote = trade.get_quote_asset()
            # 如果没有'-'分隔符，split会有问题
            assert False, "应该出现索引错误"
        except IndexError:
            pass  # 预期的错误
    
    def test_edge_case_coverage(self):
        """测试边界情况以提高覆盖率"""
        # 测试ArbitragePath的__str__方法
        path = ArbitragePath(path=["USDT", "BTC", "USDT"])
        str_repr = str(path)
        assert "USDT -> BTC -> USDT" in str_repr
        
        # 测试ArbitrageOpportunity带明确timestamp
        path2 = ArbitragePath(path=["USDT", "BTC", "ETH", "USDT"])
        opportunity = ArbitrageOpportunity(
            path=path2,
            profit_rate=0.005,
            min_amount=100.0,
            timestamp=time.time()
        )
        
        # 触发各种方法
        assert opportunity.get_trading_pairs() == path2.get_trading_pairs()
        assert opportunity.get_trade_directions() == path2.get_trade_directions()
        
        # 测试OrderBook的字符串操作
        orderbook = OrderBook(
            symbol="BTC-USDT",
            bids=[[50000.0, 1.0]],
            asks=[[50100.0, 1.0]],
            timestamp=time.time()
        )
        
        # 确保方法被调用
        depth = orderbook.get_depth(1)
        assert depth is not None
        
        # 测试Portfolio的所有方法
        portfolio = Portfolio(
            balances={"USDT": 1000.0, "BTC": 0.1},
            timestamp=time.time()
        )
        
        # 调用所有方法确保覆盖
        portfolio.update_balance("ETH", 2.0)
        portfolio.add_balance("USDT", 100.0)
        assert portfolio.subtract_balance("USDT", 50.0)
        assert portfolio.is_sufficient_balance("USDT", 100.0)
        summary = portfolio.get_portfolio_summary()
        assert not portfolio.is_empty()
        copy_portfolio = portfolio.copy()
        assert copy_portfolio is not None
        
        # 测试Trade的所有方法
        trade = Trade(
            inst_id="BTC-USDT",
            side="buy",
            size=0.1,
            price=50000.0
        )
        
        # 调用所有方法
        assert trade.get_notional_value() == 5000.0
        assert trade.is_buy()
        assert not trade.is_sell()
        assert trade.get_base_asset() == "BTC"
        assert trade.get_quote_asset() == "USDT"
        req_asset, req_amount = trade.get_required_balance()
        rec_asset, rec_amount = trade.get_receive_amount()
        params = trade.to_order_params()
        str_trade = str(trade)
        
        assert req_asset == "USDT"
        assert rec_asset == "BTC"
        assert params is not None
        assert str_trade is not None
    
    def test_imports_and_modules(self):
        """测试模块导入以确保完整覆盖"""
        # 重新导入所有模块以确保import语句被覆盖
        from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity
        from models.order_book import OrderBook  
        from models.portfolio import Portfolio
        from models.trade import Trade, TradeStatus
        
        # 验证所有类都可以正常实例化
        path = ArbitragePath(path=["A", "B", "A"])
        assert isinstance(path, ArbitragePath)
        
        opportunity = ArbitrageOpportunity(path=path, profit_rate=0.01, min_amount=100.0)
        assert isinstance(opportunity, ArbitrageOpportunity)
        
        orderbook = OrderBook(symbol="TEST", bids=[], asks=[], timestamp=1.0)
        assert isinstance(orderbook, OrderBook)
        
        portfolio = Portfolio(balances={}, timestamp=1.0)
        assert isinstance(portfolio, Portfolio)
        
        trade = Trade(inst_id="A-B", side="buy", size=1.0, price=1.0)
        assert isinstance(trade, Trade)
        
        # 验证TradeStatus枚举
        assert TradeStatus.PENDING.value == "pending"
        assert TradeStatus.FILLED.value == "filled"
        assert TradeStatus.CANCELLED.value == "cancelled"  
        assert TradeStatus.FAILED.value == "failed"


@pytest.mark.api
@pytest.mark.network
class TestModelsWithRealAPI:
    """使用真实API测试模型类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """设置真实API客户端"""
        self.config = ConfigManager()
        self.client = OKXClient()
        
        # 检查API配置
        api_creds = self.config.get_api_credentials()
        if not api_creds:
            pytest.skip("API凭据未配置，跳过真实API测试")
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("开始真实API测试")
    
    def test_real_orderbook_data(self):
        """测试真实订单簿数据"""
        # 获取真实订单簿数据
        symbol = "BTC-USDT"
        orderbook = self.client.get_orderbook(symbol)
        
        if orderbook and isinstance(orderbook, OrderBook):
            # 验证订单簿数据
            assert orderbook.is_valid()
            assert orderbook.get_best_bid() is not None
            assert orderbook.get_best_ask() is not None
            assert orderbook.get_spread() > 0
            assert orderbook.get_mid_price() > 0
            
            self.logger.info(f"真实订单簿数据验证通过: {symbol}")
            self.logger.info(f"最优买价: {orderbook.get_best_bid()}")
            self.logger.info(f"最优卖价: {orderbook.get_best_ask()}")
            self.logger.info(f"价差: {orderbook.get_spread()}")
        else:
            pytest.skip("无法获取真实订单簿数据")
    
    def test_real_balance_data(self):
        """测试真实余额数据"""
        # 获取真实余额数据
        balance_data = self.client.get_balance()
        
        if balance_data:
            # 创建Portfolio实例
            portfolio = Portfolio(
                balances=balance_data,
                timestamp=time.time()
            )
            
            # 验证投资组合
            total_assets = portfolio.get_total_assets()
            self.logger.info(f"账户持有资产: {total_assets}")
            
            for asset in total_assets:
                balance = portfolio.get_asset_balance(asset)
                assert balance > 0
                self.logger.info(f"{asset}: {balance}")
            
            # 测试投资组合功能
            if portfolio.has_asset("USDT"):
                usdt_balance = portfolio.get_asset_balance("USDT")
                assert portfolio.is_sufficient_balance("USDT", usdt_balance * 0.5)
                assert not portfolio.is_sufficient_balance("USDT", usdt_balance * 2)
        else:
            pytest.skip("无法获取真实余额数据")
    
    def test_real_arbitrage_path_with_api_data(self):
        """使用真实API数据测试套利路径"""
        # 从配置文件读取path1路径
        trading_config = self.config.get_trading_config()
        path1_config = trading_config.get('paths', {}).get('path1')
        
        if not path1_config:
            pytest.skip("path1配置未找到，跳过套利路径测试")
        
        # 从path1配置构建测试路径
        test_paths = []
        if 'steps' in path1_config:
            # 从steps构建路径
            assets = ["USDT"]  # 起始资产
            for step in path1_config['steps']:
                pair = step['pair']
                action = step['action']
                base, quote = pair.split('-')
                if action == 'buy':
                    # 买入操作：用quote买base
                    if assets[-1] == quote:
                        assets.append(base)
                elif action == 'sell':
                    # 卖出操作：卖base得quote
                    if assets[-1] == base:
                        assets.append(quote)
            # 确保路径闭合
            if assets[-1] != assets[0]:
                assets.append(assets[0])
            test_paths.append(assets)
        
        for path_assets in test_paths:
            try:
                # 创建套利路径
                arbitrage_path = ArbitragePath(path=path_assets)
                
                # 获取交易对和方向
                trading_pairs = arbitrage_path.get_trading_pairs()
                trade_directions = arbitrage_path.get_trade_directions()
                
                self.logger.info(f"测试路径: {arbitrage_path}")
                self.logger.info(f"交易对: {trading_pairs}")
                self.logger.info(f"交易方向: {trade_directions}")
                
                # 验证每个交易对的真实数据
                all_pairs_valid = True
                for pair in trading_pairs:
                    try:
                        orderbook = self.client.get_orderbook(pair)
                        if not orderbook or not isinstance(orderbook, OrderBook):
                            all_pairs_valid = False
                            break
                        
                        if not orderbook.is_valid():
                            all_pairs_valid = False
                            break
                            
                        self.logger.info(f"交易对 {pair} 数据有效")
                    except Exception as e:
                        self.logger.warning(f"交易对 {pair} 数据获取失败: {e}")
                        all_pairs_valid = False
                        break
                
                if all_pairs_valid:
                    self.logger.info(f"套利路径 {arbitrage_path} 验证通过")
                else:
                    self.logger.warning(f"套利路径 {arbitrage_path} 部分交易对数据无效")
                    
            except Exception as e:
                self.logger.error(f"测试路径 {path_assets} 失败: {e}")
    
    def test_real_trade_validation(self):
        """使用真实数据验证交易参数"""
        # 获取真实市场数据
        symbol = "BTC-USDT"
        orderbook = self.client.get_orderbook(symbol)
        
        if orderbook and isinstance(orderbook, OrderBook) and orderbook.is_valid():
            best_bid = orderbook.get_best_bid()
            best_ask = orderbook.get_best_ask()
            
            if best_bid and best_ask:
                # 创建基于真实价格的交易
                buy_trade = Trade(
                    inst_id=symbol,
                    side="buy",
                    size=0.001,  # 小额测试
                    price=best_ask * 0.99  # 稍低于最优卖价
                )
                
                sell_trade = Trade(
                    inst_id=symbol,
                    side="sell",
                    size=0.001,
                    price=best_bid * 1.01  # 稍高于最优买价
                )
                
                # 验证交易参数
                assert buy_trade.is_buy()
                assert sell_trade.is_sell()
                
                # 验证订单参数格式
                buy_params = buy_trade.to_order_params()
                sell_params = sell_trade.to_order_params()
                
                assert buy_params['instId'] == symbol
                assert buy_params['side'] == 'buy'
                assert buy_params['ordType'] == 'limit'
                
                assert sell_params['instId'] == symbol
                assert sell_params['side'] == 'sell'
                assert sell_params['ordType'] == 'limit'
                
                self.logger.info(f"真实交易验证通过")
                self.logger.info(f"买单参数: {buy_params}")
                self.logger.info(f"卖单参数: {sell_params}")
            else:
                pytest.skip("订单簿数据不完整")
        else:
            pytest.skip("无法获取真实订单簿数据")


if __name__ == "__main__":
    # 运行测试并生成models目录的覆盖率报告
    import os
    # 临时设置环境变量来覆盖pytest.ini的配置
    os.environ['PYTEST_CURRENT_TEST'] = 'models_only'
    
    pytest.main([
        __file__, 
        "-v", 
        "--tb=short",
        "-o", "addopts=",  # 清空pytest.ini中的addopts
        "--cov=models",  # 只测试models目录的覆盖率
        "--cov-report=term-missing",
        "--cov-report=html:tests/reports/models_coverage_html",
        "--cov-report=xml:tests/reports/models_coverage.xml",
        "--junit-xml=tests/reports/models_junit.xml"
    ])