# OKX三角套利交易机器人

## 项目概述

**项目名称：** OKX三角套利交易机器人

**功能描述：** 自动识别并执行USDT-USDC-BTC三角套利机会的智能交易系统。系统通过实时监控OKX交易所的价格数据，识别三种资产间的价格差异，自动执行套利交易以获取无风险收益。

**技术亮点：**
- 🚀 **WebSocket实时数据** - 毫秒级价格数据更新，确保套利机会不被错过
- 🛡️ **智能风险管理** - 多层风险控制机制，包括仓位限制、损失阈值、交易频率控制
- 📊 **Rich监控界面** - 美观的终端界面，实时显示交易状态、收益统计和风险指标
- ⚡ **异步高性能** - 基于asyncio的异步架构，支持并发处理多个套利路径
- 🔧 **模块化设计** - 清晰的代码结构，易于维护和扩展

## 项目结构

```
triangular-arbitrage-bot/
├── config/                    # 配置管理
│   ├── config_manager.py     # 配置管理器
│   ├── settings.ini          # 主要配置文件
│   ├── secrets.ini           # API密钥配置
│   └── secrets.ini.example   # API密钥配置模板
├── core/                     # 核心业务逻辑
│   ├── arbitrage_engine.py   # 套利引擎
│   ├── data_collector.py     # 数据收集器
│   ├── okx_client.py         # OKX API客户端
│   ├── risk_manager.py       # 风险管理器
│   ├── trade_executor.py     # 交易执行器
│   ├── trading_controller.py # 交易控制器
│   └── websocket_manager.py  # WebSocket管理器
├── models/                   # 数据模型
│   ├── arbitrage_path.py     # 套利路径模型
│   ├── order_book.py         # 订单簿模型
│   ├── portfolio.py          # 投资组合模型
│   └── trade.py              # 交易模型
├── utils/                    # 工具函数
│   ├── logger.py             # 日志工具
│   ├── performance_analyzer.py # 性能分析器
│   └── trade_logger.py       # 交易日志器
├── tests/                    # 测试代码
│   ├── test_arbitrage_engine.py
│   ├── test_integration.py
│   ├── test_risk_manager.py
│   └── test_trade_executor.py
├── examples/                 # 示例代码
│   ├── performance_monitor_demo.py
│   └── real_time_monitor.py
├── logs/                     # 日志文件
│   ├── trading.log           # 主要日志
│   ├── trade_history.json    # 交易历史
│   └── daily_stats.json      # 每日统计
├── okex/                     # OKX API客户端库
├── main.py                   # 主程序入口
├── run_tests_clean.py        # 测试运行脚本
└── requirements.txt          # 项目依赖
```

## 快速开始

### 环境要求

- Python 3.8+
- OKX交易所账户
- API密钥（支持现货交易权限）

### 安装依赖

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

### 配置设置

1. **配置API密钥**
```bash
# 复制API配置模板
cp config/secrets.ini.example config/secrets.ini

# 编辑配置文件，填入你的API信息
nano config/secrets.ini
```

2. **secrets.ini 配置说明**
```ini
[api]
api_key = your_api_key_here
secret_key = your_secret_key_here
passphrase = your_passphrase_here

# 实盘=0, 模拟盘=1 (建议先使用模拟盘测试)
flag = 1
```

3. **主要配置参数 (config/settings.ini)**
```ini
[trading]
# 套利路径配置
path1 = {"route": "USDT->BTC->USDC->USDT", "steps": [...]}
path2 = {"route": "USDT->USDC->BTC->USDT", "steps": [...]}

# 交易参数
min_profit_threshold = 0.003    # 最小利润阈值 (0.3%)
min_trade_amount = 100.0        # 最小交易金额 ($100)
monitor_interval = 1.0          # 监控间隔 (秒)

[risk]
max_position_ratio = 0.2        # 最大仓位比例 (20%)
max_single_trade_ratio = 0.1    # 单笔最大交易比例 (10%)
max_daily_trades = 100          # 最大单日交易次数
```

## 使用指南

### 基本运行命令

1. **监控模式** (推荐首次使用)
```bash
python3 main.py --mode=monitor
```
- 只监控套利机会，不执行真实交易
- 适合观察市场情况和验证策略
- 会显示发现的套利机会和预期收益

2. **交易模式** (实际交易)
```bash
python3 main.py --mode=trade
```
- 监控并执行真实交易
- 需要确保API权限正确且账户余额充足
- 会自动执行发现的套利机会

3. **自定义配置文件**
```bash
python3 main.py --mode=monitor --config=config/settings.ini
```

### 日志查看

```bash
# 查看实时日志
tail -f logs/trading.log

# 查看交易历史
cat logs/trade_history.json

# 查看每日统计
cat logs/daily_stats.json
```

### 性能监控

系统提供实时监控界面，显示：
- 套利机会发现数量
- 交易执行情况
- 实时收益统计
- 风险指标监控
- 系统性能指标

## 测试

### 运行测试套件

```bash
# 运行所有测试
python run_tests_clean.py

# 运行特定测试
python -m pytest tests/test_arbitrage_engine.py -v

# 运行集成测试
python -m pytest tests/test_integration.py -v
```

### 测试覆盖率

项目包含以下测试类型：
- **单元测试** - 测试核心组件功能
- **集成测试** - 测试组件间交互
- **风险管理测试** - 验证风险控制机制
- **交易执行测试** - 模拟交易流程

测试覆盖主要模块：
- 套利引擎 (`test_arbitrage_engine.py`)
- 风险管理 (`test_risk_manager.py`)
- 交易执行 (`test_trade_executor.py`)
- 系统集成 (`test_integration.py`)

## 核心功能

### 套利策略

系统支持两种主要套利路径：

1. **路径1**: USDT → BTC → USDC → USDT
   - 使用USDT购买BTC
   - 出售BTC获得USDC
   - 出售USDC获得USDT

2. **路径2**: USDT → USDC → BTC → USDT
   - 使用USDT购买USDC
   - 使用USDC购买BTC
   - 出售BTC获得USDT

### 风险管理

- **仓位控制**: 限制单次交易和总仓位规模
- **损失控制**: 设置日损失限额和强制止损
- **频率控制**: 防止过度频繁交易
- **余额监控**: 实时检查账户余额
- **网络重试**: 处理网络异常和API限制

### 性能优化

- **WebSocket连接**: 实时价格数据更新
- **异步处理**: 并发处理多个套利机会
- **内存优化**: 高效的数据结构和缓存机制
- **CPU优化**: 优化计算算法减少延迟

## 注意事项

### ⚠️ 重要风险提示

1. **资金安全**
   - 建议先在模拟环境测试 (`flag = 1`)
   - 使用少量资金进行实盘测试
   - 定期检查API权限设置

2. **市场风险**
   - 加密货币市场波动性高
   - 套利机会可能快速消失
   - 网络延迟可能影响收益

3. **技术风险**
   - 确保网络连接稳定
   - 监控系统资源使用情况
   - 定期备份配置和日志

### 🔧 运维建议

1. **监控检查**
   - 定期查看日志文件
   - 关注系统性能指标
   - 监控API使用量

2. **配置优化**
   - 根据市场情况调整参数
   - 优化套利路径配置
   - 更新风险管理阈值

3. **备份维护**
   - 备份重要配置文件
   - 保存交易历史数据
   - 定期更新依赖库

### 📞 技术支持

如遇到问题，请检查：
1. API配置是否正确
2. 网络连接是否稳定
3. 账户余额是否充足
4. 日志文件中的错误信息

## 许可证

本项目仅供学习和研究使用。请遵守相关法律法规，自行承担交易风险。

---

⚠️ **免责声明**: 本软件仅供教育和研究目的。任何交易都存在风险，过往收益不代表未来表现。请谨慎投资，自行承担风险。