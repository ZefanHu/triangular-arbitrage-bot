# 测试说明

## 数据层集成测试

### 概述
`test_data_integration.py` 提供了完整的数据层集成测试，使用真实的OKX模拟盘API进行测试。

### 测试覆盖范围

#### 1. REST API连接测试 (`TestRESTAPIConnection`)
- **test_rest_get_balance**: 测试获取账户余额
  - 验证返回数据格式
  - 验证包含主要币种（USDT、USDC、BTC）
  - 验证数据类型和数值范围

- **test_rest_get_orderbook**: 测试获取订单簿
  - 验证订单簿数据结构
  - 验证买卖盘数据格式
  - 验证价格排序（买盘降序，卖盘升序）
  - 验证数据有效性

#### 2. WebSocket连接测试 (`TestWebSocketConnection`)
- **test_websocket_connection**: 测试基本连接功能
  - 验证连接建立和断开
  - 验证连接状态检查

- **test_websocket_subscription_and_data_receiving**: 测试订阅和数据接收
  - 验证订阅订单簿数据
  - 验证实时数据接收
  - 验证数据格式和持续性

- **test_websocket_reconnection**: 测试断线重连
  - 模拟连接断开
  - 验证断线检测机制

#### 3. 数据采集器测试 (`TestDataCollector`)
- **test_data_collector_start_stop**: 测试启动和停止
  - 验证数据采集器生命周期
  - 验证状态管理

- **test_data_collector_sync_mechanism**: 测试同步机制
  - 验证数据实时同步
  - 验证订单簿和余额获取
  - 验证数据更新回调

- **test_data_collector_cache_mechanism**: 测试缓存机制
  - 验证数据缓存效果
  - 验证缓存性能
  - 验证数据新鲜度检查

- **test_data_collector_balance_sync**: 测试余额同步
  - 验证定期同步机制
  - 验证缓存更新策略

### 运行测试

#### 方法1：使用便捷脚本
```bash
python run_integration_tests.py
```

#### 方法2：直接运行测试文件
```bash
python -m pytest tests/test_data_integration.py -v
```

#### 方法3：运行单个测试类
```bash
python -m unittest tests.test_data_integration.TestRESTAPIConnection -v
```

### 测试前准备

1. **配置API凭据**：
   - 确保 `config/secrets.ini` 包含有效的模拟盘API凭据
   - 设置 `flag=1` 使用模拟盘

2. **网络环境**：
   - 确保可以访问OKX API服务器
   - 建议使用稳定的网络连接

3. **测试环境**：
   - 创建 `logs/` 目录存放测试日志
   - 确保有足够的权限创建文件

### 测试超时设置

- 默认超时时间：30秒
- WebSocket连接超时：30秒
- 数据接收超时：30秒

### 注意事项

1. **API限流**：
   - 模拟盘API可能有频率限制
   - 如果测试失败，请稍后重试

2. **网络延迟**：
   - 网络状况可能影响测试结果
   - 超时错误通常是网络问题

3. **数据变化**：
   - 市场数据实时变化
   - 某些验证可能因数据变化而失败

4. **并发测试**：
   - 避免同时运行多个测试实例
   - 可能导致资源竞争

### 故障排查

#### 常见错误及解决方案

1. **"无法获取API凭据"**
   - 检查 `config/secrets.ini` 文件是否存在
   - 验证API凭据格式是否正确

2. **"WebSocket连接失败"**
   - 检查网络连接
   - 验证防火墙设置
   - 确认API凭据有效

3. **"数据接收超时"**
   - 检查网络稳定性
   - 尝试增加超时时间
   - 验证交易对是否有效

4. **"缓存测试失败"**
   - 确保有足够的数据接收时间
   - 检查系统时间同步

### 性能基准

- REST API响应时间：< 1秒
- WebSocket连接时间：< 5秒
- 数据接收延迟：< 2秒
- 缓存访问时间：< 100ms

### 扩展测试

如需添加新的测试：

1. 继承相应的测试基类
2. 实现测试方法（以`test_`开头）
3. 在测试套件中注册新测试
4. 更新此文档

### 日志文件

测试日志保存在 `logs/integration_test_YYYYMMDD_HHMMSS.log`，包含：
- 测试执行步骤
- API响应数据
- 错误信息和堆栈跟踪
- 性能指标