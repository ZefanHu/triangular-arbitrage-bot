"""
交易控制器模块

负责整合所有模块，提供统一的交易控制接口
"""

import asyncio
import logging
import time
import threading
import psutil
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.trade_executor import TradeExecutor
from core.risk_manager import RiskManager
from config.config_manager import ConfigManager
from utils.trade_logger import TradeLogger


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


class TradingController:
    """
    交易控制器
    
    负责整合所有模块，提供统一的交易控制接口
    """
    
    def __init__(self, config_manager: ConfigManager = None, enable_rich_logging: bool = True):
        """
        初始化交易控制器
        
        Args:
            config_manager: 配置管理器实例
            enable_rich_logging: 是否启用Rich格式化日志
        """
        self.logger = logging.getLogger(__name__)
        
        # 配置管理
        self.config_manager = config_manager or ConfigManager()
        
        # 核心模块
        self.data_collector = DataCollector()
        self.arbitrage_engine = ArbitrageEngine(self.data_collector)
        self.trade_executor = TradeExecutor(self.data_collector.rest_client)
        self.risk_manager = RiskManager(self.config_manager, self.data_collector.rest_client)
        
        # 设置余额更新回调，连WebSocket到BalanceCache
        self.data_collector.set_balance_update_callback(self.trade_executor.balance_cache.update_from_websocket)
        
        # 交易日志记录器
        self.trade_logger = TradeLogger(enable_file_logging=True) if enable_rich_logging else None
        
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
        
        # 性能监控
        self.performance_start_time = time.time()
        self.loop_execution_times = []
        self.system_monitor_enabled = True
        
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
            loop_start_time = time.time()
            
            try:
                loop_count += 1
                self.logger.debug(f"开始第 {loop_count} 轮交易循环")
                
                # 定期输出统计信息
                current_time = time.time()
                if current_time - last_stats_log >= stats_log_interval:
                    self._log_periodic_stats()
                    if self.trade_logger:
                        self.trade_logger.print_daily_report()
                    last_stats_log = current_time
                
                # 更新系统资源使用情况
                if self.system_monitor_enabled:
                    self._update_system_metrics()
                
                # 1. 获取套利机会
                opportunities = self.arbitrage_engine.find_opportunities()
                
                if opportunities:
                    self.logger.info(f"发现 {len(opportunities)} 个套利机会")
                    
                    # 更新统计
                    with self.stats_lock:
                        self.stats.total_opportunities += len(opportunities)
                        self.stats.last_opportunity_time = time.time()
                    
                    # 记录套利机会到日志
                    if self.trade_logger:
                        for opp in opportunities:
                            self.trade_logger.log_opportunity_found(opp)
                    
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
            finally:
                # 记录循环执行时间
                loop_execution_time = time.time() - loop_start_time
                self.loop_execution_times.append(loop_execution_time)
                
                # 只保留最近100次的执行时间
                if len(self.loop_execution_times) > 100:
                    self.loop_execution_times.pop(0)
                
                # 更新性能统计
                with self.stats_lock:
                    self.stats.total_execution_time += loop_execution_time
                    self.stats.min_execution_time = min(self.stats.min_execution_time, loop_execution_time)
                    self.stats.max_execution_time = max(self.stats.max_execution_time, loop_execution_time)
                    if loop_count > 0:
                        self.stats.avg_execution_time = self.stats.total_execution_time / loop_count
                
                # 更新TradeLogger的性能指标
                if self.trade_logger:
                    self.trade_logger.update_performance_metrics(
                        execution_time=loop_execution_time,
                        api_calls=1,  # 每次循环至少一次API调用
                        api_errors=0  # 这里简化处理，实际应该从具体模块获取
                    )
        
        self.logger.info("主交易循环结束")
    
    def _update_system_metrics(self):
        """更新系统资源使用指标"""
        try:
            # 获取当前进程的资源使用情况
            process = psutil.Process()
            
            # 内存使用情况 (MB)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # CPU使用率
            cpu_percent = process.cpu_percent()
            
            # 更新统计
            with self.stats_lock:
                self.stats.peak_memory_usage = max(self.stats.peak_memory_usage, memory_mb)
                self.stats.peak_cpu_usage = max(self.stats.peak_cpu_usage, cpu_percent)
            
            # 更新TradeLogger的性能指标
            if self.trade_logger:
                self.trade_logger.performance_metrics.memory_usage = memory_mb
                self.trade_logger.performance_metrics.cpu_usage = cpu_percent
                
        except Exception as e:
            self.logger.debug(f"更新系统指标失败: {e}")
    
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
                from models.arbitrage_path import ArbitrageOpportunity, ArbitragePath
                
                # 将path列表转换为ArbitragePath对象
                arbitrage_path = ArbitragePath(path=opportunity['path'])
                
                arb_opportunity = ArbitrageOpportunity(
                    path=arbitrage_path,
                    profit_rate=opportunity['profit_rate'],
                    min_amount=opportunity['min_trade_amount'],
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
            
            # 记录交易结果到日志
            if self.trade_logger:
                self.trade_logger.log_trade_executed(opportunity, result)
            
            # 更新余额历史（如果有余额信息）
            if self.trade_logger and 'balance' in result:
                self.trade_logger.log_balance_update(result['balance'])
            
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
        
        从新的JSON格式路径配置中提取所有需要的交易对
        
        Returns:
            交易对列表
        """
        trading_config = self.config_manager.get_trading_config()
        pairs = set()  # 使用set避免重复
        
        # 从路径配置中提取交易对
        for path_name, path_config in trading_config.get('paths', {}).items():
            if not path_config:
                continue
                
            # 处理新的JSON格式
            if isinstance(path_config, dict) and 'steps' in path_config:
                for step in path_config['steps']:
                    if 'pair' in step:
                        pair = step['pair'].upper()  # 确保大写
                        pairs.add(pair)
                        
            # 向后兼容旧格式
            elif isinstance(path_config, dict) and 'assets' in path_config:
                # 这是旧格式转换后的结果，我们需要推断交易对
                assets = path_config['assets']
                for i in range(len(assets) - 1):
                    asset1, asset2 = assets[i].upper(), assets[i + 1].upper()
                    # 简单的交易对生成逻辑（可能需要根据实际情况调整）
                    if self._is_major_crypto(asset1) and self._is_stable_coin(asset2):
                        pairs.add(f"{asset1}-{asset2}")
                    elif self._is_major_crypto(asset2) and self._is_stable_coin(asset1):
                        pairs.add(f"{asset2}-{asset1}")
                    elif self._is_stable_coin(asset1) and self._is_stable_coin(asset2):
                        # 稳定币之间按字母顺序
                        if asset1 < asset2:
                            pairs.add(f"{asset1}-{asset2}")
                        else:
                            pairs.add(f"{asset2}-{asset1}")
                    else:
                        # 默认情况
                        pairs.add(f"{asset1}-{asset2}")
                        
            # 处理旧的列表格式（完全向后兼容）
            elif isinstance(path_config, list) and len(path_config) > 1:
                for i in range(len(path_config) - 1):
                    asset1, asset2 = path_config[i].upper(), path_config[i + 1].upper()
                    # 使用相同的逻辑
                    if self._is_major_crypto(asset1) and self._is_stable_coin(asset2):
                        pairs.add(f"{asset1}-{asset2}")
                    elif self._is_major_crypto(asset2) and self._is_stable_coin(asset1):
                        pairs.add(f"{asset2}-{asset1}")
                    elif self._is_stable_coin(asset1) and self._is_stable_coin(asset2):
                        if asset1 < asset2:
                            pairs.add(f"{asset1}-{asset2}")
                        else:
                            pairs.add(f"{asset2}-{asset1}")
                    else:
                        pairs.add(f"{asset1}-{asset2}")
        
        # 添加默认交易对 - 使用OKX实际支持的交易对
        default_pairs = [
            'BTC-USDT', 'ETH-USDT', 'ETH-BTC', 'USDC-USDT'
        ]
        for pair in default_pairs:
            pairs.add(pair)
        
        return list(pairs)
    
    def _is_major_crypto(self, asset: str) -> bool:
        """判断是否为主流加密货币"""
        major_cryptos = {'BTC', 'ETH', 'BNB', 'ADA', 'XRP', 'SOL', 'DOT', 'AVAX', 'MATIC'}
        return asset.upper() in major_cryptos
    
    def _is_stable_coin(self, asset: str) -> bool:
        """判断是否为稳定币"""
        stablecoins = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP'}
        return asset.upper() in stablecoins
    
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
        if self.trade_logger:
            self.trade_logger.reset_daily_stats()
        self.logger.info("每日计数器已重置")
    
    def start_real_time_monitor(self):
        """启动实时监控显示"""
        if self.trade_logger:
            self.trade_logger.start_real_time_monitor()
        else:
            self.logger.warning("实时监控需要启用Rich日志功能")
    
    def print_daily_report(self):
        """打印每日报告"""
        if self.trade_logger:
            self.trade_logger.print_daily_report()
        else:
            self._log_final_stats()
    
    def export_daily_report(self, date: str = None) -> str:
        """导出每日报告"""
        if self.trade_logger:
            return self.trade_logger.export_daily_report(date)
        else:
            self.logger.warning("导出报告需要启用Rich日志功能")
            return ""
    
    def get_performance_metrics(self) -> Dict:
        """获取性能指标"""
        with self.stats_lock:
            base_metrics = {
                'avg_execution_time': self.stats.avg_execution_time,
                'min_execution_time': self.stats.min_execution_time,
                'max_execution_time': self.stats.max_execution_time,
                'total_execution_time': self.stats.total_execution_time,
                'peak_memory_usage_mb': self.stats.peak_memory_usage,
                'peak_cpu_usage_percent': self.stats.peak_cpu_usage,
                'api_call_count': self.stats.api_call_count,
                'api_error_count': self.stats.api_error_count,
                'loop_count': len(self.loop_execution_times),
                'recent_loop_times': self.loop_execution_times[-10:] if self.loop_execution_times else []
            }
            
            if self.trade_logger:
                trade_logger_metrics = self.trade_logger.get_statistics_summary()
                base_metrics.update(trade_logger_metrics)
            
            return base_metrics
    
    def get_enhanced_stats(self) -> Dict:
        """获取增强的统计信息"""
        base_stats = self.get_stats()
        performance_metrics = self.get_performance_metrics()
        
        enhanced_stats = {
            **base_stats,
            'performance_metrics': performance_metrics,
            'system_health': {
                'data_collector_running': self.data_collector.is_running,
                'arbitrage_engine_monitoring': self.arbitrage_engine.is_monitoring,
                'risk_manager_enabled': self.risk_manager.trading_enabled,
                'trading_enabled': self.is_running,
                'current_status': self.status.value
            }
        }
        
        if self.trade_logger:
            enhanced_stats['trade_logger_stats'] = self.trade_logger.get_statistics_summary()
        
        return enhanced_stats
    
    def print_balance_history(self):
        """打印余额历史"""
        if self.trade_logger:
            self.trade_logger.print_balance_history()
        else:
            self.logger.warning("余额历史需要启用Rich日志功能")
    
    def update_balance_history(self, balance: Dict):
        """更新余额历史"""
        if self.trade_logger:
            self.trade_logger.log_balance_update(balance)
    
    def get_current_opportunities(self) -> List[Dict]:
        """获取当前套利机会"""
        if self.trade_logger:
            return self.trade_logger.current_opportunities
        else:
            return []
    
    def get_recent_trades(self) -> List[Dict]:
        """获取最近交易记录"""
        if self.trade_logger:
            return [trade.__dict__ for trade in self.trade_logger.recent_trades]
        else:
            return []