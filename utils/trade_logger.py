"""
交易日志记录器

提供美化的交易日志记录、统计报告和实时监控功能
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.rule import Rule
from rich.tree import Tree
from rich.status import Status
from rich.prompt import Prompt
from rich import box
from rich.syntax import Syntax


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: float
    trade_id: str
    path: str
    action: str  # 'opportunity_found', 'trade_executed', 'trade_failed'
    investment_amount: float = 0.0
    final_amount: float = 0.0
    profit: float = 0.0
    profit_rate: float = 0.0
    success: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class DailyStats:
    """每日统计"""
    date: str
    total_opportunities: int = 0
    executed_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    success_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    trading_hours: float = 0.0
    trades_per_hour: float = 0.0
    
    def update_from_trade(self, trade: TradeRecord):
        """从交易记录更新统计"""
        if trade.action == 'opportunity_found':
            self.total_opportunities += 1
        elif trade.action == 'trade_executed':
            self.executed_trades += 1
            if trade.success:
                self.successful_trades += 1
                self.total_profit += max(0, trade.profit)
                self.total_loss += max(0, -trade.profit)
                self.best_trade = max(self.best_trade, trade.profit)
                self.worst_trade = min(self.worst_trade, trade.profit)
            else:
                self.failed_trades += 1
        
        # 重新计算衍生统计
        self.net_profit = self.total_profit - self.total_loss
        self.success_rate = self.successful_trades / self.executed_trades if self.executed_trades > 0 else 0
        self.avg_profit_per_trade = self.net_profit / self.executed_trades if self.executed_trades > 0 else 0


@dataclass
class PerformanceMetrics:
    """性能指标"""
    check_frequency: float = 0.0  # 检查频率 (次/秒)
    avg_execution_time: float = 0.0  # 平均执行时间 (秒)
    max_execution_time: float = 0.0  # 最大执行时间 (秒)
    min_execution_time: float = float('inf')  # 最小执行时间 (秒)
    total_execution_count: int = 0
    total_execution_time: float = 0.0
    api_call_count: int = 0
    api_error_count: int = 0
    memory_usage: float = 0.0  # MB
    cpu_usage: float = 0.0  # %
    
    def update_execution_time(self, execution_time: float):
        """更新执行时间统计"""
        self.total_execution_count += 1
        self.total_execution_time += execution_time
        self.avg_execution_time = self.total_execution_time / self.total_execution_count
        self.max_execution_time = max(self.max_execution_time, execution_time)
        self.min_execution_time = min(self.min_execution_time, execution_time)


class TradeLogger:
    """交易日志记录器"""
    
    def __init__(self, log_dir: str = "logs", enable_file_logging: bool = True):
        """
        初始化交易日志记录器
        
        Args:
            log_dir: 日志目录
            enable_file_logging: 是否启用文件日志
        """
        self.console = Console()
        
        # 从配置管理器获取配置
        from config.config_manager import ConfigManager
        config_manager = ConfigManager()
        system_config = config_manager.get_system_config()
        
        # 使用配置中的值，如果没有则使用默认值
        self.enable_file_logging = system_config.get('enable_trade_history', enable_file_logging)
        trade_history_file = system_config.get('trade_history_file', 'logs/trade_history.json')
        
        # 设置日志目录和文件
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件
        if self.enable_file_logging:
            self.trade_log_file = Path(trade_history_file)
            self.trade_log_file.parent.mkdir(exist_ok=True)  # 确保目录存在
            self.daily_stats_file = self.log_dir / "daily_stats.json"
        
        # 交易记录
        self.trade_records: List[TradeRecord] = []
        self.current_day_stats: DailyStats = DailyStats(date=datetime.now().strftime("%Y-%m-%d"))
        self.performance_metrics = PerformanceMetrics()
        
        # 实时监控数据
        self.current_opportunities: List[Dict] = []
        self.recent_trades: List[TradeRecord] = []
        self.balance_history: List[Dict] = []
        
        # 加载历史数据
        self._load_historical_data()
        
        # 设置标准日志记录器
        self.logger = logging.getLogger(__name__)
        
        self.console.print(Panel(
            "[bold green]交易日志记录器已启动[/bold green]",
            title="系统启动",
            border_style="green"
        ))
    
    def _load_historical_data(self):
        """加载历史数据"""
        try:
            if self.enable_file_logging:
                # 加载交易记录
                if self.trade_log_file.exists():
                    with open(self.trade_log_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.trade_records = [TradeRecord(**record) for record in data]
                
                # 加载每日统计
                if self.daily_stats_file.exists():
                    with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        current_date = datetime.now().strftime("%Y-%m-%d")
                        if current_date in data:
                            self.current_day_stats = DailyStats(**data[current_date])
                        else:
                            self.current_day_stats = DailyStats(date=current_date)
        except Exception as e:
            self.logger.error(f"加载历史数据失败: {e}")
    
    def _save_data(self):
        """保存数据到文件"""
        try:
            if self.enable_file_logging:
                # 保存交易记录
                with open(self.trade_log_file, 'w', encoding='utf-8') as f:
                    json.dump([asdict(record) for record in self.trade_records], f, 
                             indent=2, ensure_ascii=False)
                
                # 保存每日统计
                daily_data = {}
                if self.daily_stats_file.exists():
                    with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                        daily_data = json.load(f)
                
                daily_data[self.current_day_stats.date] = asdict(self.current_day_stats)
                
                with open(self.daily_stats_file, 'w', encoding='utf-8') as f:
                    json.dump(daily_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存数据失败: {e}")
    
    def log_opportunity_found(self, opportunity: Dict):
        """记录发现套利机会"""
        trade_record = TradeRecord(
            timestamp=time.time(),
            trade_id=f"opp_{int(time.time() * 1000)}",
            path=opportunity.get('path_name', 'Unknown'),
            action='opportunity_found',
            details=opportunity
        )
        
        self.trade_records.append(trade_record)
        self.current_day_stats.update_from_trade(trade_record)
        self.current_opportunities.append(opportunity)
        
        # 限制当前机会列表长度
        if len(self.current_opportunities) > 10:
            self.current_opportunities.pop(0)
        
        # 输出美化的机会信息
        self._print_opportunity(opportunity)
        
        self._save_data()
    
    def log_trade_executed(self, opportunity: Dict, result: Dict):
        """记录交易执行结果"""
        trade_record = TradeRecord(
            timestamp=time.time(),
            trade_id=f"trade_{int(time.time() * 1000)}",
            path=opportunity.get('path_name', 'Unknown'),
            action='trade_executed',
            investment_amount=result.get('investment_amount', 0),
            final_amount=result.get('final_amount', 0),
            profit=result.get('actual_profit', 0),
            profit_rate=result.get('actual_profit_rate', 0),
            success=result.get('success', False),
            details={
                'opportunity': opportunity,
                'result': result
            },
            error_message=result.get('error') if not result.get('success') else None
        )
        
        self.trade_records.append(trade_record)
        self.current_day_stats.update_from_trade(trade_record)
        self.recent_trades.append(trade_record)
        
        # 限制最近交易列表长度
        if len(self.recent_trades) > 20:
            self.recent_trades.pop(0)
        
        # 输出美化的交易结果
        self._print_trade_result(trade_record)
        
        self._save_data()
    
    def log_balance_update(self, balance: Dict):
        """记录余额更新"""
        balance_record = {
            'timestamp': time.time(),
            'balance': balance.copy(),
            'total_usdt': sum(balance.values())
        }
        
        self.balance_history.append(balance_record)
        
        # 限制余额历史长度
        if len(self.balance_history) > 100:
            self.balance_history.pop(0)
    
    def update_performance_metrics(self, execution_time: float, api_calls: int = 0, api_errors: int = 0):
        """更新性能指标"""
        self.performance_metrics.update_execution_time(execution_time)
        self.performance_metrics.api_call_count += api_calls
        self.performance_metrics.api_error_count += api_errors
        
        # 计算检查频率
        if len(self.trade_records) > 1:
            time_span = self.trade_records[-1].timestamp - self.trade_records[0].timestamp
            self.performance_metrics.check_frequency = len(self.trade_records) / time_span if time_span > 0 else 0
    
    def _print_opportunity(self, opportunity: Dict):
        """打印套利机会"""
        path_name = opportunity.get('path_name', 'Unknown')
        profit_rate = opportunity.get('profit_rate', 0)
        min_amount = opportunity.get('min_trade_amount', 0)
        max_amount = opportunity.get('max_trade_amount', 0)
        
        # 创建机会面板
        content = f"""
[bold yellow]路径:[/bold yellow] {path_name}
[bold yellow]利润率:[/bold yellow] [green]{profit_rate:.4%}[/green]
[bold yellow]交易范围:[/bold yellow] {min_amount:.2f} - {max_amount:.2f} USDT
[bold yellow]发现时间:[/bold yellow] {datetime.now().strftime('%H:%M:%S')}
        """.strip()
        
        self.console.print(Panel(
            content,
            title="[bold blue]🎯 套利机会[/bold blue]",
            border_style="blue",
            expand=False
        ))
    
    def _print_trade_result(self, trade_record: TradeRecord):
        """打印交易结果"""
        if trade_record.success:
            # 成功交易
            content = f"""
[bold green]✅ 交易成功[/bold green]
[bold]路径:[/bold] {trade_record.path}
[bold]投资金额:[/bold] {trade_record.investment_amount:.6f} USDT
[bold]最终金额:[/bold] {trade_record.final_amount:.6f} USDT
[bold]实际利润:[/bold] [green]{trade_record.profit:+.6f}[/green] USDT
[bold]利润率:[/bold] [green]{trade_record.profit_rate:+.4%}[/green]
[bold]执行时间:[/bold] {datetime.fromtimestamp(trade_record.timestamp).strftime('%H:%M:%S')}
            """.strip()
            
            self.console.print(Panel(
                content,
                title="[bold green]💰 交易成功[/bold green]",
                border_style="green",
                expand=False
            ))
        else:
            # 失败交易
            content = f"""
[bold red]❌ 交易失败[/bold red]
[bold]路径:[/bold] {trade_record.path}
[bold]错误信息:[/bold] [red]{trade_record.error_message or '未知错误'}[/red]
[bold]执行时间:[/bold] {datetime.fromtimestamp(trade_record.timestamp).strftime('%H:%M:%S')}
            """.strip()
            
            self.console.print(Panel(
                content,
                title="[bold red]⚠️ 交易失败[/bold red]",
                border_style="red",
                expand=False
            ))
    
    def print_daily_report(self):
        """打印每日报告"""
        stats = self.current_day_stats
        
        # 创建统计表格
        table = Table(title=f"📊 每日交易报告 - {stats.date}", box=box.ROUNDED)
        table.add_column("指标", style="cyan", no_wrap=True)
        table.add_column("数值", style="magenta", no_wrap=True)
        table.add_column("说明", style="white")
        
        # 添加统计数据
        table.add_row("发现机会", str(stats.total_opportunities), "今日发现的套利机会总数")
        table.add_row("执行交易", str(stats.executed_trades), "今日执行的交易总数")
        table.add_row("成功交易", str(stats.successful_trades), "今日成功的交易数量")
        table.add_row("失败交易", str(stats.failed_trades), "今日失败的交易数量")
        table.add_row("成功率", f"{stats.success_rate:.2%}", "交易成功率")
        table.add_row("总利润", f"{stats.total_profit:.6f} USDT", "今日总利润")
        table.add_row("总损失", f"{stats.total_loss:.6f} USDT", "今日总损失")
        table.add_row("净利润", f"[green]{stats.net_profit:+.6f}[/green] USDT", "今日净利润")
        table.add_row("平均利润", f"{stats.avg_profit_per_trade:.6f} USDT", "每笔交易平均利润")
        table.add_row("最佳交易", f"[green]{stats.best_trade:+.6f}[/green] USDT", "今日最佳交易利润")
        table.add_row("最差交易", f"[red]{stats.worst_trade:+.6f}[/red] USDT", "今日最差交易利润")
        
        self.console.print(table)
        
        # 性能指标
        perf_table = Table(title="⚡ 性能指标", box=box.ROUNDED)
        perf_table.add_column("指标", style="cyan", no_wrap=True)
        perf_table.add_column("数值", style="magenta", no_wrap=True)
        
        perf_table.add_row("检查频率", f"{self.performance_metrics.check_frequency:.2f} 次/秒")
        perf_table.add_row("平均执行时间", f"{self.performance_metrics.avg_execution_time:.3f} 秒")
        perf_table.add_row("最大执行时间", f"{self.performance_metrics.max_execution_time:.3f} 秒")
        perf_table.add_row("最小执行时间", f"{self.performance_metrics.min_execution_time:.3f} 秒")
        perf_table.add_row("API调用总数", str(self.performance_metrics.api_call_count))
        perf_table.add_row("API错误总数", str(self.performance_metrics.api_error_count))
        
        self.console.print(perf_table)
    
    def print_real_time_monitor(self):
        """打印实时监控面板"""
        # 创建布局
        layout = Layout()
        
        # 分割布局
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=5)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # 头部 - 系统状态
        header_content = f"""
[bold blue]🚀 三角套利交易系统 - 实时监控[/bold blue]
[bold]当前时间:[/bold] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | [bold]运行状态:[/bold] [green]运行中[/green]
        """.strip()
        
        layout["header"].update(Panel(header_content, style="blue"))
        
        # 左侧 - 当前机会
        if self.current_opportunities:
            opp_table = Table(title="🎯 当前套利机会", box=box.SIMPLE)
            opp_table.add_column("路径", style="cyan")
            opp_table.add_column("利润率", style="green")
            opp_table.add_column("发现时间", style="white")
            
            for opp in self.current_opportunities[-5:]:  # 显示最近5个机会
                discovery_time = datetime.fromtimestamp(opp.get('timestamp', time.time())).strftime('%H:%M:%S')
                opp_table.add_row(
                    opp.get('path_name', 'Unknown'),
                    f"{opp.get('profit_rate', 0):.4%}",
                    discovery_time
                )
            
            layout["left"].update(opp_table)
        else:
            layout["left"].update(Panel(
                "[yellow]暂无套利机会[/yellow]",
                title="🎯 当前套利机会",
                style="yellow"
            ))
        
        # 右侧 - 最近交易
        if self.recent_trades:
            trade_table = Table(title="📈 最近交易记录", box=box.SIMPLE)
            trade_table.add_column("时间", style="cyan")
            trade_table.add_column("路径", style="white")
            trade_table.add_column("状态", style="white")
            trade_table.add_column("利润", style="white")
            
            for trade in self.recent_trades[-5:]:  # 显示最近5笔交易
                trade_time = datetime.fromtimestamp(trade.timestamp).strftime('%H:%M:%S')
                status = "[green]成功[/green]" if trade.success else "[red]失败[/red]"
                profit = f"[green]{trade.profit:+.6f}[/green]" if trade.profit > 0 else f"[red]{trade.profit:+.6f}[/red]"
                
                trade_table.add_row(
                    trade_time,
                    trade.path,
                    status,
                    profit
                )
            
            layout["right"].update(trade_table)
        else:
            layout["right"].update(Panel(
                "[yellow]暂无交易记录[/yellow]",
                title="📈 最近交易记录",
                style="yellow"
            ))
        
        # 底部 - 统计信息
        stats_content = f"""
[bold]今日统计:[/bold] 机会 {self.current_day_stats.total_opportunities} | 执行 {self.current_day_stats.executed_trades} | 成功 {self.current_day_stats.successful_trades} | 成功率 {self.current_day_stats.success_rate:.2%}
[bold]净利润:[/bold] [green]{self.current_day_stats.net_profit:+.6f}[/green] USDT | [bold]最佳交易:[/bold] [green]{self.current_day_stats.best_trade:+.6f}[/green] USDT
[bold]性能:[/bold] 检查频率 {self.performance_metrics.check_frequency:.2f}/秒 | 平均执行时间 {self.performance_metrics.avg_execution_time:.3f}秒 | API调用 {self.performance_metrics.api_call_count}
        """.strip()
        
        layout["footer"].update(Panel(stats_content, title="📊 系统统计", style="green"))
        
        return layout
    
    def print_balance_history(self):
        """打印余额变化历史"""
        if not self.balance_history:
            self.console.print("[yellow]暂无余额历史数据[/yellow]")
            return
        
        # 创建余额历史表格
        table = Table(title="💰 余额变化历史", box=box.ROUNDED)
        table.add_column("时间", style="cyan")
        table.add_column("USDT", style="green")
        table.add_column("USDC", style="green")
        table.add_column("BTC", style="green")
        table.add_column("总计(USDT)", style="yellow")
        
        for record in self.balance_history[-10:]:  # 显示最近10条记录
            timestamp = datetime.fromtimestamp(record['timestamp']).strftime('%H:%M:%S')
            balance = record['balance']
            
            table.add_row(
                timestamp,
                f"{balance.get('USDT', 0):.2f}",
                f"{balance.get('USDC', 0):.2f}",
                f"{balance.get('BTC', 0):.6f}",
                f"{record['total_usdt']:.2f}"
            )
        
        self.console.print(table)
    
    def start_real_time_monitor(self):
        """启动实时监控显示"""
        try:
            with Live(self.print_real_time_monitor(), refresh_per_second=1) as live:
                while True:
                    live.update(self.print_real_time_monitor())
                    time.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]实时监控已停止[/yellow]")
    
    def export_daily_report(self, date: str = None) -> str:
        """导出每日报告到文件"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        report_file = self.log_dir / f"daily_report_{date}.txt"
        
        # 生成报告内容
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"三角套利交易系统 - 每日报告 {date}\n")
            f.write("=" * 50 + "\n\n")
            
            # 统计信息
            stats = self.current_day_stats
            f.write("交易统计:\n")
            f.write(f"  发现机会: {stats.total_opportunities}\n")
            f.write(f"  执行交易: {stats.executed_trades}\n")
            f.write(f"  成功交易: {stats.successful_trades}\n")
            f.write(f"  失败交易: {stats.failed_trades}\n")
            f.write(f"  成功率: {stats.success_rate:.2%}\n")
            f.write(f"  净利润: {stats.net_profit:.6f} USDT\n")
            f.write(f"  最佳交易: {stats.best_trade:.6f} USDT\n")
            f.write(f"  最差交易: {stats.worst_trade:.6f} USDT\n\n")
            
            # 性能指标
            perf = self.performance_metrics
            f.write("性能指标:\n")
            f.write(f"  检查频率: {perf.check_frequency:.2f} 次/秒\n")
            f.write(f"  平均执行时间: {perf.avg_execution_time:.3f} 秒\n")
            f.write(f"  API调用总数: {perf.api_call_count}\n")
            f.write(f"  API错误总数: {perf.api_error_count}\n\n")
            
            # 交易详情
            f.write("今日交易详情:\n")
            daily_trades = [trade for trade in self.trade_records 
                          if datetime.fromtimestamp(trade.timestamp).strftime("%Y-%m-%d") == date]
            
            for trade in daily_trades:
                if trade.action == 'trade_executed':
                    f.write(f"  {datetime.fromtimestamp(trade.timestamp).strftime('%H:%M:%S')} | "
                           f"{trade.path} | {'成功' if trade.success else '失败'} | "
                           f"利润: {trade.profit:+.6f} USDT\n")
        
        return str(report_file)
    
    def get_statistics_summary(self) -> Dict:
        """获取统计摘要"""
        return {
            'daily_stats': asdict(self.current_day_stats),
            'performance_metrics': asdict(self.performance_metrics),
            'current_opportunities_count': len(self.current_opportunities),
            'recent_trades_count': len(self.recent_trades),
            'balance_records_count': len(self.balance_history),
            'total_records_count': len(self.trade_records)
        }
    
    def reset_daily_stats(self):
        """重置每日统计"""
        self.current_day_stats = DailyStats(date=datetime.now().strftime("%Y-%m-%d"))
        self.console.print(Panel(
            "[bold green]每日统计已重置[/bold green]",
            title="系统重置",
            border_style="green"
        ))
    
    def cleanup(self):
        """清理资源"""
        self._save_data()
        self.console.print(Panel(
            "[bold yellow]交易日志记录器已关闭[/bold yellow]",
            title="系统关闭",
            border_style="yellow"
        ))