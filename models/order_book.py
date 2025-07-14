"""
订单簿数据模型

定义订单簿的核心数据结构和相关方法
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class OrderBook:
    """
    订单簿数据模型
    
    Attributes:
        symbol: 交易对符号，如'BTC-USDT'
        bids: 买单列表 [[price, size], ...]，按价格降序排列
        asks: 卖单列表 [[price, size], ...]，按价格升序排列
        timestamp: 时间戳
    """
    symbol: str
    bids: List[List[float]]
    asks: List[List[float]]
    timestamp: float
    
    def get_best_bid(self) -> Optional[float]:
        """
        获取最优买价
        
        Returns:
            最优买价，如果没有买单则返回None
        """
        if self.bids:
            return self.bids[0][0]
        return None
    
    def get_best_ask(self) -> Optional[float]:
        """
        获取最优卖价
        
        Returns:
            最优卖价，如果没有卖单则返回None
        """
        if self.asks:
            return self.asks[0][0]
        return None
    
    def get_spread(self) -> Optional[float]:
        """
        获取买卖价差
        
        Returns:
            买卖价差，如果没有买单或卖单则返回None
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is not None and best_ask is not None:
            return best_ask - best_bid
        return None
    
    def get_mid_price(self) -> Optional[float]:
        """
        获取中间价格
        
        Returns:
            中间价格，如果没有买单或卖单则返回None
        """
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2
        return None
    
    def get_depth(self, levels: int = 5) -> dict:
        """
        获取指定档位的订单簿深度
        
        Args:
            levels: 档位数量，默认5档
            
        Returns:
            包含买卖档位的字典
        """
        return {
            'bids': self.bids[:levels],
            'asks': self.asks[:levels]
        }
    
    def is_valid(self) -> bool:
        """
        检查订单簿数据是否有效
        
        Returns:
            数据是否有效
        """
        return bool(self.bids and self.asks and self.symbol and self.timestamp > 0)