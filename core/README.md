# Core 模块技术文档

## 目录结构

```
core/
├── __init__.py                # 核心业务逻辑模块初始化
├── arbitrage_engine.py        # 套利计算引擎
├── data_collector.py          # 数据采集器
├── okx_client.py             # OKX交易所REST API客户端
├── risk_manager.py           # 风险管理模块
├── trade_executor.py         # 交易执行模块
├── trading_controller.py     # 交易控制器
└── websocket_manager.py      # WebSocket连接管理器
```

## 核心模块说明

### 1. arbitrage_engine.py - 套利计算引擎

**主要类：** `ArbitrageEngine`、`ArbitrageOpportunity`

**功能描述：**  
负责分析市场数据，识别和计算三角套利机会。支持多种配置格式，包括JSON格式的显式交易对配置。

**核心方法：**
- `find_opportunities() -> List[Dict]`
  - 功能：查找所有配置路径的套利机会
  - 返回：套利机会列表，包含路径、利润率、交易量等信息
  
- `calculate_arbitrage(path: List[str]) -> Optional[ArbitrageOpportunity]`
  - 功能：计算单条路径的套利机会
  - 参数：path - 交易路径，如 ['USDT', 'BTC', 'USDC', 'USDT']
  - 返回：套利机会信息，无套利机会则返回None

- `calculate_path_profit(path: List[str], amount: float) -> Tuple[float, float]`
  - 功能：计算指定路径和金额的利润
  - 参数：path - 交易路径，amount - 初始金额
  - 返回：(最终金额, 利润率) 元组

**使用示例：**
```python
# 初始化套利引擎
data_collector = DataCollector()
engine = ArbitrageEngine(data_collector)

# 查找套利机会
opportunities = engine.find_opportunities()
for opp in opportunities:
    print(f"路径: {opp['path']}, 利润率: {opp['profit_rate']:.4%}")
```

### 2. data_collector.py - 数据采集器

**主要类：** `DataCollector`

**功能描述：**  
整合REST和WebSocket数据源，提供统一的数据接口。REST用于账户数据，WebSocket用于实时市场数据。

**核心方法：**
- `async start(trading_pairs: List[str] = None) -> bool`
  - 功能：启动数据采集，建立WebSocket连接并订阅数据
  - 参数：trading_pairs - 要订阅的交易对列表
  - 返回：启动是否成功

- `get_orderbook(inst_id: str) -> Optional[OrderBook]`
  - 功能：获取订单簿数据，优先使用缓存
  - 参数：inst_id - 产品ID，如'BTC-USDT'
  - 返回：订单簿数据或None

- `get_balance() -> Optional[Portfolio]`
  - 功能：获取账户余额，使用缓存机制
  - 返回：投资组合数据或None

**使用示例：**
```python
# 初始化数据采集器
collector = DataCollector()

# 启动采集
await collector.start(['BTC-USDT', 'ETH-USDT'])

# 获取订单簿
orderbook = collector.get_orderbook('BTC-USDT')
balance = collector.get_balance()
```

### 3. okx_client.py - OKX交易所REST API客户端

**主要类：** `OKXClient`

**功能描述：**  
负责与OKX交易所进行通信，提供账户信息查询、市场数据获取、订单管理等功能。

**核心方法：**
- `get_balance() -> Optional[Dict[str, float]]`
  - 功能：获取账户余额信息
  - 返回：格式化的余额信息，如 {'USDT': 1000.0, 'BTC': 0.01}

- `get_orderbook(inst_id: str, size: str = "20") -> Optional[OrderBook]`
  - 功能：获取产品深度数据
  - 参数：inst_id - 产品ID，size - 深度档位数量
  - 返回：OrderBook实例

- `place_order(inst_id: str, side: str, order_type: str, size: str, price: str = None) -> Optional[str]`
  - 功能：下单
  - 参数：inst_id - 产品ID，side - 订单方向(buy/sell)，order_type - 订单类型，size - 委托数量，price - 委托价格
  - 返回：订单ID

**使用示例：**
```python
# 初始化客户端
client = OKXClient()

# 获取余额
balance = client.get_balance()

# 下单
order_id = client.place_order('BTC-USDT', 'buy', 'limit', '0.001', '50000')
```

### 4. risk_manager.py - 风险管理模块

**主要类：** `RiskManager`、`RiskCheckResult`

**功能描述：**  
负责管理交易风险，包括仓位限制、频率控制、资金管理等。

**核心方法：**
- `check_position_limit(asset: str, amount: float) -> RiskCheckResult`
  - 功能：检查仓位限制
  - 参数：asset - 资产类型，amount - 请求的交易数量
  - 返回：风险检查结果

- `validate_opportunity(opportunity: ArbitrageOpportunity, total_balance: float, requested_amount: float = None) -> RiskCheckResult`
  - 功能：验证套利机会是否符合风险要求
  - 参数：opportunity - 套利机会，total_balance - 总资产，requested_amount - 请求的交易金额
  - 返回：风险检查结果

- `calculate_position_size(opportunity: ArbitrageOpportunity, balance: Dict[str, float] = None) -> float`
  - 功能：计算合适的交易量
  - 参数：opportunity - 套利机会，balance - 当前余额
  - 返回：建议的交易金额

**使用示例：**
```python
# 初始化风险管理器
risk_manager = RiskManager(config_manager, okx_client)

# 检查仓位限制
result = risk_manager.check_position_limit('USDT', 1000.0)
if result.passed:
    print("仓位检查通过")
```

### 5. trade_executor.py - 交易执行模块

**主要类：** `TradeExecutor`、`BalanceCache`、`TradeResult`、`ArbitrageRecord`

**功能描述：**  
负责执行套利交易，包括下单、监控订单状态、处理超时等。

**核心方法：**
- `execute_arbitrage(opportunity: ArbitrageOpportunity, investment_amount: float) -> Dict[str, any]`
  - 功能：执行套利交易
  - 参数：opportunity - 套利机会，investment_amount - 投资金额
  - 返回：执行结果字典

- `_execute_single_trade(inst_id: str, side: str, size: float, price: float) -> TradeResult`
  - 功能：执行单笔交易
  - 参数：inst_id - 交易对ID，side - 交易方向，size - 交易数量，price - 交易价格
  - 返回：交易结果

**使用示例：**
```python
# 初始化交易执行器
executor = TradeExecutor(okx_client)

# 执行套利交易
result = executor.execute_arbitrage(opportunity, 1000.0)
if result['success']:
    print(f"套利成功，利润: {result['actual_profit']}")
```

### 6. trading_controller.py - 交易控制器

**主要类：** `TradingController`、`TradingStatus`、`TradingStats`

**功能描述：**  
负责整合所有模块，提供统一的交易控制接口。是系统的核心控制器。

**核心方法：**
- `async start() -> bool`
  - 功能：启动交易系统
  - 返回：启动是否成功

- `async stop() -> bool`
  - 功能：停止交易系统
  - 返回：停止是否成功

- `get_status() -> Dict`
  - 功能：获取交易系统状态
  - 返回：状态信息字典

- `get_stats() -> Dict`
  - 功能：获取交易统计信息
  - 返回：统计信息字典

**使用示例：**
```python
# 初始化交易控制器
controller = TradingController()

# 启动交易系统
await controller.start()

# 获取状态
status = controller.get_status()
stats = controller.get_stats()
```

### 7. websocket_manager.py - WebSocket连接管理器

**主要类：** `WebSocketManager`

**功能描述：**  
负责管理WebSocket连接，处理实时数据订阅和消息处理。支持自动重连和checksum校验。

**核心方法：**
- `async connect() -> bool`
  - 功能：建立WebSocket连接
  - 返回：连接是否成功

- `async subscribe_orderbooks(inst_ids: List[str]) -> bool`
  - 功能：订阅订单簿数据
  - 参数：inst_ids - 产品ID列表
  - 返回：订阅是否成功

- `get_orderbook(inst_id: str) -> Optional[Dict[str, Any]]`
  - 功能：获取当前订单簿数据
  - 参数：inst_id - 产品ID
  - 返回：订单簿数据或None

**使用示例：**
```python
# 初始化WebSocket管理器
ws_manager = WebSocketManager()

# 连接并订阅
await ws_manager.connect()
await ws_manager.subscribe_orderbooks(['BTC-USDT', 'ETH-USDT'])

# 获取数据
orderbook = ws_manager.get_orderbook('BTC-USDT')
```

## 模块关系图

```
TradingController (交易控制器)
├── DataCollector (数据采集器)
│   ├── OKXClient (REST API客户端)
│   └── WebSocketManager (WebSocket管理器)
├── ArbitrageEngine (套利引擎)
│   └── DataCollector (数据采集器)
├── TradeExecutor (交易执行器)
│   └── OKXClient (REST API客户端)
└── RiskManager (风险管理器)
    └── OKXClient (REST API客户端)
```

**依赖关系说明：**
1. `TradingController` 是系统的核心控制器，整合所有其他模块
2. `DataCollector` 整合 `OKXClient` 和 `WebSocketManager`，提供统一数据接口
3. `ArbitrageEngine` 依赖 `DataCollector` 获取市场数据进行套利计算
4. `TradeExecutor` 和 `RiskManager` 都依赖 `OKXClient` 进行交易和余额查询
5. `WebSocketManager` 是独立的WebSocket连接管理模块

## 使用指南

### 基本使用流程

1. **初始化系统**
```python
from config.config_manager import ConfigManager
from core.trading_controller import TradingController

# 创建配置管理器
config_manager = ConfigManager()

# 创建交易控制器
controller = TradingController(config_manager)
```

2. **启动交易系统**
```python
# 启动系统
success = await controller.start()
if success:
    print("交易系统启动成功")
```

3. **监控交易状态**
```python
# 获取系统状态
status = controller.get_status()
stats = controller.get_stats()

print(f"系统状态: {status['status']}")
print(f"交易统计: {stats}")
```

4. **停止系统**
```python
# 停止系统
await controller.stop()
```

### 单独使用模块

如果需要单独使用某个模块，可以按以下方式：

```python
# 单独使用OKX客户端
from core.okx_client import OKXClient
client = OKXClient()
balance = client.get_balance()

# 单独使用数据采集器
from core.data_collector import DataCollector
collector = DataCollector()
await collector.start(['BTC-USDT'])
orderbook = collector.get_orderbook('BTC-USDT')
```

### 注意事项

1. **配置文件**：确保 `secrets.ini` 文件包含正确的API凭据
2. **网络连接**：WebSocket连接需要稳定的网络环境
3. **风险控制**：系统包含多层风险控制，建议在测试环境先运行
4. **日志记录**：所有模块都包含详细的日志记录，便于调试和监控
5. **异步编程**：大部分核心功能使用异步编程，需要在async环境中运行

### 扩展开发

如果需要扩展功能，建议：

1. **新增交易所支持**：继承或参考 `OKXClient` 实现新的交易所客户端
2. **新增套利策略**：在 `ArbitrageEngine` 中添加新的套利算法
3. **自定义风险控制**：扩展 `RiskManager` 类添加新的风险检查规则
4. **数据存储**：可以扩展 `DataCollector` 添加数据持久化功能

### 性能优化建议

1. **缓存机制**：系统已实现多级缓存，避免重复API调用
2. **并发控制**：合理设置并发交易数量限制
3. **内存管理**：定期清理过期数据和缓存
4. **网络优化**：WebSocket断线重连机制保证数据连续性

## 故障排除

### 常见问题

1. **API连接失败**：检查网络连接和API凭据
2. **WebSocket断连**：系统有自动重连机制，检查网络稳定性
3. **交易失败**：检查余额、交易对有效性和风险限制
4. **数据延迟**：检查WebSocket连接状态和网络延迟

### 调试建议

1. 启用详细日志记录
2. 使用模拟盘环境测试
3. 监控系统资源使用情况
4. 检查配置文件正确性

---

*本文档基于代码分析生成，如有疑问请参考源代码注释或联系开发团队。*