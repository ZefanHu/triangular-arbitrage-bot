#!/usr/bin/env python3
"""
调试订单簿数据格式
"""
import sys
import asyncio
import json
sys.path.append('.')

from core.okx_client import OKXClient
from config.config_manager import ConfigManager

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

                # 输出原始数据
                print(f"原始数据类型: {type(orderbook_data)}")
                print(f"原始数据: {json.dumps(orderbook_data, indent=2, default=str)}")

                # 检查数据结构
                if isinstance(orderbook_data, dict):
                    print(f"数据键: {list(orderbook_data.keys())}")

                    # 检查是否有data字段
                    if 'data' in orderbook_data:
                        print(f"data字段类型: {type(orderbook_data['data'])}")
                        if isinstance(orderbook_data['data'], list) and len(orderbook_data['data']) > 0:
                            data = orderbook_data['data'][0]
                            print(f"data[0]键: {list(data.keys()) if isinstance(data, dict) else 'data[0]不是字典'}")

                            # 检查bids和asks
                            if isinstance(data, dict):
                                if 'bids' in data and 'asks' in data:
                                    print(f"bids数量: {len(data['bids'])}")
                                    print(f"asks数量: {len(data['asks'])}")

                                    if data['bids']:
                                        print(f"第一个bid: {data['bids'][0]}")
                                    if data['asks']:
                                        print(f"第一个ask: {data['asks'][0]}")
                                else:
                                    print("❌ 缺少bids或asks字段")
                            else:
                                print("❌ data[0]不是字典格式")
                        else:
                            print("❌ data字段为空或不是列表")
                    else:
                        print("❌ 缺少data字段")

                        # 如果没有data字段，检查其他可能的结构
                        if 'bids' in orderbook_data and 'asks' in orderbook_data:
                            print("✅ 发现直接的bids/asks结构")
                            print(f"bids数量: {len(orderbook_data['bids'])}")
                            print(f"asks数量: {len(orderbook_data['asks'])}")
                else:
                    print("❌ 返回数据不是字典格式")

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
