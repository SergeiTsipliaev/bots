#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для отправки тестового сигнала через Telegram.
Используйте этот скрипт для проверки работы уведомлений без запуска всего бота.
"""

import asyncio
import json
import argparse
import sys
import os
import requests
from datetime import datetime

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем конфигурацию и логгер
from config import CONFIG, COIN_DESCRIPTIONS
from cati_bot.utils import logger

async def send_test_message(chat_id, message):
    """Отправка тестового сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message
        }
        
        print(f"Отправка тестового сообщения в чат {chat_id}...")
        
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        if data.get("ok"):
            print(f"✅ Сообщение успешно отправлено!")
            return True
        else:
            error_msg = data.get("description", "Неизвестная ошибка")
            print(f"❌ Ошибка отправки сообщения: {error_msg}")
            return False
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения: {e}")
        return False

async def send_test_signal(chat_id, symbol):
    """Отправка тестового торгового сигнала"""
    try:
        # Создаем тестовый сигнал
        test_signal = create_test_signal(symbol)
        
        # Форматируем сообщение
        message = format_signal_message(test_signal)
        
        # Отправляем сообщение
        return await send_test_message(chat_id, message)
    except Exception as e:
        print(f"❌ Ошибка при подготовке тестового сигнала: {e}")
        return False

def create_test_signal(symbol):
    """Создание тестового сигнала"""
    # Базовая структура сигнала
    signal = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "signal_type": "BUY",
        "strength": 0.75,
        "price": 1000.00,
        "messages": [
            "5m: RSI перепродан (28.35) (70%)",
            "15m: RSI перепродан (24.12) (70%)",
            "1h: Повышенный объем при росте цены (60%)"
        ],
        "suggested_actions": [
            "Цена входа: 1000.00",
            "Ближайший тейк-профит: 1130.00 (13.00%)",
            "Стоп-лосс: 970.00 (3%)",
            "",
            "Долгосрочные целевые уровни:",
            "1. 1450.00 (45.00% от текущей) - Уровень сопротивления #2",
            "2. 1320.00 (32.00% от текущей) - Уровень сопротивления #1",
            "3. 1200.00 (20.00% от текущей) - Прогнозный максимум через 7 дней",
            "",
            "Прогнозы движения цены:",
            "6 часов: ↗️ 1020.00 (±2.00%)",
            "  Диапазон: 980.00 - 1040.00",
            "24 часа: ↗️ 1080.00 (±8.00%)",
            "  Диапазон: 920.00 - 1130.00",
            "7 дней: ↗️ 1200.00 (±20.00%)",
            "  Диапазон: 800.00 - 1200.00"
        ],
        "market_info": [
            f"Инструмент: {symbol}",
            "Текущая цена: 1000.00",
            "Изменение за день: +5.25%",
            "Общий тренд: восходящий",
            "Рыночная фаза: бычий",
            "Ближайшая поддержка: 970.00",
            "Ближайшее сопротивление: 1130.00"
        ],
        "trend": {
            "5m": "восходящий",
            "15m": "восходящий",
            "1h": "восходящий",
            "4h": "восходящий",
            "общий": "восходящий"
        },
        "market_cycles": {
            "phase": "бычий",
            "confidence": 0.8,
            "patterns": [
                {
                    "pattern": "продолжение восходящего тренда",
                    "confidence": 0.7,
                    "description": "Признаки продолжения бычьего тренда"
                },
                {
                    "pattern": "пробой уровня сопротивления",
                    "confidence": 0.65,
                    "description": "Пробой важного уровня сопротивления"
                }
            ],
            "price_change_percent": 8.5
        },
        "price_predictions": {
            "short_term": {
                "min": 980.00,
                "max": 1040.00,
                "expected": 1020.00,
                "confidence": 0.8
            },
            "medium_term": {
                "min": 920.00,
                "max": 1130.00,
                "expected": 1080.00,
                "confidence": 0.6
            },
            "long_term": {
                "min": 800.00,
                "max": 1200.00,
                "expected": 1200.00,
                "confidence": 0.4
            }
        }
    }
    
    # Описание монеты, если есть
    coin_description = COIN_DESCRIPTIONS.get(symbol, "")
    if coin_description:
        description_line = f"Инструмент: {symbol} - {coin_description}"
        signal["market_info"][0] = description_line
    
    return signal

def format_signal_message(signal):
    """Форматирование сообщения сигнала"""
    emoji_map = {
        'BUY': '🟢 ПОКУПКА',
        'SELL': '🔴 ПРОДАЖА',
        'HOLD': '⚪ ОЖИДАНИЕ'
    }
    
    message = f"{emoji_map.get(signal['signal_type'], signal['signal_type'])} | {signal['symbol']}\n\n"
    
    # Добавляем информацию о рынке
    message += "\n".join(signal['market_info']) + "\n\n"
    
    # Добавляем тренды
    message += "Тренды:\n"
    for timeframe, trend in signal['trend'].items():
        if timeframe == 'общий':
            continue
        message += f"- {timeframe}: {trend}\n"
    message += "\n"
    
    # Добавляем информацию о рыночной фазе
    if 'market_cycles' in signal and signal['market_cycles'].get('phase'):
        market_phase = signal['market_cycles'].get('phase')
        confidence = signal['market_cycles'].get('confidence', 0) * 100
        message += f"Рыночная фаза: {market_phase} (уверенность: {confidence:.0f}%)\n\n"
        
        # Добавляем замеченные паттерны, если они есть
        patterns = signal['market_cycles'].get('patterns', [])
        if patterns:
            message += "Замеченные паттерны:\n"
            for pattern in patterns:
                message += f"- {pattern['pattern']} ({pattern['confidence'] * 100:.0f}%)\n"
            message += "\n"
    
    # Добавляем силу сигнала
    if signal['signal_type'] != 'HOLD':
        message += f"Сила сигнала: {signal['strength'] * 100:.0f}%\n\n"
    
    # Добавляем рекомендуемые действия
    message += "Рекомендуемые действия:\n"
    message += "\n".join(signal['suggested_actions']) + "\n\n"
    
    # Добавляем причины сигнала
    if signal['messages']:
        message += "Причины сигнала:\n"
        message += "\n".join(signal['messages']) + "\n"
    
    return message

async def main():
    parser = argparse.ArgumentParser(description="Отправка тестового сигнала через Telegram")
    parser.add_argument("--chat_id", help="ID чата для отправки (по умолчанию из config.py)", default=CONFIG["telegram_chat_id"])
    parser.add_argument("--symbol", help="Символ для тестового сигнала", default="BTCUSDT")
    parser.add_argument("--message", help="Простое тестовое сообщение вместо сигнала")
    args = parser.parse_args()
    
    # Проверяем, что токен бота настроен
    if not CONFIG["telegram_bot_token"]:
        print("❌ Не указан токен Telegram бота в config.py")
        return 1
    
    # Проверяем, что chat_id указан
    if not args.chat_id:
        print("❌ Не указан ID чата в аргументах или в config.py")
        return 1
    
    # Если указано простое сообщение, отправляем его
    if args.message:
        success = await send_test_message(args.chat_id, args.message)
    else:
        # Иначе отправляем тестовый сигнал
        symbol = args.symbol.upper()
        if symbol not in CONFIG["available_symbols"]:
            print(f"⚠️ Символ {symbol} не найден в списке доступных. Используется тестовый символ.")
        
        success = await send_test_signal(args.chat_id, symbol)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))