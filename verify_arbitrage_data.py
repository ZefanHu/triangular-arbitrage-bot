#!/usr/bin/env python3
"""
深度验证套利计算的实时数据获取和分析脚本
"""

import sys
import os
import time
from datetime import datetime

# 添加项目根目录到path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.okx_client import OKXClient
from core.data_collector import DataCollector
import asyncio


def get_precise_market_data():
    """获取精确的市场数据用于验证分析"""
    print("🔍 深度验证套利计算 - 实时数据获取")
    print("=" * 60)
    print(f"📅 获取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 初始化OKX客户端
        okx_client = OKXClient()
        print("✅ OKX客户端初始化成功")
        
        # 获取三个关键交易对的订单簿数据
        pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
        market_data = {}
        
        print("\n📊 获取实时订单簿数据:")
        print("-" * 40)
        
        for pair in pairs:
            print(f"\n🔍 获取 {pair} 订单簿...")
            orderbook = okx_client.get_orderbook(pair, size="20")
            
            if orderbook:
                market_data[pair] = {
                    'symbol': orderbook.symbol,
                    'timestamp': orderbook.timestamp,
                    'bids': orderbook.bids[:5],  # 前5档买单
                    'asks': orderbook.asks[:5],  # 前5档卖单
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
                print(f"  📏 价差: {market_data[pair]['spread']:.8f} ({market_data[pair]['spread_pct']:.4f}%)")
                print(f"  🕐 时间戳: {market_data[pair]['timestamp']}")
            else:
                print(f"  ❌ 获取 {pair} 数据失败")
                return None
        
        return market_data
        
    except Exception as e:
        print(f"❌ 获取市场数据失败: {e}")
        return None


def manual_arbitrage_calculation(market_data, initial_amount=100.0, fee_rate=0.001):
    """手动计算套利路径，详细记录每个步骤"""
    print(f"\n🧮 手动套利计算验证")
    print("=" * 60)
    print(f"💰 初始金额: {initial_amount} USDT")
    print(f"💸 手续费率: {fee_rate:.3%}")
    print()
    
    # Path1: USDT -> BTC -> USDC -> USDT
    print("🛤️ **Path1 分析: USDT → BTC → USDC → USDT**")
    print("-" * 50)
    
    try:
        current_amount = initial_amount
        
        # 步骤1: USDT -> BTC (买入BTC)
        print(f"\n📍 步骤1: USDT → BTC (买入BTC)")
        btc_usdt_ask = market_data['BTC-USDT']['best_ask']  # 买入BTC用卖一价
        print(f"  🏷️ 使用价格: {btc_usdt_ask} (BTC-USDT 卖一价)")
        print(f"  💰 投入: {current_amount} USDT")
        
        btc_amount = (current_amount / btc_usdt_ask) * (1 - fee_rate)
        print(f"  🧮 计算: ({current_amount} / {btc_usdt_ask}) × (1 - {fee_rate}) = {btc_amount:.8f}")
        print(f"  📊 获得: {btc_amount:.8f} BTC")
        current_amount = btc_amount
        
        # 步骤2: BTC -> USDC (卖出BTC) 
        print(f"\n📍 步骤2: BTC → USDC (卖出BTC)")
        btc_usdc_bid = market_data['BTC-USDC']['best_bid']  # 卖出BTC用买一价
        print(f"  🏷️ 使用价格: {btc_usdc_bid} (BTC-USDC 买一价)")
        print(f"  💰 投入: {current_amount:.8f} BTC")
        
        usdc_amount = (current_amount * btc_usdc_bid) * (1 - fee_rate)
        print(f"  🧮 计算: ({current_amount:.8f} × {btc_usdc_bid}) × (1 - {fee_rate}) = {usdc_amount:.6f}")
        print(f"  📊 获得: {usdc_amount:.6f} USDC")
        current_amount = usdc_amount
        
        # 步骤3: USDC -> USDT (买入USDT)
        print(f"\n📍 步骤3: USDC → USDT (买入USDT)")
        usdt_usdc_ask = market_data['USDT-USDC']['best_ask']  # 买入USDT用卖一价
        print(f"  🏷️ 使用价格: {usdt_usdc_ask} (USDT-USDC 卖一价)")
        print(f"  💰 投入: {current_amount:.6f} USDC")
        
        final_usdt = (current_amount / usdt_usdc_ask) * (1 - fee_rate)
        print(f"  🧮 计算: ({current_amount:.6f} / {usdt_usdc_ask}) × (1 - {fee_rate}) = {final_usdt:.6f}")
        print(f"  📊 获得: {final_usdt:.6f} USDT")
        
        # 计算利润率
        profit = final_usdt - initial_amount
        profit_rate = profit / initial_amount
        
        print(f"\n📈 **Path1 最终结果:**")
        print(f"  💰 初始金额: {initial_amount} USDT")
        print(f"  💵 最终金额: {final_usdt:.6f} USDT") 
        print(f"  💲 利润: {profit:.6f} USDT")
        print(f"  📊 利润率: {profit_rate:.6%}")
        
        # 合理性分析
        total_fees = 3 * fee_rate  # 三笔交易的总手续费率
        print(f"\n🔍 **合理性分析:**")
        print(f"  💸 总手续费成本: {total_fees:.3%}")
        print(f"  📏 BTC-USDT价差: {market_data['BTC-USDT']['spread_pct']:.4f}%")
        print(f"  📏 BTC-USDC价差: {market_data['BTC-USDC']['spread_pct']:.4f}%")
        print(f"  📏 USDT-USDC价差: {market_data['USDT-USDC']['spread_pct']:.4f}%")
        
        # 关键价格比率分析
        btc_price_ratio = btc_usdc_bid / btc_usdt_ask  # BTC在USDC和USDT市场的价格比率
        usdt_usdc_rate = 1 / usdt_usdc_ask  # USDT/USDC汇率
        
        print(f"\n🔬 **关键比率分析:**")
        print(f"  🏷️ BTC价格比率 (USDC/USDT): {btc_price_ratio:.6f}")
        print(f"  🏷️ USDT/USDC汇率: {usdt_usdc_rate:.6f}")
        print(f"  🔍 理论利润空间: {(btc_price_ratio * usdt_usdc_rate - 1):.6%}")
        
        return {
            'path': 'USDT->BTC->USDC->USDT',
            'initial_amount': initial_amount,
            'final_amount': final_usdt,
            'profit': profit,
            'profit_rate': profit_rate,
            'steps': [
                {'step': 1, 'from': 'USDT', 'to': 'BTC', 'price': btc_usdt_ask, 'amount': btc_amount},
                {'step': 2, 'from': 'BTC', 'to': 'USDC', 'price': btc_usdc_bid, 'amount': usdc_amount},
                {'step': 3, 'from': 'USDC', 'to': 'USDT', 'price': usdt_usdc_ask, 'amount': final_usdt}
            ],
            'analysis': {
                'total_fees': total_fees,
                'btc_price_ratio': btc_price_ratio,
                'usdt_usdc_rate': usdt_usdc_rate,
                'theoretical_profit': btc_price_ratio * usdt_usdc_rate - 1
            }
        }
        
    except Exception as e:
        print(f"❌ 手动计算失败: {e}")
        return None


def compare_with_system_calculation():
    """对比系统计算结果"""
    print(f"\n🔄 系统计算对比")
    print("=" * 60)
    
    # 运行系统的套利计算
    print("🚀 运行系统套利计算...")
    
    # 这里我们需要运行系统的套利引擎来获取计算结果
    # 然后与我们的手动计算进行对比
    
    return True


if __name__ == "__main__":
    print("🔬 超深度套利利润率验证分析")
    print("🎯 目标: 找出5.38%异常高利润率的根本原因")
    print()
    
    # 1. 获取实时市场数据
    market_data = get_precise_market_data()
    if not market_data:
        print("❌ 无法获取市场数据，验证终止")
        exit(1)
    
    # 2. 手动计算套利路径
    manual_result = manual_arbitrage_calculation(market_data)
    if not manual_result:
        print("❌ 手动计算失败，验证终止")
        exit(1)
    
    # 3. 对比系统计算
    # compare_with_system_calculation()
    
    print(f"\n✅ 验证分析完成")
    print(f"📊 手动计算利润率: {manual_result['profit_rate']:.6%}")
    
    if abs(manual_result['profit_rate']) > 0.01:  # 1%
        print(f"🚨 利润率异常，需要进一步分析")
    else:
        print(f"✅ 利润率在合理范围内")