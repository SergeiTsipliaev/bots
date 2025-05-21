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

    def _calculate_price_prediction(self, timeframe: str, hours: int) -> Dict[str, float]:
        """
        Метод для расчета прогноза цены на указанное количество часов вперед
        
        Args:
            timeframe: Таймфрейм для анализа
            hours: Количество часов для прогноза
            
        Returns:
            Словарь с прогнозом цены
        """
        try:
            df = self.market_data.candles.get(timeframe)
            if df is None or len(df) < 30:
                # Безопасное значение, если нет данных
                current_price = self.market_data.last_price
                return {
                    "min": current_price * 0.95,
                    "max": current_price * 1.05,
                    "expected": current_price,
                    "confidence": 0.5
                }
            
            current_price = df['close'].iloc[-1]
            
            # Получаем индикаторы
            indicators = self.market_data.indicators.get(timeframe)
            if not indicators:
                # Безопасное значение, если нет индикаторов
                return {
                    "min": current_price * 0.95,
                    "max": current_price * 1.05,
                    "expected": current_price,
                    "confidence": 0.5
                }
            
            # Рассчитываем волатильность (стандартное отклонение в процентах)
            volatility = df['close'].pct_change().std() * 100
            
            # Минимальная волатильность для предотвращения нулевых прогнозов
            if np.isnan(volatility) or volatility < 0.5:
                volatility = 0.5  # Минимальная волатильность 0.5%
                
            # Корректируем прогноз на основе временного горизонта и волатильности
            time_factor = 1.0
            if 'h' in timeframe:
                time_periods = int(timeframe.replace('h', ''))
                if time_periods > 0:
                    time_factor = np.sqrt(hours / time_periods)
            else:
                # Для других временных периодов (например, минуты)
                if timeframe == '5m':
                    time_factor = np.sqrt(hours / (5/60))
                elif timeframe == '15m':
                    time_factor = np.sqrt(hours / (15/60))
                elif timeframe == '24':
                    time_factor = np.sqrt(hours / 24)
                else:
                    time_factor = np.sqrt(hours)
            
            volatility_adjusted = volatility * time_factor
            
            # Рассчитываем ожидаемое движение цены на основе тренда
            trend_direction = 0
            if self.trend[timeframe] == "восходящий":
                trend_direction = 1
            elif self.trend[timeframe] == "нисходящий":
                trend_direction = -1
            
            # Даже при нейтральном тренде добавляем компонент направления
            if trend_direction == 0:
                # Рассчитываем среднее направление движения за последние несколько свечей
                recent_changes = df['close'].pct_change().tail(10).mean() * 100
                # Если не получается рассчитать среднее изменение, используем небольшое случайное значение
                if np.isnan(recent_changes):
                    import random
                    recent_changes = random.uniform(-0.5, 0.5)
                trend_direction = 0.3 * (1 if recent_changes > 0 else -1)
            
            # Рассчитываем ожидаемое изменение цены на основе тренда
            expected_change_percent = trend_direction * volatility_adjusted * 0.5
            
            # Безопасное значение для изменения - минимум 0.1% если тренд не ровно боковой
            if abs(expected_change_percent) < 0.1:
                expected_change_percent = max(0.1, abs(expected_change_percent)) * (1 if trend_direction > 0 else -1)
            
            # Рассчитываем ожидаемую цену и диапазон
            expected_price = current_price * (1 + expected_change_percent / 100)
            min_price = current_price * (1 - volatility_adjusted / 100)
            max_price = current_price * (1 + volatility_adjusted / 100)
            
            # Если есть четкий тренд, смещаем коридор в сторону тренда
            if trend_direction != 0:
                min_price = min_price * (1 + trend_direction * 0.2 * volatility / 100)
                max_price = max_price * (1 + trend_direction * 0.2 * volatility / 100)
            
            # Учитываем поддержки/сопротивления для уточнения прогноза
            supports = [level['price'] for level in self.market_data.support]
            resistances = [level['price'] for level in self.market_data.resistance]
            
            # Проверяем наличие уровней поддержек и сопротивлений
            if supports:
                nearest_support = min(supports, key=lambda x: abs(x - min_price))
                if nearest_support > min_price:
                    min_price = (min_price + nearest_support) / 2
            
            if resistances:
                nearest_resistance = min(resistances, key=lambda x: abs(x - max_price))
                if nearest_resistance < max_price:
                    max_price = (max_price + nearest_resistance) / 2
            
            # Определяем уверенность в прогнозе (от 0 до 1)
            # Чем дольше период и выше волатильность, тем ниже уверенность
            confidence = max(0.3, 1 - (time_factor * volatility / 100))
            
            # Проверяем на корректность значений перед возвратом
            if expected_price <= 0 or min_price <= 0 or max_price <= 0:
                return {
                    "min": current_price * 0.95,
                    "max": current_price * 1.05,
                    "expected": current_price,
                    "confidence": 0.5
                }
            
            return {
                "min": min_price,
                "max": max_price,
                "expected": expected_price,
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Ошибка при расчете прогноза для {self.symbol} на таймфрейме {timeframe}: {str(e)}")
            import traceback
            logger.error(f"Трассировка: {traceback.format_exc()}")
            
            # В случае ошибки возвращаем текущую цену как безопасный вариант
            current_price = self.market_data.last_price
            return {
                "min": current_price * 0.95,
                "max": current_price * 1.05,
                "expected": current_price,
                "confidence": 0.5
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

    def _generate_trade_signal(self) -> Dict:
        """Метод для генерации торгового сигнала на основе собранных данных"""
        try:
            # Определяем тип сигнала на основе анализа
            signal_type = "HOLD"  # По умолчанию сигнал ожидания
            signal_strength = 0.0
            # Добавляем переменную для уверенности в сигнале
            signal_confidence = 0.0  # Инициализируем уверенность нулем
            messages = []
            suggested_actions = []
            
            # Анализируем сигналы от разных таймфреймов с весами
            weights = {
                '5m': 0.1,
                '15m': 0.2,
                '1h': 0.3,
                '4h': 0.4
            }
            
            buy_score = 0.0
            sell_score = 0.0
            buy_messages = []
            sell_messages = []
            total_weight = 0.0
            
            # Логика определения сигнала на основе весов таймфреймов
            for timeframe, weight in weights.items():
                if timeframe not in self.signals:
                    continue
                    
                total_weight += weight
                
                # Проверяем сигналы на покупку
                for signal in self.signals[timeframe]['buy']:
                    buy_score += signal['strength'] * weight
                    buy_messages.append(f"{timeframe}: {signal['message']} ({signal['strength']*100:.0f}%)")
                
                # Проверяем сигналы на продажу
                for signal in self.signals[timeframe]['sell']:
                    sell_score += signal['strength'] * weight
                    sell_messages.append(f"{timeframe}: {signal['message']} ({signal['strength']*100:.0f}%)")
            
            # Нормализуем оценки
            if total_weight > 0:
                buy_score /= total_weight
                sell_score /= total_weight
            
            # Получаем уверенность в рыночной фазе
            market_phase_confidence = self.market_cycles.get('confidence', 0.5)
            
            # Определяем окончательный тип сигнала
            if buy_score > 0.4 and buy_score > sell_score * 1.5:
                signal_type = "BUY"
                signal_strength = buy_score
                # Рассчитываем уверенность в сигнале как произведение силы сигнала и уверенности в рыночной фазе
                signal_confidence = buy_score * market_phase_confidence
                messages = buy_messages
            elif sell_score > 0.4 and sell_score > buy_score * 1.5:
                signal_type = "SELL"
                signal_strength = sell_score
                # Рассчитываем уверенность в сигнале как произведение силы сигнала и уверенности в рыночной фазе
                signal_confidence = sell_score * market_phase_confidence
                messages = sell_messages
            else:
                # Проверяем различие между buy и sell сигналами
                if abs(buy_score - sell_score) < 0.1:
                    # Если разница незначительная, считаем сигнал ожидания
                    signal_type = "HOLD"
                    signal_strength = max(0.3, (buy_score + sell_score) / 2)
                    # Рассчитываем уверенность в сигнале ожидания
                    signal_confidence = signal_strength * market_phase_confidence
                    messages = buy_messages + sell_messages
                else:
                    # Иначе выбираем сигнал с большим значением
                    if buy_score > sell_score:
                        signal_type = "BUY"
                        signal_strength = buy_score
                        signal_confidence = buy_score * market_phase_confidence
                        messages = buy_messages
                    else:
                        signal_type = "SELL"
                        signal_strength = sell_score
                        signal_confidence = sell_score * market_phase_confidence
                        messages = sell_messages
            
            # Проверяем уровень уверенности и игнорируем сигналы с низкой уверенностью
            if signal_confidence < 0.6:  # Порог 60%
                logger.info(f"Сигнал {signal_type} для {self.symbol} имеет низкую уверенность ({signal_confidence*100:.2f}%), игнорируем")
                return None
            
            # Формируем рекомендации на основе типа сигнала
            if signal_type in ["BUY", "SELL"]:
                current_price = self.market_data.last_price
                
                if signal_type == "BUY":
                    # Находим ближайшее сопротивление для тейк-профита
                    if self.market_data.resistance and len(self.market_data.resistance) > 0:
                        take_profit = self.market_data.resistance[0]['price']
                        tp_percent = ((take_profit - current_price) / current_price) * 100
                    else:
                        # Если нет данных о сопротивлении, используем процент из конфига
                        take_profit = current_price * (1 + CONFIG["take_profit_percent"] / 100)
                        tp_percent = CONFIG["take_profit_percent"]
                    
                    # Находим ближайшую поддержку для стоп-лосса
                    if self.market_data.support and len(self.market_data.support) > 0:
                        stop_loss = max(
                            self.market_data.support[0]['price'],
                            current_price * (1 - CONFIG["stop_loss_percent"] / 100)
                        )
                    else:
                        stop_loss = current_price * (1 - CONFIG["stop_loss_percent"] / 100)
                    
                    sl_percent = ((current_price - stop_loss) / current_price) * 100
                    
                    suggested_actions.append(f"Цена входа: {current_price:.6f}")
                    suggested_actions.append(f"Ближайший тейк-профит: {take_profit:.6f} ({tp_percent:.2f}%)")
                    suggested_actions.append(f"Стоп-лосс: {stop_loss:.6f} ({sl_percent:.2f}%)")
                
                elif signal_type == "SELL":
                    # Для сигнала на продажу меняем логику тейк-профит и стоп-лосс
                    if self.market_data.support and len(self.market_data.support) > 0:
                        take_profit = self.market_data.support[0]['price']
                        tp_percent = ((current_price - take_profit) / current_price) * 100
                    else:
                        take_profit = current_price * (1 - CONFIG["take_profit_percent"] / 100)
                        tp_percent = CONFIG["take_profit_percent"]
                    
                    if self.market_data.resistance and len(self.market_data.resistance) > 0:
                        stop_loss = min(
                            self.market_data.resistance[0]['price'],
                            current_price * (1 + CONFIG["stop_loss_percent"] / 100)
                        )
                    else:
                        stop_loss = current_price * (1 + CONFIG["stop_loss_percent"] / 100)
                    
                    sl_percent = ((stop_loss - current_price) / current_price) * 100
                    
                    suggested_actions.append(f"Цена входа: {current_price:.6f}")
                    suggested_actions.append(f"Ближайший тейк-профит: {take_profit:.6f} ({tp_percent:.2f}%)")
                    suggested_actions.append(f"Стоп-лосс: {stop_loss:.6f} ({sl_percent:.2f}%)")
                
                # Добавляем долгосрочные целевые уровни
                suggested_actions.append("")
                suggested_actions.append("Долгосрочные целевые уровни:")
                
                if signal_type == "BUY" and self.long_term_targets.get("sell"):
                    # Для сигнала на покупку добавляем целевые уровни продажи (сопротивления)
                    targets = self.long_term_targets["sell"]
                    for i, target in enumerate(targets[:3]):  # Берем максимум 3 уровня
                        profit_percent = ((target["price"] - current_price) / current_price) * 100
                        suggested_actions.append(
                            f"{i+1}. {target['price']:.6f} ({profit_percent:.2f}% от текущей) - {target['description']}"
                        )
                
                elif signal_type == "SELL" and self.long_term_targets.get("buy"):
                    # Для сигнала на продажу добавляем целевые уровни покупки (поддержки)
                    targets = self.long_term_targets["buy"]
                    for i, target in enumerate(targets[:3]):  # Берем максимум 3 уровня
                        profit_percent = ((current_price - target["price"]) / current_price) * 100
                        suggested_actions.append(
                            f"{i+1}. {target['price']:.6f} ({profit_percent:.2f}% от текущей) - {target['description']}"
                        )
                
                # Добавляем прогнозы цен
                suggested_actions.append("")
                suggested_actions.append("Прогнозы движения цены:")
                
                try:
                    # Краткосрочный прогноз (6 часов)
                    if self.price_predictions.get("short_term"):
                        short_term = self.price_predictions["short_term"]
                        if short_term.get("expected", 0) > 0:
                            change_percent = ((short_term["expected"] - current_price) / current_price) * 100
                            direction = "↗️" if change_percent > 0 else "↘️"
                            # Проверка на адекватность процента изменения
                            if abs(change_percent) > 20:
                                change_percent = 5.0 * (1 if change_percent > 0 else -1)
                            suggested_actions.append(
                                f"6 часов: {direction} {short_term['expected']:.6f} (±{abs(change_percent):.2f}%)"
                            )
                            # Проверяем валидность диапазона
                            min_val = max(0.000001, short_term.get("min", current_price * 0.95))
                            max_val = max(min_val * 1.001, short_term.get("max", current_price * 1.05))
                            suggested_actions.append(
                                f"  Диапазон: {min_val:.6f} - {max_val:.6f}"
                            )
                        else:
                            # Если данные недоступны, используем значения по умолчанию
                            suggested_actions.append(
                                f"6 часов: ↗️ {current_price * 1.01:.6f} (±1.00%)"
                            )
                            suggested_actions.append(
                                f"  Диапазон: {current_price * 0.995:.6f} - {current_price * 1.025:.6f}"
                            )
                    
                    # Среднесрочный прогноз (24 часа)
                    if self.price_predictions.get("medium_term"):
                        medium_term = self.price_predictions["medium_term"]
                        if medium_term.get("expected", 0) > 0:
                            change_percent = ((medium_term["expected"] - current_price) / current_price) * 100
                            direction = "↗️" if change_percent > 0 else "↘️"
                            # Проверка на адекватность процента изменения
                            if abs(change_percent) > 20:
                                change_percent = 7.0 * (1 if change_percent > 0 else -1)
                            suggested_actions.append(
                                f"24 часа: {direction} {medium_term['expected']:.6f} (±{abs(change_percent):.2f}%)"
                            )
                            # Проверяем валидность диапазона
                            min_val = max(0.000001, medium_term.get("min", current_price * 0.9))
                            max_val = max(min_val * 1.001, medium_term.get("max", current_price * 1.1))
                            suggested_actions.append(
                                f"  Диапазон: {min_val:.6f} - {max_val:.6f}"
                            )
                        else:
                            # Если данные недоступны, используем значения по умолчанию
                            suggested_actions.append(
                                f"24 часа: ↗️ {current_price * 1.02:.6f} (±2.00%)"
                            )
                            suggested_actions.append(
                                f"  Диапазон: {current_price * 0.99:.6f} - {current_price * 1.05:.6f}"
                            )
                    
                    # Долгосрочный прогноз (7 дней)
                    if self.price_predictions.get("long_term"):
                        long_term = self.price_predictions["long_term"]
                        if long_term.get("expected", 0) > 0:
                            change_percent = ((long_term["expected"] - current_price) / current_price) * 100
                            direction = "↗️" if change_percent > 0 else "↘️"
                            # Проверка на адекватность процента изменения
                            if abs(change_percent) > 20:
                                change_percent = 10.0 * (1 if change_percent > 0 else -1)
                            suggested_actions.append(
                                f"7 дней: {direction} {long_term['expected']:.6f} (±{abs(change_percent):.2f}%)"
                            )
                            # Проверяем валидность диапазона
                            min_val = max(0.000001, long_term.get("min", current_price * 0.85))
                            max_val = max(min_val * 1.001, long_term.get("max", current_price * 1.15))
                            suggested_actions.append(
                                f"  Диапазон: {min_val:.6f} - {max_val:.6f}"
                            )
                        else:
                            # Если данные недоступны, используем значения по умолчанию
                            suggested_actions.append(
                                f"7 дней: ↗️ {current_price * 1.03:.6f} (±3.00%)"
                            )
                            suggested_actions.append(
                                f"  Диапазон: {current_price * 0.97:.6f} - {current_price * 1.09:.6f}"
                            )
                except Exception as e:
                    logger.error(f"Ошибка при формировании прогнозов: {e}")
                    # Добавляем базовые прогнозы в случае ошибки
                    suggested_actions.append(f"6 часов: ↔️ {current_price:.6f} (прогноз недоступен)")
                    suggested_actions.append(f"24 часа: ↔️ {current_price:.6f} (прогноз недоступен)")
                    suggested_actions.append(f"7 дней: ↔️ {current_price:.6f} (прогноз недоступен)")
            
            # Создаем структуру сигнала
            market_info = [
                f"Инструмент: {self.symbol}",
                f"Текущая цена: {self.market_data.last_price:.6f}",
                f"Изменение за день: {self.market_data.daily_change:.2f}%",
                f"Общий тренд: {self.trend['общий']}",
                f"Рыночная фаза: {self.market_cycles.get('phase', 'неопределенная')}",
            ]
            
            # Добавляем информацию о ближайших уровнях поддержки и сопротивления
            if self.market_data.support and len(self.market_data.support) > 0:
                market_info.append(f"Ближайшая поддержка: {self.market_data.support[0]['price']:.6f}")
            
            if self.market_data.resistance and len(self.market_data.resistance) > 0:
                market_info.append(f"Ближайшее сопротивление: {self.market_data.resistance[0]['price']:.6f}")
            
            # Формируем полный сигнал
            self.last_signal = {
                "timestamp": datetime.datetime.now().isoformat(),
                "symbol": self.symbol,
                "signal_type": signal_type,
                "strength": signal_strength,
                "confidence": signal_confidence,
                "price": self.market_data.last_price,
                "messages": messages,
                "suggested_actions": suggested_actions,
                "market_info": market_info,
                "trend": self.trend,
                "market_cycles": self.market_cycles,
                "price_predictions": self.price_predictions,
                "long_term_targets": self.long_term_targets
            }
            
            logger.info(f"Сгенерирован сигнал {signal_type} для {self.symbol} с силой {signal_strength:.2f} и уверенностью {signal_confidence*100:.2f}%")
            return self.last_signal
        
        except Exception as e:
            logger.error(f"Ошибка генерации сигнала для {self.symbol}: {e}")
            # Логируем полную трассировку для отладки
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            
            # Возвращаем базовый сигнал с минимальными данными
            default_signal = {
                "timestamp": datetime.datetime.now().isoformat(),
                "symbol": self.symbol,
                "signal_type": "HOLD",
                "strength": 0.0,
                "confidence": 0.0,
                "price": self.market_data.last_price,
                "messages": ["Ошибка при генерации сигнала"],
                "suggested_actions": ["Требуется проверка системы"],
                "market_info": [
                    f"Инструмент: {self.symbol}",
                    f"Текущая цена: {self.market_data.last_price:.6f}"
                ],
                "trend": {"общий": "неопределен"}
            }
            self.last_signal = default_signal
            return None  # Возвращаем None, чтобы не отправлять ошибочный сигнал

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