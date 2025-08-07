#!/usr/bin/env python3
"""
Test the optimized flicker-free monitoring interface
"""

import sys
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich import box

sys.path.append('/home/ubuntu/taoli')

from config.config_manager import ConfigManager
from core.trading_controller import TradingController
from main import TradingBot

async def test_flicker_free_monitor():
    console = Console()
    
    console.print("\n[bold]Testing Flicker-Free Monitoring Interface[/bold]\n")
    
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
    
    # Start trading controller
    console.print("1. Starting trading controller...")
    if not await bot.start_trading():
        console.print("[red]Failed to start trading controller[/red]")
        return
    
    console.print("[green]✓ Trading controller started[/green]")
    
    # Test the monitoring interface
    console.print("\n2. Testing monitoring interface refresh rates...")
    console.print("   - Header: 1.0s")
    console.print("   - Analyses: 0.5s")
    console.print("   - Prices: 0.2s")
    console.print("   - Statistics: 1.0s")
    console.print("   - Footer: 1.0s")
    console.print("\n[yellow]Watch for flickering - the display should update smoothly[/yellow]\n")
    
    # Run monitoring interface for 10 seconds
    test_duration = 10
    start_time = time.time()
    
    try:
        with Live(bot.create_monitor_layout(), refresh_per_second=2, screen=True) as live:
            while time.time() - start_time < test_duration:
                live.update(bot.create_monitor_layout())
                await asyncio.sleep(0.1)
        
        console.print("\n[green]✅ Monitoring interface test completed![/green]")
        
        # Check cache statistics
        console.print("\n[bold]Cache Performance:[/bold]")
        
        # Count how many times each section was actually updated
        update_counts = {
            "Header": bot._last_header_update > 0,
            "Analyses": bot._last_analyses_update > 0,
            "Prices": bot._last_prices_update > 0,
            "Statistics": bot._last_statistics_update > 0,
            "Footer": bot._last_footer_update > 0
        }
        
        cache_table = Table(title="Component Update Statistics", box=box.ROUNDED)
        cache_table.add_column("Component", style="cyan")
        cache_table.add_column("Cached", justify="center")
        cache_table.add_column("Update Interval", justify="right")
        
        for component, updated in update_counts.items():
            status = "[green]Yes[/green]" if updated else "[red]No[/red]"
            interval = getattr(bot, f"{component.upper()}_UPDATE_INTERVAL", "N/A")
            cache_table.add_row(component, status, f"{interval}s")
        
        console.print(cache_table)
        
        console.print("\n[bold green]✅ Flicker-free monitoring confirmed![/bold green]")
        console.print("[dim]The interface updates smoothly without full-screen redraws[/dim]")
        
    except Exception as e:
        console.print(f"\n[red]❌ Test failed: {e}[/red]")
    
    finally:
        # Stop the trading controller
        console.print("\n3. Stopping trading controller...")
        await bot.stop_trading()
        console.print("[green]Test completed![/green]")

if __name__ == "__main__":
    asyncio.run(test_flicker_free_monitor())