#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Технические индикаторы для анализа рынка CATIUSDT.
"""

import pandas as pd
import numpy as np


def calculate_rsi(prices: pd.Series, period: int) -> pd.Series:
    """
    Рассчитывает индикатор RSI (Relative Strength Index)
    
    Args:
        prices: Серия цен закрытия
        period: Период RSI
        
    Returns:
        Серия значений RSI
    """
    delta = prices.diff()
    
    # Получаем только положительные и отрицательные изменения
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Рассчитываем среднее изменение
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    # Рассчитываем относительную силу
    rs = avg_gain / avg_loss.replace(0, 1e-10)  # Избегаем деления на ноль
    
    # Рассчитываем RSI
    rsi = 100 - (100 / (1 + rs))
    
    # Заполняем NaN значения нейтральным значением 50
    rsi = rsi.fillna(50)
    
    return rsi


def calculate_macd(prices: pd.Series, fast_period: int, slow_period: int, signal_period: int) -> dict:
    """
    Рассчитывает индикатор MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: Серия цен закрытия
        fast_period: Период быстрой EMA
        slow_period: Период медленной EMA
        signal_period: Период сигнальной линии
        
    Returns:
        Словарь с линией MACD, сигнальной линией и гистограммой
    """
    # Рассчитываем EMA
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)
    
    # Рассчитываем линию MACD
    macd_line = fast_ema - slow_ema
    
    # Рассчитываем сигнальную линию
    signal_line = macd_line.rolling(window=signal_period).mean()
    
    # Рассчитываем гистограмму
    histogram = macd_line - signal_line
    
    return {
        'macd_line': macd_line,
        'signal_line': signal_line,
        'histogram': histogram
    }


def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
    """
    Рассчитывает Экспоненциальную скользящую среднюю (EMA)
    
    Args:
        prices: Серия цен закрытия
        period: Период EMA
        
    Returns:
        Серия значений EMA
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
    """
    Рассчитывает Простую скользящую среднюю (SMA)
    
    Args:
        prices: Серия цен закрытия
        period: Период SMA
        
    Returns:
        Серия значений SMA
    """
    return prices.rolling(window=period).mean()