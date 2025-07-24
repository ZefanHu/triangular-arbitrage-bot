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
        """
        获取标准化的交易对和交易方向
        
        注意：这个方法仅用于向后兼容，建议使用配置文件中的显式交易对配置。
        """
        # 特殊处理USDT和USDC的顺序，确保总是生成USDT-USDC
        if {asset1, asset2} == {'USDT', 'USDC'}:
            if asset1 == 'USDT' and asset2 == 'USDC':
                return 'USDT-USDC', 'sell'  # 卖出USDT换USDC
            else:  # asset1 == 'USDC' and asset2 == 'USDT'
                return 'USDT-USDC', 'buy'   # 买入USDT用USDC
        
        # 简化的交易对生成：优先使用常见的交易对格式
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
        
        # 多重验证机制
        validation_result = self._validate_arbitrage_opportunity(final_amount, profit_rate, trade_steps)
        if not validation_result['valid']:
            self.logger.warning(f"套利机会验证失败: {validation_result['reason']}")
            return None
        
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
    
    def validate_data_consistency(self, orderbooks: Dict) -> bool:
        """
        验证套利计算用数据的时间一致性
        
        Args:
            orderbooks: 订单簿数据字典
            
        Returns:
            数据是否在时间窗口内一致
        """
        if len(orderbooks) < 2:
            return False
        
        # 获取所有时间戳
        timestamps = []
        for pair, orderbook in orderbooks.items():
            if orderbook and hasattr(orderbook, 'timestamp'):
                timestamps.append(orderbook.timestamp)
            else:
                self.logger.warning(f"交易对 {pair} 缺少有效时间戳")
                return False
        
        if len(timestamps) < 2:
            return False
        
        # 计算最大时间差
        max_timestamp = max(timestamps)
        min_timestamp = min(timestamps)
        time_diff = max_timestamp - min_timestamp
        
        # 数据必须在200ms内
        max_time_diff = 0.2  # 200ms
        is_consistent = time_diff <= max_time_diff
        
        if not is_consistent:
            self.logger.warning(f"数据时间一致性检查失败: 最大时间差 {time_diff*1000:.1f}ms > {max_time_diff*1000}ms")
            # 输出详细的时间戳信息用于调试
            for pair, orderbook in orderbooks.items():
                if orderbook and hasattr(orderbook, 'timestamp'):
                    self.logger.debug(f"  {pair}: {orderbook.timestamp} ({orderbook.timestamp*1000:.0f}ms)")
            
        return is_consistent

    def find_opportunities(self) -> List[Dict]:
        """
        查找所有配置路径的套利机会
        
        现在完全使用配置文件中的显式交易对，不再进行推断
        
        Returns:
            套利机会列表，每个元素包含路径、利润率、交易量等信息
        """
        opportunities = []
        
        # 更新统计
        self.stats['check_count'] += 1
        self.stats['last_check_time'] = time.time()
        
        # 预先获取并验证所有需要的订单簿数据
        required_pairs = set()
        for path_name, path_config in self.paths.items():
            if isinstance(path_config, dict) and 'steps' in path_config:
                for step in path_config['steps']:
                    if 'pair' in step:
                        required_pairs.add(step['pair'])
        
        # 获取所有必需的订单簿数据（使用高精度方法）
        orderbooks = {}
        for pair in required_pairs:
            orderbook = self.data_collector.get_arbitrage_orderbook(pair)
            if orderbook:
                orderbooks[pair] = orderbook
            else:
                self.logger.debug(f"无法获取 {pair} 的高精度订单簿数据，跳过此轮套利检查")
                return opportunities
        
        # 数据一致性检查
        if not self.validate_data_consistency(orderbooks):
            self.logger.debug("数据时间一致性检查失败，跳过此轮套利检查")
            return opportunities
        
        # 检查所有配置的路径
        for path_name, path_config in self.paths.items():
            if not path_config:
                continue
                
            # 优先使用新的JSON格式配置
            if isinstance(path_config, dict) and 'steps' in path_config:
                # 新的JSON格式，直接使用配置的交易对，传递已验证的订单簿数据
                self.logger.debug(f"使用显式配置分析路径 {path_name}")
                opportunity = self.calculate_arbitrage_from_steps(path_name, path_config, orderbooks)
            else:
                # 对于旧格式，建议用户升级到新格式
                self.logger.warning(f"路径 {path_name} 使用旧格式配置，建议升级到JSON格式以获得更好的性能和准确性")
                # 暂时保留向后兼容，但会在日志中提醒
                path_assets = self._parse_path_config(path_name, path_config)
                if not path_assets:
                    continue
                    
                self.logger.debug(f"分析路径 {path_name}: {' -> '.join(path_assets)} (使用推断模式)")
                opportunity = self.calculate_arbitrage(path_assets)
            
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
    
    def calculate_arbitrage_from_steps(self, path_name: str, path_config: dict, validated_orderbooks: Dict = None) -> Optional[ArbitrageOpportunity]:
        """
        直接使用配置文件中的交易步骤计算套利机会
        
        Args:
            path_name: 路径名称
            path_config: 包含steps的路径配置
            validated_orderbooks: 已验证一致性的订单簿数据
            
        Returns:
            套利机会信息，如果无套利机会则返回None
        """
        try:
            steps = path_config.get('steps', [])
            if not steps:
                self.logger.warning(f"路径 {path_name} 没有交易步骤")
                return None
            
            route = path_config.get('route', '')
            if route:
                # 从路径描述中提取资产列表
                path_assets = [asset.strip() for asset in route.split('->')]
            else:
                # 从steps中推断路径
                path_assets = self._extract_path_from_steps(steps)
            
            if len(path_assets) < 3 or path_assets[0] != path_assets[-1]:
                self.logger.warning(f"无效路径: {path_assets}")
                return None
            
            trade_steps = []
            
            # 直接使用配置中的交易对，不重新推断
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    self.logger.warning(f"路径 {path_name} 第{i+1}步不是字典格式: {step}")
                    return None
                
                # 支持两种格式：1) pair+action格式，2) from+to格式（测试用）
                pair = step.get('pair')
                action = step.get('action')
                
                # 如果没有pair和action，尝试从from/to转换
                if not pair or not action:
                    from_asset = step.get('from')
                    to_asset = step.get('to')
                    
                    if from_asset and to_asset:
                        # 从from/to转换为pair和action
                        pair, action = self._get_trading_pair(from_asset, to_asset)
                        self.logger.debug(f"从测试格式转换: {from_asset}->{to_asset} => {pair} {action}")
                    else:
                        self.logger.warning(f"路径 {path_name} 第{i+1}步缺少必要信息: {step}")
                        return None
                
                # 优先使用已验证的订单簿数据
                if validated_orderbooks and pair in validated_orderbooks:
                    order_book = validated_orderbooks[pair]
                else:
                    # 回退到从数据采集器获取
                    order_book = self.data_collector.get_orderbook(pair)
                    if not order_book:
                        self.logger.warning(f"无法获取交易对 {pair} 的订单簿")
                        return None
                
                trade_steps.append({
                    'pair': pair,
                    'action': action,
                    'order_book': order_book
                })
            
            # 计算利润率
            final_amount, profit_rate = self.calculate_path_profit_from_steps(trade_steps, self.min_trade_amount)
            
            # 多重验证机制
            validation_result = self._validate_arbitrage_opportunity(final_amount, profit_rate, trade_steps)
            if not validation_result['valid']:
                self.logger.warning(f"套利机会验证失败: {validation_result['reason']}")
                return None
            
            # 判断是否有套利机会
            if profit_rate <= self.min_profit_threshold:
                return None
            
            # 计算最大可交易量（基于订单簿深度）
            max_trade_amount = self._calculate_max_trade_amount_from_steps(trade_steps)
            
            return ArbitrageOpportunity(
                path=path_assets,
                profit_rate=profit_rate,
                min_trade_amount=self.min_trade_amount,
                max_trade_amount=max_trade_amount,
                trade_steps=trade_steps,
                estimated_profit=(final_amount - self.min_trade_amount),
                timestamp=time.time()
            )
            
        except Exception as e:
            self.logger.error(f"计算路径 {path_name} 套利机会失败: {e}")
            return None
    
    def _extract_path_from_steps(self, steps: list) -> list:
        """从交易步骤中提取资产路径"""
        if not steps:
            return []
        
        try:
            first_step = steps[0]
            
            # 支持两种格式：1) pair+action格式，2) from+to格式（测试用）
            if 'pair' in first_step and 'action' in first_step:
                # 使用pair+action格式
                first_pair = first_step['pair']
                first_action = first_step['action']
                base, quote = first_pair.split('-')
                
                # 根据action确定起始资产
                if first_action == 'buy':
                    # 买入base用quote，所以起始资产是quote
                    assets = [quote]
                    current_asset = base
                else:
                    # 卖出base换quote，所以起始资产是base
                    assets = [base]
                    current_asset = quote
                
                assets.append(current_asset)
                
                # 处理后续步骤
                for step in steps[1:]:
                    if 'pair' not in step or 'action' not in step:
                        self.logger.warning(f"步骤缺少pair/action: {step}")
                        return []
                    
                    pair = step['pair']
                    action = step['action']
                    step_base, step_quote = pair.split('-')
                    
                    if action == 'buy':
                        if current_asset == step_quote:
                            current_asset = step_base
                        elif current_asset == step_base:
                            current_asset = step_quote
                    else:  # sell
                        if current_asset == step_base:
                            current_asset = step_quote
                        elif current_asset == step_quote:
                            current_asset = step_base
                    
                    assets.append(current_asset)
                
            elif 'from' in first_step and 'to' in first_step:
                # 使用from+to格式（测试用）
                assets = [first_step['from']]
                
                for step in steps:
                    if 'from' not in step or 'to' not in step:
                        self.logger.warning(f"步骤缺少from/to: {step}")
                        return []
                    
                    to_asset = step['to']
                    if to_asset not in assets:
                        assets.append(to_asset)
                
                # 确保形成闭环
                if assets[-1] != assets[0]:
                    assets.append(assets[0])
            else:
                self.logger.warning(f"无法识别的步骤格式: {first_step}")
                return []
            
            return assets
            
        except Exception as e:
            self.logger.error(f"提取路径时发生错误: {e}")
            return []
    
    def calculate_path_profit_from_steps(self, trade_steps: list, amount: float) -> tuple:
        """
        使用交易步骤计算路径利润
        
        Args:
            trade_steps: 交易步骤列表
            amount: 初始金额
            
        Returns:
            (最终金额, 利润率) 元组
        """
        current_amount = amount
        self.logger.debug(f"开始套利计算: 初始金额 {amount}")
        
        for i, step in enumerate(trade_steps):
            pair = step['pair']
            action = step['action']
            order_book = step['order_book']
            
            # 根据action选择价格
            if action == 'buy':
                # 买入时使用卖一价（asks）
                if hasattr(order_book, 'asks') and order_book.asks:
                    price = order_book.asks[0][0]
                elif isinstance(order_book, dict) and order_book.get('asks'):
                    price = order_book['asks'][0][0]
                else:
                    price = 0
                if price == 0:
                    self.logger.error(f"步骤{i+1}: {pair} {action} 价格为0")
                    return 0, -1
                # 买入计算：current_amount / price（获得多少目标资产）
                prev_amount = current_amount
                current_amount = (current_amount / price) * (1 - self.fee_rate)
                self.logger.debug(f"步骤{i+1}: {pair} {action} @ {price}, {prev_amount:.6f} -> {current_amount:.6f} (手续费:{self.fee_rate:.3%})")
            else:  # sell
                # 卖出时使用买一价（bids）
                if hasattr(order_book, 'bids') and order_book.bids:
                    price = order_book.bids[0][0]
                elif isinstance(order_book, dict) and order_book.get('bids'):
                    price = order_book['bids'][0][0]
                else:
                    price = 0
                if price == 0:
                    self.logger.error(f"步骤{i+1}: {pair} {action} 价格为0")
                    return 0, -1
                # 卖出计算：current_amount * price（获得多少计价资产）
                prev_amount = current_amount
                current_amount = (current_amount * price) * (1 - self.fee_rate)
                self.logger.debug(f"步骤{i+1}: {pair} {action} @ {price}, {prev_amount:.6f} -> {current_amount:.6f} (手续费:{self.fee_rate:.3%})")
        
        profit_rate = (current_amount - amount) / amount
        self.logger.debug(f"套利计算完成: {amount} -> {current_amount:.6f}, 利润率: {profit_rate:.6%}")
        
        # 添加合理性检查
        if profit_rate > 0.1:  # 10%以上的利润率可能不合理
            self.logger.warning(f"🚨 利润率异常高: {profit_rate:.2%}, 可能存在计算错误")
        
        return current_amount, profit_rate
    
    def _calculate_max_trade_amount_from_steps(self, trade_steps: list) -> float:
        """基于交易步骤计算最大可交易量"""
        max_amount = float('inf')
        
        # 从后往前计算，确保每一步都有足够的深度
        for step in reversed(trade_steps):
            order_book = step['order_book']
            action = step['action']
            
            if action == 'buy':
                # 买入时，检查卖单深度
                if hasattr(order_book, 'asks') and order_book.asks:
                    available = sum(ask[1] for ask in order_book.asks[:5])  # 前5档
                    max_amount = min(max_amount, available)
                elif isinstance(order_book, dict) and order_book.get('asks'):
                    available = sum(ask[1] for ask in order_book['asks'][:5])  # 前5档
                    max_amount = min(max_amount, available)
            else:  # sell
                # 卖出时，检查买单深度
                if hasattr(order_book, 'bids') and order_book.bids:
                    available = sum(bid[1] for bid in order_book.bids[:5])  # 前5档
                    max_amount = min(max_amount, available)
                elif isinstance(order_book, dict) and order_book.get('bids'):
                    available = sum(bid[1] for bid in order_book['bids'][:5])  # 前5档
                    max_amount = min(max_amount, available)
        
        return min(max_amount, 10000.0)  # 限制最大交易量
    
    def _parse_path_config(self, path_name: str, path_config) -> List[str]:
        """
        解析路径配置，支持JSON格式和旧格式
        
        Args:
            path_name: 路径名称
            path_config: 路径配置
            
        Returns:
            资产列表，如 ['USDT', 'BTC', 'USDC', 'USDT']
        """
        try:
            # 处理新的JSON格式
            if isinstance(path_config, dict) and 'route' in path_config:
                route = path_config['route']
                # 从路径描述中提取资产列表
                # 例如："USDT->BTC->USDC->USDT" -> ['USDT', 'BTC', 'USDC', 'USDT']
                assets = [asset.strip() for asset in route.split('->')]
                return assets
                
            # 处理新的JSON格式（包含steps）
            elif isinstance(path_config, dict) and 'steps' in path_config:
                # 从steps中推断资产路径
                steps = path_config['steps']
                if not steps:
                    return []
                
                # 从第一个交易对开始推断起始资产
                first_pair = steps[0]['pair']
                first_action = steps[0]['action']
                base, quote = first_pair.split('-')
                
                # 根据action确定起始资产
                if first_action == 'buy':
                    # 买入base用quote，所以起始资产是quote
                    assets = [quote]
                    current_asset = base
                else:
                    # 卖出base换quote，所以起始资产是base
                    assets = [base]
                    current_asset = quote
                
                assets.append(current_asset)
                
                # 处理后续步骤
                for step in steps[1:]:
                    pair = step['pair']
                    action = step['action']
                    step_base, step_quote = pair.split('-')
                    
                    if action == 'buy':
                        if current_asset == step_quote:
                            current_asset = step_base
                        elif current_asset == step_base:
                            current_asset = step_quote
                    else:  # sell
                        if current_asset == step_base:
                            current_asset = step_quote
                        elif current_asset == step_quote:
                            current_asset = step_base
                    
                    assets.append(current_asset)
                
                return assets
                
            # 向后兼容：处理旧格式转换后的结果
            elif isinstance(path_config, dict) and 'assets' in path_config:
                return path_config['assets']
                
            # 向后兼容：处理完全旧格式（列表）
            elif isinstance(path_config, list):
                return path_config
                
            else:
                self.logger.warning(f"未知的路径配置格式: {path_name} = {path_config}")
                return []
                
        except Exception as e:
            self.logger.error(f"解析路径配置失败 {path_name}: {e}")
            return []
    
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
    
    def _validate_arbitrage_opportunity(self, final_amount: float, profit_rate: float, trade_steps: list) -> dict:
        """
        验证套利机会的合理性（增强版）
        
        Args:
            final_amount: 最终金额
            profit_rate: 利润率
            trade_steps: 交易步骤
            
        Returns:
            {'valid': bool, 'reason': str} 验证结果
        """
        # 1. 基本数值检查
        if final_amount <= 0:
            return {'valid': False, 'reason': '最终金额必须大于0'}
        
        if profit_rate < -0.5:  # 损失超过50%不合理
            return {'valid': False, 'reason': f'损失过大: {profit_rate:.2%}'}
            
        # 2. 异常高利润率检查 - 适应真实市场条件
        if profit_rate > 0.01:  # 1% - 真实市场的合理阈值
            return {'valid': False, 'reason': f'利润率异常高: {profit_rate:.2%}, 超过真实市场套利范围(>1%)'}
            
        # 3. 价格合理性检查
        stablecoin_pairs = []  # 记录稳定币交易对
        
        for i, step in enumerate(trade_steps):
            order_book = step.get('order_book')
            if not order_book:
                return {'valid': False, 'reason': f'步骤{i+1}缺少订单簿数据'}
                
            # 检查买卖价差
            if hasattr(order_book, 'bids') and hasattr(order_book, 'asks'):
                if order_book.bids and order_book.asks:
                    bid_price = order_book.bids[0][0]
                    ask_price = order_book.asks[0][0]
                    spread = (ask_price - bid_price) / bid_price
                    
                    # 获取交易对名称
                    pair = step.get('pair', '')
                    
                    # 稳定币交易对的特殊检查
                    if 'USDT-USDC' in pair or 'USDC-USDT' in pair:
                        stablecoin_pairs.append((pair, bid_price, ask_price, spread))
                        
                        # 稳定币价差不应超过0.5%
                        if spread > 0.005:  # 0.5%
                            return {'valid': False, 'reason': f'稳定币{pair}价差异常: {spread:.2%} > 0.5%，疑似模拟环境测试数据'}
                        
                        # 稳定币汇率合理性检查
                        avg_price = (bid_price + ask_price) / 2
                        if avg_price < 0.98 or avg_price > 1.02:  # USDT/USDC应在0.98-1.02范围内
                            return {'valid': False, 'reason': f'稳定币{pair}汇率异常: {avg_price:.4f}，偏离1.0过多'}
                    
                    # 一般价差检查
                    if spread > 0.02:  # 2%
                        return {'valid': False, 'reason': f'步骤{i+1}价差过大: {spread:.2%}'}
                    
                    # 价格倒挂
                    if bid_price >= ask_price:
                        return {'valid': False, 'reason': f'步骤{i+1}价格倒挂: bid={bid_price}, ask={ask_price}'}
        
        # 4. 稳定币套利异常检查
        if stablecoin_pairs:
            self.logger.warning(f"检测到稳定币交易对: {[p[0] for p in stablecoin_pairs]}")
            for pair, bid, ask, spread in stablecoin_pairs:
                self.logger.warning(f"  {pair}: bid={bid:.4f}, ask={ask:.4f}, spread={spread:.4%}")
        
        # 5. 路径逻辑检查
        if len(trade_steps) != 3:
            return {'valid': False, 'reason': f'套利路径必须是3步，当前为{len(trade_steps)}步'}
        
        # 6. 手续费合理性检查
        total_fee_impact = len(trade_steps) * self.fee_rate
        if profit_rate > 0 and profit_rate < total_fee_impact * 1.5:
            # 利润率应该明显超过手续费成本
            self.logger.debug(f"利润率 {profit_rate:.2%} 接近手续费成本 {total_fee_impact:.2%}")
        
        # 7. 模拟环境特殊检查
        if profit_rate > 0.005:  # 0.5%
            self.logger.warning(f"检测到高利润率 {profit_rate:.2%}，可能为模拟环境测试数据")
            return {'valid': False, 'reason': f'利润率 {profit_rate:.2%} 可能为模拟环境异常数据，真实市场中不太可能存在'}
        
        return {'valid': True, 'reason': '验证通过'}