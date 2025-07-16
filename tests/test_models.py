"""
models目录统一测试文件

使用真实的OKX API测试所有model类的功能
"""

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
        # 定义测试路径
        test_paths = [
            ["USDT", "BTC", "ETH", "USDT"],
            ["USDT", "BTC", "USDC", "USDT"],
            ["USDT", "ETH", "BTC", "USDT"]
        ]
        
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
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])