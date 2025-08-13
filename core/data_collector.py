"""
数据采集器

整合REST和WebSocket数据源，提供统一的数据接口
"""

import asyncio
import time
from utils.logger import setup_logger
import threading
from typing import Dict, Any, Optional, List, Callable
from core.okx_client import OKXClient
from core.websocket_manager import WebSocketManager
from models.order_book import OrderBook
from models.portfolio import Portfolio


class DataCollector:
    """
    数据采集器
    
    负责协调REST和WebSocket数据采集，提供统一的数据接口。
    - REST用于账户数据（余额等）
    - WebSocket用于实时市场数据（订单簿等）
    """
    
    def __init__(self):
        """初始化数据采集器"""
        self.logger = setup_logger(__name__)
        
        # 初始化REST客户端
        self.rest_client = OKXClient()
        
        # 初始化WebSocket管理器
        self.ws_manager = WebSocketManager()
        
        # 余额更新回调（将在TradeExecutor中设置）
        self.balance_update_callback = None
        
        # 运行状态
        self.is_running = False
        
        # 订阅的交易对
        self.subscribed_pairs = set()
        
        # 数据更新回调
        self.data_callbacks = []
        
        # 订单簿缓存
        self.orderbook_cache = {}
        self.cache_lock = threading.Lock()
        
        # 账户余额缓存
        self.balance_cache = None
        self.balance_last_updated = 0
        self.balance_lock = threading.Lock()
        
        # 数据有效性配置 - 更严格的时间阈值
        self.data_stale_threshold = 2.0  # 2秒（从5秒降低到2秒）
        self.arbitrage_data_threshold = 0.5  # 套利计算专用：500ms
        self.balance_sync_interval = 30.0  # 30秒
        
        # 定期同步任务
        self.sync_task = None
        self.reconnect_task = None
        self.stats_task = None
        
        # 性能统计信息
        self.stats = {
            'start_time': time.time(),
            'api_calls': {
                'get_balance': {'count': 0, 'total_time': 0, 'errors': 0},
                'get_orderbook': {'count': 0, 'total_time': 0, 'errors': 0}
            },
            'websocket': {
                'messages_received': 0,
                'last_message_time': 0,
                'connection_errors': 0,
                'reconnections': 0
            },
            'cache': {
                'hits': 0,
                'misses': 0,
                'orderbook_updates': 0,
                'balance_updates': 0
            },
            'errors': {
                'total': 0,
                'last_hour': 0,
                'last_error_time': 0
            }
        }
        self.stats_lock = threading.Lock()
        
        # 性能监控配置
        self.stats_log_interval = 60.0  # 每分钟记录一次
        self.error_count_reset_time = time.time()
        
        self.logger.info("数据采集器初始化完成")
    
    def set_balance_update_callback(self, callback: Callable):
        """设置余额更新回调函数
        
        Args:
            callback: 回调函数，接收参数 (balances: Dict[str, float])
        """
        self.balance_update_callback = callback
        # 如果WebSocket已连接，立即设置回调
        if self.ws_manager and self.is_running:
            self.ws_manager.set_balance_update_callback(callback)
        self.logger.info("已设置余额更新回调函数")
    
    async def start(self, trading_pairs: List[str] = None) -> bool:
        """
        启动数据采集
        
        Args:
            trading_pairs: 要订阅的交易对列表，如['BTC-USDT', 'ETH-USDT']
            
        Returns:
            启动是否成功
        """
        try:
            if self.is_running:
                self.logger.warning("数据采集器已在运行")
                return True
            
            self.logger.info("正在启动数据采集器...")
            
            # 设置默认交易对 - 使用实盘支持的BTC-USDT-USDC三角套利对
            if trading_pairs is None:
                trading_pairs = [
                    'BTC-USDT', 'BTC-USDC', 'USDC-USDT'
                ]
            
            # 启动WebSocket连接
            if not await self.ws_manager.connect():
                self.logger.error("WebSocket连接失败")
                return False
            
            # 订阅订单簿数据
            if not await self.ws_manager.subscribe_orderbooks(trading_pairs):
                self.logger.error("订阅订单簿失败")
                return False
            
            # 记录订阅的交易对
            self.subscribed_pairs.update(trading_pairs)
            
            # 添加数据更新回调
            self.ws_manager.add_data_callback(self._on_data_update)
            
            # 设置WebSocket余额更新回调
            if self.balance_update_callback:
                self.ws_manager.set_balance_update_callback(self.balance_update_callback)
            
            # 启动定期同步任务
            self.sync_task = asyncio.create_task(self._balance_sync_loop())
            
            # 启动自动重连监控
            self.reconnect_task = asyncio.create_task(self._reconnect_monitor())
            
            # 启动性能统计任务
            self.stats_task = asyncio.create_task(self._stats_logger_loop())
            
            # 初始化余额缓存
            await self._sync_balance()
            
            # 重置统计信息
            with self.stats_lock:
                self.stats['start_time'] = time.time()
                self.error_count_reset_time = time.time()
            
            self.is_running = True
            self.logger.info(f"数据采集器启动成功，已订阅 {len(trading_pairs)} 个交易对")
            
            return True
            
        except Exception as e:
            self.logger.error(f"启动数据采集器失败: {e}")
            return False
    
    async def stop(self) -> bool:
        """
        停止数据采集
        
        Returns:
            停止是否成功
        """
        try:
            if not self.is_running:
                self.logger.warning("数据采集器未运行")
                return True
            
            self.logger.info("正在停止数据采集器...")
            
            # 停止WebSocket连接
            await self.ws_manager.disconnect()
            
            # 取消定期同步任务
            if self.sync_task:
                self.sync_task.cancel()
                self.sync_task = None
            
            # 取消自动重连监控
            if self.reconnect_task:
                self.reconnect_task.cancel()
                self.reconnect_task = None
            
            # 取消性能统计任务
            if self.stats_task:
                self.stats_task.cancel()
                self.stats_task = None
            
            # 清理状态
            self.subscribed_pairs.clear()
            self.data_callbacks.clear()
            
            # 清理缓存
            with self.cache_lock:
                self.orderbook_cache.clear()
            
            with self.balance_lock:
                self.balance_cache = None
                self.balance_last_updated = 0
            
            self.is_running = False
            
            self.logger.info("数据采集器已停止")
            return True
            
        except Exception as e:
            self.logger.error(f"停止数据采集器失败: {e}")
            return False
    
    def get_orderbook(self, inst_id: str) -> Optional[OrderBook]:
        """
        获取订单簿数据（优先使用缓存数据）
        
        Args:
            inst_id: 产品ID，如'BTC-USDT'
            
        Returns:
            订单簿数据或None
        """
        try:
            # 先检查缓存
            with self.cache_lock:
                cached_orderbook = self.orderbook_cache.get(inst_id)
                if cached_orderbook and self._is_data_fresh(cached_orderbook.timestamp):
                    # 记录缓存命中
                    self._record_cache_hit()
                    return cached_orderbook
            
            # 记录缓存未命中
            self._record_cache_miss()
            
            # 如果缓存没有或数据过期，尝试从WebSocket获取
            if self.is_running and self.ws_manager.is_ws_connected():
                ws_data = self.ws_manager.get_orderbook(inst_id)
                if ws_data:
                    # 修复时间戳处理：WebSocket返回的是毫秒时间戳字符串，需要转换为秒
                    ws_timestamp = ws_data.get('timestamp', '')
                    if ws_timestamp and ws_timestamp != '':
                        try:
                            timestamp = float(ws_timestamp) / 1000.0  # 毫秒转秒
                        except (ValueError, TypeError):
                            self.logger.warning(f"无效的WebSocket时间戳: {ws_timestamp}，使用本地时间")
                            timestamp = time.time()
                    else:
                        timestamp = time.time()
                    
                    orderbook = OrderBook(
                        symbol=inst_id,
                        bids=ws_data['bids'],
                        asks=ws_data['asks'],
                        timestamp=timestamp
                    )
                    # 更新缓存
                    with self.cache_lock:
                        self.orderbook_cache[inst_id] = orderbook
                    return orderbook
            
            # 如果WebSocket数据不可用，使用REST获取
            self.logger.debug(f"使用REST获取{inst_id}订单簿数据")
            start_time = time.time()
            rest_data = self.rest_client.get_orderbook(inst_id)
            response_time = time.time() - start_time
            
            # 记录API调用统计
            self._record_api_call('get_orderbook', response_time, rest_data is not None)
            
            # rest_client.get_orderbook现在直接返回OrderBook对象
            if rest_data and isinstance(rest_data, OrderBook):
                orderbook = rest_data
                # 更新缓存
                with self.cache_lock:
                    self.orderbook_cache[inst_id] = orderbook
                return orderbook
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取{inst_id}订单簿数据失败: {e}")
            self._record_error()
            return None
    
    def get_arbitrage_orderbook(self, inst_id: str) -> Optional[OrderBook]:
        """
        获取用于套利计算的高精度订单簿数据
        
        使用更严格的数据新鲜度要求（500ms内）
        
        Args:
            inst_id: 产品ID
            
        Returns:
            订单簿对象或None
        """
        start_time = time.time()
        
        try:
            # 首先检查缓存中的数据是否足够新鲜
            with self.cache_lock:
                cached_orderbook = self.orderbook_cache.get(inst_id)
                if cached_orderbook and self._is_arbitrage_data_fresh(cached_orderbook.timestamp):
                    # 记录缓存命中
                    self._record_cache_hit()
                    return cached_orderbook
            
            # 如果缓存数据不够新鲜，记录并返回None
            # 套利计算不接受任何过期数据
            if cached_orderbook:
                data_age = time.time() - cached_orderbook.timestamp
                self.logger.debug(f"{inst_id} 数据太旧用于套利计算: {data_age*1000:.1f}ms > {self.arbitrage_data_threshold*1000}ms")
            else:
                self.logger.debug(f"{inst_id} 没有缓存数据用于套利计算")
                
            self._record_cache_miss()
            return None
            
        except Exception as e:
            self.logger.error(f"获取套利订单簿失败 {inst_id}: {e}")
            self._record_api_call('get_orderbook', time.time() - start_time, True)
            return None
    
    def get_balance(self) -> Optional[Portfolio]:
        """
        获取账户余额（使用缓存）
        
        Returns:
            投资组合数据或None
        """
        try:
            # 检查缓存
            with self.balance_lock:
                if (self.balance_cache and 
                    time.time() - self.balance_last_updated < self.balance_sync_interval):
                    return self.balance_cache
            
            # 缓存过期或不存在，重新获取
            start_time = time.time()
            balance_data = self.rest_client.get_balance()
            response_time = time.time() - start_time
            
            # 记录API调用统计
            self._record_api_call('get_balance', response_time, balance_data is not None)
            
            if balance_data:
                portfolio = Portfolio(
                    balances=balance_data,
                    timestamp=time.time()
                )
                # 更新缓存
                with self.balance_lock:
                    self.balance_cache = portfolio
                    self.balance_last_updated = time.time()
                
                # 记录余额更新
                self._record_balance_update()
                return portfolio
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取账户余额失败: {e}")
            self._record_error()
            return None
    
    def get_best_prices(self, inst_id: str) -> Optional[Dict[str, float]]:
        """
        获取最优买卖价格
        
        Args:
            inst_id: 产品ID
            
        Returns:
            最优价格信息或None
        """
        try:
            # 优先使用WebSocket数据
            if self.is_running and self.ws_manager.is_ws_connected():
                return self.ws_manager.get_best_prices(inst_id)
            
            # 使用REST数据
            orderbook = self.get_orderbook(inst_id)
            if orderbook:
                best_bid = orderbook.get_best_bid()
                best_ask = orderbook.get_best_ask()
                if best_bid and best_ask:
                    return {
                        'best_bid': best_bid,
                        'best_ask': best_ask,
                        'spread': best_ask - best_bid
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取{inst_id}最优价格失败: {e}")
            return None
    
    def add_data_callback(self, callback: Callable) -> None:
        """
        添加数据更新回调函数
        
        Args:
            callback: 回调函数
        """
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
            self.logger.info(f"添加数据更新回调: {callback.__name__}")
    
    def remove_data_callback(self, callback: Callable) -> None:
        """
        移除数据更新回调函数
        
        Args:
            callback: 回调函数
        """
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
            self.logger.info(f"移除数据更新回调: {callback.__name__}")
    
    async def _on_data_update(self, inst_id: str, action: str, bids: List, asks: List, server_timestamp: str = None):
        """
        处理数据更新事件（WebSocket更新时刷新缓存）
        
        Args:
            inst_id: 产品ID
            action: 操作类型
            bids: 买单数据
            asks: 卖单数据
            server_timestamp: 服务器时间戳
        """
        try:
            # 记录WebSocket消息接收
            self._record_websocket_message()
            
            # 解析服务器时间戳，转换为浮点数秒
            if server_timestamp:
                try:
                    # OKX返回的时间戳是毫秒级别的字符串
                    timestamp = float(server_timestamp) / 1000.0
                except (ValueError, TypeError):
                    self.logger.warning(f"无效的服务器时间戳: {server_timestamp}，使用本地时间")
                    timestamp = time.time()
            else:
                self.logger.debug(f"未收到服务器时间戳，使用本地时间")
                timestamp = time.time()
            
            # 创建OrderBook对象
            orderbook = OrderBook(
                symbol=inst_id,
                bids=[[float(bid[0]), float(bid[1])] for bid in bids],
                asks=[[float(ask[0]), float(ask[1])] for ask in asks],
                timestamp=timestamp
            )
            
            # 更新缓存
            with self.cache_lock:
                self.orderbook_cache[inst_id] = orderbook
            
            # 记录订单簿更新
            self._record_orderbook_update()
            
            # 通知所有回调函数
            for callback in self.data_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(inst_id, action, orderbook)
                    else:
                        callback(inst_id, action, orderbook)
                except Exception as e:
                    self.logger.error(f"数据更新回调执行失败: {e}")
                    self._record_error()
                    
        except Exception as e:
            self.logger.error(f"处理数据更新事件失败: {e}")
            self._record_error()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取数据采集器状态
        
        Returns:
            状态信息
        """
        return {
            'is_running': self.is_running,
            'ws_connected': self.ws_manager.is_ws_connected() if self.is_running else False,
            'subscribed_pairs': list(self.subscribed_pairs),
            'callback_count': len(self.data_callbacks)
        }
    
    def is_data_available(self, inst_id: str) -> bool:
        """
        检查指定交易对的数据是否可用
        
        Args:
            inst_id: 产品ID
            
        Returns:
            数据是否可用
        """
        return (
            self.is_running and 
            inst_id in self.subscribed_pairs and 
            self.ws_manager.get_orderbook(inst_id) is not None
        )
    
    async def add_trading_pair(self, inst_id: str) -> bool:
        """
        添加新的交易对订阅
        
        Args:
            inst_id: 产品ID
            
        Returns:
            添加是否成功
        """
        try:
            if not self.is_running:
                self.logger.warning("数据采集器未运行，无法添加交易对")
                return False
            
            if inst_id in self.subscribed_pairs:
                self.logger.info(f"交易对 {inst_id} 已订阅")
                return True
            
            # 订阅新的交易对
            if await self.ws_manager.subscribe_orderbooks([inst_id]):
                self.subscribed_pairs.add(inst_id)
                self.logger.info(f"成功添加交易对订阅: {inst_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"添加交易对订阅失败: {e}")
            return False
    
    def _is_data_fresh(self, timestamp: float) -> bool:
        """
        检查数据是否新鲜（数据有效性检查）
        
        Args:
            timestamp: 数据时间戳
            
        Returns:
            数据是否新鲜
        """
        return time.time() - timestamp < self.data_stale_threshold
    
    def _is_arbitrage_data_fresh(self, timestamp: float) -> bool:
        """
        检查数据是否足够新鲜用于套利计算（更严格的阈值）
        
        Args:
            timestamp: 数据时间戳
            
        Returns:
            数据是否足够新鲜用于套利计算
        """
        return time.time() - timestamp < self.arbitrage_data_threshold
    
    async def _balance_sync_loop(self):
        """
        定期同步账户余额机制
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.balance_sync_interval)
                if self.is_running:
                    await self._sync_balance()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"定期同步余额失败: {e}")
    
    async def _sync_balance(self):
        """
        同步账户余额
        """
        try:
            balance_data = self.rest_client.get_balance()
            if balance_data:
                portfolio = Portfolio(
                    balances=balance_data,
                    timestamp=time.time()
                )
                with self.balance_lock:
                    self.balance_cache = portfolio
                    self.balance_last_updated = time.time()
                self.logger.debug("账户余额同步成功")
            else:
                self.logger.warning("账户余额同步失败：无法获取数据")
        except Exception as e:
            self.logger.error(f"同步账户余额失败: {e}")
    
    async def _reconnect_monitor(self):
        """
        WebSocket断线自动重连监控
        """
        while self.is_running:
            try:
                await asyncio.sleep(5)  # 每5秒检查一次
                if self.is_running and not self.ws_manager.is_ws_connected():
                    self.logger.warning("WebSocket连接断开，尝试重连...")
                    self._record_websocket_error()
                    await self._attempt_reconnect()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"重连监控失败: {e}")
    
    async def _attempt_reconnect(self):
        """
        尝试重新连接WebSocket
        """
        try:
            # 重新连接WebSocket
            if await self.ws_manager.connect():
                # 重新订阅交易对
                if self.subscribed_pairs:
                    trading_pairs = list(self.subscribed_pairs)
                    if await self.ws_manager.subscribe_orderbooks(trading_pairs):
                        self.logger.info("WebSocket重连成功")
                        self._record_reconnection()
                    else:
                        self.logger.error("WebSocket重连失败：无法重新订阅")
                        self._record_websocket_error()
                else:
                    self.logger.info("WebSocket重连成功")
                    self._record_reconnection()
            else:
                self.logger.error("WebSocket重连失败")
                self._record_websocket_error()
        except Exception as e:
            self.logger.error(f"WebSocket重连异常: {e}")
            self._record_error()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息
        
        Returns:
            缓存统计信息
        """
        with self.cache_lock:
            orderbook_count = len(self.orderbook_cache)
            fresh_count = sum(1 for ob in self.orderbook_cache.values() 
                            if self._is_data_fresh(ob.timestamp))
            stale_count = orderbook_count - fresh_count
        
        with self.balance_lock:
            balance_age = time.time() - self.balance_last_updated if self.balance_last_updated > 0 else 0
            balance_fresh = balance_age < self.balance_sync_interval
        
        return {
            'orderbook_cache_count': orderbook_count,
            'fresh_orderbook_count': fresh_count,
            'stale_orderbook_count': stale_count,
            'balance_cache_exists': self.balance_cache is not None,
            'balance_age_seconds': balance_age,
            'balance_fresh': balance_fresh
        }
    
    def clear_stale_data(self):
        """
        清理过期数据
        """
        with self.cache_lock:
            stale_keys = [
                inst_id for inst_id, orderbook in self.orderbook_cache.items()
                if not self._is_data_fresh(orderbook.timestamp)
            ]
            for key in stale_keys:
                del self.orderbook_cache[key]
            
            if stale_keys:
                self.logger.info(f"清理了 {len(stale_keys)} 个过期的订单簿缓存")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            性能统计数据
        """
        with self.stats_lock:
            current_time = time.time()
            uptime = current_time - self.stats['start_time']
            
            # 计算速率
            api_stats = {}
            for api_name, data in self.stats['api_calls'].items():
                if data['count'] > 0:
                    avg_time = data['total_time'] / data['count']
                    error_rate = data['errors'] / data['count']
                else:
                    avg_time = 0
                    error_rate = 0
                
                api_stats[api_name] = {
                    'count': data['count'],
                    'avg_response_time': avg_time,
                    'error_rate': error_rate,
                    'errors': data['errors']
                }
            
            # WebSocket统计
            ws_stats = self.stats['websocket'].copy()
            if uptime > 0:
                ws_stats['msg_rate_per_sec'] = ws_stats['messages_received'] / uptime
            else:
                ws_stats['msg_rate_per_sec'] = 0
            
            # 缓存统计
            cache_stats = self.stats['cache'].copy()
            total_cache_requests = cache_stats['hits'] + cache_stats['misses']
            if total_cache_requests > 0:
                cache_stats['hit_rate'] = cache_stats['hits'] / total_cache_requests
            else:
                cache_stats['hit_rate'] = 0
            
            # 错误统计
            error_stats = self.stats['errors'].copy()
            if uptime > 0:
                error_stats['error_rate_per_min'] = error_stats['total'] / (uptime / 60)
            else:
                error_stats['error_rate_per_min'] = 0
            
            return {
                'uptime_seconds': uptime,
                'api_calls': api_stats,
                'websocket': ws_stats,
                'cache': cache_stats,
                'errors': error_stats,
                'timestamp': current_time
            }
    
    def _record_api_call(self, api_name: str, response_time: float, success: bool):
        """记录API调用统计"""
        with self.stats_lock:
            if api_name in self.stats['api_calls']:
                self.stats['api_calls'][api_name]['count'] += 1
                self.stats['api_calls'][api_name]['total_time'] += response_time
                if not success:
                    self.stats['api_calls'][api_name]['errors'] += 1
    
    def _record_websocket_message(self):
        """记录WebSocket消息接收"""
        with self.stats_lock:
            self.stats['websocket']['messages_received'] += 1
            self.stats['websocket']['last_message_time'] = time.time()
    
    def _record_cache_hit(self):
        """记录缓存命中"""
        with self.stats_lock:
            self.stats['cache']['hits'] += 1
    
    def _record_cache_miss(self):
        """记录缓存未命中"""
        with self.stats_lock:
            self.stats['cache']['misses'] += 1
    
    def _record_orderbook_update(self):
        """记录订单簿更新"""
        with self.stats_lock:
            self.stats['cache']['orderbook_updates'] += 1
    
    def _record_balance_update(self):
        """记录余额更新"""
        with self.stats_lock:
            self.stats['cache']['balance_updates'] += 1
    
    def _record_error(self):
        """记录错误"""
        with self.stats_lock:
            current_time = time.time()
            self.stats['errors']['total'] += 1
            self.stats['errors']['last_error_time'] = current_time
            
            # 重置每小时错误计数
            if current_time - self.error_count_reset_time > 3600:
                self.stats['errors']['last_hour'] = 0
                self.error_count_reset_time = current_time
            
            self.stats['errors']['last_hour'] += 1
    
    def _record_websocket_error(self):
        """记录WebSocket错误"""
        with self.stats_lock:
            self.stats['websocket']['connection_errors'] += 1
        self._record_error()
    
    def _record_reconnection(self):
        """记录重连"""
        with self.stats_lock:
            self.stats['websocket']['reconnections'] += 1
    
    async def _stats_logger_loop(self):
        """
        性能统计日志记录循环
        """
        while self.is_running:
            try:
                await asyncio.sleep(self.stats_log_interval)
                if self.is_running:
                    await self._log_performance_stats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"性能统计记录失败: {e}")
    
    async def _log_performance_stats(self):
        """
        记录性能统计信息
        """
        try:
            stats = self.get_stats()
            
            # 记录性能日志
            self.logger.info(f"性能统计 - 运行时间: {stats['uptime_seconds']:.1f}秒")
            
            # API调用统计
            for api_name, api_stats in stats['api_calls'].items():
                if api_stats['count'] > 0:
                    self.logger.info(f"API[{api_name}] - 调用: {api_stats['count']}次, "
                                   f"平均响应: {api_stats['avg_response_time']:.3f}s, "
                                   f"错误率: {api_stats['error_rate']:.2%}")
            
            # WebSocket统计
            ws_stats = stats['websocket']
            self.logger.info(f"WebSocket - 消息: {ws_stats['messages_received']}条, "
                           f"速率: {ws_stats['msg_rate_per_sec']:.1f}条/秒, "
                           f"错误: {ws_stats['connection_errors']}次, "
                           f"重连: {ws_stats['reconnections']}次")
            
            # 缓存统计
            cache_stats = stats['cache']
            self.logger.info(f"缓存 - 命中率: {cache_stats['hit_rate']:.2%}, "
                           f"订单簿更新: {cache_stats['orderbook_updates']}次, "
                           f"余额更新: {cache_stats['balance_updates']}次")
            
            # 错误统计
            error_stats = stats['errors']
            if error_stats['total'] > 0:
                self.logger.warning(f"错误统计 - 总计: {error_stats['total']}次, "
                                  f"最近1小时: {error_stats['last_hour']}次, "
                                  f"错误率: {error_stats['error_rate_per_min']:.2f}次/分钟")
            
        except Exception as e:
            self.logger.error(f"记录性能统计失败: {e}")