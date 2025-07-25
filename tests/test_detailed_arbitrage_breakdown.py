#!/usr/bin/env python3
"""
详细套利计算过程分析 - 5.37%利润率完整验证
"""

import sys
import os
import time
from datetime import datetime
import json

# 添加项目根目录到path  
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.okx_client import OKXClient
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
import asyncio


def print_section_header(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def print_step_header(step_num, title):
    """打印步骤标题"""
    print(f"\n{'📍' if step_num else '🎯'} [{step_num if step_num else 'FINAL'}] {title}")
    print("-" * 50)


def get_detailed_market_data():
    """获取详细的市场数据用于完整验证"""
    print_section_header("获取实时市场数据")
    
    try:
        # 初始化OKX客户端
        okx_client = OKXClient()
        print("✅ OKX客户端初始化成功")
        
        # 获取三个关键交易对的详细数据
        pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
        detailed_data = {}
        
        for pair in pairs:
            print(f"\n🔍 获取 {pair} 详细数据...")
            orderbook = okx_client.get_orderbook(pair, size="20")
            
            if orderbook:
                # 保存原始数据
                detailed_data[pair] = {
                    'symbol': orderbook.symbol,
                    'timestamp': orderbook.timestamp,
                    'timestamp_str': datetime.fromtimestamp(orderbook.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f'),
                    'raw_bids': orderbook.bids[:10],  # 前10档
                    'raw_asks': orderbook.asks[:10],  # 前10档
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
                
                # 打印详细信息
                print(f"  📊 时间戳: {detailed_data[pair]['timestamp_str']}")
                print(f"  📈 最优买价: {detailed_data[pair]['best_bid']:,.8f} (数量: {detailed_data[pair]['best_bid_size']:.8f})")
                print(f"  📉 最优卖价: {detailed_data[pair]['best_ask']:,.8f} (数量: {detailed_data[pair]['best_ask_size']:.8f})")
                print(f"  📏 价差: {detailed_data[pair]['spread_abs']:.8f} ({detailed_data[pair]['spread_pct']:.6f}%)")
                print(f"  🎯 中间价: {detailed_data[pair]['mid_price']:,.8f}")
                
            else:
                print(f"  ❌ 获取 {pair} 数据失败")
                return None
        
        return detailed_data
        
    except Exception as e:
        print(f"❌ 获取市场数据失败: {e}")
        return None


def detailed_arbitrage_calculation(market_data, initial_amount=1000.0, fee_rate=0.001):
    """详细的套利计算过程分析"""
    print_section_header("完整套利计算过程分析")
    print(f"🎯 分析目标: 验证5.37%利润率的每个计算细节")
    print(f"💰 初始投资金额: {initial_amount:,.2f} USDT")
    print(f"💸 手续费率: {fee_rate:.3%} (每笔交易)")
    print(f"📊 套利路径: USDT → BTC → USDC → USDT")
    
    # 记录完整的计算过程
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
        step_count = 0
        
        # 步骤1: USDT -> BTC (买入BTC)
        step_count += 1
        print_step_header(step_count, "USDT → BTC (买入BTC)")
        
        # 获取BTC-USDT的卖一价（买BTC用的价格）
        btc_usdt_ask = market_data['BTC-USDT']['best_ask']
        btc_usdt_ask_size = market_data['BTC-USDT']['best_ask_size']
        btc_usdt_timestamp = market_data['BTC-USDT']['timestamp_str']
        
        print(f"  🏷️ 使用价格: {btc_usdt_ask:,.2f} USDT/BTC")
        print(f"  📊 价格来源: BTC-USDT 卖一价 (ask price)")
        print(f"  📈 可用数量: {btc_usdt_ask_size:.8f} BTC")
        print(f"  🕐 数据时间: {btc_usdt_timestamp}")
        print(f"  💰 投入金额: {current_amount:,.8f} USDT")
        
        # 计算能买到的BTC数量（扣除手续费）
        gross_btc = current_amount / btc_usdt_ask
        fee_amount_1 = gross_btc * fee_rate
        net_btc = gross_btc * (1 - fee_rate)
        
        print(f"  🧮 计算过程:")
        print(f"    • 总BTC数量 = {current_amount:,.8f} USDT ÷ {btc_usdt_ask:,.2f} = {gross_btc:.10f} BTC")
        print(f"    • 手续费 = {gross_btc:.10f} × {fee_rate:.3%} = {fee_amount_1:.10f} BTC")
        print(f"    • 净得BTC = {gross_btc:.10f} × (1 - {fee_rate:.3%}) = {net_btc:.10f} BTC")
        print(f"  📊 结果: 获得 {net_btc:.10f} BTC")
        
        # 记录步骤1
        step1_data = {
            'step': 1,
            'from_asset': 'USDT',
            'to_asset': 'BTC',
            'input_amount': current_amount,
            'exchange_rate': btc_usdt_ask,
            'rate_source': 'BTC-USDT ask price',
            'gross_output': gross_btc,
            'fee_amount': fee_amount_1,
            'net_output': net_btc,
            'data_timestamp': btc_usdt_timestamp
        }
        calculation_log['steps'].append(step1_data)
        calculation_log['market_data_used']['BTC-USDT'] = market_data['BTC-USDT']
        
        current_amount = net_btc
        
        # 步骤2: BTC -> USDC (卖出BTC)
        step_count += 1
        print_step_header(step_count, "BTC → USDC (卖出BTC)")
        
        # 获取BTC-USDC的买一价（卖BTC用的价格）
        btc_usdc_bid = market_data['BTC-USDC']['best_bid']
        btc_usdc_bid_size = market_data['BTC-USDC']['best_bid_size']
        btc_usdc_timestamp = market_data['BTC-USDC']['timestamp_str']
        
        print(f"  🏷️ 使用价格: {btc_usdc_bid:,.2f} USDC/BTC")
        print(f"  📊 价格来源: BTC-USDC 买一价 (bid price)")
        print(f"  📉 可接受数量: {btc_usdc_bid_size:.8f} BTC")
        print(f"  🕐 数据时间: {btc_usdc_timestamp}")
        print(f"  💰 投入金额: {current_amount:.10f} BTC")
        
        # 计算能得到的USDC数量（扣除手续费）
        gross_usdc = current_amount * btc_usdc_bid
        fee_amount_2 = gross_usdc * fee_rate
        net_usdc = gross_usdc * (1 - fee_rate)
        
        print(f"  🧮 计算过程:")
        print(f"    • 总USDC数量 = {current_amount:.10f} BTC × {btc_usdc_bid:,.2f} = {gross_usdc:.8f} USDC")
        print(f"    • 手续费 = {gross_usdc:.8f} × {fee_rate:.3%} = {fee_amount_2:.8f} USDC")
        print(f"    • 净得USDC = {gross_usdc:.8f} × (1 - {fee_rate:.3%}) = {net_usdc:.8f} USDC")
        print(f"  📊 结果: 获得 {net_usdc:.8f} USDC")
        
        # 记录步骤2
        step2_data = {
            'step': 2,
            'from_asset': 'BTC',
            'to_asset': 'USDC',
            'input_amount': current_amount,
            'exchange_rate': btc_usdc_bid,
            'rate_source': 'BTC-USDC bid price',
            'gross_output': gross_usdc,
            'fee_amount': fee_amount_2,
            'net_output': net_usdc,
            'data_timestamp': btc_usdc_timestamp
        }
        calculation_log['steps'].append(step2_data)
        calculation_log['market_data_used']['BTC-USDC'] = market_data['BTC-USDC']
        
        current_amount = net_usdc
        
        # 步骤3: USDC -> USDT (兑换回USDT)
        step_count += 1
        print_step_header(step_count, "USDC → USDT (兑换回USDT)")
        
        # 获取USDT-USDC的卖一价（买USDT用的价格）
        usdt_usdc_ask = market_data['USDT-USDC']['best_ask']
        usdt_usdc_ask_size = market_data['USDT-USDC']['best_ask_size']
        usdt_usdc_timestamp = market_data['USDT-USDC']['timestamp_str']
        
        # USDT-USDC交易对：买USDT用USDC支付
        print(f"  🏷️ 使用价格: {usdt_usdc_ask:.6f} USDC/USDT")
        print(f"  📊 价格来源: USDT-USDC 卖一价 (ask price)")
        print(f"  📈 可用数量: {usdt_usdc_ask_size:.2f} USDT")
        print(f"  🕐 数据时间: {usdt_usdc_timestamp}")
        print(f"  💰 投入金额: {current_amount:.8f} USDC")
        
        # 计算能得到的USDT数量（扣除手续费）
        gross_usdt = current_amount / usdt_usdc_ask
        fee_amount_3 = gross_usdt * fee_rate
        net_usdt = gross_usdt * (1 - fee_rate)
        
        print(f"  �� 计算过程:")
        print(f"    • 总USDT数量 = {current_amount:.8f} USDC ÷ {usdt_usdc_ask:.6f} = {gross_usdt:.8f} USDT")
        print(f"    • 手续费 = {gross_usdt:.8f} × {fee_rate:.3%} = {fee_amount_3:.8f} USDT")
        print(f"    • 净得USDT = {gross_usdt:.8f} × (1 - {fee_rate:.3%}) = {net_usdt:.8f} USDT")
        print(f"  📊 结果: 获得 {net_usdt:.8f} USDT")
        
        # 记录步骤3
        step3_data = {
            'step': 3,
            'from_asset': 'USDC',
            'to_asset': 'USDT',
            'input_amount': current_amount,
            'exchange_rate': usdt_usdc_ask,
            'rate_source': 'USDT-USDC ask price',
            'gross_output': gross_usdt,
            'fee_amount': fee_amount_3,
            'net_output': net_usdt,
            'data_timestamp': usdt_usdc_timestamp
        }
        calculation_log['steps'].append(step3_data)
        calculation_log['market_data_used']['USDT-USDC'] = market_data['USDT-USDC']
        
        final_amount = net_usdt
        
        # 计算最终利润和利润率
        print_step_header(0, "最终结果计算")
        
        total_profit = final_amount - initial_amount
        profit_rate = total_profit / initial_amount
        total_fees_usdt = (fee_amount_1 * btc_usdt_ask) + fee_amount_2 + fee_amount_3
        
        print(f"  💰 初始投资: {initial_amount:,.8f} USDT")
        print(f"  💵 最终获得: {final_amount:,.8f} USDT")
        print(f"  💲 绝对利润: {total_profit:,.8f} USDT")
        print(f"  📊 利润率: ({final_amount:,.8f} - {initial_amount:,.8f}) ÷ {initial_amount:,.8f} = {profit_rate:.8f}")
        print(f"  📈 利润率百分比: {profit_rate:.6%}")
        print(f"  💸 总手续费成本: {total_fees_usdt:.8f} USDT")
        
        # 记录最终结果
        calculation_log['final_result'] = {
            'initial_amount': initial_amount,
            'final_amount': final_amount,
            'absolute_profit': total_profit,
            'profit_rate': profit_rate,
            'profit_rate_percent': profit_rate * 100,
            'total_fees_usdt': total_fees_usdt
        }
        
        # 分析异常原因
        print_section_header("异常原因分析")
        
        # USDT-USDC汇率分析
        usdt_usdc_rate = 1 / usdt_usdc_ask
        print(f"🔍 关键汇率分析:")
        print(f"  • USDT-USDC卖价: {usdt_usdc_ask:.6f}")
        print(f"  • 隐含USDT/USDC汇率: {usdt_usdc_rate:.6f}")
        print(f"  • 正常市场预期: 约1.000 (±0.002)")
        print(f"  • 当前偏差: {(usdt_usdc_rate - 1.0) * 100:+.3f}%")
        
        # BTC价格套利空间分析
        btc_price_diff = btc_usdc_bid - btc_usdt_ask
        btc_price_diff_pct = btc_price_diff / btc_usdt_ask * 100
        print(f"\n🔍 BTC价格差异分析:")
        print(f"  • BTC-USDT卖价: {btc_usdt_ask:,.2f}")
        print(f"  • BTC-USDC买价: {btc_usdc_bid:,.2f}")
        print(f"  • 价格差异: {btc_price_diff:+.2f} ({btc_price_diff_pct:+.4f}%)")
        
        # 理论利润计算
        theoretical_profit = ((btc_usdc_bid / btc_usdt_ask) * usdt_usdc_rate - 1) * 100
        print(f"\n🔍 理论利润率:")
        print(f"  • 计算公式: (BTC_USDC/BTC_USDT) × (1/USDT_USDC) - 1")
        print(f"  • 理论利润: ({btc_usdc_bid:.2f}/{btc_usdt_ask:.2f}) × {usdt_usdc_rate:.6f} - 1 = {theoretical_profit:.4f}%")
        print(f"  • 实际利润: {profit_rate * 100:.4f}%")
        print(f"  • 手续费影响: -{fee_rate * 3 * 100:.2f}%")
        
        return calculation_log
        
    except Exception as e:
        print(f"❌ 计算过程失败: {e}")
        return None


def compare_with_system_result(manual_result):
    """与系统计算结果对比"""
    print_section_header("与系统计算结果对比")
    
    if manual_result:
        manual_profit_rate = manual_result['final_result']['profit_rate_percent']
        print(f"📊 手动计算结果: {manual_profit_rate:.6f}%")
        print(f"📊 系统报告结果: 5.37%")
        print(f"📊 差异: {abs(manual_profit_rate - 5.37):.6f}%")
        
        if abs(manual_profit_rate - 5.37) < 0.01:
            print("✅ 计算结果一致，数学逻辑正确")
        else:
            print("❌ 计算结果有差异，需要进一步分析")


if __name__ == "__main__":
    print("🔬 套利利润率5.37%详细计算过程分析")
    print("🎯 目标: 验证每个数值的来源和计算过程")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 获取详细市场数据
    market_data = get_detailed_market_data()
    if not market_data:
        print("❌ 无法获取市场数据，分析终止")
        exit(1)
    
    # 2. 详细计算过程分析
    calculation_result = detailed_arbitrage_calculation(market_data)
    if not calculation_result:
        print("❌ 计算分析失败，分析终止")
        exit(1)
    
    # 3. 与系统结果对比
    compare_with_system_result(calculation_result)
    
    # 4. 保存详细分析结果
    with open('arbitrage_calculation_breakdown.json', 'w', encoding='utf-8') as f:
        json.dump(calculation_result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 详细分析完成")
    print(f"📄 完整数据已保存到: arbitrage_calculation_breakdown.json")
    print(f"📊 最终利润率: {calculation_result['final_result']['profit_rate_percent']:.6f}%")
