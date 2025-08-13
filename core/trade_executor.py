"""
交易执行模块

负责执行套利交易的核心组件
"""

import time
from utils.logger import setup_logger
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import threading

from core.okx_client import OKXClient
from models.arbitrage_path import ArbitrageOpportunity
from models.trade import Trade, TradeStatus, TradeResult, ArbitrageRecord


class BalanceCache:
    """
    余额缓存管理器
    
    维护本地余额缓存，结合WebSocket实时更新和REST API
    """
    
    def __init__(self, okx_client: OKXClient):
        self.okx_client = okx_client
        self.cache: Dict[str, float] = {}
        self.last_update: float = 0
        self.cache_ttl: float = 30.0  # 延长缓存有效期，因为有WebSocket实时更新
        self.lock = threading.Lock()
        self.logger = setup_logger(__name__)
        self.websocket_connected = False
    
    def get_balance(self, force_refresh: bool = False) -> Dict[str, float]:
        """获取余额，优先使用WebSocket实时数据"""
        with self.lock:
            current_time = time.time()
            
            # 如果WebSocket未连接或强制刷新或缓存过期，则使用REST API
            if force_refresh or not self.websocket_connected or (current_time - self.last_update > self.cache_ttl):
                self.logger.debug("使用REST API刷新余额缓存")
                balance = self.okx_client.get_balance()
                if balance:
                    self.cache = balance
                    self.last_update = current_time
                    self.logger.debug(f"REST API余额缓存已更新: {self.cache}")
                else:
                    self.logger.warning("REST API获取余额失败，使用旧缓存")
            
            return self.cache.copy()
    
    def update_from_websocket(self, balances: Dict[str, float]):
        """从WebSocket更新余额缓存
        
        Args:
            balances: WebSocket推送的余额数据
        """
        with self.lock:
            self.cache = balances
            self.last_update = time.time()
            self.websocket_connected = True
            self.logger.debug(f"WebSocket余额更新: {self.cache}")
    
    def set_websocket_connected(self, connected: bool):
        """设置WebSocket连接状态
        
        Args:
            connected: WebSocket是否已连接
        """
        self.websocket_connected = connected
    
    def update_balance(self, asset: str, amount: float):
        """更新本地余额缓存"""
        with self.lock:
            if asset in self.cache:
                old_balance = self.cache[asset]
                self.cache[asset] = amount
                self.logger.debug(f"更新余额缓存: {asset} {old_balance} -> {amount}")
            else:
                self.cache[asset] = amount
                self.logger.debug(f"添加余额缓存: {asset} = {amount}")
    
    def adjust_balance(self, asset: str, delta: float):
        """调整余额缓存"""
        with self.lock:
            if asset in self.cache:
                old_balance = self.cache[asset]
                self.cache[asset] = max(0, old_balance + delta)
                self.logger.debug(f"调整余额缓存: {asset} {old_balance} + {delta} = {self.cache[asset]}")
            else:
                self.cache[asset] = max(0, delta)
                self.logger.debug(f"初始化余额缓存: {asset} = {self.cache[asset]}")


class TradeExecutor:
    """
    交易执行器
    
    负责执行套利交易，包括下单、监控订单状态、处理超时等
    """
    
    def __init__(self, okx_client: OKXClient):
        """
        初始化交易执行器
        
        Args:
            okx_client: OKX客户端实例
        """
        self.okx_client = okx_client
        self.logger = setup_logger(__name__)
        
        # 从配置管理器获取配置
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        trading_config = config_manager.get_trading_config()
        risk_config = config_manager.get_risk_config()
        
        # 交易配置
        self.order_timeout = trading_config['parameters'].get('order_timeout', 10.0)
        self.price_adjustment = trading_config['parameters'].get('price_adjustment', 0.001)
        self.max_retries = 3  # 保持硬编码，因为已从配置中移除
        self.min_profit_threshold = trading_config['parameters'].get('min_profit_threshold', 0.0005)
        
        # 网络重试配置
        self.network_retry_count = risk_config.get('network_retry_count', 3)
        self.network_retry_delay = risk_config.get('network_retry_delay', 1.0)
        
        # 余额缓存管理
        self.balance_cache = BalanceCache(okx_client)
        
        # 交易记录
        self.trade_records: List[ArbitrageRecord] = []
        
        self.logger.info("交易执行器初始化完成")
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity, 
                         investment_amount: float) -> Dict[str, any]:
        """
        执行套利交易
        
        Args:
            opportunity: 套利机会
            investment_amount: 投资金额
            
        Returns:
            执行结果字典
        """
        self.logger.info(f"开始执行套利交易: {opportunity.path} 投资金额: {investment_amount}")
        
        try:
            # 检查套利机会是否过期
            if opportunity.is_expired():
                self.logger.warning("套利机会已过期")
                return {
                    'success': False,
                    'error': '套利机会已过期',
                    'trades': []
                }
            
            # 检查投资金额是否足够
            if not opportunity.is_amount_sufficient(investment_amount):
                self.logger.warning(f"投资金额不足，最小需要: {opportunity.min_amount}")
                return {
                    'success': False,
                    'error': f'投资金额不足，最小需要: {opportunity.min_amount}',
                    'trades': []
                }
            
            # 创建交易记录
            record = ArbitrageRecord(
                opportunity=opportunity,
                investment_amount=investment_amount,
                expected_profit=opportunity.get_profit_amount(investment_amount)
            )
            
            # 交易前检查
            pre_check_result = self._pre_trade_check(opportunity, investment_amount)
            if not pre_check_result['success']:
                self.logger.error(f"交易前检查失败: {pre_check_result['error']}")
                record.success = False
                record.end_time = datetime.now().timestamp()
                self.trade_records.append(record)
                return {
                    'success': False,
                    'error': pre_check_result['error'],
                    'trades': []
                }
            
            self.logger.info(f"交易前检查通过: {pre_check_result['message']}")
            
            # 生成交易列表
            trades = self._generate_trades(opportunity, investment_amount)
            if not trades:
                self.logger.error("无法生成交易列表")
                return {
                    'success': False,
                    'error': '无法生成交易列表',
                    'trades': []
                }
            
            self.logger.info(f"生成 {len(trades)} 笔交易")
            
            # 按顺序执行三笔交易
            trade_results = []
            current_amount = investment_amount
            
            for i, trade in enumerate(trades):
                self.logger.info(f"=== 执行第 {i+1} 笔交易 ===")
                self.logger.info(f"交易详情: {trade.inst_id} {trade.side} {trade.size} @ {trade.price}")
                
                # 根据实际资产数量调整交易数量
                if i > 0:
                    # 使用上一笔交易的成交结果
                    prev_result = trade_results[-1]
                    if prev_result.success and prev_result.filled_size > 0:
                        # 更新交易数量
                        if trade.side == 'buy':
                            # 买入：用上一笔交易得到的资产数量
                            trade.size = prev_result.filled_size * prev_result.avg_price / trade.price
                        else:
                            # 卖出：直接使用上一笔交易的成交数量
                            trade.size = prev_result.filled_size
                        self.logger.info(f"根据上一笔交易结果调整数量: {trade.size}")
                
                # 执行单笔交易
                result = self._execute_single_trade_with_safety(trade.inst_id, trade.side, trade.size, trade.price)
                trade_results.append(result)
                record.trade_results.append(result)
                
                if not result.success:
                    self.logger.error(f"第 {i+1} 笔交易失败: {result.error_message}")
                    # 处理失败的交易
                    self._handle_trade_failure(record, i, result)
                    return {
                        'success': False,
                        'error': f'第 {i+1} 笔交易失败: {result.error_message}',
                        'trades': trade_results
                    }
                
                self.logger.info(f"第 {i+1} 笔交易成功: 成交量 {result.filled_size}, 平均价 {result.avg_price}")
                
                # 交易后处理
                self._post_trade_processing(trade, result)
                
                # 检查是否需要继续执行后续交易
                if i < len(trades) - 1:
                    # 等待一小段时间，让交易确认
                    time.sleep(0.1)
            
            # 计算实际利润
            final_amount = trade_results[-1].filled_size * trade_results[-1].avg_price if trade_results else 0
            actual_profit = final_amount - investment_amount
            actual_profit_rate = actual_profit / investment_amount if investment_amount > 0 else 0
            
            # 完成交易记录
            record.actual_profit = actual_profit
            record.success = True
            record.end_time = datetime.now().timestamp()
            self.trade_records.append(record)
            
            self.logger.info(f"套利交易完成，实际利润: {actual_profit:.6f}, 利润率: {actual_profit_rate:.4%}")
            
            return {
                'success': True,
                'investment_amount': investment_amount,
                'final_amount': final_amount,
                'actual_profit': actual_profit,
                'actual_profit_rate': actual_profit_rate,
                'trades': trade_results,
                'record': record
            }
            
        except Exception as e:
            self.logger.error(f"执行套利交易时发生异常: {e}")
            # 记录异常
            if 'record' in locals():
                record.success = False
                record.end_time = datetime.now().timestamp()
                self.trade_records.append(record)
            return {
                'success': False,
                'error': f'执行套利交易时发生异常: {str(e)}',
                'trades': []
            }
    
    def _execute_single_trade(self, inst_id: str, side: str, size: float, price: float) -> TradeResult:
        """
        执行单笔交易
        
        Args:
            inst_id: 交易对ID，如BTC-USDT
            side: 交易方向，buy或sell
            size: 交易数量
            price: 交易价格
            
        Returns:
            交易结果
        """
        self.logger.info(f"开始执行单笔交易: {inst_id} {side} {size} @ {price}")
        
        try:
            # 获取当前市场价格进行验证
            ticker = self.okx_client.get_ticker(inst_id)
            if not ticker:
                return TradeResult(
                    success=False,
                    error_message=f"无法获取 {inst_id} 市场价格"
                )
            
            # 优化价格以提高成交概率
            optimized_price = self._optimize_price_for_trade(inst_id, side, price, ticker)
            
            # 尝试下单
            for attempt in range(self.max_retries):
                self.logger.info(f"第 {attempt + 1} 次尝试下单: {inst_id} {side} {size} @ {optimized_price}")
                
                # 调用okx_client.place_order()，参考example.py，使用tdMode='cash'（现货模式）
                order_id = self.okx_client.place_order(
                    inst_id=inst_id,
                    side=side,
                    order_type='limit',
                    size=str(size),
                    price=str(optimized_price)
                )
                
                if not order_id:
                    self.logger.warning(f"第 {attempt + 1} 次下单失败，可能是参数错误或余额不足")
                    # 如果不是最后一次尝试，稍微调整价格
                    if attempt < self.max_retries - 1:
                        if side == 'buy':
                            optimized_price *= 1.001  # 买入时稍微提高价格
                        else:
                            optimized_price *= 0.999  # 卖出时稍微降低价格
                    continue
                
                self.logger.info(f"下单成功，订单ID: {order_id}")
                
                # 等待订单成交
                result = self._wait_order_filled(inst_id, order_id, self.order_timeout)
                
                if result.success:
                    self.logger.info(f"交易成功，订单ID: {order_id}，成交量: {result.filled_size}，平均价: {result.avg_price}")
                    return result
                else:
                    self.logger.warning(f"订单 {order_id} 未成交: {result.error_message}")
                    # 撤销未成交订单
                    cancel_success = self.okx_client.cancel_order(inst_id, order_id)
                    if cancel_success:
                        self.logger.info(f"成功撤销订单 {order_id}")
                    else:
                        self.logger.warning(f"撤销订单 {order_id} 失败")
            
            return TradeResult(
                success=False,
                error_message=f"经过 {self.max_retries} 次尝试后仍未成交"
            )
            
        except Exception as e:
            self.logger.error(f"执行单笔交易时发生异常: {e}")
            return TradeResult(
                success=False,
                error_message=f"执行单笔交易时发生异常: {str(e)}"
            )
    
    def _wait_order_filled(self, inst_id: str, order_id: str, timeout: float) -> TradeResult:
        """
        等待订单成交
        
        Args:
            inst_id: 交易对ID
            order_id: 订单ID
            timeout: 超时时间（秒）
            
        Returns:
            交易结果
        """
        self.logger.info(f"等待订单 {order_id} 成交，超时时间: {timeout}秒")
        
        start_time = time.time()
        check_interval = 0.1  # 检查间隔（秒）
        last_state = None
        
        try:
            while time.time() - start_time < timeout:
                # 查询订单状态
                order_status = self.okx_client.get_order_status(inst_id, order_id)
                
                if not order_status:
                    self.logger.warning(f"无法获取订单 {order_id} 状态")
                    time.sleep(check_interval)
                    continue
                
                state = order_status.get('state', '')
                filled_size = order_status.get('filled_size', 0)
                avg_price = order_status.get('avg_price', 0)
                
                # 记录状态变化
                if state != last_state:
                    self.logger.info(f"订单 {order_id} 状态变化: {last_state} -> {state}")
                    last_state = state
                
                # 检查OKX API返回的具体状态
                if state == 'filled':
                    self.logger.info(f"订单 {order_id} 完全成交: 成交量 {filled_size}, 平均价 {avg_price}")
                    return TradeResult(
                        success=True,
                        order_id=order_id,
                        filled_size=filled_size,
                        avg_price=avg_price if avg_price else 0
                    )
                elif state == 'partially_filled':
                    self.logger.info(f"订单 {order_id} 部分成交: {filled_size}")
                    # 继续等待
                    time.sleep(check_interval)
                elif state == 'live':
                    # 订单还在等待成交
                    self.logger.debug(f"订单 {order_id} 等待成交中...")
                    time.sleep(check_interval)
                elif state in ['cancelled', 'canceled']:
                    self.logger.warning(f"订单 {order_id} 已被取消")
                    return TradeResult(
                        success=False,
                        error_message=f"订单已被取消"
                    )
                elif state == 'failed':
                    self.logger.error(f"订单 {order_id} 失败")
                    return TradeResult(
                        success=False,
                        error_message=f"订单失败"
                    )
                else:
                    # 未知状态，继续等待
                    self.logger.debug(f"订单 {order_id} 状态: {state}")
                    time.sleep(check_interval)
            
            # 超时，尝试撤单
            self.logger.warning(f"订单 {order_id} 等待超时，尝试撤单")
            cancel_success = self.okx_client.cancel_order(inst_id, order_id)
            if cancel_success:
                self.logger.info(f"超时撤单成功: {order_id}")
            else:
                self.logger.warning(f"超时撤单失败: {order_id}")
                
            return TradeResult(
                success=False,
                error_message="订单等待超时"
            )
            
        except Exception as e:
            self.logger.error(f"等待订单成交时发生异常: {e}")
            return TradeResult(
                success=False,
                error_message=f"等待订单成交时发生异常: {str(e)}"
            )
    
    def _get_trading_pair_price(self, pair: str) -> Optional[Dict[str, float]]:
        """
        获取交易对价格，支持合成价格
        
        对于OKX不直接支持的交易对（如BTC-USDC），
        通过相关的USDT计价对合成价格
        
        Args:
            pair: 交易对，如 "BTC-USDC"
            
        Returns:
            包含best_bid和best_ask的价格字典，失败返回None
        """
        # 首先尝试直接获取
        ticker = self.okx_client.get_ticker(pair)
        if ticker:
            return {
                'best_bid': ticker['best_bid'],
                'best_ask': ticker['best_ask']
            }
        
        # 如果直接获取失败，尝试合成价格
        self.logger.debug(f"无法直接获取 {pair} 价格，尝试合成价格")
        
        # 解析交易对
        if '-' not in pair:
            self.logger.error(f"无效的交易对格式: {pair}")
            return None
        
        base_asset, quote_asset = pair.split('-')
        
        # 对于USDT/USDC/BTC三币种系统，处理合成价格
        if base_asset in ['USDT', 'USDC', 'BTC'] and quote_asset in ['USDT', 'USDC', 'BTC']:
            # 尝试通过USDT计价对合成
            if quote_asset != 'USDT':
                # 获取 base_asset-USDT 和 quote_asset-USDT 的价格
                base_usdt_ticker = self.okx_client.get_ticker(f"{base_asset}-USDT")
                quote_usdt_ticker = self.okx_client.get_ticker(f"{quote_asset}-USDT")
                
                if base_usdt_ticker and quote_usdt_ticker:
                    # 计算合成价格: (base_asset/USDT) / (quote_asset/USDT) = base_asset/quote_asset
                    base_usdt_bid = base_usdt_ticker['best_bid']
                    base_usdt_ask = base_usdt_ticker['best_ask']
                    quote_usdt_bid = quote_usdt_ticker['best_bid']
                    quote_usdt_ask = quote_usdt_ticker['best_ask']
                    
                    # 合成买一价: base_ask / quote_bid (保守估计)
                    synthetic_bid = base_usdt_bid / quote_usdt_ask
                    # 合成卖一价: base_bid / quote_ask (保守估计)
                    synthetic_ask = base_usdt_ask / quote_usdt_bid
                    
                    self.logger.info(f"合成价格 {pair}: bid={synthetic_bid:.6f}, ask={synthetic_ask:.6f}")
                    
                    return {
                        'best_bid': synthetic_bid,
                        'best_ask': synthetic_ask
                    }
        
        self.logger.error(f"无法获取或合成 {pair} 价格")
        return None
    
    def _generate_trades(self, opportunity: ArbitrageOpportunity, 
                        investment_amount: float) -> List[Trade]:
        """
        根据套利机会生成交易列表
        
        Args:
            opportunity: 套利机会
            investment_amount: 投资金额
            
        Returns:
            交易列表
        """
        trades = []
        trading_pairs = opportunity.get_trading_pairs()
        directions = opportunity.get_trade_directions()
        
        if len(trading_pairs) != len(directions):
            self.logger.error("交易对数量与方向数量不匹配")
            return []
        
        current_amount = investment_amount
        
        for i, (pair, direction) in enumerate(zip(trading_pairs, directions)):
            # 获取当前市场价格（支持合成价格）
            price_info = self._get_trading_pair_price(pair)
            if not price_info:
                self.logger.error(f"无法获取 {pair} 市场价格")
                return []
            
            # 计算交易数量和价格
            if direction == 'buy':
                # 买入：用报价资产买基础资产
                price = price_info['best_ask']  # 买入使用卖一价
                size = current_amount / price
            else:
                # 卖出：卖基础资产得报价资产
                price = price_info['best_bid']  # 卖出使用买一价
                size = current_amount
            
            # 创建交易对象
            trade = Trade(
                inst_id=pair,
                side=direction,
                size=size,
                price=price
            )
            
            trades.append(trade)
            
            # 更新下一步的金额
            if direction == 'buy':
                current_amount = size
            else:
                current_amount = size * price
        
        return trades
    
    def _optimize_price_for_trade(self, inst_id: str, side: str, price: float, ticker: Dict[str, any]) -> float:
        """
        优化交易价格
        
        Args:
            inst_id: 交易对ID
            side: 交易方向
            price: 原始价格
            ticker: 市场行情数据
            
        Returns:
            优化后的价格
        """
        try:
            # 确保输入价格是数字类型
            if isinstance(price, str):
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    self.logger.error(f"无法转换价格为浮点数: {price}，使用默认价格")
                    return 0.0
            elif not isinstance(price, (int, float)):
                self.logger.error(f"价格类型错误: {type(price)}，使用默认价格")
                return 0.0
            
            # 确保ticker数据中的价格是数字类型
            def safe_float_convert(value, field_name):
                try:
                    if isinstance(value, str):
                        return float(value)
                    elif isinstance(value, (int, float)):
                        return float(value)
                    else:
                        self.logger.warning(f"{field_name} 类型错误: {type(value)}, 值: {value}")
                        return 0.0
                except (ValueError, TypeError):
                    self.logger.warning(f"无法转换 {field_name} 为浮点数: {value}")
                    return 0.0
            
            best_bid = safe_float_convert(ticker.get('best_bid', 0), 'best_bid')
            best_ask = safe_float_convert(ticker.get('best_ask', 0), 'best_ask')
            
            if best_bid <= 0 or best_ask <= 0:
                self.logger.error(f"无效的市场价格数据: bid={best_bid}, ask={best_ask}")
                return price
            
            if side == 'buy':
                # 买入：在买一价基础上稍微提高价格，提高成交概率
                max_price = best_ask * 1.005
                optimized_price = min(best_bid * (1 + self.price_adjustment), max_price)
            else:
                # 卖出：在卖一价基础上稍微降低价格，提高成交概率
                min_price = best_bid * 0.995
                optimized_price = max(best_ask * (1 - self.price_adjustment), min_price)
            
            self.logger.debug(f"价格优化 {inst_id}: 原价 {price} -> 优化价 {optimized_price}")
            return optimized_price
            
        except Exception as e:
            self.logger.error(f"价格优化失败: {e}，使用原价格")
            return price if isinstance(price, (int, float)) else 0.0
    
    def _pre_trade_check(self, opportunity: ArbitrageOpportunity, 
                        investment_amount: float) -> Dict[str, any]:
        """
        交易前检查
        
        Args:
            opportunity: 套利机会
            investment_amount: 投资金额
            
        Returns:
            检查结果
        """
        # 检查套利机会是否过期
        if opportunity.is_expired():
            return {
                'success': False,
                'error': '套利机会已过期'
            }
        
        # 检查投资金额是否足够
        if not opportunity.is_amount_sufficient(investment_amount):
            return {
                'success': False,
                'error': f'投资金额不足，最小需要: {opportunity.min_amount}'
            }
        
        # 检查余额
        balance_check = self.get_balance_check(opportunity, investment_amount)
        if not balance_check['success']:
            return {
                'success': False,
                'error': balance_check['error']
            }
        
        return {
            'success': True,
            'message': '检查通过'
        }
    
    def get_balance_check(self, opportunity: ArbitrageOpportunity, 
                         investment_amount: float) -> Dict[str, any]:
        """
        检查执行套利交易所需的资产余额
        
        Args:
            opportunity: 套利机会
            investment_amount: 投资金额
            
        Returns:
            余额检查结果
        """
        balance = self.okx_client.get_balance()
        if not balance:
            return {
                'success': False,
                'error': '无法获取账户余额'
            }
        
        start_asset = opportunity.path.get_start_asset()
        required_balance = investment_amount
        available_balance = balance.get(start_asset, 0)
        
        if available_balance < required_balance:
            return {
                'success': False,
                'error': f'余额不足，需要 {required_balance} {start_asset}，可用 {available_balance} {start_asset}'
            }
        
        return {
            'success': True,
            'start_asset': start_asset,
            'required_balance': required_balance,
            'available_balance': available_balance
        }