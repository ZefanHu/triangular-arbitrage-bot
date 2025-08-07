#!/usr/bin/env python3
"""
Test script to verify that the monitoring interface correctly displays arbitrage analyses
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
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from core.trading_controller import TradingController

async def test_monitoring_display():
    console = Console()
    
    # Initialize components
    config_manager = ConfigManager()
    trading_controller = TradingController(config_manager, enable_rich_logging=False)
    
    console.print("\n[bold]Starting test of monitoring interface analysis display...[/bold]\n")
    
    # Start the system
    console.print("1. Starting trading controller...")
    await trading_controller.start()
    await asyncio.sleep(3)
    
    # Disable trading (monitor mode)
    trading_controller.disable_trading("Monitor mode test")
    console.print("[yellow]Trading disabled (Monitor mode)[/yellow]\n")
    
    # Wait for a few cycles to collect data
    console.print("2. Waiting for arbitrage analyses to be collected...")
    await asyncio.sleep(5)
    
    # Check if we have analyses
    if hasattr(trading_controller, 'arbitrage_engine'):
        engine = trading_controller.arbitrage_engine
        analyses_count = len(engine.recent_analyses) if hasattr(engine, 'recent_analyses') else 0
        console.print(f"\n[green]✓ Found {analyses_count} analyses in the engine[/green]\n")
        
        if analyses_count > 0:
            # Create the same table structure as main.py
            analysis_table = Table(title="🔍 Real-Time Arbitrage Analysis", box=box.ROUNDED, border_style="cyan")
            analysis_table.add_column("Path", style="cyan")
            analysis_table.add_column("Expected Profit", justify="right")
            analysis_table.add_column("Profit Rate", justify="right")
            analysis_table.add_column("Status", justify="center")
            analysis_table.add_column("Time", style="white")
            
            # Sort by profit rate (highest first)
            sorted_analyses = sorted(engine.recent_analyses, key=lambda x: x.get('profit_rate', 0), reverse=True)
            
            # Display analyses with color coding
            for analysis in sorted_analyses[-10:]:
                path = analysis.get('path_name', 'Unknown')
                profit_rate = analysis.get('profit_rate', 0)
                profit_pct = profit_rate * 100
                timestamp = datetime.fromtimestamp(analysis.get('timestamp', time.time())).strftime('%H:%M:%S')
                
                # Determine color and status based on profit rate
                if profit_rate > 0.003:  # >0.3% - Strong profit
                    profit_str = f"[bright_green]+{profit_pct:.3f}%[/bright_green]"
                    rate_str = f"[bright_green]{profit_rate:.4%}[/bright_green]"
                    status = "✅ [bright_green]High Profit[/bright_green]"
                elif profit_rate > 0.001:  # 0.1% to 0.3% - Moderate profit
                    profit_str = f"[green]+{profit_pct:.3f}%[/green]"
                    rate_str = f"[green]{profit_rate:.4%}[/green]"
                    status = "✅ [green]Profitable[/green]"
                elif profit_rate > 0:  # 0% to 0.1% - Minimal profit
                    profit_str = f"[yellow]+{profit_pct:.3f}%[/yellow]"
                    rate_str = f"[yellow]{profit_rate:.4%}[/yellow]"
                    status = "⚠️ [yellow]Low Profit[/yellow]"
                elif profit_rate > -0.001:  # -0.1% to 0% - Near break-even
                    profit_str = f"[dim]{profit_pct:+.3f}%[/dim]"
                    rate_str = f"[dim]{profit_rate:.4%}[/dim]"
                    status = "⚖️ [dim]Break-even[/dim]"
                elif profit_rate > -0.003:  # -0.3% to -0.1% - Small loss
                    profit_str = f"[orange3]{profit_pct:.3f}%[/orange3]"
                    rate_str = f"[orange3]{profit_rate:.4%}[/orange3]"
                    status = "⚠️ [orange3]Small Loss[/orange3]"
                else:  # < -0.3% - Significant loss
                    profit_str = f"[red]{profit_pct:.3f}%[/red]"
                    rate_str = f"[red]{profit_rate:.4%}[/red]"
                    status = "❌ [red]Loss[/red]"
                
                analysis_table.add_row(
                    path[:25],
                    profit_str,
                    rate_str,
                    status,
                    timestamp
                )
            
            console.print(analysis_table)
            console.print("\n[bold green]✅ SUCCESS: Arbitrage analyses are being displayed correctly![/bold green]")
        else:
            console.print("[yellow]No analyses found yet. The system may need more time to collect data.[/yellow]")
    else:
        console.print("[red]❌ Error: Arbitrage engine not found in trading controller[/red]")
    
    # Stop the system
    console.print("\n3. Stopping trading controller...")
    await trading_controller.stop()
    console.print("[green]Test completed![/green]")

if __name__ == "__main__":
    asyncio.run(test_monitoring_display())