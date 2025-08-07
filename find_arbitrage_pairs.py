#!/usr/bin/env python3
"""
Find valid triangular arbitrage paths on OKX
"""

import sys
sys.path.append('/home/ubuntu/taoli')

from core.okx_client import OKXClient

def find_triangular_paths():
    """Find valid triangular arbitrage paths"""
    
    client = OKXClient()
    
    # Common trading pairs to test
    test_pairs = [
        'BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'SOL-USDT',
        'USDC-USDT', 'DAI-USDT', 'BUSD-USDT',
        'ETH-BTC', 'BNB-BTC', 'SOL-BTC',
        'ETH-USDC', 'BTC-USDC', 'BNB-USDC',
        'MATIC-USDT', 'AVAX-USDT', 'DOT-USDT'
    ]
    
    print("Checking available pairs on OKX:")
    print("-" * 50)
    
    available_pairs = []
    
    for pair in test_pairs:
        try:
            orderbook = client.get_orderbook(pair)
            if orderbook and hasattr(orderbook, 'bids') and orderbook.bids:
                available_pairs.append(pair)
                print(f"  ✓ {pair}")
        except:
            pass
    
    print(f"\nFound {len(available_pairs)} available pairs")
    
    # Find triangular paths
    print("\n" + "=" * 50)
    print("Possible triangular arbitrage paths:")
    print("-" * 50)
    
    # Group pairs by assets
    assets = set()
    pair_map = {}
    
    for pair in available_pairs:
        parts = pair.split('-')
        if len(parts) == 2:
            base, quote = parts
            assets.add(base)
            assets.add(quote)
            
            if base not in pair_map:
                pair_map[base] = {}
            pair_map[base][quote] = pair
            
            if quote not in pair_map:
                pair_map[quote] = {}
            pair_map[quote][base] = pair
    
    # Find triangular paths starting with USDT
    paths_found = []
    
    if 'USDT' in pair_map:
        for asset1 in pair_map['USDT']:
            if asset1 in pair_map:
                for asset2 in pair_map[asset1]:
                    if asset2 != 'USDT' and asset2 in pair_map:
                        if 'USDT' in pair_map[asset2]:
                            # Found a triangular path: USDT -> asset1 -> asset2 -> USDT
                            path = f"USDT -> {asset1} -> {asset2} -> USDT"
                            pairs_used = [
                                pair_map['USDT'].get(asset1, f"{asset1}-USDT"),
                                pair_map[asset1].get(asset2, f"{asset2}-{asset1}"),
                                pair_map[asset2].get('USDT', f"USDT-{asset2}")
                            ]
                            
                            # Check if all pairs exist
                            if all(p in available_pairs for p in pairs_used):
                                paths_found.append((path, pairs_used))
    
    # Display found paths
    if paths_found:
        for i, (path, pairs) in enumerate(paths_found[:5], 1):
            print(f"\nPath {i}: {path}")
            print(f"  Pairs: {' -> '.join(pairs)}")
    else:
        print("\nNo valid triangular paths found with available pairs")
    
    # Suggest simple arbitrage
    print("\n" + "=" * 50)
    print("Alternative: Two-pair arbitrage")
    print("-" * 50)
    print("\nSince true triangular arbitrage may be limited, consider:")
    print("1. Spread arbitrage on BTC-USDT")
    print("2. Spread arbitrage on ETH-USDT")
    print("3. USDT-USDC conversion arbitrage")

if __name__ == "__main__":
    find_triangular_paths()