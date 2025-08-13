# TaoLi 测试套件说明文档

## 目录

- [概述](#概述)
- [测试文件说明](#测试文件说明)
- [使用方法](#使用方法)
- [测试覆盖率](#测试覆盖率)
- [注意事项](#注意事项)
- [快速开始](#快速开始)

## 概述

本目录包含 TaoLi 三角套利系统的完整测试套件，涵盖单元测试、集成测试和专项测试。所有测试都使用 OKX 的模拟交易 API 进行，确保不会产生真实交易。

所有测试基于标准的 Python unittest 框架，无需额外的测试框架依赖。

## 测试文件说明

### 1. test_models.py - 数据模型测试
**用途**: 测试所有数据模型类的功能

**测试内容**:
- ArbitragePath: 套利路径验证和交易对生成
- ArbitrageOpportunity: 套利机会计算和验证
- OrderBook: 订单簿数据结构和操作
- Portfolio: 投资组合管理
- Trade: 交易对象和状态管理

**运行方式**:
```bash
# 基础测试 - 快速验证核心功能
python3 tests/test_models.py

# 完整测试 - 运行所有测试用例
python3 tests/test_models.py --full

# 生成覆盖率报告
python3 tests/test_models.py --coverage
```

**输出文件**:
- 日志文件：`tests/logs/test_models_YYYYMMDD_HHMMSS.log`
- 覆盖率报告：`tests/reports/models_coverage_html/index.html`（使用--coverage参数时生成）

### 2. test_run_core.py - 核心功能测试
**用途**: 核心模块的综合功能测试

**测试内容**:
1. 配置管理器验证
2. OKX API 连接测试
3. 数据采集器功能
4. 套利计算引擎
5. 风险管理器
6. 交易执行器（安全模式）
7. WebSocket 连接（完整测试模式）
8. 系统集成测试（完整测试模式）
9. 性能和资源监控（完整测试模式）
10. 错误处理和恢复（完整测试模式）

**运行方式**:
```bash
# 基础测试 - 快速验证核心功能（30-60秒）
python3 tests/test_run_core.py

# 完整测试 - 运行所有测试用例
python3 tests/test_run_core.py --full

# 生成覆盖率报告
python3 tests/test_run_core.py --coverage
```

**输出文件**:
- 日志文件：`tests/logs/test_core_YYYYMMDD_HHMMSS.log`
- 测试报告：`tests/reports/core_test_report_YYYYMMDD_HHMMSS.json`
- 覆盖率报告：`tests/reports/core_coverage_html/index.html`（使用--coverage参数时生成）

### 3. test_misc.py - 专项测试集合
**用途**: 套利系统的专项测试集合

**测试内容**:
1. **套利检测准确性测试**（arbitrage-detection）
   - 时间戳一致性检查
   - 数据新鲜度验证
   - 虚假套利机会过滤
   - 实时数据同步性测试

2. **利润计算分析测试**（profit-calculation）
   - 逐步分解套利路径计算
   - 验证手续费计算准确性
   - 分析价格滑点影响
   - 支持自定义目标利润率验证

3. **深度数据验证测试**（data-validation）
   - 实时获取市场数据
   - 验证订单簿有效性
   - 检查价格合理性
   - 分析套利机会的真实性

**运行方式**:
```bash
# 默认运行 - 运行所有测试的快速版本
python3 tests/test_misc.py

# 运行特定测试
python3 tests/test_misc.py --test arbitrage-detection  # 套利检测准确性测试
python3 tests/test_misc.py --test profit-calculation   # 利润计算分析测试
python3 tests/test_misc.py --test data-validation      # 深度数据验证测试

# 带参数运行（仅profit-calculation支持）
python3 tests/test_misc.py --test profit-calculation --profit-rate 0.03  # 验证3%利润率
```

**输出文件**:
- 日志文件：`tests/logs/test_misc_YYYYMMDD_HHMMSS.log`
- JSON输出：`tests/outputs/test_misc_arbitrage_breakdown.json`（仅profit-calculation测试时生成）

## 测试覆盖率

### 运行覆盖率测试

#### 方式一：使用测试脚本内置功能
```bash
# 测试models模块覆盖率
python3 tests/test_models.py --coverage

# 测试core模块覆盖率
python3 tests/test_run_core.py --coverage
```

#### 方式二：使用coverage工具直接运行
```bash
# 使用coverage运行unittest
coverage run -m unittest tests.test_models
coverage run -m unittest tests.test_run_core

# 查看覆盖率报告
coverage report
coverage html  # 生成HTML报告

# 运行所有测试并生成覆盖率
coverage run -m unittest discover tests
coverage report
```

#### 方式三：直接使用unittest运行（不生成覆盖率）
```bash
# 运行单个测试文件
python -m unittest tests.test_models -v

# 发现并运行所有测试
python -m unittest discover tests -v
```

### 覆盖率目标
- models/: >95%
- core/: >80%
- utils/: >70%
- 整体: >80%

### 覆盖率报告位置
- HTML报告：`tests/reports/[module]_coverage_html/index.html`
- XML报告：`tests/reports/[module]_coverage.xml`

## 注意事项

### 1. API 凭据配置
- 确保 `config/secrets.ini` 文件已正确配置
- 使用 OKX 模拟交易 API（flag='1'）
- 不要使用真实交易 API 进行测试

### 2. 网络要求
- 部分测试需要稳定的网络连接
- WebSocket 测试可能受网络延迟影响
- 建议在网络状况良好的环境下运行测试

### 3. 测试顺序
- 建议先运行 `test_models.py` 验证基础功能
- 然后运行 `test_run_core.py` 进行集成测试
- 最后运行 `test_misc.py` 进行专项测试

### 4. 日志和输出文件
所有测试都会生成独立的带时间戳的日志文件：

| 测试文件 | 日志位置 | 其他输出 |
|---------|---------|---------|
| test_models.py | tests/logs/test_models_*.log | 覆盖率报告 |
| test_run_core.py | tests/logs/test_core_*.log | 测试报告JSON、覆盖率报告 |
| test_misc.py | tests/logs/test_misc_*.log | 套利分析JSON |

### 5. 并行测试
- 避免同时运行多个测试文件，可能导致 API 限流
- WebSocket 测试不支持并行运行

### 6. 测试环境清理
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
python3 tests/test_models.py      # 测试数据模型
python3 tests/test_run_core.py    # 测试核心功能
python3 tests/test_misc.py        # 运行专项测试

# 4. 运行完整测试
python3 tests/test_models.py --full
python3 tests/test_run_core.py --full

# 5. 生成覆盖率报告
python3 tests/test_models.py --coverage
python3 tests/test_run_core.py --coverage
```

## 测试执行总结

| 测试文件 | 默认模式 | 完整模式 | 覆盖率报告 | 预计耗时 |
|---------|---------|---------|-----------|---------|
| test_models.py | ✓ | ✓ | ✓ | 基础:10s / 完整:30s |
| test_run_core.py | ✓ | ✓ | ✓ | 基础:60s / 完整:3-5分钟 |
| test_misc.py | ✓ | - | - | 每个测试:1-2分钟 |

## 故障排查

### 1. API连接失败
- 检查 secrets.ini 配置
- 确认使用模拟交易环境（flag='1'）
- 验证网络连接

### 2. 测试超时
- 检查网络延迟
- 使用基础测试模式而非完整模式
- 考虑单独运行失败的测试

### 3. 覆盖率报告生成失败
- 确保安装了 coverage：`pip install coverage`
- 检查 tests/reports 目录权限
- 清理旧的覆盖率数据：`rm -rf .coverage*`

### 4. 日志文件问题
- 所有日志都生成在 `tests/logs/` 目录下
- 每次运行都会生成新的带时间戳的日志文件
- 可以定期清理旧的日志文件以节省空间