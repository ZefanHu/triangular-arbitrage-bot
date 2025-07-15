"""
交易控制器模块

负责整合所有模块，提供统一的交易控制接口
"""

import asyncio
import logging
import time
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.trade_executor import TradeExecutor
from core.risk_manager import RiskManager
from config.config_manager import ConfigManager


class TradingStatus(Enum):
    """交易状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


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


class TradingController:
    """
    交易控制器
    
    负责整合所有模块，提供统一的交易控制接口
    """
    
    def __init__(self, config_manager: ConfigManager = None):
        """
        初始化交易控制器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.logger = logging.getLogger(__name__)
        
        # 配置管理
        self.config_manager = config_manager or ConfigManager()
        
        # 核心模块
        self.data_collector = DataCollector()
        self.arbitrage_engine = ArbitrageEngine(self.data_collector)
        self.trade_executor = TradeExecutor(self.data_collector.rest_client)
        self.risk_manager = RiskManager(self.config_manager, self.data_collector.rest_client)
        
        # 交易状态
        self.status = TradingStatus.STOPPED
        self.is_running = False
        self.trading_loop_task = None
        
        # 交易控制
        self.trading_interval = self.config_manager.get_trading_config().get('parameters', {}).get('monitor_interval', 1.0)
        self.max_concurrent_trades = 1  # 限制并发交易数量
        self.current_trades = 0
        
        # 交易统计
        self.stats = TradingStats(start_time=time.time())
        self.stats_lock = threading.Lock()
        
        # 事件回调
        self.opportunity_callbacks: List[Callable] = []
        self.trade_result_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # 获取交易对配置
        self.trading_pairs = self._get_trading_pairs()
        
        self.logger.info("交易控制器初始化完成")
    
    async def start(self) -> bool:
        """
        启动交易系统
        
        Returns:
            启动是否成功
        """
        if self.is_running:
            self.logger.warning("交易系统已在运行")
            return True
        
        try:
            self.logger.info("正在启动交易系统...")
            self.status = TradingStatus.STARTING
            
            # 启动数据采集器
            self.logger.info("启动数据采集器...")
            if not await self.data_collector.start(self.trading_pairs):
                self.logger.error("数据采集器启动失败")
                self.status = TradingStatus.ERROR
                return False
            
            # 等待数据采集器稳定
            await asyncio.sleep(2)
            
            # 注意：不再使用回调模式，直接在交易循环中获取套利机会
            # 这样可以更好地控制交易流程和时机
            
            # 套利引擎不需要启动监控，直接在交易循环中调用find_opportunities()
            self.logger.info("套利引擎已就绪，使用同步模式")
            
            # 启动主交易循环
            self.logger.info("启动主交易循环...")
            self.is_running = True
            self.trading_loop_task = asyncio.create_task(self._trading_loop())
            
            # 重置统计信息
            with self.stats_lock:
                self.stats = TradingStats(start_time=time.time())
            
            self.status = TradingStatus.RUNNING
            self.logger.info("交易系统启动成功")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动交易系统失败: {e}")
            self.status = TradingStatus.ERROR
            await self._cleanup()
            return False
    
    async def stop(self) -> bool:
        """
        停止交易系统
        
        Returns:
            停止是否成功
        """
        if not self.is_running:
            self.logger.warning("交易系统未在运行")
            return True
        
        try:
            self.logger.info("正在停止交易系统...")
            self.status = TradingStatus.STOPPING
            
            # 停止主交易循环
            self.is_running = False
            if self.trading_loop_task:
                self.logger.info("正在停止主交易循环...")
                await self._ensure_graceful_shutdown()
                self.trading_loop_task = None
            
            # 等待当前交易完成
            timeout = 30  # 30秒超时
            start_time = time.time()
            while self.current_trades > 0 and time.time() - start_time < timeout:
                self.logger.info(f"等待 {self.current_trades} 个交易完成...")
                await asyncio.sleep(1)
            
            if self.current_trades > 0:
                self.logger.warning(f"超时，仍有 {self.current_trades} 个交易未完成")
            
            # 套利引擎不需要停止监控，因为我们使用同步模式
            self.logger.info("套利引擎已停止")
            
            # 停止数据采集器
            self.logger.info("停止数据采集器...")
            await self.data_collector.stop()
            
            # 清理资源
            await self._cleanup()
            
            self.status = TradingStatus.STOPPED
            self.logger.info("交易系统已停止")
            
            # 输出最终统计
            self._log_final_stats()
            
            return True
            
        except Exception as e:
            self.logger.error(f"停止交易系统失败: {e}")
            self.status = TradingStatus.ERROR
            return False
    
    async def _trading_loop(self):
        """
        主交易循环
        
        完整的交易循环逻辑：
        1. 获取套利机会
        2. 按path1→path2顺序处理
        3. 风险检查（包括频率限制）
        4. 执行套利（三笔交易连续执行）
        5. 记录结果
        6. 等待下一轮监控
        """
        self.logger.info("主交易循环开始")
        loop_count = 0
        last_stats_log = time.time()
        stats_log_interval = 300  # 每5分钟输出一次统计
        
        while self.is_running:
            try:
                loop_count += 1
                self.logger.debug(f"开始第 {loop_count} 轮交易循环")
                
                # 定期输出统计信息
                current_time = time.time()
                if current_time - last_stats_log >= stats_log_interval:
                    self._log_periodic_stats()
                    last_stats_log = current_time
                
                # 1. 获取套利机会
                opportunities = self.arbitrage_engine.find_opportunities()
                
                if opportunities:
                    self.logger.info(f"发现 {len(opportunities)} 个套利机会")
                    
                    # 更新统计
                    with self.stats_lock:
                        self.stats.total_opportunities += len(opportunities)
                        self.stats.last_opportunity_time = time.time()
                    
                    # 2. 按path1→path2顺序处理
                    for opp in opportunities:
                        if not self.is_running:
                            self.logger.info("系统停止运行，退出交易循环")
                            break
                        
                        # 检查并发交易限制
                        if self.current_trades >= self.max_concurrent_trades:
                            self.logger.info(f"达到最大并发交易数量限制: {self.max_concurrent_trades}")
                            break
                        
                        # 处理单个套利机会
                        await self._process_opportunity_in_loop(opp)
                
                else:
                    self.logger.debug("未发现套利机会")
                
                # 检查系统状态
                await self._check_system_health()
                
                # 6. 等待下一轮监控
                await asyncio.sleep(self.trading_interval)
                
            except asyncio.CancelledError:
                self.logger.info("交易循环被取消")
                break
            except Exception as e:
                self.logger.error(f"交易循环异常: {e}")
                self._notify_error(f"交易循环异常: {e}")
                await asyncio.sleep(5)  # 异常后等待5秒再继续
        
        self.logger.info("主交易循环结束")
    
    async def _ensure_graceful_shutdown(self):
        """
        确保优雅关闭交易循环
        """
        try:
            # 给交易循环一个机会自然结束
            if self.trading_loop_task and not self.trading_loop_task.done():
                self.logger.info("等待交易循环自然结束...")
                try:
                    await asyncio.wait_for(self.trading_loop_task, timeout=5.0)
                except asyncio.TimeoutError:
                    self.logger.warning("交易循环未在5秒内结束，强制取消")
                    self.trading_loop_task.cancel()
                    try:
                        await self.trading_loop_task
                    except asyncio.CancelledError:
                        pass
                except asyncio.CancelledError:
                    pass
            
            self.logger.info("交易循环已优雅关闭")
            
        except Exception as e:
            self.logger.error(f"优雅关闭交易循环异常: {e}")
    
    def _log_periodic_stats(self):
        """
        定期输出统计信息
        """
        try:
            with self.stats_lock:
                runtime = time.time() - self.stats.start_time
                
                self.logger.info("=== 交易系统定期统计 ===")
                self.logger.info(f"运行时间: {runtime/60:.1f}分钟")
                self.logger.info(f"发现机会: {self.stats.total_opportunities}个")
                self.logger.info(f"执行交易: {self.stats.executed_trades}个")
                self.logger.info(f"成功交易: {self.stats.successful_trades}个")
                self.logger.info(f"失败交易: {self.stats.failed_trades}个")
                self.logger.info(f"当前并发交易: {self.current_trades}个")
                
                if self.stats.executed_trades > 0:
                    success_rate = self.stats.successful_trades / self.stats.executed_trades
                    self.logger.info(f"成功率: {success_rate:.2%}")
                
                self.logger.info(f"净利润: {self.stats.net_profit:.6f}")
                
                # 风险管理统计
                risk_stats = self.risk_manager.get_risk_statistics()
                self.logger.info(f"风险级别: {risk_stats['risk_level']}")
                self.logger.info(f"拒绝机会: {risk_stats['rejected_opportunities']}个")
                
                if runtime > 0:
                    opp_rate = self.stats.total_opportunities / runtime * 3600
                    trade_rate = self.stats.executed_trades / runtime * 3600
                    self.logger.info(f"机会发现率: {opp_rate:.1f}个/小时")
                    self.logger.info(f"交易执行率: {trade_rate:.1f}个/小时")
                
        except Exception as e:
            self.logger.error(f"输出定期统计异常: {e}")
    
    async def _process_opportunity_in_loop(self, opportunity: Dict):
        """
        在交易循环中处理单个套利机会
        
        Args:
            opportunity: 套利机会
        """
        try:
            path_name = opportunity['path_name']
            profit_rate = opportunity['profit_rate']
            
            self.logger.info(f"=== 处理套利机会: {path_name}, 利润率: {profit_rate:.4%} ===")
            
            # 通知套利机会回调
            self._notify_opportunity(opportunity)
            
            # 增加当前交易计数
            self.current_trades += 1
            
            try:
                # 获取当前余额
                portfolio = self.data_collector.get_balance()
                if not portfolio:
                    self.logger.error("无法获取账户余额")
                    return
                
                balance = portfolio.balances
                total_balance_usdt = sum(balance.values())  # 简化计算
                
                # 创建ArbitrageOpportunity对象
                from models.arbitrage_path import ArbitrageOpportunity
                arb_opportunity = ArbitrageOpportunity(
                    path=opportunity['path'],
                    profit_rate=opportunity['profit_rate'],
                    min_amount=opportunity['min_trade_amount'],
                    max_amount=opportunity['max_trade_amount'],
                    timestamp=opportunity['timestamp']
                )
                
                # 3. 风险检查（包括频率限制）
                self.logger.info("开始风险检查...")
                
                # 检查套利频率
                frequency_check = self.risk_manager.check_arbitrage_frequency()
                if not frequency_check.passed:
                    self.logger.warning(f"频率检查失败: {frequency_check.message}")
                    self.risk_manager.record_rejected_opportunity(frequency_check.message)
                    return
                
                # 验证套利机会
                risk_result = self.risk_manager.validate_opportunity(
                    arb_opportunity, 
                    total_balance_usdt
                )
                
                if not risk_result.passed:
                    self.logger.warning(f"风险检查失败: {risk_result.message}")
                    self.risk_manager.record_rejected_opportunity(risk_result.message)
                    return
                
                self.logger.info("风险检查通过")
                
                # 计算交易量
                trade_amount = self.risk_manager.calculate_position_size(arb_opportunity, balance)
                if trade_amount <= 0:
                    self.logger.warning("计算的交易量为0")
                    self.risk_manager.record_rejected_opportunity("计算的交易量为0")
                    return
                
                self.logger.info(f"计算交易量: {trade_amount:.6f}")
                
                # 4. 执行套利（三笔交易连续执行）
                self.logger.info("开始执行套利交易...")
                
                # 更新统计
                with self.stats_lock:
                    self.stats.executed_trades += 1
                    self.stats.last_trade_time = time.time()
                
                # 执行交易
                result = self.trade_executor.execute_arbitrage(arb_opportunity, trade_amount)
                
                # 5. 记录结果
                self._log_trade_result(arb_opportunity, result)
                
                # 处理交易结果
                await self._handle_trade_result(arb_opportunity, result)
                
            finally:
                # 减少当前交易计数
                self.current_trades -= 1
                
        except Exception as e:
            self.logger.error(f"处理套利机会异常: {e}")
            self._notify_error(f"处理套利机会异常: {e}")
    
    def _log_trade_result(self, opportunity, result: Dict):
        """
        记录交易结果
        
        Args:
            opportunity: 套利机会
            result: 交易结果
        """
        try:
            path_name = opportunity.path if hasattr(opportunity, 'path') else 'Unknown'
            
            if result['success']:
                profit = result['actual_profit']
                profit_rate = result['actual_profit_rate']
                investment = result['investment_amount']
                final_amount = result['final_amount']
                
                self.logger.info(f"=== 交易成功 ===")
                self.logger.info(f"路径: {path_name}")
                self.logger.info(f"投资金额: {investment:.6f}")
                self.logger.info(f"最终金额: {final_amount:.6f}")
                self.logger.info(f"实际利润: {profit:.6f}")
                self.logger.info(f"实际利润率: {profit_rate:.4%}")
                
                # 记录交易详情
                if 'trades' in result:
                    self.logger.info("交易详情:")
                    for i, trade in enumerate(result['trades']):
                        self.logger.info(f"  第{i+1}笔: 成交量={trade.filled_size:.6f}, 价格={trade.avg_price:.6f}")
                
            else:
                error = result.get('error', 'Unknown error')
                self.logger.error(f"=== 交易失败 ===")
                self.logger.error(f"路径: {path_name}")
                self.logger.error(f"错误: {error}")
                
                # 记录失败的交易详情
                if 'trades' in result:
                    self.logger.error("交易详情:")
                    for i, trade in enumerate(result['trades']):
                        if trade.success:
                            self.logger.error(f"  第{i+1}笔: 成功 - 成交量={trade.filled_size:.6f}, 价格={trade.avg_price:.6f}")
                        else:
                            self.logger.error(f"  第{i+1}笔: 失败 - {trade.error_message}")
                
        except Exception as e:
            self.logger.error(f"记录交易结果异常: {e}")
    
    async def _handle_trade_result(self, opportunity, result: Dict):
        """
        处理交易结果
        
        Args:
            opportunity: 套利机会
            result: 交易结果
        """
        try:
            if result['success']:
                # 成功的交易
                profit = result['actual_profit']
                self.logger.info(f"交易成功: 实际利润={profit:.6f}")
                
                # 更新统计
                with self.stats_lock:
                    self.stats.successful_trades += 1
                    if profit > 0:
                        self.stats.total_profit += profit
                    else:
                        self.stats.total_loss += abs(profit)
                    self.stats.net_profit = self.stats.total_profit - self.stats.total_loss
                
                # 记录到风险管理器
                self.risk_manager.record_arbitrage_attempt(True, profit)
                
            else:
                # 失败的交易
                self.logger.error(f"交易失败: {result['error']}")
                
                # 更新统计
                with self.stats_lock:
                    self.stats.failed_trades += 1
                
                # 记录到风险管理器
                self.risk_manager.record_arbitrage_attempt(False, 0)
                
                # 通知错误
                self._notify_error(f"交易失败: {result['error']}")
            
            # 通知交易结果回调
            self._notify_trade_result(opportunity, result)
            
        except Exception as e:
            self.logger.error(f"处理交易结果异常: {e}")
    
    async def _check_system_health(self):
        """
        检查系统健康状态
        """
        try:
            # 检查数据采集器状态
            if not self.data_collector.is_running:
                self.logger.warning("数据采集器未运行，尝试重启...")
                if not await self.data_collector.start(self.trading_pairs):
                    self.logger.error("数据采集器重启失败")
                    self._notify_error("数据采集器重启失败")
            
            # 套利引擎在同步模式下不需要检查监控状态
            
            # 检查风险管理器状态
            if not self.risk_manager.trading_enabled:
                self.logger.warning("风险管理器已禁用交易")
                self._notify_error("风险管理器已禁用交易")
            
        except Exception as e:
            self.logger.error(f"系统健康检查异常: {e}")
    
    def _get_trading_pairs(self) -> List[str]:
        """
        获取交易对配置
        
        Returns:
            交易对列表
        """
        trading_config = self.config_manager.get_trading_config()
        pairs = []
        
        # 从路径配置中提取交易对
        for path_name, path in trading_config.get('paths', {}).items():
            if isinstance(path, list) and len(path) > 1:
                # 从路径生成交易对
                for i in range(len(path) - 1):
                    asset1, asset2 = path[i], path[i + 1]
                    # 标准化交易对名称
                    pair1 = f"{asset1}-{asset2}"
                    pair2 = f"{asset2}-{asset1}"
                    if pair1 not in pairs:
                        pairs.append(pair1)
                    if pair2 not in pairs:
                        pairs.append(pair2)
        
        # 添加默认交易对
        default_pairs = [
            'BTC-USDT', 'ETH-USDT', 'BTC-USDC', 'ETH-USDC', 'USDT-USDC'
        ]
        for pair in default_pairs:
            if pair not in pairs:
                pairs.append(pair)
        
        return pairs
    
    def _notify_opportunity(self, opportunity: Dict):
        """通知套利机会回调"""
        for callback in self.opportunity_callbacks:
            try:
                callback(opportunity)
            except Exception as e:
                self.logger.error(f"套利机会回调执行失败: {e}")
    
    def _notify_trade_result(self, opportunity, result: Dict):
        """通知交易结果回调"""
        for callback in self.trade_result_callbacks:
            try:
                callback(opportunity, result)
            except Exception as e:
                self.logger.error(f"交易结果回调执行失败: {e}")
    
    def _notify_error(self, error_message: str):
        """通知错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error_message)
            except Exception as e:
                self.logger.error(f"错误回调执行失败: {e}")
    
    async def _cleanup(self):
        """清理资源"""
        try:
            # 清理回调
            self.opportunity_callbacks.clear()
            self.trade_result_callbacks.clear()
            self.error_callbacks.clear()
            
            # 重置状态
            self.current_trades = 0
            
        except Exception as e:
            self.logger.error(f"清理资源异常: {e}")
    
    def _log_final_stats(self):
        """记录最终统计信息"""
        try:
            with self.stats_lock:
                runtime = time.time() - self.stats.start_time
                
                self.logger.info("=== 交易统计 ===")
                self.logger.info(f"运行时间: {runtime:.1f}秒")
                self.logger.info(f"发现机会: {self.stats.total_opportunities}个")
                self.logger.info(f"执行交易: {self.stats.executed_trades}个")
                self.logger.info(f"成功交易: {self.stats.successful_trades}个")
                self.logger.info(f"失败交易: {self.stats.failed_trades}个")
                self.logger.info(f"总利润: {self.stats.total_profit:.6f}")
                self.logger.info(f"总损失: {self.stats.total_loss:.6f}")
                self.logger.info(f"净利润: {self.stats.net_profit:.6f}")
                
                if self.stats.executed_trades > 0:
                    success_rate = self.stats.successful_trades / self.stats.executed_trades
                    self.logger.info(f"成功率: {success_rate:.2%}")
                
                if runtime > 0:
                    opp_rate = self.stats.total_opportunities / runtime * 3600
                    trade_rate = self.stats.executed_trades / runtime * 3600
                    self.logger.info(f"机会发现率: {opp_rate:.1f}个/小时")
                    self.logger.info(f"交易执行率: {trade_rate:.1f}个/小时")
                
        except Exception as e:
            self.logger.error(f"记录最终统计异常: {e}")
    
    # 公共接口方法
    
    def get_status(self) -> Dict:
        """
        获取交易系统状态
        
        Returns:
            状态信息
        """
        return {
            'status': self.status.value,
            'is_running': self.is_running,
            'current_trades': self.current_trades,
            'data_collector_running': self.data_collector.is_running,
            'arbitrage_engine_monitoring': self.arbitrage_engine.is_monitoring,
            'risk_manager_enabled': self.risk_manager.trading_enabled,
            'subscribed_pairs': list(self.data_collector.subscribed_pairs),
            'risk_level': self.risk_manager.risk_level.value
        }
    
    def get_stats(self) -> Dict:
        """
        获取交易统计信息
        
        Returns:
            统计信息
        """
        with self.stats_lock:
            runtime = time.time() - self.stats.start_time
            return {
                'runtime_seconds': runtime,
                'total_opportunities': self.stats.total_opportunities,
                'executed_trades': self.stats.executed_trades,
                'successful_trades': self.stats.successful_trades,
                'failed_trades': self.stats.failed_trades,
                'success_rate': self.stats.successful_trades / self.stats.executed_trades if self.stats.executed_trades > 0 else 0,
                'total_profit': self.stats.total_profit,
                'total_loss': self.stats.total_loss,
                'net_profit': self.stats.net_profit,
                'last_opportunity_time': self.stats.last_opportunity_time,
                'last_trade_time': self.stats.last_trade_time,
                'opportunities_per_hour': self.stats.total_opportunities / runtime * 3600 if runtime > 0 else 0,
                'trades_per_hour': self.stats.executed_trades / runtime * 3600 if runtime > 0 else 0
            }
    
    def get_risk_stats(self) -> Dict:
        """
        获取风险统计信息
        
        Returns:
            风险统计信息
        """
        return self.risk_manager.get_risk_statistics()
    
    def add_opportunity_callback(self, callback: Callable):
        """
        添加套利机会回调
        
        Args:
            callback: 回调函数
        """
        if callback not in self.opportunity_callbacks:
            self.opportunity_callbacks.append(callback)
            self.logger.info(f"添加套利机会回调: {callback.__name__}")
    
    def add_trade_result_callback(self, callback: Callable):
        """
        添加交易结果回调
        
        Args:
            callback: 回调函数
        """
        if callback not in self.trade_result_callbacks:
            self.trade_result_callbacks.append(callback)
            self.logger.info(f"添加交易结果回调: {callback.__name__}")
    
    def add_error_callback(self, callback: Callable):
        """
        添加错误回调
        
        Args:
            callback: 回调函数
        """
        if callback not in self.error_callbacks:
            self.error_callbacks.append(callback)
            self.logger.info(f"添加错误回调: {callback.__name__}")
    
    def enable_trading(self):
        """启用交易"""
        self.risk_manager.enable_trading()
        self.logger.info("交易已启用")
    
    def disable_trading(self, reason: str = "手动禁用"):
        """
        禁用交易
        
        Args:
            reason: 禁用原因
        """
        self.risk_manager.disable_trading(reason)
        self.logger.info(f"交易已禁用: {reason}")
    
    def reset_daily_counters(self):
        """重置每日计数器"""
        self.risk_manager.reset_daily_counters()
        self.logger.info("每日计数器已重置")