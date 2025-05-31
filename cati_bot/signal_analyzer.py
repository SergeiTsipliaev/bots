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

    def _find_signals(self, timeframe: str) -> None:
        """Метод для поиска сигналов на конкретном таймфрейме"""
        try:
            indicators = self.market_data.indicators.get(timeframe)
            if not indicators:
                return

            signals = []

            # Получаем последние значения индикаторов
            rsi = indicators['rsi'].iloc[-1]
            macd_data = indicators['macd']
            macd_line = macd_data['macd_line'].iloc[-1]
            signal_line = macd_data['signal_line'].iloc[-1]

            # Анализ RSI
            if rsi < CONFIG["rsi_oversold"]:
                signals.append(f"{timeframe}: RSI перепродан ({rsi:.2f})")
            elif rsi > CONFIG["rsi_overbought"]:
                signals.append(f"{timeframe}: RSI перекуплен ({rsi:.2f})")

            # Анализ MACD
            if macd_line > signal_line:
                signals.append(f"{timeframe}: MACD бычий сигнал")
            elif macd_line < signal_line:
                signals.append(f"{timeframe}: MACD медвежий сигнал")

            # Анализ объемов
            volumes = indicators['volumes']
            avg_volume = indicators['avg_volume']
            if len(volumes) > 0 and len(avg_volume) > 0:
                current_volume = volumes.iloc[-1]
                avg_vol = avg_volume.iloc[-1]
                if current_volume > avg_vol * CONFIG["vol_multiplier"]:
                    signals.append(f"{timeframe}: Повышенный объем")

            self.signals[timeframe] = signals
        except Exception as e:
            logger.error(f"Ошибка поиска сигналов для {self.symbol} на {timeframe}: {e}")
            self.signals[timeframe] = []

    def _determine_overall_trend(self) -> None:
        """Метод для определения общего тренда"""
        try:
            trends = [self.trend[tf] for tf in ['5m', '15m', '1h', '4h']]

            # Подсчитываем количество восходящих, нисходящих и смешанных трендов
            bullish_count = trends.count('восходящий')
            bearish_count = trends.count('нисходящий')
            mixed_count = trends.count('смешанный')

            # Определяем общий тренд
            if bullish_count >= 3:
                self.trend['общий'] = 'восходящий'
            elif bearish_count >= 3:
                self.trend['общий'] = 'нисходящий'
            elif bullish_count > bearish_count:
                self.trend['общий'] = 'слабо восходящий'
            elif bearish_count > bullish_count:
                self.trend['общий'] = 'слабо нисходящий'
            else:
                self.trend['общий'] = 'боковой'

            logger.info(f"Общий тренд для {self.symbol}: {self.trend['общий']}")
        except Exception as e:
            logger.error(f"Ошибка определения общего тренда для {self.symbol}: {e}")
            self.trend['общий'] = 'неопределен'

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

            logger.info(f"Рыночная фаза для {self.symbol}: {market_phase} (уверенность: {confidence * 100:.1f}%)")

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
        """Расчет прогноза цены для конкретного периода"""
        try:
            df = self.market_data.candles.get(timeframe)
            if df is None or len(df) < 20:
                return {"min": 0, "max": 0, "expected": 0, "confidence": 0}

            current_price = self.market_data.last_price
            if current_price <= 0:
                current_price = float(df['close'].iloc[-1])

            # Рассчитываем историческую волатильность
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Дневная волатильность

            # Учитываем тренд
            trend_factor = self._get_trend_factor()

            # Базовое изменение цены на основе тренда и времени
            base_change = trend_factor * (hours / 24) * 0.02  # 2% в день при сильном тренде

            # Диапазон волатильности
            volatility_range = volatility * CONFIG.get("volatility_multiplier", 1.5) * (hours / 24)

            # Прогнозируемая цена
            expected_price = current_price * (1 + base_change)

            # Минимальная и максимальная цена
            min_price = expected_price * (1 - volatility_range)
            max_price = expected_price * (1 + volatility_range)

            # Уверенность в прогнозе (снижается с увеличением времени)
            confidence = max(0.2, 0.9 - (hours / 168) * 0.7)  # От 90% до 20%

            return {
                "min": max(0, min_price),
                "max": max_price,
                "expected": expected_price,
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Ошибка расчета прогноза цены для {self.symbol}: {e}")
            return {"min": 0, "max": 0, "expected": 0, "confidence": 0}

    def _get_trend_factor(self) -> float:
        """Получение фактора тренда для прогнозирования"""
        try:
            overall_trend = self.trend.get('общий', 'неопределен')

            if overall_trend == 'восходящий':
                return 0.5
            elif overall_trend == 'слабо восходящий':
                return 0.2
            elif overall_trend == 'нисходящий':
                return -0.5
            elif overall_trend == 'слабо нисходящий':
                return -0.2
            else:
                return 0.0
        except Exception as e:
            logger.error(f"Ошибка получения фактора тренда для {self.symbol}: {e}")
            return 0.0

    def _set_long_term_targets(self) -> None:
        """Определение долгосрочных целевых уровней"""
        try:
            current_price = self.market_data.last_price
            if current_price <= 0:
                return

            targets = {
                "buy_targets": [],
                "sell_targets": []
            }

            # Используем уровни поддержки как цели для покупки
            for i, support in enumerate(self.market_data.support[:5]):  # Берем первые 5 уровней
                distance_percent = ((current_price - support['price']) / current_price) * 100
                if distance_percent > 1:  # Только если уровень ниже на 1%+
                    targets["buy_targets"].append({
                        "price": support['price'],
                        "distance_percent": distance_percent,
                        "description": f"Уровень поддержки #{i + 1}",
                        "strength": support.get('strength', 1)
                    })

            # Используем уровни сопротивления как цели для продажи
            for i, resistance in enumerate(self.market_data.resistance[:5]):  # Берем первые 5 уровней
                distance_percent = ((resistance['price'] - current_price) / current_price) * 100
                if distance_percent > 1:  # Только если уровень выше на 1%+
                    targets["sell_targets"].append({
                        "price": resistance['price'],
                        "distance_percent": distance_percent,
                        "description": f"Уровень сопротивления #{i + 1}",
                        "strength": resistance.get('strength', 1)
                    })

            # Добавляем прогнозные цели на основе долгосрочного прогноза
            long_term_prediction = self.price_predictions.get("long_term", {})
            if long_term_prediction.get("expected", 0) > 0:
                expected_price = long_term_prediction["expected"]
                distance_percent = ((expected_price - current_price) / current_price) * 100

                if distance_percent > 2:  # Если ожидается рост больше 2%
                    targets["sell_targets"].append({
                        "price": expected_price,
                        "distance_percent": distance_percent,
                        "description": "Прогнозный максимум через 7 дней",
                        "strength": long_term_prediction.get("confidence", 0.5)
                    })
                elif distance_percent < -2:  # Если ожидается падение больше 2%
                    targets["buy_targets"].append({
                        "price": expected_price,
                        "distance_percent": abs(distance_percent),
                        "description": "Прогнозный минимум через 7 дней",
                        "strength": long_term_prediction.get("confidence", 0.5)
                    })

            # Сортируем цели по расстоянию (ближайшие первыми)
            targets["buy_targets"].sort(key=lambda x: x["distance_percent"])
            targets["sell_targets"].sort(key=lambda x: x["distance_percent"])

            self.long_term_targets = targets

            logger.info(
                f"Долгосрочные цели для {self.symbol}: {len(targets['buy_targets'])} для покупки, {len(targets['sell_targets'])} для продажи")

        except Exception as e:
            logger.error(f"Ошибка определения долгосрочных целей для {self.symbol}: {e}")
            self.long_term_targets = {"buy_targets": [], "sell_targets": []}

    def _generate_trade_signal(self) -> Dict[str, Any]:
        """Генерация торгового сигнала (общий анализ)"""
        try:
            return self._generate_comprehensive_signal("ALL")
        except Exception as e:
            logger.error(f"Ошибка генерации торгового сигнала для {self.symbol}: {e}")
            return None

    def _generate_short_term_signal(self) -> Dict[str, Any]:
        """Генерация краткосрочного торгового сигнала"""
        try:
            return self._generate_comprehensive_signal("SHORT")
        except Exception as e:
            logger.error(f"Ошибка генерации краткосрочного сигнала для {self.symbol}: {e}")
            return None

    def _generate_long_term_signal(self) -> Dict[str, Any]:
        """Генерация долгосрочного торгового сигнала"""
        try:
            return self._generate_comprehensive_signal("LONG")
        except Exception as e:
            logger.error(f"Ошибка генерации долгосрочного сигнала для {self.symbol}: {e}")
            return None

    def _generate_comprehensive_signal(self, signal_term_type: str) -> Dict[str, Any]:
        """Комплексная генерация торгового сигнала"""
        try:
            # Собираем все сигналы
            all_signals = []
            signal_weights = {}

            for timeframe, signals in self.signals.items():
                weight = self._get_timeframe_weight(timeframe, signal_term_type)
                signal_weights[timeframe] = weight

                for signal in signals:
                    all_signals.append({
                        "timeframe": timeframe,
                        "signal": signal,
                        "weight": weight
                    })

            if not all_signals:
                return None

            # Анализируем индикаторы для определения направления сигнала
            buy_score = 0
            sell_score = 0
            signal_messages = []

            # Анализ по каждому таймфрейму
            for timeframe in CONFIG["timeframes"]:
                indicators = self.market_data.indicators.get(timeframe)
                if not indicators:
                    continue

                weight = signal_weights.get(timeframe, 1.0)
                timeframe_buy_score, timeframe_sell_score, messages = self._analyze_timeframe_signals(
                    timeframe, indicators, weight
                )

                buy_score += timeframe_buy_score
                sell_score += timeframe_sell_score
                signal_messages.extend(messages)

            # Определяем тип сигнала
            if buy_score > sell_score and buy_score > 2:
                signal_type = "BUY"
                strength = min(buy_score / 10, 1.0)  # Нормализуем до 0-1
            elif sell_score > buy_score and sell_score > 2:
                signal_type = "SELL"
                strength = min(sell_score / 10, 1.0)
            else:
                signal_type = "HOLD"
                strength = 0.5

            # Рассчитываем уверенность в сигнале
            confidence = self._calculate_signal_confidence(signal_type, buy_score, sell_score, signal_term_type)

            # Если уверенность слишком низкая, не генерируем сигнал
            min_confidence_key = f"{signal_term_type.lower()}_term_confidence"
            min_confidence = CONFIG.get(min_confidence_key, 0.6)
            if confidence < min_confidence:
                logger.info(
                    f"Сигнал для {self.symbol} отклонен из-за низкой уверенности: {confidence:.2f} < {min_confidence}")
                return None

            # Формируем сигнал
            signal = {
                "timestamp": datetime.datetime.now().isoformat(),
                "symbol": self.symbol,
                "signal_type": signal_type,
                "term_type": signal_term_type,
                "strength": strength,
                "confidence": confidence,
                "messages": signal_messages,
                "trend": self.trend.copy(),
                "market_cycles": self.market_cycles.copy(),
                "price_predictions": self.price_predictions.copy(),
                "market_info": self._get_market_info(),
                "suggested_actions": self._get_suggested_actions(signal_type, signal_term_type)
            }

            logger.info(
                f"Сгенерирован сигнал {signal_type} для {self.symbol} (тип: {signal_term_type}, сила: {strength:.2f}, уверенность: {confidence:.2f})")
            return signal

        except Exception as e:
            logger.error(f"Ошибка генерации комплексного сигнала для {self.symbol}: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return None

    def _get_timeframe_weight(self, timeframe: str, signal_term_type: str) -> float:
        """Получение веса таймфрейма в зависимости от типа сигнала"""
        if signal_term_type == "SHORT":
            # Для краткосрочных сигналов больше внимания к малым таймфреймам
            weights = {"5m": 2.0, "15m": 1.5, "1h": 1.0, "4h": 0.5}
        elif signal_term_type == "LONG":
            # Для долгосрочных сигналов больше внимания к большим таймфреймам
            weights = {"5m": 0.5, "15m": 0.8, "1h": 1.2, "4h": 2.0}
        else:
            # Для общих сигналов равный вес
            weights = {"5m": 1.0, "15m": 1.0, "1h": 1.0, "4h": 1.0}

        return weights.get(timeframe, 1.0)

    def _analyze_timeframe_signals(self, timeframe: str, indicators: Dict, weight: float) -> Tuple[
        float, float, List[str]]:
        """Анализ сигналов на конкретном таймфрейме"""
        try:
            buy_score = 0
            sell_score = 0
            messages = []

            # Анализ RSI
            rsi = indicators['rsi'].iloc[-1]
            if rsi < CONFIG["rsi_oversold"]:
                buy_score += 2 * weight
                messages.append(f"{timeframe}: RSI перепродан ({rsi:.2f}) ({int(70 * weight)}%)")
            elif rsi > CONFIG["rsi_overbought"]:
                sell_score += 2 * weight
                messages.append(f"{timeframe}: RSI перекуплен ({rsi:.2f}) ({int(70 * weight)}%)")

            # Анализ MACD
            macd_data = indicators['macd']
            macd_line = macd_data['macd_line'].iloc[-1]
            signal_line = macd_data['signal_line'].iloc[-1]

            if macd_line > signal_line:
                buy_score += 1.5 * weight
                messages.append(f"{timeframe}: MACD бычий сигнал ({int(60 * weight)}%)")
            else:
                sell_score += 1.5 * weight
                messages.append(f"{timeframe}: MACD медвежий сигнал ({int(60 * weight)}%)")

            # Анализ трендов EMA
            ema_short = indicators['ema_short'].iloc[-1]
            ema_medium = indicators['ema_medium'].iloc[-1]
            ema_long = indicators['ema_long'].iloc[-1]

            if ema_short > ema_medium > ema_long:
                buy_score += 1 * weight
                messages.append(f"{timeframe}: Восходящий тренд EMA ({int(50 * weight)}%)")
            elif ema_short < ema_medium < ema_long:
                sell_score += 1 * weight
                messages.append(f"{timeframe}: Нисходящий тренд EMA ({int(50 * weight)}%)")

            # Анализ объемов
            volumes = indicators['volumes']
            avg_volume = indicators['avg_volume']
            if len(volumes) > 0 and len(avg_volume) > 0:
                current_volume = volumes.iloc[-1]
                avg_vol = avg_volume.iloc[-1]
                if current_volume > avg_vol * CONFIG["vol_multiplier"]:
                    # Повышенный объем при росте цены - бычий сигнал
                    df = self.market_data.candles.get(timeframe)
                    if df is not None and len(df) >= 2:
                        price_change = df['close'].iloc[-1] - df['close'].iloc[-2]
                        if price_change > 0:
                            buy_score += 1 * weight
                            messages.append(f"{timeframe}: Повышенный объем при росте цены ({int(60 * weight)}%)")
                        else:
                            sell_score += 1 * weight
                            messages.append(f"{timeframe}: Повышенный объем при падении цены ({int(60 * weight)}%)")

            return buy_score, sell_score, messages

        except Exception as e:
            logger.error(f"Ошибка анализа сигналов таймфрейма {timeframe} для {self.symbol}: {e}")
            return 0, 0, []

    def _calculate_signal_confidence(self, signal_type: str, buy_score: float, sell_score: float,
                                     signal_term_type: str) -> float:
        """Расчет уверенности в сигнале"""
        try:
            if signal_type == "HOLD":
                return 0.5

            # Базовая уверенность на основе разности очков
            total_score = buy_score + sell_score
            if total_score == 0:
                return 0.5

            dominant_score = max(buy_score, sell_score)
            confidence = min(dominant_score / total_score, 1.0)

            # Корректировка на основе рыночных циклов
            market_confidence = self.market_cycles.get('confidence', 0.5)
            confidence = (confidence + market_confidence) / 2

            # Корректировка на основе количества подтверждающих сигналов
            signal_count = 0
            for timeframe_signals in self.signals.values():
                signal_count += len(timeframe_signals)

            if signal_count >= 3:
                confidence += 0.1
            elif signal_count >= 5:
                confidence += 0.2

            return min(max(confidence, 0.1), 0.95)  # Ограничиваем от 10% до 95%

        except Exception as e:
            logger.error(f"Ошибка расчета уверенности сигнала для {self.symbol}: {e}")
            return 0.5

    def _get_market_info(self) -> List[str]:
        """Получение информации о рынке"""
        try:
            info = []

            # Основная информация о инструменте
            symbol_name = self.symbol

            info.append(f"Инструмент: {symbol_name}")
            info.append(f"Текущая цена: {self.market_data.last_price:.6f}")
            info.append(f"Изменение за день: {self.market_data.daily_change:+.2f}%")
            info.append(f"Общий тренд: {self.trend.get('общий', 'неопределен')}")

            # Информация о рыночной фазе
            market_phase = self.market_cycles.get('phase', 'неопределенный')
            info.append(f"Рыночная фаза: {market_phase}")

            # Ближайшие уровни поддержки и сопротивления
            if self.market_data.support:
                nearest_support = self.market_data.support[0]['price']
                info.append(f"Ближайшая поддержка: {nearest_support:.6f}")

            if self.market_data.resistance:
                nearest_resistance = self.market_data.resistance[0]['price']
                info.append(f"Ближайшее сопротивление: {nearest_resistance:.6f}")

            return info

        except Exception as e:
            logger.error(f"Ошибка получения информации о рынке для {self.symbol}: {e}")
            return [f"Инструмент: {self.symbol}"]

    def _get_suggested_actions(self, signal_type: str, signal_term_type: str) -> List[str]:
        """Получение рекомендуемых действий"""
        try:
            actions = []
            current_price = self.market_data.last_price

            if signal_type == "BUY":
                actions.append(f"Цена входа: {current_price:.6f}")

                # Ближайший тейк-профит (ближайшее сопротивление)
                if self.market_data.resistance:
                    take_profit = self.market_data.resistance[0]['price']
                    profit_percent = ((take_profit - current_price) / current_price) * 100
                    actions.append(f"Ближайший тейк-профит: {take_profit:.6f} ({profit_percent:.2f}%)")

                # Стоп-лосс (ближайшая поддержка или процент)
                stop_loss_price = current_price * (1 - CONFIG["stop_loss_percent"] / 100)
                if self.market_data.support:
                    support_price = self.market_data.support[0]['price']
                    if support_price < current_price and support_price > stop_loss_price:
                        stop_loss_price = support_price

                stop_loss_percent = ((current_price - stop_loss_price) / current_price) * 100
                actions.append(f"Стоп-лосс: {stop_loss_price:.6f} ({stop_loss_percent:.0f}%)")

                # Долгосрочные цели
                sell_targets = self.long_term_targets.get("sell_targets", [])
                if sell_targets:
                    actions.append("")
                    actions.append("Долгосрочные целевые уровни:")
                    for i, target in enumerate(sell_targets[:3]):  # Первые 3 цели
                        actions.append(
                            f"{i + 1}. {target['price']:.6f} ({target['distance_percent']:.2f}% от текущей) - {target['description']}")

                # Прогнозы цен
                self._add_price_forecasts(actions, signal_term_type)

            elif signal_type == "SELL":
                actions.append(f"Цена выхода: {current_price:.6f}")

                # Ближайший тейк-профит при продаже (ближайшая поддержка)
                if self.market_data.support:
                    take_profit = self.market_data.support[0]['price']
                    profit_percent = ((current_price - take_profit) / current_price) * 100
                    actions.append(f"Ближайший тейк-профит: {take_profit:.6f} ({profit_percent:.2f}%)")

                # Стоп-лосс при продаже (ближайшее сопротивление или процент)
                stop_loss_price = current_price * (1 + CONFIG["stop_loss_percent"] / 100)
                if self.market_data.resistance:
                    resistance_price = self.market_data.resistance[0]['price']
                    if resistance_price > current_price and resistance_price < stop_loss_price:
                        stop_loss_price = resistance_price

                stop_loss_percent = ((stop_loss_price - current_price) / current_price) * 100
                actions.append(f"Стоп-лосс: {stop_loss_price:.6f} ({stop_loss_percent:.0f}%)")

                # Долгосрочные цели для покупки обратно
                buy_targets = self.long_term_targets.get("buy_targets", [])
                if buy_targets:
                    actions.append("")
                    actions.append("Долгосрочные уровни для покупки обратно:")
                    for i, target in enumerate(buy_targets[:3]):  # Первые 3 цели
                        actions.append(
                            f"{i + 1}. {target['price']:.6f} ({target['distance_percent']:.2f}% от текущей) - {target['description']}")

                # Прогнозы цен
                self._add_price_forecasts(actions, signal_term_type)

            else:  # HOLD
                actions.append("Рекомендуется воздержаться от торговли")
                actions.append("Ожидайте более четких сигналов")

                # Можем добавить уровни наблюдения
                if self.market_data.support and self.market_data.resistance:
                    actions.append(
                        f"Наблюдайте за диапазоном: {self.market_data.support[0]['price']:.6f} - {self.market_data.resistance[0]['price']:.6f}")

            return actions

        except Exception as e:
            logger.error(f"Ошибка получения рекомендуемых действий для {self.symbol}: {e}")
            return ["Ошибка получения рекомендаций"]

    def _add_price_forecasts(self, actions: List[str], signal_term_type: str) -> None:
        """Добавление прогнозов цен в список действий"""
        try:
            predictions = self.price_predictions
            if not predictions:
                return

            actions.append("")
            actions.append("Прогнозы движения цены:")

            # Краткосрочный прогноз (6 часов)
            short_term = predictions.get("short_term", {})
            if short_term.get("expected", 0) > 0:
                expected = short_term["expected"]
                min_price = short_term["min"]
                max_price = short_term["max"]
                current_price = self.market_data.last_price

                change_percent = ((expected - current_price) / current_price) * 100
                direction = "↗️" if change_percent > 0 else "↘️" if change_percent < 0 else "➡️"

                actions.append(f"6 часов: {direction} {expected:.6f} (±{abs(change_percent):.2f}%)")
                actions.append(f"  Диапазон: {min_price:.6f} - {max_price:.6f}")

            # Среднесрочный прогноз (24 часа)
            medium_term = predictions.get("medium_term", {})
            if medium_term.get("expected", 0) > 0:
                expected = medium_term["expected"]
                min_price = medium_term["min"]
                max_price = medium_term["max"]
                current_price = self.market_data.last_price

                change_percent = ((expected - current_price) / current_price) * 100
                direction = "↗️" if change_percent > 0 else "↘️" if change_percent < 0 else "➡️"

                actions.append(f"24 часа: {direction} {expected:.6f} (±{abs(change_percent):.2f}%)")
                actions.append(f"  Диапазон: {min_price:.6f} - {max_price:.6f}")

            # Долгосрочный прогноз (7 дней) - только для долгосрочных или общих сигналов
            if signal_term_type in ["LONG", "ALL"]:
                long_term = predictions.get("long_term", {})
                if long_term.get("expected", 0) > 0:
                    expected = long_term["expected"]
                    min_price = long_term["min"]
                    max_price = long_term["max"]
                    current_price = self.market_data.last_price

                    change_percent = ((expected - current_price) / current_price) * 100
                    direction = "↗️" if change_percent > 0 else "↘️" if change_percent < 0 else "➡️"

                    actions.append(f"7 дней: {direction} {expected:.6f} (±{abs(change_percent):.2f}%)")
                    actions.append(f"  Диапазон: {min_price:.6f} - {max_price:.6f}")

        except Exception as e:
            logger.error(f"Ошибка добавления прогнозов цен для {self.symbol}: {e}")
            возможное
            дно(перепроданность + разворот)
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

            # Проверка на