import asyncio
import websockets
import json
import logging
import time
import zlib
from typing import Dict, Any, List, Optional, Callable
from config.config_manager import ConfigManager


def partial(res):
    """
    处理snapshot消息（全量数据）
    从websocket_example.py移植
    """
    data_obj = res['data'][0]
    bids = data_obj['bids']
    asks = data_obj['asks']
    instrument_id = res['arg']['instId']
    return bids, asks, instrument_id


def update_bids(res, bids_p):
    """
    处理增量bids数据更新
    从websocket_example.py移植
    """
    # 获取增量bids数据
    bids_u = res['data'][0]['bids']
    
    # bids合并
    for i in bids_u:
        bid_price = i[0]
        for j in bids_p:
            if bid_price == j[0]:
                if i[1] == '0':
                    bids_p.remove(j)
                    break
                else:
                    del j[1]
                    j.insert(1, i[1])
                    break
        else:
            if i[1] != "0":
                bids_p.append(i)
    else:
        bids_p.sort(key=lambda price: sort_num(price[0]), reverse=True)
    
    return bids_p


def update_asks(res, asks_p):
    """
    处理增量asks数据更新
    从websocket_example.py移植
    """
    # 获取增量asks数据
    asks_u = res['data'][0]['asks']
    
    # asks合并
    for i in asks_u:
        ask_price = i[0]
        for j in asks_p:
            if ask_price == j[0]:
                if i[1] == '0':
                    asks_p.remove(j)
                    break
                else:
                    del j[1]
                    j.insert(1, i[1])
                    break
        else:
            if i[1] != "0":
                asks_p.append(i)
    else:
        asks_p.sort(key=lambda price: sort_num(price[0]))
    
    return asks_p


def sort_num(n):
    """
    价格排序函数
    从websocket_example.py移植
    """
    if n.isdigit():
        return int(n)
    else:
        return float(n)


def check(bids, asks):
    """
    校验checksum
    从websocket_example.py移植
    """
    # 获取bid档str
    bids_l = []
    bid_l = []
    count_bid = 1
    while count_bid <= 25:
        if count_bid > len(bids):
            break
        bids_l.append(bids[count_bid-1])
        count_bid += 1
    for j in bids_l:
        str_bid = ':'.join(j[0 : 2])
        bid_l.append(str_bid)
    
    # 获取ask档str
    asks_l = []
    ask_l = []
    count_ask = 1
    while count_ask <= 25:
        if count_ask > len(asks):
            break
        asks_l.append(asks[count_ask-1])
        count_ask += 1
    for k in asks_l:
        str_ask = ':'.join(k[0 : 2])
        ask_l.append(str_ask)
    
    # 拼接str
    num = ''
    if len(bid_l) == len(ask_l):
        for m in range(len(bid_l)):
            num += bid_l[m] + ':' + ask_l[m] + ':'
    elif len(bid_l) > len(ask_l):
        # bid档比ask档多
        for n in range(len(ask_l)):
            num += bid_l[n] + ':' + ask_l[n] + ':'
        for l in range(len(ask_l), len(bid_l)):
            num += bid_l[l] + ':'
    elif len(bid_l) < len(ask_l):
        # ask档比bid档多
        for n in range(len(bid_l)):
            num += bid_l[n] + ':' + ask_l[n] + ':'
        for l in range(len(bid_l), len(ask_l)):
            num += ask_l[l] + ':'

    new_num = num[:-1]
    int_checksum = zlib.crc32(new_num.encode())
    fina = change(int_checksum)
    return fina


def change(num_old):
    """
    checksum变换函数
    从websocket_example.py移植
    """
    num = pow(2, 31) - 1
    if num_old > num:
        out = num_old - num * 2 - 2
    else:
        out = num_old
    return out


class WebSocketManager:
    """
    OKX WebSocket连接管理器
    
    负责管理WebSocket连接，处理实时数据订阅和消息处理。
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        初始化WebSocket管理器
        
        Args:
            callback: 消息处理回调函数
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        
        # 获取API凭据
        credentials = self.config_manager.get_api_credentials()
        if not credentials:
            raise ValueError("无法获取API凭据，请检查secrets.ini文件")
        
        self.api_key = credentials['api_key']
        self.secret_key = credentials['secret_key']
        self.passphrase = credentials['passphrase']
        self.flag = credentials['flag']
        
        # WebSocket连接URL
        if self.flag == '1':  # 模拟盘
            self.public_url = "wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999"
            self.private_url = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        else:  # 实盘
            self.public_url = "wss://ws.okx.com:8443/ws/v5/public"
            self.private_url = "wss://ws.okx.com:8443/ws/v5/private"
        
        # 连接状态
        self.ws_public = None
        self.ws_private = None
        self.is_connected = False
        self.subscribed_channels = []
        
        # 消息处理回调
        self.message_callback = callback
        
        # 订单簿数据存储
        self.orderbook_data = {}
        
        # 数据更新回调列表
        self.data_update_callbacks = []
        
        # 异步任务管理
        self.message_loop_task = None
        
        self.logger.info(f"WebSocket管理器初始化完成，使用{'模拟盘' if self.flag == '1' else '实盘'}")
    
    async def connect(self) -> bool:
        """
        建立WebSocket连接
        
        Returns:
            连接是否成功
        """
        try:
            self.logger.info(f"正在连接WebSocket: {self.public_url}")
            
            # 连接公共频道
            self.ws_public = await websockets.connect(self.public_url)
            self.is_connected = True
            
            self.logger.info("公共频道WebSocket连接成功")
            
            # 启动消息处理任务
            self.message_loop_task = asyncio.create_task(self._start_message_loop())
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """
        断开WebSocket连接
        
        Returns:
            断开是否成功
        """
        try:
            self.is_connected = False
            
            # 取消消息循环任务
            if self.message_loop_task and not self.message_loop_task.done():
                self.message_loop_task.cancel()
                try:
                    await self.message_loop_task
                except asyncio.CancelledError:
                    self.logger.debug("消息循环任务已取消")
                except Exception as e:
                    self.logger.warning(f"取消消息循环任务时出错: {e}")
                finally:
                    self.message_loop_task = None
            
            if self.ws_public:
                await self.ws_public.close()
                self.ws_public = None
                self.logger.info("公共频道WebSocket连接已关闭")
            
            if self.ws_private:
                await self.ws_private.close()
                self.ws_private = None
                self.logger.info("私有频道WebSocket连接已关闭")
            
            self.subscribed_channels.clear()
            self.orderbook_data.clear()
            
            return True
            
        except Exception as e:
            self.logger.error(f"WebSocket断开失败: {e}")
            return False
    
    async def subscribe_orderbooks(self, inst_ids: List[str]) -> bool:
        """
        订阅订单簿数据
        
        Args:
            inst_ids: 产品ID列表，如['BTC-USDT', 'ETH-USDT']
            
        Returns:
            订阅是否成功
        """
        try:
            if not self.is_connected or not self.ws_public:
                self.logger.error("WebSocket未连接，无法订阅")
                return False
            
            # 构建订阅参数，参考websocket_example.py
            channels = []
            for inst_id in inst_ids:
                channels.append({
                    "channel": "books",
                    "instId": inst_id
                })
            
            # 发送订阅请求
            sub_param = {"op": "subscribe", "args": channels}
            sub_str = json.dumps(sub_param)
            
            await self.ws_public.send(sub_str)
            self.logger.info(f"发送订阅请求: {sub_str}")
            
            # 记录订阅的频道
            self.subscribed_channels.extend(channels)
            
            return True
            
        except Exception as e:
            self.logger.error(f"订阅订单簿失败: {e}")
            return False
    
    async def _start_message_loop(self):
        """
        启动消息处理循环，参考websocket_example.py的subscribe_without_login
        """
        try:
            while self.is_connected:
                try:
                    if not self.ws_public:
                        break
                        
                    # 接收消息，超时时间25秒
                    try:
                        message = await asyncio.wait_for(self.ws_public.recv(), timeout=25)
                        await self._handle_message(message)
                    except asyncio.TimeoutError:
                        # 超时时发送ping保持连接
                        try:
                            await self.ws_public.send('ping')
                            pong_message = await self.ws_public.recv()
                            self.logger.debug(f"收到pong: {pong_message}")
                            continue
                        except Exception as ping_error:
                            self.logger.error(f"ping失败: {ping_error}")
                            break
                    except websockets.exceptions.ConnectionClosed:
                        self.logger.warning("WebSocket连接关闭，正在重连...")
                        await self._reconnect()
                        break
                        
                except Exception as e:
                    self.logger.error(f"消息循环中发生错误: {e}")
                    await self._reconnect()
                    break
        except asyncio.CancelledError:
            self.logger.debug("消息循环任务被取消")
            raise
        except Exception as e:
            self.logger.error(f"消息循环异常: {e}")
        finally:
            # 确保任务清理
            self.logger.debug("消息循环任务结束，清理资源")
            if hasattr(self, 'ws_public') and self.ws_public:
                try:
                    await self.ws_public.close()
                except Exception as close_error:
                    self.logger.debug(f"关闭WebSocket连接时出错: {close_error}")
            self.is_connected = False
    
    async def _handle_message(self, message: str):
        """
        处理接收到的消息
        
        Args:
            message: WebSocket消息
        """
        try:
            # 跳过ping/pong消息
            if message == 'pong':
                return
            
            self.logger.debug(f"收到消息: {message}")
            
            # 解析JSON消息
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                self.logger.warning(f"无法解析JSON消息: {message}")
                return
            
            # 处理事件消息（订阅确认等）
            if 'event' in data:
                if data['event'] == 'subscribe':
                    self.logger.info(f"订阅成功: {data.get('arg', {})}")
                elif data['event'] == 'error':
                    self.logger.error(f"WebSocket错误: {data}")
                return
            
            # 处理数据消息
            if 'data' in data and 'arg' in data:
                await self._process_orderbook_data(data)
            
            # 调用用户定义的回调函数
            if self.message_callback:
                try:
                    if asyncio.iscoroutinefunction(self.message_callback):
                        await self.message_callback(data)
                    else:
                        self.message_callback(data)
                except Exception as callback_error:
                    self.logger.error(f"回调函数执行失败: {callback_error}")
                
        except Exception as e:
            self.logger.error(f"处理消息时发生错误: {e}")
    
    async def _process_orderbook_data(self, data: Dict[str, Any]):
        """
        处理订单簿数据，使用websocket_example.py的proven逻辑
        
        Args:
            data: 解析后的消息数据
        """
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel', '')
            inst_id = arg.get('instId', '')
            
            # 处理订单簿数据
            if channel == 'books' and 'books5' not in channel and inst_id:
                action = data.get('action', '')
                
                if action == 'snapshot':
                    # 处理全量数据
                    bids_p, asks_p, instrument_id = partial(data)
                    
                    # 存储全量数据
                    self.orderbook_data[inst_id] = {
                        'bids_p': bids_p,
                        'asks_p': asks_p,
                        'instrument_id': instrument_id,
                        'action': action,
                        'timestamp': data.get('data', [{}])[0].get('ts', '')
                    }
                    
                    # 校验checksum
                    checksum = data['data'][0].get('checksum')
                    if checksum:
                        check_num = check(bids_p, asks_p)
                        if check_num == checksum:
                            self.logger.debug(f"{inst_id} checksum校验通过")
                        else:
                            self.logger.warning(f"{inst_id} checksum校验失败，需要重新订阅")
                    
                    # 通知回调函数
                    await self._notify_data_callbacks(inst_id, action, bids_p, asks_p)
                    
                    self.logger.debug(f"更新{inst_id}订单簿全量数据: 买单:{len(bids_p)}个, 卖单:{len(asks_p)}个")
                    
                elif action == 'update':
                    # 处理增量数据
                    if inst_id in self.orderbook_data:
                        # 获取当前全量数据
                        current_data = self.orderbook_data[inst_id]
                        bids_p = current_data['bids_p']
                        asks_p = current_data['asks_p']
                        
                        # 合并增量数据
                        bids_p = update_bids(data, bids_p)
                        asks_p = update_asks(data, asks_p)
                        
                        # 更新存储的数据
                        current_data['bids_p'] = bids_p
                        current_data['asks_p'] = asks_p
                        current_data['action'] = action
                        current_data['timestamp'] = data.get('data', [{}])[0].get('ts', '')
                        
                        # 校验checksum
                        checksum = data['data'][0].get('checksum')
                        if checksum:
                            check_num = check(bids_p, asks_p)
                            if check_num == checksum:
                                self.logger.debug(f"{inst_id} checksum校验通过")
                            else:
                                self.logger.warning(f"{inst_id} checksum校验失败，需要重新订阅")
                        
                        # 通知回调函数
                        await self._notify_data_callbacks(inst_id, action, bids_p, asks_p)
                        
                        self.logger.debug(f"更新{inst_id}订单簿增量数据: 买单:{len(bids_p)}个, 卖单:{len(asks_p)}个")
                    else:
                        self.logger.warning(f"收到{inst_id}的增量数据，但没有全量数据基础")
                
        except Exception as e:
            self.logger.error(f"处理订单簿数据时发生错误: {e}")
    
    async def _reconnect(self):
        """
        重新连接WebSocket
        """
        try:
            self.logger.info("连接断开，正在重连...")
            
            # 先断开现有连接
            await self.disconnect()
            
            # 等待一段时间后重连
            await asyncio.sleep(2)
            
            # 重新连接
            if await self.connect():
                # 重新订阅之前的频道
                if self.subscribed_channels:
                    inst_ids = [ch.get('instId') for ch in self.subscribed_channels if ch.get('instId')]
                    if inst_ids:
                        await asyncio.sleep(1)  # 等待连接稳定
                        await self.subscribe_orderbooks(inst_ids)
                
                self.logger.info("WebSocket重连成功")
            else:
                self.logger.error("WebSocket重连失败")
                
        except Exception as e:
            self.logger.error(f"重连时发生错误: {e}")
    
    def get_orderbook(self, inst_id: str) -> Optional[Dict[str, Any]]:
        """
        获取当前订单簿数据
        
        Args:
            inst_id: 产品ID
            
        Returns:
            订单簿数据或None
        """
        data = self.orderbook_data.get(inst_id)
        if data:
            return {
                'bids': [[float(bid[0]), float(bid[1])] for bid in data.get('bids_p', [])],
                'asks': [[float(ask[0]), float(ask[1])] for ask in data.get('asks_p', [])],
                'timestamp': data.get('timestamp', ''),
                'action': data.get('action', '')
            }
        return None
    
    def get_best_prices(self, inst_id: str) -> Optional[Dict[str, float]]:
        """
        获取最优买卖价格
        
        Args:
            inst_id: 产品ID
            
        Returns:
            最优价格信息或None
        """
        data = self.orderbook_data.get(inst_id)
        if not data:
            return None
        
        try:
            bids_p = data.get('bids_p', [])
            asks_p = data.get('asks_p', [])
            
            best_bid = float(bids_p[0][0]) if bids_p else 0
            best_ask = float(asks_p[0][0]) if asks_p else 0
            
            return {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread': best_ask - best_bid if best_ask > 0 and best_bid > 0 else 0
            }
        except (IndexError, KeyError, ValueError):
            return None
    
    def is_ws_connected(self) -> bool:
        """
        检查WebSocket连接状态
        
        Returns:
            是否已连接
        """
        return self.is_connected and self.ws_public is not None
    
    def add_data_callback(self, callback: Callable):
        """
        添加数据更新回调函数
        
        Args:
            callback: 回调函数，接收参数 (inst_id, action, bids, asks)
        """
        if callback not in self.data_update_callbacks:
            self.data_update_callbacks.append(callback)
            self.logger.info(f"添加数据更新回调函数: {callback.__name__}")
    
    def remove_data_callback(self, callback: Callable):
        """
        移除数据更新回调函数
        
        Args:
            callback: 要移除的回调函数
        """
        if callback in self.data_update_callbacks:
            self.data_update_callbacks.remove(callback)
            self.logger.info(f"移除数据更新回调函数: {callback.__name__}")
    
    async def _notify_data_callbacks(self, inst_id: str, action: str, bids: List, asks: List):
        """
        通知所有数据更新回调函数
        
        Args:
            inst_id: 产品ID
            action: 操作类型 (snapshot/update)
            bids: 买单数据
            asks: 卖单数据
        """
        for callback in self.data_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(inst_id, action, bids, asks)
                else:
                    callback(inst_id, action, bids, asks)
            except Exception as e:
                self.logger.error(f"数据更新回调函数执行失败: {e}")