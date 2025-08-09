# OKX三角套利交易机器人

## 项目概述

**项目名称：** OKX三角套利交易机器人

**项目状态：** 系统已完全实现，支持自动交易和监控模式（实盘/模拟盘）

**功能描述：** 专业级的三角套利交易系统，支持USDT-USDC-BTC等多种资产的自动套利交易。系统通过WebSocket实时监控OKX交易所价格数据，使用先进的算法识别套利机会，并在严格的风险控制下自动执行交易。

**核心特性：**
- 🚀 **毫秒级实时数据** - WebSocket + REST双重数据源，确保数据准确性和实时性  
- 🛡️ **多层风险管理** - 智能仓位控制、频率限制、损失阈值等全方位风险防护
- 📊 **Rich可视化监控** - 实时交易面板、性能指标、余额历史等专业监控界面
- ⚡ **高性能异步架构** - 基于asyncio，支持并发数据采集和多路径套利计算
- 🔧 **企业级模块设计** - 松耦合架构，支持热配置更新，易于扩展和维护
- 📈 **智能交易执行** - 优化的价格策略、订单管理和异常处理机制

## 核心架构

### 📁 项目结构
```
taoli/                        # OKX三角套利交易系统
├── 🔧 core/                  # 核心交易引擎
│   ├── trading_controller.py # 🎮 主控制器 - 统一交易流程管理
│   ├── data_collector.py     # 📡 数据采集器 - WebSocket+REST双重数据源
│   ├── arbitrage_engine.py   # 🧮 套利引擎 - 智能机会识别与计算
│   ├── trade_executor.py     # ⚡ 交易执行器 - 高效订单执行管理
│   ├── risk_manager.py       # 🛡️ 风险管理器 - 多层风险控制系统
│   ├── okx_client.py         # 🔌 OKX客户端 - API接口封装
│   └── websocket_manager.py  # 🌐 WebSocket管理器 - 实时数据连接
├── 📊 models/                # 核心数据模型
│   ├── arbitrage_path.py     # 🛤️ 套利路径模型 - 路径定义与验证
│   ├── order_book.py         # 📈 订单簿模型 - 市场深度数据
│   ├── portfolio.py          # 💰 投资组合模型 - 资产管理
│   └── trade.py              # 💱 交易模型 - 订单状态管理
├── ⚙️ config/               # 智能配置管理
│   ├── config_manager.py     # 🔨 配置管理器 - 支持热更新
│   ├── settings.ini          # ⚙️ 交易参数配置
│   ├── secrets.ini           # 🔐 API密钥配置
│   └── secrets.ini.example   # 📋 密钥配置模板
├── 🛠️ utils/                # 专业工具套件
│   ├── logger.py             # 📝 日志工具 - Rich格式化输出
│   ├── trade_logger.py       # 📊 交易日志器 - 专业交易记录
│   └── performance_analyzer.py # 📈 性能分析器 - 系统监控
├── 🧪 tests/                # 全面测试覆盖
│   ├── test_core_comprehensive.py  # 核心功能测试
│   ├── test_run_core.py      # 快速功能验证
│   ├── test_models.py        # 数据模型测试
│   └── test_arbitrage_*.py   # 套利算法测试
├── 🔌 okex/                 # OKX官方API库
├── 📝 main.py               # ⭐ 主程序入口
└── 📦 requirements.txt      # 项目依赖
```

### 🏗️ 系统架构关系
```
┌─────────────────┐    ┌─────────────────┐
│  TradingController │────│   DataCollector   │
│   (主控制器)       │    │   (数据采集)      │
└─────────┬───────┘    └─────────┬───────┘
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ ArbitrageEngine │    │ WebSocketManager│
│   (套利计算)     │    │  (实时数据)      │
└─────────┬───────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│   RiskManager   │────│  TradeExecutor  │
│   (风险控制)     │    │   (交易执行)     │
└─────────────────┘    └─────────────────┘
```

## 🚀 主程序使用 (main.py)

### 启动系统

```bash
# 启动交易系统
python main.py
```

### 运行模式选择

系统启动后会提示选择运行模式：

1. **🤖 自动交易模式 (trading)**
   - 自动执行三角套利交易
   - 实时监控套利机会
   - 自动风险控制
   - 支持实盘和模拟盘

2. **📊 监控模式 (monitor)**  
   - 仅监控不交易
   - 实时显示套利机会
   - 查看市场数据和分析
   - 无风险了解系统运行

3. **🧪 测试模式 (test)**
   - 系统功能测试
   - 验证配置和连接
   - 检查API权限
   - 不执行实际交易

### 监控界面功能

运行后显示实时监控面板，包含：

- **系统状态** - 运行时间、交易模式、启用状态
- **套利分析** - 实时套利机会和利润率
- **价格监控** - 关键交易对实时价格
- **交易统计** - 成功/失败次数、总利润
- **性能指标** - CPU、内存、API调用统计
- **控制指令** - 键盘快捷键操作

### 键盘控制

- `Space` - 暂停/恢复交易
- `R` - 刷新显示
- `Q` - 退出程序
- `Ctrl+C` - 强制退出

## 🔧 环境要求

- **Python 3.8+** (推荐3.9+以获得最佳性能)
- **OKX交易所账户** (需要现货交易权限)
- **API密钥配置** (API Key, Secret Key, Passphrase)
- **网络环境** (稳定的互联网连接，建议低延迟)

## 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd triangular-arbitrage-bot

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 配置方法

### 1. 配置API密钥

```bash
# 复制API配置模板
cp config/secrets.ini.example config/secrets.ini

# 编辑配置文件，填入你的API信息
nano config/secrets.ini
```

**secrets.ini 配置说明**
```ini
[api]
api_key = your_api_key_here
secret_key = your_secret_key_here
passphrase = your_passphrase_here

# 实盘=0, 模拟盘=1 (建议先使用模拟盘测试)
flag = 1
```

### 2. 配置文件详细说明

### 📊 主配置文件 (config/settings.ini)

**🛤️ 套利路径配置** - 支持JSON格式精确定义
```ini
[trading]
# 预设套利路径 - JSON格式定义（单行）
# 每个路径包含：route（路径描述）和 steps（具体交易步骤）
path1 = {"route": "USDT->BTC->USDC->USDT", "steps": [{"pair": "BTC-USDT", "action": "buy"}, {"pair": "BTC-USDC", "action": "sell"}, {"pair": "USDC-USDT", "action": "sell"}]}
path2 = {"route": "USDT->USDC->BTC->USDT", "steps": [{"pair": "USDC-USDT", "action": "buy"}, {"pair": "BTC-USDC", "action": "buy"}, {"pair": "BTC-USDT", "action": "sell"}]}

# 初始持有量配置（根据实际账户资金设置）
initial_usdt = 40.54317        # USDT初始数量
initial_usdc = 30.0            # USDC初始数量
initial_btc = 0.0002997        # BTC初始数量

# 再平衡阈值（偏差百分比）
rebalance_threshold = 5.0      # 触发再平衡的偏差阈值

# 交易手续费配置（支持差异化费率）
fee_rate = 0.001               # 默认手续费率（兜底配置）

# 按交易对的差异化手续费配置（根据OKX实际费率设置）
fee_rate_usdc_usdt = 0.0       # USDC-USDT免手续费
fee_rate_btc_usdt = 0.001      # BTC-USDT标准手续费
fee_rate_btc_usdc = 0.001      # BTC-USDC标准手续费

# 交易执行参数
slippage_tolerance = 0.002     # 滑点容忍度 (0.2%)
min_profit_threshold = 0.003   # 最小利润阈值 (0.3%)
order_timeout = 3.0            # 订单超时时间（秒）
min_trade_amount = 10.0        # 最小交易金额（美元）
monitor_interval = 1.0         # 监控间隔（秒）
price_adjustment = 0.001       # 价格调整幅度

# 套利合理性验证（可选）
enable_profit_validation = false         # 是否启用利润验证
max_profit_rate_threshold = 0.01        # 最大合理利润率
max_simulated_profit_rate = 0.005       # 模拟最大利润率
max_price_spread = 0.02                 # 最大价差阈值
max_stablecoin_spread = 0.005           # 稳定币最大价差
stablecoin_price_range_min = 0.98       # 稳定币价格下限
stablecoin_price_range_max = 1.02       # 稳定币价格上限
```

**🛡️ 风险管理配置**
```ini
[risk]
# 仓位控制参数
max_position_ratio = 0.3        # 最大仓位比例 (30%总资产)
max_single_trade_ratio = 0.15   # 单笔最大交易比例 (15%总资产)

# 交易频率控制
min_arbitrage_interval = 10     # 套利最小间隔（秒）
max_daily_trades = 50           # 单日最大交易次数

# 损失控制参数
max_daily_loss_ratio = 0.05     # 单日最大损失比例 (5%)
stop_loss_ratio = 0.1           # 强制停止损失阈值 (10%)

# 系统检查参数
balance_check_interval = 60     # 余额检查间隔（秒）

# 网络重试配置
network_retry_count = 3         # 网络重试次数
network_retry_delay = 1.0       # 重试延迟（秒）
```

**⚙️ 系统配置**
```ini
[system]
# 日志配置
log_level = INFO                # 日志级别 (DEBUG/INFO/WARNING/ERROR)
log_file = logs/trading.log     # 日志文件路径

# 数据存储配置
enable_trade_history = true                    # 是否记录交易历史
trade_history_file = logs/trade_history.json   # 交易历史文件路径
```

### 🔐 API密钥配置 (config/secrets.ini)

**重要提示**：此文件包含敏感信息，不应提交到版本控制系统

```ini
[api]
# OKX API密钥配置
api_key = your_api_key_here        # API Key（从OKX获取）
secret_key = your_secret_key_here  # Secret Key（从OKX获取）
passphrase = your_passphrase_here  # Passphrase（创建API时设置）

# 交易环境选择
flag = 1                           # 0=实盘, 1=模拟盘（强烈建议先使用模拟盘）
```

### 📝 配置最佳实践

1. **手续费配置优化**
   - 系统支持按交易对配置不同的手续费率
   - OKX对某些稳定币交易对（如USDC-USDT）提供零手续费
   - 正确配置可显著提高套利收益（可节省约33%的手续费成本）

2. **风险参数调整建议**
   - **小额账户**（<$1000）：可适当提高仓位比例至30-40%
   - **大额账户**（>$10000）：建议保持保守的10-20%仓位
   - **初次使用**：建议使用最小交易金额测试

3. **路径配置说明**
   - 每个路径必须形成闭环（起点和终点相同）
   - steps中的action只有两种：buy（买入）和sell（卖出）
   - pair格式必须与OKX交易对格式一致（如BTC-USDT）

4. **性能优化建议**
   - `monitor_interval`：网络好时可设为0.5-1秒，网络差时设为2-3秒
   - `order_timeout`：根据网络延迟调整，通常3-5秒较合适
   - `balance_check_interval`：频繁交易时可设为30秒，否则60秒即可

## 🧪 测试与验证

### 📋 快速功能测试
```bash
# 运行核心功能快速验证 (30-60秒)
python tests/test_run_core.py

# 生成详细覆盖率报告
python tests/test_run_core.py --coverage

# 完整系统测试
python tests/test_run_core.py --full
```

### 📊 实时监控
```bash
# 启动主程序并选择监控模式
python main.py
# 然后选择 2 (Monitor Mode)
```

### 🔍 可用的测试功能
- ✅ **配置管理验证** - API密钥、交易参数有效性检查
- ✅ **OKX API连接测试** - 网络连接、认证状态验证  
- ✅ **数据采集测试** - WebSocket连接、订单簿获取
- ✅ **套利引擎测试** - 机会识别、利润计算验证
- ✅ **风险管理测试** - 仓位控制、频率限制验证
- ✅ **交易执行测试** - 订单管理、错误处理验证
- ✅ **系统集成测试** - 端到端流程验证
- ✅ **性能基准测试** - 响应时间、资源使用分析

## 🚨 重要风险提示与最佳实践

### ⚠️ 安全第一
- **强制要求**: 首次运行必须使用模拟环境 (`flag = 1` in secrets.ini)
- **资金安全**: 实盘测试请使用少量资金
- **权限检查**: 定期验证API权限设置，仅授予必需权限
- **网络稳定**: 确保稳定低延迟网络连接

### 💡 推荐工作流程
1. **环境准备** → 配置API密钥，设置模拟环境
2. **功能验证** → 运行测试套件确保系统正常
3. **模拟运行** → 在模拟环境观察系统行为
4. **小额实测** → 使用最小金额进行实盘验证
5. **逐步增加** → 根据表现逐步调整交易规模

## 🌟 已实现的核心功能

### 💎 数据采集与处理
- **双重数据源**: WebSocket实时数据 + REST API备份
- **毫秒级精度**: 支持500ms内的高频套利计算
- **智能缓存**: 自动数据验证、过期清理和一致性检查
- **自动重连**: WebSocket断线自动恢复，确保数据连续性

### 🧮 智能套利算法
- **多路径支持**: 灵活的JSON配置格式，支持复杂套利路径
- **精确计算**: 考虑手续费、滑点的利润率精确计算
- **实时验证**: 数据时间一致性检查，避免过期数据交易
- **性能优化**: 高效的订单簿处理和套利机会识别

### 🛡️ 企业级风险管理
- **多层防护**: 仓位限制、交易频率、日损失控制
- **动态调整**: 基于实时风险水平的智能交易量调整
- **异常处理**: 完善的错误恢复和交易回滚机制
- **实时监控**: 风险指标实时跟踪和预警系统

### ⚡ 高性能交易执行
- **智能订单**: 价格优化、超时处理、重试机制
- **余额管理**: 本地缓存 + 定期同步，减少API调用
- **执行追踪**: 详细的交易执行记录和状态管理
- **异步架构**: 基于asyncio的并发执行框架

### 📊 专业监控工具
- **Rich界面**: 美观的终端实时监控面板
- **性能分析**: CPU、内存、API响应时间监控
- **交易统计**: 成功率、利润分析、风险指标
- **历史记录**: 完整的交易历史和余额变化追踪

### 🔧 开发者友好
- **模块化设计**: 松耦合架构，易于扩展和维护
- **全面测试**: 90%+代码覆盖率，包含集成测试
- **详细日志**: Rich格式化日志，支持多级别输出
- **配置热更新**: 运行时配置修改，无需重启系统

---

## 📄 许可证与免责声明

本项目仅供学习和研究使用。请遵守相关法律法规，自行承担交易风险。

---

⚠️ **免责声明**: 本软件仅供教育和研究目的。任何交易都存在风险，过往收益不代表未来表现。请谨慎投资，自行承担风险。