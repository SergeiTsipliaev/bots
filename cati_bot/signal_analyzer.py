#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Класс для анализа торговых сигналов криптовалют.
Анализирует рыночные данные и генерирует торговые сигналы.
"""

import datetime
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

from config import CONFIG
from cati_bot.utils import logger
from cati_bot.market_data import MarketData


class SignalAnalyzer:
    """Класс для анализа торговых сигналов"""

    def __init__(self, market_data: MarketData):
        self.market_data = market_data
        self.symbol = market_data.symbol
        self.signals = {}  # Хранилище сигналов по разным таймфреймам
        self.trend = {
            # Тренды по разным таймфреймам
            '5m': 'неопределен',
            '15m': 'неопределен',
            '1h': 'неопределен',
            '4h': 'неопределен',
            'общий': 'неопределен'
        }
        self.last_signal = None  # Последний сгенерированный сигнал
        self.price_predictions = {}  # Прогнозы цен на разные периоды
        self.long_term_targets = {}  # Долгосрочные целевые уровни
        self.market_cycles = {}  # Определение циклов рынка для долгосрочного анализа

    def _analyze_trend(self, timeframe: str) -> None:
        """Метод для определения тренда на конкретном таймфрейме"""
        try:
            indicators = self.market_data.indicators.get(timeframe)
            if not indicators:
                return
            
            # Получаем последние значения индикаторов
            ema_short = indicators['ema_short'].iloc[-1]
            ema_medium = indicators['ema_medium'].iloc[-1]
            ema_long = indicators['ema_long'].iloc[-1]
            
            # Проверка EMA
            short_above_medium = ema_short > ema_medium
            medium_above_long = ema_medium > ema_long
            short_above_long = ema_short > ema_long
            
            # Расчет силы тренда
            trend_strength = 0
            if short_above_medium: trend_strength += 1
            if medium_above_long: trend_strength += 1
            if short_above_long: trend_strength += 1
            
            # Определение тренда
            if trend_strength == 3:
                self.trend[timeframe] = 'восходящий'
            elif trend_strength == 0:
                self.trend[timeframe] = 'нисходящий'
            else:
                self.trend[timeframe] = 'смешанный'
            
            logger.info(f"Тренд {self.symbol} на таймфрейме {timeframe}: {self.trend[timeframe]}")
        except Exception as e:
            logger.error(f"Ошибка в _analyze_trend для {self.symbol} на таймфрейме {timeframe}: {e}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            # Установим безопасное значение по умолчанию
            self.trend[timeframe] = 'неопределен'

    def analyze(self, signal_type: str = "ALL") -> bool:
        """
        Метод для анализа данных и генерации сигналов
        
        Args:
            signal_type: Тип сигнала для генерации (SHORT, LONG, ALL)
            
        Returns:
            bool: True если сигнал сгенерирован, False в противном случае
        """
        try:
            logger.info(f"Анализ рыночных данных для {self.symbol} (тип сигнала: {signal_type})...")
            
            # Определение тренда на разных таймфреймах
            for timeframe in CONFIG["timeframes"]:
                self._analyze_trend(timeframe)
                self._find_signals(timeframe)
            
            # Определение общего тренда
            self._determine_overall_trend()
            
            # Анализ циклов рынка и долгосрочного тренда
            self._analyze_market_cycles()
            
            # Прогнозирование цен на разные периоды
            self._predict_future_prices()
            
            # Определение долгосрочных целевых уровней
            self._set_long_term_targets()
            
            # Генерация торгового сигнала в зависимости от типа
            if signal_type == "SHORT":
                self.last_signal = self._generate_short_term_signal()
            elif signal_type == "LONG":
                self.last_signal = self._generate_long_term_signal()
            else:  # "ALL" и любые другие значения
                self.last_signal = self._generate_trade_signal()
            
            logger.info(f"Анализ {self.symbol} завершен")
            
            # Если сгенерирован сигнал, возвращаем True
            return self.last_signal is not None
        except Exception as e:
            logger.error(f"Ошибка анализа {self.symbol}: {e}")
            return False
    
    def _analyze_market_cycles(self) -> None:
        """Метод для анализа рыночных циклов и определения фазы рынка"""
        try:
            # Используем 4-часовой таймфрейм для долгосрочного анализа
            timeframe = '4h'
            df = self.market_data.candles.get(timeframe)
            if df is None or len(df) < 30:
                return

            # Получаем индикаторы
            indicators = self.market_data.indicators.get(timeframe)
            if not indicators:
                return
            
            # Получаем последние значения RSI
            rsi = indicators['rsi']
            current_rsi = rsi.iloc[-1]
            
            # Получаем последние значения MACD
            macd = indicators['macd']
            macd_line = macd['macd_line'].iloc[-1]
            signal_line = macd['signal_line'].iloc[-1]
            
            # Получаем цены закрытия
            closes = df['close']
            price_20_periods_ago = closes.iloc[-21] if len(closes) > 20 else closes.iloc[0]
            current_price = closes.iloc[-1]
            
            # Расчет изменения цены за последние 20 периодов (для 4h это примерно 3-4 дня)
            price_change_percent = ((current_price - price_20_periods_ago) / price_20_periods_ago) * 100
            
            # Определяем фазу рынка на основе индикаторов и ценового движения
            if current_rsi > 60 and macd_line > signal_line and price_change_percent > 5:
                # Признаки бычьего тренда
                market_phase = "бычий"
                confidence = min(0.5 + abs(price_change_percent) / 20, 0.9)  # Максимум 90% уверенности
            elif current_rsi < 40 and macd_line < signal_line and price_change_percent < -5:
                # Признаки медвежьего тренда
                market_phase = "медвежий"
                confidence = min(0.5 + abs(price_change_percent) / 20, 0.9)
            elif 40 <= current_rsi <= 60 and abs(price_change_percent) < 3:
                # Признаки бокового тренда
                market_phase = "боковой"
                confidence = 0.7
            else:
                # Переходная фаза или неопределенное состояние
                market_phase = "переходный"
                confidence = 0.5
            
            # Определяем возможные циклические паттерны
            cycle_patterns = []
            
            # Проверка на возможное дно (перепроданность + разворот)
            if current_rsi < 30 and rsi.iloc[-2] < rsi.iloc[-1] and macd_line > signal_line:
                cycle_patterns.append({
                    "pattern": "возможное дно",
                    "confidence": 0.6,
                    "description": "Признаки разворота от перепроданности"
                })
            
            # Проверка на возможную вершину (перекупленность + разворот)
            if current_rsi > 70 and rsi.iloc[-2] > rsi.iloc[-1] and macd_line < signal_line:
                cycle_patterns.append({
                    "pattern": "возможная вершина",
                    "confidence": 0.6,
                    "description": "Признаки разворота от перекупленности"
                })
            
            # Проверка на продолжение тренда
            if (self.trend[timeframe] == "восходящий" and current_rsi > 50 and 
                macd_line > signal_line and price_change_percent > 0):
                cycle_patterns.append({
                    "pattern": "продолжение восходящего тренда",
                    "confidence": 0.7,
                    "description": "Признаки продолжения бычьего тренда"
                })
            
            if (self.trend[timeframe] == "нисходящий" and current_rsi < 50 and 
                macd_line < signal_line and price_change_percent < 0):
                cycle_patterns.append({
                    "pattern": "продолжение нисходящего тренда",
                    "confidence": 0.7,
                    "description": "Признаки продолжения медвежьего тренда"
                })
            
            # Сохраняем результаты анализа
            self.market_cycles = {
                "phase": market_phase,
                "confidence": confidence,
                "patterns": cycle_patterns,
                "price_change_percent": price_change_percent
            }
            
            logger.info(f"Рыночная фаза для {self.symbol}: {market_phase} (уверенность: {confidence*100:.1f}%)")
            
        except Exception as e:
            logger.error(f"Ошибка анализа рыночных циклов для {self.symbol}: {e}")
            self.market_cycles = {
                "phase": "неопределенный",
                "confidence": 0.0,
                "patterns": [],
                "price_change_percent": 0.0
            }

    def _predict_future_prices(self) -> None:
        """Метод для прогнозирования цен на будущие периоды"""
        try:
            # Используем различные таймфреймы для разных периодов прогноза
            # 1h для краткосрочного прогноза, 4h для среднесрочного
            predictions = {}
            
            # Краткосрочный прогноз (2-6 часов)
            short_term = self._calculate_price_prediction('1h', hours=6)
            predictions["short_term"] = short_term
            
            # Среднесрочный прогноз (12-24 часа)
            medium_term = self._calculate_price_prediction('4h', hours=24)
            predictions["medium_term"] = medium_term
            
            # Долгосрочный прогноз (2-7 дней)
            long_term = self._calculate_price_prediction('4h', hours=168)  # 7 дней
            predictions["long_term"] = long_term
            
            self.price_predictions = predictions
            
            logger.info(f"Прогнозы цен для {self.symbol}:")
            logger.info(f"Краткосрочный (6ч): {short_term['min']:.6f} - {short_term['max']:.6f}")
            logger.info(f"Среднесрочный (24ч): {medium_term['min']:.6f} - {medium_term['max']:.6f}")
            logger.info(f"Долгосрочный (7д): {long_term['min']:.6f} - {long_term['max']:.6f}")
            
        except Exception as e:
            logger.error(f"Ошибка прогнозирования цен для {self.symbol}: {e}")
            self.price_predictions = {
                "short_term": {"min": 0, "max": 0, "expected": 0, "confidence": 0},
                "medium_term": {"min": 0, "max": 0, "expected": 0, "confidence": 0},
                "long_term": {"min": 0, "max": 0, "expected": 0, "confidence": 0}
            }