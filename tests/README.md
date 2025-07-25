# 测试目录说明

本目录包含项目的所有测试文件和测试相关配置，确保代码质量和功能正确性。

## 目录结构

```
tests/
├── README.md                   # 本说明文件
├── __init__.py                # Python包初始化文件
├── pytest.ini                # pytest配置文件
├── test_run_core.py           # 核心功能快速测试脚本
├── test_core_comprehensive.py # 核心功能综合测试
├── test_models.py             # 模型类单元测试
├── logs/                      # 测试日志目录
│   └── pytest.log            # pytest执行日志
└── reports/                   # 测试报告目录
    ├── coverage.xml           # 覆盖率XML报告
    ├── coverage_html/         # 覆盖率HTML报告
    └── junit.xml              # JUnit格式测试报告
```

## 主要测试文件

### 1. test_run_core.py - 核心功能测试脚本

这是一个功能全面的测试入口脚本，支持快速测试和完整测试模式。

#### 使用方法

**快速测试**（推荐日常使用）：
```bash
python tests/test_run_core.py
```

**完整测试**：
```bash
python tests/test_run_core.py --full
```

**覆盖率测试**：
```bash
python tests/test_run_core.py --coverage
```

#### 功能特点

- **快速测试模式**：运行核心功能验证，预计耗时30-60秒
- **完整测试模式**：运行所有测试用例，包含详细的功能验证
- **覆盖率报告**：生成代码覆盖率报告，支持HTML和XML格式
- **性能分析**：显示每个测试的执行时间和性能统计
- **错误诊断**：提供详细的错误信息和修复建议

#### 测试范围

1. **配置验证** - 检查配置文件的有效性和完整性
2. **OKX API连接** - 验证API连接和基础功能
3. **数据采集** - 测试市场数据采集功能
4. **套利计算** - 验证套利机会识别和计算
5. **风险管理** - 测试风险控制和仓位管理
6. **交易执行** - 验证交易执行器功能（安全模式）
7. **WebSocket连接** - 测试实时数据流连接
8. **系统集成** - 验证各模块间的协作
9. **性能监控** - 检查系统性能指标
10. **错误处理** - 测试异常情况的处理能力

### 2. test_models.py - 模型类单元测试

针对`models/`目录下所有模型类的详细单元测试。

#### 使用方法

**运行所有模型测试**：
```bash
pytest tests/test_models.py -v
```

**运行特定测试类**：
```bash
pytest tests/test_models.py::TestArbitragePath -v
```

**生成覆盖率报告**：
```bash
python tests/test_models.py
```

#### 测试覆盖的模型类

1. **ArbitragePath** - 套利路径模型
   - 有效路径验证
   - 交易对生成
   - 交易方向计算
   - 三角套利和多步套利支持

2. **ArbitrageOpportunity** - 套利机会模型
   - 利润计算
   - 机会验证
   - 过期检查
   - 金额充足性验证

3. **OrderBook** - 订单簿模型
   - 订单簿有效性检查
   - 最优价格获取
   - 价差计算
   - 深度数据处理

4. **Portfolio** - 投资组合模型
   - 余额管理
   - 资产检查
   - 余额操作（增加、减少、更新）
   - 投资组合复制和摘要

5. **Trade** - 交易模型
   - 交易参数验证
   - 订单参数转换
   - 所需余额计算
   - 交易方向判断

#### 真实API测试

使用`@pytest.mark.api`和`@pytest.mark.network`标记的测试需要真实的API连接：

```bash
# 运行真实API测试
pytest tests/test_models.py -m "api and network" -v

# 跳过真实API测试
pytest tests/test_models.py -m "not api" -v
```

### 3. test_core_comprehensive.py - 核心功能综合测试

包含`CoreTester`类，提供详细的核心功能测试实现。由`run_core_tests.py`调用。

## 配置文件

### pytest.ini

pytest的主配置文件，定义了测试发现、执行和报告的规则。

#### 主要配置项

- **测试发现**：自动发现`test_*.py`文件
- **标记系统**：定义测试类型标记（unit, integration, api, network等）
- **覆盖率配置**：自动生成代码覆盖率报告
- **日志配置**：设置测试日志的输出格式和级别
- **超时设置**：防止测试无限运行
- **异步支持**：支持asyncio异步测试

#### 测试标记

- `@pytest.mark.unit` - 单元测试（无外部依赖）
- `@pytest.mark.integration` - 集成测试（可能需要网络/API）
- `@pytest.mark.api` - 需要API访问的测试
- `@pytest.mark.network` - 需要网络连接的测试
- `@pytest.mark.slow` - 运行时间较长的测试
- `@pytest.mark.trading` - 涉及交易操作的测试

## 其他目录和文件

### logs/ - 测试日志目录

- `pytest.log` - pytest执行的详细日志，包含所有测试的运行记录

### reports/ - 测试报告目录

- `coverage.xml` - 机器可读的覆盖率报告（XML格式）
- `coverage_html/` - 人类可读的覆盖率报告（HTML格式）
- `junit.xml` - JUnit格式的测试结果报告，用于CI/CD集成

### .core_coveragerc - 覆盖率配置文件

专门为core模块定制的覆盖率配置，定义了需要包含和排除的文件。

## 使用建议

### 日常开发

1. **开发过程中**：运行快速测试确保基本功能正常
   ```bash
   python tests/test_run_core.py
   ```

2. **功能完成后**：运行完整测试确保所有功能正常
   ```bash
   python tests/test_run_core.py --full
   ```

3. **提交代码前**：生成覆盖率报告确保测试充分
   ```bash
   python tests/test_run_core.py --coverage
   ```

### 持续集成

使用pytest命令进行自动化测试：

```bash
# 运行所有测试
pytest tests/ -v

# 只运行单元测试
pytest tests/ -m "unit" -v

# 跳过需要网络的测试
pytest tests/ -m "not network" -v

# 生成覆盖率报告
pytest tests/ --cov=core --cov=models --cov-report=html
```

### 调试和排错

1. **查看详细日志**：
   ```bash
   tail -f tests/logs/pytest.log
   ```

2. **运行特定测试**：
   ```bash
   pytest tests/test_models.py::TestTrade::test_valid_trade -v -s
   ```

3. **查看覆盖率报告**：
   打开`tests/reports/coverage_html/index.html`查看详细的覆盖率分析

## 注意事项

1. **API凭据**：真实API测试需要正确配置`config/secrets.ini`文件
2. **网络连接**：部分测试需要稳定的网络连接
3. **测试环境**：建议在独立的测试环境中运行，避免影响生产数据
4. **资源占用**：完整测试可能消耗较多CPU和网络资源
5. **测试时间**：完整测试可能需要几分钟时间，请耐心等待

## 贡献指南

添加新测试时，请遵循以下规范：

1. **命名规范**：测试文件以`test_`开头，测试函数以`test_`开头
2. **文档说明**：为测试函数添加清晰的文档字符串
3. **标记分类**：正确使用pytest标记分类测试类型
4. **错误处理**：确保测试能优雅处理各种异常情况
5. **清理资源**：测试结束后清理临时资源和连接

## 常见问题

**Q: 测试失败怎么办？**
A: 首先查看错误信息，然后检查配置文件和网络连接，最后查看详细日志文件。

**Q: 如何跳过某些测试？**
A: 使用pytest的`-m`参数跳过特定标记的测试，或使用`--ignore`跳过特定文件。

**Q: 覆盖率报告在哪里？**
A: HTML格式报告在`tests/reports/coverage_html/index.html`，XML格式在`tests/reports/coverage.xml`。

**Q: 真实API测试安全吗？**
A: 测试使用只读API调用和小金额测试交易，不会影响实际资金安全。