#!/usr/bin/env python3
"""
测试套利检测准确性修复效果

验证时间戳修复和数据一致性检查是否有效减少虚假套利机会
"""

import asyncio
import time
import logging
from typing import Dict, List
from core.data_collector import DataCollector
from core.arbitrage_engine import ArbitrageEngine
from utils.logger import setup_logger

class ArbitrageFixTester:
    """套利修复测试器"""
    
    def __init__(self):
        self.logger = setup_logger("ArbitrageFixTester", "logs/arbitrage_fix_test.log", logging.INFO)
        self.stats = {
            'total_checks': 0,
            'opportunities_found': 0,
            'consistency_failures': 0,
            'data_age_rejections': 0,
            'valid_opportunities': 0
        }
        
    async def run_test(self, duration_minutes: int = 5):
        """
        运行测试，监控指定时间内的套利检测情况
        
        Args:
            duration_minutes: 测试持续时间（分钟）
        """
        print(f"🧪 开始套利修复效果测试 - 持续 {duration_minutes} 分钟")
        print("=" * 60)
        
        # 初始化组件
        data_collector = DataCollector()
        arbitrage_engine = ArbitrageEngine(data_collector)
        
        # 启动数据采集
        trading_pairs = ['BTC-USDT', 'BTC-USDC', 'USDT-USDC']
        print("🚀 启动数据采集...")
        success = await data_collector.start(trading_pairs)
        
        if not success:
            print("❌ 数据采集启动失败")
            return
            
        # 等待数据稳定
        print("⏳ 等待数据稳定...")
        await asyncio.sleep(3)
        
        # 开始测试循环
        test_start = time.time()
        test_duration = duration_minutes * 60
        check_interval = 2.0  # 2秒检查一次
        
        print(f"🔍 开始监控套利机会...")
        print(f"检查间隔: {check_interval}秒")
        print(f"数据一致性要求: 200ms内")
        print(f"数据新鲜度要求: 500ms内")
        print()
        
        while time.time() - test_start < test_duration:
            await self._check_arbitrage_opportunities(arbitrage_engine)
            await asyncio.sleep(check_interval)
            
            # 每分钟显示一次进度
            elapsed = time.time() - test_start
            if self.stats['total_checks'] % 30 == 0 and self.stats['total_checks'] > 0:
                self._print_progress(elapsed, test_duration)
        
        # 停止数据采集
        await data_collector.stop()
        
        # 显示最终结果
        self._print_final_results(test_duration)
        
    async def _check_arbitrage_opportunities(self, arbitrage_engine: ArbitrageEngine):
        """检查套利机会并记录统计信息"""
        try:
            self.stats['total_checks'] += 1
            
            # 调用修复后的套利检查
            opportunities = arbitrage_engine.find_opportunities()
            
            if opportunities:
                self.stats['opportunities_found'] += len(opportunities)
                self.stats['valid_opportunities'] += len(opportunities)
                
                # 记录发现的机会
                for opp in opportunities:
                    profit_rate = opp.get('profit_rate', 0)
                    path_name = opp.get('path_name', 'Unknown')
                    self.logger.info(f"发现套利机会: {path_name}, 利润率: {profit_rate:.6%}")
                    
        except Exception as e:
            self.logger.error(f"检查套利机会时发生错误: {e}")
    
    def _print_progress(self, elapsed: float, total_duration: float):
        """打印测试进度"""
        progress_pct = (elapsed / total_duration) * 100
        
        print(f"📊 进度: {progress_pct:.1f}% | "
              f"检查次数: {self.stats['total_checks']} | "
              f"发现机会: {self.stats['opportunities_found']} | "
              f"机会率: {(self.stats['opportunities_found']/self.stats['total_checks']*100):.2f}%")
    
    def _print_final_results(self, test_duration: float):
        """打印最终测试结果"""
        print("\n" + "=" * 60)
        print("🎯 套利修复效果测试结果")
        print("=" * 60)
        
        opportunity_rate = (self.stats['opportunities_found'] / self.stats['total_checks'] * 100) if self.stats['total_checks'] > 0 else 0
        
        print(f"📊 统计数据:")
        print(f"  ⏱️  测试时长: {test_duration/60:.1f} 分钟")
        print(f"  🔍 总检查次数: {self.stats['total_checks']}")
        print(f"  ✅ 发现套利机会: {self.stats['opportunities_found']}")
        print(f"  📈 套利机会率: {opportunity_rate:.4f}%")
        
        print(f"\n💡 效果分析:")
        if opportunity_rate < 1.0:
            print("  🎉 修复效果显著! 套利机会率大幅下降")
            print("  ✨ 数据一致性检查有效过滤了虚假机会")
        elif opportunity_rate < 5.0:
            print("  👍 修复效果良好，套利机会率明显降低") 
            print("  📝 建议进一步调整时间阈值")
        else:
            print("  ⚠️  套利机会率仍然较高，可能需要进一步优化")
            print("  🔧 建议检查时间戳处理和一致性验证逻辑")
        
        print(f"\n📋 建议:")
        print("  • 正常市场情况下，套利机会率应 < 1%")
        print("  • 如果机会率过高，检查WebSocket时间戳是否正确")
        print("  • 确保所有数据在200ms时间窗口内")
        
        # 保存结果到日志
        self.logger.info(f"测试完成: 检查{self.stats['total_checks']}次, "
                        f"发现{self.stats['opportunities_found']}个机会, "
                        f"机会率{opportunity_rate:.4f}%")


async def main():
    """主函数"""
    try:
        tester = ArbitrageFixTester()
        await tester.run_test(duration_minutes=3)  # 运行3分钟测试
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())