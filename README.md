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

## 环境要求

- Python 3.8+
- OKX交易所账户  
- API密钥（支持现货交易权限）

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

**交易配置**
```ini
[trading]
# 套利路径配置
path1 = {"route": "USDT->BTC->USDC->USDT", "steps": [...]}
path2 = {"route": "USDT->USDC->BTC->USDT", "steps": [...]}

# 交易参数
min_profit_threshold = 0.003    # 最小利润阈值 (0.3%)
min_trade_amount = 100.0        # 最小交易金额 ($100)
monitor_interval = 1.0          # 监控间隔 (秒)
```

**风险管理配置**
```ini
[risk]
max_position_ratio = 0.2        # 最大仓位比例 (20%)
max_single_trade_ratio = 0.1    # 单笔最大交易比例 (10%)
max_daily_trades = 100          # 最大单日交易次数
max_daily_loss_ratio = 0.05     # 最大单日损失比例 (5%)
stop_loss_ratio = 0.1           # 强制停止交易的损失比例 (10%)
```

**系统配置**
```ini
[system]
log_level = INFO
log_file = logs/trading.log
enable_performance_monitoring = true
enable_trade_history = true
```

## 注意事项

⚠️ **重要风险提示**
- 建议先在模拟环境测试 (`flag = 1`)
- 使用少量资金进行实盘测试
- 定期检查API权限设置
- 确保网络连接稳定

## 许可证

本项目仅供学习和研究使用。请遵守相关法律法规，自行承担交易风险。

---

⚠️ **免责声明**: 本软件仅供教育和研究目的。任何交易都存在风险，过往收益不代表未来表现。请谨慎投资，自行承担风险。