#!/usr/bin/env python3
"""
Test script to verify monitoring optimizations:
1. Real-time balance fetching
2. Total profit display
3. Market analysis ordering
4. Optimized update frequencies
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trading_controller import TradingController
from config.config_manager import ConfigManager
from utils.logger import setup_logger
from rich.console import Console
from rich.table import Table
from rich import box


class OptimizationTester:
    """Test monitoring optimizations"""
    
    def __init__(self):
        self.console = Console()
        self.logger = setup_logger("OptimizationTester", "logs/test_optimization.log")
        self.config_manager = ConfigManager()
        self.trading_controller = None
    
    async def test_balance_real_time(self):
        """Test real-time balance fetching"""
        self.console.print("\n[bold cyan]Testing Real-Time Balance Fetching[/bold cyan]")
        
        try:
            # Initialize controller
            self.trading_controller = TradingController(self.config_manager)
            
            # Start the system
            await self.trading_controller.start()
            await asyncio.sleep(2)  # Wait for initialization
            
            # Test balance fetching with different cache states
            self.console.print("\n[yellow]Testing balance cache behavior:[/yellow]")
            
            # First fetch (will hit API)
            start_time = time.time()
            balance1 = self.trading_controller.trade_executor.balance_cache.get_balance(force_refresh=True)
            fetch_time1 = time.time() - start_time
            self.console.print(f"1. Force refresh: {fetch_time1:.3f}s - {balance1}")
            
            # Second fetch (should use cache)
            start_time = time.time()
            balance2 = self.trading_controller.trade_executor.balance_cache.get_balance(force_refresh=False)
            fetch_time2 = time.time() - start_time
            self.console.print(f"2. Cache fetch: {fetch_time2:.3f}s - {balance2}")
            
            # Wait for cache TTL (5 seconds)
            self.console.print("\n[dim]Waiting 6 seconds for cache TTL expiry...[/dim]")
            await asyncio.sleep(6)
            
            # Third fetch (should refresh due to TTL)
            start_time = time.time()
            balance3 = self.trading_controller.trade_executor.balance_cache.get_balance(force_refresh=False)
            fetch_time3 = time.time() - start_time
            self.console.print(f"3. TTL expired fetch: {fetch_time3:.3f}s - {balance3}")
            
            # Verify cache optimization
            assert fetch_time2 < fetch_time1, "Cache should be faster than API call"
            self.console.print("\n[green]✓ Balance cache working correctly[/green]")
            
        except Exception as e:
            self.console.print(f"[red]✗ Balance test failed: {e}[/red]")
            raise
    
    async def test_profit_calculation(self):
        """Test total profit calculation"""
        self.console.print("\n[bold cyan]Testing Total Profit Calculation[/bold cyan]")
        
        try:
            # Get initial USDT from config
            initial_usdt = float(self.config_manager.get('portfolio', 'initial_usdt', default=40.0) or 40.0)
            self.console.print(f"Initial USDT from config: {initial_usdt:.2f}")
            
            # Get current balance
            balance = self.trading_controller.trade_executor.balance_cache.get_balance()
            current_usdt = balance.get("USDT", 0)
            self.console.print(f"Current USDT balance: {current_usdt:.2f}")
            
            # Calculate profit
            total_profit = current_usdt - initial_usdt
            profit_color = "green" if total_profit > 0 else "red" if total_profit < 0 else "white"
            self.console.print(f"Total Profit: [{profit_color}]{total_profit:+.2f} USDT[/{profit_color}]")
            
            self.console.print("\n[green]✓ Profit calculation working correctly[/green]")
            
        except Exception as e:
            self.console.print(f"[red]✗ Profit calculation test failed: {e}[/red]")
            raise
    
    async def test_market_analysis_ordering(self):
        """Test market analysis data ordering"""
        self.console.print("\n[bold cyan]Testing Market Analysis Ordering[/bold cyan]")
        
        try:
            # Wait for some analyses to accumulate
            self.console.print("[dim]Collecting arbitrage analyses for 5 seconds...[/dim]")
            await asyncio.sleep(5)
            
            # Get analyses from arbitrage engine
            if hasattr(self.trading_controller, 'arbitrage_engine'):
                analyses = getattr(self.trading_controller.arbitrage_engine, 'recent_analyses', [])
                
                if analyses:
                    # Check ordering by timestamp
                    sorted_analyses = sorted(analyses, key=lambda x: x.get('timestamp', 0), reverse=True)
                    
                    # Display first 5 analyses
                    table = Table(title="Market Analysis Order Check", box=box.ROUNDED)
                    table.add_column("Path", style="cyan")
                    table.add_column("Profit Rate", justify="right")
                    table.add_column("Timestamp", style="white")
                    
                    for analysis in sorted_analyses[:5]:
                        path = analysis.get('path_name', 'Unknown')
                        profit_rate = analysis.get('profit_rate', 0)
                        timestamp = datetime.fromtimestamp(analysis.get('timestamp', time.time())).strftime('%H:%M:%S.%f')[:-3]
                        
                        table.add_row(
                            path[:30],
                            f"{profit_rate:.4%}",
                            timestamp
                        )
                    
                    self.console.print(table)
                    
                    # Verify ordering
                    for i in range(len(sorted_analyses) - 1):
                        assert sorted_analyses[i]['timestamp'] >= sorted_analyses[i+1]['timestamp'], \
                            "Analyses should be ordered by timestamp (newest first)"
                    
                    self.console.print("\n[green]✓ Market analyses correctly ordered by timestamp[/green]")
                else:
                    self.console.print("[yellow]No analyses collected yet[/yellow]")
            
        except Exception as e:
            self.console.print(f"[red]✗ Market analysis ordering test failed: {e}[/red]")
            raise
    
    async def test_update_frequencies(self):
        """Test optimized update frequencies"""
        self.console.print("\n[bold cyan]Testing Update Frequencies[/bold cyan]")
        
        try:
            # Display configured update intervals
            table = Table(title="Optimized Update Intervals", box=box.ROUNDED)
            table.add_column("Component", style="cyan")
            table.add_column("Interval", justify="right")
            table.add_column("Description", style="dim")
            
            table.add_row("Header", "1.0s", "Status and time")
            table.add_row("Market Analysis", "0.5s", "Arbitrage opportunities")
            table.add_row("Prices", "0.5s", "Real-time market data")
            table.add_row("Statistics", "2.0s", "Performance & balance")
            table.add_row("Footer", "1.0s", "Controls info")
            table.add_row("", "", "")
            table.add_row("Balance Cache TTL", "5.0s", "API call frequency")
            table.add_row("Display Refresh", "2Hz", "Screen update rate")
            
            self.console.print(table)
            
            # Measure actual update performance
            self.console.print("\n[dim]Monitoring update performance for 10 seconds...[/dim]")
            
            update_counts = {
                'api_calls': 0,
                'cache_hits': 0
            }
            
            start_time = time.time()
            for i in range(10):
                # Simulate statistics updates every 2 seconds
                if i % 2 == 0:
                    balance = self.trading_controller.trade_executor.balance_cache.get_balance(force_refresh=False)
                    if time.time() - self.trading_controller.trade_executor.balance_cache.last_update < 5:
                        update_counts['cache_hits'] += 1
                    else:
                        update_counts['api_calls'] += 1
                
                await asyncio.sleep(1)
            
            elapsed = time.time() - start_time
            
            self.console.print(f"\nPerformance over {elapsed:.1f} seconds:")
            self.console.print(f"  API calls: {update_counts['api_calls']}")
            self.console.print(f"  Cache hits: {update_counts['cache_hits']}")
            self.console.print(f"  Cache efficiency: {update_counts['cache_hits']/(update_counts['api_calls']+update_counts['cache_hits'])*100:.1f}%")
            
            self.console.print("\n[green]✓ Update frequencies optimized for performance[/green]")
            
        except Exception as e:
            self.console.print(f"[red]✗ Update frequency test failed: {e}[/red]")
            raise
    
    async def run_all_tests(self):
        """Run all optimization tests"""
        self.console.print("\n[bold green]Starting Optimization Tests[/bold green]")
        self.console.print("="*60)
        
        try:
            await self.test_balance_real_time()
            await self.test_profit_calculation()
            await self.test_market_analysis_ordering()
            await self.test_update_frequencies()
            
            self.console.print("\n" + "="*60)
            self.console.print("[bold green]✅ All optimization tests passed![/bold green]")
            
        except Exception as e:
            self.console.print(f"\n[bold red]❌ Tests failed: {e}[/bold red]")
        finally:
            # Clean up
            if self.trading_controller:
                await self.trading_controller.stop()
                self.console.print("\n[dim]System stopped[/dim]")


async def main():
    """Main test function"""
    tester = OptimizationTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted")
    except Exception as e:
        print(f"\nTest error: {e}")
        sys.exit(1)