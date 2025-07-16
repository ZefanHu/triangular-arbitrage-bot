#!/usr/bin/env python3
"""
三角套利交易系统主程序

支持两种运行模式：
- monitor: 只监控套利机会，不执行真实交易
- trade: 监控并执行真实交易

用法：
    python main.py --mode monitor --config config/settings.ini
    python main.py --mode trade --config config/settings.ini
"""

import asyncio
import argparse
import logging
import signal
import sys
import os
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.trading_controller import TradingController
from config.config_manager import ConfigManager
from utils.logger import setup_logger


class TradingApplication:
    """
    三角套利交易应用程序主类
    """
    
    def __init__(self, mode: str, config_path: str):
        """
        初始化应用程序
        
        Args:
            mode: 运行模式 (monitor/trade)
            config_path: 配置文件路径（注意：ConfigManager使用固定路径config/settings.ini）
        """
        self.mode = mode
        self.config_path = config_path
        self.is_running = False
        self.trading_controller: Optional[TradingController] = None
        self.logger = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        信号处理器，用于优雅退出
        
        Args:
            signum: 信号编号
            frame: 当前堆栈帧
        """
        if self.logger:
            self.logger.info(f"接收到信号 {signum}，开始优雅退出...")
        else:
            print(f"接收到信号 {signum}，开始优雅退出...")
        
        self.is_running = False
        
        # 如果有交易控制器在运行，停止它
        if self.trading_controller and self.trading_controller.is_running:
            asyncio.create_task(self.trading_controller.stop())
    
    def _validate_config_file(self) -> bool:
        """
        验证配置文件是否存在
        注意：ConfigManager使用固定的config/settings.ini路径
        
        Returns:
            配置文件是否有效
        """
        # ConfigManager使用固定路径，所以我们检查默认路径
        default_config = PROJECT_ROOT / "config" / "settings.ini"
        if not default_config.exists():
            print(f"错误: 配置文件不存在: {default_config}")
            print("ConfigManager使用固定的config/settings.ini路径")
            return False
        
        if not default_config.is_file():
            print(f"错误: 配置路径不是文件: {default_config}")
            return False
        
        # 如果用户指定了不同的配置文件，给出警告
        if self.config_path != "config/settings.ini":
            print(f"警告: ConfigManager使用固定路径config/settings.ini，忽略--config参数: {self.config_path}")
        
        return True
    
    def _setup_logging(self):
        """设置日志系统"""
        try:
            # 确保日志目录存在
            log_dir = PROJECT_ROOT / "logs"
            log_dir.mkdir(exist_ok=True)
            
            # 设置日志
            log_file = PROJECT_ROOT / "logs" / "trading.log"
            self.logger = setup_logger("main", str(log_file))
            self.logger.info("=" * 60)
            self.logger.info("三角套利交易系统启动")
            self.logger.info(f"运行模式: {self.mode}")
            self.logger.info(f"配置文件: config/settings.ini (固定路径)")
            self.logger.info("=" * 60)
            
        except Exception as e:
            print(f"设置日志系统失败: {e}")
            raise
    
    def _load_config(self) -> ConfigManager:
        """
        加载配置
        
        Returns:
            配置管理器实例
        """
        try:
            self.logger.info("加载配置文件...")
            config_manager = ConfigManager()  # ConfigManager使用单例模式，不需要参数
            
            # 验证关键配置项
            trading_config = config_manager.get_trading_config()
            if not trading_config:
                raise ValueError("无法加载交易配置")
            
            self.logger.info("配置文件加载成功")
            return config_manager
            
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    async def _verify_api_connection(self, config_manager: ConfigManager) -> bool:
        """
        验证API连接
        
        Args:
            config_manager: 配置管理器
            
        Returns:
            API连接是否成功
        """
        try:
            self.logger.info("验证API连接...")
            
            # 创建临时的数据采集器来测试连接
            from core.data_collector import DataCollector
            data_collector = DataCollector()
            
            # 测试REST API连接
            balance = data_collector.get_balance()
            if balance is None:
                self.logger.error("无法获取账户余额，API连接失败")
                return False
            
            self.logger.info("API连接验证成功")
            self.logger.info(f"账户资产种类数量: {balance.get_total_balance_count()}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"API连接验证失败: {e}")
            return False
    
    def _display_startup_info(self, config_manager: ConfigManager):
        """
        显示启动信息和统计
        
        Args:
            config_manager: 配置管理器
        """
        try:
            self.logger.info("系统配置信息:")
            
            # 显示交易配置
            trading_config = config_manager.get_trading_config()
            self.logger.info(f"  监控间隔: {trading_config.get('parameters', {}).get('monitor_interval', 1.0)}秒")
            self.logger.info(f"  最小利润阈值: {trading_config.get('parameters', {}).get('min_profit_threshold', 0.003):.3%}")
            self.logger.info(f"  最小交易金额: ${trading_config.get('parameters', {}).get('min_trade_amount', 100.0)}")
            
            # 显示风险配置
            risk_config = config_manager.get_risk_config()
            self.logger.info(f"  最大仓位比例: {risk_config.get('max_position_ratio', 0.2):.1%}")
            self.logger.info(f"  单笔最大交易比例: {risk_config.get('max_single_trade_ratio', 0.1):.1%}")
            self.logger.info(f"  最大单日交易次数: {risk_config.get('max_daily_trades', 100)}")
            
            # 显示套利路径
            paths = trading_config.get('paths', {})
            self.logger.info(f"  配置的套利路径数量: {len(paths)}")
            for path_name, path_config in paths.items():
                if isinstance(path_config, dict) and 'route' in path_config:
                    # 新的JSON格式
                    route = path_config['route']
                    self.logger.info(f"    {path_name}: {route}")
                    if 'steps' in path_config:
                        steps_info = []
                        for step in path_config['steps']:
                            pair = step.get('pair', 'Unknown')
                            action = step.get('action', 'Unknown')
                            steps_info.append(f"{pair}({action})")
                        self.logger.info(f"      交易步骤: {' -> '.join(steps_info)}")
                elif isinstance(path_config, list):
                    # 旧格式
                    path_str = " -> ".join(path_config)
                    self.logger.info(f"    {path_name}: {path_str}")
                elif isinstance(path_config, dict) and 'assets' in path_config:
                    # 旧格式转换后的结果
                    path_str = " -> ".join(path_config['assets'])
                    self.logger.info(f"    {path_name}: {path_str}")
                else:
                    self.logger.info(f"    {path_name}: {path_config}")
            
            # 显示运行模式说明
            if self.mode == "monitor":
                self.logger.info("🔍 监控模式: 只监控套利机会，不执行真实交易")
            else:
                self.logger.info("💰 交易模式: 监控并执行真实交易")
                self.logger.info("⚠️  请确保API权限和余额充足")
            
        except Exception as e:
            self.logger.error(f"显示启动信息失败: {e}")
    
    async def _create_and_start_trading_controller(self, config_manager: ConfigManager) -> bool:
        """
        创建并启动交易控制器
        
        Args:
            config_manager: 配置管理器
            
        Returns:
            启动是否成功
        """
        try:
            self.logger.info("创建交易控制器...")
            
            # 根据模式决定是否启用Rich日志
            enable_rich_logging = True
            
            # 创建交易控制器
            self.trading_controller = TradingController(
                config_manager=config_manager,
                enable_rich_logging=enable_rich_logging
            )
            
            # 如果是监控模式，禁用真实交易
            if self.mode == "monitor":
                self.trading_controller.disable_trading("监控模式 - 禁用真实交易")
                self.logger.info("已禁用真实交易（监控模式）")
            else:
                self.trading_controller.enable_trading()
                self.logger.info("已启用真实交易（交易模式）")
            
            # 启动交易控制器
            self.logger.info("启动交易控制器...")
            if not await self.trading_controller.start():
                self.logger.error("交易控制器启动失败")
                return False
            
            self.logger.info("交易控制器启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"创建/启动交易控制器失败: {e}")
            return False
    
    async def _run_main_loop(self):
        """
        运行主循环
        """
        self.logger.info("进入主循环...")
        self.is_running = True
        
        try:
            # 定期显示统计信息
            stats_interval = 300  # 5分钟
            last_stats_time = 0
            
            while self.is_running and self.trading_controller.is_running:
                current_time = asyncio.get_event_loop().time()
                
                # 定期显示统计信息
                if current_time - last_stats_time >= stats_interval:
                    self._display_runtime_stats()
                    last_stats_time = current_time
                
                # 检查交易控制器状态
                if not self.trading_controller.is_running:
                    self.logger.warning("交易控制器已停止")
                    break
                
                # 短暂休眠
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.info("主循环被取消")
        except Exception as e:
            self.logger.error(f"主循环异常: {e}")
        
        self.logger.info("主循环结束")
    
    def _display_runtime_stats(self):
        """显示运行时统计信息"""
        try:
            stats = self.trading_controller.get_stats()
            
            self.logger.info("=" * 50)
            self.logger.info("运行时统计:")
            self.logger.info(f"  运行时间: {stats['runtime_seconds']/60:.1f}分钟")
            self.logger.info(f"  发现套利机会: {stats['total_opportunities']}个")
            self.logger.info(f"  执行交易: {stats['executed_trades']}个")
            self.logger.info(f"  成功交易: {stats['successful_trades']}个")
            
            if stats['executed_trades'] > 0:
                self.logger.info(f"  交易成功率: {stats['success_rate']:.1%}")
            
            self.logger.info(f"  净利润: {stats['net_profit']:+.6f}")
            self.logger.info(f"  机会发现率: {stats['opportunities_per_hour']:.1f}个/小时")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"显示运行时统计失败: {e}")
    
    async def _shutdown(self):
        """
        关闭应用程序
        """
        self.logger.info("开始关闭应用程序...")
        
        try:
            # 停止交易控制器
            if self.trading_controller and self.trading_controller.is_running:
                self.logger.info("停止交易控制器...")
                if await self.trading_controller.stop():
                    self.logger.info("交易控制器已成功停止")
                else:
                    self.logger.warning("交易控制器停止时发生错误")
            
            # 显示最终统计
            if self.trading_controller:
                self.logger.info("最终统计:")
                self.trading_controller.print_daily_report()
            
            self.logger.info("应用程序已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭应用程序时发生错误: {e}")
    
    async def run(self) -> int:
        """
        运行应用程序主流程
        
        Returns:
            退出代码 (0表示成功)
        """
        try:
            # 1. 验证配置文件
            if not self._validate_config_file():
                return 1
            
            # 2. 设置日志系统
            self._setup_logging()
            
            # 3. 加载配置
            config_manager = self._load_config()
            
            # 4. 验证API连接
            if not await self._verify_api_connection(config_manager):
                self.logger.error("API连接验证失败，无法继续运行")
                return 1
            
            # 5. 显示启动信息
            self._display_startup_info(config_manager)
            
            # 6. 创建并启动交易控制器
            if not await self._create_and_start_trading_controller(config_manager):
                return 1
            
            # 7. 运行主循环
            await self._run_main_loop()
            
            return 0
            
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("用户中断程序")
            else:
                print("用户中断程序")
            return 0
        except Exception as e:
            if self.logger:
                self.logger.error(f"程序运行异常: {e}")
            else:
                print(f"程序运行异常: {e}")
            return 1
        finally:
            # 清理资源
            await self._shutdown()


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="三角套利交易系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
运行模式说明:
  monitor  只监控套利机会，不执行真实交易（适合测试和观察）
  trade    监控并执行真实交易（需要确保API权限和余额）

示例用法:
  python main.py --mode monitor --config config/settings.ini
  python main.py --mode trade --config config/settings.ini
  python main.py --mode monitor  # 使用默认配置文件
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["monitor", "trade"],
        default="monitor",
        help="运行模式: monitor(只监控) 或 trade(实际交易)，默认为monitor"
    )
    
    parser.add_argument(
        "--config",
        default="config/settings.ini",
        help="配置文件路径，默认为 config/settings.ini"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="三角套利交易系统 v1.0.0"
    )
    
    return parser.parse_args()


async def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 创建并运行应用程序
        app = TradingApplication(mode=args.mode, config_path=args.config)
        exit_code = await app.run()
        
        return exit_code
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        return 1


if __name__ == "__main__":
    # 运行主程序
    exit_code = asyncio.run(main())
    sys.exit(exit_code)