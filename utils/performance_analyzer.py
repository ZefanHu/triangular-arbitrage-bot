"""
性能分析工具

提供性能数据分析和可视化功能
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from utils.logger import setup_logger


logger = setup_logger(__name__)


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
    
    def analyze_stats_file(self, stats_file: str) -> Dict[str, Any]:
        """
        分析单个统计文件
        
        Args:
            stats_file: 统计文件路径
            
        Returns:
            分析结果
        """
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
            
            analysis = {
                'file': stats_file,
                'timestamp': stats.get('timestamp', 0),
                'uptime_seconds': stats.get('uptime_seconds', 0),
                'summary': self._analyze_summary(stats),
                'api_performance': self._analyze_api_performance(stats),
                'websocket_performance': self._analyze_websocket_performance(stats),
                'cache_performance': self._analyze_cache_performance(stats),
                'error_analysis': self._analyze_errors(stats)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析统计文件失败: {e}")
            return {}
    
    def _analyze_summary(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析总体性能"""
        try:
            uptime = stats.get('uptime_seconds', 0)
            
            # 计算整体健康度
            health_score = 100
            
            # API错误率影响
            api_calls = stats.get('api_calls', {})
            total_api_calls = sum(api['count'] for api in api_calls.values())
            total_api_errors = sum(api['errors'] for api in api_calls.values())
            
            if total_api_calls > 0:
                api_error_rate = total_api_errors / total_api_calls
                health_score -= api_error_rate * 30  # 最多扣30分
            
            # WebSocket连接错误影响
            ws_stats = stats.get('websocket', {})
            ws_errors = ws_stats.get('connection_errors', 0)
            if ws_errors > 0:
                health_score -= min(ws_errors * 5, 20)  # 最多扣20分
            
            # 缓存命中率影响
            cache_stats = stats.get('cache', {})
            cache_hit_rate = cache_stats.get('hit_rate', 0)
            if cache_hit_rate < 0.8:  # 低于80%
                health_score -= (0.8 - cache_hit_rate) * 25  # 最多扣20分
            
            health_score = max(0, min(100, health_score))
            
            return {
                'uptime_minutes': uptime / 60,
                'health_score': health_score,
                'total_api_calls': total_api_calls,
                'total_api_errors': total_api_errors,
                'websocket_errors': ws_errors,
                'cache_hit_rate': cache_hit_rate
            }
            
        except Exception as e:
            logger.error(f"分析总体性能失败: {e}")
            return {}
    
    def _analyze_api_performance(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析API性能"""
        try:
            api_calls = stats.get('api_calls', {})
            analysis = {}
            
            for api_name, api_stats in api_calls.items():
                if api_stats['count'] > 0:
                    # 性能等级
                    avg_time = api_stats['avg_response_time']
                    if avg_time < 0.5:
                        performance_level = 'excellent'
                    elif avg_time < 1.0:
                        performance_level = 'good'
                    elif avg_time < 2.0:
                        performance_level = 'fair'
                    else:
                        performance_level = 'poor'
                    
                    analysis[api_name] = {
                        'count': api_stats['count'],
                        'avg_response_time': avg_time,
                        'error_rate': api_stats['error_rate'],
                        'errors': api_stats['errors'],
                        'performance_level': performance_level,
                        'recommendations': self._get_api_recommendations(api_stats)
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析API性能失败: {e}")
            return {}
    
    def _analyze_websocket_performance(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析WebSocket性能"""
        try:
            ws_stats = stats.get('websocket', {})
            
            msg_rate = ws_stats.get('msg_rate_per_sec', 0)
            
            # 消息速率等级
            if msg_rate > 10:
                rate_level = 'high'
            elif msg_rate > 1:
                rate_level = 'normal'
            elif msg_rate > 0.1:
                rate_level = 'low'
            else:
                rate_level = 'very_low'
            
            # 连接稳定性
            total_errors = ws_stats.get('connection_errors', 0)
            reconnections = ws_stats.get('reconnections', 0)
            
            if total_errors == 0 and reconnections == 0:
                stability = 'excellent'
            elif total_errors <= 2 and reconnections <= 1:
                stability = 'good'
            elif total_errors <= 5 and reconnections <= 3:
                stability = 'fair'
            else:
                stability = 'poor'
            
            return {
                'messages_received': ws_stats.get('messages_received', 0),
                'msg_rate_per_sec': msg_rate,
                'rate_level': rate_level,
                'connection_errors': total_errors,
                'reconnections': reconnections,
                'stability': stability,
                'recommendations': self._get_websocket_recommendations(ws_stats)
            }
            
        except Exception as e:
            logger.error(f"分析WebSocket性能失败: {e}")
            return {}
    
    def _analyze_cache_performance(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析缓存性能"""
        try:
            cache_stats = stats.get('cache', {})
            
            hit_rate = cache_stats.get('hit_rate', 0)
            
            # 缓存效率等级
            if hit_rate >= 0.9:
                efficiency = 'excellent'
            elif hit_rate >= 0.8:
                efficiency = 'good'
            elif hit_rate >= 0.6:
                efficiency = 'fair'
            else:
                efficiency = 'poor'
            
            return {
                'hits': cache_stats.get('hits', 0),
                'misses': cache_stats.get('misses', 0),
                'hit_rate': hit_rate,
                'efficiency': efficiency,
                'orderbook_updates': cache_stats.get('orderbook_updates', 0),
                'balance_updates': cache_stats.get('balance_updates', 0),
                'recommendations': self._get_cache_recommendations(cache_stats)
            }
            
        except Exception as e:
            logger.error(f"分析缓存性能失败: {e}")
            return {}
    
    def _analyze_errors(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析错误统计"""
        try:
            error_stats = stats.get('errors', {})
            
            total_errors = error_stats.get('total', 0)
            error_rate = error_stats.get('error_rate_per_min', 0)
            
            # 错误严重程度
            if total_errors == 0:
                severity = 'none'
            elif error_rate < 0.5:
                severity = 'low'
            elif error_rate < 2:
                severity = 'medium'
            else:
                severity = 'high'
            
            return {
                'total_errors': total_errors,
                'last_hour_errors': error_stats.get('last_hour', 0),
                'error_rate_per_min': error_rate,
                'severity': severity,
                'recommendations': self._get_error_recommendations(error_stats)
            }
            
        except Exception as e:
            logger.error(f"分析错误统计失败: {e}")
            return {}
    
    def _get_api_recommendations(self, api_stats: Dict[str, Any]) -> List[str]:
        """获取API性能建议"""
        recommendations = []
        
        if api_stats['avg_response_time'] > 2.0:
            recommendations.append("API响应时间过长，建议检查网络连接或服务器负载")
        
        if api_stats['error_rate'] > 0.05:  # 5%错误率
            recommendations.append("API错误率较高，建议检查API凭据和网络稳定性")
        
        if api_stats['count'] > 1000:
            recommendations.append("API调用频繁，建议优化缓存策略")
        
        return recommendations
    
    def _get_websocket_recommendations(self, ws_stats: Dict[str, Any]) -> List[str]:
        """获取WebSocket性能建议"""
        recommendations = []
        
        if ws_stats.get('connection_errors', 0) > 3:
            recommendations.append("WebSocket连接不稳定，建议检查网络环境")
        
        if ws_stats.get('reconnections', 0) > 2:
            recommendations.append("频繁重连，建议优化重连策略")
        
        if ws_stats.get('msg_rate_per_sec', 0) < 0.1:
            recommendations.append("消息接收速率过低，建议检查订阅配置")
        
        return recommendations
    
    def _get_cache_recommendations(self, cache_stats: Dict[str, Any]) -> List[str]:
        """获取缓存性能建议"""
        recommendations = []
        
        if cache_stats.get('hit_rate', 0) < 0.8:
            recommendations.append("缓存命中率较低，建议调整缓存策略")
        
        if cache_stats.get('misses', 0) > cache_stats.get('hits', 0):
            recommendations.append("缓存未命中过多，建议增加缓存时间")
        
        return recommendations
    
    def _get_error_recommendations(self, error_stats: Dict[str, Any]) -> List[str]:
        """获取错误处理建议"""
        recommendations = []
        
        if error_stats.get('error_rate_per_min', 0) > 1:
            recommendations.append("错误率过高，建议检查系统健康状况")
        
        if error_stats.get('last_hour', 0) > 10:
            recommendations.append("近期错误频繁，建议检查日志排查问题")
        
        return recommendations
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """生成性能报告"""
        try:
            report = []
            report.append("=" * 60)
            report.append("性能分析报告")
            report.append("=" * 60)
            
            # 总体情况
            summary = analysis.get('summary', {})
            report.append(f"运行时间: {summary.get('uptime_minutes', 0):.1f}分钟")
            report.append(f"健康评分: {summary.get('health_score', 0):.1f}/100")
            report.append(f"API调用总数: {summary.get('total_api_calls', 0)}")
            report.append(f"缓存命中率: {summary.get('cache_hit_rate', 0):.2%}")
            report.append("")
            
            # API性能
            api_perf = analysis.get('api_performance', {})
            if api_perf:
                report.append("API性能分析:")
                for api_name, api_data in api_perf.items():
                    report.append(f"  {api_name}: {api_data['performance_level']}")
                    report.append(f"    平均响应时间: {api_data['avg_response_time']:.3f}s")
                    report.append(f"    错误率: {api_data['error_rate']:.2%}")
                report.append("")
            
            # WebSocket性能
            ws_perf = analysis.get('websocket_performance', {})
            if ws_perf:
                report.append("WebSocket性能分析:")
                report.append(f"  消息速率: {ws_perf.get('msg_rate_per_sec', 0):.1f}条/秒 ({ws_perf.get('rate_level', 'unknown')})")
                report.append(f"  连接稳定性: {ws_perf.get('stability', 'unknown')}")
                report.append(f"  重连次数: {ws_perf.get('reconnections', 0)}")
                report.append("")
            
            # 缓存性能
            cache_perf = analysis.get('cache_performance', {})
            if cache_perf:
                report.append("缓存性能分析:")
                report.append(f"  命中率: {cache_perf.get('hit_rate', 0):.2%} ({cache_perf.get('efficiency', 'unknown')})")
                report.append(f"  更新次数: {cache_perf.get('orderbook_updates', 0)}")
                report.append("")
            
            # 错误分析
            error_analysis = analysis.get('error_analysis', {})
            if error_analysis:
                report.append("错误分析:")
                report.append(f"  总错误数: {error_analysis.get('total_errors', 0)}")
                report.append(f"  错误严重程度: {error_analysis.get('severity', 'unknown')}")
                report.append("")
            
            # 建议
            all_recommendations = set()
            for section in ['api_performance', 'websocket_performance', 'cache_performance', 'error_analysis']:
                section_data = analysis.get(section, {})
                if isinstance(section_data, dict):
                    if 'recommendations' in section_data:
                        all_recommendations.update(section_data['recommendations'])
                    else:
                        for item in section_data.values():
                            if isinstance(item, dict) and 'recommendations' in item:
                                all_recommendations.update(item['recommendations'])
            
            if all_recommendations:
                report.append("优化建议:")
                for i, rec in enumerate(sorted(all_recommendations), 1):
                    report.append(f"  {i}. {rec}")
                report.append("")
            
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"生成性能报告失败: {e}")
            return "报告生成失败"
    
    def find_stats_files(self, days: int = 7) -> List[str]:
        """查找最近几天的统计文件"""
        try:
            files = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for file_path in self.logs_dir.glob("performance_stats_*.json"):
                try:
                    # 从文件名提取日期
                    date_str = file_path.stem.split('_')[-2:]
                    date_str = '_'.join(date_str)
                    file_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                    
                    if file_date >= cutoff_date:
                        files.append(str(file_path))
                except ValueError:
                    continue
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"查找统计文件失败: {e}")
            return []


def main():
    """主函数 - 分析最新的性能统计文件"""
    analyzer = PerformanceAnalyzer()
    
    # 查找最近的统计文件
    stats_files = analyzer.find_stats_files(days=1)
    
    if not stats_files:
        print("未找到性能统计文件")
        return
    
    # 分析最新文件
    latest_file = stats_files[-1]
    print(f"分析文件: {latest_file}")
    
    analysis = analyzer.analyze_stats_file(latest_file)
    if analysis:
        report = analyzer.generate_report(analysis)
        print(report)
        
        # 保存报告
        report_file = f"logs/performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n报告已保存到: {report_file}")


if __name__ == "__main__":
    main()