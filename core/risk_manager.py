"""
风险管理模块

负责管理交易风险，包括仓位限制、频率控制、资金管理等
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from config.config_manager import ConfigManager
from models.arbitrage_path import ArbitrageOpportunity


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class RiskManager:
    """
    风险管理器
    
    负责管理交易风险，包括仓位限制、频率控制、资金管理等
    """
    
    def __init__(self, config_manager: ConfigManager, okx_client=None):
        """
        初始化风险管理器
        
        Args:
            config_manager: 配置管理器实例
            okx_client: OKX客户端实例（可选）
        """
        self.config_manager = config_manager
        self.okx_client = okx_client
        self.logger = logging.getLogger(__name__)
        
        # 加载风险配置
        self.risk_config = self.config_manager.get_risk_config()
        self.trading_config = self.config_manager.get_trading_config()
        
        # 风险参数
        self.max_position_ratio = self.risk_config.get('max_position_ratio', 0.2)
        self.max_single_trade_ratio = self.risk_config.get('max_single_trade_ratio', 0.1)
        self.min_arbitrage_interval = self.risk_config.get('min_arbitrage_interval', 10)
        self.max_daily_trades = self.risk_config.get('max_daily_trades', 100)
        self.max_daily_loss_ratio = self.risk_config.get('max_daily_loss_ratio', 0.05)
        self.stop_loss_ratio = self.risk_config.get('stop_loss_ratio', 0.1)
        
        # 交易参数
        self.min_trade_amount = self.trading_config.get('parameters', {}).get('min_trade_amount', 100.0)
        
        # 套利频率跟踪（只控制套利机会之间的间隔）
        self.last_arbitrage_time = 0
        self.arbitrage_count_today = 0
        self.last_reset_date = datetime.now().date()
        
        # 风险统计
        self.total_profit_today = 0.0
        self.total_loss_today = 0.0
        self.rejected_opportunities = 0
        
        # 风险状态
        self.risk_level = RiskLevel.LOW
        self.trading_enabled = True
        
        # 余额缓存（每60秒刷新一次）
        self.balance_cache = {}
        self.balance_cache_time = 0
        self.balance_cache_ttl = 60.0
        
        self.logger.info("风险管理器初始化完成")
        self.logger.info(f"风险参数: 最大仓位比例={self.max_position_ratio}, 最大单笔交易比例={self.max_single_trade_ratio}, 最小套利间隔={self.min_arbitrage_interval}秒")
    
    def check_position_limit(self, asset: str, amount: float) -> RiskCheckResult:
        """
        检查仓位限制
        
        Args:
            asset: 资产类型（如'USDT'）
            amount: 请求的交易数量
            
        Returns:
            风险检查结果
        """
        self.logger.debug(f"检查仓位限制: {asset} {amount}")
        
        try:
            # 获取当前余额
            current_balance = self.get_current_balance()
            if not current_balance:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message=f"无法获取当前余额",
                    suggested_amount=0
                )
            
            # 计算总资产价值（以USDT计价）
            total_balance_usdt = self._calculate_total_balance_usdt(current_balance)
            
            # 获取当前资产余额
            current_asset_balance = current_balance.get(asset, 0)
            
            # 检查资产余额是否足够
            if current_asset_balance < amount:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"{asset}余额不足: 需要{amount}, 可用{current_asset_balance}",
                    suggested_amount=current_asset_balance
                )
            
            # 计算交易后的仓位比例（以USDT计价）
            amount_usdt = self._convert_to_usdt(asset, amount)
            position_ratio = amount_usdt / total_balance_usdt if total_balance_usdt > 0 else 0
            
            warnings = []
            
            # 检查单笔交易限制
            if position_ratio > self.max_single_trade_ratio:
                max_amount_usdt = total_balance_usdt * self.max_single_trade_ratio
                suggested_amount = self._convert_from_usdt(asset, max_amount_usdt)
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"单笔交易金额超限: {position_ratio:.2%} > {self.max_single_trade_ratio:.2%}",
                    suggested_amount=suggested_amount,
                    warnings=warnings
                )
            
            # 检查最大仓位限制
            if position_ratio > self.max_position_ratio:
                max_amount_usdt = total_balance_usdt * self.max_position_ratio
                suggested_amount = self._convert_from_usdt(asset, max_amount_usdt)
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"仓位比例超限: {position_ratio:.2%} > {self.max_position_ratio:.2%}",
                    suggested_amount=suggested_amount,
                    warnings=warnings
                )
            
            # 生成警告
            if position_ratio > self.max_single_trade_ratio * 0.8:
                warnings.append(f"仓位比例接近单笔交易限制: {position_ratio:.2%}")
            
            # 确定风险级别
            if position_ratio > self.max_single_trade_ratio * 0.8:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            return RiskCheckResult(
                passed=True,
                risk_level=risk_level,
                message=f"仓位检查通过: {asset} {amount} ({position_ratio:.2%})",
                suggested_amount=amount,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"检查仓位限制异常: {e}")
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"仓位检查异常: {str(e)}",
                suggested_amount=0
            )
    
    def check_arbitrage_frequency(self) -> RiskCheckResult:
        """
        检查套利频率限制
        
        注意：这里只控制两次套利机会之间的间隔，不影响单次套利内部的三笔交易
        
        Returns:
            风险检查结果
        """
        self.logger.debug("检查套利频率限制")
        
        try:
            current_time = time.time()
            
            # 检查是否需要重置每日计数
            self._reset_daily_counters_if_needed()
            
            # 检查两次套利机会之间的最小间隔
            time_since_last = current_time - self.last_arbitrage_time
            if self.last_arbitrage_time > 0 and time_since_last < self.min_arbitrage_interval:
                remaining_time = self.min_arbitrage_interval - time_since_last
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"套利机会间隔不足: 需等待{remaining_time:.1f}秒（上次套利于{time_since_last:.1f}秒前）",
                    suggested_amount=0
                )
            
            # 检查每日套利次数限制
            if self.arbitrage_count_today >= self.max_daily_trades:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"今日套利次数已达上限: {self.arbitrage_count_today}/{self.max_daily_trades}",
                    suggested_amount=0
                )
            
            warnings = []
            
            # 生成警告
            if self.arbitrage_count_today > self.max_daily_trades * 0.8:
                warnings.append(f"今日套利次数接近上限: {self.arbitrage_count_today}/{self.max_daily_trades}")
            
            # 确定风险级别
            if self.arbitrage_count_today > self.max_daily_trades * 0.8:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            return RiskCheckResult(
                passed=True,
                risk_level=risk_level,
                message=f"频率检查通过: 今日套利次数{self.arbitrage_count_today}/{self.max_daily_trades}",
                suggested_amount=0,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"检查套利频率异常: {e}")
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"频率检查异常: {str(e)}",
                suggested_amount=0
            )
    
    def calculate_position_size(self, opportunity: ArbitrageOpportunity, balance: Dict[str, float] = None) -> float:
        """
        计算合适的交易量
        
        Args:
            opportunity: 套利机会
            balance: 当前余额（可选）
            
        Returns:
            建议的交易金额（以起始资产计价）
        """
        self.logger.debug(f"计算交易量: 利润率={opportunity.profit_rate:.4%}")
        
        try:
            # 获取当前余额
            if balance is None:
                balance = self.get_current_balance()
                if not balance:
                    self.logger.error("无法获取余额信息")
                    return 0.0
            
            # 计算总资产价值（以USDT计价）
            total_balance_usdt = self._calculate_total_balance_usdt(balance)
            if total_balance_usdt <= 0:
                self.logger.error("总资产为零或负数")
                return 0.0
            
            # 获取起始资产
            start_asset = opportunity.path.get_start_asset()
            available_balance = balance.get(start_asset, 0)
            
            if available_balance <= 0:
                self.logger.warning(f"{start_asset}余额为零")
                return 0.0
            
            # 基于风险配置计算基础交易量
            max_single_trade_usdt = total_balance_usdt * self.max_single_trade_ratio
            base_amount = self._convert_from_usdt(start_asset, max_single_trade_usdt)
            
            # 根据利润率调整交易量（高利润率可以使用更大的交易量）
            profit_multiplier = min(opportunity.profit_rate / 0.005, 1.5)  # 最大1.5倍，基于0.5%利润率
            adjusted_amount = base_amount * profit_multiplier
            
            # 确保不超过最大仓位限制
            max_position_usdt = total_balance_usdt * self.max_position_ratio
            max_allowed = self._convert_from_usdt(start_asset, max_position_usdt)
            final_amount = min(adjusted_amount, max_allowed)
            
            # 确保不超过可用余额
            final_amount = min(final_amount, available_balance)
            
            # 确保满足最小交易金额要求
            if final_amount < self.min_trade_amount:
                # 如果计算的金额太小，检查是否有足够的余额满足最小要求
                if available_balance >= self.min_trade_amount:
                    final_amount = self.min_trade_amount
                else:
                    self.logger.warning(f"{start_asset}余额{available_balance}不足以满足最小交易金额{self.min_trade_amount}")
                    return 0.0
            
            # 确保满足套利机会的最小金额要求
            final_amount = max(final_amount, opportunity.min_amount)
            
            # 检查订单簿深度限制
            depth_limited_amount = self._check_orderbook_depth_limit(opportunity, final_amount)
            if depth_limited_amount < final_amount:
                self.logger.warning(f"根据订单簿深度调整交易量: {final_amount:.2f} -> {depth_limited_amount:.2f}")
                final_amount = depth_limited_amount
            
            self.logger.debug(f"计算结果: 基础金额={base_amount:.2f}, 调整后={adjusted_amount:.2f}, 最终金额={final_amount:.2f}")
            
            return final_amount
            
        except Exception as e:
            self.logger.error(f"计算交易量异常: {e}")
            return 0.0
    
    def validate_opportunity(self, opportunity: ArbitrageOpportunity, 
                           total_balance: float, requested_amount: float = None) -> RiskCheckResult:
        """
        验证套利机会是否符合风险要求
        
        Args:
            opportunity: 套利机会
            total_balance: 总资产
            requested_amount: 请求的交易金额（可选）
            
        Returns:
            风险检查结果
        """
        self.logger.info(f"验证套利机会: {opportunity.path}, 利润率={opportunity.profit_rate:.4%}")
        
        try:
            # 检查交易是否被禁用
            if not self.trading_enabled:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.CRITICAL,
                    message="交易已被禁用",
                    suggested_amount=0
                )
            
            # 检查套利频率
            frequency_result = self.check_arbitrage_frequency()
            if not frequency_result.passed:
                return frequency_result
            
            # 计算建议的交易金额
            if requested_amount is None:
                requested_amount = self.calculate_position_size(opportunity)
            
            # 检查仓位限制
            start_asset = opportunity.path.get_start_asset()
            position_result = self.check_position_limit(start_asset, requested_amount)
            if not position_result.passed:
                return position_result
            
            # 检查利润率是否满足最小要求
            min_profit_threshold = self.trading_config.get('parameters', {}).get('min_profit_threshold', 0.003)
            if opportunity.profit_rate < min_profit_threshold:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    message=f"利润率不足: {opportunity.profit_rate:.4%} < {min_profit_threshold:.4%}",
                    suggested_amount=requested_amount
                )
            
            # 检查套利机会是否过期
            if opportunity.is_expired():
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.MEDIUM,
                    message="套利机会已过期",
                    suggested_amount=requested_amount
                )
            
            # 检查今日损失限制
            daily_loss_check = self._check_daily_loss_limit(total_balance)
            if not daily_loss_check.passed:
                return daily_loss_check
            
            # 合并所有警告
            all_warnings = frequency_result.warnings + position_result.warnings
            
            # 确定最终风险级别
            final_risk_level = max(frequency_result.risk_level, position_result.risk_level, key=lambda x: x.value)
            
            return RiskCheckResult(
                passed=True,
                risk_level=final_risk_level,
                message=f"套利机会验证通过: 利润率={opportunity.profit_rate:.4%}, 建议金额={requested_amount:.2f}",
                suggested_amount=requested_amount,
                warnings=all_warnings
            )
            
        except Exception as e:
            self.logger.error(f"验证套利机会异常: {e}")
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"验证套利机会异常: {str(e)}",
                suggested_amount=0
            )
    
    def record_arbitrage_attempt(self, success: bool, profit: float = 0.0):
        """
        记录套利尝试
        
        Args:
            success: 是否成功
            profit: 利润金额（负数表示亏损）
        """
        try:
            current_time = time.time()
            
            # 更新最后套利时间
            self.last_arbitrage_time = current_time
            
            # 更新今日交易次数
            self.arbitrage_count_today += 1
            
            # 更新利润统计
            if profit > 0:
                self.total_profit_today += profit
            else:
                self.total_loss_today += abs(profit)
            
            # 记录日志
            if success:
                self.logger.info(f"套利成功记录: 利润={profit:.6f}, 今日交易次数={self.arbitrage_count_today}")
            else:
                self.logger.warning(f"套利失败记录: 亏损={profit:.6f}, 今日交易次数={self.arbitrage_count_today}")
            
            # 更新风险级别
            self._update_risk_level()
            
        except Exception as e:
            self.logger.error(f"记录套利尝试异常: {e}")
    
    def record_rejected_opportunity(self, reason: str):
        """
        记录被拒绝的套利机会
        
        Args:
            reason: 拒绝原因
        """
        try:
            self.rejected_opportunities += 1
            self.logger.info(f"拒绝套利机会: {reason}, 今日拒绝次数={self.rejected_opportunities}")
            
        except Exception as e:
            self.logger.error(f"记录拒绝机会异常: {e}")
    
    def get_risk_statistics(self) -> Dict[str, any]:
        """
        获取风险统计信息
        
        Returns:
            风险统计数据
        """
        try:
            return {
                'risk_level': self.risk_level.value,
                'trading_enabled': self.trading_enabled,
                'arbitrage_count_today': self.arbitrage_count_today,
                'max_daily_trades': self.max_daily_trades,
                'total_profit_today': self.total_profit_today,
                'total_loss_today': self.total_loss_today,
                'net_profit_today': self.total_profit_today - self.total_loss_today,
                'rejected_opportunities': self.rejected_opportunities,
                'last_arbitrage_time': self.last_arbitrage_time,
                'time_since_last_arbitrage': time.time() - self.last_arbitrage_time if self.last_arbitrage_time > 0 else 0,
                'can_trade_now': self._can_trade_now(),
                'risk_limits': {
                    'max_position_ratio': self.max_position_ratio,
                    'max_single_trade_ratio': self.max_single_trade_ratio,
                    'min_arbitrage_interval': self.min_arbitrage_interval,
                    'max_daily_trades': self.max_daily_trades,
                    'max_daily_loss_ratio': self.max_daily_loss_ratio,
                    'stop_loss_ratio': self.stop_loss_ratio
                }
            }
            
        except Exception as e:
            self.logger.error(f"获取风险统计异常: {e}")
            return {}
    
    def reset_daily_counters(self):
        """重置每日计数器"""
        try:
            self.arbitrage_count_today = 0
            self.total_profit_today = 0.0
            self.total_loss_today = 0.0
            self.rejected_opportunities = 0
            self.last_reset_date = datetime.now().date()
            
            self.logger.info("每日计数器已重置")
            
        except Exception as e:
            self.logger.error(f"重置每日计数器异常: {e}")
    
    def _reset_daily_counters_if_needed(self):
        """如果需要则重置每日计数器"""
        try:
            current_date = datetime.now().date()
            if current_date > self.last_reset_date:
                self.reset_daily_counters()
                
        except Exception as e:
            self.logger.error(f"检查每日计数器重置异常: {e}")
    
    def _check_daily_loss_limit(self, total_balance: float) -> RiskCheckResult:
        """检查每日损失限制"""
        try:
            max_daily_loss = total_balance * self.max_daily_loss_ratio
            
            if self.total_loss_today >= max_daily_loss:
                return RiskCheckResult(
                    passed=False,
                    risk_level=RiskLevel.HIGH,
                    message=f"今日损失达到上限: {self.total_loss_today:.2f} >= {max_daily_loss:.2f}",
                    suggested_amount=0
                )
            
            return RiskCheckResult(
                passed=True,
                risk_level=RiskLevel.LOW,
                message="每日损失检查通过",
                suggested_amount=0
            )
            
        except Exception as e:
            self.logger.error(f"检查每日损失限制异常: {e}")
            return RiskCheckResult(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                message=f"每日损失检查异常: {str(e)}",
                suggested_amount=0
            )
    
    def _update_risk_level(self):
        """更新风险级别"""
        try:
            # 基于今日交易次数确定风险级别
            if self.arbitrage_count_today >= self.max_daily_trades * 0.9:
                self.risk_level = RiskLevel.HIGH
            elif self.arbitrage_count_today >= self.max_daily_trades * 0.7:
                self.risk_level = RiskLevel.MEDIUM
            else:
                self.risk_level = RiskLevel.LOW
            
            # 基于损失情况调整风险级别
            if self.total_loss_today > 0:
                if self.risk_level == RiskLevel.LOW:
                    self.risk_level = RiskLevel.MEDIUM
                elif self.risk_level == RiskLevel.MEDIUM:
                    self.risk_level = RiskLevel.HIGH
            
        except Exception as e:
            self.logger.error(f"更新风险级别异常: {e}")
    
    def _can_trade_now(self) -> bool:
        """检查当前是否可以交易"""
        try:
            current_time = time.time()
            time_since_last = current_time - self.last_arbitrage_time
            
            return (
                self.trading_enabled and
                time_since_last >= self.min_arbitrage_interval and
                self.arbitrage_count_today < self.max_daily_trades
            )
            
        except Exception as e:
            self.logger.error(f"检查交易状态异常: {e}")
            return False
    
    def disable_trading(self, reason: str):
        """禁用交易"""
        try:
            self.trading_enabled = False
            self.risk_level = RiskLevel.CRITICAL
            self.logger.warning(f"交易已禁用: {reason}")
            
        except Exception as e:
            self.logger.error(f"禁用交易异常: {e}")
    
    def enable_trading(self):
        """启用交易"""
        try:
            self.trading_enabled = True
            self.risk_level = RiskLevel.LOW
            self.logger.info("交易已启用")
            
        except Exception as e:
            self.logger.error(f"启用交易异常: {e}")
    
    def get_current_balance(self) -> Dict[str, float]:
        """获取当前余额"""
        try:
            current_time = time.time()
            
            # 检查缓存是否有效
            if (self.balance_cache and 
                current_time - self.balance_cache_time < self.balance_cache_ttl):
                return self.balance_cache
            
            # 从OKX客户端获取余额
            if self.okx_client:
                balance = self.okx_client.get_balance()
                if balance:
                    self.balance_cache = balance
                    self.balance_cache_time = current_time
                    return balance
            
            # 如果无法获取，返回缓存的余额
            return self.balance_cache or {}
            
        except Exception as e:
            self.logger.error(f"获取当前余额异常: {e}")
            return self.balance_cache or {}
    
    def _convert_to_usdt(self, asset: str, amount: float) -> float:
        """转换为USDT价值"""
        try:
            if asset == "USDT":
                return amount
            elif asset == "BTC":
                return amount * 50000.0  # 假设BTC价格
            elif asset == "ETH":
                return amount * 3000.0   # 假设ETH价格
            elif asset == "BNB":
                return amount * 500.0    # 假设BNB价格
            elif asset == "USDC":
                return amount * 1.0      # USDC约等于USDT
            else:
                return amount * 100.0    # 其他资产默认价格
        except Exception as e:
            self.logger.error(f"转换为USDT异常: {e}")
            return 0.0
    
    def _convert_from_usdt(self, asset: str, usdt_amount: float) -> float:
        """从USDT价值转换为资产数量"""
        try:
            if asset == "USDT":
                return usdt_amount
            elif asset == "BTC":
                return usdt_amount / 50000.0
            elif asset == "ETH":
                return usdt_amount / 3000.0
            elif asset == "BNB":
                return usdt_amount / 500.0
            elif asset == "USDC":
                return usdt_amount / 1.0
            else:
                return usdt_amount / 100.0
        except Exception as e:
            self.logger.error(f"从USDT转换异常: {e}")
            return 0.0
    
    def _check_orderbook_depth_limit(self, opportunity, amount: float) -> float:
        """检查订单簿深度限制"""
        try:
            # 简化实现，返回原金额的80%作为深度限制
            return amount * 0.8
        except Exception as e:
            self.logger.error(f"检查订单簿深度限制异常: {e}")
            return amount
    
    def _calculate_total_balance_usdt(self, balance: Dict[str, float]) -> float:
        """计算总资产价值（以USDT计价）"""
        try:
            total_usdt = 0.0
            for asset, amount in balance.items():
                if amount > 0:
                    usdt_value = self._convert_to_usdt(asset, amount)
                    total_usdt += usdt_value
            return total_usdt
        except Exception as e:
            self.logger.error(f"计算总资产价值异常: {e}")
            return 0.0