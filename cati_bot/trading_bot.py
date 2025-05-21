#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной класс бота для анализа криптовалют.
"""

import asyncio
import datetime
from typing import Dict, Any, List

from config import CONFIG
from cati_bot.utils import logger
from cati_bot.market_data import MarketData
from cati_bot.signal_analyzer import SignalAnalyzer
from cati_bot.notification import NotificationSender


class TradingBot:
    """Основной класс бота"""

    def __init__(self):
        self.market_data_cache = {}  # Кэш объектов MarketData для разных символов
        self.notification_sender = NotificationSender()
        self.is_running = False
        self._stop_event = None
        self.symbols_to_analyze = []  # Список символов для анализа
        self.user_requests = {}  # Запросы от пользователей для анализа конкретных монет

    async def initialize(self, symbols: List[str] = None) -> bool:
        """Метод инициализации бота"""
        try:
            logger.info("Инициализация бота...")
            
            # Определяем список символов для анализа
            self.symbols_to_analyze = symbols or [CONFIG["default_symbol"]]
            
            # Инициализируем данные для каждого символа
            for symbol in self.symbols_to_analyze:
                # Создаем объект MarketData для символа
                market_data = MarketData(symbol)
                
                # Инициализируем данные
                data_initialized = await market_data.initialize()
                if not data_initialized:
                    logger.error(f"Не удалось инициализировать данные для {symbol}")
                    continue
                
                # Сохраняем в кэше
                self.market_data_cache[symbol] = market_data
                logger.info(f"Данные для {symbol} инициализированы успешно")
            
            # Запускаем обработку Telegram-обновлений
            asyncio.create_task(self.notification_sender.poll_updates())
            
            logger.info("Бот инициализирован успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            return False

    async def start(self) -> bool:
        """Метод запуска бота"""
        if self.is_running:
            logger.info("Бот уже запущен")
            return False
        
        logger.info("Запуск бота...")
        self.is_running = True
        self._stop_event = asyncio.Event()
        
        # Запускаем первую итерацию сразу
        await self.run_analysis_iteration()
        
        # Запускаем бесконечный цикл анализа
        asyncio.create_task(self._analysis_loop())
        
        # Запускаем обработку запросов пользователей
        asyncio.create_task(self._process_user_requests_loop())
        
        logger.info(f"Бот запущен, интервал обновления: {CONFIG['time_interval_minutes']} минут")
        return True

    async def _analysis_loop(self) -> None:
        """Метод для периодического запуска анализа"""
        while not self._stop_event.is_set():
            # Ждем указанное время
            await asyncio.sleep(CONFIG["time_interval_minutes"] * 60)
            
            # Если бот не остановлен, запускаем анализ
            if not self._stop_event.is_set():
                await self.run_analysis_iteration()

    async def _process_user_requests_loop(self) -> None:
        """Метод для обработки запросов пользователей через Telegram"""
        while not self._stop_event.is_set():
            try:
                # Проверяем наличие запросов на анализ
                requests = self.notification_sender.get_analyze_requests()
                
                for request in requests:
                    symbol = request["symbol"]
                    chat_id = request["chat_id"]
                    
                    # Анализируем запрошенную монету
                    await self.analyze_symbol(symbol, chat_id)
                
                # Небольшая пауза перед следующей проверкой
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка обработки запросов пользователей: {e}")
                await asyncio.sleep(5)

    def stop(self) -> bool:
        """Метод остановки бота"""
        if not self.is_running:
            logger.info("Бот уже остановлен")
            return False
        
        logger.info("Остановка бота...")
        self._stop_event.set()
        self.is_running = False
        logger.info("Бот остановлен")
        return True

    async def run_analysis_iteration(self) -> bool:
        """Метод выполнения одной итерации анализа для всех символов"""
        logger.info("=== НОВАЯ ИТЕРАЦИЯ АНАЛИЗА ===")
        logger.info(f"Время: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        success = True
        
        # Запускаем анализ для каждого символа
        for symbol in self.symbols_to_analyze:
            try:
                # Анализируем символ
                await self.analyze_symbol(symbol)
            except Exception as e:
                logger.error(f"Ошибка анализа {symbol}: {e}")
                success = False
        
        logger.info("Итерация анализа завершена")
        return success

    async def analyze_symbol(self, symbol: str, chat_id: str = None) -> bool:
        """Метод для анализа конкретного символа"""
        try:
            logger.info(f"Анализ символа {symbol}")
            
            # Проверяем наличие данных в кэше
            if symbol not in self.market_data_cache:
                # Если данных нет, инициализируем их
                market_data = MarketData(symbol)
                initialized = await market_data.initialize()
                if not initialized:
                    logger.error(f"Не удалось инициализировать данные для {symbol}")
                    return False
                
                # Сохраняем в кэше
                self.market_data_cache[symbol] = market_data
            else:
                # Обновляем существующие данные
                await self.market_data_cache[symbol].update()
            
            # Получаем объект MarketData
            market_data = self.market_data_cache[symbol]
            
            # Создаем анализатор сигналов
            signal_analyzer = SignalAnalyzer(market_data)
            
            # Анализируем данные
            analysis_result = signal_analyzer.analyze()
            
            # Получаем торговый сигнал
            signal = signal_analyzer.last_signal
            
            # Проверяем, был ли сгенерирован сигнал
            if not signal:
                logger.info(f"Для {symbol} не сгенерирован сигнал покупки или продажи")
                return True  # Возвращаем True, так как анализ произведён успешно
            
            # Отправляем уведомление о сигнале
            if chat_id:
                # Если указан конкретный chat_id, отправляем только ему
                message = self.notification_sender._format_signal_message(signal)
                await self.notification_sender._send_telegram_message(message, chat_id)
            else:
                # Иначе отправляем через стандартный механизм (подписчикам)
                await self.notification_sender.send_signal_notification(signal)
            
            logger.info(f"Анализ {symbol} выполнен успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка анализа {symbol}: {e}")
            
            # Если был указан конкретный chat_id, отправляем сообщение об ошибке
            if chat_id:
                await self.notification_sender._send_telegram_message(
                    f"❌ Ошибка при анализе {symbol}: {str(e)}",
                    chat_id
                )
            
            return False

    async def add_symbol(self, symbol: str) -> bool:
        """Добавление нового символа для анализа"""
        if symbol in self.symbols_to_analyze:
            logger.info(f"Символ {symbol} уже анализируется")
            return True
        
        try:
            # Инициализируем данные для нового символа
            market_data = MarketData(symbol)
            initialized = await market_data.initialize()
            
            if not initialized:
                logger.error(f"Не удалось инициализировать данные для {symbol}")
                return False
            
            # Добавляем в кэш и список символов
            self.market_data_cache[symbol] = market_data
            self.symbols_to_analyze.append(symbol)
            
            logger.info(f"Символ {symbol} добавлен для анализа")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления символа {symbol}: {e}")
            return False

    async def remove_symbol(self, symbol: str) -> bool:
        """Удаление символа из списка анализируемых"""
        if symbol not in self.symbols_to_analyze:
            logger.info(f"Символ {symbol} не анализируется")
            return True
        
        try:
            # Удаляем из списка и кэша
            self.symbols_to_analyze.remove(symbol)
            if symbol in self.market_data_cache:
                del self.market_data_cache[symbol]
            
            logger.info(f"Символ {symbol} удален из анализа")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления символа {symbol}: {e}")
            return False