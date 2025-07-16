# Models 测试文档

本文档说明如何使用 `test_models.py` 文件测试models目录下的四个核心数据模型。

## 📋 测试覆盖范围

### 1. ArbitragePath (套利路径)
- ✅ 三角套利路径验证
- ✅ 多步套利路径支持
- ✅ 交易对生成算法
- ✅ 交易方向计算
- ✅ 路径有效性检查

### 2. ArbitrageOpportunity (套利机会)
- ✅ 机会创建和验证
- ✅ 利润率计算
- ✅ 过期时间检查
- ✅ 最小金额验证
- ✅ 盈利性判断

### 3. OrderBook (订单簿)
- ✅ 订单簿数据验证
- ✅ 最优买卖价格计算
- ✅ 价差和中间价计算
- ✅ 订单簿深度查询
- ✅ 空订单簿处理

### 4. Portfolio (投资组合)
- ✅ 余额管理操作
- ✅ 资产增减功能
- ✅ 余额充足性检查
- ✅ 投资组合复制
- ✅ 空投资组合处理

### 5. Trade (交易)
- ✅ 交易参数验证
- ✅ 买卖方向判断
- ✅ 资产需求计算
- ✅ 订单参数转换
- ✅ 交易价值计算

## 🚀 运行测试

### 基础测试 (单元测试)
```bash
# 运行所有单元测试
pytest tests/test_models.py -v

# 运行特定模型测试
pytest tests/test_models.py::TestArbitragePath -v
pytest tests/test_models.py::TestOrderBook -v
pytest tests/test_models.py::TestPortfolio -v
pytest tests/test_models.py::TestTrade -v
```

### 真实API测试 (集成测试)
```bash
# 运行所有真实API测试
pytest tests/test_models.py::TestModelsWithRealAPI -v --run-integration

# 运行特定API测试
pytest tests/test_models.py::TestModelsWithRealAPI::test_real_orderbook_data -v --run-integration
pytest tests/test_models.py::TestModelsWithRealAPI::test_real_arbitrage_path_with_api_data -v --run-integration
```

### 带详细日志的测试
```bash
# 查看详细日志输出
pytest tests/test_models.py::TestModelsWithRealAPI -v --run-integration -s
```

## 🔧 配置要求

### API 配置
测试需要正确配置 OKX API 凭据：

1. 复制 `config/secrets.ini.example` 为 `config/secrets.ini`
2. 填入真实的 API 凭据：
   ```ini
   [api]
   api_key = your_api_key_here
   secret_key = your_secret_key_here
   passphrase = your_passphrase_here
   flag = 1  # 1=模拟盘, 0=实盘
   ```

### 交易对支持
测试会验证以下交易对：
- BTC-USDT ✅
- ETH-USDT ✅
- BTC-USDC ✅
- USDT-USDC ✅
- BTC-ETH ❌ (可能无数据)

## 📊 测试结果解读

### 测试统计
```
✅ 26个单元测试通过 (0.06s)
✅ 4个API集成测试通过 (1.22s)
✅ 总计30个测试，100%通过率
```

### 成功案例
```
✅ 真实订单簿数据验证通过: BTC-USDT
✅ 最优买价: 118666.6
✅ 最优卖价: 118888.0  
✅ 价差: 221.4
✅ 真实余额数据验证通过
✅ 账户资产: USDC(59940.0), USDT(39990.0), BTC(0.099)等
```

### 套利路径验证
```
✅ 套利路径 USDT -> BTC -> USDC -> USDT 验证通过
⚠️  套利路径 USDT -> BTC -> ETH -> USDT 部分交易对数据无效
```

### 跳过的测试
- 如果没有 `--run-integration` 参数，API测试会被跳过
- 如果API凭据未配置，相关测试会被跳过
- 如果某些交易对无数据，相关测试会被跳过

### 修复历史
- **2025-07-16**: 修复了OKX API时间戳格式问题（`Invalid OK-ACCESS-TIMESTAMP`）
  - 问题：okex库的`get_timestamp()`函数生成格式为`2025-07-16T17:25:27.917+00:00Z`
  - 修复：移除多余的`+00:00`，正确格式为`2025-07-16T17:25:27.917Z`
  - 影响：所有需要认证的API调用（余额、订单等）

## 🐛 常见问题

### 1. API凭据错误
```
ValueError: 无法获取API凭据，请检查secrets.ini文件
```
**解决方案**: 检查 `config/secrets.ini` 文件是否存在且配置正确

### 2. 交易对无数据
```
WARNING: BTC-ETH订单簿数据为空
```
**解决方案**: 正常现象，某些交易对在特定时间可能无数据

### 3. 网络连接问题
```
ERROR: 获取订单簿失败: Connection timeout
```
**解决方案**: 检查网络连接，稍后重试

## 📈 性能指标

- 单元测试: ~0.06s (26个测试)
- API测试: ~1.22s (4个测试)
- 网络请求: 每个交易对 ~100ms
- 总测试时间: ~1.28s (完整测试套件)

## 🔍 调试技巧

1. **查看详细日志**: 添加 `-s` 参数
2. **只运行失败的测试**: 使用 `--lf` 参数
3. **并行运行测试**: 安装 `pytest-xdist` 并使用 `-n auto`
4. **生成测试报告**: 使用 `--html=report.html` 生成HTML报告

## 🎯 下一步

1. 添加更多交易对支持
2. 增加错误处理测试
3. 添加性能基准测试
4. 集成到CI/CD流程

---

*测试文件位置: `/tests/test_models.py`*
*创建日期: 2025-07-16*