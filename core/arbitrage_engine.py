import logging
import time
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Callable
from config.config_manager import ConfigManager


@dataclass
class ArbitrageOpportunity:
    """套利机会数据类"""
    path: List[str]
    profit_rate: float
    min_trade_amount: float
    max_trade_amount: float
    trade_steps: List[Dict[str, any]]
    estimated_profit: float
    timestamp: float


class ArbitrageEngine:
    """
    套利计算引擎
    
    负责分析市场数据，识别和计算三角套利机会。
    """
    
    def __init__(self, data_collector):
        """
        初始化套利计算引擎
        
        Args:
            data_collector: 数据采集器实例，用于获取市场数据
        """
        self.data_collector = data_collector
        self.config_manager = ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # 从配置管理器获取交易配置
        self.trading_config = self.config_manager.get_trading_config()
        self.paths = self.trading_config.get('paths', {})
        self.fee_rate = self.trading_config.get('parameters', {}).get('fee_rate', 0.001)
        self.min_profit_threshold = self.trading_config.get('parameters', {}).get('min_profit_threshold', 0.003)
        self.min_trade_amount = float(self.config_manager.get('trading', 'min_trade_amount', 100.0))
        
        # 监控相关
        self.monitor_interval = float(self.config_manager.get('trading', 'monitor_interval', 1.0))
        self.is_monitoring = False
        self.monitor_thread = None
        self.opportunity_callbacks = []
        
        # 统计数据
        self.stats = {
            'check_count': 0,
            'opportunity_count': 0,
            'total_profit_rate': 0.0,
            'last_check_time': None,
            'start_time': time.time()
        }
        
        self.logger.info("套利引擎初始化完成")
        self.logger.info(f"手续费率: {self.fee_rate}")
        self.logger.info(f"最小利润阈值: {self.min_profit_threshold}")
        self.logger.info(f"最小交易金额: {self.min_trade_amount}")
        self.logger.info(f"监控间隔: {self.monitor_interval}秒")
    
    def _get_trading_pair(self, asset1: str, asset2: str) -> Tuple[str, str]:
        """获取标准化的交易对和交易方向"""
        # 标准交易对规则：BTC-USDT, ETH-USDT, ETH-BTC 等
        # 基础货币通常是价值较高的币种
        priority = {'BTC': 3, 'ETH': 2, 'USDT': 1, 'USDC': 1}
        
        p1 = priority.get(asset1, 0)
        p2 = priority.get(asset2, 0)
        
        if p1 > p2:
            return f"{asset1}-{asset2}", 'sell'  # 卖出asset1换asset2
        else:
            return f"{asset2}-{asset1}", 'buy'   # 买入asset1用asset2
    
    def calculate_arbitrage(self, path: List[str]) -> Optional[ArbitrageOpportunity]:
        """
        计算单条路径的套利机会
        
        Args:
            path: 交易路径，例如 ['USDT', 'BTC', 'USDC', 'USDT']
        
        Returns:
            套利机会信息字典，包含利润率、交易量等，如果无套利机会则返回None
        """
        if len(path) < 3 or path[0] != path[-1]:
            self.logger.warning(f"无效路径: {path}")
            return None
        
        trade_steps = []
        
        # 获取所有交易对的订单簿
        for i in range(len(path) - 1):
            from_asset = path[i]
            to_asset = path[i + 1]
            
            # 获取交易对和方向
            pair, direction = self._get_trading_pair(from_asset, to_asset)
            
            # 从数据采集器获取订单簿
            order_book = self.data_collector.get_orderbook(pair)
            if not order_book:
                # 尝试获取反向交易对
                assets = pair.split('-')
                if len(assets) == 2:
                    reverse_pair = f"{assets[1]}-{assets[0]}"
                    order_book = self.data_collector.get_orderbook(reverse_pair)
                    if order_book:
                        # 如果找到了反向交易对，调整交易方向
                        pair = reverse_pair
                        direction = 'buy' if direction == 'sell' else 'sell'
                        self.logger.debug(f"使用反向交易对 {pair}, 方向: {direction}")
                    else:
                        self.logger.warning(f"无法获取交易对 {pair} 或其反向交易对的订单簿")
                        return None
                else:
                    self.logger.warning(f"无法获取交易对 {pair} 的订单簿")
                    return None
            
            trade_steps.append({
                'from': from_asset,
                'to': to_asset,
                'pair': pair,
                'direction': direction,
                'order_book': order_book
            })
        
        # 计算利润率
        final_amount, profit_rate = self.calculate_path_profit(path, self.min_trade_amount)
        
        # 判断是否有套利机会
        if profit_rate <= self.min_profit_threshold:
            return None
        
        # 计算最大可交易量（基于订单簿深度）
        max_trade_amount = self._calculate_max_trade_amount(trade_steps)
        
        return ArbitrageOpportunity(
            path=path,
            profit_rate=profit_rate,
            min_trade_amount=self.min_trade_amount,
            max_trade_amount=max_trade_amount,
            trade_steps=trade_steps,
            estimated_profit=(final_amount - self.min_trade_amount),
            timestamp=time.time()
        )
    
    def find_opportunities(self) -> List[Dict]:
        """
        查找所有配置路径的套利机会
        
        Returns:
            套利机会列表，每个元素包含路径、利润率、交易量等信息
        """
        opportunities = []
        
        # 更新统计
        self.stats['check_count'] += 1
        self.stats['last_check_time'] = time.time()
        
        # 按顺序检查路径 (path1, path2)
        for path_name in ['path1', 'path2']:
            path = self.paths.get(path_name, [])
            if not path:
                continue
                
            self.logger.debug(f"分析路径 {path_name}: {' -> '.join(path)}")
            
            # 计算该路径的套利机会
            opportunity = self.calculate_arbitrage(path)
            
            if opportunity:
                opportunity_dict = {
                    'path_name': path_name,
                    'path': opportunity.path,
                    'profit_rate': opportunity.profit_rate,
                    'min_trade_amount': opportunity.min_trade_amount,
                    'max_trade_amount': opportunity.max_trade_amount,
                    'estimated_profit': opportunity.estimated_profit,
                    'timestamp': opportunity.timestamp
                }
                opportunities.append(opportunity_dict)
                
                # 更新统计
                self.stats['opportunity_count'] += 1
                self.stats['total_profit_rate'] += opportunity.profit_rate
                
                self.logger.info(f"发现套利机会: {path_name}, 利润率: {opportunity.profit_rate:.4%}")
        
        return opportunities
    
    def calculate_path_profit(self, path: List[str], amount: float) -> Tuple[float, float]:
        """
        计算指定路径和金额的利润
        
        Args:
            path: 交易路径
            amount: 初始金额
        
        Returns:
            (最终金额, 利润率) 元组
        """
        current_amount = amount
        
        for i in range(len(path) - 1):
            from_asset = path[i]
            to_asset = path[i + 1]
            
            # 获取交易对和方向
            pair, direction = self._get_trading_pair(from_asset, to_asset)
            
            # 获取订单簿
            order_book = self.data_collector.get_orderbook(pair)
            if not order_book:
                # 尝试获取反向交易对
                assets = pair.split('-')
                if len(assets) == 2:
                    reverse_pair = f"{assets[1]}-{assets[0]}"
                    order_book = self.data_collector.get_orderbook(reverse_pair)
                    if order_book:
                        # 如果找到了反向交易对，调整交易方向
                        pair = reverse_pair
                        direction = 'buy' if direction == 'sell' else 'sell'
                        self.logger.debug(f"使用反向交易对 {pair}, 方向: {direction}")
                    else:
                        self.logger.error(f"无法获取 {pair} 或其反向交易对的订单簿")
                        return 0.0, -1.0
                else:
                    self.logger.error(f"无法获取 {pair} 订单簿")
                    return 0.0, -1.0
            
            # 根据方向选择价格
            if direction == 'buy':
                # 买入时使用卖一价（asks）
                if hasattr(order_book, 'asks') and order_book.asks:
                    price = order_book.asks[0][0]
                elif isinstance(order_book, dict) and order_book.get('asks'):
                    price = order_book['asks'][0][0]
                else:
                    price = 0
                if price == 0:
                    return 0, -1
                # 计算获得的数量（扣除手续费）
                current_amount = (current_amount / price) * (1 - self.fee_rate)
            else:
                # 卖出时使用买一价（bids）
                if hasattr(order_book, 'bids') and order_book.bids:
                    price = order_book.bids[0][0]
                elif isinstance(order_book, dict) and order_book.get('bids'):
                    price = order_book['bids'][0][0]
                else:
                    price = 0
                if price == 0:
                    return 0, -1
                # 计算获得的数量（扣除手续费）
                current_amount = (current_amount * price) * (1 - self.fee_rate)
            
            self.logger.debug(f"{from_asset} -> {to_asset}: {direction} @ {price}, amount: {current_amount}")
        
        profit_rate = (current_amount - amount) / amount
        return current_amount, profit_rate
    
    def _calculate_max_trade_amount(self, trade_steps: List[Dict]) -> float:
        """计算基于订单簿深度的最大可交易量"""
        max_amount = float('inf')
        
        # 从后往前计算，确保每一步都有足够的深度
        for step in reversed(trade_steps):
            order_book = step['order_book']
            direction = step['direction']
            
            if direction == 'buy':
                # 买入时，检查卖单深度
                if hasattr(order_book, 'asks') and order_book.asks:
                    available = sum(ask[1] for ask in order_book.asks[:5])  # 前5档
                    max_amount = min(max_amount, available)
                elif isinstance(order_book, dict) and order_book.get('asks'):
                    available = sum(ask[1] for ask in order_book['asks'][:5])  # 前5档
                    max_amount = min(max_amount, available)
            else:
                # 卖出时，检查买单深度
                if hasattr(order_book, 'bids') and order_book.bids:
                    available = sum(bid[1] for bid in order_book.bids[:5])  # 前5档
                    max_amount = min(max_amount, available)
                elif isinstance(order_book, dict) and order_book.get('bids'):
                    available = sum(bid[1] for bid in order_book['bids'][:5])  # 前5档
                    max_amount = min(max_amount, available)
        
        return min(max_amount, 10000.0)  # 限制最大交易量
    
    def monitor_opportunities(self):
        """持续监控套利机会的核心方法"""
        self.logger.info("开始监控套利机会...")
        
        while self.is_monitoring:
            try:
                # 查找套利机会
                opportunities = self.find_opportunities()
                
                # 如果发现机会，触发回调
                if opportunities:
                    for callback in self.opportunity_callbacks:
                        try:
                            callback(opportunities)
                        except Exception as e:
                            self.logger.error(f"执行回调失败: {e}")
                
                # 按照设定的间隔等待
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.error(f"监控过程中发生错误: {e}")
                time.sleep(self.monitor_interval)
        
        self.logger.info("套利监控已停止")
    
    def start_monitoring(self):
        """启动套利机会监控"""
        if self.is_monitoring:
            self.logger.warning("监控已在运行中")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_opportunities)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.logger.info("套利监控已启动")
    
    def stop_monitoring(self):
        """停止套利机会监控"""
        if not self.is_monitoring:
            self.logger.warning("监控未在运行")
            return
        
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("套利监控已停止")
    
    def register_opportunity_callback(self, callback: Callable):
        """注册套利机会回调函数"""
        if callable(callback):
            self.opportunity_callbacks.append(callback)
            self.logger.info(f"已注册回调函数: {callback.__name__}")
        else:
            self.logger.error("尝试注册非可调用对象")
    
    def get_statistics(self) -> Dict:
        """获取监控统计信息"""
        runtime = time.time() - self.stats['start_time']
        avg_profit_rate = (self.stats['total_profit_rate'] / self.stats['opportunity_count']) if self.stats['opportunity_count'] > 0 else 0
        
        return {
            'check_count': self.stats['check_count'],
            'opportunity_count': self.stats['opportunity_count'],
            'average_profit_rate': avg_profit_rate,
            'runtime_seconds': runtime,
            'checks_per_minute': (self.stats['check_count'] / runtime * 60) if runtime > 0 else 0,
            'opportunities_per_hour': (self.stats['opportunity_count'] / runtime * 3600) if runtime > 0 else 0,
            'last_check_time': self.stats['last_check_time']
        }
    
    def reset_statistics(self):
        """重置统计数据"""
        self.stats = {
            'check_count': 0,
            'opportunity_count': 0,
            'total_profit_rate': 0.0,
            'last_check_time': None,
            'start_time': time.time()
        }
        self.logger.info("统计数据已重置")