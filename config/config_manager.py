import configparser
import difflib
import json
import os
import time
from utils.logger import setup_logger


SETTINGS_SCHEMA = {
    'trading': {
        'initial_usdt': {'type': float, 'default': 0.0, 'min': 0},
        'initial_usdc': {'type': float, 'default': 0.0, 'min': 0},
        'initial_btc': {'type': float, 'default': 0.0, 'min': 0},
        'fee_rate': {'type': float, 'default': 0.001, 'min': 0, 'max': 1},
        'slippage_tolerance': {'type': float, 'default': 0.002, 'min': 0, 'max': 0.02},
        'min_profit_threshold': {'type': float, 'default': 0.003, 'min': 0, 'max': 0.05},
        'order_timeout': {'type': float, 'default': 3.0, 'min': 0, 'max': 60, 'min_exclusive': True},
        'min_trade_amount': {'type': float, 'default': 100.0, 'min': 0, 'min_exclusive': True},
        'monitor_interval': {'type': float, 'default': 1.0, 'min': 0, 'max': 60, 'min_exclusive': True},
        'enable_profit_validation': {'type': bool, 'default': False},
        'max_profit_rate_threshold': {'type': float, 'default': 0.01, 'min': 0, 'max': 1},
        'max_simulated_profit_rate': {'type': float, 'default': 0.005, 'min': 0, 'max': 1},
        'max_price_spread': {'type': float, 'default': 0.02, 'min': 0, 'max': 1},
        'max_stablecoin_spread': {'type': float, 'default': 0.005, 'min': 0, 'max': 1},
        'stablecoin_price_range_min': {'type': float, 'default': 0.98, 'min': 0, 'max': 2},
        'stablecoin_price_range_max': {'type': float, 'default': 1.02, 'min': 0, 'max': 2}
    },
    'risk': {
        'max_position_ratio': {'type': float, 'default': 0.2, 'min': 0, 'max': 1, 'min_exclusive': True},
        'max_single_trade_ratio': {'type': float, 'default': 0.1, 'min': 0, 'max': 1, 'min_exclusive': True},
        'min_arbitrage_interval': {'type': float, 'default': 10.0, 'min': 0, 'max': 3600},
        'max_daily_trades': {'type': int, 'default': 100, 'min': 1, 'max': 10000},
        'max_daily_loss_ratio': {'type': float, 'default': 0.05, 'min': 0, 'max': 1, 'min_exclusive': True},
        'stop_loss_ratio': {'type': float, 'default': 0.1, 'min': 0, 'max': 1, 'min_exclusive': True},
        'network_retry_count': {'type': int, 'default': 3, 'min': 0, 'max': 10},
        'network_retry_delay': {'type': float, 'default': 1.0, 'min': 0, 'max': 10}
    },
    'system': {
        'log_level': {'type': str, 'default': 'INFO'},
        'system_log_file': {'type': str, 'default': 'logs/system_runtime.log'},
        'enable_trade_history': {'type': bool, 'default': True},
        'trade_record_file': {'type': str, 'default': 'logs/trade_records.json'}
    },
    'api': {
        'api_key': {'type': str, 'default': ''},
        'secret_key': {'type': str, 'default': ''},
        'passphrase': {'type': str, 'default': ''},
        'flag': {'type': str, 'default': '1'}
    }
}

DYNAMIC_KEY_RULES = {
    'trading': {
        'path': {'type': str},
        'fee_rate_': {'type': float, 'min': 0, 'max': 1}
    }
}

DEPRECATED_KEYS = {
    ('trading', 'price_adjustment'): ('trading', 'slippage_tolerance')
}


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
        self.logger = setup_logger(__name__)
        
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

            if os.path.exists(self.settings_path):
                self._apply_deprecated_keys()
                self.validate_config()
                
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
                'parameters': {
                    'fee_rate': float(self._strip_inline_comment(self.get('trading', 'fee_rate', '0.001'))),
                    'slippage_tolerance': float(self._strip_inline_comment(self.get('trading', 'slippage_tolerance', 0.002))),
                    'min_profit_threshold': float(self._strip_inline_comment(self.get('trading', 'min_profit_threshold', 0.003))),
                    'order_timeout': float(self._strip_inline_comment(self.get('trading', 'order_timeout', 3.0))),
                    'min_trade_amount': float(self._strip_inline_comment(self.get('trading', 'min_trade_amount', 100.0))),
                    'monitor_interval': float(self._strip_inline_comment(self.get('trading', 'monitor_interval', 1.0)))
                },
                'validation': {
                    'enable_profit_validation': self._strip_inline_comment(self.get('trading', 'enable_profit_validation', 'false')).lower() == 'true',
                    'max_profit_rate_threshold': float(self._strip_inline_comment(self.get('trading', 'max_profit_rate_threshold', 0.01))),
                    'max_simulated_profit_rate': float(self._strip_inline_comment(self.get('trading', 'max_simulated_profit_rate', 0.005))),
                    'max_price_spread': float(self._strip_inline_comment(self.get('trading', 'max_price_spread', 0.02))),
                    'max_stablecoin_spread': float(self._strip_inline_comment(self.get('trading', 'max_stablecoin_spread', 0.005))),
                    'stablecoin_price_range_min': float(self._strip_inline_comment(self.get('trading', 'stablecoin_price_range_min', 0.98))),
                    'stablecoin_price_range_max': float(self._strip_inline_comment(self.get('trading', 'stablecoin_price_range_max', 1.02)))
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
                'max_position_ratio': self._parse_value(self.get('risk', 'max_position_ratio', 0.2), float),
                'max_single_trade_ratio': self._parse_value(self.get('risk', 'max_single_trade_ratio', 0.1), float),
                'min_arbitrage_interval': self._parse_value(self.get('risk', 'min_arbitrage_interval', 10), float),
                'max_daily_trades': self._parse_value(self.get('risk', 'max_daily_trades', 100), int),
                'max_daily_loss_ratio': self._parse_value(self.get('risk', 'max_daily_loss_ratio', 0.05), float),
                'stop_loss_ratio': self._parse_value(self.get('risk', 'stop_loss_ratio', 0.1), float),
                'network_retry_count': self._parse_value(self.get('risk', 'network_retry_count', 3), int),
                'network_retry_delay': self._parse_value(self.get('risk', 'network_retry_delay', 1.0), float)
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
                'log_level': self._parse_value(self.get('system', 'log_level', 'INFO'), str),
                'system_log_file': self._parse_value(self.get('system', 'system_log_file', 'logs/system_runtime.log'), str),
                'enable_trade_history': self._parse_value(self.get('system', 'enable_trade_history', 'true'), bool),
                'trade_record_file': self._parse_value(self.get('system', 'trade_record_file', 'logs/trade_records.json'), str)
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
                'flag': self._strip_inline_comment(self.get('api', 'flag', '1'))
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
            unknown_keys = {}
            parsed_values = {}

            required_sections = ['trading', 'system']
            for section in required_sections:
                if not self.config.has_section(section):
                    errors.append(f"缺少配置节: [{section}]")

            for section in self.config.sections():
                if section not in SETTINGS_SCHEMA:
                    errors.append(f"未知配置节: [{section}]")
                    continue

                parsed_values[section] = {}
                schema = SETTINGS_SCHEMA[section]
                dynamic_rules = DYNAMIC_KEY_RULES.get(section, {})

                for key, raw_value in self.config.items(section):
                    if key in schema:
                        spec = schema[key]
                    else:
                        spec = None
                        for prefix, rule_spec in dynamic_rules.items():
                            if key.startswith(prefix):
                                spec = rule_spec
                                break
                        if spec is None:
                            unknown_keys.setdefault(section, []).append(key)
                            continue

                    try:
                        value = self._parse_value(raw_value, spec['type'])
                        self._validate_value_range(section, key, value, spec, raw_value)
                    except ValueError as e:
                        errors.append(f"[{section}] {key}={raw_value} 无效: {e}")
                        continue
                    parsed_values[section][key] = value

            if unknown_keys:
                for section, keys in unknown_keys.items():
                    allowed_keys = list(SETTINGS_SCHEMA.get(section, {}).keys())
                    allowed_keys.extend(f"{prefix}*" for prefix in DYNAMIC_KEY_RULES.get(section, {}).keys())
                    for key in keys:
                        suggestion = difflib.get_close_matches(key, allowed_keys, n=1)
                        if suggestion:
                            errors.append(f"未知配置项: [{section}] {key}，你可能想写: {suggestion[0]}")
                        else:
                            errors.append(f"未知配置项: [{section}] {key}")

            risk_values = parsed_values.get('risk', {})
            if 'max_single_trade_ratio' in risk_values and 'max_position_ratio' in risk_values:
                if risk_values['max_single_trade_ratio'] > risk_values['max_position_ratio']:
                    errors.append("max_single_trade_ratio不能大于max_position_ratio")

            trading_values = parsed_values.get('trading', {})
            if 'stablecoin_price_range_min' in trading_values and 'stablecoin_price_range_max' in trading_values:
                if trading_values['stablecoin_price_range_min'] > trading_values['stablecoin_price_range_max']:
                    errors.append("stablecoin_price_range_min不能大于stablecoin_price_range_max")

            if errors:
                message = f"配置验证失败: {', '.join(errors)}"
                self.logger.error(message)
                raise ValueError(message)

            self.logger.info("配置验证通过")
            return True, []
                
        except Exception as e:
            self.logger.error(f"配置验证异常: {e}")
            raise

    def _apply_deprecated_keys(self) -> None:
        for (section, key), (target_section, target_key) in DEPRECATED_KEYS.items():
            if not self.config.has_section(section) or not self.config.has_option(section, key):
                continue
            value = self._strip_inline_comment(self.config.get(section, key))
            if not self.config.has_section(target_section):
                self.config.add_section(target_section)
            if not self.config.has_option(target_section, target_key):
                self.config.set(target_section, target_key, value)
            self.logger.warning(f"配置项 [{section}] {key} 已弃用，已映射至 [{target_section}] {target_key}")
            self.config.remove_option(section, key)

    def _strip_inline_comment(self, value: str) -> str:
        if value is None:
            return value
        if not isinstance(value, str):
            value = str(value)
        for marker in ['#', ';']:
            if marker in value:
                value = value.split(marker)[0]
        return value.strip()

    def _parse_value(self, raw_value: str, expected_type: type):
        value = self._strip_inline_comment(raw_value)
        if expected_type is bool:
            if isinstance(value, bool):
                return value
            normalized = str(value).strip().lower()
            if normalized in ['true', '1', 'yes', 'on']:
                return True
            if normalized in ['false', '0', 'no', 'off']:
                return False
            raise ValueError(f"无法解析布尔值: {raw_value}")
        if expected_type is int:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"无法解析整数: {raw_value}")
            if not numeric.is_integer():
                raise ValueError(f"整数格式无效: {raw_value}")
            return int(numeric)
        if expected_type is float:
            try:
                return float(value)
            except (TypeError, ValueError):
                raise ValueError(f"无法解析浮点数: {raw_value}")
        if expected_type is str:
            return str(value)
        return value

    def _validate_value_range(self, section: str, key: str, value, spec: dict, raw_value: str) -> None:
        if not isinstance(value, (int, float)):
            return
        min_value = spec.get('min', None)
        max_value = spec.get('max', None)
        min_exclusive = spec.get('min_exclusive', False)
        max_exclusive = spec.get('max_exclusive', False)

        if min_value is not None:
            if min_exclusive and not value > min_value:
                raise ValueError(f"{key}必须大于{min_value}，当前值: {raw_value}")
            if not min_exclusive and not value >= min_value:
                raise ValueError(f"{key}必须大于等于{min_value}，当前值: {raw_value}")
        if max_value is not None:
            if max_exclusive and not value < max_value:
                raise ValueError(f"{key}必须小于{max_value}，当前值: {raw_value}")
            if not max_exclusive and not value <= max_value:
                raise ValueError(f"{key}必须小于等于{max_value}，当前值: {raw_value}")
    
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
                self._apply_deprecated_keys()
                self.validate_config()
            
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
