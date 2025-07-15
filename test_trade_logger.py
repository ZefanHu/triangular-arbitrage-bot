#!/usr/bin/env python3
"""
交易日志系统测试脚本

测试TradeLogger和TradingController的集成功能
"""

import sys
import os
import time
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.trade_logger import TradeLogger
from core.trading_controller import TradingController
from config.config_manager import ConfigManager


def test_trade_logger_basic():
    """测试TradeLogger基本功能"""
    print("🧪 测试TradeLogger基本功能...")
    
    # 创建日志记录器
    logger = TradeLogger(log_dir="logs/test", enable_file_logging=True)
    
    # 测试套利机会记录
    test_opportunity = {
        'path_name': 'USDT->USDC->BTC->USDT',
        'profit_rate': 0.0025,
        'min_trade_amount': 100.0,
        'max_trade_amount': 5000.0,
        'timestamp': time.time()
    }
    
    logger.log_opportunity_found(test_opportunity)
    
    # 测试交易结果记录
    test_result = {
        'success': True,
        'investment_amount': 1000.0,
        'final_amount': 1002.5,
        'actual_profit': 2.5,
        'actual_profit_rate': 0.0025,
        'trades': []
    }
    
    logger.log_trade_executed(test_opportunity, test_result)
    
    # 测试余额记录
    test_balance = {
        'USDT': 8000.0,
        'USDC': 2000.0,
        'BTC': 0.1
    }
    
    logger.log_balance_update(test_balance)
    
    # 测试性能指标更新
    logger.update_performance_metrics(execution_time=0.5, api_calls=3, api_errors=0)
    
    print("✅ TradeLogger基本功能测试完成")
    return logger


def test_trading_controller_integration():
    """测试TradingController集成功能"""
    print("🧪 测试TradingController集成功能...")
    
    try:
        # 创建配置管理器
        config_manager = ConfigManager()
        
        # 创建交易控制器（启用Rich日志）
        controller = TradingController(
            config_manager=config_manager,
            enable_rich_logging=True
        )
        
        # 测试统计功能
        stats = controller.get_stats()
        print(f"📊 基础统计: {stats}")
        
        # 测试性能指标
        performance_metrics = controller.get_performance_metrics()
        print(f"⚡ 性能指标: {performance_metrics}")
        
        # 测试增强统计
        enhanced_stats = controller.get_enhanced_stats()
        print(f"📈 增强统计: 包含 {len(enhanced_stats)} 个指标")
        
        # 测试日志功能
        if controller.trade_logger:
            print("✅ TradeLogger已启用")
            controller.print_daily_report()
        else:
            print("❌ TradeLogger未启用")
        
        print("✅ TradingController集成功能测试完成")
        return controller
        
    except Exception as e:
        print(f"❌ TradingController集成测试失败: {e}")
        return None


def test_rich_formatting():
    """测试Rich格式化功能"""
    print("🧪 测试Rich格式化功能...")
    
    logger = TradeLogger(enable_file_logging=False)
    
    # 生成一些测试数据
    test_opportunities = [
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
    
    test_results = [
        {
            'success': True,
            'investment_amount': 1000.0,
            'final_amount': 1002.5,
            'actual_profit': 2.5,
            'actual_profit_rate': 0.0025,
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
    
    test_balances = [
        {'USDT': 8000.0, 'USDC': 2000.0, 'BTC': 0.1},
        {'USDT': 8002.5, 'USDC': 2000.0, 'BTC': 0.1}
    ]
    
    # 记录测试数据
    for i, opp in enumerate(test_opportunities):
        logger.log_opportunity_found(opp)
        
        if i < len(test_results):
            logger.log_trade_executed(opp, test_results[i])
        
        if i < len(test_balances):
            logger.log_balance_update(test_balances[i])
        
        # 添加一些延迟以模拟真实情况
        time.sleep(0.1)
    
    # 更新性能指标
    logger.update_performance_metrics(execution_time=0.5, api_calls=5, api_errors=1)
    
    print("✅ Rich格式化功能测试完成")
    return logger


def test_report_generation():
    """测试报告生成功能"""
    print("🧪 测试报告生成功能...")
    
    logger = test_rich_formatting()
    
    # 生成并显示日报
    print("\n📅 生成每日报告:")
    logger.print_daily_report()
    
    # 导出报告
    report_file = logger.export_daily_report()
    print(f"📄 报告已导出到: {report_file}")
    
    # 显示余额历史
    print("\n💰 余额历史:")
    logger.print_balance_history()
    
    # 获取统计摘要
    summary = logger.get_statistics_summary()
    print(f"\n📊 统计摘要: {summary}")
    
    print("✅ 报告生成功能测试完成")


def test_real_time_display():
    """测试实时显示功能"""
    print("🧪 测试实时显示功能...")
    
    logger = test_rich_formatting()
    
    # 创建实时监控布局
    layout = logger.print_real_time_monitor()
    
    print("✅ 实时显示功能测试完成")
    print("💡 要查看实时监控效果，请运行: python examples/real_time_monitor.py")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始测试交易日志系统...")
    print("=" * 50)
    
    try:
        # 测试基本功能
        logger = test_trade_logger_basic()
        print()
        
        # 测试集成功能
        controller = test_trading_controller_integration()
        print()
        
        # 测试Rich格式化
        test_rich_formatting()
        print()
        
        # 测试报告生成
        test_report_generation()
        print()
        
        # 测试实时显示
        test_real_time_display()
        print()
        
        print("=" * 50)
        print("🎉 所有测试完成！")
        
        # 显示使用说明
        print("\n📖 使用说明:")
        print("1. 运行实时监控: python examples/real_time_monitor.py")
        print("2. 查看日志文件: logs/trade_history.json")
        print("3. 查看每日统计: logs/daily_stats.json")
        print("4. 导出的报告: logs/daily_report_*.txt")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()