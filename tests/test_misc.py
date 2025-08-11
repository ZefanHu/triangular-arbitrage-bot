#!/usr/bin/env python3
"""
TaoLi 杂项测试集合

包含套利系统的各种专项测试：
1. 套利检测准确性测试
2. 利润计算分析测试
3. 深度数据验证测试

使用方法：
- python3 tests/test_misc.py                              # 运行所有测试的快速版本
- python3 tests/test_misc.py --test arbitrage-detection   # 套利检测准确性测试
- python3 tests/test_misc.py --test profit-calculation    # 利润计算分析测试  
- python3 tests/test_misc.py --test data-validation       # 深度数据验证测试
- python3 tests/test_misc.py --test profit-calculation --profit-rate 0.03  # 指定利润率
"""

import asyncio
import time
import logging
import sys
import os
import argparse
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# 添加项目根目录到path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.okx_client import OKXClient
from utils.logger import setup_logger


class MiscTests:
    """杂项测试集合类"""
    
    def __init__(self):
        # 获取tests目录的绝对路径
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        # 确保日志目录存在
        os.makedirs(os.path.join(tests_dir, "logs"), exist_ok=True)
        # 生成带时间戳的日志文件名
        test_start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(tests_dir, f"logs/test_misc_{test_start_time}.log")
        self.logger = setup_logger("MiscTests", log_file, logging.INFO)
        # 可配置的目标利润率（用于profit-calculation测试）
        self.target_profit_rate = 0.0537  # 默认5.37%，可以修改测试其他利润率
        
    # ==================== 套利检测准确性测试 ====================
    async def test_arbitrage_detection(self):
        """
        测试套利检测准确性
        验证时间戳修复和数据一致性检查是否有效减少虚假套利机会
        """
        print(f"\n🧪 开始套利检测准确性测试")
        print("=" * 60)
        
        # 固定测试时长为1分钟
        duration_minutes = 1
        
        stats = {
            'total_checks': 0,
            'opportunities_found': 0,
            'consistency_failures': 0,
            'data_age_rejections': 0,
            'valid_opportunities': 0
        }
        
        # 初始化组件
        data_collector = DataCollector()
        arbitrage_engine = ArbitrageEngine(data_collector)
        
        # 启动数据采集
        trading_pairs = ['BTC-USDT', 'BTC-USDC', 'USDC-USDT']
        print("🚀 启动数据采集...")
        success = await data_collector.start(trading_pairs)
        
        if not success:
            print("❌ 数据采集启动失败")
            return
            
        # 等待数据稳定
        print("⏳ 等待数据稳定...")
        await asyncio.sleep(3)
        
        # 开始测试循环
        test_start = time.time()
        test_duration = duration_minutes * 60
        check_interval = 2.0
        
        print(f"🔍 开始监控套利机会...")
        print(f"检查间隔: {check_interval}秒")
        print(f"数据一致性要求: 200ms内")
        print(f"数据新鲜度要求: 500ms内")
        print()
        
        while time.time() - test_start < test_duration:
            try:
                stats['total_checks'] += 1
                opportunities = arbitrage_engine.find_opportunities()
                
                if opportunities:
                    stats['opportunities_found'] += len(opportunities)
                    stats['valid_opportunities'] += len(opportunities)
                    
                    for opp in opportunities:
                        profit_rate = opp.get('profit_rate', 0)
                        path_name = opp.get('path_name', 'Unknown')
                        self.logger.info(f"发现套利机会: {path_name}, 利润率: {profit_rate:.6%}")
                        
            except Exception as e:
                self.logger.error(f"检查套利机会时发生错误: {e}")
            
            await asyncio.sleep(check_interval)
            
            # 每分钟显示一次进度
            elapsed = time.time() - test_start
            if stats['total_checks'] % 30 == 0 and stats['total_checks'] > 0:
                progress_pct = (elapsed / test_duration) * 100
                print(f"📊 进度: {progress_pct:.1f}% | "
                      f"检查次数: {stats['total_checks']} | "
                      f"发现机会: {stats['opportunities_found']} | "
                      f"机会率: {(stats['opportunities_found']/stats['total_checks']*100):.2f}%")
        
        # 停止数据采集
        await data_collector.stop()
        
        # 显示最终结果
        self._print_fix_results(stats, test_duration)
        
    def _print_fix_results(self, stats: Dict, test_duration: float):
        """打印套利修复测试结果"""
        print("\n" + "=" * 60)
        print("🎯 套利修复效果测试结果")
        print("=" * 60)
        
        opportunity_rate = (stats['opportunities_found'] / stats['total_checks'] * 100) if stats['total_checks'] > 0 else 0
        
        print(f"📊 统计数据:")
        print(f"  ⏱️  测试时长: {test_duration/60:.1f} 分钟")
        print(f"  🔍 总检查次数: {stats['total_checks']}")
        print(f"  ✅ 发现套利机会: {stats['opportunities_found']}")
        print(f"  📈 套利机会率: {opportunity_rate:.4f}%")
        
        print(f"\n💡 效果分析:")
        if opportunity_rate < 1.0:
            print("  🎉 修复效果显著! 套利机会率大幅下降")
            print("  ✨ 数据一致性检查有效过滤了虚假机会")
        elif opportunity_rate < 5.0:
            print("  👍 修复效果良好，套利机会率明显降低") 
            print("  📝 建议进一步调整时间阈值")
        else:
            print("  ⚠️  套利机会率仍然较高，可能需要进一步优化")
            print("  🔧 建议检查时间戳处理和一致性验证逻辑")
    
    # ==================== 利润计算分析测试 ====================
    def test_profit_calculation(self):
        """
        详细套利计算过程分析
        验证特定利润率（默认5.37%）的计算过程
        """
        print(f"\n🔬 套利利润率{self.target_profit_rate:.2%}详细计算过程分析")
        print("🎯 目标: 验证每个数值的来源和计算过程")
        print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取详细市场数据
        market_data = self._get_detailed_market_data()
        if not market_data:
            print("❌ 无法获取市场数据，分析终止")
            return
        
        # 详细计算过程分析
        calculation_result = self._detailed_arbitrage_calculation(market_data)
        if not calculation_result:
            print("❌ 计算分析失败，分析终止")
            return
        
        # 与目标结果对比
        self._compare_with_target(calculation_result)
        
        # 保存详细分析结果
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(os.path.join(tests_dir, 'outputs'), exist_ok=True)
        output_file = os.path.join(tests_dir, 'outputs/test_misc_arbitrage_breakdown.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(calculation_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 详细分析完成")
        print(f"📄 完整数据已保存到: tests/outputs/test_misc_arbitrage_breakdown.json")
        print(f"📊 最终利润率: {calculation_result['final_result']['profit_rate_percent']:.6f}%")
    
    def _get_detailed_market_data(self) -> Optional[Dict]:
        """获取详细的市场数据"""
        print("\n🔍 获取实时市场数据")
        print("=" * 60)
        
        try:
            okx_client = OKXClient()
            print("✅ OKX客户端初始化成功")
            
            pairs = ['BTC-USDT', 'BTC-USDC', 'USDC-USDT']
            detailed_data = {}
            
            for pair in pairs:
                print(f"\n🔍 获取 {pair} 详细数据...")
                orderbook = okx_client.get_orderbook(pair, size="20")
                
                if orderbook:
                    detailed_data[pair] = {
                        'symbol': orderbook.symbol,
                        'timestamp': orderbook.timestamp,
                        'timestamp_str': datetime.fromtimestamp(orderbook.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'),
                        'raw_bids': orderbook.bids[:10],
                        'raw_asks': orderbook.asks[:10],
                        'best_bid': orderbook.bids[0][0] if orderbook.bids else 0,
                        'best_ask': orderbook.asks[0][0] if orderbook.asks else 0,
                        'best_bid_size': orderbook.bids[0][1] if orderbook.bids else 0,
                        'best_ask_size': orderbook.asks[0][1] if orderbook.asks else 0,
                        'spread_abs': 0,
                        'spread_pct': 0,
                        'mid_price': 0
                    }
                    
                    # 计算价差和中间价
                    if orderbook.bids and orderbook.asks:
                        best_bid = orderbook.bids[0][0]
                        best_ask = orderbook.asks[0][0]
                        spread_abs = best_ask - best_bid
                        spread_pct = spread_abs / best_bid * 100
                        mid_price = (best_bid + best_ask) / 2
                        
                        detailed_data[pair]['spread_abs'] = spread_abs
                        detailed_data[pair]['spread_pct'] = spread_pct
                        detailed_data[pair]['mid_price'] = mid_price
                    
                    print(f"  📊 时间戳: {detailed_data[pair]['timestamp_str']}")
                    print(f"  📈 最优买价: {detailed_data[pair]['best_bid']:,.8f}")
                    print(f"  📉 最优卖价: {detailed_data[pair]['best_ask']:,.8f}")
                    print(f"  📏 价差: {detailed_data[pair]['spread_pct']:.6f}%")
                else:
                    print(f"  ❌ 获取 {pair} 数据失败")
                    return None
            
            return detailed_data
            
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
            return None
    
    def _detailed_arbitrage_calculation(self, market_data: Dict, initial_amount: float = 1000.0, 
                                      fee_rate: float = 0.001) -> Optional[Dict]:
        """详细的套利计算过程分析"""
        print("\n📊 完整套利计算过程分析")
        print("=" * 60)
        print(f"💰 初始投资金额: {initial_amount:,.2f} USDT")
        print(f"💸 手续费率: {fee_rate:.3%} (每笔交易)")
        print(f"📊 套利路径: USDT → BTC → USDC → USDT")
        
        calculation_log = {
            'initial_amount': initial_amount,
            'fee_rate': fee_rate,
            'path': 'USDT->BTC->USDC->USDT',
            'steps': [],
            'market_data_used': {},
            'final_result': {}
        }
        
        try:
            current_amount = initial_amount
            
            # 步骤1: USDT -> BTC
            print("\n📍 [1] USDT → BTC (买入BTC)")
            print("-" * 50)
            btc_usdt_ask = market_data['BTC-USDT']['best_ask']
            btc_amount = (current_amount / btc_usdt_ask) * (1 - fee_rate)
            
            print(f"  🏷️ 使用价格: {btc_usdt_ask:,.2f} USDT/BTC")
            print(f"  💰 投入金额: {current_amount:,.8f} USDT")
            print(f"  📊 获得BTC: {btc_amount:.10f} BTC")
            
            calculation_log['steps'].append({
                'step': 1,
                'from_asset': 'USDT',
                'to_asset': 'BTC',
                'input_amount': current_amount,
                'exchange_rate': btc_usdt_ask,
                'output_amount': btc_amount
            })
            current_amount = btc_amount
            
            # 步骤2: BTC -> USDC
            print("\n📍 [2] BTC → USDC (卖出BTC)")
            print("-" * 50)
            btc_usdc_bid = market_data['BTC-USDC']['best_bid']
            usdc_amount = (current_amount * btc_usdc_bid) * (1 - fee_rate)
            
            print(f"  🏷️ 使用价格: {btc_usdc_bid:,.2f} USDC/BTC")
            print(f"  💰 投入金额: {current_amount:.10f} BTC")
            print(f"  📊 获得USDC: {usdc_amount:.8f} USDC")
            
            calculation_log['steps'].append({
                'step': 2,
                'from_asset': 'BTC',
                'to_asset': 'USDC',
                'input_amount': current_amount,
                'exchange_rate': btc_usdc_bid,
                'output_amount': usdc_amount
            })
            current_amount = usdc_amount
            
            # 步骤3: USDC -> USDT
            print("\n📍 [3] USDC → USDT (兑换回USDT)")
            print("-" * 50)
            usdt_usdc_ask = market_data['USDC-USDT']['best_ask']
            final_usdt = (current_amount / usdt_usdc_ask) * (1 - fee_rate)
            
            print(f"  🏷️ 使用价格: {usdt_usdc_ask:.6f} USDC/USDT")
            print(f"  💰 投入金额: {current_amount:.8f} USDC")
            print(f"  📊 获得USDT: {final_usdt:.8f} USDT")
            
            calculation_log['steps'].append({
                'step': 3,
                'from_asset': 'USDC',
                'to_asset': 'USDT',
                'input_amount': current_amount,
                'exchange_rate': usdt_usdc_ask,
                'output_amount': final_usdt
            })
            
            # 计算最终结果
            profit = final_usdt - initial_amount
            profit_rate = profit / initial_amount
            
            print("\n🎯 [FINAL] 最终结果计算")
            print("-" * 50)
            print(f"  💰 初始投资: {initial_amount:,.8f} USDT")
            print(f"  💵 最终获得: {final_usdt:,.8f} USDT")
            print(f"  💲 绝对利润: {profit:,.8f} USDT")
            print(f"  📈 利润率: {profit_rate:.6%}")
            
            calculation_log['final_result'] = {
                'initial_amount': initial_amount,
                'final_amount': final_usdt,
                'absolute_profit': profit,
                'profit_rate': profit_rate,
                'profit_rate_percent': profit_rate * 100
            }
            
            # 异常原因分析
            self._analyze_profit_reasons(market_data, calculation_log)
            
            return calculation_log
            
        except Exception as e:
            print(f"❌ 计算过程失败: {e}")
            return None
    
    def _analyze_profit_reasons(self, market_data: Dict, calculation_log: Dict):
        """分析利润产生的原因"""
        print("\n🔍 异常原因分析")
        print("=" * 60)
        
        # USDC-USDT汇率分析
        usdt_usdc_ask = market_data['USDC-USDT']['best_ask']
        usdt_usdc_rate = 1 / usdt_usdc_ask
        print(f"🔍 关键汇率分析:")
        print(f"  • USDC-USDT卖价: {usdt_usdc_ask:.6f}")
        print(f"  • 隐含USDT/USDC汇率: {usdt_usdc_rate:.6f}")
        print(f"  • 正常市场预期: 约1.000 (±0.002)")
        print(f"  • 当前偏差: {(usdt_usdc_rate - 1.0) * 100:+.3f}%")
        
        # BTC价格套利空间分析
        btc_usdt_ask = market_data['BTC-USDT']['best_ask']
        btc_usdc_bid = market_data['BTC-USDC']['best_bid']
        btc_price_diff = btc_usdc_bid - btc_usdt_ask
        btc_price_diff_pct = btc_price_diff / btc_usdt_ask * 100
        
        print(f"\n🔍 BTC价格差异分析:")
        print(f"  • BTC-USDT卖价: {btc_usdt_ask:,.2f}")
        print(f"  • BTC-USDC买价: {btc_usdc_bid:,.2f}")
        print(f"  • 价格差异: {btc_price_diff:+.2f} ({btc_price_diff_pct:+.4f}%)")
    
    def _compare_with_target(self, calculation_result: Dict):
        """与目标利润率对比"""
        print("\n📊 与目标结果对比")
        print("=" * 60)
        
        if calculation_result:
            actual_profit_rate = calculation_result['final_result']['profit_rate_percent']
            target_profit_rate = self.target_profit_rate * 100
            
            print(f"📊 实际计算结果: {actual_profit_rate:.6f}%")
            print(f"📊 目标利润率: {target_profit_rate:.2f}%")
            print(f"📊 差异: {abs(actual_profit_rate - target_profit_rate):.6f}%")
            
            if abs(actual_profit_rate - target_profit_rate) < 0.01:
                print("✅ 计算结果与目标一致")
            else:
                print("⚠️  计算结果与目标有差异，市场价格可能已变化")
    
    # ==================== 深度数据验证测试 ====================
    def test_data_validation(self):
        """
        深度验证套利计算的实时数据获取和分析
        """
        print("\n🔬 深度套利数据验证分析")
        print("🎯 目标: 验证实时数据的准确性和套利计算的合理性")
        print(f"📅 验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取精确的市场数据
        market_data = self._get_precise_market_data()
        if not market_data:
            print("❌ 无法获取市场数据，验证终止")
            return
        
        # 手动计算套利路径
        manual_result = self._manual_arbitrage_calculation(market_data)
        if not manual_result:
            print("❌ 手动计算失败，验证终止")
            return
        
        print(f"\n✅ 验证分析完成")
        print(f"📊 手动计算利润率: {manual_result['profit_rate']:.6%}")
        
        if abs(manual_result['profit_rate']) > 0.01:  # 1%
            print(f"🚨 利润率异常，需要进一步分析")
        else:
            print(f"✅ 利润率在合理范围内")
    
    def _get_precise_market_data(self) -> Optional[Dict]:
        """获取精确的市场数据用于验证分析"""
        print("\n📊 获取实时订单簿数据:")
        print("-" * 40)
        
        try:
            okx_client = OKXClient()
            pairs = ['BTC-USDT', 'BTC-USDC', 'USDC-USDT']
            market_data = {}
            
            for pair in pairs:
                print(f"\n🔍 获取 {pair} 订单簿...")
                orderbook = okx_client.get_orderbook(pair, size="20")
                
                if orderbook:
                    market_data[pair] = {
                        'symbol': orderbook.symbol,
                        'timestamp': orderbook.timestamp,
                        'bids': orderbook.bids[:5],
                        'asks': orderbook.asks[:5],
                        'best_bid': orderbook.bids[0][0] if orderbook.bids else 0,
                        'best_ask': orderbook.asks[0][0] if orderbook.asks else 0,
                        'spread': 0,
                        'spread_pct': 0
                    }
                    
                    # 计算价差
                    if orderbook.bids and orderbook.asks:
                        best_bid = orderbook.bids[0][0]
                        best_ask = orderbook.asks[0][0]
                        spread = best_ask - best_bid
                        spread_pct = spread / best_bid * 100
                        
                        market_data[pair]['spread'] = spread
                        market_data[pair]['spread_pct'] = spread_pct
                    
                    print(f"  ✅ 数据获取成功")
                    print(f"  📈 最优买价: {market_data[pair]['best_bid']}")
                    print(f"  📉 最优卖价: {market_data[pair]['best_ask']}")
                    print(f"  📏 价差: {market_data[pair]['spread_pct']:.4f}%")
                else:
                    print(f"  ❌ 获取 {pair} 数据失败")
                    return None
            
            return market_data
            
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
            return None
    
    def _manual_arbitrage_calculation(self, market_data: Dict, initial_amount: float = 100.0, 
                                    fee_rate: float = 0.001) -> Optional[Dict]:
        """手动计算套利路径"""
        print(f"\n🧮 手动套利计算验证")
        print("=" * 60)
        print(f"💰 初始金额: {initial_amount} USDT")
        print(f"💸 手续费率: {fee_rate:.3%}")
        
        print("\n🛤️ **Path1 分析: USDT → BTC → USDC → USDT**")
        print("-" * 50)
        
        try:
            current_amount = initial_amount
            
            # 步骤1: USDT -> BTC
            print(f"\n📍 步骤1: USDT → BTC")
            btc_usdt_ask = market_data['BTC-USDT']['best_ask']
            btc_amount = (current_amount / btc_usdt_ask) * (1 - fee_rate)
            print(f"  获得: {btc_amount:.8f} BTC")
            current_amount = btc_amount
            
            # 步骤2: BTC -> USDC
            print(f"\n📍 步骤2: BTC → USDC")
            btc_usdc_bid = market_data['BTC-USDC']['best_bid']
            usdc_amount = (current_amount * btc_usdc_bid) * (1 - fee_rate)
            print(f"  获得: {usdc_amount:.6f} USDC")
            current_amount = usdc_amount
            
            # 步骤3: USDC -> USDT
            print(f"\n📍 步骤3: USDC → USDT")
            usdt_usdc_ask = market_data['USDC-USDT']['best_ask']
            final_usdt = (current_amount / usdt_usdc_ask) * (1 - fee_rate)
            print(f"  获得: {final_usdt:.6f} USDT")
            
            # 计算利润率
            profit = final_usdt - initial_amount
            profit_rate = profit / initial_amount
            
            print(f"\n📈 **最终结果:**")
            print(f"  💰 初始: {initial_amount} USDT")
            print(f"  💵 最终: {final_usdt:.6f} USDT") 
            print(f"  💲 利润: {profit:.6f} USDT")
            print(f"  📊 利润率: {profit_rate:.6%}")
            
            # 合理性分析
            total_fees = 3 * fee_rate
            print(f"\n🔍 **合理性分析:**")
            print(f"  💸 总手续费成本: {total_fees:.3%}")
            print(f"  📏 BTC-USDT价差: {market_data['BTC-USDT']['spread_pct']:.4f}%")
            print(f"  📏 BTC-USDC价差: {market_data['BTC-USDC']['spread_pct']:.4f}%")
            print(f"  📏 USDC-USDT价差: {market_data['USDC-USDT']['spread_pct']:.4f}%")
            
            return {
                'path': 'USDT->BTC->USDC->USDT',
                'initial_amount': initial_amount,
                'final_amount': final_usdt,
                'profit': profit,
                'profit_rate': profit_rate
            }
            
        except Exception as e:
            print(f"❌ 手动计算失败: {e}")
            return None


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TaoLi 专项测试集合')
    parser.add_argument('--test', type=str, choices=['arbitrage-detection', 'profit-calculation', 'data-validation'],
                        help='运行特定测试')
    parser.add_argument('--profit-rate', type=float, default=0.0537, 
                        help='目标利润率(用于profit-calculation测试，默认5.37%)')
    
    args = parser.parse_args()
    
    # 创建测试实例
    misc_tests = MiscTests()
    
    # 设置目标利润率
    if args.profit_rate:
        misc_tests.target_profit_rate = args.profit_rate
    
    try:
        if args.test == 'arbitrage-detection':
            # 运行套利检测准确性测试
            await misc_tests.test_arbitrage_detection()
        elif args.test == 'profit-calculation':
            # 运行利润计算分析测试
            misc_tests.test_profit_calculation()
        elif args.test == 'data-validation':
            # 运行深度数据验证测试
            misc_tests.test_data_validation()
        else:
            # 默认运行所有测试的快速版本
            print("🚀 运行所有测试的快速版本")
            print("=" * 60)
            await misc_tests.test_arbitrage_detection()
            misc_tests.test_profit_calculation()
            misc_tests.test_data_validation()
            print("\n✅ 所有测试完成")
            
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())