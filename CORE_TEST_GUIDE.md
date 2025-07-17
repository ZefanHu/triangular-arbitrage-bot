# Core功能测试指南

## 🎯 快速开始

### 1. 配置API密钥
```bash
# 复制示例配置文件
cp config/secrets.ini.example config/secrets.ini

# 编辑配置文件，填入OKX API密钥
# 确保 flag = 1 (使用虚拟账户)
```

### 2. 运行测试
```bash
# 快速测试（推荐）
python run_core_tests.py

# 完整测试
python run_core_tests.py --full

# 直接运行综合测试
python test_core_comprehensive.py
```

## 📋 测试内容

✅ **配置管理器** - 验证配置加载和参数验证  
✅ **OKX API客户端** - 测试API连接和数据获取  
✅ **数据采集器** - 验证REST和WebSocket数据整合  
✅ **套利计算引擎** - 测试三角套利机会识别  
✅ **风险管理器** - 验证交易风险控制机制  
✅ **交易执行器** - 测试交易逻辑（安全模式）  
✅ **WebSocket管理器** - 验证实时数据连接  
✅ **系统集成** - 测试模块间协作  
✅ **性能监控** - 检查响应时间和资源使用  
✅ **错误处理** - 验证异常恢复能力  

## 🛡️ 安全保证

- **虚拟账户测试** - 不涉及真实资金
- **安全模式执行** - 不实际下单交易
- **API密钥保护** - 不记录敏感信息

## 📊 测试结果

测试完成后会生成：
- **实时控制台输出** - 显示测试进度和结果
- **详细日志文件** - `logs/core_test_YYYYMMDD_HHMMSS.log`
- **JSON测试报告** - `logs/core_test_report_YYYYMMDD_HHMMSS.json`

## 🚨 注意事项

1. **确保网络连接稳定**
2. **使用虚拟账户进行测试**  
3. **检查API密钥权限设置**
4. **防火墙允许WebSocket连接**

## ✅ 成功标准

- **成功率 ≥ 80%** - 基本功能正常
- **API响应时间 < 5秒** - 性能在合理范围
- **无严重错误** - 系统稳定运行

---

**开始测试**: `python run_core_tests.py`