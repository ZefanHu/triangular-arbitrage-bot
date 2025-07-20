# Models 模块文档

本模块包含加密货币套利交易系统的核心数据模型，定义了应用程序中用于表示交易路径、套利机会、市场数据、投资组合和单笔交易的基础数据结构。

## 📋 目录

- [文件结构概览](#文件结构概览)
- [套利路径模块](#套利路径模块)
  - [ArbitragePath 类](#arbitragepath-类)
  - [ArbitrageOpportunity 类](#arbitrageopportunity-类)
- [订单簿模块](#订单簿模块)
  - [OrderBook 类](#orderbook-类)
- [投资组合模块](#投资组合模块)
  - [Portfolio 类](#portfolio-类)
- [交易模块](#交易模块)
  - [TradeStatus 枚举](#tradestatus-枚举)
  - [Trade 类](#trade-类)
- [使用示例](#使用示例)

## 📁 文件结构概览

| 文件 | 用途 | 主要类 |
|------|------|--------|
| `__init__.py` | 模块初始化 | - |
| `arbitrage_path.py` | 套利路径和机会模型 | `ArbitragePath`, `ArbitrageOpportunity` |
| `order_book.py` | 市场订单簿数据模型 | `OrderBook` |
| `portfolio.py` | 投资组合和资产余额管理 | `Portfolio` |
| `trade.py` | 单笔交易表示 | `Trade`, `TradeStatus` |

---

## 套利路径模块

### ArbitragePath 类

表示一个完整的套利交易路径，形成闭环结构。

#### 构造函数参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | `List[str]` | ✅ | 构成套利路径的资产列表 (例如: `['USDT', 'USDC', 'BTC', 'USDT']`) |

#### 方法

##### `get_trading_pairs() -> List[str]`
返回套利路径所需的交易对。

**返回值:** 交易对列表，格式如 `['USDC-USDT', 'BTC-USDC', 'USDT-BTC']`

##### `get_trade_directions() -> List[str]`
返回每个步骤的交易方向（买入/卖出）。

**返回值:** 方向列表 `['buy', 'sell', 'buy']`

##### `get_step_count() -> int`
返回套利路径中的交易步数。

**返回值:** 步数整数

##### `get_start_asset() -> str`
返回起始资产符号。

**返回值:** 资产符号字符串

##### `is_triangular() -> bool`
检查是否为三角套利（3步）。

**返回值:** 布尔值，表示是否为三角套利

**使用示例:**
```python
from models.arbitrage_path import ArbitragePath

# 创建三角套利路径
path = ArbitragePath(['USDT', 'BTC', 'ETH', 'USDT'])
print(path.get_trading_pairs())  # ['BTC-USDT', 'ETH-BTC', 'USDT-ETH']
print(path.is_triangular())      # True
```

---

### ArbitrageOpportunity 类

表示具体的套利机会，包含利润计算。

#### 构造函数参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `path` | `ArbitragePath` | ✅ | - | 套利路径 |
| `profit_rate` | `float` | ✅ | - | 预期利润率 (例如: 0.01 表示1%) |
| `min_amount` | `float` | ✅ | - | 最小交易金额 |
| `timestamp` | `Optional[float]` | ❌ | `None` | 时间戳（如为None则自动生成） |

#### 方法

##### `is_profitable(threshold: float = 0.001) -> bool`
检查机会是否满足最小利润阈值。

**参数:**
- `threshold`: 最小利润阈值（默认: 0.1%）

**返回值:** 布尔值，表示是否有利可图

##### `get_profit_amount(investment: float) -> float`
计算给定投资额的预期利润金额。

**参数:**
- `investment`: 投资金额

**返回值:** 预期利润金额

##### `get_final_amount(investment: float) -> float`
计算套利执行后的最终金额。

**参数:**
- `investment`: 初始投资金额

**返回值:** 最终金额（投资 + 利润）

##### `is_amount_sufficient(amount: float) -> bool`
检查金额是否满足最小要求。

**参数:**
- `amount`: 要检查的投资金额

**返回值:** 布尔值，表示金额是否足够

##### `is_expired(max_age_seconds: float = 5.0) -> bool`
检查机会是否已过期。

**参数:**
- `max_age_seconds`: 最大有效时间，单位秒（默认: 5.0）

**返回值:** 布尔值，表示是否过期

**使用示例:**
```python
from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity

path = ArbitragePath(['USDT', 'BTC', 'ETH', 'USDT'])
opportunity = ArbitrageOpportunity(
    path=path,
    profit_rate=0.015,  # 1.5% 利润
    min_amount=100.0
)

print(opportunity.is_profitable(0.01))      # True (1.5% > 1%)
print(opportunity.get_profit_amount(1000))  # 15.0
print(opportunity.get_final_amount(1000))   # 1015.0
```

---

## 订单簿模块

### OrderBook 类

表示市场订单簿数据，包含买卖盘信息。

#### 构造函数参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | `str` | ✅ | 交易对符号（例如: 'BTC-USDT'） |
| `bids` | `List[List[float]]` | ✅ | 买单 `[[价格, 数量], ...]`（价格降序） |
| `asks` | `List[List[float]]` | ✅ | 卖单 `[[价格, 数量], ...]`（价格升序） |
| `timestamp` | `float` | ✅ | Unix 时间戳 |

#### 方法

##### `get_best_bid() -> Optional[float]`
返回最高买价。

**返回值:** 最优买价，如无买单则返回 None

##### `get_best_ask() -> Optional[float]`
返回最低卖价。

**返回值:** 最优卖价，如无卖单则返回 None

##### `get_spread() -> Optional[float]`
计算买卖价差。

**返回值:** 价格差，如数据不完整则返回 None

##### `get_mid_price() -> Optional[float]`
计算中间价格。

**返回值:** 中间价格 `(最优买价 + 最优卖价) / 2`，如数据不完整则返回 None

##### `get_depth(levels: int = 5) -> dict`
返回指定档位的订单簿深度。

**参数:**
- `levels`: 价格档位数量（默认: 5）

**返回值:** 包含 'bids' 和 'asks' 数组的字典

##### `is_valid() -> bool`
验证订单簿数据完整性。

**返回值:** 布尔值，表示数据是否有效

**使用示例:**
```python
from models.order_book import OrderBook
import time

order_book = OrderBook(
    symbol='BTC-USDT',
    bids=[[50000.0, 1.5], [49999.0, 2.0]],
    asks=[[50001.0, 1.0], [50002.0, 1.5]],
    timestamp=time.time()
)

print(order_book.get_best_bid())    # 50000.0
print(order_book.get_best_ask())    # 50001.0
print(order_book.get_spread())      # 1.0
print(order_book.get_mid_price())   # 50000.5
```

---

## 投资组合模块

### Portfolio 类

管理加密货币投资组合余额和操作。

#### 构造函数参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `balances` | `Dict[str, float]` | ✅ | 资产余额字典 `{资产: 余额}` |
| `timestamp` | `float` | ✅ | Unix 时间戳 |

#### 方法

##### `get_asset_balance(asset: str) -> float`
返回指定资产的余额。

**参数:**
- `asset`: 资产符号（例如: 'BTC', 'USDT'）

**返回值:** 资产余额（如未找到则返回 0.0）

##### `has_asset(asset: str) -> bool`
检查投资组合是否包含具有正余额的资产。

**参数:**
- `asset`: 资产符号

**返回值:** 布尔值，表示是否持有该资产

##### `get_total_assets() -> List[str]`
返回所有具有正余额的资产列表。

**返回值:** 资产符号列表

##### `get_total_balance_count() -> int`
返回具有正余额的资产数量。

**返回值:** 资产数量整数

##### `update_balance(asset: str, balance: float) -> None`
将资产余额设置为指定值。

**参数:**
- `asset`: 资产符号
- `balance`: 新的余额值

##### `add_balance(asset: str, amount: float) -> None`
增加现有资产余额。

**参数:**
- `asset`: 资产符号
- `amount`: 要增加的数量

##### `subtract_balance(asset: str, amount: float) -> bool`
如果资金充足，则从资产余额中减去金额。

**参数:**
- `asset`: 资产符号
- `amount`: 要减去的数量

**返回值:** 布尔值，表示操作是否成功

##### `is_sufficient_balance(asset: str, required_amount: float) -> bool`
检查是否有足够余额进行交易。

**参数:**
- `asset`: 资产符号
- `required_amount`: 所需数量

**返回值:** 布尔值，表示余额是否充足

##### `get_portfolio_summary() -> Dict[str, float]`
返回所有非零余额的摘要。

**返回值:** 资产余额字典

##### `is_empty() -> bool`
检查投资组合是否没有正余额。

**返回值:** 布尔值，表示是否为空

##### `copy() -> Portfolio`
创建投资组合的深度复制。

**返回值:** 新的 Portfolio 实例

**使用示例:**
```python
from models.portfolio import Portfolio
import time

portfolio = Portfolio(
    balances={'BTC': 0.5, 'USDT': 1000.0, 'ETH': 2.0},
    timestamp=time.time()
)

print(portfolio.get_asset_balance('BTC'))           # 0.5
print(portfolio.has_asset('BTC'))                   # True
print(portfolio.is_sufficient_balance('USDT', 500)) # True

portfolio.subtract_balance('USDT', 100)
print(portfolio.get_asset_balance('USDT'))          # 900.0
```

---

## 交易模块

### TradeStatus 枚举

可能的交易状态枚举。

#### 值

| 值 | 说明 |
|----|------|
| `PENDING` | 交易待执行 |
| `FILLED` | 交易已完成 |
| `CANCELLED` | 交易已取消 |
| `FAILED` | 交易执行失败 |

---

### Trade 类

表示单个交易操作。

#### 构造函数参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `inst_id` | `str` | ✅ | - | 交易对ID（例如: 'BTC-USDT'） |
| `side` | `str` | ✅ | - | 交易方向（'buy' 或 'sell'） |
| `size` | `float` | ✅ | - | 交易数量 |
| `price` | `float` | ✅ | - | 交易价格 |
| `order_id` | `Optional[str]` | ❌ | `None` | 可选的订单ID |

#### 方法

##### `get_notional_value() -> float`
计算交易的总价值。

**返回值:** 名义价值（数量 × 价格）

##### `is_buy() -> bool`
检查是否为买单。

**返回值:** 布尔值，表示是否为买方向

##### `is_sell() -> bool`
检查是否为卖单。

**返回值:** 布尔值，表示是否为卖方向

##### `get_base_asset() -> str`
从交易对中提取基础资产。

**返回值:** 基础资产符号

##### `get_quote_asset() -> str`
从交易对中提取报价资产。

**返回值:** 报价资产符号

##### `get_required_balance() -> tuple[str, float]`
返回执行交易所需的资产和数量。

**返回值:** 元组 (资产符号, 所需数量)

##### `get_receive_amount() -> tuple[str, float]`
返回将要收到的资产和数量。

**返回值:** 元组 (资产符号, 收到数量)

##### `to_order_params() -> dict`
将交易转换为交易所API订单参数。

**返回值:** 订单参数字典

**使用示例:**
```python
from models.trade import Trade, TradeStatus

trade = Trade(
    inst_id='BTC-USDT',
    side='buy',
    size=0.1,
    price=50000.0
)

print(trade.get_notional_value())    # 5000.0
print(trade.is_buy())                # True
print(trade.get_base_asset())        # 'BTC'
print(trade.get_quote_asset())       # 'USDT'
print(trade.get_required_balance())  # ('USDT', 5000.0)
print(trade.get_receive_amount())    # ('BTC', 0.1)

# 转换为订单参数
params = trade.to_order_params()
print(params)  # {'instId': 'BTC-USDT', 'side': 'buy', 'ordType': 'limit', 'sz': '0.1', 'px': '50000.0'}
```

---

## 🚀 使用示例

### 完整套利工作流

```python
from models.arbitrage_path import ArbitragePath, ArbitrageOpportunity
from models.portfolio import Portfolio
from models.trade import Trade
from models.order_book import OrderBook
import time

# 1. 创建套利路径
path = ArbitragePath(['USDT', 'BTC', 'ETH', 'USDT'])

# 2. 创建套利机会
opportunity = ArbitrageOpportunity(
    path=path,
    profit_rate=0.02,  # 2% 利润
    min_amount=1000.0
)

# 3. 检查机会是否有利可图且有效
if opportunity.is_profitable(0.01) and not opportunity.is_expired():
    print(f"有利可图的机会: {opportunity}")
    
    # 4. 检查投资组合余额
    portfolio = Portfolio(
        balances={'USDT': 5000.0, 'BTC': 0.0, 'ETH': 0.0},
        timestamp=time.time()
    )
    
    investment = 2000.0
    if portfolio.is_sufficient_balance('USDT', investment):
        # 5. 为套利执行创建交易
        trading_pairs = opportunity.get_trading_pairs()
        directions = opportunity.get_trade_directions()
        
        trades = []
        for pair, direction in zip(trading_pairs, directions):
            trade = Trade(
                inst_id=pair,
                side=direction,
                size=0.1,  # 计算适当的数量
                price=50000.0  # 使用真实市场价格
            )
            trades.append(trade)
        
        print(f"预期利润: {opportunity.get_profit_amount(investment)}")
        print(f"最终金额: {opportunity.get_final_amount(investment)}")

# 6. 处理订单簿数据
order_book = OrderBook(
    symbol='BTC-USDT',
    bids=[[50000.0, 1.5], [49999.0, 2.0]],
    asks=[[50001.0, 1.0], [50002.0, 1.5]],
    timestamp=time.time()
)

if order_book.is_valid():
    spread = order_book.get_spread()
    mid_price = order_book.get_mid_price()
    print(f"市场价差: {spread}, 中间价: {mid_price}")
```

### 投资组合管理

```python
from models.portfolio import Portfolio
import time

# 初始化投资组合
portfolio = Portfolio(
    balances={'BTC': 1.0, 'ETH': 10.0, 'USDT': 50000.0},
    timestamp=time.time()
)

# 投资组合操作
print(f"总资产数: {portfolio.get_total_balance_count()}")
print(f"投资组合摘要: {portfolio.get_portfolio_summary()}")

# 模拟交易执行
if portfolio.subtract_balance('USDT', 5000.0):
    portfolio.add_balance('BTC', 0.1)
    print("交易执行成功")
    
# 创建备份
portfolio_backup = portfolio.copy()
```

## 📝 注意事项

- 所有货币值都用浮点数表示
- 资产符号遵循交易所约定（例如: 'BTC-USDT'）
- 时间戳使用Unix时间格式
- 所有类都包含全面的数据验证
- 关键操作内置异常处理
- 模型设计适用于高频交易场景

## ⚠️ 重要考虑

1. **精度**: 处理小额时要注意浮点精度问题
2. **验证**: 所有模型都包含内置验证以防止无效状态
3. **性能**: 模型针对频繁实例化和计算进行了优化
4. **线程安全**: 模型本身不是线程安全的；并发访问时需使用适当的锁定
5. **交易所集成**: 交易参数设计为与主要加密货币交易所兼容

---

*本文档涵盖了完整的 models 模块 API。在更广泛的交易系统中的使用，请参考 core 模块文档和示例。*