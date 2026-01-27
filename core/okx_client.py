from typing import Dict, Any, Optional, List, Union
from utils.logger import setup_logger
import json
import okex.Account_api as Account
import okex.Market_api as Market
import okex.Trade_api as Trade
from config.config_manager import ConfigManager
from models.order_book import OrderBook


class OKXClient:
    """
    OKX交易所REST API客户端
    
    负责与OKX交易所进行通信，提供账户信息查询、市场数据获取、订单管理等功能。
    """
    
    def __init__(self):
        """初始化OKX客户端"""
        self.logger = setup_logger(__name__)
        self.config_manager = ConfigManager()
        
        # 获取API凭据
        credentials = self.config_manager.get_api_credentials()
        self.public_only = False
        if not credentials:
            self.public_only = True
            self.api_key = ""
            self.secret_key = ""
            self.passphrase = ""
            self.flag = self.config_manager.get('api', 'flag', '1')
            self.logger.warning("API凭据缺失，OKX客户端进入只读模式：账户与交易接口已禁用")
        else:
            self.api_key = credentials['api_key']
            self.secret_key = credentials['secret_key']
            self.passphrase = credentials['passphrase']
            self.flag = credentials['flag']  # '1'为模拟盘，'0'为实盘
        
        # 初始化各个API对象
        self.account_api = None
        self.trade_api = None
        if not self.public_only:
            self.account_api = Account.AccountAPI(
                self.api_key, 
                self.secret_key, 
                self.passphrase, 
                False, 
                self.flag
            )
        
        self.market_api = Market.MarketAPI(
            self.api_key, 
            self.secret_key, 
            self.passphrase, 
            False, 
            self.flag
        )
        
        if not self.public_only:
            self.trade_api = Trade.TradeAPI(
                self.api_key, 
                self.secret_key, 
                self.passphrase, 
                False, 
                self.flag
            )
        
        self.logger.info(f"OKX客户端初始化完成，使用{'模拟盘' if self.flag == '1' else '实盘'}")
    
    def get_balance(self) -> Optional[Dict[str, float]]:
        """
        获取账户余额信息
        
        Returns:
            格式化的余额信息 {'USDT': 1000.0, 'USDC': 500.0, 'BTC': 0.01}
            失败返回None
        """
        try:
            if self.public_only or not self.account_api:
                self.logger.warning("只读模式下无法获取账户余额")
                return None
            result = self.account_api.get_account()
            self.logger.debug("获取账户余额成功")
            
            if not result or 'data' not in result:
                self.logger.warning("账户余额数据为空")
                return None
                
            # 解析余额数据
            balance_data = {}
            for account in result['data']:
                if 'details' in account:
                    for detail in account['details']:
                        currency = detail.get('ccy', '').upper()
                        available = float(detail.get('availBal', 0))
                        if currency and available > 0:
                            balance_data[currency] = available
            
            # 确保包含主要币种
            for currency in ['USDT', 'USDC', 'BTC']:
                if currency not in balance_data:
                    balance_data[currency] = 0.0
            
            self.logger.info(f"解析账户余额: {balance_data}")
            return balance_data
            
        except Exception as e:
            self.logger.error(f"获取账户余额失败: {e}")
            return None
    
    def get_orderbook(self, inst_id: str, size: str = "20") -> Optional[OrderBook]:
        """
        获取产品深度数据
        
        Args:
            inst_id: 产品ID，如BTC-USDT
            size: 深度档位数量，默认20
            
        Returns:
            OrderBook实例，失败返回None
        """
        try:
            result = self.market_api.get_orderbook(inst_id, size)
            self.logger.debug(f"获取{inst_id}订单簿成功")
            
            if not result or 'data' not in result or not result['data']:
                self.logger.warning(f"{inst_id}订单簿数据为空")
                return None
            
            orderbook_data = result['data'][0]
            
            # 转换数据格式为OrderBook对象
            bids = [[float(bid[0]), float(bid[1])] for bid in orderbook_data.get('bids', [])]
            asks = [[float(ask[0]), float(ask[1])] for ask in orderbook_data.get('asks', [])]
            
            # 转换时间戳为float（OKX返回的是毫秒时间戳字符串）
            timestamp_str = orderbook_data.get('ts', '0')
            timestamp = float(timestamp_str) / 1000.0  # 转换为秒
            
            # 创建OrderBook对象
            orderbook = OrderBook(
                symbol=inst_id,
                bids=bids,
                asks=asks,
                timestamp=timestamp
            )
            
            self.logger.debug(f"{inst_id}订单簿: {len(bids)}个买单, {len(asks)}个卖单")
            return orderbook
            
        except Exception as e:
            self.logger.error(f"获取{inst_id}订单簿失败: {e}")
            return None
    
    def place_order(self, inst_id: str, side: str, order_type: str, 
                   size: str, price: str = None) -> Optional[str]:
        """
        下单
        
        Args:
            inst_id: 产品ID，如BTC-USDT
            side: 订单方向，buy或sell
            order_type: 订单类型，limit(限价)或market(市价)
            size: 委托数量
            price: 委托价格，市价单可不传
            
        Returns:
            订单ID，失败返回None
        """
        try:
            if self.public_only or not self.trade_api:
                self.logger.warning("只读模式下禁止下单")
                return None
            # 现货交易使用cash模式
            result = self.trade_api.place_order(
                instId=inst_id,
                tdMode='cash',
                side=side,
                ordType=order_type,
                sz=size,
                px=price
            )
            
            if result and 'data' in result and result['data']:
                order_id = result['data'][0].get('ordId', '')
                self.logger.info(f"下单成功: {inst_id} {side} {size} @ {price or 'market'}, 订单ID: {order_id}")
                return order_id
            else:
                self.logger.warning(f"下单返回数据异常: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"下单失败: {e}")
            return None
    
    def cancel_order(self, inst_id: str, order_id: str) -> bool:
        """
        撤单
        
        Args:
            inst_id: 产品ID，如BTC-USDT
            order_id: 订单ID
            
        Returns:
            撤单是否成功
        """
        try:
            if self.public_only or not self.trade_api:
                self.logger.warning("只读模式下禁止撤单")
                return False
            result = self.trade_api.cancel_order(inst_id, order_id)
            
            if result and 'data' in result and result['data']:
                self.logger.info(f"撤单成功: {inst_id} {order_id}")
                return True
            else:
                self.logger.warning(f"撤单返回数据异常: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"撤单失败: {e}")
            return False
    
    def get_ticker(self, inst_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个产品行情信息
        
        Args:
            inst_id: 产品ID，如BTC-USDT
            
        Returns:
            行情数据，失败返回None
        """
        try:
            result = self.market_api.get_ticker(inst_id)
            self.logger.debug(f"获取{inst_id}行情成功")
            
            if not result or 'data' not in result or not result['data']:
                self.logger.warning(f"{inst_id}行情数据为空")
                return None
            
            ticker_data = result['data'][0]
            
            # 格式化行情数据
            formatted_data = {
                'symbol': ticker_data.get('instId', ''),
                'last_price': float(ticker_data.get('last', 0)),
                'best_bid': float(ticker_data.get('bidPx', 0)),
                'best_ask': float(ticker_data.get('askPx', 0)),
                'bid_size': float(ticker_data.get('bidSz', 0)),
                'ask_size': float(ticker_data.get('askSz', 0)),
                'volume_24h': float(ticker_data.get('vol24h', 0)),
                'open_24h': float(ticker_data.get('open24h', 0)),
                'high_24h': float(ticker_data.get('high24h', 0)),
                'low_24h': float(ticker_data.get('low24h', 0)),
                'change_24h': float(ticker_data.get('chg24h', 0)),
                'timestamp': ticker_data.get('ts', '')
            }
            
            self.logger.debug(f"{inst_id}行情: 最新价{formatted_data['last_price']}, 买一{formatted_data['best_bid']}, 卖一{formatted_data['best_ask']}")
            return formatted_data
            
        except Exception as e:
            self.logger.error(f"获取{inst_id}行情失败: {e}")
            return None
    
    def get_order_status(self, inst_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取订单状态
        
        Args:
            inst_id: 产品ID，如BTC-USDT
            order_id: 订单ID
            
        Returns:
            订单状态信息，失败返回None
        """
        try:
            if self.public_only or not self.trade_api:
                self.logger.warning("只读模式下无法获取订单状态")
                return None
            result = self.trade_api.get_orders(inst_id, order_id)
            self.logger.debug(f"获取{inst_id}订单{order_id}状态成功")
            
            if not result or 'data' not in result or not result['data']:
                self.logger.warning(f"订单{order_id}状态数据为空")
                return None
            
            order_data = result['data'][0]
            
            # 格式化订单状态数据
            formatted_data = {
                'order_id': order_data.get('ordId', ''),
                'symbol': order_data.get('instId', ''),
                'side': order_data.get('side', ''),
                'order_type': order_data.get('ordType', ''),
                'size': float(order_data.get('sz', 0)),
                'price': float(order_data.get('px', 0)) if order_data.get('px') else None,
                'filled_size': float(order_data.get('fillSz', 0)),
                'avg_price': float(order_data.get('avgPx', 0)) if order_data.get('avgPx') else None,
                'state': order_data.get('state', ''),
                'created_time': order_data.get('cTime', ''),
                'updated_time': order_data.get('uTime', ''),
                'fee': float(order_data.get('fee', 0)),
                'fee_currency': order_data.get('feeCcy', '')
            }
            
            self.logger.debug(f"订单{order_id}状态: {formatted_data['state']}, 成交量: {formatted_data['filled_size']}/{formatted_data['size']}")
            return formatted_data
            
        except Exception as e:
            self.logger.error(f"获取订单{order_id}状态失败: {e}")
            return None
