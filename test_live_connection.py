#!/usr/bin/env python3
"""
Test live trading connection and data retrieval
"""

import sys
import asyncio
import time
from rich.console import Console
from rich.table import Table

sys.path.append('/home/ubuntu/taoli')

from config.config_manager import ConfigManager
from core.okx_client import OKXClient
from core.trading_controller import TradingController

async def test_live_connection():
    console = Console()
    
    console.print("\n[bold yellow]🔴 LIVE TRADING MODE TEST[/bold yellow]")
    console.print("[red]This will connect to your REAL trading account![/red]\n")
    
    # Step 1: Check configuration
    console.print("1. Checking configuration...")
    config_manager = ConfigManager()
    credentials = config_manager.get_api_credentials()
    
    if credentials['flag'] == '0':
        console.print("   ✓ [green]Live trading mode enabled[/green]")
    else:
        console.print("   ✗ [red]Still in demo mode![/red]")
        return
    
    # Step 2: Test REST API connection
    console.print("\n2. Testing REST API connection...")
    try:
        okx_client = OKXClient()
        
        # Get account balance
        balance = okx_client.get_balance()
        if balance:
            console.print("   ✓ [green]REST API connected successfully[/green]")
            
            # Display balance
            table = Table(title="Live Account Balance")
            table.add_column("Currency", style="cyan")
            table.add_column("Balance", style="yellow")
            
            for currency, amount in balance.items():
                if amount > 0:
                    table.add_row(currency, f"{amount:.8f}")
            
            console.print(table)
            
            # Calculate total value in USDT
            total_usdt = balance.get('USDT', 0)
            total_usdt += balance.get('USDC', 0) * 1.0  # Assume 1:1 with USDT
            if balance.get('BTC', 0) > 0:
                # Get BTC price
                btc_orderbook = okx_client.get_orderbook('BTC-USDT')
                if btc_orderbook:
                    btc_price = btc_orderbook.get_best_bid()
                    total_usdt += balance.get('BTC', 0) * btc_price
                    console.print(f"\n   BTC Price: ${btc_price:,.2f}")
            
            console.print(f"\n   [bold]Total Account Value: ${total_usdt:.2f} USDT[/bold]")
        else:
            console.print("   ✗ [red]Failed to get balance[/red]")
            return
    except Exception as e:
        console.print(f"   ✗ [red]REST API error: {e}[/red]")
        return
    
    # Step 3: Test market data for trading pairs
    console.print("\n3. Testing market data for arbitrage pairs...")
    pairs = ['BTC-USDT', 'BTC-USDC', 'USDC-USDT']
    
    table = Table(title="Live Market Data")
    table.add_column("Pair", style="cyan")
    table.add_column("Best Bid", style="green")
    table.add_column("Best Ask", style="red")
    table.add_column("Spread", style="yellow")
    
    for pair in pairs:
        orderbook = okx_client.get_orderbook(pair)
        if orderbook:
            bid = orderbook.get_best_bid()
            ask = orderbook.get_best_ask()
            spread = ask - bid
            spread_pct = (spread / bid) * 100
            table.add_row(
                pair,
                f"{bid:.8f}",
                f"{ask:.8f}",
                f"{spread_pct:.4f}%"
            )
        else:
            table.add_row(pair, "N/A", "N/A", "N/A")
    
    console.print(table)
    
    # Step 4: Test WebSocket connection
    console.print("\n4. Testing WebSocket connection...")
    controller = TradingController(config_manager, enable_rich_logging=False)
    controller.disable_trading("Test mode")
    
    await controller.start()
    console.print("   ✓ [green]WebSocket connected[/green]")
    
    # Wait for data
    console.print("\n5. Collecting real-time data (10 seconds)...")
    await asyncio.sleep(10)
    
    # Check WebSocket data
    console.print("\n6. Verifying WebSocket data:")
    has_all_data = True
    for pair in pairs:
        orderbook = controller.data_collector.get_orderbook(pair)
        if orderbook and orderbook.is_valid():
            age = time.time() - orderbook.timestamp
            console.print(f"   ✓ {pair}: Data age {age:.1f}s")
        else:
            console.print(f"   ✗ {pair}: No WebSocket data")
            has_all_data = False
    
    # Step 5: Test arbitrage calculation
    if has_all_data:
        console.print("\n7. Testing arbitrage calculation...")
        if hasattr(controller, 'arbitrage_engine'):
            analyses = getattr(controller.arbitrage_engine, 'recent_analyses', [])
            if analyses:
                console.print(f"   ✓ Found {len(analyses)} arbitrage analyses")
                
                # Show recent analyses
                table = Table(title="Recent Arbitrage Opportunities")
                table.add_column("Path", style="cyan")
                table.add_column("Profit Rate", style="yellow")
                table.add_column("Status", style="green")
                
                for analysis in analyses[-5:]:
                    path = analysis.get('path_name', 'Unknown')
                    rate = analysis.get('profit_rate', 0)
                    if rate == -1:
                        table.add_row(path, "ERROR", "[red]Invalid[/red]")
                    else:
                        color = "green" if rate > 0 else "red"
                        table.add_row(
                            path,
                            f"[{color}]{rate*100:+.4f}%[/{color}]",
                            "Valid"
                        )
                
                console.print(table)
            else:
                console.print("   ⚠️ No arbitrage analyses generated yet")
        else:
            console.print("   ⚠️ Arbitrage engine not initialized")
    
    # Stop controller
    await controller.stop()
    
    # Summary
    console.print("\n" + "="*50)
    console.print("[bold green]✅ LIVE CONNECTION TEST COMPLETED[/bold green]")
    console.print("\n[yellow]Summary:[/yellow]")
    console.print(f"  • Account Value: ${total_usdt:.2f}")
    console.print(f"  • Trading Mode: [red]LIVE[/red]")
    console.print(f"  • Trading Pairs: {', '.join(pairs)}")
    console.print(f"  • Min Trade Amount: $10")
    console.print("\n[bold yellow]⚠️ WARNING: You are now configured for LIVE trading![/bold yellow]")
    console.print("[dim]All trades will use REAL money. Please trade responsibly.[/dim]")

if __name__ == "__main__":
    asyncio.run(test_live_connection())