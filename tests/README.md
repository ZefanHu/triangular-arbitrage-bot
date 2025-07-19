# 三角套利机器人测试系统

本目录包含三角套利机器人的所有测试文件和相关文档，提供完整的测试覆盖和验证功能。

## 📁 目录结构

```
tests/
├── README.md                    # 本文件 - 测试系统总览
├── TEST_README.md              # Core模块测试详细说明
├── README_models.md            # 数据模型测试说明
├── run_core_tests.py           # 快速测试入口脚本
├── test_core_comprehensive.py  # 完整的Core模块测试套件
├── test_models.py              # 数据模型测试
├── debug_orderbook.py          # 订单簿调试工具
├── pytest.ini                 # pytest配置文件
├── logs/                       # 测试日志目录
└── reports/                    # 测试报告目录
```

## 🚀 快速开始

### 1. 环境准备

确保已激活虚拟环境：
```bash
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 2. API配置

配置OKX API密钥（使用虚拟账户）：
```bash
cp config/secrets.ini.example config/secrets.ini
# 编辑secrets.ini，设置API密钥和flag=1
```

### 3. 运行测试

#### 快速测试（推荐新手）
```bash
cd tests
python run_core_tests.py
```

#### 完整测试套件
```bash
cd tests
python test_core_comprehensive.py
```

#### 特定模块测试
```bash
cd tests
python -m pytest test_models.py -v
```

## 📋 测试类型

### 1. Core模块测试 (`test_core_comprehensive.py`)

**测试覆盖**：
- ✅ 配置管理器 - API密钥验证和配置加载
- ✅ OKX客户端 - REST API连接和数据获取
- ✅ 数据采集器 - 实时数据同步和缓存
- ✅ 套利引擎 - 三角套利机会计算
- ✅ 风险管理器 - 交易风险控制
- ✅ 交易执行器 - 订单执行逻辑（安全模式）
- ✅ WebSocket管理器 - 实时数据连接
- ✅ 系统集成测试 - 各模块协作验证

**运行方式**：
```bash
python test_core_comprehensive.py     # 完整测试
python run_core_tests.py             # 快速测试
```

### 2. 数据模型测试 (`test_models.py`)

**测试覆盖**：
- 订单簿模型 (`OrderBook`)
- 套利路径模型 (`ArbitragePath`)
- 投资组合模型 (`Portfolio`)
- 交易模型 (`Trade`)

**运行方式**：
```bash
python -m pytest test_models.py -v
```

### 3. 调试工具 (`debug_orderbook.py`)

订单簿数据格式调试和验证工具，帮助开发者理解OKX API返回的数据结构。

**运行方式**：
```bash
python debug_orderbook.py
```

## 📊 测试报告

### 实时输出
测试过程显示彩色进度：
```
🔧 开始配置管理器测试...
✅ config_test 通过
🌐 开始OKX API测试...
✅ okx_api_test 通过
⚠️  websocket_test 跳过 (网络问题)
```

### 详细报告
测试完成后生成：
- `logs/core_test_YYYYMMDD_HHMMSS.log` - 详细测试日志
- `logs/core_test_report_YYYYMMDD_HHMMSS.json` - 结构化测试报告

### 测试指标
- **成功率统计** - 通过/失败/跳过的测试数量
- **性能指标** - API响应时间和资源使用
- **错误详情** - 失败原因和解决建议

## 🛡️ 安全保证

### 交易安全
- **虚拟账户模式** - 所有测试使用模拟盘 (`flag=1`)
- **安全模式执行** - 交易执行器只验证参数，不实际下单
- **风险控制验证** - 确保所有安全机制正常运行

### 数据安全
- **API密钥保护** - 测试日志不记录敏感信息
- **本地执行** - 所有测试在本地环境运行
- **无数据泄露** - 报告不包含敏感凭据

## 🔧 配置文件

### pytest.ini
pytest测试框架配置，包含：
- 测试发现规则
- 输出格式设置
- 插件配置

### API配置要求
在 `config/secrets.ini` 中设置：
```ini
[api]
api_key = your_api_key_here
secret_key = your_secret_key_here
passphrase = your_passphrase_here
flag = 1  # 重要：必须使用虚拟账户
```

## 📈 性能基准

### 预期响应时间
- 余额查询：< 2秒
- 订单簿获取：< 3秒
- 套利计算：< 1秒
- WebSocket连接：< 5秒

### 资源使用
- 内存增长：< 100MB
- CPU使用：正常范围内
- 网络请求：合理频率

## 🐛 故障排查

### 常见问题

#### API连接失败
```
❌ okx_api_test 失败: API连接错误
```
**解决方案**：
1. 检查网络连接
2. 验证API密钥正确性
3. 确认IP白名单设置
4. 检查代理/防火墙配置

#### WebSocket连接问题
```
❌ websocket_test 失败: WebSocket连接失败
```
**解决方案**：
1. 检查防火墙WebSocket端口
2. 验证网络稳定性
3. 确认代理设置正确

#### 配置验证失败
```
❌ config_test 失败: 配置验证异常
```
**解决方案**：
1. 检查 `config/secrets.ini` 和 `config/settings.ini` 格式
2. 验证所有必需配置项存在
3. 确认数值范围合理

#### 导入路径错误
```
ModuleNotFoundError: No module named 'core'
```
**解决方案**：
1. 确保从 `tests/` 目录运行测试
2. 检查 `sys.path` 设置是否正确
3. 验证项目结构完整

## 📝 开发指南

### 添加新测试

1. **Core模块测试**：
   在 `test_core_comprehensive.py` 中添加新的测试方法：
   ```python
   async def test_new_feature(self) -> bool:
       """新功能测试"""
       try:
           # 测试逻辑
           result = await new_feature_test()
           success = result is not None
           self.log_test_result('new_feature_test', success, {'result': result})
           return success
       except Exception as e:
           self.log_test_result('new_feature_test', False, {'error': str(e)})
           return False
   ```

2. **数据模型测试**：
   在 `test_models.py` 中添加新的测试类或方法：
   ```python
   def test_new_model_functionality(self):
       """测试新模型功能"""
       # 测试实现
       pass
   ```

### 测试最佳实践

1. **使用描述性测试名称**
2. **提供清晰的错误信息**
3. **测试边界条件和错误情况**
4. **保持测试独立性**
5. **使用适当的断言**

## 📞 支持

遇到问题时：

1. **查看测试日志** - 检查 `logs/` 目录中的详细日志
2. **检查配置** - 验证API密钥和配置文件
3. **网络诊断** - 确认网络连接和防火墙设置
4. **查看报告** - 分析JSON格式的测试报告

## 📚 相关文档

- [`TEST_README.md`](TEST_README.md) - Core模块测试详细说明
- [`README_models.md`](README_models.md) - 数据模型测试说明
- [`../README.md`](../README.md) - 项目主要文档
- [`../FUNC_README.md`](../FUNC_README.md) - 功能特性说明

---

⚠️ **重要提醒**：
- 所有测试均使用虚拟账户，确保 `flag=1`
- 不会执行真实交易操作
- 测试前请确保网络环境稳定
- 定期更新API密钥以保持测试有效性