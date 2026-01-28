# README 与代码不一致清单

- Last audited: 2026-01-28
- Baseline commit: 4792c0f
- Scope: README.md vs (main.py / core/* / config/* / requirements.txt / tests/*)

> 说明：本文件只记录“仍然存在的差异”，已解决项不会长期保留在这里（但会在 PR 描述中总结移除内容）。

## Summary

- Open gaps: 3 (P0: 0 / P1: 1 / P2: 2)
- 本次收敛移除：1 条
- 本次新增：3 条

## 1) 运行（Run）

- 当前未发现 README 与代码/配置/测试之间的运行差异。

## 2) 配置（Config）

- **P1 — README 示例包含已不再受支持的配置键，触发 fail-fast 校验**
  - README：`rebalance_threshold` 与 `balance_check_interval` 仍出现在配置示例中。（README.md L168-L169；README.md L213）
  - 代码/配置/测试：`SETTINGS_SCHEMA` 与 `DYNAMIC_KEY_RULES` 未包含上述键，`validate_config` 会将未知键视为错误并抛出 `ValueError`。（config/config_manager.py L9-L57；config/config_manager.py L299-L364；tests/test_slippage_and_config.py L34-L51）
  - 影响：用户直接复制 README 示例将导致配置验证失败，程序启动即报错。
  - 建议：从 README 示例中移除这些键，或补充说明已移除/当前不再支持。

- **P2 — README 仍指导使用已弃用的 `price_adjustment`**
  - README：交易参数示例包含 `price_adjustment`。（README.md L179-L185）
  - 代码/配置/测试：`price_adjustment` 不在 `SETTINGS_SCHEMA` 中，仅以弃用映射方式被替换为 `slippage_tolerance`。（config/config_manager.py L9-L61；config/config_manager.py L373-L383）
  - 影响：用户会误以为 `price_adjustment` 仍是正式配置项，实际仅作为弃用兼容键处理并会触发警告。
  - 建议：README 用 `slippage_tolerance` 替代 `price_adjustment`，并说明旧键已弃用。

## 3) 依赖（Dependencies）

- 当前未发现 README 与依赖配置之间的差异。

## 4) 测试命令（Tests）

- **P2 — README 未列出新增的 `test_slippage_and_config.py`，也未提示需要 pytest**
  - README：tests 列表仅包含 `test_run_core.py` / `test_models.py` / `test_misc.py`。（README.md L46-L49；README.md L266-L269）
  - 代码/配置/测试：`tests/test_slippage_and_config.py` 存在且依赖 pytest。（tests/test_slippage_and_config.py L1-L51）
  - 影响：用户可能遗漏该测试文件，且按照 README 准备环境时不知需安装 pytest。
  - 建议：在 README 的测试清单中补充该文件，并说明运行该测试需要 pytest。
