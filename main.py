#!/usr/bin/env python3
"""
OKX Triangular Arbitrage Trading Bot - Main Entry Point

Main features:
1. System initialization and environment check
2. Start trading controller and data collection
3. Provide real-time monitoring interface
4. Graceful exit and error handling
"""

import asyncio
import sys
import os
import signal
import logging
import time
from datetime import datetime
from typing import Optional

# Ensure project directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trading_controller import TradingController, TradingStatus
from config.config_manager import ConfigManager
from utils.logger import setup_logger
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich import box
from rich.rule import Rule


class TradingBot:
    """OKX Triangular Arbitrage Trading Bot Main Class"""
    
    def __init__(self):
        """Initialize trading bot"""
        self.console = Console()
        self.logger = setup_logger("TradingBot", "logs/trading_bot.log")
        self.config_manager = ConfigManager()
        self.trading_controller: Optional[TradingController] = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self.all_analyses = []  # Store all arbitrage analyses
        self.key_prices = {}  # Store key trading pair prices
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}, preparing graceful exit...")
        self.shutdown_event.set()
    
    def show_welcome(self):
        """Display welcome screen"""
        welcome_text = """
[bold blue]OKX Triangular Arbitrage Trading Bot[/bold blue]

[bold]System Features:[/bold]
• Real-time data collection (WebSocket + REST API)
• Intelligent arbitrage opportunity detection
• Multi-layer risk management
• Automated trade execution
• Real-time monitoring dashboard
• Performance metrics tracking

[bold]Running Modes:[/bold]
• Auto Mode - Fully automated arbitrage trading
• Monitor Mode - Monitor only, no trading

[bold yellow]Tip: First-time users should use Monitor Mode to familiarize with the system[/bold yellow]
        """
        
        self.console.print(Panel(
            welcome_text,
            title="[bold green]System Startup[/bold green]",
            border_style="green",
            padding=(1, 2)
        ))
    
    async def check_environment(self) -> bool:
        """Check runtime environment"""
        self.console.print("\n[bold]Checking runtime environment...[/bold]")
        
        checks = []
        
        # Check configuration files
        try:
            api_key = self.config_manager.get('api', 'api_key')
            secret_key = self.config_manager.get('api', 'secret_key')
            passphrase = self.config_manager.get('api', 'passphrase')
            
            if all([api_key, secret_key, passphrase]):
                checks.append(("API Config", True, "Configured"))
            else:
                checks.append(("API Config", False, "Not configured"))
        except Exception as e:
            checks.append(("API Config", False, str(e)))
        
        # Check trading configuration
        try:
            trading_config = self.config_manager.get_trading_config()
            if trading_config:
                checks.append(("Trading Config", True, "Loaded"))
            else:
                checks.append(("Trading Config", False, "Empty config"))
        except Exception as e:
            checks.append(("Trading Config", False, str(e)))
        
        # Check log directory
        try:
            os.makedirs("logs", exist_ok=True)
            checks.append(("Log Directory", True, "Created"))
        except Exception as e:
            checks.append(("Log Directory", False, str(e)))
        
        # Display check results
        table = Table(title="Environment Check Results", box=box.ROUNDED)
        table.add_column("Check Item", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        all_passed = True
        for item, passed, detail in checks:
            status = "[green]✓[/green]" if passed else "[red]✗[/red]"
            table.add_row(item, status, detail)
            if not passed:
                all_passed = False
        
        self.console.print(table)
        
        if not all_passed:
            self.console.print("\n[red]Environment check failed, please check configuration and try again[/red]")
            return False
        
        self.console.print("\n[green]✅ Environment check passed[/green]")
        return True
    
    def select_mode(self) -> str:
        """Select running mode"""
        self.console.print("\n[bold]Select running mode:[/bold]")
        
        mode_table = Table(box=box.SIMPLE)
        mode_table.add_column("Option", style="cyan")
        mode_table.add_column("Mode")
        mode_table.add_column("Description", style="dim")
        
        mode_table.add_row("1", "Auto Mode", "Fully automated arbitrage trading")
        mode_table.add_row("2", "Monitor Mode", "Monitor opportunities only, no trading")
        
        self.console.print(mode_table)
        
        choice = Prompt.ask(
            "\n[bold cyan]Please select mode[/bold cyan]",
            choices=["1", "2"],
            default="2"
        )
        
        mode_map = {
            "1": "auto",
            "2": "monitor"
        }
        
        return mode_map[choice]
    
    async def initialize_system(self, mode: str) -> bool:
        """Initialize system"""
        self.console.print(f"\n[bold]Initializing system (mode: {mode})...[/bold]")
        
        try:
            # Create trading controller
            self.trading_controller = TradingController(
                config_manager=self.config_manager,
                enable_rich_logging=True
            )
            
            # Configure based on mode
            if mode == "monitor":
                # Monitor mode: disable trading
                self.trading_controller.disable_trading("Monitor mode")
                self.console.print("[yellow]Trading disabled (Monitor mode)[/yellow]")
            
            # Set up callback to capture all analyses
            if hasattr(self.trading_controller, 'arbitrage_engine'):
                engine = self.trading_controller.arbitrage_engine
                if not hasattr(engine, 'recent_analyses'):
                    engine.recent_analyses = []
                
                # Wrap the calculate methods to capture ALL analysis results
                original_calc_steps = engine.calculate_arbitrage_from_steps
                original_calc = engine.calculate_arbitrage
                
                def wrapped_calculate_arbitrage_from_steps(path_name, path_config, validated_orderbooks=None):
                    # Call original method
                    opportunity = original_calc_steps(path_name, path_config, validated_orderbooks)
                    
                    # Extract path info for storage
                    route = path_config.get('route', '')
                    if route:
                        path_assets = [asset.strip() for asset in route.split('->')]
                    else:
                        steps = path_config.get('steps', [])
                        path_assets = engine._extract_path_from_steps(steps) if hasattr(engine, '_extract_path_from_steps') else []
                    
                    # Calculate profit rate even if no opportunity
                    if not opportunity and len(path_assets) >= 3:
                        # Try to calculate the profit rate anyway
                        try:
                            trade_steps = []
                            for step in path_config.get('steps', []):
                                pair = step.get('pair')
                                action = step.get('action')
                                if pair and validated_orderbooks and pair in validated_orderbooks:
                                    trade_steps.append({
                                        'pair': pair,
                                        'action': action,
                                        'order_book': validated_orderbooks[pair]
                                    })
                            
                            if trade_steps:
                                final_amount, profit_rate = engine.calculate_path_profit_from_steps(trade_steps, engine.min_trade_amount)
                            else:
                                profit_rate = 0.0
                        except:
                            profit_rate = 0.0
                    else:
                        profit_rate = opportunity.profit_rate if opportunity else 0.0
                    
                    # Store the analysis result
                    analysis = {
                        'path_name': path_name,
                        'profit_rate': profit_rate,
                        'timestamp': time.time(),
                        'is_profitable': profit_rate > engine.min_profit_threshold
                    }
                    engine.recent_analyses.append(analysis)
                    
                    # Keep only recent analyses (last 200)
                    engine.recent_analyses = engine.recent_analyses[-200:]
                    
                    return opportunity
                
                def wrapped_calculate_arbitrage(path):
                    # Call original method
                    opportunity = original_calc(path)
                    
                    # Calculate profit rate even if no opportunity
                    if not opportunity:
                        try:
                            final_amount, profit_rate = engine.calculate_path_profit(path, engine.min_trade_amount)
                        except:
                            profit_rate = 0.0
                    else:
                        profit_rate = opportunity.profit_rate
                    
                    # Store the analysis result
                    path_name = ' -> '.join(path)
                    analysis = {
                        'path_name': path_name,
                        'profit_rate': profit_rate,
                        'timestamp': time.time(),
                        'is_profitable': profit_rate > engine.min_profit_threshold
                    }
                    engine.recent_analyses.append(analysis)
                    
                    # Keep only recent analyses (last 200)
                    engine.recent_analyses = engine.recent_analyses[-200:]
                    
                    return opportunity
                
                engine.calculate_arbitrage_from_steps = wrapped_calculate_arbitrage_from_steps
                engine.calculate_arbitrage = wrapped_calculate_arbitrage
            
            self.console.print("[green]✅ System initialization completed[/green]")
            return True
            
        except Exception as e:
            self.logger.error(f"System initialization failed: {e}")
            self.console.print(f"[red]❌ System initialization failed: {e}[/red]")
            return False
    
    async def start_trading(self):
        """Start trading system"""
        self.console.print("\n[bold]Starting trading system...[/bold]")
        
        try:
            # Start trading controller
            success = await self.trading_controller.start()
            
            if not success:
                raise Exception("Trading controller failed to start")
            
            self.is_running = True
            self.console.print("[green]✅ Trading system started successfully[/green]")
            
            # Wait for initial data
            self.console.print("[yellow]Waiting for data to stabilize...[/yellow]")
            await asyncio.sleep(3)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start trading system: {e}")
            self.console.print(f"[red]❌ Start failed: {e}[/red]")
            return False
    
    def create_monitor_layout(self) -> Layout:
        """Create monitoring interface layout"""
        layout = Layout()
        
        # Split layout
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4)
        )
        
        # Split main into three columns for better organization
        layout["main"].split_row(
            Layout(name="left", ratio=2),  # Wider for analyses
            Layout(name="middle", ratio=1),  # Prices
            Layout(name="right", ratio=1)   # Stats
        )
        
        # Update each section
        self._update_header(layout["header"])
        self._update_all_analyses(layout["left"])
        self._update_prices(layout["middle"])
        self._update_statistics(layout["right"])
        self._update_footer(layout["footer"])
        
        return layout
    
    def _update_header(self, layout: Layout):
        """Update header information"""
        try:
            status = self.trading_controller.get_status() if self.trading_controller else {}
            status_text = status.get('status', 'unknown')
            
            # Status color mapping
            status_colors = {
                'running': 'green',
                'stopped': 'red',
                'starting': 'yellow',
                'stopping': 'yellow',
                'error': 'red'
            }
            color = status_colors.get(status_text, 'white')
            
            # Get current mode by checking if trading is enabled in risk manager
            mode = "Auto"
            mode_color = "green"
            
            if self.trading_controller and hasattr(self.trading_controller, 'risk_manager'):
                try:
                    if hasattr(self.trading_controller.risk_manager, 'trading_enabled'):
                        if not self.trading_controller.risk_manager.trading_enabled:
                            mode = "Monitor"
                            mode_color = "yellow"
                except Exception as e:
                    self.logger.debug(f"Error checking trading mode: {e}")
            
            header_content = f"""
[bold blue]🎯 OKX Triangular Arbitrage Trading System[/bold blue]
[bold]Time:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [bold]Status:[/bold] [{color}]{status_text}[/{color}] | [bold]Mode:[/bold] [{mode_color}]{mode}[/{mode_color}] | [bold]Risk:[/bold] {status.get('risk_level', 'N/A')}
            """.strip()
            
            layout.update(Panel(header_content, style="bold blue", box=box.DOUBLE))
        except Exception as e:
            # Fallback header in case of error
            header_content = f"[bold blue]🎯 OKX Triangular Arbitrage Trading System[/bold blue]\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            layout.update(Panel(header_content, style="bold blue"))
    
    def _update_all_analyses(self, layout: Layout):
        """Update all arbitrage analysis results"""
        try:
            if not self.trading_controller:
                layout.update(Panel("[dim]No data[/dim]", title="Arbitrage Analysis"))
                return
            
            # Create tables for different profit categories
            profitable_table = Table(title="🎯 Profitable Opportunities", box=box.ROUNDED, border_style="green")
            profitable_table.add_column("Path", style="cyan")
            profitable_table.add_column("Profit Rate", style="bright_green", justify="right")
            profitable_table.add_column("Time", style="white")
            
            unprofitable_table = Table(title="📊 All Market Analyses", box=box.SIMPLE)
            unprofitable_table.add_column("Path", style="dim cyan")
            unprofitable_table.add_column("Profit Rate", justify="right")
            unprofitable_table.add_column("Time", style="dim white")
            
            # Get recent analyses from arbitrage engine
            if hasattr(self.trading_controller, 'arbitrage_engine') and self.trading_controller.arbitrage_engine:
                analyses = getattr(self.trading_controller.arbitrage_engine, 'recent_analyses', [])
                
                # Sort by profit rate
                sorted_analyses = sorted(analyses, key=lambda x: x.get('profit_rate', 0), reverse=True)
                
                profitable_count = 0
                for analysis in sorted_analyses[-20:]:  # Show last 20 analyses
                    path = analysis.get('path_name', 'Unknown')
                    profit_rate = analysis.get('profit_rate', 0)
                    timestamp = datetime.fromtimestamp(analysis.get('timestamp', time.time())).strftime('%H:%M:%S')
                    
                    if profit_rate > 0.001:  # 0.1% threshold
                        profitable_table.add_row(
                            path[:30],
                            f"{profit_rate:.3%}",
                            timestamp
                        )
                        profitable_count += 1
                    else:
                        # Color code based on profit
                        if profit_rate > 0:
                            rate_str = f"[yellow]{profit_rate:.3%}[/yellow]"
                        elif profit_rate == 0:
                            rate_str = f"[dim]{profit_rate:.3%}[/dim]"
                        else:
                            rate_str = f"[red]{profit_rate:.3%}[/red]"
                        
                        unprofitable_table.add_row(
                            path[:30],
                            rate_str,
                            timestamp
                        )
            
            # Add empty row messages if needed
            if profitable_table.row_count == 0:
                profitable_table.add_row("[dim]No profitable opportunities[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")
            
            if unprofitable_table.row_count == 0:
                unprofitable_table.add_row("[dim]Analyzing market...[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")
            
            # Recent trades table
            trades_table = Table(title="📈 Recent Executed Trades", box=box.SIMPLE)
            trades_table.add_column("Time", style="cyan")
            trades_table.add_column("Path", style="white")
            trades_table.add_column("Result", justify="right")
            
            if self.trading_controller.trade_logger:
                recent_trades = self.trading_controller.trade_logger.recent_trades
                for trade in recent_trades[-5:]:
                    trade_time = datetime.fromtimestamp(trade.timestamp).strftime('%H:%M:%S')
                    if trade.success:
                        result = f"[green]+{trade.profit:.3f} ({trade.profit_rate:.2%})[/green]"
                    else:
                        result = f"[red]Failed[/red]"
                    
                    trades_table.add_row(
                        trade_time,
                        trade.path[:25],
                        result
                    )
            
            if trades_table.row_count == 0:
                trades_table.add_row("[dim]No trades executed[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")
            
            # Combine tables
            combined = Table.grid(padding=1)
            combined.add_column()
            combined.add_row(profitable_table)
            combined.add_row(unprofitable_table)
            combined.add_row(trades_table)
            
            layout.update(Panel(combined, title="🔍 Market Analysis", border_style="blue"))
        except Exception as e:
            self.logger.error(f"Error updating analyses: {e}")
            layout.update(Panel("[red]Error loading analysis data[/red]", title="Market Analysis"))
    
    def _update_prices(self, layout: Layout):
        """Update real-time price information"""
        try:
            if not self.trading_controller or not self.trading_controller.data_collector:
                layout.update(Panel("[dim]No price data[/dim]", title="Market Prices"))
                return
            
            price_table = Table(title="💹 Real-Time Prices", box=box.ROUNDED)
            price_table.add_column("Pair", style="cyan")
            price_table.add_column("Bid", style="green", justify="right")
            price_table.add_column("Ask", style="red", justify="right")
            price_table.add_column("Spread", style="yellow", justify="right")
            
            # Key trading pairs to monitor
            key_pairs = ['BTC-USDT', 'ETH-USDT', 'BTC-USDC', 'ETH-USDC', 'USDT-USDC']
            
            for pair in key_pairs:
                orderbook = self.trading_controller.data_collector.get_orderbook(pair)
                if orderbook and orderbook.is_valid():
                    bid = orderbook.get_best_bid()
                    ask = orderbook.get_best_ask()
                    spread = orderbook.get_spread()
                    spread_pct = (spread / ask * 100) if ask > 0 else 0
                    
                    # Format prices based on pair
                    if 'BTC' in pair:
                        bid_str = f"{bid:,.2f}"
                        ask_str = f"{ask:,.2f}"
                    elif 'ETH' in pair:
                        bid_str = f"{bid:,.2f}"
                        ask_str = f"{ask:,.2f}"
                    else:
                        bid_str = f"{bid:.4f}"
                        ask_str = f"{ask:.4f}"
                    
                    price_table.add_row(
                        pair,
                        bid_str,
                        ask_str,
                        f"{spread_pct:.3f}%"
                    )
                else:
                    price_table.add_row(
                        pair,
                        "[dim]--[/dim]",
                        "[dim]--[/dim]",
                        "[dim]--[/dim]"
                    )
            
            # Market summary
            summary_table = Table(box=box.SIMPLE, show_header=False)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value", style="white", justify="right")
            
            # Calculate average spreads
            total_spread = 0
            valid_spreads = 0
            
            for pair in key_pairs:
                orderbook = self.trading_controller.data_collector.get_orderbook(pair)
                if orderbook and orderbook.is_valid():
                    spread_pct = (orderbook.get_spread() / orderbook.get_best_ask() * 100)
                    total_spread += spread_pct
                    valid_spreads += 1
            
            avg_spread = total_spread / valid_spreads if valid_spreads > 0 else 0
            
            summary_table.add_row("Avg Spread", f"{avg_spread:.3f}%")
            summary_table.add_row("Active Pairs", f"{valid_spreads}/{len(key_pairs)}")
            summary_table.add_row("Update", datetime.now().strftime('%H:%M:%S'))
            
            # Combine tables
            combined = Table.grid(padding=1)
            combined.add_column()
            combined.add_row(price_table)
            combined.add_row(Rule(style="dim"))
            combined.add_row(summary_table)
        
            # Color border based on market conditions
            border_color = "green" if avg_spread < 0.1 else "yellow" if avg_spread < 0.2 else "red"
            
            layout.update(Panel(combined, title="📊 Market Data", border_style=border_color))
        except Exception as e:
            self.logger.error(f"Error updating prices: {e}")
            layout.update(Panel("[red]Error loading price data[/red]", title="Market Prices"))
    
    def _update_statistics(self, layout: Layout):
        """Update statistics information"""
        try:
            if not self.trading_controller:
                layout.update(Panel("[dim]No data[/dim]", title="Statistics"))
                return
            
            stats = self.trading_controller.get_stats()
            
            # Create a visually appealing statistics panel
            stats_table = Table(title="📊 Trading Performance", box=box.ROUNDED)
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="white", justify="right")
            
            # Runtime
            runtime = stats.get('runtime_seconds', 0)
            hours = int(runtime // 3600)
            minutes = int((runtime % 3600) // 60)
            runtime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m {int(runtime % 60)}s"
            
            # Add statistics with color coding
            stats_table.add_row("Runtime", runtime_str)
            
            opportunities = stats.get('total_opportunities', 0)
            opp_color = "green" if opportunities > 0 else "dim"
            stats_table.add_row("Opportunities", f"[{opp_color}]{opportunities}[/{opp_color}]")
            
            executed = stats.get('executed_trades', 0)
            successful = stats.get('successful_trades', 0)
            
            stats_table.add_row("Trades", f"{executed} / {successful} ✓")
            
            success_rate = stats.get('success_rate', 0)
            rate_color = "green" if success_rate > 0.7 else "yellow" if success_rate > 0.5 else "red"
            stats_table.add_row("Success Rate", f"[{rate_color}]{success_rate:.1%}[/{rate_color}]")
            
            net_profit = stats.get('net_profit', 0)
            profit_color = "bright_green" if net_profit > 0 else "red" if net_profit < 0 else "white"
            stats_table.add_row("Net Profit", f"[{profit_color}]{net_profit:+.6f}[/{profit_color}]")
            
            # Risk statistics
            risk_table = Table(title="⚠️ Risk Management", box=box.SIMPLE)
            risk_table.add_column("Metric", style="cyan")
            risk_table.add_column("Value", style="white", justify="right")
            
            risk_stats = self.trading_controller.get_risk_stats()
            risk_level = risk_stats.get('risk_level', 'N/A')
            risk_color = "green" if risk_level == "LOW" else "yellow" if risk_level == "MEDIUM" else "red"
            risk_table.add_row("Risk Level", f"[{risk_color}]{risk_level}[/{risk_color}]")
            risk_table.add_row("Rejected", str(risk_stats.get('rejected_opportunities', 0)))
            
            # Balance summary
            balance_table = Table(title="💰 Account Balance", box=box.SIMPLE)
            balance_table.add_column("Asset", style="cyan")
            balance_table.add_column("Amount", style="white", justify="right")
            
            if self.trading_controller.trade_executor:
                balances = self.trading_controller.trade_executor.balance_cache.get_balance()
                usdt_balance = balances.get("USDT", 0)
                usdc_balance = balances.get("USDC", 0)
                btc_balance = balances.get("BTC", 0)
                
                balance_table.add_row("USDT", f"{usdt_balance:,.2f}")
                balance_table.add_row("USDC", f"{usdc_balance:,.2f}")
                balance_table.add_row("BTC", f"{btc_balance:.6f}")
            
            # Combine all tables
            combined = Table.grid(padding=1)
            combined.add_column()
            combined.add_row(stats_table)
            combined.add_row(risk_table)
            combined.add_row(balance_table)
        
            # Dynamic border color based on performance
            border_color = "green" if net_profit > 0 else "yellow" if net_profit == 0 else "red"
            layout.update(Panel(combined, title="📈 Performance", border_style=border_color))
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
            layout.update(Panel("[red]Error loading statistics[/red]", title="Performance"))
    
    def _update_footer(self, layout: Layout):
        """Update footer control information"""
        # Get system metrics
        if self.trading_controller and hasattr(self.trading_controller, 'arbitrage_engine'):
            engine = self.trading_controller.arbitrage_engine
            analyses_count = len(getattr(engine, 'recent_analyses', []))
            check_interval = getattr(engine, 'check_interval', 1.0)
            checks_per_sec = 1.0 / check_interval if check_interval > 0 else 0
        else:
            analyses_count = 0
            checks_per_sec = 0
        
        footer_content = f"""
[bold]Controls:[/bold] [cyan]Ctrl+C[/cyan] to exit safely | [bold]Analysis Rate:[/bold] {checks_per_sec:.1f}/sec | [bold]Total Analyses:[/bold] {analyses_count}
[dim]System is actively analyzing all triangular arbitrage paths in real-time[/dim]
        """.strip()
        
        layout.update(Panel(footer_content, style="bold yellow", box=box.DOUBLE_EDGE))
    
    async def run_monitor_loop(self):
        """Run monitoring loop"""
        self.console.print("\n[bold]Starting real-time monitoring interface...[/bold]")
        self.console.print("[dim]Press Q to quit, H for help[/dim]\n")
        
        try:
            with Live(self.create_monitor_layout(), refresh_per_second=2, screen=True) as live:
                while self.is_running and not self.shutdown_event.is_set():
                    # Update display
                    live.update(self.create_monitor_layout())
                    
                    # Check for keyboard input (non-blocking)
                    # Note: This is simplified, actual applications may need more complex input handling
                    await asyncio.sleep(0.5)
                    
        except KeyboardInterrupt:
            self.logger.info("User interrupted monitoring interface")
    
    async def stop_trading(self):
        """Stop trading system"""
        self.console.print("\n[bold]Stopping trading system...[/bold]")
        
        try:
            if self.trading_controller:
                success = await self.trading_controller.stop()
                
                if success:
                    self.console.print("[green]✅ Trading system stopped safely[/green]")
                    
                    # Show final statistics
                    self.show_final_statistics()
                else:
                    self.console.print("[yellow]⚠️ Warning while stopping trading system[/yellow]")
            
            self.is_running = False
            
        except Exception as e:
            self.logger.error(f"Failed to stop trading system: {e}")
            self.console.print(f"[red]❌ Stop failed: {e}[/red]")
    
    def show_final_statistics(self):
        """Display final statistics"""
        if not self.trading_controller:
            return
        
        stats = self.trading_controller.get_stats()
        
        self.console.print("\n" + "="*60)
        self.console.print("[bold]Final Statistics Report[/bold]")
        self.console.print("="*60)
        
        # Create statistics table
        table = Table(box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white", justify="right")
        
        # Runtime statistics
        runtime = stats.get('runtime_seconds', 0)
        table.add_row("Total Runtime", f"{runtime/60:.1f} minutes")
        table.add_row("Arbitrage Opportunities Found", f"{stats.get('total_opportunities', 0)}")
        table.add_row("Trades Executed", f"{stats.get('executed_trades', 0)}")
        table.add_row("Successful Trades", f"{stats.get('successful_trades', 0)}")
        table.add_row("Failed Trades", f"{stats.get('failed_trades', 0)}")
        table.add_row("Success Rate", f"{stats.get('success_rate', 0):.2%}")
        table.add_row("", "")  # Empty row
        
        # Profit statistics
        table.add_row("Total Profit", f"{stats.get('total_profit', 0):.6f}")
        table.add_row("Total Loss", f"{stats.get('total_loss', 0):.6f}")
        table.add_row("Net Profit", f"{stats.get('net_profit', 0):.6f}")
        
        self.console.print(table)
        self.console.print("="*60)
    
    async def run(self):
        """Main run function"""
        try:
            # Show welcome screen
            self.show_welcome()
            
            # Check environment
            if not await self.check_environment():
                return
            
            # Select running mode
            mode = self.select_mode()
            
            # Initialize system
            if not await self.initialize_system(mode):
                return
            
            # Confirm startup
            if not Confirm.ask("\n[bold cyan]Start trading system?[/bold cyan]", default=True):
                self.console.print("[yellow]Startup cancelled[/yellow]")
                return
            
            # Start trading
            if not await self.start_trading():
                return
            
            # Run monitoring loop
            await self.run_monitor_loop()
            
        except Exception as e:
            self.logger.error(f"System runtime error: {e}")
            self.console.print(f"\n[red]❌ System error: {e}[/red]")
            
        finally:
            # Ensure safe system exit
            await self.stop_trading()
            self.console.print("\n[bold green]Thank you for using OKX Triangular Arbitrage Trading Bot![/bold green]")


async def main():
    """Main entry point"""
    bot = TradingBot()
    await bot.run()


if __name__ == "__main__":
    # Run main program
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSystem exited")
    except Exception as e:
        print(f"\nSystem error: {e}")
        sys.exit(1)