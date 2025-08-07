#!/usr/bin/env python3
"""
Test data accuracy after caching optimization fix
"""

import sys
import asyncio
import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

sys.path.append('/home/ubuntu/taoli')

from config.config_manager import ConfigManager
from core.trading_controller import TradingController
from main import TradingBot

async def test_data_accuracy():
    console = Console()
    
    console.print("\n[bold]Testing Data Accuracy After Caching Fix[/bold]\n")
    
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
    console.print(f"[cyan]Arbitrage pairs: {bot.arbitrage_pairs}[/cyan]")
    
    # Start trading controller
    console.print("\n1. Starting trading controller...")
    if not await bot.start_trading():
        console.print("[red]Failed to start trading controller[/red]")
        return
    
    console.print("[green]✓ Trading controller started[/green]")
    
    # Wait for data to stabilize
    console.print("\n2. Waiting for data to stabilize...")
    await asyncio.sleep(5)
    
    # Test 1: Check if orderbook data is available
    console.print("\n[bold]Test 1: Orderbook Data Availability[/bold]")
    orderbook_table = Table(title="Orderbook Status", box=box.ROUNDED)
    orderbook_table.add_column("Pair", style="cyan")
    orderbook_table.add_column("Has Data", justify="center")
    orderbook_table.add_column("Best Bid", justify="right")
    orderbook_table.add_column("Best Ask", justify="right")
    orderbook_table.add_column("Timestamp", justify="right")
    
    for pair in bot.arbitrage_pairs:
        orderbook = bot.trading_controller.data_collector.get_orderbook(pair)
        if orderbook and orderbook.is_valid():
            has_data = "[green]✓[/green]"
            bid = f"{orderbook.get_best_bid():.4f}"
            ask = f"{orderbook.get_best_ask():.4f}"
            age = f"{time.time() - orderbook.timestamp:.1f}s"
        else:
            has_data = "[red]✗[/red]"
            bid = "--"
            ask = "--"
            age = "--"
        
        orderbook_table.add_row(pair, has_data, bid, ask, age)
    
    console.print(orderbook_table)
    
    # Test 2: Check arbitrage analyses
    console.print("\n[bold]Test 2: Arbitrage Analysis Data[/bold]")
    
    if hasattr(bot.trading_controller, 'arbitrage_engine'):
        engine = bot.trading_controller.arbitrage_engine
        analyses = getattr(engine, 'recent_analyses', [])
        
        if analyses:
            analysis_table = Table(title="Recent Arbitrage Analyses", box=box.ROUNDED)
            analysis_table.add_column("Path", style="cyan")
            analysis_table.add_column("Profit Rate", justify="right")
            analysis_table.add_column("Status", justify="center")
            analysis_table.add_column("Age", justify="right")
            
            for analysis in analyses[-5:]:
                path = analysis.get('path_name', 'Unknown')
                profit_rate = analysis.get('profit_rate', 0)
                
                # Check for the -1 error value
                if profit_rate == -1:
                    rate_str = "[red]-100.000% (ERROR)[/red]"
                    status = "[red]Data Error[/red]"
                else:
                    profit_pct = profit_rate * 100
                    if profit_rate > 0:
                        rate_str = f"[green]+{profit_pct:.3f}%[/green]"
                        status = "[green]Valid[/green]"
                    else:
                        rate_str = f"[yellow]{profit_pct:.3f}%[/yellow]"
                        status = "[yellow]Valid[/yellow]"
                
                age = f"{time.time() - analysis.get('timestamp', time.time()):.1f}s"
                
                analysis_table.add_row(path, rate_str, status, age)
            
            console.print(analysis_table)
            
            # Count error analyses
            error_count = sum(1 for a in analyses if a.get('profit_rate', 0) == -1)
            valid_count = len(analyses) - error_count
            
            console.print(f"\n[bold]Analysis Summary:[/bold]")
            console.print(f"  Total analyses: {len(analyses)}")
            console.print(f"  Valid analyses: [green]{valid_count}[/green]")
            console.print(f"  Error analyses: [red]{error_count}[/red]")
            
            if error_count > 0:
                console.print("\n[yellow]⚠️ Some analyses show -100% error rate, indicating data fetch issues[/yellow]")
            else:
                console.print("\n[green]✅ All analyses show valid profit rates[/green]")
        else:
            console.print("[yellow]No analyses found yet[/yellow]")
    else:
        console.print("[red]Arbitrage engine not found[/red]")
    
    # Test 3: Monitor data updates for a few seconds
    console.print("\n[bold]Test 3: Monitoring Data Updates (5 seconds)[/bold]")
    
    start_time = time.time()
    update_count = 0
    prev_data = {}
    
    while time.time() - start_time < 5:
        # Check for data changes
        for pair in bot.arbitrage_pairs:
            orderbook = bot.trading_controller.data_collector.get_orderbook(pair)
            if orderbook:
                current_price = orderbook.get_best_bid()
                if pair not in prev_data or prev_data[pair] != current_price:
                    update_count += 1
                    prev_data[pair] = current_price
        
        await asyncio.sleep(0.2)
    
    console.print(f"  Data updates detected: {update_count}")
    console.print(f"  Updates per second: {update_count / 5:.1f}")
    
    if update_count > 0:
        console.print("[green]✅ Data is updating correctly[/green]")
    else:
        console.print("[red]❌ No data updates detected - possible data collection issue[/red]")
    
    # Stop the trading controller
    console.print("\n4. Stopping trading controller...")
    await bot.stop_trading()
    console.print("[green]Test completed![/green]")

if __name__ == "__main__":
    asyncio.run(test_data_accuracy())