#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Класс для работы с рыночными данными криптовалют.
Получает данные с Binance API и вычисляет технические индикаторы.
"""

import datetime
import requests
import pandas as pd
from typing import Dict, List, Optional

from config import CONFIG
from cati_bot.utils import (
    logger,
    calculate_rsi,
    calculate_macd,
    calculate_ema
)


class MarketData:
    """Класс для хранения исторических данных цен и индикаторов"""

    def __init__(self, symbol: str = None):
        self.symbol = symbol or CONFIG["default_symbol"]
        self.candles = {}  # Хранилище для свечей по разным таймфреймам
        self.indicators = {}  # Хранилище для рассчитанных индикаторов
        self.support = []  # Уровни поддержки
        self.resistance = []  # Уровни сопротивления
        self.last_price = 0  # Последняя цена
        self.daily_change = 0  # Изменение цены за день (%)

    async def initialize(self) -> bool:
        """Метод для инициализации исторических данных"""
        try:
            logger.info(f"Инициализация данных для {self.symbol}...")
            # Загрузка данных по каждому таймфрейму
            for timeframe in CONFIG["timeframes"]:
                await self.fetch_candles(timeframe)
                self.calculate_indicators(timeframe)
            
            # Определение уровней поддержки и сопротивления
            self.find_support_resistance_levels()
            logger.info(f"Данные для {self.symbol} инициализированы успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации данных для {self.symbol}: {e}")
            return False

    async def update(self) -> bool:
        """Метод для обновления данных"""
        try:
            logger.info(f"Обновление данных для {self.symbol}...")
            # Обновление данных по каждому таймфрейму
            for timeframe in CONFIG["timeframes"]:
                await self.fetch_candles(timeframe)
                self.calculate_indicators(timeframe)
            
            # Пересчет уровней поддержки и сопротивления
            self.find_support_resistance_levels()
            logger.info(f"Данные для {self.symbol} обновлены успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления данных для {self.symbol}: {e}")
            return False

    async def fetch_candles(self, timeframe: str) -> pd.DataFrame:
        """Метод для получения свечных данных с API биржи"""
        try:
            limit = 500  # Количество свечей для запроса
            interval = self._timeframe_to_api_interval(timeframe)
            url = f"{CONFIG['api_base_url']}/api/v3/klines"
            params = {
                "symbol": self.symbol,
                "interval": interval,
                "limit": limit
            }
            
            logger.info(f"Получение свечей для {self.symbol} на таймфрейме {timeframe}...")
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_asset_volume',
                'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Преобразуем типы данных
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric)
            
            # Устанавливаем индекс
            df.set_index('timestamp', inplace=True)
            
            self.candles[timeframe] = df
            
            # Обновляем последнюю цену и дневное изменение
            if timeframe == '5m':
                self.last_price = df['close'].iloc[-1]
                
                # Расчет изменения за день (последние 288 5-минутных свечей или меньше если данных недостаточно)
                day_start_index = max(0, len(df) - 288)
                day_start_price = df['close'].iloc[day_start_index]
                self.daily_change = ((self.last_price - day_start_price) / day_start_price) * 100
            
            logger.info(f"Получено {len(df)} свечей для {self.symbol} на таймфрейме {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Ошибка получения свечей для {self.symbol} на таймфрейме {timeframe}: {e}")
            raise

    def _timeframe_to_api_interval(self, timeframe: str) -> str:
        """Вспомогательный метод для преобразования формата таймфрейма в формат API Binance"""
        interval_map = {
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h'
        }
        return interval_map.get(timeframe, '5m')

    def calculate_indicators(self, timeframe: str) -> None:
        """Метод для расчета технических индикаторов"""
        df = self.candles.get(timeframe)
        if df is None or df.empty:
            logger.error(f"Нет данных для расчета индикаторов ({self.symbol} - {timeframe})")
            return

        # Создаем структуру для хранения индикаторов текущего таймфрейма
        if timeframe not in self.indicators:
            self.indicators[timeframe] = {}

        # Расчет RSI
        self.indicators[timeframe]['rsi'] = calculate_rsi(df['close'], CONFIG["rsi_period"])

        # Расчет MACD
        self.indicators[timeframe]['macd'] = calculate_macd(
            df['close'], 
            CONFIG["macd_fast_period"], 
            CONFIG["macd_slow_period"], 
            CONFIG["macd_signal_period"]
        )

        # Расчет EMA
        self.indicators[timeframe]['ema_short'] = calculate_ema(df['close'], CONFIG["ema_short"])
        self.indicators[timeframe]['ema_medium'] = calculate_ema(df['close'], CONFIG["ema_medium"])
        self.indicators[timeframe]['ema_long'] = calculate_ema(df['close'], CONFIG["ema_long"])

        # Расчет объемов
        self.indicators[timeframe]['volumes'] = df['volume']
        self.indicators[timeframe]['avg_volume'] = df['volume'].rolling(window=20).mean()

        logger.info(f"Индикаторы для {self.symbol} на таймфрейме {timeframe} рассчитаны")

    def find_support_resistance_levels(self) -> None:
        """Метод для определения уровней поддержки и сопротивления"""
        # Используем 4-часовой таймфрейм для определения ключевых уровней
        df = self.candles.get('4h')
        if df is None or len(df) < 30:
            return
        
        # Находим локальные минимумы и максимумы
        pivot_points = []
        
        for i in range(2, len(df) - 2):
            # Проверка на локальный минимум
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i-2] and 
                df['low'].iloc[i] < df['low'].iloc[i+1] and 
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                pivot_points.append({
                    'price': df['low'].iloc[i],
                    'type': 'support',
                    'strength': 1
                })
            
            # Проверка на локальный максимум
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i-2] and 
                df['high'].iloc[i] > df['high'].iloc[i+1] and 
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                pivot_points.append({
                    'price': df['high'].iloc[i],
                    'type': 'resistance',
                    'strength': 1
                })
        
        # Группируем близкие уровни
        grouped_levels = self._group_levels(pivot_points)
        
        # Сортируем уровни по цене
        sorted_levels = sorted(grouped_levels, key=lambda x: x['price'])
        
        # Разделяем уровни на поддержку и сопротивление относительно текущей цены
        current_price = self.last_price
        
        self.support = sorted([level for level in sorted_levels if level['price'] < current_price], 
                             key=lambda x: -x['price'])  # Сортируем по убыванию (ближайшие сверху)
        
        self.resistance = sorted([level for level in sorted_levels if level['price'] > current_price], 
                               key=lambda x: x['price'])  # Сортируем по возрастанию (ближайшие сверху)

    def _group_levels(self, levels: List[Dict]) -> List[Dict]:
        """Метод для группировки близких уровней"""
        if not levels:
            return []
            
        threshold = self.last_price * 0.005  # 0.5% как порог для группировки
        grouped = []
        
        levels_copy = levels.copy()
        
        while levels_copy:
            current = levels_copy.pop(0)
            similar_levels = [l for l in levels_copy if abs(l['price'] - current['price']) < threshold and l['type'] == current['type']]
            
            # Удаляем найденные похожие уровни из основного массива
            for level in similar_levels:
                if level in levels_copy:
                    levels_copy.remove(level)
            
            # Объединяем данные
            total_strength = current['strength'] + sum(level['strength'] for level in similar_levels)
            total_price = (current['price'] * current['strength'] + 
                          sum(level['price'] * level['strength'] for level in similar_levels)) / total_strength
            
            grouped.append({
                'price': total_price,
                'type': current['type'],
                'strength': total_strength
            })
        
        return grouped