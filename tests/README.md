# TaoLi 测试套件说明文档

## 目录

- [概述](#概述)
- [测试文件分类](#测试文件分类)
- [测试文件说明](#测试文件说明)
- [使用方法](#使用方法)
- [测试覆盖率](#测试覆盖率)
- [注意事项](#注意事项)

## 概述

本目录包含 TaoLi 三角套利系统的完整测试套件，涵盖单元测试、集成测试和性能测试。所有测试都使用 OKX 的模拟交易 API 进行，确保不会产生真实交易。

## 测试文件分类

### 1. pytest 标准测试文件
- **test_models.py**: 可通过 pytest 自动发现和运行
- **特点**: 使用标准的 pytest 测试函数格式

### 2. 独立运行的测试脚本
- **test_run_core.py**: 支持 pytest 运行，但主要设计为独立脚本
- **test_misc.py**: 必须独立运行，不支持 pytest（需要命令行参数）
- **特点**: 使用 argparse 处理命令行参数，有自定义的运行逻辑

## pytest 配置说明

测试框架使用 pytest，配置文件为 `pytest.ini`。默认配置：
- 自动发现 test_*.py 文件（仅限标准 pytest 格式）
- 显示详细输出 (-v)
- 简短的错误信息格式 (--tb=short)
- 生成测试日志到 tests/logs/pytest.log
- 不自动生成覆盖率报告（需要时通过命令行参数指定）

## 测试文件说明

### 1. test_models.py
**用途**: 测试所有数据模型类的功能

**测试内容**:
- ArbitragePath: 套利路径验证和交易对生成
- ArbitrageOpportunity: 套利机会计算和验证
- OrderBook: 订单簿数据结构和操作
- Portfolio: 投资组合管理
- Trade: 交易对象和状态管理

**运行方式**:
```bash
# 使用pytest运行（推荐）
pytest tests/test_models.py -v

# 或直接运行脚本（会自动生成覆盖率报告）
python3 tests/test_models.py
```

**预期输出**:
- 终端显示所有测试用例的执行结果
- 如果直接运行脚本，会在 `tests/reports/models_coverage_html/` 生成覆盖率报告
- 测试日志记录到 `tests/logs/pytest.log`（仅通过 pytest 运行时）
- 不会生成独立的日志文件

### 2. test_run_core.py
**用途**: 核心模块的综合功能测试

**测试内容**:
- 配置管理器验证
- OKX API 连接测试
- 数据采集器功能
- 套利计算引擎
- 风险管理器
- 交易执行器（安全模式）
- WebSocket 连接
- 系统集成测试

**运行方式**:
```bash
# 快速测试 - 验证核心功能（推荐）
python3 tests/test_run_core.py

# 完整测试 - 运行所有测试用例
python3 tests/test_run_core.py --full

# 生成覆盖率报告
python3 tests/test_run_core.py --coverage

# 使用pytest运行（仅运行基础测试）
pytest tests/test_run_core.py -v
```

**预期输出**:
- 生成日志文件：`tests/logs/test_core_YYYYMMDD_HHMMSS.log`（每次运行都会生成新文件）
- 终端显示各个测试模块的执行结果（✓ 或 ✗）
- 如果使用 --coverage 参数，会在 `tests/reports/core_coverage_html/` 生成覆盖率报告
- 快速测试：30-60秒内完成核心功能验证
- 完整测试：运行所有测试用例，包括性能和错误处理测试

### 3. test_misc.py
**用途**: 套利系统的杂项专项测试集合（必须独立运行，不支持 pytest）

**测试内容**:
1. **套利修复效果测试**
   - 时间戳一致性检查
   - 数据新鲜度验证
   - 虚假套利机会过滤
   - 实时数据同步性测试

2. **详细套利计算分析**
   - 逐步分解套利路径计算
   - 验证手续费计算准确性
   - 分析价格滑点影响
   - 支持自定义目标利润率验证

3. **深度数据验证**
   - 实时获取市场数据
   - 验证订单簿有效性
   - 检查价格合理性
   - 分析套利机会的真实性

**运行方式**:
```bash
# 注意：必须使用 python3 直接运行，不能使用 pytest

# 运行套利修复效果测试（默认3分钟）
python3 tests/test_misc.py --fix
python3 tests/test_misc.py --fix --duration 5  # 运行5分钟

# 运行详细计算分析（默认验证5.37%利润率）
python3 tests/test_misc.py --breakdown
python3 tests/test_misc.py --breakdown --profit-rate 0.03  # 验证3%利润率

# 运行数据验证测试
python3 tests/test_misc.py --verify

# 运行所有测试
python3 tests/test_misc.py --all

# 查看帮助信息
python3 tests/test_misc.py --help
```

**预期输出**:
- 生成日志文件：`tests/logs/test_misc_main.log`（所有测试模式共享）
- 套利修复测试（--fix）：
  - 终端显示实时套利机会统计
  - 测试结束后显示套利机会率汇总
- 详细计算分析（--breakdown）：
  - 终端显示详细的计算步骤
  - 生成 JSON 文件：`tests/outputs/test_misc_arbitrage_breakdown.json`
- 数据验证测试（--verify）：
  - 终端显示数据验证结果
  - 显示套利机会的真实性分析

## 测试覆盖率

### 运行完整覆盖率测试
```bash
# 测试所有pytest兼容文件并生成综合报告（不包括test_misc.py）
pytest tests/ -v --cov=core --cov=models --cov=utils --cov-report=html:tests/reports/coverage_html --cov-report=term-missing

# 分别测试不同模块
pytest tests/test_models.py -v --cov=models --cov-report=term-missing
pytest tests/test_run_core.py -v --cov=core --cov-report=term-missing

# 只运行pytest测试，不生成覆盖率报告
pytest tests/ -v -s

# 运行所有测试（包括非pytest文件）
# 1. 先运行pytest测试
pytest tests/ -v -s
# 2. 再运行独立测试脚本
python3 tests/test_misc.py --all
```

### 覆盖率目标
- models/: >95%
- core/: >80%
- utils/: >70%
- 整体: >80%

## 注意事项

1. **API 凭据配置**
   - 确保 `config/secrets.ini` 文件已正确配置
   - 使用 OKX 模拟交易 API（flag='1'）

2. **网络要求**
   - 部分测试需要稳定的网络连接
   - WebSocket 测试可能受网络延迟影响

3. **测试顺序**
   - 建议先运行 `test_models.py` 验证基础功能
   - 然后运行 `test_run_core.py` 进行集成测试
   - 最后运行 `test_misc.py` 进行专项测试

4. **日志文件和输出文件说明**
   - 测试日志保存在 `tests/logs/` 目录
     - `pytest.log`: pytest运行时的综合日志（包含所有通过pytest运行的测试）
     - `test_core_YYYYMMDD_HHMMSS.log`: test_run_core.py运行时生成（每次运行新文件）
     - `test_misc_main.log`: test_misc.py运行时生成（所有测试模式共享）
     - test_models.py不生成独立日志文件
   - JSON输出文件保存在 `tests/outputs/` 目录
     - `test_misc_arbitrage_breakdown.json`: 运行 test_misc.py --breakdown 时生成
   - 覆盖率报告保存在 `tests/reports/` 目录
     - `coverage_html/`: pytest综合覆盖率报告
     - `models_coverage_html/`: 直接运行test_models.py时生成
     - `core_coverage_html/`: 运行test_run_core.py --coverage时生成

5. **并行测试**
   - 避免同时运行多个测试文件，可能导致 API 限流
   - WebSocket 测试不支持并行运行

6. **测试环境清理**
   - 测试完成后自动清理临时数据
   - 不会影响生产环境配置

## 快速开始

```bash
# 1. 配置API凭据
cp config/secrets.ini.example config/secrets.ini
# 编辑 secrets.ini 填入模拟交易API凭据

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行快速测试验证环境
python3 tests/test_run_core.py

# 4. 运行pytest测试套件（仅test_models.py和部分test_run_core.py）
pytest tests/ -v -s

# 5. 运行所有测试（包括test_misc.py）
pytest tests/ -v -s && python3 tests/test_misc.py --all

# 6. 运行测试并生成覆盖率报告
pytest tests/ -v --cov=core --cov=models --cov=utils --cov-report=html:tests/reports/coverage_html
```

## 测试执行总结

| 测试文件 | pytest支持 | 独立运行 | 生成日志 | 生成报告 | 生成其他文件 |
|---------|-----------|---------|---------|---------|------------|
| test_models.py | ✓ | ✓ | pytest.log | models_coverage_html | - |
| test_run_core.py | ✓ | ✓ | test_core_*.log | core_coverage_html | - |
| test_misc.py | ✗ | ✓ | test_misc_main.log | - | test_misc_arbitrage_breakdown.json |

## 故障排查

1. **API连接失败**
   - 检查 secrets.ini 配置
   - 确认使用模拟交易环境（flag='1'）
   - 验证网络连接

2. **测试超时**
   - 增加 pytest 超时时间：`pytest --timeout=300`
   - 检查网络延迟
   - 使用快速测试模式

3. **覆盖率报告生成失败**
   - 确保安装了 pytest-cov：`pip install pytest-cov`
   - 检查 tests/reports 目录权限
   - 清理旧的覆盖率数据：`rm -rf .coverage*`

4. **日志文件位置问题**
   - 所有日志现在都生成在 `tests/logs/` 目录下
   - 如果在项目根目录看到日志，可能是旧文件，可以安全删除
   - test_misc.py的日志和JSON文件只在运行特定参数时生成：
     - 需要使用 --fix、--breakdown 或 --verify 参数
     - 不会通过 pytest 命令生成