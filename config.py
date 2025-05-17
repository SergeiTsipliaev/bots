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
        # "ETHUSDT",    # Ethereum
        "XRPUSDT",    # Ripple
        "BNBUSDT",    # Binance Coin
        "DOGEUSDT",   # Dogecoin
        "SOLUSDT",    # Solana
        "AVAXUSDT",   # Avalanche
        "BTCUSDT",    # Bitcoin
        "ADAUSDT",    # Cardano
        "CATIUSDT",   # Catizen
    ],
    "time_interval_minutes": 1,
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
    "stop_loss_percent": 1.5,  # Процент для стоп-лосса
    "take_profit_percent": 9,  # Процент для тейк-профита
    
    # API и уведомления
    "api_base_url": "https://api.binance.com",
    "telegram_bot_token": "8117006241:AAHMbaFLvDEnMzQnWpFnq2AAyj4Wa1ae_CU",  # Заменить на свой токен
    "telegram_chat_id": "-1002690491295",  # Заменить на свой ID чата
    
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
    "AVAXUSDT": "Avalanche (AVAX) - платформа для децентрализованных приложений"
}