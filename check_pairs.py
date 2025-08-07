#!/usr/bin/env python3
"""
Check which trading pairs are actually available on OKX
"""

import sys
import requests
import json

def check_okx_pairs():
    """Check available trading pairs on OKX"""
    
    # OKX public API endpoint for instruments
    url = "https://www.okx.com/api/v5/public/instruments"
    
    # We're interested in spot trading
    params = {
        "instType": "SPOT"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['code'] == '0':
            instruments = data['data']
            
            # Filter for pairs we're interested in
            target_pairs = []
            for inst in instruments:
                inst_id = inst['instId']
                
                # Check for BTC, USDT, USDC combinations
                if any(base in inst_id for base in ['BTC', 'USDT', 'USDC']):
                    if 'BTC' in inst_id and ('USDT' in inst_id or 'USDC' in inst_id):
                        target_pairs.append(inst_id)
                    elif 'USDT' in inst_id and 'USDC' in inst_id:
                        target_pairs.append(inst_id)
            
            print("Available relevant trading pairs on OKX:")
            print("-" * 40)
            
            # Sort and display
            for pair in sorted(target_pairs):
                print(f"  {pair}")
            
            print("\nSpecifically checking for triangular arbitrage pairs:")
            print("-" * 40)
            
            # Check specific pairs
            check_pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC', 'USDC-USDT']
            for pair in check_pairs:
                if pair in [inst['instId'] for inst in instruments]:
                    print(f"  ✓ {pair} - Available")
                else:
                    print(f"  ✗ {pair} - NOT available")
            
            # Find alternative pairs
            print("\nSuggested triangular arbitrage paths:")
            print("-" * 40)
            
            btc_pairs = [p for p in target_pairs if 'BTC' in p]
            usdt_usdc_pairs = [p for p in target_pairs if 'USDT' in p and 'USDC' in p]
            
            print(f"  BTC pairs: {', '.join(btc_pairs[:5])}")
            print(f"  USDT-USDC pairs: {', '.join(usdt_usdc_pairs)}")
            
        else:
            print(f"Error fetching data: {data}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_okx_pairs()