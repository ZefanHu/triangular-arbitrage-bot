"""
pytest配置文件和通用fixtures

提供测试所需的通用fixtures和配置
"""

import pytest
import asyncio
import logging
import os
import sys
import time
from unittest.mock import Mock, MagicMock
from typing import Dict, List, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



from core.okx_client import OKXClient
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.trade_executor import TradeExecutor
from core.risk_manager import RiskManager
from core.trading_controller import TradingController
from config.config_manager import ConfigManager
from models.arbitrage_path import ArbitrageOpportunity, ArbitragePath
from models.order_book import OrderBook
from models.portfolio import Portfolio


# pytest插件配置
def pytest_configure(config):
    """pytest配置钩子"""
    # 配置pytest标记
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "network: marks tests that require network connectivity"
    )
    config.addinivalue_line(
        "markers", "api: marks tests that require API access"
    )
    config.addinivalue_line(
        "markers", "trading: marks tests that involve trading operations"
    )
    
    # 创建报告目录
    os.makedirs("tests/reports", exist_ok=True)
    os.makedirs("tests/logs", exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('tests/logs/test.log'),
            logging.StreamHandler()
        ]
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    # 为集成测试添加标记
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "test_real" in item.name or "real_" in item.name:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.network)


# 事件循环fixtures
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_session():
    """异步测试会话"""
    # 会话级别的异步初始化
    yield
    # 清理


# 配置fixtures
@pytest.fixture(scope="session")
def test_config_path():
    """测试配置文件路径"""
    return os.path.join(os.path.dirname(__file__), "test_config.ini")


@pytest.fixture(scope="session")
def config_manager(test_config_path):
    """配置管理器fixture"""
    config = ConfigManager()
    config.config_file = test_config_path
    return config


@pytest.fixture(scope="session")
def trading_pairs():
    """测试交易对"""
    return ["BTC-USDT", "ETH-USDT", "ETH-BTC", "BTC-USDC", "ETH-USDC"]


# 客户端fixtures
@pytest.fixture(scope="session")
def okx_client():
    """真实OKX客户端"""
    return OKXClient()


@pytest.fixture
def mock_okx_client():
    """模拟OKX客户端"""
    client = Mock(spec=OKXClient)
    
    # 设置默认返回值
    client.get_balance.return_value = {
        "USDT": 10000.0,
        "BTC": 0.5,
        "ETH": 5.0,
        "BNB": 20.0
    }
    
    client.get_ticker.return_value = {
        "best_bid": 50000.0,
        "best_ask": 50100.0,
        "last_price": 50050.0
    }
    
    client.get_orderbook.return_value = {
        "data": [{
            "bids": [["50000.0", "1.0"], ["49900.0", "2.0"]],
            "asks": [["50100.0", "1.0"], ["50200.0", "2.0"]],
            "ts": str(int(time.time() * 1000))
        }]
    }
    
    client.place_order.return_value = "test_order_123"
    client.cancel_order.return_value = True
    client.get_order_status.return_value = {
        "state": "filled",
        "filled_size": 1.0,
        "avg_price": 50050.0
    }
    
    return client


# 核心组件fixtures
@pytest.fixture
def data_collector():
    """数据采集器fixture"""
    return DataCollector()


@pytest.fixture
def mock_data_collector():
    """模拟数据采集器"""
    collector = Mock(spec=DataCollector)
    collector.is_running = True
    collector.subscribed_pairs = set(["BTC-USDT", "ETH-USDT", "ETH-BTC"])
    
    # 模拟订单簿
    collector.get_orderbook.return_value = OrderBook(
        symbol="BTC-USDT",
        bids=[[50000.0, 1.0], [49900.0, 2.0]],
        asks=[[50100.0, 1.0], [50200.0, 2.0]],
        timestamp=time.time()
    )
    
    # 模拟余额
    collector.get_balance.return_value = Portfolio(
        balances={
            "USDT": 10000.0,
            "BTC": 0.5,
            "ETH": 5.0
        },
        timestamp=time.time()
    )
    
    return collector


@pytest.fixture
def arbitrage_engine(mock_data_collector):
    """套利引擎fixture"""
    return ArbitrageEngine(mock_data_collector)


@pytest.fixture
def trade_executor(mock_okx_client):
    """交易执行器fixture"""
    return TradeExecutor(mock_okx_client)


@pytest.fixture
def risk_manager(config_manager, mock_okx_client):
    """风险管理器fixture"""
    return RiskManager(config_manager, mock_okx_client)


@pytest.fixture
def trading_controller(config_manager):
    """交易控制器fixture"""
    return TradingController(config_manager)


# 数据fixtures
@pytest.fixture
def sample_balance():
    """样本余额数据"""
    return {
        "USDT": 10000.0,
        "BTC": 0.5,
        "ETH": 5.0,
        "BNB": 20.0,
        "USDC": 5000.0
    }


@pytest.fixture
def sample_orderbook():
    """样本订单簿数据"""
    return {
        "BTC-USDT": {
            "bids": [[50000.0, 1.0], [49900.0, 2.0], [49800.0, 3.0]],
            "asks": [[50100.0, 1.0], [50200.0, 2.0], [50300.0, 3.0]]
        },
        "ETH-USDT": {
            "bids": [[3000.0, 10.0], [2990.0, 20.0], [2980.0, 30.0]],
            "asks": [[3010.0, 10.0], [3020.0, 20.0], [3030.0, 30.0]]
        },
        "ETH-BTC": {
            "bids": [[0.060, 10.0], [0.059, 20.0], [0.058, 30.0]],
            "asks": [[0.061, 10.0], [0.062, 20.0], [0.063, 30.0]]
        }
    }


@pytest.fixture
def sample_opportunity():
    """样本套利机会"""
    path = ArbitragePath(
        path=["USDT", "BTC", "ETH", "USDT"]
    )
    return ArbitrageOpportunity(
        path=path,
        profit_rate=0.005,
        min_amount=100.0,
        timestamp=time.time()
    )


@pytest.fixture
def small_opportunity():
    """小额套利机会"""
    path = ArbitragePath(
        path=["USDT", "BTC", "ETH", "USDT"]
    )
    return ArbitrageOpportunity(
        path=path,
        profit_rate=0.003,
        min_amount=50.0,
        timestamp=time.time()
    )


@pytest.fixture
def expired_opportunity():
    """过期套利机会"""
    path = ArbitragePath(
        path=["USDT", "BTC", "ETH", "USDT"]
    )
    opportunity = ArbitrageOpportunity(
        path=path,
        profit_rate=0.005,
        min_amount=100.0,
        timestamp=time.time() - 3600  # 1小时前
    )
    return opportunity


# 工具函数fixtures
@pytest.fixture
def create_mock_orderbook():
    """创建模拟订单簿的工厂函数"""
    def _create_orderbook(symbol, bids, asks):
        return OrderBook(
            symbol=symbol,
            bids=bids,
            asks=asks,
            timestamp=time.time()
        )
    return _create_orderbook


@pytest.fixture
def create_mock_opportunity():
    """创建模拟套利机会的工厂函数"""
    def _create_opportunity(path_assets, profit_rate, min_amount=100.0):
        path = ArbitragePath(
            path=path_assets
        )
        return ArbitrageOpportunity(
            path=path,
            profit_rate=profit_rate,
            min_amount=min_amount,
            timestamp=time.time()
        )
    return _create_opportunity


# 测试环境fixtures
@pytest.fixture(scope="session")
def test_environment():
    """测试环境信息"""
    return {
        "api_mode": "demo",
        "trading_enabled": False,
        "small_amounts": True,
        "max_test_time": 300,
        "cleanup_required": True
    }


@pytest.fixture(autouse=True)
def setup_test_logging():
    """自动设置测试日志"""
    # 为每个测试设置日志
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建测试专用的日志处理器
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 避免重复添加处理器
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(handler)
    
    yield
    
    # 清理
    logger.removeHandler(handler)


# 异步测试helpers
@pytest.fixture
def async_test_timeout():
    """异步测试超时时间"""
    return 30.0


@pytest.fixture
async def async_cleanup():
    """异步测试清理"""
    cleanup_tasks = []
    
    def register_cleanup(coro):
        cleanup_tasks.append(coro)
    
    yield register_cleanup
    
    # 执行清理任务
    for task in cleanup_tasks:
        try:
            await task
        except Exception as e:
            logging.error(f"清理任务失败: {e}")


# 性能测试fixtures
@pytest.fixture
def performance_monitor():
    """性能监控器"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.operations = []
        
        def start(self):
            self.start_time = time.time()
        
        def end(self):
            self.end_time = time.time()
        
        def record_operation(self, name, duration):
            self.operations.append({"name": name, "duration": duration})
        
        def get_total_time(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0
        
        def get_average_operation_time(self):
            if self.operations:
                return sum(op["duration"] for op in self.operations) / len(self.operations)
            return 0
    
    return PerformanceMonitor()


# 集成测试标记
@pytest.fixture(autouse=True)
def skip_integration_tests(request):
    """跳过集成测试（如果需要）"""
    if request.node.get_closest_marker("integration"):
        if not request.config.getoption("--run-integration"):
            pytest.skip("集成测试被跳过，使用 --run-integration 来运行")


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="运行集成测试"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="运行慢速测试"
    )
    parser.addoption(
        "--api-mode",
        action="store",
        default="demo",
        help="API模式：demo 或 live"
    )


# 错误处理fixtures
@pytest.fixture
def error_handler():
    """错误处理器"""
    class ErrorHandler:
        def __init__(self):
            self.errors = []
        
        def handle_error(self, error, context=""):
            self.errors.append({
                "error": error,
                "context": context,
                "timestamp": time.time()
            })
            logging.error(f"测试错误 [{context}]: {error}")
        
        def get_errors(self):
            return self.errors
        
        def clear_errors(self):
            self.errors.clear()
    
    return ErrorHandler()


# 清理fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """测试后自动清理"""
    yield
    
    # 测试后清理
    try:
        # 清理日志处理器
        logging.getLogger().handlers.clear()
        
        # 重置模块状态
        # 这里可以添加更多清理逻辑
        
    except Exception as e:
        logging.error(f"测试清理失败: {e}")


if __name__ == "__main__":
    # 运行测试配置验证
    print("pytest配置验证...")
    print("配置文件加载成功")