#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурационный файл для бота анализа криптовалют.
Содержит все настройки и параметры бота.
"""

# Основные настройки бота
CONFIG = {
    "default_symbol": "CATIUSDT",  # Символ по умолчанию
    "available_symbols": [
        "TONUSDT",    # Toncoin
        "ETHUSDT",    # Ethereum
        "XRPUSDT",    # Ripple
        "BNBUSDT",    # Binance Coin
        "DOGEUSDT",   # Dogecoin
        "SOLUSDT",    # Solana
        "AVAXUSDT",   # Avalanche
        "BTCUSDT",    # Bitcoin
        "ADAUSDT",    # Cardano
        "CATIUSDT",   # Catizen
        # Добавленные новые монеты
        "MATICUSDT",  # Polygon
        "DOTUSDT",    # Polkadot
        "LTCUSDT",    # Litecoin
        "LINKUSDT",   # Chainlink
        "ATOMUSDT",   # Cosmos
        "UNIUSDT",    # Uniswap
        "AAVEUSDT",   # Aave
        "SHIBUSDT",   # Shiba Inu
        "APTUSDT",    # Aptos
        "NEARUSDT",   # NEAR Protocol
    ],
    "time_interval_minutes": 0.5,
    "timeframes": ["5m", "15m", "1h", "4h", "24"],
    
    # Настройки индикаторов
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "macd_fast_period": 12,
    "macd_slow_period": 26,
    "macd_signal_period": 9,
    "ema_short": 9,
    "ema_medium": 21,
    "ema_long": 50,
    "vol_multiplier": 2.0,  # Множитель для определения всплеска объема
    
    # Настройки для управления рисками
    "stop_loss_percent": 1,  # Процент для стоп-лосса
    "take_profit_percent": 9,  # Процент для тейк-профита
    
    # API и уведомления
    "api_base_url": "https://api.bybit.com",  # Базовый URL API Bybit
    "telegram_bot_token": "8117006241:AAHMbaFLvDEnMzQnWpFnq2AAyj4Wa1ae_CU",  # Заменить на свой токен 
    "telegram_chat_id": "845124301",  # Заменить на свой ID чата -1002690491295
    
    # Настройки логирования
    "log_level": "INFO",
    "log_file": "logs/crypto_bot.log",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# Описания монет для помощи пользователям
COIN_DESCRIPTIONS = {
    "CATIUSDT": "Catizen (CATI) - токен игровой платформы на Telegram",
    "TONUSDT": "Toncoin (TON) - криптовалюта экосистемы TON (Telegram Open Network)",
    "BTCUSDT": "Bitcoin (BTC) - первая и крупнейшая криптовалюта",
    "ETHUSDT": "Ethereum (ETH) - платформа для смарт-контрактов и decentralized apps",
    "XRPUSDT": "Ripple (XRP) - цифровая валюта для платежных систем",
    "BNBUSDT": "Binance Coin (BNB) - нативный токен биржи Binance",
    "DOGEUSDT": "Dogecoin (DOGE) - мем-криптовалюта, первоначально созданная как шутка",
    "SOLUSDT": "Solana (SOL) - блокчейн с высокой пропускной способностью",
    "ADAUSDT": "Cardano (ADA) - proof-of-stake блокчейн с научным подходом",
    "AVAXUSDT": "Avalanche (AVAX) - платформа для децентрализованных приложений",
    # Описания для новых монет
    "MATICUSDT": "Polygon (MATIC) - решение для масштабирования Ethereum уровня 2",
    "DOTUSDT": "Polkadot (DOT) - платформа для взаимодействия разных блокчейнов",
    "LTCUSDT": "Litecoin (LTC) - одна из первых альткоинов, форк Bitcoin с быстрыми транзакциями",
    "LINKUSDT": "Chainlink (LINK) - децентрализованная сеть оракулов для смарт-контрактов",
    "ATOMUSDT": "Cosmos (ATOM) - экосистема взаимосвязанных блокчейнов",
    "UNIUSDT": "Uniswap (UNI) - децентрализованная биржа на Ethereum",
    "AAVEUSDT": "Aave (AAVE) - протокол кредитования и заимствования DeFi",
    "SHIBUSDT": "Shiba Inu (SHIB) - мем-токен экосистемы Ethereum",
    "APTUSDT": "Aptos (APT) - блокчейн первого уровня с высокой производительностью",
    "NEARUSDT": "NEAR Protocol (NEAR) - платформа для создания децентрализованных приложений"
}