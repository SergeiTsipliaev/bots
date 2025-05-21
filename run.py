#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Основной файл для запуска бота анализа криптовалют.
"""

import asyncio
import requests
import argparse
from typing import List

from config import CONFIG
from cati_bot.utils import logger
from cati_bot.trading_bot import TradingBot


async def main() -> int:
    """Главная функция для запуска бота"""
    try:
        # Парсим аргументы командной строки
        parser = argparse.ArgumentParser(description="Бот для анализа криптовалют")
        parser.add_argument("--symbols", type=str, help="Список символов для анализа, разделенный запятыми", default="")
        parser.add_argument("--interval", type=int, help="Интервал анализа в минутах", default=CONFIG["time_interval_minutes"])
        args = parser.parse_args()
        
        # Определяем символы для анализа
        symbols_to_analyze = []
        if args.symbols:
            symbols_to_analyze = [s.strip().upper() for s in args.symbols.split(",")]
            # Проверяем, что все символы есть в списке доступных
            for symbol in symbols_to_analyze:
                if symbol not in CONFIG["available_symbols"]:
                    logger.error(f"Символ {symbol} не найден в списке доступных")
                    return 1
        else:
            # Если символы не указаны, используем все доступные
            symbols_to_analyze = CONFIG["available_symbols"]
        
        # Обновляем интервал анализа, если указан
        if args.interval:
            CONFIG["time_interval_minutes"] = args.interval
        
        logger.info("Запуск бота для анализа криптовалют...")
        logger.info(f"Монеты для анализа: {', '.join(symbols_to_analyze)}")
        logger.info(f"Интервал обновления: {CONFIG['time_interval_minutes']} минут")
        
        # Проверка подключения к API Bybit
        try:
            response = requests.get(f"{CONFIG['api_base_url']}/v5/market/time")
            response.raise_for_status()
            data = response.json()
            if data.get('retCode') == 0:
                logger.info("Подключение к Bybit API успешно")
            else:
                logger.error(f"Ошибка API Bybit: {data.get('retMsg')}")
                raise Exception(f"Ошибка API Bybit: {data.get('retMsg')}")
        except Exception as e:
            logger.error(f"Ошибка подключения к API: {e}")
            raise Exception("Не удалось подключиться к API биржи. Проверьте соединение с интернетом или работоспособность API.")
        
        # Создаем экземпляр бота
        bot = TradingBot()
        
        # Инициализируем бота с указанными символами
        initialized = await bot.initialize(symbols_to_analyze)
        if not initialized:
            raise Exception("Не удалось инициализировать бота")
        
        # Запускаем бота
        await bot.start()
        
        # Держим основной поток активным
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)...")
        if 'bot' in locals():
            await bot.stop()
        logger.info("Бот остановлен")
        return 0
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        logger.info("Бот не запущен из-за ошибки.")
        return 1


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)...")
        logger.info("Бот остановлен")