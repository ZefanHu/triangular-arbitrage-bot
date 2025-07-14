"""
交易数据模型

定义交易的核心数据结构和相关方法
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TradeStatus(Enum):
    """交易状态枚举"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Trade:
    """
    交易数据模型
    
    Attributes:
        inst_id: 交易对ID，如'BTC-USDT'
        side: 交易方向 'buy' 或 'sell'
        size: 交易数量
        price: 交易价格
        order_id: 订单ID，可选
    """
    inst_id: str
    side: str  # 'buy' or 'sell'
    size: float
    price: float
    order_id: Optional[str] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.side not in ['buy', 'sell']:
            raise ValueError("side must be 'buy' or 'sell'")
        if self.size <= 0:
            raise ValueError("size must be positive")
        if self.price <= 0:
            raise ValueError("price must be positive")
    
    def get_notional_value(self) -> float:
        """
        获取交易的名义价值
        
        Returns:
            名义价值 (数量 * 价格)
        """
        return self.size * self.price
    
    def is_buy(self) -> bool:
        """
        检查是否为买单
        
        Returns:
            是否为买单
        """
        return self.side == 'buy'
    
    def is_sell(self) -> bool:
        """
        检查是否为卖单
        
        Returns:
            是否为卖单
        """
        return self.side == 'sell'
    
    def get_base_asset(self) -> str:
        """
        获取基础资产
        
        Returns:
            基础资产符号
        """
        return self.inst_id.split('-')[0]
    
    def get_quote_asset(self) -> str:
        """
        获取报价资产
        
        Returns:
            报价资产符号
        """
        return self.inst_id.split('-')[1]
    
    def get_required_balance(self) -> tuple[str, float]:
        """
        获取执行交易所需的资产和数量
        
        Returns:
            (资产符号, 需要数量)
        """
        if self.is_buy():
            # 买入需要报价资产
            return self.get_quote_asset(), self.get_notional_value()
        else:
            # 卖出需要基础资产
            return self.get_base_asset(), self.size
    
    def get_receive_amount(self) -> tuple[str, float]:
        """
        获取交易完成后收到的资产和数量
        
        Returns:
            (资产符号, 收到数量)
        """
        if self.is_buy():
            # 买入收到基础资产
            return self.get_base_asset(), self.size
        else:
            # 卖出收到报价资产
            return self.get_quote_asset(), self.get_notional_value()
    
    def to_order_params(self) -> dict:
        """
        转换为订单参数字典
        
        Returns:
            订单参数字典
        """
        return {
            'instId': self.inst_id,
            'side': self.side,
            'ordType': 'limit',
            'sz': str(self.size),
            'px': str(self.price)
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Trade({self.side} {self.size} {self.inst_id} @ {self.price})"