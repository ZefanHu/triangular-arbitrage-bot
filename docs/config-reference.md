# Config Reference (settings.ini / secrets.ini)

Last updated: 2026-01-28  
Baseline commit: 0c260e7  
Source of truth: `config/config_manager.py` (SETTINGS_SCHEMA / DYNAMIC_KEY_RULES / DEPRECATED_KEYS)

## 1) 总览

- **校验策略：严格 schema + fail-fast**。配置会被逐项校验，**未知 key 会直接报错并终止启动**（含拼写建议）。
- **支持 inline 注释**：每个值允许在结尾追加 `#` 或 `;` 作为行内注释，解析时会被剥离。
- **动态 key**：
  - `[trading] path*`：任意 `path` 前缀的 key（如 `path1`、`path_btc_usdt`），类型为字符串。
  - `[trading] fee_rate_*`：任意 `fee_rate_` 前缀的 key（如 `fee_rate_btc_usdt`），类型为浮点数，范围 0–1。
- **弃用 key**：
  - `trading.price_adjustment` 已弃用，启动时会被映射为 `trading.slippage_tolerance`，并输出弃用警告。
- **slippage_tolerance 提示**：该值用于每一腿下单价格的保守滑点调整（买单使用 `1 + slippage_tolerance`，卖单使用 `1 - slippage_tolerance`）。

> **提醒**：未知 key 会触发 fail-fast。请勿在 settings.ini 中随意添加未在本表或动态 key 规则中允许的字段。

## 2) [trading] keys

| key | type | default | range | 说明 |
| --- | --- | --- | --- | --- |
| initial_usdt | float | 0.0 | >= 0 | 初始 USDT 余额。 |
| initial_usdc | float | 0.0 | >= 0 | 初始 USDC 余额。 |
| initial_btc | float | 0.0 | >= 0 | 初始 BTC 余额。 |
| fee_rate | float | 0.001 | 0–1 | 默认手续费率。 |
| slippage_tolerance | float | 0.002 | 0–0.02 | 滑点容忍度（用于每一腿下单价格的保守调整）。 |
| min_profit_threshold | float | 0.003 | 0–0.05 | 最小套利收益阈值。 |
| order_timeout | float | 3.0 | > 0 且 <= 60 | 订单超时（秒）。 |
| min_trade_amount | float | 100.0 | > 0 | 最小交易金额。 |
| monitor_interval | float | 1.0 | > 0 且 <= 60 | 监控间隔（秒）。 |
| enable_profit_validation | bool | False | N/A | 是否启用收益校验。 |
| max_profit_rate_threshold | float | 0.01 | 0–1 | 收益率上限阈值。 |
| max_simulated_profit_rate | float | 0.005 | 0–1 | 模拟收益率上限。 |
| max_price_spread | float | 0.02 | 0–1 | 最大价格价差。 |
| max_stablecoin_spread | float | 0.005 | 0–1 | 稳定币价差上限。 |
| stablecoin_price_range_min | float | 0.98 | 0–2 | 稳定币价格区间下限。 |
| stablecoin_price_range_max | float | 1.02 | 0–2 | 稳定币价格区间上限。 |

**动态 key（[trading]）**

| key pattern | type | range | 说明 |
| --- | --- | --- | --- |
| path* | str | N/A | 路径配置（字符串，支持 JSON 或旧格式）。 |
| fee_rate_* | float | 0–1 | 针对特定交易对的手续费率覆盖。 |

## 3) [risk] keys

| key | type | default | range | 说明 |
| --- | --- | --- | --- | --- |
| max_position_ratio | float | 0.2 | > 0 且 <= 1 | 最大持仓比例。 |
| max_single_trade_ratio | float | 0.1 | > 0 且 <= 1 | 单笔交易最大占比。 |
| min_arbitrage_interval | float | 10.0 | 0–3600 | 最小套利间隔（秒）。 |
| max_daily_trades | int | 100 | 1–10000 | 每日最大交易次数。 |
| max_daily_loss_ratio | float | 0.05 | > 0 且 <= 1 | 每日最大亏损比例。 |
| stop_loss_ratio | float | 0.1 | > 0 且 <= 1 | 止损比例。 |
| network_retry_count | int | 3 | 0–10 | 网络重试次数。 |
| network_retry_delay | float | 1.0 | 0–10 | 网络重试等待（秒）。 |

## 4) [system] keys

| key | type | default | range | 说明 |
| --- | --- | --- | --- | --- |
| log_level | str | INFO | N/A | 日志级别。 |
| system_log_file | str | logs/system_runtime.log | N/A | 系统日志文件路径。 |
| enable_trade_history | bool | True | N/A | 是否记录交易历史。 |
| trade_record_file | str | logs/trade_records.json | N/A | 交易记录文件路径。 |

## 5) [api] keys（来自 secrets.ini）

> `secrets.ini` 与 `settings.ini` 分开存放，敏感信息不应提交到版本库。

| key | type | default | range | 说明 |
| --- | --- | --- | --- | --- |
| api_key | str | 空字符串 | N/A | API Key。 |
| secret_key | str | 空字符串 | N/A | API Secret。 |
| passphrase | str | 空字符串 | N/A | API Passphrase。 |
| flag | str | 1 | N/A | 交易环境标识：`0`=实盘，`1`=模拟盘。 |

## 6) 合规示例

**settings.ini（示例）**

```ini
[trading]
initial_usdt = 1000
initial_usdc = 500
initial_btc = 0.0
fee_rate = 0.001
fee_rate_btc_usdt = 0.0008
slippage_tolerance = 0.002
min_profit_threshold = 0.003
order_timeout = 5
min_trade_amount = 100
monitor_interval = 1
enable_profit_validation = false
max_profit_rate_threshold = 0.01
max_simulated_profit_rate = 0.005
max_price_spread = 0.02
max_stablecoin_spread = 0.005
stablecoin_price_range_min = 0.98
stablecoin_price_range_max = 1.02
path1 = {"route": "BTC->USDT->USDC", "assets": ["BTC", "USDT", "USDC"]}

[risk]
max_position_ratio = 0.2
max_single_trade_ratio = 0.1
min_arbitrage_interval = 10
max_daily_trades = 100
max_daily_loss_ratio = 0.05
stop_loss_ratio = 0.1
network_retry_count = 3
network_retry_delay = 1

[system]
log_level = INFO
system_log_file = logs/system_runtime.log
enable_trade_history = true
trade_record_file = logs/trade_records.json
```

**secrets.ini（示例）**

```ini
[api]
api_key = your_api_key_here
secret_key = your_secret_key_here
passphrase = your_passphrase_here
flag = 1
```
