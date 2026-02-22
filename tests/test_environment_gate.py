import asyncio

from main import TradingBot


def test_monitor_mode_allows_missing_api_credentials(monkeypatch):
    bot = TradingBot()

    monkeypatch.setattr(bot.config_manager, "get_api_credentials", lambda: None)
    monkeypatch.setattr(bot.config_manager, "get_trading_config", lambda: {"parameters": {}})

    assert asyncio.run(bot.check_environment("monitor")) is True


def test_auto_mode_rejects_missing_api_credentials(monkeypatch):
    bot = TradingBot()

    monkeypatch.setattr(bot.config_manager, "get_api_credentials", lambda: None)
    monkeypatch.setattr(bot.config_manager, "get_trading_config", lambda: {"parameters": {}})

    assert asyncio.run(bot.check_environment("auto")) is False


def test_auto_mode_accepts_configured_api_credentials(monkeypatch):
    bot = TradingBot()

    monkeypatch.setattr(
        bot.config_manager,
        "get_api_credentials",
        lambda: {"api_key": "k", "secret_key": "s", "passphrase": "p"},
    )
    monkeypatch.setattr(bot.config_manager, "get_trading_config", lambda: {"parameters": {}})

    assert asyncio.run(bot.check_environment("auto")) is True
