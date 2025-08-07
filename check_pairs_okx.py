#!/usr/bin/env python3
"""
Check which trading pairs are actually available on OKX using the OKX client
"""

import sys
import asyncio

sys.path.append('/home/ubuntu/taoli')

from core.okx_client import OKXClient

def check_okx_pairs():
    """Check available trading pairs on OKX"""
    
    client = OKXClient()
    
    # Test specific pairs
    test_pairs = [
        'BTC-USDT',
        'BTC-USDC', 
        'USDT-USDC',
        'USDC-USDT',
        'ETH-USDT',
        'ETH-USDC'
    ]
    
    print("Testing trading pairs availability on OKX:")
    print("-" * 50)
    
    for pair in test_pairs:
        try:
            # Try to get orderbook for the pair
            orderbook = client.get_orderbook(pair)
            
            if orderbook and hasattr(orderbook, 'bids') and orderbook.bids:
                print(f"  ✓ {pair:<12} - Available (bid: {orderbook.bids[0][0]:.4f})")
            else:
                print(f"  ✗ {pair:<12} - NOT available or no data")
                
        except Exception as e:
            print(f"  ✗ {pair:<12} - Error: {str(e)[:50]}")
    
    print("\n" + "=" * 50)
    print("Recommendation for triangular arbitrage:")
    print("-" * 50)
    
    # Based on common OKX pairs
    print("\nOption 1: BTC-USDT and USDC-USDT")
    print("  Path 1: USDT -> BTC -> USDT (via BTC-USDT)")
    print("  Path 2: USDT -> USDC -> USDT (via USDC-USDT)")
    print("\nNote: Direct BTC-USDC pair may not be available.")
    print("Most exchanges use USDC-USDT instead of USDT-USDC")

if __name__ == "__main__":
    check_okx_pairs()