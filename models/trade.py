"""
交易数据模型

定义交易的核心数据结构和相关方法
"""

from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from models.arbitrage_path import ArbitrageOpportunity


class TradeStatus(Enum):
    """交易状态枚举"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SystemStatus(Enum):
    """系统状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TradeResult:
    """
    交易结果数据模型
    
    Attributes:
        success: 是否成功
        order_id: 订单ID
        filled_size: 成交数量
        avg_price: 平均成交价
        error_message: 错误信息
        timestamp: 执行时间戳
        execution_time: 执行耗时（毫秒）
    """
    success: bool
    order_id: Optional[str] = None
    filled_size: float = 0.0
    avg_price: float = 0.0
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    execution_time: float = 0.0


@dataclass
class ArbitrageRecord:
    """
    套利交易记录
    
    Attributes:
        opportunity: 套利机会
        investment_amount: 投资金额
        expected_profit: 预期利润
        actual_profit: 实际利润
        trade_results: 交易结果列表
        start_time: 开始时间
        end_time: 结束时间
        success: 是否成功
    """
    opportunity: 'ArbitrageOpportunity'  # 套利机会对象
    investment_amount: float
    expected_profit: float
    actual_profit: float = 0.0
    trade_results: List[TradeResult] = field(default_factory=list)
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: Optional[float] = None
    success: bool = False


@dataclass
class RiskCheckResult:
    """
    风险检查结果数据模型
    
    Attributes:
        passed: 是否通过风险检查
        risk_level: 风险级别
        message: 检查结果信息
        suggested_amount: 建议的交易金额
        warnings: 警告信息列表
    """
    passed: bool
    risk_level: RiskLevel
    message: str
    suggested_amount: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class TradingStats:
    """
    交易统计信息
    """
    start_time: float
    total_opportunities: int = 0
    executed_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    last_opportunity_time: float = 0.0
    last_trade_time: float = 0.0
    
    # 新增性能指标
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    
    # 新增API统计
    api_call_count: int = 0
    api_error_count: int = 0
    
    # 新增系统资源统计
    peak_memory_usage: float = 0.0
    peak_cpu_usage: float = 0.0


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