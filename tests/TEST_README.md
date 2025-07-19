# Core模块测试系统

本测试系统为三角套利机器人的所有核心功能提供全面的测试验证，使用真实的OKX API获取市场数据，确保系统在实际环境中的稳定性和功能完整性。

## 🎯 测试目标

- **验证所有core模块功能正常**
- **检测模块间是否存在冲突**
- **使用真实OKX API测试（虚拟账户）**
- **确保系统稳定性和性能**

## 📋 测试覆盖范围

### 核心模块测试
1. **配置管理器 (config_manager)** - 配置加载和验证
2. **OKX客户端 (okx_client)** - API连接和数据获取
3. **数据采集器 (data_collector)** - REST和WebSocket数据整合
4. **套利引擎 (arbitrage_engine)** - 三角套利机会计算
5. **风险管理器 (risk_manager)** - 交易风险控制
6. **交易执行器 (trade_executor)** - 交易执行逻辑（安全模式）
7. **WebSocket管理器 (websocket_manager)** - 实时数据连接
8. **交易控制器 (trading_controller)** - 系统整体协调

### 系统测试
- **集成测试** - 各模块协作验证
- **性能测试** - 响应时间和资源使用
- **错误处理测试** - 异常恢复能力

## 🚀 快速开始

### 前置要求

1. **配置API密钥**
   ```bash
   cp config/secrets.ini.example config/secrets.ini
   # 编辑secrets.ini，填入你的OKX API密钥
   ```

2. **确保虚拟环境**
   ```bash
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

### 运行测试

#### 快速测试（推荐）
```bash
python run_core_tests.py
```
- 运行关键功能验证
- 约2-3分钟完成
- 适合日常检查

#### 完整测试
```bash
python run_core_tests.py --full
```
- 运行所有测试项目
- 约5-10分钟完成
- 生成详细报告

#### 直接运行综合测试
```bash
python test_core_comprehensive.py
```
- 最完整的测试套件
- 包含所有测试功能
- 生成JSON格式详细报告

## 📊 测试输出

### 实时日志
测试过程中会显示实时进度：
```
🔧 开始配置管理器测试...
✅ config_test 通过
🌐 开始OKX API测试...
✅ okx_api_test 通过
```

### 测试报告
完整测试会生成以下文件：
- `logs/core_test_YYYYMMDD_HHMMSS.log` - 详细测试日志
- `logs/core_test_report_YYYYMMDD_HHMMSS.json` - JSON格式测试报告

### 报告示例
```
==============================================================
Core模块综合测试报告
==============================================================
测试时间: 20250717_143022
运行时长: 156.78秒
总测试数: 10
通过测试: 9
失败测试: 1
成功率: 90.00%

详细结果:
✅ config_test: passed
✅ okx_api_test: passed
✅ data_collector_test: passed
✅ arbitrage_engine_test: passed
✅ risk_manager_test: passed
✅ trade_executor_test: passed
❌ websocket_test: failed
✅ integration_test: passed
✅ performance_test: passed
✅ error_handling_test: passed
```

## 🔧 API配置说明

### 必需配置
在 `config/secrets.ini` 中设置：

```ini
[api]
api_key = your_api_key_here
secret_key = your_secret_key_here
passphrase = your_passphrase_here
flag = 1  # 1=虚拟账户, 0=实盘账户
```

⚠️ **重要**: 
- 确保使用虚拟账户 (`flag = 1`)
- 不要将真实API密钥提交到版本控制
- 测试不会执行真实交易

## 🛡️ 安全保证

### 交易安全
- **只使用虚拟账户** - `flag = 1` 设置
- **交易执行器安全模式** - 只验证参数，不实际下单
- **风险管理验证** - 确保所有安全机制正常

### 数据安全
- **API密钥保护** - 不记录在日志中
- **本地测试** - 所有测试在本地环境执行
- **无敏感信息泄露** - 测试报告不包含密钥信息

## 📈 性能基准

### 预期响应时间
- **余额查询**: < 2秒
- **订单簿获取**: < 3秒
- **套利计算**: < 1秒
- **WebSocket连接**: < 5秒

### 资源使用
- **内存增长**: < 100MB
- **CPU使用**: 正常范围
- **网络请求**: 控制在合理频率

## 🐛 常见问题

### API连接失败
```
❌ okx_api_test 失败: API连接错误
```
**解决方案**:
1. 检查网络连接
2. 验证API密钥正确性
3. 确认API权限设置
4. 检查IP白名单设置

### WebSocket连接异常
```
❌ websocket_test 失败: WebSocket连接失败
```
**解决方案**:
1. 检查防火墙设置
2. 确认WebSocket端口未被占用
3. 验证代理设置

### 配置验证失败
```
❌ config_test 失败: 配置验证异常
```
**解决方案**:
1. 检查 `config/settings.ini` 格式
2. 验证数值范围合理性
3. 确认必需配置项存在

## 🔍 深度测试说明

### 套利引擎测试
- 验证三角套利路径配置
- 测试利润计算算法
- 检查手续费和滑点处理

### 风险管理测试
- 验证仓位限制机制
- 测试交易频率控制
- 检查资金安全保护

### 数据采集测试
- 验证REST API数据获取
- 测试WebSocket实时数据
- 检查数据缓存机制

## 📝 扩展测试

### 添加自定义测试
如需添加特定测试功能，在 `test_core_comprehensive.py` 中：

```python
async def test_custom_feature(self) -> bool:
    """自定义功能测试"""
    try:
        # 测试逻辑
        result = custom_test_logic()
        
        details = {'test_result': result}
        success = result is not None
        
        self.log_test_result('custom_test', success, details)
        return success
    except Exception as e:
        self.log_test_result('custom_test', False, {'error': str(e)})
        return False
```

### 测试环境配置
可在 `config/settings.ini` 中调整测试参数：
- 最小交易金额
- 超时时间设置
- 重试次数配置

## 📞 支持

如遇到测试问题：
1. 查看详细日志文件
2. 检查测试报告JSON
3. 验证配置文件正确性
4. 确认网络环境稳定

---

**注意**: 本测试系统专为开发和验证目的设计，确保在生产环境部署前所有测试通过。