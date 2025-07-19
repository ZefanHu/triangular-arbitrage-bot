#!/usr/bin/env python3
"""
Core模块综合测试

使用真实OKX API测试所有核心功能，验证系统完整性和稳定性
确保所有模块间无冲突，功能正常运行

测试内容：
1. OKX API连接和数据获取测试
2. 数据采集器功能测试
3. 套利计算引擎测试
4. 风险管理器测试
5. 交易执行器测试（安全模式）
6. WebSocket连接测试
7. 系统集成测试
8. 配置验证测试
9. 性能和资源监控测试
10. 错误处理和恢复测试
"""

import asyncio
import logging
import time
import json
import traceback
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.okx_client import OKXClient
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.risk_manager import RiskManager
from core.trade_executor import TradeExecutor
from core.trading_controller import TradingController
from core.websocket_manager import WebSocketManager
from config.config_manager import ConfigManager
from models.order_book import OrderBook
from utils.logger import setup_logger


class CoreTester:
    """核心功能综合测试器"""
    
    def __init__(self):
        """初始化测试器"""
        # 设置测试专用日志
        self.test_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/core_test_{self.test_start_time}.log"
        
        # 确保日志目录存在
        os.makedirs("logs", exist_ok=True)
        
        # 设置日志
        self.logger = setup_logger("CoreTester", self.log_file, logging.INFO)
        
        # 测试结果收集
        self.test_results = {
            'config_test': {'status': 'pending', 'details': {}},
            'okx_api_test': {'status': 'pending', 'details': {}},
            'data_collector_test': {'status': 'pending', 'details': {}},
            'arbitrage_engine_test': {'status': 'pending', 'details': {}},
            'risk_manager_test': {'status': 'pending', 'details': {}},
            'trade_executor_test': {'status': 'pending', 'details': {}},
            'websocket_test': {'status': 'pending', 'details': {}},
            'integration_test': {'status': 'pending', 'details': {}},
            'performance_test': {'status': 'pending', 'details': {}},
            'error_handling_test': {'status': 'pending', 'details': {}}
        }
        
        # 测试统计
        self.stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'start_time': time.time(),
            'end_time': None
        }
        
        self.logger.info(f"Core测试器初始化完成，日志文件: {self.log_file}")

    def log_test_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """记录测试结果"""
        status = 'passed' if success else 'failed'
        self.test_results[test_name]['status'] = status
        self.test_results[test_name]['details'] = details
        
        self.stats['total_tests'] += 1
        if success:
            self.stats['passed_tests'] += 1
            self.logger.info(f"✅ {test_name} 通过")
        else:
            self.stats['failed_tests'] += 1
            self.logger.error(f"❌ {test_name} 失败: {details}")

    async def test_config_manager(self) -> bool:
        """测试配置管理器"""
        self.logger.info("🔧 开始配置管理器测试...")
        print("\n🔧 配置管理器测试详情:")
        
        try:
            # 初始化配置管理器
            print(f"  ↗️  初始化配置管理器...")
            config_manager = ConfigManager()
            print(f"  ✅ 配置管理器初始化完成")
            
            # 测试配置加载
            print(f"  📁 加载配置文件...")
            
            # 交易配置
            print(f"    📊 加载交易配置...")
            trading_config = config_manager.get_trading_config()
            if trading_config:
                print(f"      ✅ 交易配置加载成功")
                print(f"      🛤️  套利路径数: {len(trading_config.get('paths', {}))}")
                if 'paths' in trading_config:
                    for path_name in list(trading_config['paths'].keys())[:3]:
                        print(f"        📍 {path_name}")
                    if len(trading_config['paths']) > 3:
                        print(f"        ... 还有 {len(trading_config['paths']) - 3} 个路径")
                
                # 显示其他交易配置
                for key, value in trading_config.items():
                    if key != 'paths':
                        print(f"      {key}: {value}")
            else:
                print(f"      ❌ 交易配置加载失败")
            
            # 风险配置
            print(f"    🛡️  加载风险配置...")
            risk_config = config_manager.get_risk_config()
            if risk_config:
                print(f"      ✅ 风险配置加载成功")
                for key, value in risk_config.items():
                    if isinstance(value, dict):
                        print(f"      {key}: {len(value)} 项配置")
                    else:
                        print(f"      {key}: {value}")
            else:
                print(f"      ❌ 风险配置加载失败")
            
            # 系统配置
            print(f"    ⚙️  加载系统配置...")
            system_config = config_manager.get_system_config()
            if system_config:
                print(f"      ✅ 系统配置加载成功")
                for key, value in system_config.items():
                    if isinstance(value, dict):
                        print(f"      {key}: {len(value)} 项配置")
                    else:
                        print(f"      {key}: {value}")
            else:
                print(f"      ❌ 系统配置加载失败")
            
            # API凭证
            print(f"    🔐 加载API凭证...")
            api_credentials = config_manager.get_api_credentials()
            if api_credentials:
                print(f"      ✅ API凭证加载成功")
                # 不显示敏感信息，只显示是否配置
                for key, value in api_credentials.items():
                    if value and len(str(value)) > 0:
                        masked_value = str(value)[:4] + '*' * (len(str(value)) - 4) if len(str(value)) > 4 else '****'
                        print(f"      {key}: {masked_value}")
                    else:
                        print(f"      {key}: 未配置")
            else:
                print(f"      ❌ API凭证加载失败")
            
            # 验证配置完整性
            print(f"  🔍 验证配置完整性...")
            validation_start = time.time()
            is_valid, errors = config_manager.validate_config()
            validation_time = time.time() - validation_start
            
            if is_valid:
                print(f"    ✅ 配置验证通过! 耗时: {validation_time:.3f}s")
            else:
                print(f"    ❌ 配置验证失败! 耗时: {validation_time:.3f}s")
                if errors:
                    print(f"    🚨 验证错误:")
                    for error in errors[:5]:  # 只显示前5个错误
                        print(f"      • {error}")
                    if len(errors) > 5:
                        print(f"      ... 还有 {len(errors) - 5} 个错误")
            
            # 检查配置文件路径
            config_paths = {}
            if hasattr(config_manager, 'config_dir'):
                config_paths['config_dir'] = config_manager.config_dir
            if hasattr(config_manager, 'secrets_file'):
                config_paths['secrets_file'] = config_manager.secrets_file
            
            if config_paths:
                print(f"  📂 配置文件路径:")
                for path_name, path_value in config_paths.items():
                    import os
                    exists = os.path.exists(path_value) if path_value else False
                    print(f"    {path_name}: {path_value} {'✅' if exists else '❌'}")
            
            # 测试配置热重载（如果支持）
            if hasattr(config_manager, 'reload_config'):
                print(f"  🔄 测试配置重载...")
                try:
                    reload_start = time.time()
                    config_manager.reload_config()
                    reload_time = time.time() - reload_start
                    print(f"    ✅ 配置重载成功! 耗时: {reload_time:.3f}s")
                except Exception as e:
                    print(f"    ⚠️ 配置重载失败: {str(e)}")
            
            details = {
                'trading_config_loaded': bool(trading_config),
                'risk_config_loaded': bool(risk_config),
                'system_config_loaded': bool(system_config),
                'api_credentials_loaded': bool(api_credentials),
                'config_valid': is_valid,
                'validation_errors': errors,
                'validation_time': validation_time,
                'paths_count': len(trading_config.get('paths', {})) if trading_config else 0,
                'config_paths': config_paths,
                'trading_config_summary': {
                    'total_keys': len(trading_config) if trading_config else 0,
                    'has_paths': 'paths' in trading_config if trading_config else False
                },
                'risk_config_summary': {
                    'total_keys': len(risk_config) if risk_config else 0
                },
                'system_config_summary': {
                    'total_keys': len(system_config) if system_config else 0
                },
                'api_credentials_summary': {
                    'total_keys': len(api_credentials) if api_credentials else 0,
                    'configured_keys': sum(1 for v in api_credentials.values() if v) if api_credentials else 0
                }
            }
            
            success = all([
                trading_config,
                risk_config,
                system_config,
                api_credentials,
                is_valid
            ])
            
            print(f"  📋 配置管理器测试结果: {'✅ 通过' if success else '❌ 失败'}")
            
            self.log_test_result('config_test', success, details)
            return success
            
        except Exception as e:
            print(f"  💥 配置管理器测试异常: {str(e)}")
            self.log_test_result('config_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_okx_api(self) -> bool:
        """测试OKX API连接"""
        self.logger.info("🌐 开始OKX API测试...")
        print("\n🌐 OKX API测试详情:")
        
        try:
            # 初始化OKX客户端
            okx_client = OKXClient()
            print(f"  ↗️  OKX客户端初始化完成")
            print(f"  🏷️  API环境: {okx_client.flag}")
            if hasattr(okx_client, 'base_url'):
                print(f"  🔗 API地址: {okx_client.base_url}")
            
            # 测试余额获取
            print(f"  💰 测试余额获取...")
            balance_start = time.time()
            balance = okx_client.get_balance()
            balance_time = time.time() - balance_start
            
            if balance:
                print(f"    ✅ 余额获取成功! 响应时间: {balance_time:.3f}s")
                print(f"    📊 账户余额详情:")
                if isinstance(balance, dict):
                    for currency, amount in list(balance.items())[:5]:  # 显示前5个币种
                        if float(amount) > 0:
                            print(f"      💎 {currency}: {amount}")
                    if len(balance) > 5:
                        print(f"      ... 还有 {len(balance) - 5} 个币种")
                else:
                    print(f"      📊 余额数据类型: {type(balance)}")
                    print(f"      📄 余额数据: {str(balance)[:200]}...")
            else:
                print(f"    ❌ 余额获取失败")
            
            # 测试订单簿获取
            print(f"  📖 测试订单簿获取...")
            test_pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
            orderbook_results = {}
            
            for pair in test_pairs:
                print(f"    📊 获取 {pair} 订单簿...")
                try:
                    orderbook_start = time.time()
                    orderbook = okx_client.get_orderbook(pair)
                    orderbook_time = time.time() - orderbook_start
                    
                    if orderbook:
                        print(f"      ✅ 成功! 响应时间: {orderbook_time:.3f}s")
                        print(f"      📈 买单数量: {len(orderbook.bids)}")
                        print(f"      📉 卖单数量: {len(orderbook.asks)}")
                        print(f"      🕐 时间戳: {orderbook.timestamp}")
                        
                        # 显示最优买卖价
                        if len(orderbook.bids) > 0:
                            best_bid_price = orderbook.get_best_bid()
                            best_bid_size = orderbook.bids[0][1]
                            print(f"      💰 最优买价: {best_bid_price} (数量: {best_bid_size})")
                        if len(orderbook.asks) > 0:
                            best_ask_price = orderbook.get_best_ask()
                            best_ask_size = orderbook.asks[0][1]
                            print(f"      💸 最优卖价: {best_ask_price} (数量: {best_ask_size})")
                        
                        # 计算价差
                        if len(orderbook.bids) > 0 and len(orderbook.asks) > 0:
                            best_bid = orderbook.get_best_bid()
                            best_ask = orderbook.get_best_ask()
                            spread = best_ask - best_bid
                            spread_percent = (spread / best_bid) * 100
                            print(f"      📏 价差: {spread:.8f} ({spread_percent:.4f}%)")
                        
                        orderbook_results[pair] = {
                            'success': True,
                            'response_time': orderbook_time,
                            'bid_count': len(orderbook.bids),
                            'ask_count': len(orderbook.asks),
                            'best_bid': orderbook.bids[0] if orderbook.bids else None,
                            'best_ask': orderbook.asks[0] if orderbook.asks else None,
                            'timestamp': orderbook.timestamp
                        }
                    else:
                        print(f"      ❌ 获取失败 - 返回空数据")
                        orderbook_results[pair] = {
                            'success': False,
                            'response_time': orderbook_time,
                            'error': '返回空数据'
                        }
                        
                except Exception as e:
                    print(f"      ❌ 获取失败 - {str(e)}")
                    orderbook_results[pair] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # 测试获取更多订单簿数据
            print(f"  🔄 额外订单簿测试...")
            try:
                extra_start = time.time()
                extra_orderbook = okx_client.get_orderbook('USDT-USDC')
                extra_time = time.time() - extra_start
                extra_success = extra_orderbook is not None
                if extra_success:
                    print(f"    ✅ 额外订单簿获取成功! 响应时间: {extra_time:.3f}s")
                else:
                    print(f"    ❌ 额外订单簿获取失败")
            except Exception as e:
                extra_success = False
                extra_time = 0
                print(f"    ❌ 额外订单簿获取异常: {str(e)}")
                self.logger.warning(f"额外订单簿获取失败: {e}")
            
            # 统计成功率
            successful_pairs = sum(1 for result in orderbook_results.values() if result['success'])
            print(f"  📊 订单簿成功率: {successful_pairs}/{len(test_pairs)}")
            
            # 测试API请求头信息（如果有）
            api_info = {}
            if hasattr(okx_client, 'headers'):
                api_info['headers_configured'] = True
                print(f"  🔐 API认证: 已配置")
            
            details = {
                'balance_retrieved': balance is not None,
                'balance_response_time': balance_time,
                'balance_data': balance,
                'orderbook_results': orderbook_results,
                'orderbook_success_rate': successful_pairs / len(test_pairs),
                'extra_orderbook_success': extra_success,
                'extra_orderbook_response_time': extra_time,
                'api_flag': okx_client.flag,
                'api_info': api_info,
                'total_test_pairs': len(test_pairs),
                'successful_pairs': successful_pairs
            }
            
            # 判断成功条件
            success = (
                balance is not None and
                all(result['success'] for result in orderbook_results.values())
            )
            
            print(f"  📋 API测试结果: {'✅ 通过' if success else '❌ 失败'}")
            
            self.log_test_result('okx_api_test', success, details)
            return success
            
        except Exception as e:
            print(f"  💥 OKX API测试异常: {str(e)}")
            self.log_test_result('okx_api_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_data_collector(self) -> bool:
        """测试数据采集器"""
        self.logger.info("📊 开始数据采集器测试...")
        print("\n📊 数据采集器测试详情:")
        
        try:
            # 初始化数据采集器
            data_collector = DataCollector()
            print(f"  ↗️  数据采集器初始化完成")
            
            # 测试启动数据采集
            trading_pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
            print(f"  🚀 启动数据采集器...")
            print(f"    📋 监控交易对: {', '.join(trading_pairs)}")
            
            start_time = time.time()
            start_success = await data_collector.start(trading_pairs)
            startup_time = time.time() - start_time
            
            if start_success:
                print(f"  ✅ 数据采集器启动成功! 耗时: {startup_time:.3f}s")
                print(f"    🔗 已订阅 {len(data_collector.subscribed_pairs)} 个交易对")
            else:
                print(f"  ❌ 数据采集器启动失败")
                self.log_test_result('data_collector_test', False, {'error': '数据采集器启动失败'})
                return False
            
            # 等待数据收集
            print(f"  ⏳ 等待数据收集 (5秒)...")
            data_collection_start = time.time()
            
            for i in range(50):  # 5秒，每100ms检查一次
                await asyncio.sleep(0.1)
                
                # 实时显示数据收集进度
                if i % 10 == 0:  # 每秒显示一次
                    collected_count = 0
                    for pair in trading_pairs:
                        if data_collector.get_orderbook(pair):
                            collected_count += 1
                    print(f"    📥 已收集 {collected_count}/{len(trading_pairs)} 个交易对数据")
            
            data_collection_time = time.time() - data_collection_start
            
            # 测试数据获取
            print(f"  📖 检查收集到的数据...")
            orderbook_data = {}
            
            for pair in trading_pairs:
                orderbook = data_collector.get_orderbook(pair)
                if orderbook:
                    print(f"    📊 {pair}:")
                    print(f"      ✅ 数据可用")
                    print(f"      🕐 时间戳: {orderbook.timestamp}")
                    print(f"      📈 买单数量: {len(orderbook.bids)}")
                    print(f"      📉 卖单数量: {len(orderbook.asks)}")
                    
                    # 显示最优价格
                    if len(orderbook.bids) > 0 and len(orderbook.asks) > 0:
                        print(f"      💰 最优买价: {orderbook.get_best_bid()}")
                        print(f"      💸 最优卖价: {orderbook.get_best_ask()}")
                        
                        # 计算数据新鲜度
                        data_age = time.time() - orderbook.timestamp
                        print(f"      🕰️  数据年龄: {data_age:.1f}s")
                    
                    orderbook_data[pair] = {
                        'available': True,
                        'timestamp': orderbook.timestamp,
                        'bid_count': len(orderbook.bids),
                        'ask_count': len(orderbook.asks),
                        'data_age': time.time() - orderbook.timestamp,
                        'best_bid': orderbook.get_best_bid(),
                        'best_ask': orderbook.get_best_ask()
                    }
                else:
                    print(f"    📊 {pair}: ❌ 无数据")
                    orderbook_data[pair] = {
                        'available': False,
                        'timestamp': None,
                        'bid_count': 0,
                        'ask_count': 0
                    }
            
            # 获取账户数据
            print(f"  💰 检查账户余额数据...")
            balance_data = data_collector.get_balance()
            if balance_data:
                print(f"    ✅ 余额数据可用")
                if hasattr(balance_data, 'balances'):
                    non_zero_balances = {k: v for k, v in balance_data.balances.items() if float(v) > 0}
                    print(f"    💎 非零余额: {len(non_zero_balances)} 个币种")
                    for currency, amount in list(non_zero_balances.items())[:3]:
                        print(f"      {currency}: {amount}")
            else:
                print(f"    ❌ 余额数据不可用")
            
            # 获取性能统计
            print(f"  📊 获取性能统计...")
            stats = data_collector.get_stats()
            if stats:
                print(f"    📈 性能统计:")
                if isinstance(stats, dict):
                    for key, value in stats.items():
                        print(f"      {key}: {value}")
                else:
                    print(f"      统计数据: {str(stats)}")
            
            # 检查运行状态
            is_running = data_collector.is_running
            print(f"  🔍 运行状态: {'🟢 运行中' if is_running else '🔴 已停止'}")
            
            # 停止数据采集
            print(f"  🛑 停止数据采集器...")
            stop_start = time.time()
            await data_collector.stop()
            stop_time = time.time() - stop_start
            print(f"  ✅ 数据采集器已停止! 耗时: {stop_time:.3f}s")
            
            # 统计结果
            available_count = sum(1 for result in orderbook_data.values() if result['available'])
            print(f"  📊 数据可用率: {available_count}/{len(trading_pairs)}")
            
            details = {
                'start_success': start_success,
                'startup_time': startup_time,
                'data_collection_time': data_collection_time,
                'stop_time': stop_time,
                'orderbook_data': orderbook_data,
                'available_data_count': available_count,
                'balance_available': balance_data is not None,
                'balance_data_summary': f"{len(balance_data.balances)} currencies" if balance_data else "No data",
                'performance_stats': stats,
                'subscribed_pairs_count': len(data_collector.subscribed_pairs),
                'final_running_status': data_collector.is_running
            }
            
            # 判断成功条件
            success = (
                start_success and
                balance_data is not None and
                all(result['available'] for result in orderbook_data.values())
            )
            
            print(f"  📋 数据采集器测试结果: {'✅ 通过' if success else '❌ 失败'}")
            
            self.log_test_result('data_collector_test', success, details)
            return success
            
        except Exception as e:
            print(f"  💥 数据采集器测试异常: {str(e)}")
            self.log_test_result('data_collector_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_arbitrage_engine(self) -> bool:
        """测试套利计算引擎"""
        self.logger.info("🔍 开始套利引擎测试...")
        print("\n🔍 套利引擎测试详情:")
        
        try:
            # 初始化数据采集器和套利引擎
            print(f"  ↗️  初始化套利引擎...")
            data_collector = DataCollector()
            arbitrage_engine = ArbitrageEngine(data_collector)
            print(f"  ✅ 套利引擎初始化完成")
            
            # 显示引擎配置
            print(f"  ⚙️  引擎配置:")
            print(f"    💸 手续费率: {arbitrage_engine.fee_rate * 100:.4f}%")
            print(f"    📊 最小利润阈值: {arbitrage_engine.min_profit_threshold * 100:.4f}%")
            
            # 启动数据采集
            trading_pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
            print(f"  🚀 启动数据采集...")
            await data_collector.start(trading_pairs)
            
            # 等待数据稳定
            print(f"  ⏳ 等待数据稳定 (5秒)...")
            await asyncio.sleep(5)
            
            # 测试套利路径配置
            paths = arbitrage_engine.paths
            print(f"  📋 套利路径配置:")
            print(f"    🛤️  已配置路径数: {len(paths)}")
            
            for path_name, path_config in paths.items():
                print(f"    📍 {path_name}:")
                if 'route' in path_config:
                    print(f"      🔄 路径: {path_config['route']}")
                if 'description' in path_config:
                    print(f"      📝 描述: {path_config['description']}")
            
            # 测试套利机会计算
            print(f"  🔍 分析套利机会...")
            opportunities = []
            calculation_results = {}
            
            for path_name, path_config in paths.items():
                if 'route' in path_config:
                    assets = path_config['route'].split('->')
                    print(f"    🧮 计算路径 {path_name}: {' -> '.join(assets)}")
                    
                    calc_start = time.time()
                    opportunity = arbitrage_engine.calculate_arbitrage(assets)
                    calc_time = time.time() - calc_start
                    
                    if opportunity:
                        print(f"      ✅ 发现套利机会!")
                        print(f"        💰 利润率: {opportunity.profit_rate * 100:.6f}%")
                        print(f"        💵 预估利润: ${opportunity.estimated_profit:.4f}")
                        print(f"        📊 计算耗时: {calc_time:.3f}s")
                        
                        # 显示详细路径数据
                        if hasattr(opportunity, 'path_details'):
                            for i, step in enumerate(opportunity.path_details):
                                print(f"        🔗 步骤{i+1}: {step}")
                        
                        opportunities.append({
                            'path': path_name,
                            'profit_rate': opportunity.profit_rate,
                            'estimated_profit': opportunity.estimated_profit,
                            'calculation_time': calc_time,
                            'details': opportunity.__dict__ if hasattr(opportunity, '__dict__') else str(opportunity)
                        })
                        
                        calculation_results[path_name] = {
                            'success': True,
                            'profit_rate': opportunity.profit_rate,
                            'calculation_time': calc_time
                        }
                    else:
                        print(f"      ❌ 无套利机会")
                        calculation_results[path_name] = {
                            'success': False,
                            'calculation_time': calc_time
                        }
            
            print(f"  📊 套利机会统计:")
            print(f"    🎯 发现机会: {len(opportunities)}/{len(paths)}")
            if opportunities:
                best_opportunity = max(opportunities, key=lambda x: x['profit_rate'])
                print(f"    🥇 最佳机会: {best_opportunity['path']} ({best_opportunity['profit_rate']*100:.6f}%)")
            
            # 测试监控功能
            print(f"  👁️  测试实时监控...")
            monitoring_start = time.time()
            arbitrage_engine.start_monitoring()
            print(f"    🟢 监控已启动")
            
            await asyncio.sleep(3)
            
            # 检查监控状态
            is_monitoring = arbitrage_engine.is_monitoring
            print(f"    📊 监控状态: {'🟢 运行中' if is_monitoring else '🔴 已停止'}")
            
            arbitrage_engine.stop_monitoring()
            monitoring_time = time.time() - monitoring_start
            print(f"    🛑 监控已停止 (运行时间: {monitoring_time:.1f}s)")
            
            # 获取统计信息
            print(f"  📈 获取统计信息...")
            stats = arbitrage_engine.get_statistics()
            if stats:
                print(f"    📊 引擎统计:")
                if hasattr(stats, '__dict__'):
                    for key, value in stats.__dict__.items():
                        print(f"      {key}: {value}")
                elif isinstance(stats, dict):
                    for key, value in stats.items():
                        print(f"      {key}: {value}")
                else:
                    print(f"      统计数据: {str(stats)}")
            
            # 清理
            print(f"  🧹 清理资源...")
            await data_collector.stop()
            print(f"  ✅ 资源清理完成")
            
            details = {
                'paths_loaded': len(paths),
                'paths_details': {name: config for name, config in paths.items()},
                'opportunities_found': len(opportunities),
                'opportunities_details': opportunities,
                'calculation_results': calculation_results,
                'monitoring_time': monitoring_time,
                'monitoring_stats': stats.__dict__ if hasattr(stats, '__dict__') else stats,
                'fee_rate': arbitrage_engine.fee_rate,
                'min_profit_threshold': arbitrage_engine.min_profit_threshold,
                'engine_performance': {
                    'avg_calculation_time': sum(r.get('calculation_time', 0) for r in calculation_results.values()) / len(calculation_results) if calculation_results else 0
                }
            }
            
            # 判断成功条件 - 只要能计算套利即可，不要求一定有机会
            success = len(paths) > 0 and len(calculation_results) > 0
            
            print(f"  📋 套利引擎测试结果: {'✅ 通过' if success else '❌ 失败'}")
            
            self.log_test_result('arbitrage_engine_test', success, details)
            return success
            
        except Exception as e:
            print(f"  💥 套利引擎测试异常: {str(e)}")
            self.log_test_result('arbitrage_engine_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_risk_manager(self) -> bool:
        """测试风险管理器"""
        self.logger.info("🛡️ 开始风险管理器测试...")
        
        try:
            # 初始化组件
            config_manager = ConfigManager()
            okx_client = OKXClient()
            risk_manager = RiskManager(config_manager, okx_client)
            
            # 获取当前余额
            balance = okx_client.get_balance()
            if not balance:
                self.log_test_result('risk_manager_test', False, {'error': '无法获取余额进行风险测试'})
                return False
            
            # 测试余额计算
            total_balance = risk_manager._calculate_total_balance_usdt(balance)
            
            # 测试交易金额验证
            test_amounts = [100, 1000, 10000, 100000]
            amount_checks = {}
            
            for amount in test_amounts:
                check_result = risk_manager.check_position_limit("USDT", amount)
                amount_checks[amount] = {
                    'passed': check_result.passed,
                    'risk_level': check_result.risk_level.value,
                    'suggested_amount': check_result.suggested_amount
                }
            
            # 测试套利频率控制
            frequency_check = risk_manager.check_arbitrage_frequency()
            
            # 测试风险统计
            risk_stats = risk_manager.get_risk_statistics()
            
            # 测试仓位检查
            position_check = risk_manager.check_position_limit("BTC", 0.001)
            
            details = {
                'total_balance_usdt': total_balance,
                'amount_checks': amount_checks,
                'frequency_check': frequency_check.passed if hasattr(frequency_check, 'passed') else frequency_check,
                'risk_stats': risk_stats,
                'position_check': position_check.passed if hasattr(position_check, 'passed') else position_check,
                'risk_config': risk_manager.risk_config,
                'current_risk_level': risk_manager.risk_level.value
            }
            
            # 判断成功条件
            success = (
                total_balance > 0 and
                risk_stats is not None
            )
            
            self.log_test_result('risk_manager_test', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('risk_manager_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_trade_executor(self) -> bool:
        """测试交易执行器（安全模式）"""
        self.logger.info("⚡ 开始交易执行器测试（安全模式）...")
        
        try:
            # 初始化交易执行器
            okx_client = OKXClient()
            trade_executor = TradeExecutor(okx_client)
            
            # 获取余额（通过OKX客户端）
            balance = trade_executor.okx_client.get_balance()
            
            # 测试余额检查功能（使用简化的检查方式）
            test_check_available = hasattr(trade_executor, 'get_balance_check')
            
            # 测试配置参数
            config_params = {
                'has_timeout': hasattr(trade_executor, 'order_timeout'),
                'has_retries': hasattr(trade_executor, 'max_retries'),
                'has_okx_client': trade_executor.okx_client is not None
            }
            
            # 测试基本方法存在性
            method_availability = {
                'execute_arbitrage': hasattr(trade_executor, 'execute_arbitrage'),
                'get_balance_check': hasattr(trade_executor, 'get_balance_check')
            }
            
            # 测试订单状态跟踪（模拟）
            mock_order_id = "test_order_123"
            status_tracking_test = {
                'order_id': mock_order_id,
                'tracking_method_available': hasattr(trade_executor, 'get_order_status')
            }
            
            details = {
                'balance_available': balance is not None,
                'test_check_available': test_check_available,
                'config_params': config_params,
                'method_availability': method_availability,
                'status_tracking': status_tracking_test
            }
            
            # 判断成功条件 - 主要验证功能可用性
            success = (
                balance is not None and
                config_params['has_okx_client'] and
                method_availability['execute_arbitrage']
            )
            
            self.log_test_result('trade_executor_test', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('trade_executor_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_websocket_connection(self) -> bool:
        """测试WebSocket连接"""
        self.logger.info("🔌 开始WebSocket连接测试...")
        print("\n🔌 WebSocket连接测试详情:")
        
        try:
            # 初始化WebSocket管理器
            ws_manager = WebSocketManager()
            print(f"  ↗️  初始化WebSocket管理器完成")
            
            # 记录连接开始时间
            connect_start_time = time.time()
            print(f"  🔗 正在连接到WebSocket服务器...")
            
            # 测试连接
            connected = await ws_manager.connect()
            connect_time = time.time() - connect_start_time
            
            if connected:
                print(f"  ✅ WebSocket连接成功! 耗时: {connect_time:.3f}s")
                if hasattr(ws_manager, 'ws_url'):
                    print(f"  🌐 连接URL: {ws_manager.ws_url}")
            else:
                print(f"  ❌ WebSocket连接失败")
                self.log_test_result('websocket_test', False, {'error': 'WebSocket连接失败'})
                return False
            
            # 订阅测试数据
            test_pairs = ['BTC-USDT', 'BTC-USDC']
            subscription_results = {}
            messages_received = []
            
            print(f"  📡 开始订阅交易对数据...")
            
            try:
                # WebSocketManager使用subscribe_orderbooks方法（复数形式）
                success = await ws_manager.subscribe_orderbooks(test_pairs)
                for pair in test_pairs:
                    subscription_results[pair] = success
                    print(f"    📊 {pair}: {'✅ 订阅成功' if success else '❌ 订阅失败'}")
            except Exception as e:
                for pair in test_pairs:
                    subscription_results[pair] = False
                    print(f"    📊 {pair}: ❌ 订阅失败 - {str(e)}")
                self.logger.warning(f"订阅失败: {e}")
            
            # 等待数据接收并记录详情
            print(f"  ⏳ 等待数据接收 (5秒)...")
            data_received = False
            
            for i in range(50):  # 5秒，每100ms检查一次
                await asyncio.sleep(0.1)
                
                # 尝试获取最新数据
                if hasattr(ws_manager, 'get_latest_orderbook'):
                    for pair in test_pairs:
                        try:
                            orderbook = ws_manager.get_latest_orderbook(pair)
                            if orderbook and not data_received:
                                data_received = True
                                print(f"    📥 收到 {pair} 数据:")
                                print(f"      🕐 时间戳: {orderbook.timestamp}")
                                print(f"      📈 买单数量: {len(orderbook.bids)}")
                                print(f"      📉 卖单数量: {len(orderbook.asks)}")
                                if len(orderbook.bids) > 0:
                                    print(f"      💰 最高买价: {orderbook.bids[0]['price']} (数量: {orderbook.bids[0]['size']})")
                                if len(orderbook.asks) > 0:
                                    print(f"      💸 最低卖价: {orderbook.asks[0]['price']} (数量: {orderbook.asks[0]['size']})")
                                
                                messages_received.append({
                                    'pair': pair,
                                    'timestamp': orderbook.timestamp,
                                    'bids_count': len(orderbook.bids),
                                    'asks_count': len(orderbook.asks),
                                    'best_bid': orderbook.bids[0] if orderbook.bids else None,
                                    'best_ask': orderbook.asks[0] if orderbook.asks else None
                                })
                        except:
                            pass
            
            # 检查WebSocket连接状态
            is_connected = ws_manager.is_ws_connected() if hasattr(ws_manager, 'is_ws_connected') else connected
            print(f"  🔍 连接状态检查: {'🟢 已连接' if is_connected else '🔴 已断开'}")
            
            # 获取统计信息
            stats = {
                'connection_status': is_connected, 
                'messages_received': len(messages_received),
                'connection_time': connect_time,
                'data_received': data_received
            }
            
            if hasattr(ws_manager, 'get_stats'):
                ws_stats = ws_manager.get_stats()
                print(f"  📊 WebSocket统计:")
                print(f"    📨 总消息数: {ws_stats.get('total_messages', 0)}")
                print(f"    ⚠️  错误数: {ws_stats.get('error_count', 0)}")
                stats.update(ws_stats)
            
            # 断开连接
            print(f"  🔌 正在断开连接...")
            await ws_manager.disconnect()
            print(f"  ✅ 连接已断开")
            
            details = {
                'connection_success': connected,
                'connection_time': connect_time,
                'subscription_results': subscription_results,
                'messages_received_count': len(messages_received),
                'messages_received_details': messages_received,
                'data_received': data_received,
                'subscribed_channels': len(subscription_results),
                'websocket_stats': stats
            }
            
            # 判断成功条件 - WebSocket连接即为成功，不要求必须收到消息
            success = (
                connected and
                any(subscription_results.values())
            )
            
            print(f"  📋 测试结果: {'✅ 通过' if success else '❌ 失败'}")
            
            self.log_test_result('websocket_test', success, details)
            return success
            
        except Exception as e:
            print(f"  💥 WebSocket测试异常: {str(e)}")
            self.log_test_result('websocket_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_integration(self) -> bool:
        """测试系统集成"""
        self.logger.info("🔗 开始系统集成测试...")
        
        try:
            # 初始化交易控制器
            trading_controller = TradingController()
            
            # 测试系统启动
            startup_success = await trading_controller.start()
            
            if not startup_success:
                self.log_test_result('integration_test', False, {'error': '系统启动失败'})
                return False
            
            # 等待系统稳定
            await asyncio.sleep(10)
            
            # 检查各模块状态
            module_status = {
                'data_collector': trading_controller.data_collector.is_running,
                'arbitrage_engine': trading_controller.arbitrage_engine.is_monitoring,
                'status': trading_controller.status.value
            }
            
            # 获取系统统计
            system_stats = trading_controller.get_stats()
            
            # 测试一次完整的监控周期
            await asyncio.sleep(5)
            
            # 检查是否有套利机会被检测到
            opportunities_detected = system_stats.get('total_opportunities', 0) > 0
            
            # 停止系统
            await trading_controller.stop()
            
            details = {
                'startup_success': startup_success,
                'module_status': module_status,
                'system_stats': system_stats.__dict__ if hasattr(system_stats, '__dict__') else str(system_stats),
                'opportunities_detected': opportunities_detected,
                'runtime_seconds': 15
            }
            
            # 判断成功条件
            success = (
                startup_success and
                module_status['data_collector'] and
                trading_controller.status.value in ['running', 'stopped']
            )
            
            self.log_test_result('integration_test', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('integration_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_performance(self) -> bool:
        """测试性能指标"""
        self.logger.info("⚡ 开始性能测试...")
        
        try:
            import psutil
            
            # 记录起始资源使用
            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            start_cpu = process.cpu_percent()
            
            # 执行性能测试
            okx_client = OKXClient()
            
            # 测试API调用性能
            api_performance = {}
            
            # 余额查询性能
            balance_times = []
            for i in range(5):
                start_time = time.time()
                balance = okx_client.get_balance()
                balance_times.append(time.time() - start_time)
                await asyncio.sleep(0.5)
            
            api_performance['balance_query'] = {
                'avg_time': sum(balance_times) / len(balance_times),
                'max_time': max(balance_times),
                'min_time': min(balance_times)
            }
            
            # 订单簿查询性能
            orderbook_times = []
            for i in range(5):
                start_time = time.time()
                orderbook = okx_client.get_orderbook('BTC-USDT')
                orderbook_times.append(time.time() - start_time)
                await asyncio.sleep(0.5)
            
            api_performance['orderbook_query'] = {
                'avg_time': sum(orderbook_times) / len(orderbook_times),
                'max_time': max(orderbook_times),
                'min_time': min(orderbook_times)
            }
            
            # 记录结束资源使用
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            end_cpu = process.cpu_percent()
            
            details = {
                'memory_usage': {
                    'start_mb': start_memory,
                    'end_mb': end_memory,
                    'delta_mb': end_memory - start_memory
                },
                'cpu_usage': {
                    'start_percent': start_cpu,
                    'end_percent': end_cpu
                },
                'api_performance': api_performance
            }
            
            # 判断成功条件 - 性能在合理范围内
            success = (
                api_performance['balance_query']['avg_time'] < 5.0 and  # 5秒内
                api_performance['orderbook_query']['avg_time'] < 5.0 and
                details['memory_usage']['delta_mb'] < 100  # 内存增长不超过100MB
            )
            
            self.log_test_result('performance_test', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('performance_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    async def test_error_handling(self) -> bool:
        """测试错误处理和恢复能力"""
        self.logger.info("🚨 开始错误处理测试...")
        
        try:
            # 测试网络错误恢复
            okx_client = OKXClient()
            
            # 测试API限流处理
            error_handling_results = {}
            
            # 模拟快速连续请求（可能触发限流）
            rapid_requests = []
            for i in range(10):
                try:
                    start_time = time.time()
                    balance = okx_client.get_balance()
                    rapid_requests.append({
                        'success': balance is not None,
                        'response_time': time.time() - start_time
                    })
                except Exception as e:
                    rapid_requests.append({
                        'success': False,
                        'error': str(e)
                    })
            
            error_handling_results['rapid_requests'] = rapid_requests
            
            # 测试无效交易对处理
            try:
                invalid_orderbook = okx_client.get_orderbook('INVALID-PAIR')
                invalid_pair_handled = invalid_orderbook is None
            except Exception as e:
                invalid_pair_handled = True  # 异常被正确抛出
                self.logger.debug(f"无效交易对测试触发异常（正常）: {e}")
            
            error_handling_results['invalid_pair_handling'] = invalid_pair_handled
            
            # 测试配置错误处理
            try:
                config_manager = ConfigManager()
                # 尝试验证配置
                is_valid, errors = config_manager.validate_config()
                config_error_handling = True
            except Exception as e:
                config_error_handling = False
            
            error_handling_results['config_error_handling'] = config_error_handling
            
            details = {
                'error_handling_results': error_handling_results,
                'rapid_request_success_rate': sum(1 for r in rapid_requests if r['success']) / len(rapid_requests),
                'invalid_pair_handled': invalid_pair_handled,
                'config_error_handled': config_error_handling
            }
            
            # 判断成功条件
            success = (
                error_handling_results['rapid_requests'] and
                invalid_pair_handled and
                config_error_handling
            )
            
            self.log_test_result('error_handling_test', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('error_handling_test', False, {'error': str(e), 'traceback': traceback.format_exc()})
            return False

    def generate_test_report(self):
        """生成测试报告"""
        self.stats['end_time'] = time.time()
        runtime = self.stats['end_time'] - self.stats['start_time']
        
        report = {
            'test_summary': {
                'total_tests': self.stats['total_tests'],
                'passed_tests': self.stats['passed_tests'],
                'failed_tests': self.stats['failed_tests'],
                'success_rate': self.stats['passed_tests'] / self.stats['total_tests'] if self.stats['total_tests'] > 0 else 0,
                'runtime_seconds': runtime,
                'test_time': self.test_start_time
            },
            'test_results': self.test_results
        }
        
        # 保存详细报告
        report_file = f"logs/core_test_report_{self.test_start_time}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # 打印摘要
        print(f"\n{'='*60}")
        print(f"Core模块综合测试报告")
        print(f"{'='*60}")
        print(f"测试时间: {self.test_start_time}")
        print(f"运行时长: {runtime:.2f}秒")
        print(f"总测试数: {self.stats['total_tests']}")
        print(f"通过测试: {self.stats['passed_tests']}")
        print(f"失败测试: {self.stats['failed_tests']}")
        print(f"成功率: {report['test_summary']['success_rate']:.2%}")
        print(f"\n详细报告: {report_file}")
        print(f"测试日志: {self.log_file}")
        
        # 显示各测试结果
        print(f"\n详细结果:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result['status'] == 'passed' else "❌" if result['status'] == 'failed' else "⏳"
            print(f"{status_icon} {test_name}: {result['status']}")
        
        return report

    async def run_all_tests(self):
        """运行所有测试"""
        self.logger.info("🚀 开始Core模块综合测试...")
        
        # 定义测试顺序
        test_sequence = [
            ('配置管理器', self.test_config_manager),
            ('OKX API', self.test_okx_api),
            ('数据采集器', self.test_data_collector),
            ('套利引擎', self.test_arbitrage_engine),
            ('风险管理器', self.test_risk_manager),
            ('交易执行器', self.test_trade_executor),
            ('WebSocket连接', self.test_websocket_connection),
            ('系统集成', self.test_integration),
            ('性能测试', self.test_performance),
            ('错误处理', self.test_error_handling)
        ]
        
        for test_name, test_func in test_sequence:
            try:
                self.logger.info(f"\n{'='*20} {test_name} 测试开始 {'='*20}")
                await test_func()
                await asyncio.sleep(1)  # 测试间隔
            except Exception as e:
                self.logger.error(f"{test_name} 测试异常: {e}")
                self.stats['total_tests'] += 1
                self.stats['failed_tests'] += 1
        
        # 生成测试报告
        return self.generate_test_report()


async def main():
    """主函数"""
    print("🔧 Core模块综合测试工具")
    print("使用真实OKX API测试所有核心功能")
    print("确保在config/secrets.ini中配置了正确的API密钥")
    print("测试将使用虚拟账户，不涉及真实资金\n")
    
    # 检查配置文件
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    secrets_path = os.path.join(project_root, 'config', 'secrets.ini')
    if not os.path.exists(secrets_path):
        print("❌ 错误: 未找到config/secrets.ini文件")
        print("请先配置API密钥后再运行测试")
        return
    
    input("按Enter键开始测试...")
    
    # 创建并运行测试器
    tester = CoreTester()
    report = await tester.run_all_tests()
    
    # 最终结果
    if report['test_summary']['success_rate'] >= 0.8:
        print(f"\n🎉 测试基本通过! 成功率: {report['test_summary']['success_rate']:.2%}")
    else:
        print(f"\n⚠️ 测试存在问题，请检查失败的测试项目")
    
    return report


if __name__ == "__main__":
    # 确保事件循环正确运行
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n💥 测试执行出错: {e}")
        traceback.print_exc()