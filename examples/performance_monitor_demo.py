#!/usr/bin/env python3
"""
性能监控演示

展示如何使用DataCollector的性能监控功能
"""
import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import json
from datetime import datetime
from core.data_collector import DataCollector


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceMonitorDemo:
    def __init__(self):
        self.data_collector = DataCollector()
        
    async def run_demo(self):
        """运行性能监控演示"""
        try:
            logger.info("启动性能监控演示...")
            
            # 启动数据采集器
            trading_pairs = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT']
            if not await self.data_collector.start(trading_pairs):
                logger.error("数据采集器启动失败")
                return
            
            # 运行一段时间，观察性能统计
            logger.info("运行数据采集器，收集性能数据...")
            
            for i in range(10):  # 运行10分钟
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 获取性能统计
                stats = self.data_collector.get_stats()
                
                # 显示关键指标
                logger.info(f"=== 性能统计 (第{i+1}分钟) ===")
                logger.info(f"运行时间: {stats['uptime_seconds']:.1f}秒")
                
                # API调用统计
                for api_name, api_stats in stats['api_calls'].items():
                    if api_stats['count'] > 0:
                        logger.info(f"API[{api_name}]: {api_stats['count']}次调用, "
                                   f"平均响应时间: {api_stats['avg_response_time']:.3f}s, "
                                   f"错误率: {api_stats['error_rate']:.2%}")
                
                # WebSocket统计
                ws_stats = stats['websocket']
                logger.info(f"WebSocket消息: {ws_stats['messages_received']}条, "
                           f"速率: {ws_stats['msg_rate_per_sec']:.1f}条/秒")
                
                # 缓存统计
                cache_stats = stats['cache']
                logger.info(f"缓存命中率: {cache_stats['hit_rate']:.2%}, "
                           f"订单簿更新: {cache_stats['orderbook_updates']}次")
                
                # 错误统计
                error_stats = stats['errors']
                if error_stats['total'] > 0:
                    logger.warning(f"错误统计: 总计{error_stats['total']}次, "
                                 f"错误率: {error_stats['error_rate_per_min']:.2f}次/分钟")
                
                # 测试一些操作来产生统计数据
                if i % 2 == 0:
                    # 测试获取订单簿
                    for pair in trading_pairs:
                        orderbook = self.data_collector.get_orderbook(pair)
                        if orderbook:
                            logger.debug(f"{pair}最优价格: 买{orderbook.get_best_bid()}, 卖{orderbook.get_best_ask()}")
                
                if i % 3 == 0:
                    # 测试获取余额
                    portfolio = self.data_collector.get_balance()
                    if portfolio:
                        logger.debug(f"账户资产数量: {portfolio.get_total_balance_count()}")
                
                # 导出完整统计到文件
                if i % 5 == 0:
                    await self.export_stats_to_file(stats)
                
                logger.info("-" * 50)
                
        except KeyboardInterrupt:
            logger.info("用户中断演示")
        except Exception as e:
            logger.error(f"演示运行异常: {e}")
        finally:
            # 停止数据采集器
            await self.data_collector.stop()
            logger.info("演示结束")
    
    async def export_stats_to_file(self, stats: dict):
        """导出统计数据到文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/performance_stats_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            logger.info(f"性能统计已导出到: {filename}")
            
        except Exception as e:
            logger.error(f"导出统计数据失败: {e}")
    
    async def stress_test(self):
        """压力测试"""
        logger.info("开始压力测试...")
        
        try:
            # 启动数据采集器
            trading_pairs = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'USDT-USDC']
            if not await self.data_collector.start(trading_pairs):
                logger.error("数据采集器启动失败")
                return
            
            # 高频率访问数据
            for i in range(100):
                # 快速获取所有交易对的订单簿
                for pair in trading_pairs:
                    orderbook = self.data_collector.get_orderbook(pair)
                    if orderbook:
                        _ = orderbook.get_best_bid()
                        _ = orderbook.get_best_ask()
                
                # 获取余额
                portfolio = self.data_collector.get_balance()
                
                if i % 10 == 0:
                    # 每10次循环显示统计
                    stats = self.data_collector.get_stats()
                    cache_stats = stats['cache']
                    logger.info(f"压力测试进度: {i}/100, "
                               f"缓存命中率: {cache_stats['hit_rate']:.2%}, "
                               f"API调用总数: {sum(api['count'] for api in stats['api_calls'].values())}")
                
                await asyncio.sleep(0.1)  # 100ms间隔
            
            # 显示最终统计
            final_stats = self.data_collector.get_stats()
            logger.info("=== 压力测试完成 ===")
            logger.info(f"总运行时间: {final_stats['uptime_seconds']:.1f}秒")
            logger.info(f"缓存命中率: {final_stats['cache']['hit_rate']:.2%}")
            logger.info(f"WebSocket消息速率: {final_stats['websocket']['msg_rate_per_sec']:.1f}条/秒")
            logger.info(f"总错误数: {final_stats['errors']['total']}")
            
        except Exception as e:
            logger.error(f"压力测试异常: {e}")
        finally:
            await self.data_collector.stop()


async def main():
    """主函数"""
    demo = PerformanceMonitorDemo()
    
    # 选择运行模式
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'stress':
        await demo.stress_test()
    else:
        await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
