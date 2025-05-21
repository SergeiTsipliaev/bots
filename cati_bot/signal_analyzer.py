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
        self.last_signal = None  # Последний сигeнерированный сигнал
        self.price_predictions = {}  # Прогнозы цен на разные периоды
        self.long_term_targets = {}  # Долгосрочные целевые уровни
        self.market_cycles = {}  # Определение циклов рынка для долгосрочного анализа

    def analyze(self) -> bool:
        """Метод для анализа данных и генерации сигналов"""
        try:
            logger.info(f"Анализ рыночных данных для {self.symbol}...")
            
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
            
            # Генерация торгового сигнала
            self._generate_trade_signal()
            
            logger.info(f"Анализ {self.symbol} завершен")
            return True
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

    def _calculate_price_prediction(self, timeframe: str, hours: int) -> Dict[str, float]:
        """
        Метод для расчета прогноза цены на указанное количество часов вперед
        
        Args:
            timeframe: Таймфрейм для анализа
            hours: Количество часов для прогноза
            
        Returns:
            Словарь с прогнозом цены
        """
        df = self.market_data.candles.get(timeframe)
        if df is None or len(df) < 30:
            return {"min": 0, "max": 0, "expected": 0, "confidence": 0}
        
        current_price = df['close'].iloc[-1]
        
        # Получаем индикаторы
        indicators = self.market_data.indicators.get(timeframe)
        if not indicators:
            return {"min": 0, "max": 0, "expected": 0, "confidence": 0}
        
        # Рассчитываем волатильность (стандартное отклонение в процентах)
        volatility = df['close'].pct_change().std() * 100
        
        # Корректируем прогноз на основе временного горизонта и волатильности
        # Чем дольше период и выше волатильность, тем шире коридор прогноза
        time_factor = np.sqrt(hours / int(timeframe.replace('h', ''))) if 'h' in timeframe else np.sqrt(hours / 1)
        volatility_adjusted = volatility * time_factor
        
        # Рассчитываем ожидаемое движение цены на основе тренда
        trend_direction = 0
        if self.trend[timeframe] == "восходящий":
            trend_direction = 1
        elif self.trend[timeframe] == "нисходящий":
            trend_direction = -1
        
        # Рассчитываем ожидаемое изменение цены на основе тренда
        expected_change_percent = trend_direction * volatility_adjusted * 0.5
        
        # Рассчитываем ожидаемую цену
        expected_price = current_price * (1 + expected_change_percent / 100)
        
        # Рассчитываем минимальную и максимальную цены в прогнозе
        min_price = current_price * (1 - volatility_adjusted / 100)
        max_price = current_price * (1 + volatility_adjusted / 100)
        
        # Если есть четкий тренд, смещаем коридор в сторону тренда
        if trend_direction != 0:
            min_price = min_price * (1 + trend_direction * 0.2 * volatility / 100)
            max_price = max_price * (1 + trend_direction * 0.2 * volatility / 100)
        
        # Учитываем поддержки/сопротивления для уточнения прогноза
        supports = [level['price'] for level in self.market_data.support]
        resistances = [level['price'] for level in self.market_data.resistance]
        
        # Находим ближайшие уровни поддержки и сопротивления
        nearest_support = min(supports, key=lambda x: abs(x - min_price)) if supports else min_price
        nearest_resistance = min(resistances, key=lambda x: abs(x - max_price)) if resistances else max_price
        
        # Корректируем прогноз с учетом уровней
        if nearest_support > min_price:
            min_price = (min_price + nearest_support) / 2
        
        if nearest_resistance < max_price:
            max_price = (max_price + nearest_resistance) / 2
        
        # Определяем уверенность в прогнозе (от 0 до 1)
        # Чем дольше период и выше волатильность, тем ниже уверенность
        confidence = max(0.3, 1 - (time_factor * volatility / 100))
        
        return {
            "min": min_price,
            "max": max_price,
            "expected": expected_price,
            "confidence": confidence
        }

    def _set_long_term_targets(self) -> None:
        """Метод для определения долгосрочных целевых уровней"""
        try:
            # Используем 4-часовой таймфрейм для определения долгосрочных целей
            df = self.market_data.candles.get('4h')
            if df is None or len(df) < 30:
                return
            
            current_price = df['close'].iloc[-1]
            
            # Основные поддержки и сопротивления
            supports = self.market_data.support
            resistances = self.market_data.resistance
            
            # Определяем ключевые уровни (берем до 5 уровней)
            key_supports = supports[:min(5, len(supports))]
            key_resistances = resistances[:min(5, len(resistances))]
            
            # Определяем долгосрочные целевые уровни на основе текущего тренда
            targets = {
                "buy": [],   # Целевые уровни для покупки (поддержки)
                "sell": [],  # Целевые уровни для продажи (сопротивления)
                "neutral": []  # Нейтральные уровни
            }
            
            # Форматирование поддержек как целей для покупки
            for i, support in enumerate(key_supports):
                support_price = support['price']
                # Рассчитываем потенциальную прибыль
                potential_profit = ((current_price - support_price) / current_price) * 100
                distance_percent = abs(potential_profit)
                
                # Определяем силу сигнала на основе расстояния и силы уровня
                strength = max(0.3, min(0.9, (1 - distance_percent / 20) * support['strength']))
                
                targets["buy"].append({
                    "price": support_price,
                    "distance_percent": distance_percent,
                    "strength": strength,
                    "type": "поддержка",
                    "description": f"Уровень поддержки #{i+1} ({support_price:.6f})"
                })
            
            # Форматирование сопротивлений как целей для продажи
            for i, resistance in enumerate(key_resistances):
                resistance_price = resistance['price']
                # Рассчитываем потенциальную прибыль
                potential_profit = ((resistance_price - current_price) / current_price) * 100
                distance_percent = abs(potential_profit)
                
                # Определяем силу сигнала на основе расстояния и силы уровня
                strength = max(0.3, min(0.9, (1 - distance_percent / 20) * resistance['strength']))
                
                targets["sell"].append({
                    "price": resistance_price,
                    "distance_percent": distance_percent,
                    "strength": strength,
                    "type": "сопротивление",
                    "description": f"Уровень сопротивления #{i+1} ({resistance_price:.6f})"
                })
            
            # Добавляем прогнозные уровни из анализа цен
            if self.price_predictions:
                # Среднесрочный прогноз как нейтральный уровень
                medium_term = self.price_predictions.get("medium_term", {})
                if medium_term and medium_term.get("expected", 0) > 0:
                    expected_price = medium_term["expected"]
                    confidence = medium_term.get("confidence", 0.5)
                    
                    targets["neutral"].append({
                        "price": expected_price,
                        "distance_percent": abs(((expected_price - current_price) / current_price) * 100),
                        "strength": confidence,
                        "type": "прогноз",
                        "description": f"Ожидаемая цена через 24 часа ({expected_price:.6f})"
                    })
                
                # Долгосрочный прогноз максимума как цель для продажи
                long_term = self.price_predictions.get("long_term", {})
                if long_term and long_term.get("max", 0) > 0:
                    max_price = long_term["max"]
                    confidence = long_term.get("confidence", 0.4)
                    
                    targets["sell"].append({
                        "price": max_price,
                        "distance_percent": abs(((max_price - current_price) / current_price) * 100),
                        "strength": confidence,
                        "type": "прогноз",
                        "description": f"Прогнозный максимум через 7 дней ({max_price:.6f})"
                    })
                
                # Долгосрочный прогноз минимума как цель для покупки
                if long_term and long_term.get("min", 0) > 0:
                    min_price = long_term["min"]
                    confidence = long_term.get("confidence", 0.4)
                    
                    targets["buy"].append({
                        "price": min_price,
                        "distance_percent": abs(((current_price - min_price) / current_price) * 100),
                        "strength": confidence,
                        "type": "прогноз",
                        "description": f"Прогнозный минимум через 7 дней ({min_price:.6f})"
                    })
            
            # Сортируем целевые уровни по расстоянию (ближайшие первыми)
            for key in targets:
                targets[key] = sorted(targets[key], key=lambda x: x["distance_percent"])
            
            self.long_term_targets = targets
            
            logger.info(f"Целевые уровни для {self.symbol} определены:")
            logger.info(f"Уровни для покупки: {len(targets['buy'])}")
            logger.info(f"Уровни для продажи: {len(targets['sell'])}")
            
        except Exception as e:
            logger.error(f"Ошибка определения целевых уровней для {self.symbol}: {e}")
            self.long_term_targets = {"buy": [], "sell": [], "neutral": []}

    def _analyze_trend(self, timeframe: str) -> None:
        """Метод для определения тренда на конкретном таймфрейме"""
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

    def _determine_overall_trend(self) -> None:
        """Метод для определения общего тренда"""
        # Весовые коэффициенты для разных таймфреймов (длительные имеют больший вес)
        weights = {
            '5m': 1,
            '15m': 2,
            '1h': 3,
            '4h': 5
        }
        
        up_trend_score = 0
        down_trend_score = 0
        total_weight = 0
        
        for timeframe, trend in self.trend.items():
            if timeframe == 'общий':
                continue
            
            weight = weights.get(timeframe, 1)
            total_weight += weight
            
            if trend == 'восходящий':
                up_trend_score += weight
            elif trend == 'нисходящий':
                down_trend_score += weight
            else:
                # Смешанный тренд распределяем поровну
                up_trend_score += weight / 2
                down_trend_score += weight / 2
        
        up_trend_percent = (up_trend_score / total_weight) * 100
        down_trend_percent = (down_trend_score / total_weight) * 100
        
        # Определение общего тренда
        if up_trend_percent >= 65:
            self.trend['общий'] = 'восходящий'
        elif down_trend_percent >= 65:
            self.trend['общий'] = 'нисходящий'
        else:
            self.trend['общий'] = 'боковой'
        
        logger.info(f"Общий тренд {self.symbol}: {self.trend['общий']} (UP: {up_trend_percent:.1f}%, DOWN: {down_trend_percent:.1f}%)")

    def _find_signals(self, timeframe: str) -> None:
        """Метод для поиска сигналов на конкретном таймфрейме"""
        indicators = self.market_data.indicators.get(timeframe)
        if not indicators:
            return
        
        # Подготавливаем структуру для сигналов
        if timeframe not in self.signals:
            self.signals[timeframe] = {
                'buy': [],
                'sell': []
            }
        else:
            # Очищаем предыдущие сигналы для этого таймфрейма
            self.signals[timeframe] = {
                'buy': [],
                'sell': []
            }
        
        # Получаем последние значения индикаторов
        rsi = indicators['rsi']
        macd = indicators['macd']
        ema_short = indicators['ema_short']
        ema_medium = indicators['ema_medium']
        volumes = indicators['volumes']
        avg_volume = indicators['avg_volume']
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        macd_line = macd['macd_line']
        signal_line = macd['signal_line']
        current_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        current_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        
        current_volume = volumes.iloc[-1]
        avg_volume_value = avg_volume.iloc[-1]
        
        # Сигналы RSI
        if current_rsi < CONFIG["rsi_oversold"] and prev_rsi < CONFIG["rsi_oversold"]:
            self.signals[timeframe]['buy'].append({
                'type': 'RSI',
                'strength': 0.7,
                'message': f"RSI перепродан ({current_rsi:.2f})"
            })
        
        if current_rsi > CONFIG["rsi_overbought"] and prev_rsi > CONFIG["rsi_overbought"]:
            self.signals[timeframe]['sell'].append({
                'type': 'RSI',
                'strength': 0.7,
                'message': f"RSI перекуплен ({current_rsi:.2f})"
            })
        
        # Сигналы MACD
        # Пересечение MACD сигнальной линии снизу вверх (бычий сигнал)
        if current_macd > current_signal and prev_macd <= prev_signal:
            self.signals[timeframe]['buy'].append({
                'type': 'MACD',
                'strength': 0.8,
                'message': 'Бычье пересечение MACD'
            })
        
        # Пересечение MACD сигнальной линии сверху вниз (медвежий сигнал)
        if current_macd < current_signal and prev_macd >= prev_signal:
            self.signals[timeframe]['sell'].append({
                'type': 'MACD',
                'strength': 0.8,
                'message': 'Медвежье пересечение MACD'
            })
        
        # Пересечение MACD нулевой линии снизу вверх (бычий сигнал)
        if current_macd > 0 and prev_macd <= 0:
            self.signals[timeframe]['buy'].append({
                'type': 'MACD Zero',
                'strength': 0.6,
                'message': 'MACD пересек нулевую линию снизу вверх'
            })
        
        # Пересечение MACD нулевой линии сверху вниз (медвежий сигнал)
        if current_macd < 0 and prev_macd >= 0:
            self.signals[timeframe]['sell'].append({
                'type': 'MACD Zero',
                'strength': 0.6,
                'message': 'MACD пересек нулевую линию сверху вниз'
            })
        
        # Сигналы EMA
        # Пересечение короткой EMA средней EMA снизу вверх (бычий сигнал)
        if (ema_short.iloc[-1] > ema_medium.iloc[-1] and 
            ema_short.iloc[-2] <= ema_medium.iloc[-2]):
            self.signals[timeframe]['buy'].append({
                'type': 'EMA Cross',
                'strength': 0.7,
                'message': f"Пересечение EMA{CONFIG['ema_short']} выше EMA{CONFIG['ema_medium']}"
            })
        
        # Пересечение короткой EMA средней EMA сверху вниз (медвежий сигнал)
        if (ema_short.iloc[-1] < ema_medium.iloc[-1] and 
            ema_short.iloc[-2] >= ema_medium.iloc[-2]):
            self.signals[timeframe]['sell'].append({
                'type': 'EMA Cross',
                'strength': 0.7,
                'message': f"Пересечение EMA{CONFIG['ema_short']} ниже EMA{CONFIG['ema_medium']}"
            })
        
        # Проверка объемов
        # Повышенный объем (может быть сигналом к развороту или усилению тренда)
        if not pd.isna(current_volume) and not pd.isna(avg_volume_value) and current_volume > avg_volume_value * CONFIG["vol_multiplier"]:
            # Направление определяем по цене
            df = self.market_data.candles[timeframe]
            last_candle_open = df['open'].iloc[-1]
            last_candle_close = df['close'].iloc[-1]
            
            if last_candle_close > last_candle_open:
                self.signals[timeframe]['buy'].append({
                    'type': 'Volume',
                    'strength': 0.6,
                    'message': 'Повышенный объем при росте цены'
                })
            else:
                self.signals[timeframe]['sell'].append({
                    'type': 'Volume',
                    'strength': 0.6,
                    'message': 'Повышенный объем при падении цены'
                })