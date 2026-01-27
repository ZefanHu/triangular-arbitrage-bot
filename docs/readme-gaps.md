# README 与代码不一致清单

- Last audited: 2026-01-27
- Baseline commit: 902513c
- Scope: README.md vs (main.py / core/* / config/* / requirements.txt / tests/*)

> 说明：本文件只记录“仍然存在的差异”，已解决项不会长期保留在这里（但会在 PR 描述中总结移除内容）。

## Summary

- Open gaps: 1 (P0: 0 / P1: 0 / P2: 1)
- 本次收敛移除：7 条

## 1) 运行（Run）

- 当前未发现 README 与代码/配置/测试之间的运行差异。

## 2) 配置（Config）

- **P2 — README 将 `slippage_tolerance` 作为交易执行参数，但核心执行未使用**
  - README：`config/settings.ini` 示例将 `slippage_tolerance` 列为交易执行参数。（README.md L179-L181）
  - 代码/配置/测试：`ConfigManager` 读取 `slippage_tolerance`，但交易执行器仅消费 `order_timeout`/`price_adjustment`/`min_profit_threshold` 等参数，没有使用滑点参数。（config/config_manager.py L150-L165；core/trade_executor.py L114-L125）
  - 影响：README 暗示滑点容忍度会影响下单，但实际不会生效，容易造成配置误判。
  - 建议：在 README 标注“当前未生效/预留参数”，或在交易执行逻辑中接入该参数。

## 3) 依赖（Dependencies）

- 当前未发现 README 与依赖配置之间的差异。

## 4) 测试命令（Tests）

- 当前未发现 README 与测试脚本之间的差异。
