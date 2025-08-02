# TaoLi 三角套利系统开发指南

## 目录导航

- [项目概述](#项目概述)
- [目录结构](#目录结构)
- [开发规范](#开发规范)
  - [文件命名规则](#文件命名规则)
  - [函数注释规范](#函数注释规范)
  - [代码风格约定](#代码风格约定)
- [核心模块说明](#核心模块说明)
  - [配置管理 (config)](#配置管理-config)
  - [核心业务 (core)](#核心业务-core)
  - [数据模型 (models)](#数据模型-models)
  - [工具模块 (utils)](#工具模块-utils)
- [配置文件说明](#配置文件说明)
- [开发注意事项](#开发注意事项)

## 项目概述

TaoLi是一个基于OKX交易所的三角套利系统，实现自动化的套利机会识别、风险控制和交易执行。

## 目录结构

```
taoli/
├── config/                 # 配置文件目录
│   ├── config_manager.py  # 配置管理器（单例模式）
│   ├── settings.ini       # 系统配置文件
│   └── secrets.ini        # API密钥配置（Git忽略）
├── core/                  # 核心业务逻辑
│   ├── arbitrage_engine.py    # 套利计算引擎
│   ├── data_collector.py      # 数据采集器
│   ├── okx_client.py         # OKX API客户端
│   ├── risk_manager.py       # 风险管理器
│   ├── trade_executor.py     # 交易执行器
│   ├── trading_controller.py # 交易控制器
│   └── websocket_manager.py  # WebSocket管理器
├── models/                # 数据模型
│   ├── arbitrage_path.py     # 套利路径模型
│   ├── order_book.py        # 订单簿模型
│   ├── portfolio.py         # 投资组合模型
│   └── trade.py             # 交易模型
├── utils/                 # 工具模块
│   ├── logger.py            # 日志配置
│   ├── performance_analyzer.py # 性能分析器
│   └── trade_logger.py      # 交易日志记录器
├── okex/                  # OKX官方API库
├── tests/                 # 测试代码
├── examples/              # 示例代码
└── main.py               # 程序入口
```

## 开发规范

### 文件命名规则

- Python文件：小写字母+下划线，如 `arbitrage_engine.py`
- 配置文件：小写字母+下划线，如 `settings.ini`
- 测试文件：`test_` 前缀，如 `test_models.py`

### 函数注释规范

使用标准的Python docstring格式：

```python
def calculate_profit(self, path: List[str], amount: float) -> float:
    """
    计算指定路径的套利利润
    
    Args:
        path: 套利路径，如 ['USDT', 'BTC', 'USDC', 'USDT']
        amount: 初始交易金额
        
    Returns:
        float: 预期利润率（扣除手续费后）
    """
```

### 代码风格约定

- 类名：大驼峰命名法 `ArbitrageEngine`
- 函数名/变量名：小写字母+下划线 `calculate_profit`
- 常量：大写字母+下划线 `MAX_RETRY_COUNT`
- 私有方法：单下划线前缀 `_validate_data`
- 使用类型注解提高代码可读性

## 核心模块说明

### 配置管理 (config)

#### ConfigManager
- 路径：`config/config_manager.py`
- 功能：单例模式的配置管理器，支持配置热更新
- 主要方法：
  - `get(section, option, fallback=None)`: 获取配置值
  - `reload()`: 重新加载配置文件
  - `get_trading_config()`: 获取交易配置

### 核心业务 (core)

#### ArbitrageEngine
- 路径：`core/arbitrage_engine.py`
- 功能：套利机会识别和计算
- 主要类：
  - `ArbitrageEngine`: 套利计算引擎
  - `ArbitrageOpportunity`: 套利机会数据类

#### DataCollector
- 路径：`core/data_collector.py`
- 功能：整合REST和WebSocket数据源
- 主要功能：
  - 维护订单簿缓存
  - 协调数据更新
  - 提供统一的数据访问接口

#### OKXClient
- 路径：`core/okx_client.py`
- 功能：封装OKX REST API调用
- 主要方法：
  - 账户余额查询
  - 订单下单/取消
  - 市场数据获取

#### RiskManager
- 路径：`core/risk_manager.py`
- 主要类：
  - `RiskManager`: 风险控制核心类
  - `RiskLevel`: 风险级别枚举
  - `RiskCheckResult`: 风险检查结果

#### TradeExecutor
- 路径：`core/trade_executor.py`
- 主要类：
  - `TradeExecutor`: 交易执行器
  - `TradeResult`: 交易结果
  - `ArbitrageRecord`: 套利记录
  - `BalanceCache`: 余额缓存

#### TradingController
- 路径：`core/trading_controller.py`
- 主要类：
  - `TradingController`: 主控制器
  - `TradingStatus`: 交易状态枚举
  - `TradingStats`: 交易统计数据类

#### WebSocketManager
- 路径：`core/websocket_manager.py`
- 功能：管理WebSocket连接和实时数据推送
- 主要方法：
  - 订单簿增量更新
  - 自动重连机制

### 数据模型 (models)

#### ArbitragePath
- 路径：`models/arbitrage_path.py`
- 类：`ArbitragePath`, `ArbitrageOpportunity`
- 功能：定义套利路径和机会

#### OrderBook
- 路径：`models/order_book.py`
- 类：`OrderBook`
- 功能：订单簿数据结构

#### Portfolio
- 路径：`models/portfolio.py`
- 类：`Portfolio`
- 功能：投资组合管理

#### Trade
- 路径：`models/trade.py`
- 类：`Trade`, `TradeStatus`
- 功能：交易数据模型

### 工具模块 (utils)

#### Logger
- 路径：`utils/logger.py`
- 功能：配置Rich美化的日志输出

#### PerformanceAnalyzer
- 路径：`utils/performance_analyzer.py`
- 类：`PerformanceAnalyzer`
- 功能：性能监控和分析

#### TradeLogger
- 路径：`utils/trade_logger.py`
- 主要类：
  - `TradeLogger`: 交易日志记录器
  - `TradeRecord`: 交易记录
  - `DailyStats`: 日统计
  - `PerformanceMetrics`: 性能指标

## 配置文件说明

### settings.ini
主配置文件

### secrets.ini
API密钥配置（不提交到Git）


## 开发注意事项

1. **配置管理**
   - 使用 `ConfigManager` 单例访问配置
   - 不要硬编码配置值
   - 敏感信息存放在 `secrets.ini`

2. **错误处理**
   - 所有API调用需要异常处理
   - 使用日志记录错误信息

3. **性能优化**
   - 使用WebSocket获取实时数据
   - 批量处理数据更新

4. **安全规范**
   - 不要在日志中记录敏感信息
   - API密钥使用环境变量或配置文件

5. **测试要求**
   - 新功能必须有对应的单元测试
   - 使用OKX模拟交易API获取数据
   - 保持测试覆盖率在80%以上