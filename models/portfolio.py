"""
投资组合数据模型

定义投资组合的核心数据结构和相关方法
"""

from dataclasses import dataclass
from typing import Dict, Optional, List


@dataclass
class Portfolio:
    """
    投资组合数据模型
    
    Attributes:
        balances: 资产余额字典 {asset: balance}
        timestamp: 时间戳
    """
    balances: Dict[str, float]
    timestamp: float
    
    def get_asset_balance(self, asset: str) -> float:
        """
        获取指定资产的余额
        
        Args:
            asset: 资产符号，如'BTC', 'USDT'
            
        Returns:
            资产余额，如果不存在则返回0.0
        """
        return self.balances.get(asset, 0.0)
    
    def has_asset(self, asset: str) -> bool:
        """
        检查是否持有指定资产
        
        Args:
            asset: 资产符号
            
        Returns:
            是否持有该资产
        """
        return asset in self.balances and self.balances[asset] > 0
    
    def get_total_assets(self) -> List[str]:
        """
        获取所有持有的资产列表
        
        Returns:
            资产符号列表
        """
        return [asset for asset, balance in self.balances.items() if balance > 0]
    
    def get_total_balance_count(self) -> int:
        """
        获取持有资产的数量
        
        Returns:
            资产数量
        """
        return len(self.get_total_assets())
    
    def update_balance(self, asset: str, balance: float) -> None:
        """
        更新资产余额
        
        Args:
            asset: 资产符号
            balance: 新的余额
        """
        self.balances[asset] = balance
    
    def add_balance(self, asset: str, amount: float) -> None:
        """
        增加资产余额
        
        Args:
            asset: 资产符号
            amount: 增加的数量
        """
        current_balance = self.get_asset_balance(asset)
        self.balances[asset] = current_balance + amount
    
    def subtract_balance(self, asset: str, amount: float) -> bool:
        """
        减少资产余额
        
        Args:
            asset: 资产符号
            amount: 减少的数量
            
        Returns:
            是否成功减少（余额是否足够）
        """
        current_balance = self.get_asset_balance(asset)
        if current_balance >= amount:
            self.balances[asset] = current_balance - amount
            return True
        return False
    
    def is_sufficient_balance(self, asset: str, required_amount: float) -> bool:
        """
        检查资产余额是否足够
        
        Args:
            asset: 资产符号
            required_amount: 需要的数量
            
        Returns:
            余额是否足够
        """
        return self.get_asset_balance(asset) >= required_amount
    
    def get_portfolio_summary(self) -> Dict[str, float]:
        """
        获取投资组合摘要
        
        Returns:
            包含所有非零余额的字典
        """
        return {asset: balance for asset, balance in self.balances.items() if balance > 0}
    
    def is_empty(self) -> bool:
        """
        检查投资组合是否为空
        
        Returns:
            是否为空
        """
        return not any(balance > 0 for balance in self.balances.values())
    
    def copy(self) -> 'Portfolio':
        """
        创建投资组合的副本
        
        Returns:
            新的Portfolio实例
        """
        return Portfolio(
            balances=self.balances.copy(),
            timestamp=self.timestamp
        )