#!/usr/bin/env python3
"""
Final test of the monitoring interface with corrected trading pairs
"""

import sys
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.live import Live

sys.path.append('/home/ubuntu/taoli')

from config.config_manager import ConfigManager
from core.trading_controller import TradingController
from main import TradingBot

async def test_final_fix():
    console = Console()
    
    console.print("\n[bold green]Final Test: Monitoring Interface with Correct Trading Pairs[/bold green]\n")
    
    # Create trading bot
    bot = TradingBot()
    
    # Initialize configuration
    if not await bot.check_environment():
        console.print("[red]Environment check failed[/red]")
        return
    
    # Initialize system in monitor mode
    if not await bot.initialize_system("monitor"):
        console.print("[red]System initialization failed[/red]")
        return
    
    # Extract arbitrage pairs
    bot._extract_arbitrage_pairs()
    console.print(f"[cyan]Configured arbitrage pairs: {bot.arbitrage_pairs}[/cyan]")
    
    # Start trading controller
    console.print("\n1. Starting trading controller...")
    if not await bot.start_trading():
        console.print("[red]Failed to start trading controller[/red]")
        return
    
    console.print("[green]✓ Trading controller started[/green]")
    
    # Wait for data to stabilize
    console.print("\n2. Waiting for data collection to stabilize...")
    await asyncio.sleep(5)
    
    # Test monitoring interface for 15 seconds
    console.print("\n3. Testing monitoring interface display...")
    console.print("[yellow]The interface should show:[/yellow]")
    console.print("  - Real profit rates (not -100%)")
    console.print("  - Correct trading pairs (BTC-USDT, ETH-USDT, ETH-BTC)")
    console.print("  - Smooth updates without flicker")
    console.print("\n[dim]Running for 15 seconds...[/dim]\n")
    
    test_duration = 15
    start_time = time.time()
    
    try:
        with Live(bot.create_monitor_layout(), refresh_per_second=2, screen=True) as live:
            while time.time() - start_time < test_duration:
                live.update(bot.create_monitor_layout())
                await asyncio.sleep(0.1)
        
        console.print("\n[green]✅ Monitoring interface test completed![/green]")
        
        # Check final results
        if hasattr(bot.trading_controller, 'arbitrage_engine'):
            engine = bot.trading_controller.arbitrage_engine
            analyses = getattr(engine, 'recent_analyses', [])
            
            if analyses:
                # Count valid vs error analyses
                error_count = sum(1 for a in analyses if a.get('profit_rate', 0) == -1)
                valid_count = len(analyses) - error_count
                
                console.print(f"\n[bold]Final Analysis Summary:[/bold]")
                console.print(f"  Total analyses: {len(analyses)}")
                console.print(f"  Valid analyses: [green]{valid_count}[/green]")
                console.print(f"  Error analyses: [red]{error_count}[/red]")
                
                if valid_count > error_count:
                    console.print("\n[bold green]✅ SUCCESS: Data is displaying correctly![/bold green]")
                    console.print("[green]The arbitrage analyses show valid profit rates.[/green]")
                else:
                    console.print("\n[yellow]⚠️ Some issues remain with data collection[/yellow]")
            else:
                console.print("\n[yellow]No analyses generated yet[/yellow]")
        
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
    
    finally:
        # Stop the trading controller
        console.print("\n4. Stopping trading controller...")
        await bot.stop_trading()
        console.print("[green]Test completed![/green]")

if __name__ == "__main__":
    asyncio.run(test_final_fix())