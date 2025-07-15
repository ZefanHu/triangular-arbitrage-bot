#!/usr/bin/env python3
"""
实时监控演示脚本

展示如何使用TradeLogger进行实时监控和统计
"""

import asyncio
import time
import threading
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trading_controller import TradingController
from config.config_manager import ConfigManager
from utils.trade_logger import TradeLogger
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.prompt import Prompt
from rich.rule import Rule
from rich import box


class RealTimeMonitor:
    """实时监控器"""
    
    def __init__(self):
        self.console = Console()
        self.config_manager = ConfigManager()
        self.trading_controller = TradingController(
            config_manager=self.config_manager,
            enable_rich_logging=True
        )
        self.is_running = False
        self.demo_mode = True  # 演示模式，生成模拟数据
        
    def show_welcome(self):
        """显示欢迎界面"""
        welcome_text = """
[bold blue]🚀 三角套利交易系统 - 实时监控演示[/bold blue]

[bold]功能特性:[/bold]
• 📊 实时交易统计
• 🎯 套利机会跟踪
• 💰 利润/损失分析
• ⚡ 性能指标监控
• 📈 余额变化追踪
• 📋 详细交易日志
• 📅 每日报告生成

[bold]操作说明:[/bold]
1. 启动实时监控
2. 查看交易统计
3. 导出每日报告
4. 查看余额历史
5. 退出系统

[bold yellow]注意: 当前为演示模式，将显示模拟数据[/bold yellow]
        """
        
        self.console.print(Panel(
            welcome_text,
            title="[bold green]系统启动[/bold green]",
            border_style="green",
            padding=(1, 2)
        ))
    
    def show_menu(self):
        """显示主菜单"""
        menu_table = Table(title="📋 主菜单", box=box.ROUNDED)
        menu_table.add_column("选项", style="cyan", width=10)
        menu_table.add_column("功能", style="white", width=30)
        menu_table.add_column("描述", style="green")
        
        menu_table.add_row("1", "启动实时监控", "显示实时交易数据面板")
        menu_table.add_row("2", "查看交易统计", "显示详细的交易统计信息")
        menu_table.add_row("3", "查看性能指标", "显示系统性能和资源使用情况")
        menu_table.add_row("4", "导出每日报告", "生成并保存每日交易报告")
        menu_table.add_row("5", "查看余额历史", "显示账户余额变化历史")
        menu_table.add_row("6", "生成模拟数据", "生成一些模拟交易数据用于演示")
        menu_table.add_row("7", "重置统计数据", "清除所有统计数据")
        menu_table.add_row("q", "退出系统", "关闭监控系统")
        
        self.console.print(menu_table)
    
    def generate_demo_data(self):
        """生成演示数据"""
        self.console.print("[yellow]正在生成演示数据...[/yellow]")
        
        # 模拟套利机会
        demo_opportunities = [
            {
                'path_name': 'USDT->USDC->BTC->USDT',
                'profit_rate': 0.0025,
                'min_trade_amount': 100.0,
                'max_trade_amount': 5000.0,
                'timestamp': time.time()
            },
            {
                'path_name': 'USDT->BTC->USDC->USDT',
                'profit_rate': 0.0018,
                'min_trade_amount': 100.0,
                'max_trade_amount': 3000.0,
                'timestamp': time.time() - 30
            }
        ]
        
        # 模拟交易结果
        demo_results = [
            {
                'success': True,
                'investment_amount': 1000.0,
                'final_amount': 1002.3,
                'actual_profit': 2.3,
                'actual_profit_rate': 0.0023,
                'trades': []
            },
            {
                'success': True,
                'investment_amount': 1500.0,
                'final_amount': 1502.1,
                'actual_profit': 2.1,
                'actual_profit_rate': 0.0014,
                'trades': []
            },
            {
                'success': False,
                'investment_amount': 800.0,
                'final_amount': 0.0,
                'actual_profit': 0.0,
                'actual_profit_rate': 0.0,
                'error': '余额不足',
                'trades': []
            }
        ]
        
        # 模拟余额数据
        demo_balances = [
            {'USDT': 8000.0, 'USDC': 2000.0, 'BTC': 0.1},
            {'USDT': 8002.3, 'USDC': 2000.0, 'BTC': 0.1},
            {'USDT': 8004.4, 'USDC': 2000.0, 'BTC': 0.1}
        ]
        
        # 添加到日志系统
        if self.trading_controller.trade_logger:
            for i, opp in enumerate(demo_opportunities):
                self.trading_controller.trade_logger.log_opportunity_found(opp)
                
                if i < len(demo_results):
                    self.trading_controller.trade_logger.log_trade_executed(opp, demo_results[i])
                
                if i < len(demo_balances):
                    self.trading_controller.trade_logger.log_balance_update(demo_balances[i])
        
        self.console.print("[green]✅ 演示数据生成完成[/green]")
    
    def show_real_time_monitor(self):
        """显示实时监控"""
        if not self.trading_controller.trade_logger:
            self.console.print("[red]❌ 实时监控需要启用Rich日志功能[/red]")
            return
        
        self.console.print("[yellow]启动实时监控显示，按 Ctrl+C 退出...[/yellow]")
        time.sleep(2)
        
        try:
            with Live(self._create_monitor_layout(), refresh_per_second=2) as live:
                while True:
                    live.update(self._create_monitor_layout())
                    time.sleep(0.5)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]实时监控已停止[/yellow]")
    
    def _create_monitor_layout(self):
        """创建监控布局"""
        layout = Layout()
        
        # 分割布局
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=6)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # 头部
        header_content = f"""
[bold blue]🚀 三角套利交易系统 - 实时监控[/bold blue]
[bold]当前时间:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [bold]系统状态:[/bold] [green]监控中[/green] | [bold]模式:[/bold] [yellow]演示[/yellow]
        """.strip()
        
        layout["header"].update(Panel(header_content, style="blue"))
        
        # 左侧 - 当前机会和最近交易
        left_content = self._create_opportunities_and_trades_panel()
        layout["left"].update(left_content)
        
        # 右侧 - 余额和统计
        right_content = self._create_balance_and_stats_panel()
        layout["right"].update(right_content)
        
        # 底部 - 性能指标
        footer_content = self._create_performance_panel()
        layout["footer"].update(footer_content)
        
        return layout
    
    def _create_opportunities_and_trades_panel(self):
        """创建机会和交易面板"""
        if not self.trading_controller.trade_logger:
            return Panel("[red]日志系统未启用[/red]", title="数据")
        
        # 当前机会
        opportunities = self.trading_controller.trade_logger.current_opportunities
        opp_table = Table(title="🎯 当前套利机会", box=box.SIMPLE, show_header=True)
        opp_table.add_column("路径", style="cyan", width=20)
        opp_table.add_column("利润率", style="green", width=8)
        opp_table.add_column("时间", style="white", width=8)
        
        for opp in opportunities[-5:]:
            discovery_time = datetime.fromtimestamp(opp.get('timestamp', time.time())).strftime('%H:%M:%S')
            opp_table.add_row(
                opp.get('path_name', 'Unknown')[:18],
                f"{opp.get('profit_rate', 0):.3%}",
                discovery_time
            )
        
        if not opportunities:
            opp_table.add_row("[dim]暂无机会[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")
        
        # 最近交易
        recent_trades = self.trading_controller.trade_logger.recent_trades
        trade_table = Table(title="📈 最近交易记录", box=box.SIMPLE, show_header=True)
        trade_table.add_column("时间", style="cyan", width=8)
        trade_table.add_column("路径", style="white", width=15)
        trade_table.add_column("状态", style="white", width=6)
        trade_table.add_column("利润", style="white", width=10)
        
        for trade in recent_trades[-5:]:
            trade_time = datetime.fromtimestamp(trade.timestamp).strftime('%H:%M:%S')
            status = "[green]成功[/green]" if trade.success else "[red]失败[/red]"
            profit = f"[green]{trade.profit:+.3f}[/green]" if trade.profit > 0 else f"[red]{trade.profit:+.3f}[/red]"
            
            trade_table.add_row(
                trade_time,
                trade.path[:13],
                status,
                profit
            )
        
        if not recent_trades:
            trade_table.add_row("[dim]暂无交易[/dim]", "[dim]--[/dim]", "[dim]--[/dim]", "[dim]--[/dim]")
        
        # 合并表格
        combined_table = Table.grid(padding=1)
        combined_table.add_column()
        combined_table.add_row(opp_table)
        combined_table.add_row(trade_table)
        
        return Panel(combined_table, title="交易信息", border_style="blue")
    
    def _create_balance_and_stats_panel(self):
        """创建余额和统计面板"""
        if not self.trading_controller.trade_logger:
            return Panel("[red]日志系统未启用[/red]", title="统计")
        
        # 今日统计
        stats = self.trading_controller.trade_logger.current_day_stats
        stats_table = Table(title="📊 今日统计", box=box.SIMPLE, show_header=False)
        stats_table.add_column("项目", style="cyan", width=12)
        stats_table.add_column("数值", style="white", width=12)
        
        stats_table.add_row("发现机会", str(stats.total_opportunities))
        stats_table.add_row("执行交易", str(stats.executed_trades))
        stats_table.add_row("成功交易", str(stats.successful_trades))
        stats_table.add_row("成功率", f"{stats.success_rate:.1%}")
        stats_table.add_row("净利润", f"[green]{stats.net_profit:+.3f}[/green]")
        stats_table.add_row("最佳交易", f"[green]{stats.best_trade:+.3f}[/green]")
        
        # 余额信息
        balance_history = self.trading_controller.trade_logger.balance_history
        balance_table = Table(title="💰 当前余额", box=box.SIMPLE, show_header=False)
        balance_table.add_column("资产", style="cyan", width=6)
        balance_table.add_column("数量", style="white", width=12)
        
        if balance_history:
            latest_balance = balance_history[-1]['balance']
            balance_table.add_row("USDT", f"{latest_balance.get('USDT', 0):.2f}")
            balance_table.add_row("USDC", f"{latest_balance.get('USDC', 0):.2f}")
            balance_table.add_row("BTC", f"{latest_balance.get('BTC', 0):.6f}")
            balance_table.add_row("总计", f"{balance_history[-1]['total_usdt']:.2f}")
        else:
            balance_table.add_row("[dim]暂无数据[/dim]", "[dim]--[/dim]")
        
        # 合并表格
        combined_table = Table.grid(padding=1)
        combined_table.add_column()
        combined_table.add_row(stats_table)
        combined_table.add_row(balance_table)
        
        return Panel(combined_table, title="统计信息", border_style="green")
    
    def _create_performance_panel(self):
        """创建性能面板"""
        if not self.trading_controller.trade_logger:
            return Panel("[red]日志系统未启用[/red]", title="性能")
        
        perf = self.trading_controller.trade_logger.performance_metrics
        
        perf_content = f"""
[bold]检查频率:[/bold] {perf.check_frequency:.2f} 次/秒 | [bold]平均执行时间:[/bold] {perf.avg_execution_time:.3f}秒 | [bold]最大执行时间:[/bold] {perf.max_execution_time:.3f}秒
[bold]API调用:[/bold] {perf.api_call_count} 次 | [bold]API错误:[/bold] {perf.api_error_count} 次 | [bold]内存使用:[/bold] {perf.memory_usage:.1f}MB | [bold]CPU使用:[/bold] {perf.cpu_usage:.1f}%
[bold]运行时间:[/bold] {(time.time() - self.trading_controller.stats.start_time) / 60:.1f} 分钟 | [bold]总循环次数:[/bold] {perf.total_execution_count}
        """.strip()
        
        return Panel(perf_content, title="⚡ 性能指标", border_style="yellow")
    
    def show_detailed_stats(self):
        """显示详细统计"""
        if self.trading_controller.trade_logger:
            self.trading_controller.trade_logger.print_daily_report()
        else:
            self.console.print("[red]❌ 详细统计需要启用Rich日志功能[/red]")
    
    def show_performance_metrics(self):
        """显示性能指标"""
        metrics = self.trading_controller.get_performance_metrics()
        
        table = Table(title="⚡ 系统性能指标", box=box.ROUNDED)
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="white")
        table.add_column("说明", style="green")
        
        table.add_row("平均执行时间", f"{metrics.get('avg_execution_time', 0):.3f}秒", "每次循环平均耗时")
        table.add_row("最大执行时间", f"{metrics.get('max_execution_time', 0):.3f}秒", "单次循环最长耗时")
        table.add_row("最小执行时间", f"{metrics.get('min_execution_time', float('inf')):.3f}秒", "单次循环最短耗时")
        table.add_row("峰值内存使用", f"{metrics.get('peak_memory_usage_mb', 0):.1f}MB", "内存使用峰值")
        table.add_row("峰值CPU使用", f"{metrics.get('peak_cpu_usage_percent', 0):.1f}%", "CPU使用峰值")
        table.add_row("API调用次数", str(metrics.get('api_call_count', 0)), "累计API调用次数")
        table.add_row("API错误次数", str(metrics.get('api_error_count', 0)), "累计API错误次数")
        table.add_row("循环次数", str(metrics.get('loop_count', 0)), "主循环执行次数")
        
        self.console.print(table)
    
    def export_report(self):
        """导出报告"""
        if not self.trading_controller.trade_logger:
            self.console.print("[red]❌ 报告导出需要启用Rich日志功能[/red]")
            return
        
        report_file = self.trading_controller.export_daily_report()
        if report_file:
            self.console.print(f"[green]✅ 报告已导出到: {report_file}[/green]")
        else:
            self.console.print("[red]❌ 报告导出失败[/red]")
    
    def show_balance_history(self):
        """显示余额历史"""
        if self.trading_controller.trade_logger:
            self.trading_controller.trade_logger.print_balance_history()
        else:
            self.console.print("[red]❌ 余额历史需要启用Rich日志功能[/red]")
    
    def reset_stats(self):
        """重置统计数据"""
        if self.trading_controller.trade_logger:
            self.trading_controller.trade_logger.reset_daily_stats()
            self.console.print("[green]✅ 统计数据已重置[/green]")
        else:
            self.console.print("[red]❌ 重置功能需要启用Rich日志功能[/red]")
    
    def run(self):
        """运行监控系统"""
        self.show_welcome()
        
        while True:
            self.console.print()
            self.show_menu()
            
            choice = Prompt.ask(
                "\n[bold cyan]请选择功能[/bold cyan]",
                choices=["1", "2", "3", "4", "5", "6", "7", "q"],
                default="1"
            )
            
            if choice == "1":
                self.show_real_time_monitor()
            elif choice == "2":
                self.show_detailed_stats()
            elif choice == "3":
                self.show_performance_metrics()
            elif choice == "4":
                self.export_report()
            elif choice == "5":
                self.show_balance_history()
            elif choice == "6":
                self.generate_demo_data()
            elif choice == "7":
                self.reset_stats()
            elif choice == "q":
                self.console.print("[yellow]正在退出系统...[/yellow]")
                break
            
            if choice != "1":  # 实时监控会自动暂停
                input("\n按回车键继续...")


def main():
    """主函数"""
    try:
        monitor = RealTimeMonitor()
        monitor.run()
    except KeyboardInterrupt:
        print("\n系统已退出")
    except Exception as e:
        print(f"系统错误: {e}")


if __name__ == "__main__":
    main()