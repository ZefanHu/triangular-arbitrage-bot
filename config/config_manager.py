import configparser
import os
import logging
import time
import json


class ConfigManager:
    """
    配置管理模块
    
    负责加载和管理应用程序的配置文件，包括交易参数、系统设置和API凭证。
    使用单例模式确保全局唯一的配置管理实例。
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ConfigManager._initialized:
            return
            
        self.config_dir = os.path.dirname(os.path.abspath(__file__))
        self.settings_path = os.path.join(self.config_dir, 'settings.ini')
        self.secrets_path = os.path.join(self.config_dir, 'secrets.ini')
        
        self.config = configparser.ConfigParser()
        self.logger = logging.getLogger(__name__)
        
        # 配置热更新相关
        self._callbacks = []
        self._last_modified_time = 0
        
        self.load_config()
        self._update_modified_time()
        ConfigManager._initialized = True
    
    def load_config(self):
        try:
            if os.path.exists(self.settings_path):
                self.config.read(self.settings_path, encoding='utf-8')
                self.logger.info(f"已加载配置文件: {self.settings_path}")
            else:
                self.logger.warning(f"配置文件不存在: {self.settings_path}")
            
            if os.path.exists(self.secrets_path):
                self.config.read(self.secrets_path, encoding='utf-8')
                self.logger.info(f"已加载密钥文件: {self.secrets_path}")
            else:
                self.logger.info(f"密钥文件不存在，跳过加载: {self.secrets_path}")
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _parse_path_config(self, path_value):
        """
        解析路径配置，支持JSON格式和旧格式
        
        Args:
            path_value: 配置文件中的路径值
            
        Returns:
            dict: 解析后的路径配置
        """
        if not path_value:
            return None
        
        path_value = path_value.strip()
        
        # 尝试解析JSON格式
        if path_value.startswith('{'):
            try:
                return json.loads(path_value)
            except json.JSONDecodeError as e:
                self.logger.error(f"解析JSON路径配置失败: {e}")
                return None
        
        # 向后兼容：解析旧格式 (逗号分隔的资产列表)
        else:
            assets = [asset.strip() for asset in path_value.split(',') if asset.strip()]
            if len(assets) < 2:
                return None
            return {
                "route": "->".join(assets),
                "assets": assets,  # 为了向后兼容保留
                "legacy_format": True
            }
    
    def get_trading_pair_fee(self, pair):
        """
        获取特定交易对的手续费率
        
        Args:
            pair: 交易对，如 'BTC-USDT', 'USDC-USDT' 等
            
        Returns:
            float: 该交易对的手续费率
        """
        try:
            # 将交易对转换为配置键格式（小写，替换连字符为下划线）
            # 例如: 'BTC-USDT' -> 'fee_rate_btc_usdt'
            normalized_pair = pair.lower().replace('-', '_')
            fee_key = f'fee_rate_{normalized_pair}'
            
            # 尝试获取特定交易对的手续费配置
            fee_rate_str = self.get('trading', fee_key, None)
            
            if fee_rate_str is not None:
                # 处理可能包含注释的配置值
                fee_rate_str = fee_rate_str.split('#')[0].strip()
                fee_rate = float(fee_rate_str)
                self.logger.debug(f"使用交易对 {pair} 的特定手续费率: {fee_rate}")
                return fee_rate
            else:
                # 使用默认手续费率
                default_fee_str = self.get('trading', 'fee_rate', '0.001')
                # 处理可能包含注释的配置值
                default_fee_str = default_fee_str.split('#')[0].strip()
                default_fee = float(default_fee_str)
                self.logger.debug(f"交易对 {pair} 使用默认手续费率: {default_fee}")
                return default_fee
                
        except Exception as e:
            self.logger.error(f"获取交易对 {pair} 手续费率失败: {e}")
            # 出错时返回默认值
            default_fee_str = self.get('trading', 'fee_rate', '0.001')
            if default_fee_str:
                default_fee_str = default_fee_str.split('#')[0].strip()
            return float(default_fee_str) if default_fee_str else 0.001
    
    def get_trading_config(self):
        try:
            # 解析路径配置
            paths = {}
            
            # 查找所有path开头的配置项
            if self.config.has_section('trading'):
                for key in self.config['trading']:
                    if key.startswith('path'):
                        path_config = self._parse_path_config(self.get('trading', key, ''))
                        if path_config:
                            paths[key] = path_config
            
            trading_config = {
                'paths': paths,
                'initial_holdings': {
                    'usdt': float(self.get('trading', 'initial_usdt', 0)),
                    'usdc': float(self.get('trading', 'initial_usdc', 0)),
                    'btc': float(self.get('trading', 'initial_btc', 0))
                },
                'parameters': {
                    'rebalance_threshold': float(self.get('trading', 'rebalance_threshold', 5.0)),
                    'fee_rate': float(self.get('trading', 'fee_rate', '0.001').split('#')[0].strip()),
                    'slippage_tolerance': float(self.get('trading', 'slippage_tolerance', 0.002)),
                    'min_profit_threshold': float(self.get('trading', 'min_profit_threshold', 0.003)),
                    'order_timeout': float(self.get('trading', 'order_timeout', 3.0)),
                    'min_trade_amount': float(self.get('trading', 'min_trade_amount', 100.0)),
                    'monitor_interval': float(self.get('trading', 'monitor_interval', 1.0)),
                    'price_adjustment': float(self.get('trading', 'price_adjustment', 0.001))
                },
                'validation': {
                    'enable_profit_validation': self.get('trading', 'enable_profit_validation', 'false').lower() == 'true',
                    'max_profit_rate_threshold': float(self.get('trading', 'max_profit_rate_threshold', 0.01)),
                    'max_simulated_profit_rate': float(self.get('trading', 'max_simulated_profit_rate', 0.005)),
                    'max_price_spread': float(self.get('trading', 'max_price_spread', 0.02)),
                    'max_stablecoin_spread': float(self.get('trading', 'max_stablecoin_spread', 0.005)),
                    'stablecoin_price_range_min': float(self.get('trading', 'stablecoin_price_range_min', 0.98)),
                    'stablecoin_price_range_max': float(self.get('trading', 'stablecoin_price_range_max', 1.02))
                }
            }
            return trading_config
        except Exception as e:
            self.logger.error(f"获取交易配置失败: {e}")
            return {}
    
    def get_risk_config(self):
        """
        获取风险管理配置
        
        Returns:
            dict: 风险管理配置字典
        """
        try:
            risk_config = {
                'max_position_ratio': float(self.get('risk', 'max_position_ratio', 0.2)),
                'max_single_trade_ratio': float(self.get('risk', 'max_single_trade_ratio', 0.1)),
                'min_arbitrage_interval': float(self.get('risk', 'min_arbitrage_interval', 10)),
                'max_daily_trades': int(self.get('risk', 'max_daily_trades', 100)),
                'max_daily_loss_ratio': float(self.get('risk', 'max_daily_loss_ratio', 0.05)),
                'stop_loss_ratio': float(self.get('risk', 'stop_loss_ratio', 0.1)),
                'balance_check_interval': float(self.get('risk', 'balance_check_interval', 60)),
                'network_retry_count': int(self.get('risk', 'network_retry_count', 3)),
                'network_retry_delay': float(self.get('risk', 'network_retry_delay', 1.0))
            }
            return risk_config
        except Exception as e:
            self.logger.error(f"获取风险管理配置失败: {e}")
            return {}
    
    def get_system_config(self):
        """
        获取系统配置
        
        Returns:
            dict: 系统配置字典
        """
        try:
            system_config = {
                'log_level': self.get('system', 'log_level', 'INFO'),
                'log_file': self.get('system', 'log_file', 'logs/trading.log'),
                'enable_trade_history': self.get('system', 'enable_trade_history', 'true').lower() == 'true',
                'trade_history_file': self.get('system', 'trade_history_file', 'logs/trade_history.json')
            }
            return system_config
        except Exception as e:
            self.logger.error(f"获取系统配置失败: {e}")
            return {}
    
    def get_api_credentials(self):
        try:
            if not os.path.exists(self.secrets_path):
                self.logger.warning("API密钥文件不存在，请创建secrets.ini文件")
                return None
            
            credentials = {
                'api_key': self.get('api', 'api_key'),
                'secret_key': self.get('api', 'secret_key'),
                'passphrase': self.get('api', 'passphrase'),
                'flag': self.get('api', 'flag', '1')
            }
            
            if not all([credentials['api_key'], credentials['secret_key'], credentials['passphrase']]):
                self.logger.warning("API凭据不完整，请检查secrets.ini文件")
                return None
                
            return credentials
        except Exception as e:
            self.logger.error(f"获取API凭据失败: {e}")
            return None
    
    def validate_config(self):
        try:
            errors = []
            
            # 检查必要的配置项
            required_sections = ['trading', 'system']
            for section in required_sections:
                if not self.config.has_section(section):
                    errors.append(f"缺少配置节: [{section}]")
            
            # 验证交易参数
            if self.config.has_section('trading'):
                fee_rate_str = self.get('trading', 'fee_rate', '0.001')
                # 处理可能包含注释的配置值
                fee_rate_str = fee_rate_str.split('#')[0].strip()
                fee_rate = float(fee_rate_str)
                if not (0 <= fee_rate <= 1):
                    errors.append("fee_rate必须在0-1之间")
                
                # 验证交易对特定手续费率
                for key in self.config['trading']:
                    if key.startswith('fee_rate_') and key != 'fee_rate':
                        try:
                            pair_fee_str = self.get('trading', key, '0')
                            # 处理可能包含注释的配置值
                            pair_fee_str = pair_fee_str.split('#')[0].strip()
                            pair_fee = float(pair_fee_str)
                            if not (0 <= pair_fee <= 1):
                                errors.append(f"{key}必须在0-1之间")
                        except ValueError:
                            errors.append(f"{key}必须是有效的数字")
                
                slippage_tolerance = float(self.get('trading', 'slippage_tolerance', 0.002))
                if not (0 <= slippage_tolerance <= 1):
                    errors.append("slippage_tolerance必须在0-1之间")
                
                min_profit_threshold = float(self.get('trading', 'min_profit_threshold', 0.003))
                if min_profit_threshold < 0:
                    errors.append("min_profit_threshold必须大于等于0")
                
                order_timeout = float(self.get('trading', 'order_timeout', 3.0))
                if order_timeout <= 0:
                    errors.append("order_timeout必须大于0")
                
                min_trade_amount = float(self.get('trading', 'min_trade_amount', 100.0))
                if min_trade_amount <= 0:
                    errors.append("min_trade_amount必须大于0")
            
            # 验证风险管理参数
            if self.config.has_section('risk'):
                max_position_ratio = float(self.get('risk', 'max_position_ratio', 0.2))
                if not (0 < max_position_ratio <= 1):
                    errors.append("max_position_ratio必须在0-1之间")
                
                max_single_trade_ratio = float(self.get('risk', 'max_single_trade_ratio', 0.1))
                if not (0 < max_single_trade_ratio <= 1):
                    errors.append("max_single_trade_ratio必须在0-1之间")
                
                if max_single_trade_ratio > max_position_ratio:
                    errors.append("max_single_trade_ratio不能大于max_position_ratio")
                
                min_arbitrage_interval = float(self.get('risk', 'min_arbitrage_interval', 10))
                if min_arbitrage_interval < 0:
                    errors.append("min_arbitrage_interval必须大于等于0")
                
                max_daily_trades = int(self.get('risk', 'max_daily_trades', 100))
                if max_daily_trades <= 0:
                    errors.append("max_daily_trades必须大于0")
                
                max_daily_loss_ratio = float(self.get('risk', 'max_daily_loss_ratio', 0.05))
                if not (0 < max_daily_loss_ratio <= 1):
                    errors.append("max_daily_loss_ratio必须在0-1之间")
                
                stop_loss_ratio = float(self.get('risk', 'stop_loss_ratio', 0.1))
                if not (0 < stop_loss_ratio <= 1):
                    errors.append("stop_loss_ratio必须在0-1之间")
            
            if errors:
                self.logger.error(f"配置验证失败: {', '.join(errors)}")
                return False, errors
            else:
                self.logger.info("配置验证通过")
                return True, []
                
        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            return False, [f"验证过程中发生异常: {e}"]
    
    def reload_config(self):
        """重新加载配置文件，保留API凭据"""
        try:
            # 保存当前API凭据
            api_credentials = None
            if self.config.has_section('api'):
                api_credentials = dict(self.config.items('api'))
            
            # 重新加载settings.ini
            self.config.clear()
            if os.path.exists(self.settings_path):
                self.config.read(self.settings_path, encoding='utf-8')
                self.logger.info(f"已重新加载配置文件: {self.settings_path}")
            
            # 恢复API凭据（如果存在）
            if api_credentials:
                if not self.config.has_section('api'):
                    self.config.add_section('api')
                for key, value in api_credentials.items():
                    self.config.set('api', key, value)
            
            # 更新修改时间
            self._update_modified_time()
            
            # 通知回调
            self._notify_callbacks()
            
            self.logger.info("配置重载完成")
            return True
            
        except Exception as e:
            self.logger.error(f"重载配置失败: {e}")
            return False
    
    def watch_config_changes(self):
        """检测配置文件变化"""
        try:
            if not os.path.exists(self.settings_path):
                return False
            
            current_time = os.path.getmtime(self.settings_path)
            if current_time > self._last_modified_time:
                self.logger.info("检测到配置文件变化，准备重载")
                return self.reload_config()
            
            return False
            
        except Exception as e:
            self.logger.error(f"监控配置文件变化失败: {e}")
            return False
    
    def register_callback(self, callback):
        """注册配置更新回调函数"""
        if callable(callback):
            self._callbacks.append(callback)
            self.logger.debug(f"已注册配置更新回调: {callback.__name__}")
        else:
            self.logger.warning("尝试注册非可调用对象作为回调")
    
    def _update_modified_time(self):
        """更新配置文件修改时间"""
        try:
            if os.path.exists(self.settings_path):
                self._last_modified_time = os.path.getmtime(self.settings_path)
        except Exception as e:
            self.logger.error(f"更新文件修改时间失败: {e}")
    
    def _notify_callbacks(self):
        """通知所有注册的回调函数"""
        for callback in self._callbacks:
            try:
                callback()
                self.logger.debug(f"已通知回调: {callback.__name__}")
            except Exception as e:
                self.logger.error(f"回调执行失败 {callback.__name__}: {e}")
    
    def get(self, section, key, default=None):
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            self.logger.debug(f"配置项不存在: [{section}] {key}，使用默认值: {default}")
            return default
        except Exception as e:
            self.logger.error(f"获取配置项失败: [{section}] {key}, 错误: {e}")
            return default