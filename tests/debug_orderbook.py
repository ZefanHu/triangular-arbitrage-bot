#!/usr/bin/env python3
"""
调试订单簿数据格式
"""
import sys
import asyncio
import json
import os
from dataclasses import asdict

# Add parent directory to path to access project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.okx_client import OKXClient
from config.config_manager import ConfigManager
from models.order_book import OrderBook

def format_orderbook_data(orderbook: OrderBook) -> dict:
    """
    将OrderBook对象转换为易读的字典格式
    
    Args:
        orderbook: OrderBook对象
        
    Returns:
        格式化的字典数据
    """
    if not orderbook:
        return None
        
    return {
        'symbol': orderbook.symbol,
        'timestamp': orderbook.timestamp,
        'bids_count': len(orderbook.bids),
        'asks_count': len(orderbook.asks),
        'best_bid': orderbook.get_best_bid(),
        'best_ask': orderbook.get_best_ask(),
        'spread': orderbook.get_spread(),
        'mid_price': orderbook.get_mid_price(),
        'top_5_bids': orderbook.bids[:5],
        'top_5_asks': orderbook.asks[:5],
        'is_valid': orderbook.is_valid()
    }

async def debug_orderbook():
    """调试订单簿数据格式"""
    try:
        # 初始化配置和客户端
        config = ConfigManager()
        client = OKXClient()

        print("=== 开始调试订单簿数据格式 ===")

        # 测试不同的交易对
        test_pairs = ['BTC-USDT', 'ETH-USDT']

        for pair in test_pairs:
            print(f"\n--- 测试 {pair} ---")

            try:
                # 获取订单簿数据
                orderbook_data = client.get_orderbook(pair)

                # 输出原始数据类型
                print(f"返回数据类型: {type(orderbook_data)}")

                if orderbook_data is None:
                    print("❌ 订单簿数据为空")
                    continue

                # 检查是否为OrderBook对象
                if isinstance(orderbook_data, OrderBook):
                    print("✅ 成功获取OrderBook对象")
                    
                    # 格式化数据进行详细分析
                    formatted_data = format_orderbook_data(orderbook_data)
                    
                    print(f"交易对: {formatted_data['symbol']}")
                    print(f"时间戳: {formatted_data['timestamp']}")
                    print(f"买单数量: {formatted_data['bids_count']}")
                    print(f"卖单数量: {formatted_data['asks_count']}")
                    print(f"最优买价: {formatted_data['best_bid']}")
                    print(f"最优卖价: {formatted_data['best_ask']}")
                    print(f"价差: {formatted_data['spread']}")
                    print(f"中间价: {formatted_data['mid_price']}")
                    print(f"数据有效性: {formatted_data['is_valid']}")
                    
                    # 显示前5档买卖盘
                    print("\n前5档买盘:")
                    for i, bid in enumerate(formatted_data['top_5_bids']):
                        print(f"  {i+1}. 价格: {bid[0]}, 数量: {bid[1]}")
                    
                    print("\n前5档卖盘:")
                    for i, ask in enumerate(formatted_data['top_5_asks']):
                        print(f"  {i+1}. 价格: {ask[0]}, 数量: {ask[1]}")
                    
                    # 可选：将OrderBook对象转换为字典查看完整结构
                    print(f"\n完整OrderBook结构:")
                    full_dict = asdict(orderbook_data)
                    print(f"  symbol: {full_dict['symbol']}")
                    print(f"  timestamp: {full_dict['timestamp']}")
                    print(f"  bids总数: {len(full_dict['bids'])}")
                    print(f"  asks总数: {len(full_dict['asks'])}")
                    
                else:
                    print(f"❌ 意外的数据类型: {type(orderbook_data)}")
                    print(f"数据内容: {orderbook_data}")

            except Exception as e:
                print(f"❌ 获取{pair}订单簿失败: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_orderbook())
