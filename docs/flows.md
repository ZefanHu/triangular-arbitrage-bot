# Data & Trading Flows

## 关键状态/数据对象表（产生 → 消费 → 更新点）

| 对象 | 产生/更新点 | 主要消费者 | 备注 |
| --- | --- | --- | --- |
| **OrderBook** | DataCollector `_on_data_update()`（WS）或 `get_orderbook()`（REST fallback） | ArbitrageEngine `find_opportunities()`/`calculate_*` | 订单簿用于套利计算与监控显示；`get_arbitrage_orderbook()` 要求 500ms 新鲜度。 |
| **Opportunity**（Dict） | ArbitrageEngine `find_opportunities()` | TradingController `_trading_loop()` | 机会列表在主循环处理，并记录到 TradeLogger。 |
| **ArbitrageOpportunity** | TradingController `_process_opportunity_in_loop()` | RiskManager / TradeExecutor | 由 `ArbitragePath` 组装，用于风控与执行。 |
| **Trade / TradeResult** | TradeExecutor `_generate_trades()` / `_execute_single_trade()` / `_wait_order_filled()` | TradingController `_log_trade_result()` / `_handle_trade_result()` | 交易结果驱动统计、日志与风控记录。 |
| **Portfolio** | DataCollector `get_balance()`（REST） | TradingController `_process_opportunity_in_loop()` | 余额用于估算总资产与计算交易量；READ_ONLY/无凭据时可能为 None，余额不保证可用或更新。 |

## 行情数据流时序（WS/REST → DataCollector → OrderBook → ArbitrageEngine → TradingController）

```mermaid
sequenceDiagram
    participant WS as OKX WebSocket
    participant REST as OKX REST
    participant DC as DataCollector
    participant OB as OrderBook
    participant AE as ArbitrageEngine
    participant TC as TradingController

    WS-->>DC: 订单簿推送(snapshot/update)
    DC->>OB: _on_data_update() 创建/更新 OrderBook
    TC->>AE: find_opportunities()
    AE->>DC: get_arbitrage_orderbook(pair)
    alt 订单簿新鲜(<=500ms)
        DC-->>AE: OrderBook
    else 订单簿过期/缺失
        DC-->>AE: None
        AE->>DC: get_orderbook(pair) 作为监控回退
        DC-->>AE: OrderBook (可能不够新鲜)
    end
    alt 无机会
        AE-->>TC: [] (仅更新监控分析)
    else 有机会
        AE-->>TC: opportunities
    end
```

## 交易执行流时序（TradingController → ArbitrageEngine → RiskManager → TradeExecutor）

```mermaid
sequenceDiagram
    participant TC as TradingController
    participant AE as ArbitrageEngine
    participant DC as DataCollector
    participant RM as RiskManager
    participant TE as TradeExecutor
    participant OKX as OKX REST
    participant TL as TradeLogger

    TC->>AE: find_opportunities()
    AE-->>TC: opportunities
    TC->>DC: get_balance() -> Portfolio
    alt 余额不可用（READ_ONLY/无凭据）
        TC-->>TL: 仅记录机会与错误/监控信息
        TC-->>TC: 终止本次机会处理
    else 余额可用
        TC->>RM: check_arbitrage_frequency()
        alt 风控拒绝(频率)
            RM-->>TC: RiskCheckResult(passed=false)
            TC-->>TL: 记录拒绝原因
        else 频率通过
            TC->>RM: validate_opportunity(opportunity, total_balance)
            alt 风控拒绝(交易禁用/仓位/利润/过期等)
                RM-->>TC: RiskCheckResult(passed=false)
                TC-->>TL: 记录拒绝原因
            else 风控通过
                TC->>RM: calculate_position_size()
                RM-->>TC: trade_amount
                TC->>TE: execute_arbitrage(opportunity, trade_amount)
                TE->>OKX: get_balance / get_ticker / place_order / get_order_status
                alt 下单失败或超时
                    TE-->>OKX: cancel_order
                    TE-->>TC: success=false, error
                else 部分成交
                    TE->>OKX: 继续轮询
                    TE-->>TC: success=false (超时或取消)
                else 成功成交
                    TE-->>TC: success=true, TradeResult list
                end
                TC-->>TL: log_trade_executed(result)
                TC->>RM: record_arbitrage_attempt(success, profit)
            end
        end
    end
```

## 旁路/绕行的实际时序（测试/潜在入口）

> 生产主链路未发现绕过 TradingController 的下单路径。以下为测试/潜在旁路（需受控使用）。

```mermaid
sequenceDiagram
    participant Test as tests/*
    participant DC as DataCollector
    participant AE as ArbitrageEngine
    participant RM as RiskManager
    participant TE as TradeExecutor
    participant OKX as OKX REST

    Test->>DC: DataCollector()
    Test->>AE: ArbitrageEngine(DC)
    Test->>RM: RiskManager(config_manager)
    Test->>TE: TradeExecutor(OKXClient)
    TE->>OKX: place_order/get_order_status/cancel_order
```
