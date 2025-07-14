import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_manager import ConfigManager


class TestConfigManager:
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # 重置单例实例
        ConfigManager._instance = None
        ConfigManager._initialized = False
        yield
        # 清理
        ConfigManager._instance = None
        ConfigManager._initialized = False
    
    @pytest.fixture
    def temp_config_dir(self):
        temp_dir = tempfile.mkdtemp()
        
        # 复制测试配置文件
        test_settings_path = os.path.join(os.path.dirname(__file__), 'test_settings.ini')
        temp_settings_path = os.path.join(temp_dir, 'settings.ini')
        shutil.copy2(test_settings_path, temp_settings_path)
        
        yield temp_dir
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
    
    def test_singleton_pattern(self):
        """测试单例模式是否正常工作"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = '/mock/config'
            
            with patch('config.config_manager.os.path.exists') as mock_exists:
                mock_exists.return_value = False
                
                instance1 = ConfigManager()
                instance2 = ConfigManager()
                
                assert instance1 is instance2
                assert id(instance1) == id(instance2)
    
    def test_load_config(self, temp_config_dir):
        """测试配置加载功能"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            
            # 验证配置是否正确加载
            assert config_manager.get('trading', 'initial_usdt') == '1000'
            assert config_manager.get('trading', 'fee_rate') == '0.001'
            assert config_manager.get('system', 'log_level') == 'DEBUG'
    
    def test_get_trading_config(self, temp_config_dir):
        """测试获取交易配置"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            trading_config = config_manager.get_trading_config()
            
            assert isinstance(trading_config, dict)
            assert 'paths' in trading_config
            assert 'initial_holdings' in trading_config
            assert 'parameters' in trading_config
            
            # 验证具体数值
            assert trading_config['initial_holdings']['usdt'] == 1000.0
            assert trading_config['parameters']['fee_rate'] == 0.001
            assert trading_config['paths']['path1'] == ['USDT', 'USDC', 'BTC', 'USDT']
    
    def test_validate_config(self, temp_config_dir):
        """测试配置验证"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            is_valid, errors = config_manager.validate_config()
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_validate_config_invalid_values(self, temp_config_dir):
        """测试无效配置值的验证"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            
            # 修改配置为无效值
            config_manager.config.set('trading', 'fee_rate', '1.5')  # 超出范围
            
            is_valid, errors = config_manager.validate_config()
            
            assert is_valid is False
            assert len(errors) > 0
            assert any('fee_rate' in error for error in errors)
    
    def test_reload_config(self, temp_config_dir):
        """测试配置重载功能"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            
            # 添加一个回调函数来测试通知机制
            callback_called = False
            def test_callback():
                nonlocal callback_called
                callback_called = True
            
            config_manager.register_callback(test_callback)
            
            # 模拟配置文件修改
            original_value = config_manager.get('trading', 'initial_usdt')
            
            # 修改配置文件
            settings_path = os.path.join(temp_config_dir, 'settings.ini')
            with open(settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified_content = content.replace('initial_usdt = 1000', 'initial_usdt = 5000')
            with open(settings_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            # 重载配置
            result = config_manager.reload_config()
            
            assert result is True
            assert config_manager.get('trading', 'initial_usdt') == '5000'
            assert callback_called is True
    
    def test_get_method_with_default(self, temp_config_dir):
        """测试get方法的默认值功能"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            
            config_manager = ConfigManager()
            
            # 测试存在的配置项
            value = config_manager.get('trading', 'fee_rate', '0.002')
            assert value == '0.001'
            
            # 测试不存在的配置项
            value = config_manager.get('trading', 'nonexistent_key', 'default_value')
            assert value == 'default_value'
            
            # 测试不存在的section
            value = config_manager.get('nonexistent_section', 'key', 'default')
            assert value == 'default'
    
    def test_watch_config_changes(self, temp_config_dir):
        """测试配置文件变化监控"""
        with patch('config.config_manager.os.path.dirname') as mock_dirname:
            mock_dirname.return_value = temp_config_dir
            config_manager = ConfigManager()
            
            # 先调用一次 watch_config_changes 以同步时间戳
            config_manager.watch_config_changes()
            
            # 现在测试没有变化的情况
            result = config_manager.watch_config_changes()
            assert result is False
            
            # 修改文件
            settings_path = os.path.join(temp_config_dir, 'settings.ini')
            import time
            time.sleep(0.1)  # 确保时间差
            with open(settings_path, 'a') as f:
                f.write('\n# Test modification')
            
            # 检测变化
            result = config_manager.watch_config_changes()
            assert result is True