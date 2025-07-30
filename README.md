# OKX三角套利交易机器人

## 项目概述

**项目名称：** OKX三角套利交易机器人

**项目状态：** 核心功能已完成，仅主入口函数待实现

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
├── 🎯 examples/             # 使用示例
│   └── real_time_monitor.py  # 📺 实时监控演示
├── 🔌 okex/                 # OKX官方API库
├── 📝 main.py               # ⭐ 主程序入口 (待实现)
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

## 🚀 主入口函数 (main.py) - 待实现

### 🎯 核心任务
主入口函数需要完成以下关键任务：

```python
# 主入口函数应包含以下流程：

1. 🔧 系统初始化
   - 设置日志系统 (utils.logger)
   - 加载配置管理器 (config.ConfigManager)
   - 创建交易控制器 (core.TradingController)

2. 🛡️ 环境检查
   - 验证API密钥配置
   - 检查网络连接状态
   - 确认交易对可用性

3. 🎮 启动交易系统  
   - 启动数据采集 (WebSocket + REST)
   - 开始套利监控循环
   - 启用风险管理机制

4. 📊 监控与管理
   - 实时监控面板 (可选)
   - 优雅退出处理
   - 错误恢复机制
```

### 💡 实现建议
基于现有架构，主入口函数可以参考 `examples/real_time_monitor.py` 的实现模式，主要步骤：

```python
async def main():
    # 初始化核心组件
    controller = TradingController(enable_rich_logging=True)
    
    # 启动交易系统
    await controller.start()
    
    # 运行主循环或监控界面
    # 处理用户交互和系统管理
    
    # 优雅关闭
    await controller.stop()
```

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

### 2. 主要配置参数 (config/settings.ini)

### 📊 智能交易配置 (config/settings.ini)

**🛤️ 套利路径配置** - 支持JSON格式精确定义
```ini
[trading]
# 高级路径配置 - JSON格式，支持精确的交易对和操作定义
path1 = {"route": "USDT->BTC->USDC->USDT", "steps": [{"pair": "BTC-USDT", "action": "buy"}, {"pair": "BTC-USDC", "action": "sell"}, {"pair": "USDT-USDC", "action": "buy"}]}

path2 = {"route": "USDT->USDC->BTC->USDT", "steps": [{"pair": "USDT-USDC", "action": "buy"}, {"pair": "BTC-USDC", "action": "buy"}, {"pair": "BTC-USDT", "action": "sell"}]}

# 交易核心参数
min_profit_threshold = 0.003    # 最小利润阈值 (0.3%)
min_trade_amount = 100.0        # 最小交易金额
monitor_interval = 1.0          # 监控间隔 (秒)
fee_rate = 0.001               # 交易手续费率
slippage_tolerance = 0.002     # 滑点容忍度
```

**🛡️ 多层风险管理配置**
```ini
[risk]
max_position_ratio = 0.2        # 最大仓位比例 (20%总资产)
max_single_trade_ratio = 0.1    # 单笔最大交易比例 (10%总资产)
min_arbitrage_interval = 10     # 套利最小间隔 (秒)
max_daily_trades = 100          # 单日最大交易次数
max_daily_loss_ratio = 0.05     # 单日最大损失比例 (5%)
stop_loss_ratio = 0.1           # 强制停止损失阈值 (10%)
network_retry_count = 3         # 网络重试次数
```

**⚙️ 系统性能配置**
```ini
[system]
log_level = INFO                        # 日志级别
log_file = logs/trading.log            # 日志文件
enable_performance_monitoring = true   # 性能监控
enable_trade_history = true           # 交易历史记录
performance_log_interval = 300        # 性能日志间隔(秒)
```

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

### 📊 实时监控演示
```bash
# 启动可视化监控界面 (包含模拟数据)
python examples/real_time_monitor.py
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