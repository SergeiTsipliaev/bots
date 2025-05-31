#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Класс для работы с рыночными данными криптовалют.
Получает данные с Bybit API и вычисляет технические индикаторы.
"""

import datetime
import requests
import pandas as pd
from typing import Dict, List, Optional
import warnings

from config import CONFIG
from cati_bot.utils import (
    logger,
    calculate_rsi,
    calculate_macd,
    calculate_ema
)

# Подавляем предупреждения pandas о deprecated параметрах
warnings.filterwarnings('ignore', category=FutureWarning)


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
                try:
                    await self.fetch_candles(timeframe)
                    self.calculate_indicators(timeframe)
                except Exception as e:
                    logger.error(f"Ошибка инициализации данных для {self.symbol} на таймфрейме {timeframe}: {e}")
                    continue
            
            # Определение уровней поддержки и сопротивления
            self.find_support_resistance_levels()
            logger.info(f"Данные для {self.symbol} инициализированы успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации данных для {self.symbol}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return False

    async def update(self) -> bool:
        """Метод для обновления данных"""
        try:
            logger.info(f"Обновление данных для {self.symbol}...")
            # Обновление данных по каждому таймфрейму
            for timeframe in CONFIG["timeframes"]:
                try:
                    await self.fetch_candles(timeframe)
                    self.calculate_indicators(timeframe)
                except Exception as e:
                    logger.error(f"Ошибка обновления данных для {self.symbol} на таймфрейме {timeframe}: {e}")
                    continue
            
            # Пересчет уровней поддержки и сопротивления
            self.find_support_resistance_levels()
            logger.info(f"Данные для {self.symbol} обновлены успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления данных для {self.symbol}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return False

    async def fetch_candles(self, timeframe: str) -> pd.DataFrame:
        """Метод для получения свечных данных с API биржи Bybit"""
        try:
            limit = 500  # Количество свечей для запроса
            interval = self._timeframe_to_api_interval(timeframe)
            url = f"{CONFIG['api_base_url']}/v5/market/kline"
            
            params = {
                "category": "spot",
                "symbol": self.symbol,
                "interval": interval,
                "limit": limit
            }
            
            logger.info(f"Получение свечей для {self.symbol} на таймфрейме {timeframe}...")
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Проверяем успешность запроса
            if data.get('retCode') != 0:
                logger.error(f"Ошибка API Bybit: {data.get('retMsg')}")
                raise Exception(f"Ошибка API Bybit: {data.get('retMsg')}")
            
            # Извлекаем данные свечей
            klines = data.get('result', {}).get('list', [])
            
            if not klines:
                logger.warning(f"Получен пустой список свечей для {self.symbol} на таймфрейме {timeframe}")
                return pd.DataFrame()
            
            # В Bybit API данные идут в обратном порядке (от новых к старым), переворачиваем их
            klines.reverse()
            
            # Преобразуем данные в DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'turnover'
            ])
            
            # Преобразуем типы данных
            # Исправляем deprecated warning для to_datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Устанавливаем индекс
            df.set_index('timestamp', inplace=True)
            
            # Удаляем строки с NaN значениями
            df = df.dropna()
            
            if df.empty:
                logger.warning(f"После очистки данных получен пустой DataFrame для {self.symbol} на таймфрейме {timeframe}")
                return df
            
            self.candles[timeframe] = df
            
            # Обновляем последнюю цену и дневное изменение
            if timeframe == '5m':
                self.last_price = float(df['close'].iloc[-1])
                
                # Расчет изменения за день (последние 288 5-минутных свечей или меньше если данных недостаточно)
                day_start_index = max(0, len(df) - 288)
                day_start_price = float(df['close'].iloc[day_start_index])
                if day_start_price > 0:
                    self.daily_change = ((self.last_price - day_start_price) / day_start_price) * 100
                else:
                    self.daily_change = 0
            
            logger.info(f"Получено {len(df)} свечей для {self.symbol} на таймфрейме {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Ошибка получения свечей для {self.symbol} на таймфрейме {timeframe}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            raise

    def _timeframe_to_api_interval(self, timeframe: str) -> str:
        """Вспомогательный метод для преобразования формата таймфрейма в формат API Bybit"""
        interval_map = {
            '5m': '5',
            '15m': '15',
            '1h': '60',
            '4h': '240',
            '24h': 'D',  # для дневного таймфрейма
            '24': 'D'    # альтернативный формат для дневного таймфрейма
        }
        return interval_map.get(timeframe, '5')

    def calculate_indicators(self, timeframe: str) -> None:
        """Метод для расчета технических индикаторов"""
        try:
            df = self.candles.get(timeframe)
            if df is None or df.empty:
                logger.error(f"Нет данных для расчета индикаторов ({self.symbol} - {timeframe})")
                return

            # Создаем структуру для хранения индикаторов текущего таймфрейма
            if timeframe not in self.indicators:
                self.indicators[timeframe] = {}

            # Проверяем наличие достаточного количества данных
            min_periods = max(CONFIG["rsi_period"], CONFIG["macd_slow_period"], CONFIG["ema_long"])
            if len(df) < min_periods:
                logger.warning(f"Недостаточно данных для расчета индикаторов ({self.symbol} - {timeframe}): {len(df)} < {min_periods}")
                return

            # Расчет RSI
            try:
                self.indicators[timeframe]['rsi'] = calculate_rsi(df['close'], CONFIG["rsi_period"])
            except Exception as e:
                logger.error(f"Ошибка расчета RSI для {self.symbol} на {timeframe}: {e}")
                self.indicators[timeframe]['rsi'] = pd.Series([50] * len(df), index=df.index)

            # Расчет MACD
            try:
                self.indicators[timeframe]['macd'] = calculate_macd(
                    df['close'], 
                    CONFIG["macd_fast_period"], 
                    CONFIG["macd_slow_period"], 
                    CONFIG["macd_signal_period"]
                )
            except Exception as e:
                logger.error(f"Ошибка расчета MACD для {self.symbol} на {timeframe}: {e}")
                self.indicators[timeframe]['macd'] = {
                    'macd_line': pd.Series([0] * len(df), index=df.index),
                    'signal_line': pd.Series([0] * len(df), index=df.index),
                    'histogram': pd.Series([0] * len(df), index=df.index)
                }

            # Расчет EMA
            try:
                self.indicators[timeframe]['ema_short'] = calculate_ema(df['close'], CONFIG["ema_short"])
                self.indicators[timeframe]['ema_medium'] = calculate_ema(df['close'], CONFIG["ema_medium"])
                self.indicators[timeframe]['ema_long'] = calculate_ema(df['close'], CONFIG["ema_long"])
            except Exception as e:
                logger.error(f"Ошибка расчета EMA для {self.symbol} на {timeframe}: {e}")
                self.indicators[timeframe]['ema_short'] = df['close'].copy()
                self.indicators[timeframe]['ema_medium'] = df['close'].copy()
                self.indicators[timeframe]['ema_long'] = df['close'].copy()

            # Расчет объемов
            try:
                self.indicators[timeframe]['volumes'] = df['volume'].copy()
                self.indicators[timeframe]['avg_volume'] = df['volume'].rolling(window=20, min_periods=1).mean()
            except Exception as e:
                logger.error(f"Ошибка расчета объемов для {self.symbol} на {timeframe}: {e}")
                self.indicators[timeframe]['volumes'] = pd.Series([0] * len(df), index=df.index)
                self.indicators[timeframe]['avg_volume'] = pd.Series([0] * len(df), index=df.index)

            logger.info(f"Индикаторы для {self.symbol} на таймфрейме {timeframe} рассчитаны")
        except Exception as e:
            logger.error(f"Общая ошибка расчета индикаторов для {self.symbol} на {timeframe}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")

    def find_support_resistance_levels(self) -> None:
        """Метод для определения уровней поддержки и сопротивления"""
        try:
            # Используем 4-часовой таймфрейм для определения ключевых уровней
            df = self.candles.get('4h')
            if df is None or len(df) < 30:
                logger.warning(f"Недостаточно данных для определения уровней поддержки/сопротивления для {self.symbol}")
                self.support = []
                self.resistance = []
                return
            
            # Находим локальные минимумы и максимумы
            pivot_points = []
            
            # Увеличиваем количество исследуемых свечей для поиска более глубоких уровней
            lookback_period = min(len(df) - 4, 200)  # Максимум 200 свечей или все доступные
            
            for i in range(2, lookback_period - 2):
                try:
                    # Проверка на локальный минимум
                    if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                        df['low'].iloc[i] < df['low'].iloc[i-2] and 
                        df['low'].iloc[i] < df['low'].iloc[i+1] and 
                        df['low'].iloc[i] < df['low'].iloc[i+2]):
                        pivot_points.append({
                            'price': float(df['low'].iloc[i]),
                            'type': 'support',
                            'strength': 1,
                            'date': df.index[i]
                        })
                    
                    # Проверка на локальный максимум
                    if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                        df['high'].iloc[i] > df['high'].iloc[i-2] and 
                        df['high'].iloc[i] > df['high'].iloc[i+1] and 
                        df['high'].iloc[i] > df['high'].iloc[i+2]):
                        pivot_points.append({
                            'price': float(df['high'].iloc[i]),
                            'type': 'resistance',
                            'strength': 1,
                            'date': df.index[i]
                        })
                except (IndexError, KeyError) as e:
                    logger.warning(f"Ошибка при определении пивота на позиции {i}: {e}")
                    continue
            
            # Группируем близкие уровни
            grouped_levels = self._group_levels(pivot_points)
            
            # Сортируем уровни по цене
            sorted_levels = sorted(grouped_levels, key=lambda x: x['price'])
            
            # Разделяем уровни на поддержку и сопротивление относительно текущей цены
            current_price = self.last_price if self.last_price > 0 else float(df['close'].iloc[-1])
            
            self.support = sorted([level for level in sorted_levels if level['price'] < current_price], 
                                 key=lambda x: -x['price'])  # Сортируем по убыванию (ближайшие сверху)
            
            self.resistance = sorted([level for level in sorted_levels if level['price'] > current_price], 
                                   key=lambda x: x['price'])  # Сортируем по возрастанию (ближайшие снизу)
            
            # Оставляем большее количество уровней для более глубокого анализа
            self.support = self.support[:min(10, len(self.support))]
            self.resistance = self.resistance[:min(10, len(self.resistance))]
            
            logger.info(f"Найдено {len(self.support)} уровней поддержки и {len(self.resistance)} уровней сопротивления для {self.symbol}")
        except Exception as e:
            logger.error(f"Ошибка определения уровней поддержки/сопротивления для {self.symbol}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            self.support = []
            self.resistance = []

    def _group_levels(self, levels: List[Dict]) -> List[Dict]:
        """Метод для группировки близких уровней"""
        try:
            if not levels:
                return []
                
            current_price = self.last_price if self.last_price > 0 else 1.0
            threshold = current_price * 0.005  # 0.5% как порог для группировки
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
        except Exception as e:
            logger.error(f"Ошибка группировки уровней для {self.symbol}: {e}")
            return levels