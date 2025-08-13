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
import time
import hashlib
import json
from datetime import datetime
from typing import Optional, Any

# Ensure project directory is in Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.trading_controller import TradingController
from models.trade import SystemStatus
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
        self.config_manager = ConfigManager()
        # 从配置文件读取日志路径
        system_config = self.config_manager.get_system_config()
        log_file = system_config.get('system_log_file', 'logs/system_runtime.log')
        self.logger = setup_logger("TradingBot", log_file)
        self.trading_controller: Optional[TradingController] = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()
        self.all_analyses = []  # Store all arbitrage analyses
        self.key_prices = {}  # Store key trading pair prices
        self.arbitrage_pairs = set()  # Will hold trading pairs from arbitrage paths
        
        # Cache for rendered components to reduce flicker
        self._cached_header = None
        self._cached_analyses = None
        self._cached_prices = None
        self._cached_statistics = None
        self._cached_footer = None
        
        # Last update timestamps for each section
        self._last_header_update = 0
        self._last_analyses_update = 0
        self._last_prices_update = 0
        self._last_statistics_update = 0
        self._last_footer_update = 0
        
        # Previous data hashes for change detection
        self._prev_analyses_hash = None
        self._prev_prices_hash = None
        self._prev_stats_hash = None
        
        # Update intervals (in seconds) - optimized for performance and real-time data
        self.HEADER_UPDATE_INTERVAL = 1.0  # Header updates every 1 second
        self.ANALYSES_UPDATE_INTERVAL = 0.5  # Analyses update every 500ms
        self.PRICES_UPDATE_INTERVAL = 0.5  # Prices update every 500ms (reduced from 200ms to reduce load)
        self.STATISTICS_UPDATE_INTERVAL = 2.0  # Stats update every 2 seconds (balance API calls)
        self.FOOTER_UPDATE_INTERVAL = 1.0  # Footer updates every 1 second
        
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
            
            # Ensure the arbitrage engine has the recent_analyses list
            # (This is now handled directly in the ArbitrageEngine class)
            if hasattr(self.trading_controller, 'arbitrage_engine'):
                engine = self.trading_controller.arbitrage_engine
                # The recent_analyses list is now created in ArbitrageEngine.__init__
                self.logger.info("Arbitrage engine ready with analysis tracking")
            
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
        """Create monitoring interface layout with intelligent caching"""
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
        
        current_time = time.time()
        
        # Update header with caching (1 second interval)
        if self._cached_header is None or (current_time - self._last_header_update) >= self.HEADER_UPDATE_INTERVAL:
            self._update_header(layout["header"])
            self._last_header_update = current_time
        else:
            layout["header"].update(self._cached_header)
        
        # Update analyses with caching (500ms interval) - simplified update logic
        if self._cached_analyses is None or (current_time - self._last_analyses_update) >= self.ANALYSES_UPDATE_INTERVAL:
            self._update_all_analyses(layout["left"])
            self._last_analyses_update = current_time
        else:
            layout["left"].update(self._cached_analyses)
        
        # Update prices with caching (200ms interval) - prices always update
        if self._cached_prices is None or (current_time - self._last_prices_update) >= self.PRICES_UPDATE_INTERVAL:
            self._update_prices(layout["middle"])
            self._last_prices_update = current_time
        else:
            layout["middle"].update(self._cached_prices)
        
        # Update statistics with caching (1 second interval) - simplified update logic
        if self._cached_statistics is None or (current_time - self._last_statistics_update) >= self.STATISTICS_UPDATE_INTERVAL:
            self._update_statistics(layout["right"])
            self._last_statistics_update = current_time
        else:
            layout["right"].update(self._cached_statistics)
        
        # Update footer with caching (1 second interval)
        if self._cached_footer is None or (current_time - self._last_footer_update) >= self.FOOTER_UPDATE_INTERVAL:
            self._update_footer(layout["footer"])
            self._last_footer_update = current_time
        else:
            layout["footer"].update(self._cached_footer)
        
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
            
            self._cached_header = Panel(header_content, style="bold blue", box=box.DOUBLE)
            layout.update(self._cached_header)
        except Exception as e:
            # Fallback header in case of error
            header_content = f"[bold blue]🎯 OKX Triangular Arbitrage Trading System[/bold blue]\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._cached_header = Panel(header_content, style="bold blue")
            layout.update(self._cached_header)
    
    def _update_all_analyses(self, layout: Layout):
        """Update all arbitrage analysis results"""
        try:
            if not self.trading_controller:
                self._cached_analyses = Panel("[dim]No data[/dim]", title="Arbitrage Analysis")
                layout.update(self._cached_analyses)
                return
            
            # Create enhanced arbitrage analysis table with all results
            analysis_table = Table(title="🔍 Real-Time Arbitrage Analysis", box=box.ROUNDED, border_style="cyan")
            analysis_table.add_column("Path", style="cyan")
            analysis_table.add_column("Expected Profit", justify="right")
            analysis_table.add_column("Profit Rate", justify="right")
            analysis_table.add_column("Status", justify="center")
            analysis_table.add_column("Time", style="white")
            
            # Get recent analyses from arbitrage engine
            if hasattr(self.trading_controller, 'arbitrage_engine') and self.trading_controller.arbitrage_engine:
                analyses = getattr(self.trading_controller.arbitrage_engine, 'recent_analyses', [])
                
                # Sort by timestamp (most recent first) for consistent ordering
                sorted_analyses = sorted(analyses, key=lambda x: x.get('timestamp', 0), reverse=True)
                
                # Show last 15 analyses with color coding
                for analysis in sorted_analyses[:15]:  # Changed to first 15 (most recent)
                    path = analysis.get('path_name', 'Unknown')
                    profit_rate = analysis.get('profit_rate', 0)
                    profit_pct = profit_rate * 100  # Convert to percentage
                    timestamp = datetime.fromtimestamp(analysis.get('timestamp', time.time())).strftime('%H:%M:%S')
                    
                    # Determine color and status based on profit rate
                    if profit_rate > 0.003:  # >0.3% - Strong profit opportunity
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
            
            # Add empty row message if needed
            if analysis_table.row_count == 0:
                analysis_table.add_row(
                    "[dim]Analyzing markets...[/dim]",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]",
                    "[dim]--[/dim]"
                )
            
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
            combined.add_row(analysis_table)
            combined.add_row(trades_table)
            
            self._cached_analyses = Panel(combined, title="🔍 Market Analysis", border_style="blue")
            layout.update(self._cached_analyses)
        except Exception as e:
            self.logger.error(f"Error updating analyses: {e}")
            self._cached_analyses = Panel("[red]Error loading analysis data[/red]", title="Market Analysis")
            layout.update(self._cached_analyses)
    
    def _update_prices(self, layout: Layout):
        """Update real-time price information"""
        try:
            if not self.trading_controller or not self.trading_controller.data_collector:
                self._cached_prices = Panel("[dim]No price data[/dim]", title="Market Prices")
                layout.update(self._cached_prices)
                return
            
            price_table = Table(title="💹 Real-Time Prices", box=box.ROUNDED)
            price_table.add_column("Pair", style="cyan")
            price_table.add_column("Bid", style="green", justify="right")
            price_table.add_column("Ask", style="red", justify="right")
            price_table.add_column("Spread", style="yellow", justify="right")
            
            # Use only arbitrage-related trading pairs
            key_pairs = sorted(list(self.arbitrage_pairs)) if self.arbitrage_pairs else ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
            
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
            
            self._cached_prices = Panel(combined, title="📊 Market Data", border_style=border_color)
            layout.update(self._cached_prices)
        except Exception as e:
            self.logger.error(f"Error updating prices: {e}")
            self._cached_prices = Panel("[red]Error loading price data[/red]", title="Market Prices")
            layout.update(self._cached_prices)
    
    def _update_statistics(self, layout: Layout):
        """Update statistics information"""
        try:
            if not self.trading_controller:
                self._cached_statistics = Panel("[dim]No data[/dim]", title="Statistics")
                layout.update(self._cached_statistics)
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
            
            # Balance summary - fetch real-time balance from OKX API
            balance_table = Table(title="💰 Account Balance", box=box.SIMPLE)
            balance_table.add_column("Asset", style="cyan")
            balance_table.add_column("Amount", style="white", justify="right")
            
            total_profit_usdt = 0.0  # For calculating total profit
            # Get initial values from config (trading section)
            initial_usdt = float(self.config_manager.get('trading', 'initial_usdt', default=0) or 0)
            initial_usdc = float(self.config_manager.get('trading', 'initial_usdc', default=0) or 0)
            initial_btc = float(self.config_manager.get('trading', 'initial_btc', default=0) or 0)
            
            if self.trading_controller.trade_executor:
                # Refresh balance every 2 seconds to balance real-time data with API limits
                # Since STATISTICS_UPDATE_INTERVAL is 2 seconds, this will refresh appropriately
                balances = self.trading_controller.trade_executor.balance_cache.get_balance(force_refresh=False)
                usdt_balance = balances.get("USDT", 0)
                usdc_balance = balances.get("USDC", 0)
                btc_balance = balances.get("BTC", 0)
                
                # Display with proper precision matching OKX API
                # USDT & USDC: 5 decimal places (stablecoins), BTC: 8 decimal places
                balance_table.add_row("USDT", f"{usdt_balance:.5f}")
                balance_table.add_row("USDC", f"{usdc_balance:.5f}")  # Same precision as USDT
                balance_table.add_row("BTC", f"{btc_balance:.8f}")
                
                # Calculate total profit based on USDT change only
                # In triangular arbitrage, we start and end with USDT
                # Other currencies should remain relatively stable
                total_profit_usdt = usdt_balance - initial_usdt
                
                # Always show Total Profit, even if 0
                balance_table.add_row("", "")  # Separator
                profit_color = "bright_green" if total_profit_usdt > 0.00001 else "red" if total_profit_usdt < -0.00001 else "white"
                balance_table.add_row("Total Profit", f"[{profit_color}]{total_profit_usdt:+.5f} USDT[/{profit_color}]")
                
                # Optionally show other currency changes for monitoring (should be minimal in triangular arbitrage)
                profit_usdc = usdc_balance - initial_usdc
                profit_btc = btc_balance - initial_btc
                
                # Only show details if there are significant deviations (which might indicate issues)
                if abs(profit_usdc) > 0.1 or abs(profit_btc) > 0.00001:
                    balance_table.add_row("", "")
                    balance_table.add_row("[dim]Deviations:[/dim]", "")
                    
                    if abs(profit_usdc) > 0.1:
                        deviation_color = "yellow" if abs(profit_usdc) < 1 else "red"
                        balance_table.add_row("  USDC", f"[{deviation_color}]{profit_usdc:+.5f}[/{deviation_color}]")
                    
                    if abs(profit_btc) > 0.00001:
                        deviation_color = "yellow" if abs(profit_btc) < 0.0001 else "red"
                        balance_table.add_row("  BTC", f"[{deviation_color}]{profit_btc:+.8f}[/{deviation_color}]")
            
            # Combine all tables
            combined = Table.grid(padding=1)
            combined.add_column()
            combined.add_row(stats_table)
            combined.add_row(risk_table)
            combined.add_row(balance_table)
        
            # Dynamic border color based on total profit
            border_color = "green" if total_profit_usdt > 0 else "yellow" if total_profit_usdt == 0 else "red"
            self._cached_statistics = Panel(combined, title="📈 Performance", border_style=border_color)
            layout.update(self._cached_statistics)
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
            self._cached_statistics = Panel("[red]Error loading statistics[/red]", title="Performance")
            layout.update(self._cached_statistics)
    
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
        
        self._cached_footer = Panel(footer_content, style="bold yellow", box=box.DOUBLE_EDGE)
        layout.update(self._cached_footer)
    
    async def run_monitor_loop(self):
        """Run monitoring loop with intelligent refresh"""
        self.console.print("\n[bold]Starting real-time monitoring interface...[/bold]")
        self.console.print("[dim]Press Ctrl+C to exit safely[/dim]\n")
        
        try:
            # Reduce refresh rate to 2Hz to minimize flicker
            # The intelligent caching will still update data at appropriate intervals
            with Live(self.create_monitor_layout(), refresh_per_second=2, screen=True) as live:
                while self.is_running and not self.shutdown_event.is_set():
                    # Update display - the caching mechanism handles update frequency
                    live.update(self.create_monitor_layout())
                    
                    # Sleep for a shorter interval to maintain responsiveness
                    # The actual update frequency is controlled by the caching logic
                    await asyncio.sleep(0.1)
                    
        except KeyboardInterrupt:
            self.logger.info("User interrupted monitoring interface")
    
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash of data for change detection"""
        try:
            # Convert data to JSON string for consistent hashing
            data_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.md5(data_str.encode()).hexdigest()
        except:
            # If we can't serialize, just use str representation
            return hashlib.md5(str(data).encode()).hexdigest()
    
    def _should_update_analyses(self) -> bool:
        """Check if analyses data has changed"""
        if not self.trading_controller or not hasattr(self.trading_controller, 'arbitrage_engine'):
            return True  # Always update if not initialized
        
        analyses = getattr(self.trading_controller.arbitrage_engine, 'recent_analyses', [])
        
        # Always update if we have new data
        if not analyses and self._prev_analyses_hash is not None:
            return True  # Data was cleared, need update
        
        current_hash = self._calculate_data_hash(analyses[-15:] if analyses else [])
        
        if current_hash != self._prev_analyses_hash:
            self._prev_analyses_hash = current_hash
            return True
        return False
    
    def _should_update_prices(self) -> bool:
        """Check if price data has changed - simplified to always update"""
        # Prices change frequently, always update them
        return True
    
    def _should_update_statistics(self) -> bool:
        """Check if statistics have changed"""
        if not self.trading_controller:
            return True  # Always update if not initialized
        
        try:
            stats = self.trading_controller.get_stats()
            current_hash = self._calculate_data_hash(stats)
            
            if current_hash != self._prev_stats_hash:
                self._prev_stats_hash = current_hash
                return True
            return False
        except:
            return True  # Update on any error
    
    def _extract_arbitrage_pairs(self):
        """Extract trading pairs from arbitrage path configuration"""
        self.arbitrage_pairs = set()
        
        try:
            # Get trading config
            trading_config = self.config_manager.get_trading_config()
            
            # Get paths from config
            paths = trading_config.get('paths', {})
            
            # Extract pairs from each path
            for path_name, path_config in paths.items():
                if isinstance(path_config, dict):
                    steps = path_config.get('steps', [])
                    
                    # Extract pairs from steps
                    for step in steps:
                        pair = step.get('pair')
                        if pair:
                            self.arbitrage_pairs.add(pair)
            
            # If no pairs found, use default
            if not self.arbitrage_pairs:
                self.arbitrage_pairs = {'BTC-USDT', 'BTC-USDC', 'USDT-USDC'}
            
            self.logger.info(f"Extracted arbitrage pairs: {self.arbitrage_pairs}")
            
        except Exception as e:
            self.logger.error(f"Error extracting arbitrage pairs: {e}")
            # Use default pairs
            self.arbitrage_pairs = {'BTC-USDT', 'BTC-USDC', 'USDT-USDC'}
    
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
            
            # Extract trading pairs from arbitrage paths
            self._extract_arbitrage_pairs()
            
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