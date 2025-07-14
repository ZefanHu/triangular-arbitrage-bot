"""
套利路径数据模型

定义套利路径和套利机会的核心数据结构
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class ArbitragePath:
    """
    套利路径数据模型
    
    Attributes:
        path: 套利路径，如['USDT', 'USDC', 'BTC', 'USDT']
    """
    path: List[str]  # ['USDT', 'USDC', 'BTC', 'USDT']
    
    def __post_init__(self):
        """数据验证"""
        if len(self.path) < 3:
            raise ValueError("套利路径至少需要3个资产")
        if self.path[0] != self.path[-1]:
            raise ValueError("套利路径必须形成闭环")
    
    def get_trading_pairs(self) -> List[str]:
        """
        获取交易对列表
        
        Returns:
            交易对列表，如['USDC-USDT', 'BTC-USDC', 'USDT-BTC']
        """
        pairs = []
        for i in range(len(self.path) - 1):
            from_asset = self.path[i]
            to_asset = self.path[i + 1]
            
            # 根据资产顺序确定交易对格式
            # 通常基础资产在前，报价资产在后
            if self._is_base_asset(to_asset, from_asset):
                pairs.append(f"{to_asset}-{from_asset}")
            else:
                pairs.append(f"{from_asset}-{to_asset}")
        
        return pairs
    
    def get_trade_directions(self) -> List[str]:
        """
        获取交易方向列表
        
        Returns:
            交易方向列表，如['buy', 'buy', 'sell']
        """
        directions = []
        pairs = self.get_trading_pairs()
        
        for i, pair in enumerate(pairs):
            from_asset = self.path[i]
            to_asset = self.path[i + 1]
            
            # 检查交易对格式来决定买卖方向
            base_asset, quote_asset = pair.split('-')
            
            if from_asset == quote_asset and to_asset == base_asset:
                directions.append('buy')  # 用报价资产买基础资产
            elif from_asset == base_asset and to_asset == quote_asset:
                directions.append('sell')  # 卖基础资产得报价资产
            else:
                # 需要反向交易
                if from_asset == base_asset:
                    directions.append('sell')
                else:
                    directions.append('buy')
        
        return directions
    
    def _is_base_asset(self, asset1: str, asset2: str) -> bool:
        """
        判断哪个资产应该作为基础资产
        
        Args:
            asset1: 资产1
            asset2: 资产2
            
        Returns:
            asset1是否应该作为基础资产
        """
        # 简单的优先级排序：BTC > ETH > 其他币种 > USDT > USDC
        priority = {
            'BTC': 1,
            'ETH': 2,
            'BNB': 3,
            'USDT': 8,
            'USDC': 9
        }
        
        return priority.get(asset1, 5) < priority.get(asset2, 5)
    
    def get_step_count(self) -> int:
        """
        获取套利步数
        
        Returns:
            套利步数
        """
        return len(self.path) - 1
    
    def get_start_asset(self) -> str:
        """
        获取起始资产
        
        Returns:
            起始资产符号
        """
        return self.path[0]
    
    def is_triangular(self) -> bool:
        """
        检查是否为三角套利
        
        Returns:
            是否为三角套利
        """
        return self.get_step_count() == 3
    
    def __str__(self) -> str:
        """字符串表示"""
        return " -> ".join(self.path)


@dataclass
class ArbitrageOpportunity:
    """
    套利机会数据模型
    
    Attributes:
        path: 套利路径
        profit_rate: 利润率
        min_amount: 最小交易金额
    """
    path: ArbitragePath
    profit_rate: float
    min_amount: float
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.profit_rate <= 0:
            raise ValueError("利润率必须为正数")
        if self.min_amount <= 0:
            raise ValueError("最小交易金额必须为正数")
        if self.timestamp is None:
            self.timestamp = datetime.now().timestamp()
    
    def is_profitable(self, threshold: float = 0.001) -> bool:
        """
        检查是否达到盈利阈值
        
        Args:
            threshold: 最小盈利阈值，默认0.1%
            
        Returns:
            是否达到盈利阈值
        """
        return self.profit_rate >= threshold
    
    def get_profit_amount(self, investment: float) -> float:
        """
        计算预期利润金额
        
        Args:
            investment: 投资金额
            
        Returns:
            预期利润金额
        """
        return investment * self.profit_rate
    
    def get_final_amount(self, investment: float) -> float:
        """
        计算最终金额
        
        Args:
            investment: 投资金额
            
        Returns:
            最终金额
        """
        return investment * (1 + self.profit_rate)
    
    def is_amount_sufficient(self, amount: float) -> bool:
        """
        检查金额是否满足最小要求
        
        Args:
            amount: 投资金额
            
        Returns:
            是否满足最小要求
        """
        return amount >= self.min_amount
    
    def get_trading_pairs(self) -> List[str]:
        """
        获取交易对列表
        
        Returns:
            交易对列表
        """
        return self.path.get_trading_pairs()
    
    def get_trade_directions(self) -> List[str]:
        """
        获取交易方向列表
        
        Returns:
            交易方向列表
        """
        return self.path.get_trade_directions()
    
    def is_expired(self, max_age_seconds: float = 5.0) -> bool:
        """
        检查套利机会是否过期
        
        Args:
            max_age_seconds: 最大有效时间，默认5秒
            
        Returns:
            是否过期
        """
        if self.timestamp is None:
            return True
        
        current_time = datetime.now().timestamp()
        return (current_time - self.timestamp) > max_age_seconds
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"ArbitrageOpportunity({self.path}, profit={self.profit_rate:.4f}, min={self.min_amount})"