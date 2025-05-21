#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Пример использования официального SDK PyBit для работы с API Bybit.
Этот файл служит примером и не используется в основном коде бота.
"""

from pybit.unified_trading import HTTP
import pandas as pd
import time
from typing import List, Dict, Any

# Создание экземпляра клиента API Bybit (публичное API, без аутентификации)
session = HTTP(
    testnet=False,  # False для основной сети, True для тестовой
    api_key=None,    # Не требуется для публичных запросов
    api_secret=None  # Не требуется для публичных запросов
)

def get_klines(symbol: str, interval: str = "5", limit: int = 500) -> pd.DataFrame:
    """
    Получение свечных данных с использованием PyBit SDK
    
    Args:
        symbol: Символ криптовалюты (например, "BTCUSDT")
        interval: Интервал свечей (например, "5" для 5 минут)
        limit: Количество свечей (максимум 1000)
        
    Returns:
        DataFrame со свечными данными
    """
    try:
        # Выполнение запроса к API
        response = session.get_kline(
            category="spot",  # "spot" для спотовой торговли
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        # Проверка успешности запроса
        if response.get('retCode') != 0:
            print(f"Ошибка API Bybit: {response.get('retMsg')}")
            return pd.DataFrame()
        
        # Извлечение данных свечей
        klines = response.get('result', {}).get('list', [])
        
        # В Bybit API данные идут в обратном порядке (от новых к старым), переворачиваем их
        klines.reverse()
        
        # Преобразуем данные в DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 
            'volume', 'turnover'
        ])
        
        # Преобразуем типы данных
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover']
        df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
        
        # Устанавливаем индекс
        df.set_index('timestamp', inplace=True)
        
        return df
    except Exception as e:
        print(f"Ошибка при получении свечей: {e}")
        return pd.DataFrame()

def get_ticker_price(symbol: str) -> float:
    """
    Получение текущей цены актива
    
    Args:
        symbol: Символ криптовалюты (например, "BTCUSDT")
        
    Returns:
        Текущая цена или 0 в случае ошибки
    """
    try:
        response = session.get_tickers(
            category="spot",
            symbol=symbol
        )
        
        if response.get('retCode') != 0:
            print(f"Ошибка API Bybit: {response.get('retMsg')}")
            return 0
        
        ticker_info = response.get('result', {}).get('list', [])
        if not ticker_info:
            return 0
        
        return float(ticker_info[0].get('lastPrice', 0))
    except Exception as e:
        print(f"Ошибка при получении цены: {e}")
        return 0

def get_available_symbols() -> List[str]:
    """
    Получение списка доступных символов на бирже
    
    Returns:
        Список доступных символов
    """
    try:
        response = session.get_instruments_info(
            category="spot"
        )
        
        if response.get('retCode') != 0:
            print(f"Ошибка API Bybit: {response.get('retMsg')}")
            return []
        
        symbols_info = response.get('result', {}).get('list', [])
        
        # Извлекаем только названия символов
        symbols = [item.get('symbol') for item in symbols_info if item.get('symbol')]
        
        return symbols
    except Exception as e:
        print(f"Ошибка при получении списка символов: {e}")
        return []

def get_server_time() -> str:
    """
    Получение текущего времени сервера Bybit
    
    Returns:
        Строка с текущим временем сервера
    """
    try:
        response = session.get_server_time()
        
        if response.get('retCode') != 0:
            print(f"Ошибка API Bybit: {response.get('retMsg')}")
            return "Ошибка получения времени"
        
        # Время в миллисекундах с начала эпохи
        timestamp_ms = int(response.get('result', {}).get('timeSecond', 0)) * 1000
        
        # Преобразуем в читаемый формат
        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp_ms / 1000))
        
        return time_str
    except Exception as e:
        print(f"Ошибка при получении времени сервера: {e}")
        return "Ошибка получения времени"


if __name__ == "__main__":
    # Пример использования функций
    
    # Получаем список доступных символов
    symbols = get_available_symbols()
    print(f"Доступно {len(symbols)} символов. Первые 10: {symbols[:10]}")
    
    # Получаем текущую цену Bitcoin
    btc_price = get_ticker_price("BTCUSDT")
    print(f"Текущая цена Bitcoin: {btc_price}")
    
    # Получаем свечные данные для Bitcoin
    btc_klines = get_klines("BTCUSDT", interval="60", limit=10)  # 1-часовые свечи, последние 10
    print("\nПоследние свечи Bitcoin:")
    print(btc_klines)
    
    # Получаем время сервера
    server_time = get_server_time()
    print(f"\nВремя сервера Bybit: {server_time}")