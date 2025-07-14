"""
数据层集成测试

使用真实的模拟盘API进行测试，验证：
1. REST API连接和数据获取
2. WebSocket连接和数据接收
3. 数据采集器的同步和缓存机制
"""

import asyncio
import unittest
import logging
import time
from unittest.mock import patch, Mock
from core.okx_client import OKXClient
from core.websocket_manager import WebSocketManager
from core.data_collector import DataCollector
from models.order_book import OrderBook
from models.portfolio import Portfolio


# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDataIntegration(unittest.TestCase):
    """数据层集成测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.test_pairs = ['BTC-USDT', 'ETH-USDT']
        self.timeout = 30  # 30秒超时
        
    def tearDown(self):
        """测试后清理"""
        pass


class TestRESTAPIConnection(TestDataIntegration):
    """REST API连接测试"""
    
    def setUp(self):
        super().setUp()
        self.rest_client = OKXClient()
    
    def test_rest_get_balance(self):
        """测试获取余额"""
        logger.info("测试REST API获取余额...")
        
        # 获取账户余额
        balance = self.rest_client.get_balance()
        
        # 验证返回结果
        self.assertIsNotNone(balance, "余额数据不应为None")
        self.assertIsInstance(balance, dict, "余额应为字典格式")
        
        # 验证包含主要币种
        expected_currencies = ['USDT', 'USDC', 'BTC']
        for currency in expected_currencies:
            self.assertIn(currency, balance, f"余额应包含{currency}")
            self.assertIsInstance(balance[currency], (int, float), f"{currency}余额应为数字")
            self.assertGreaterEqual(balance[currency], 0, f"{currency}余额应大于等于0")
        
        logger.info(f"余额测试通过: {balance}")
    
    def test_rest_get_orderbook(self):
        """测试获取订单簿"""
        logger.info("测试REST API获取订单簿...")
        
        for pair in self.test_pairs:
            with self.subTest(pair=pair):
                # 获取订单簿
                orderbook = self.rest_client.get_orderbook(pair)
                
                # 验证返回结果
                self.assertIsNotNone(orderbook, f"{pair}订单簿数据不应为None")
                self.assertIsInstance(orderbook, OrderBook, "应返回OrderBook对象")
                
                # 验证基本属性
                self.assertEqual(orderbook.symbol, pair, "交易对应匹配")
                self.assertGreater(orderbook.timestamp, 0, "时间戳应大于0")
                
                # 验证数据格式
                bids = orderbook.bids
                asks = orderbook.asks
                
                self.assertIsInstance(bids, list, "bids应为列表")
                self.assertIsInstance(asks, list, "asks应为列表")
                self.assertGreater(len(bids), 0, "bids不应为空")
                self.assertGreater(len(asks), 0, "asks不应为空")
                
                # 验证价格档位格式
                for bid in bids[:5]:  # 检查前5档
                    self.assertEqual(len(bid), 2, "bid档位应包含2个字段 [price, size]")
                    self.assertIsInstance(bid[0], float, "bid价格应为float")
                    self.assertIsInstance(bid[1], float, "bid数量应为float")
                    self.assertGreater(bid[0], 0, "bid价格应大于0")
                    self.assertGreater(bid[1], 0, "bid数量应大于0")
                
                for ask in asks[:5]:  # 检查前5档
                    self.assertEqual(len(ask), 2, "ask档位应包含2个字段 [price, size]")
                    self.assertIsInstance(ask[0], float, "ask价格应为float")
                    self.assertIsInstance(ask[1], float, "ask数量应为float")
                    self.assertGreater(ask[0], 0, "ask价格应大于0")
                    self.assertGreater(ask[1], 0, "ask数量应大于0")
                
                # 验证价格排序
                bid_prices = [bid[0] for bid in bids[:5]]
                ask_prices = [ask[0] for ask in asks[:5]]
                
                self.assertEqual(bid_prices, sorted(bid_prices, reverse=True), 
                               "bid价格应按降序排列")
                self.assertEqual(ask_prices, sorted(ask_prices), 
                               "ask价格应按升序排列")
                
                # 验证OrderBook方法
                self.assertIsNotNone(orderbook.get_best_bid(), "应能获取最优买价")
                self.assertIsNotNone(orderbook.get_best_ask(), "应能获取最优卖价")
                self.assertIsNotNone(orderbook.get_spread(), "应能获取价差")
                self.assertIsNotNone(orderbook.get_mid_price(), "应能获取中间价")
                self.assertTrue(orderbook.is_valid(), "订单簿应有效")
                
                logger.info(f"{pair}订单簿测试通过，买一价: {orderbook.get_best_bid()}, 卖一价: {orderbook.get_best_ask()}")


class TestWebSocketConnection(TestDataIntegration):
    """WebSocket连接测试"""
    
    def setUp(self):
        super().setUp()
        self.ws_manager = WebSocketManager()
        self.received_data = []
        self.data_event = asyncio.Event()
    
    def tearDown(self):
        super().tearDown()
        # 清理WebSocket连接
        asyncio.run(self.ws_manager.disconnect())
    
    async def data_callback(self, inst_id, action, bids, asks):
        """数据接收回调"""
        self.received_data.append({
            'inst_id': inst_id,
            'action': action,
            'bids': bids,
            'asks': asks,
            'timestamp': time.time()
        })
        self.data_event.set()
    
    def test_websocket_connection(self):
        """测试WebSocket连接"""
        logger.info("测试WebSocket连接...")
        
        async def test_connection():
            # 连接WebSocket
            connected = await self.ws_manager.connect()
            self.assertTrue(connected, "WebSocket连接应成功")
            self.assertTrue(self.ws_manager.is_ws_connected(), "WebSocket应处于连接状态")
            
            # 断开连接
            disconnected = await self.ws_manager.disconnect()
            self.assertTrue(disconnected, "WebSocket断开应成功")
            self.assertFalse(self.ws_manager.is_ws_connected(), "WebSocket应处于断开状态")
        
        asyncio.run(test_connection())
        logger.info("WebSocket连接测试通过")
    
    def test_websocket_subscription_and_data_receiving(self):
        """测试WebSocket订阅和数据接收"""
        logger.info("测试WebSocket订阅和数据接收...")
        
        async def test_subscription():
            # 添加数据回调
            self.ws_manager.add_data_callback(self.data_callback)
            
            # 连接WebSocket
            connected = await self.ws_manager.connect()
            self.assertTrue(connected, "WebSocket连接应成功")
            
            # 订阅订单簿
            subscribed = await self.ws_manager.subscribe_orderbooks(self.test_pairs)
            self.assertTrue(subscribed, "订阅应成功")
            
            # 等待数据接收
            logger.info("等待数据接收...")
            try:
                await asyncio.wait_for(self.data_event.wait(), timeout=self.timeout)
            except asyncio.TimeoutError:
                self.fail("在指定时间内未收到数据")
            
            # 验证接收到的数据
            self.assertGreater(len(self.received_data), 0, "应收到数据")
            
            data = self.received_data[0]
            self.assertIn('inst_id', data, "数据应包含inst_id")
            self.assertIn('action', data, "数据应包含action")
            self.assertIn('bids', data, "数据应包含bids")
            self.assertIn('asks', data, "数据应包含asks")
            
            # 验证数据格式
            bids = data['bids']
            asks = data['asks']
            
            self.assertIsInstance(bids, list, "bids应为列表")
            self.assertIsInstance(asks, list, "asks应为列表")
            self.assertGreater(len(bids), 0, "bids不应为空")
            self.assertGreater(len(asks), 0, "asks不应为空")
            
            logger.info(f"接收到数据: {data['inst_id']}, action: {data['action']}")
            
            # 等待更多数据以测试持续接收
            await asyncio.sleep(5)
            self.assertGreater(len(self.received_data), 1, "应持续接收数据")
        
        asyncio.run(test_subscription())
        logger.info("WebSocket订阅和数据接收测试通过")
    
    def test_websocket_reconnection(self):
        """测试WebSocket断线重连"""
        logger.info("测试WebSocket断线重连...")
        
        async def test_reconnection():
            # 连接WebSocket
            connected = await self.ws_manager.connect()
            self.assertTrue(connected, "WebSocket连接应成功")
            
            # 订阅数据
            subscribed = await self.ws_manager.subscribe_orderbooks(self.test_pairs)
            self.assertTrue(subscribed, "订阅应成功")
            
            # 模拟断线（直接关闭WebSocket）
            if self.ws_manager.ws_public:
                await self.ws_manager.ws_public.close()
            
            # 等待重连逻辑检测到断线
            await asyncio.sleep(2)
            
            # 验证连接状态
            self.assertFalse(self.ws_manager.is_ws_connected(), "WebSocket应检测到断线")
            
            logger.info("WebSocket断线重连测试完成（注意：实际重连由DataCollector处理）")
        
        asyncio.run(test_reconnection())


class TestDataCollector(TestDataIntegration):
    """数据采集器测试"""
    
    def setUp(self):
        super().setUp()
        self.data_collector = DataCollector()
        self.received_updates = []
    
    def tearDown(self):
        super().tearDown()
        # 清理数据采集器
        asyncio.run(self.data_collector.stop())
    
    async def update_callback(self, inst_id, action, orderbook):
        """数据更新回调"""
        self.received_updates.append({
            'inst_id': inst_id,
            'action': action,
            'orderbook': orderbook
        })
    
    def test_data_collector_start_stop(self):
        """测试数据采集器启动和停止"""
        logger.info("测试数据采集器启动和停止...")
        
        async def test_start_stop():
            # 启动数据采集器
            started = await self.data_collector.start(self.test_pairs)
            self.assertTrue(started, "数据采集器启动应成功")
            self.assertTrue(self.data_collector.is_running, "数据采集器应处于运行状态")
            
            # 检查状态
            status = self.data_collector.get_status()
            self.assertTrue(status['is_running'], "状态应显示运行中")
            self.assertTrue(status['ws_connected'], "WebSocket应连接")
            self.assertEqual(set(status['subscribed_pairs']), set(self.test_pairs), 
                           "订阅的交易对应匹配")
            
            # 停止数据采集器
            stopped = await self.data_collector.stop()
            self.assertTrue(stopped, "数据采集器停止应成功")
            self.assertFalse(self.data_collector.is_running, "数据采集器应停止运行")
        
        asyncio.run(test_start_stop())
        logger.info("数据采集器启动停止测试通过")
    
    def test_data_collector_sync_mechanism(self):
        """测试数据采集器同步机制"""
        logger.info("测试数据采集器同步机制...")
        
        async def test_sync():
            # 添加更新回调
            self.data_collector.add_data_callback(self.update_callback)
            
            # 启动数据采集器
            started = await self.data_collector.start(self.test_pairs)
            self.assertTrue(started, "数据采集器启动应成功")
            
            # 等待数据同步
            await asyncio.sleep(10)
            
            # 测试获取余额
            portfolio = self.data_collector.get_balance()
            self.assertIsNotNone(portfolio, "应能获取到余额")
            self.assertIsInstance(portfolio, Portfolio, "应返回Portfolio对象")
            
            # 测试获取订单簿
            for pair in self.test_pairs:
                orderbook = self.data_collector.get_orderbook(pair)
                self.assertIsNotNone(orderbook, f"应能获取到{pair}的订单簿")
                self.assertIsInstance(orderbook, OrderBook, "应返回OrderBook对象")
                self.assertEqual(orderbook.symbol, pair, "交易对应匹配")
                self.assertTrue(orderbook.is_valid(), "订单簿数据应有效")
                
                # 测试最优价格
                best_prices = self.data_collector.get_best_prices(pair)
                self.assertIsNotNone(best_prices, f"应能获取到{pair}的最优价格")
                self.assertIn('best_bid', best_prices, "应包含最优买价")
                self.assertIn('best_ask', best_prices, "应包含最优卖价")
                self.assertIn('spread', best_prices, "应包含价差")
                
                logger.info(f"{pair}最优价格: {best_prices}")
            
            # 验证数据更新回调
            self.assertGreater(len(self.received_updates), 0, "应收到数据更新")
            
            update = self.received_updates[0]
            self.assertIn(update['inst_id'], self.test_pairs, "更新的交易对应在订阅列表中")
            self.assertIsInstance(update['orderbook'], OrderBook, "更新应包含OrderBook对象")
        
        asyncio.run(test_sync())
        logger.info("数据采集器同步机制测试通过")
    
    def test_data_collector_cache_mechanism(self):
        """测试数据采集器缓存机制"""
        logger.info("测试数据采集器缓存机制...")
        
        async def test_cache():
            # 启动数据采集器
            started = await self.data_collector.start(self.test_pairs)
            self.assertTrue(started, "数据采集器启动应成功")
            
            # 等待数据填充缓存
            await asyncio.sleep(10)
            
            # 获取缓存信息
            cache_info = self.data_collector.get_cache_info()
            self.assertIsInstance(cache_info, dict, "缓存信息应为字典")
            self.assertIn('orderbook_cache_count', cache_info, "应包含订单簿缓存数量")
            self.assertIn('fresh_orderbook_count', cache_info, "应包含新鲜订单簿数量")
            self.assertIn('balance_cache_exists', cache_info, "应包含余额缓存状态")
            
            logger.info(f"缓存信息: {cache_info}")
            
            # 测试缓存效果
            start_time = time.time()
            for _ in range(5):
                for pair in self.test_pairs:
                    orderbook = self.data_collector.get_orderbook(pair)
                    self.assertIsNotNone(orderbook, f"应能从缓存获取{pair}订单簿")
            end_time = time.time()
            
            cache_time = end_time - start_time
            self.assertLess(cache_time, 1.0, "缓存访问应很快")
            
            logger.info(f"缓存访问耗时: {cache_time:.3f}秒")
            
            # 测试数据新鲜度
            for pair in self.test_pairs:
                orderbook = self.data_collector.get_orderbook(pair)
                if orderbook:
                    data_age = time.time() - orderbook.timestamp
                    self.assertLess(data_age, 30, f"{pair}数据应相对新鲜")
                    
            # 测试清理过期数据
            self.data_collector.clear_stale_data()
            cache_info_after = self.data_collector.get_cache_info()
            logger.info(f"清理后缓存信息: {cache_info_after}")
        
        asyncio.run(test_cache())
        logger.info("数据采集器缓存机制测试通过")
    
    def test_data_collector_balance_sync(self):
        """测试余额同步机制"""
        logger.info("测试余额同步机制...")
        
        async def test_balance_sync():
            # 启动数据采集器
            started = await self.data_collector.start(self.test_pairs)
            self.assertTrue(started, "数据采集器启动应成功")
            
            # 立即获取余额
            portfolio1 = self.data_collector.get_balance()
            self.assertIsNotNone(portfolio1, "应能获取到初始余额")
            
            # 再次获取余额（应从缓存）
            portfolio2 = self.data_collector.get_balance()
            self.assertIsNotNone(portfolio2, "应能获取到缓存余额")
            
            # 验证缓存效果
            self.assertEqual(portfolio1.timestamp, portfolio2.timestamp, 
                           "短时间内应返回相同的缓存数据")
            
            # 等待超过同步间隔（模拟）
            self.data_collector.balance_sync_interval = 2  # 设置为2秒
            await asyncio.sleep(3)
            
            # 再次获取余额（应重新同步）
            portfolio3 = self.data_collector.get_balance()
            self.assertIsNotNone(portfolio3, "应能获取到更新后的余额")
            
            logger.info("余额同步机制测试通过")
        
        asyncio.run(test_balance_sync())


class TestDataIntegrationSuite(unittest.TestSuite):
    """数据集成测试套件"""
    
    def __init__(self):
        super().__init__()
        
        # 添加REST API测试
        self.addTest(TestRESTAPIConnection('test_rest_get_balance'))
        self.addTest(TestRESTAPIConnection('test_rest_get_orderbook'))
        
        # 添加WebSocket测试
        self.addTest(TestWebSocketConnection('test_websocket_connection'))
        self.addTest(TestWebSocketConnection('test_websocket_subscription_and_data_receiving'))
        self.addTest(TestWebSocketConnection('test_websocket_reconnection'))
        
        # 添加数据采集器测试
        self.addTest(TestDataCollector('test_data_collector_start_stop'))
        self.addTest(TestDataCollector('test_data_collector_sync_mechanism'))
        self.addTest(TestDataCollector('test_data_collector_cache_mechanism'))
        self.addTest(TestDataCollector('test_data_collector_balance_sync'))


def run_integration_tests():
    """运行集成测试"""
    logger.info("开始运行数据层集成测试...")
    
    # 创建测试套件
    suite = TestDataIntegrationSuite()
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        logger.info("所有集成测试通过！")
        return True
    else:
        logger.error(f"测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        return False


if __name__ == '__main__':
    # 运行集成测试
    success = run_integration_tests()
    exit(0 if success else 1)