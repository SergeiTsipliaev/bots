#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурационный файл для бота анализа криптовалют.
"""

# Основные настройки
CONFIG = {
    # API настройки
    "api_base_url": "https://api.bybit.com",

    # Символы для анализа
    "default_symbol": "BTCUSDT",
    "available_symbols": [
        "CATIUSDT",  # Catizen
        "TONUSDT",  # Toncoin
        "BTCUSDT",  # Bitcoin
        "ETHUSDT",  # Ethereum
        "MATICUSDT",  # Polygon
        "DOTUSDT",  # Polkadot
        "ADAUSDT",  # Cardano
        "SOLUSDT",  # Solana
        "LINKUSDT",  # Chainlink
        "AVAXUSDT",  # Avalanche
        "LTCUSDT",  # Litecoin
        "UNIUSDT",  # Uniswap
        "ATOMUSDT",  # Cosmos
        "XLMUSDT",  # Stellar
        "VETUSDT",  # VeChain
        "XRPUSDT",  # Ripple
        "TRXUSDT",  # TRON
        "EOSUSDT",  # EOS
        "ALGOUSDT",  # Algorand
        "MANAUSDT"  # Decentraland
    ],

    # Таймфреймы для анализа
    "timeframes": ["5m", "15m", "1h", "4h"],

    # Временные настройки
    "time_interval_minutes": 0.5,  # Интервал обновления данных в минутах

    # Параметры индикаторов
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "macd_fast_period": 12,
    "macd_slow_period": 26,
    "macd_signal_period": 9,
    "ema_short": 9,
    "ema_medium": 21,
    "ema_long": 50,
    "vol_multiplier": 1.5,  # Множитель для определения повышенного объема

    # Параметры риск-менеджмента
    "stop_loss_percent": 3,  # Процент стоп-лосса по умолчанию
    "take_profit_percent": 10,  # Процент тейк-профита по умолчанию

    # Параметры для долгосрочного анализа
    "long_term_analysis": True,  # Включен ли долгосрочный анализ
    "support_resistance_lookback": 200,  # Количество свечей для поиска уровней
    "volatility_multiplier": 1.5,  # Множитель для расчета волатильности в прогнозе
    "trend_impact_factor": 0.7,  # Степень влияния тренда на прогноз (0-1)

    # Настройки типов сигналов
    "signal_types": ["SHORT", "LONG", "ALL"],
    "default_signal_type": "ALL",

    # Минимальная уверенность для разных типов сигналов
    "short_term_confidence": 0.6,  # 60% для краткосрочных
    "long_term_confidence": 0.5,  # 50% для долгосрочных
    "all_term_confidence": 0.6,  # 60% для общих

    # Telegram настройки
    "telegram_bot_token": "8139148387:AAE9DPDxII-osu5QlwET_KmNkE3ulUCTPyA",  # Вставьте ваш токен бота здесь
    "telegram_chat_id": "845124301",  # Вставьте ваш chat ID здесь
    "always_send_to_main_chat": True,  # Всегда отправлять копию в основной чат

    # Настройки логирования
    "log_file": "logs/cati_bot.log",
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# Описания монет для удобства пользователей
COIN_DESCRIPTIONS = {
    "CATIUSDT": "Catizen - игровая экосистема в Telegram",
    "TONUSDT": "Toncoin - блокчейн от команды Telegram",
    "BTCUSDT": "Bitcoin - первая и самая популярная криптовалюта",
    "ETHUSDT": "Ethereum - платформа для смарт-контрактов",
    "MATICUSDT": "Polygon - решение масштабирования для Ethereum",
    "DOTUSDT": "Polkadot - протокол для соединения блокчейнов",
    "ADAUSDT": "Cardano - блокчейн-платформа третьего поколения",
    "SOLUSDT": "Solana - высокопроизводительный блокчейн",
    "LINKUSDT": "Chainlink - децентрализованная сеть оракулов",
    "AVAXUSDT": "Avalanche - быстрая и масштабируемая платформа",
    "LTCUSDT": "Litecoin - цифровое серебро",
    "UNIUSDT": "Uniswap - ведущий DEX на Ethereum",
    "ATOMUSDT": "Cosmos - интернет блокчейнов",
    "XLMUSDT": "Stellar - платформа для международных платежей",
    "VETUSDT": "VeChain - блокчейн для цепочек поставок",
    "XRPUSDT": "Ripple - система для международных переводов",
    "TRXUSDT": "TRON - платформа для децентрализованного интернета",
    "EOSUSDT": "EOS - операционная система для блокчейнов",
    "ALGOUSDT": "Algorand - чистый proof-of-stake блокчейн",
    "MANAUSDT": "Decentraland - виртуальный мир на блокчейне"
}

# Описания типов сигналов
SIGNAL_TYPE_DESCRIPTIONS = {
    "SHORT": "Краткосрочные сигналы (до 24 часов)",
    "LONG": "Долгосрочные сигналы (от 1 дня до недели)",
    "ALL": "Все типы сигналов"
}