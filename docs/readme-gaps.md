# README 与代码不一致清单

- Last audited: 2026-01-27
- Baseline commit: 85c1d44
- Scope: README.md vs (main.py / core/* / config/* / requirements.txt / tests/*)

> 说明：本文件只记录“仍然存在的差异”，已解决项不会长期保留在这里（但会在 PR 描述中总结移除内容）。

## Summary

- Open gaps: 2 (P0: 0 / P1: 1 / P2: 1)
- 本次收敛移除：7 条

## 1) 运行（Run）

- 当前未发现 README 与代码/配置/测试之间的运行差异。

## 2) 配置（Config）

- **P1 — README 标注“首次运行必须使用模拟盘”，但代码未强制限制**
  - README：安全提示中写明“首次运行必须使用模拟环境 (flag = 1 in secrets.ini)”（README.md L305-L309）
  - 代码/配置/测试：`ConfigManager.get_api_credentials()` 仅读取并返回 `flag`，`OKXClient` 直接使用该值初始化客户端，没有强制限制首次运行必须为模拟盘。（config/config_manager.py L225-L236；core/okx_client.py L23-L38）
  - 影响：README 暗示系统会强制阻止首次实盘，但实际只接受配置值，可能导致用户误解风险控制边界。
  - 建议：将 README 语气调整为“强烈建议/安全最佳实践”，或在代码中加入首次运行的强制校验。

- **P2 — README 将 `slippage_tolerance` 作为交易执行参数，但核心执行未使用**
  - README：`config/settings.ini` 示例将 `slippage_tolerance` 列为交易执行参数。（README.md L179-L181）
  - 代码/配置/测试：`ConfigManager` 读取 `slippage_tolerance`，但交易执行器仅消费 `order_timeout`/`price_adjustment`/`min_profit_threshold` 等参数，没有使用滑点参数。（config/config_manager.py L150-L165；core/trade_executor.py L114-L125）
  - 影响：README 暗示滑点容忍度会影响下单，但实际不会生效，容易造成配置误判。
  - 建议：在 README 标注“当前未生效/预留参数”，或在交易执行逻辑中接入该参数。

## 3) 依赖（Dependencies）

- 当前未发现 README 与依赖配置之间的差异。

## 4) 测试命令（Tests）

- 当前未发现 README 与测试脚本之间的差异。
