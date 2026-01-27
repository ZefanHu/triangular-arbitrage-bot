# README 与代码不一致清单

> 说明：以代码为事实来源，分级 P0/P1/P2 并给出建议更新方向（不改 README）。

## 1) 运行（Run）

- **P1 — README 声称存在“测试模式 (test)”与多种键盘控制**
  - **证据**：`main.py` 仅提供 Auto/Monitor 模式选择，未实现 test 模式与 Space/R/Q 键盘控制逻辑。
  - **建议**：更新 README 运行模式描述，仅保留 Auto/Monitor；移除或改写键盘控制说明。

- **P2 — README 的运行示例暗示直接 `python main.py` 即可完整启用交易**
  - **证据**：`ConfigManager.get_api_credentials()` 缺失时返回 None，`TradingController` 会进入 READ_ONLY 并禁用交易；`OKXClient`/`WebSocketManager` 在无凭据时仅启用公共能力。
  - **建议**：在运行步骤中说明未配置 secrets.ini 时进入只读/监控模式，可启动但无法交易或使用私有账户功能（并非启动失败）。

## 2) 配置（Config）

- **P0 — README 描述 `secrets.ini` 必须存在，但仓库默认仅有 `secrets.ini.example`**
  - **证据**：`ConfigManager.get_api_credentials()` 若缺少 secrets.ini 会返回 None；系统会进入 READ_ONLY，交易与私有账户功能被禁用。
  - **建议**：README 明确提示：启用真实交易/账户余额/私有频道需配置 secrets.ini；否则进入只读监控模式（仍可启动但不能交易）。

- **P1 — README 示例配置与 `settings.ini` 实际值不一致**
  - **证据**：
    - README 示例 `min_profit_threshold = 0.003`，而 `settings.ini` 为 `0.0001`。
    - README 示例 `fee_rate_btc_usdc = 0.001`，而 `settings.ini` 为 `0.0007`。
    - README 示例 `max_position_ratio = 0.3` / `max_single_trade_ratio = 0.15`，而 `settings.ini` 目前均为 `1`。
  - **建议**：统一 README 示例与 `settings.ini` 现值，或明确 README 为“示例值”。

- **P2 — README 表述 `slippage_tolerance` 为交易执行参数，但代码未实际使用该值**
  - **证据**：`ConfigManager` 读取 `slippage_tolerance`，但核心执行路径未引用。
  - **建议**：在 README 中标注该参数“暂未生效”，或在代码实现后再保留说明。

## 3) 依赖（Dependencies）

- **P2 — README 未明确 websockets/psutil 等依赖在 `requirements.txt` 中强制使用**
  - **证据**：`WebSocketManager` 依赖 websockets，`TradingController` 依赖 psutil。
  - **建议**：在 README “环境要求/依赖”部分补充关键依赖用途说明。

## 4) 测试命令（Tests）

- **P1 — README 列出的测试文件与仓库实际不一致**
  - **证据**：README 提到 `test_core_comprehensive.py` 与 `test_arbitrage_*.py`，但 `tests/` 目录不存在这些文件。
  - **建议**：更新 README 的测试文件清单，仅保留实际存在的 `test_run_core.py` / `test_models.py` / `test_misc.py`。

- **P2 — README 的“测试模式”入口与代码不一致**
  - **证据**：README 提到主程序 test mode，但 `main.py` 未提供 test mode 入口。
  - **建议**：将测试流程统一到 `tests/test_run_core.py` 等脚本说明中。
