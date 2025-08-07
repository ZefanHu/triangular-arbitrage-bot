#!/usr/bin/env python3
"""
Quick test to verify data collection with new trading pairs
"""

import sys
import asyncio
import time

sys.path.append('/home/ubuntu/taoli')

from config.config_manager import ConfigManager
from core.trading_controller import TradingController

async def quick_test():
    print("\n=== Quick Data Collection Test ===\n")
    
    # Initialize
    config_manager = ConfigManager()
    controller = TradingController(config_manager, enable_rich_logging=False)
    
    # Start in monitor mode
    controller.disable_trading("Monitor mode test")
    
    print("1. Starting controller...")
    await controller.start()
    
    # Wait for data
    print("2. Waiting for data collection...")
    await asyncio.sleep(5)
    
    # Check data
    print("\n3. Checking collected data:")
    print("-" * 40)
    
    # Check orderbooks
    pairs = ['BTC-USDT', 'ETH-USDT', 'ETH-BTC', 'USDC-USDT']
    for pair in pairs:
        orderbook = controller.data_collector.get_orderbook(pair)
        if orderbook and orderbook.is_valid():
            print(f"  ✓ {pair}: bid={orderbook.get_best_bid():.4f}")
        else:
            print(f"  ✗ {pair}: No data")
    
    # Check analyses
    print("\n4. Checking arbitrage analyses:")
    print("-" * 40)
    
    if hasattr(controller, 'arbitrage_engine'):
        analyses = getattr(controller.arbitrage_engine, 'recent_analyses', [])
        if analyses:
            for a in analyses[-3:]:
                rate = a.get('profit_rate', 0)
                if rate == -1:
                    print(f"  ✗ {a.get('path_name')}: ERROR (-100%)")
                else:
                    print(f"  ✓ {a.get('path_name')}: {rate*100:+.3f}%")
        else:
            print("  No analyses yet")
    
    # Stop
    print("\n5. Stopping controller...")
    await controller.stop()
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(quick_test())