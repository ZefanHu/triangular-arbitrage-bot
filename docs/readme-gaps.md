# README 与代码不一致清单

- Last audited: 2026-03-05
- Baseline commit: 5f0db21
- Scope: README.md vs (main.py / core/* / config/* / requirements.txt / tests/*)

> 说明：本文件只记录"仍然存在的差异"，已解决项不会长期保留在这里（但会在 PR 描述中总结移除内容）。

## Summary

- Open gaps: 0 (P0: 0 / P1: 0 / P2: 0)
- 本次收敛移除：3 条（已于上一轮修复）
- 本次新增：0 条（本轮文档审查已同步修复所有新发现的差异）

## 1) 运行（Run）

- 当前未发现 README 与代码/配置/测试之间的运行差异。

## 2) 配置（Config）

- 当前未发现 README 与配置之间的差异。

  > **已关闭（上一轮）**：README 示例中的 `rebalance_threshold`、`balance_check_interval`、`price_adjustment` 已移除。
  > **已关闭（本轮）**：README 路径示例已更新为 ETH 路径（USDT->BTC->ETH->USDT），初始持有量已补充 `initial_eth`，手续费示例已替换为 ETH 相关交易对，风控参数值已与 settings.ini 对齐（max_position_ratio=0.3、max_single_trade_ratio=0.15）。

## 3) 依赖（Dependencies）

- 当前未发现 README 与依赖配置之间的差异。

## 4) 测试命令（Tests）

- 当前未发现 README 与测试文件列表之间的差异。

  > **已关闭（本轮）**：README 与 tests/README.md 均已补充 `test_precision.py`、`test_leg_recovery.py`、`test_trade_amount_flow.py`、`test_environment_gate.py` 四个新测试文件。
