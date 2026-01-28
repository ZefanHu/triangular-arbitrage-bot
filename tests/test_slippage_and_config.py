import configparser

import pytest

from config.config_manager import ConfigManager
from core.arbitrage_engine import ArbitrageEngine


class DummyCollector:
    def get_orderbook(self, pair):
        return None


def test_slippage_reduces_profit():
    engine = ArbitrageEngine(DummyCollector())
    order_book = {
        'asks': [(100.0, 1.0)],
        'bids': [(99.0, 1.0)]
    }
    trade_steps = [
        {'pair': 'BTC-USDT', 'action': 'buy', 'order_book': order_book},
        {'pair': 'BTC-USDT', 'action': 'sell', 'order_book': order_book}
    ]

    engine.slippage_tolerance = 0.0
    _, profit_without_slippage = engine.calculate_path_profit_from_steps(trade_steps, 100.0)

    engine.slippage_tolerance = 0.01
    _, profit_with_slippage = engine.calculate_path_profit_from_steps(trade_steps, 100.0)

    assert profit_with_slippage < profit_without_slippage


def test_unknown_key_fails_fast():
    config_manager = ConfigManager()
    original_config = config_manager.config

    temp_config = configparser.ConfigParser()
    temp_config['trading'] = {
        'fee_rate': '0.001',
        'slippage_tolerance': '0.001',
        'unknown_key': '1'
    }
    temp_config['system'] = {
        'log_level': 'INFO'
    }

    try:
        config_manager.config = temp_config
        with pytest.raises(ValueError, match="未知配置项"):
            config_manager.validate_config()
    finally:
        config_manager.config = original_config
