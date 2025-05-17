#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Класс для анализа торговых сигналов криптовалют.
Анализирует рыночные данные и генерирует торговые сигналы.
"""

import datetime
from typing import Dict, List, Any
import pandas as pd

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
            
            # Генерация торгового сигнала
            self._generate_trade_signal()
            
            logger.info(f"Анализ {self.symbol} завершен")
            return True
        except Exception as e:
            logger.error(f"Ошибка анализа {self.symbol}: {e}")
            return False

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

    def _generate_trade_signal(self) -> Dict:
        """Метод для генерации торгового сигнала на основе всех данных"""
        # Весовые коэффициенты для разных таймфреймов
        weights = {
            '5m': 0.15,
            '15m': 0.25,
            '1h': 0.3,
            '4h': 0.3
        }
        
        buy_signal_strength = 0
        sell_signal_strength = 0
        buy_messages = []
        sell_messages = []
        
        # Анализируем сигналы по всем таймфреймам
        for timeframe, signals in self.signals.items():
            weight = weights.get(timeframe, 0.25)
            
            # Суммируем силу сигналов на покупку
            for signal in signals['buy']:
                buy_signal_strength += signal['strength'] * weight
                buy_messages.append(f"{timeframe}: {signal['message']} ({signal['strength'] * 100:.0f}%)")
            
            # Суммируем силу сигналов на продажу
            for signal in signals['sell']:
                sell_signal_strength += signal['strength'] * weight
                sell_messages.append(f"{timeframe}: {signal['message']} ({signal['strength'] * 100:.0f}%)")
        
        # Нормализуем силу сигналов (максимум 1.0)
        buy_signal_strength = min(buy_signal_strength, 1.0)
        sell_signal_strength = min(sell_signal_strength, 1.0)
        
        current_price = self.market_data.last_price
        
        # Определяем тип сигнала
        signal_type = 'HOLD'  # По умолчанию - удержание позиции
        signal_strength = 0
        messages = []
        suggested_actions = []
        
        # Порог для генерации сигнала (40% от максимальной силы)
        threshold = 0.4
        
        if buy_signal_strength > threshold and buy_signal_strength > sell_signal_strength:
            signal_type = 'BUY'
            signal_strength = buy_signal_strength
            messages = buy_messages
            
            # Ближайший уровень сопротивления для тейк-профита
            take_profit = (self.market_data.resistance[0]['price'] 
                          if self.market_data.resistance 
                          else current_price * (1 + CONFIG["take_profit_percent"] / 100))
                
            # Уровень стоп-лосса
            stop_loss = current_price * (1 - CONFIG["stop_loss_percent"] / 100)
            
            suggested_actions.append(f"Цена входа: {current_price:.6f}")
            suggested_actions.append(f"Тейк-профит: {take_profit:.6f} ({((take_profit/current_price - 1) * 100):.2f}%)")
            suggested_actions.append(f"Стоп-лосс: {stop_loss:.6f} ({CONFIG['stop_loss_percent']}%)")
        
        elif sell_signal_strength > threshold and sell_signal_strength > buy_signal_strength:
            signal_type = 'SELL'
            signal_strength = sell_signal_strength
            messages = sell_messages
            
            # Ближайший уровень поддержки для тейк-профита шорта
            take_profit = (self.market_data.support[0]['price'] 
                          if self.market_data.support 
                          else current_price * (1 - CONFIG["take_profit_percent"] / 100))
                
            # Уровень стоп-лосса для шорта
            stop_loss = current_price * (1 + CONFIG["stop_loss_percent"] / 100)
            
            suggested_actions.append(f"Цена входа (шорт): {current_price:.6f}")
            suggested_actions.append(f"Тейк-профит: {take_profit:.6f} ({((1 - take_profit/current_price) * 100):.2f}%)")
            suggested_actions.append(f"Стоп-лосс: {stop_loss:.6f} ({CONFIG['stop_loss_percent']}%)")
        
        # Общая информация о рынке
        market_info = [
            f"Инструмент: {self.symbol}",
            f"Текущая цена: {current_price:.6f}",
            f"Изменение за день: {self.market_data.daily_change:.2f}%",
            f"Общий тренд: {self.trend['общий']}",
            f"Ближайшая поддержка: {self.market_data.support[0]['price']:.6f}" if self.market_data.support else "Ближайшая поддержка: не определена",
            f"Ближайшее сопротивление: {self.market_data.resistance[0]['price']:.6f}" if self.market_data.resistance else "Ближайшее сопротивление: не определено"
        ]
        
        # Формируем итоговый сигнал
        self.last_signal = {
            "timestamp": datetime.datetime.now().isoformat(),
            "symbol": self.symbol,
            "signal_type": signal_type,
            "strength": signal_strength,
            "price": current_price,
            "messages": messages,
            "suggested_actions": suggested_actions,
            "market_info": market_info,
            "trend": self.trend
        }
        
        logger.info(f"Сгенерирован сигнал для {self.symbol}: {signal_type} (сила: {signal_strength * 100:.0f}%)")
        
        return self.last_signal