#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Класс для отправки уведомлений о торговых сигналах.
Обеспечивает обработку команд Telegram-бота и отправку уведомлений.
"""

import asyncio
import requests
import json
from typing import Dict, Any, List, Optional

from config import CONFIG, COIN_DESCRIPTIONS
from cati_bot.utils import logger


class NotificationSender:
    """Класс для отправки уведомлений и обработки Telegram-команд"""

    def __init__(self):
        # Проверяем, что настроены Telegram-параметры
        self.telegram_enabled = bool(CONFIG["telegram_bot_token"] and CONFIG["telegram_chat_id"])
        
        # Отслеживание последнего update_id
        self.last_update_id = 0
        
        # Словарь для отслеживания подписок пользователей на монеты
        self.user_subscriptions = {}  # {chat_id: [coins]}
        
        # Временные данные для поддержки диалога с пользователем
        self.user_context = {}  # {chat_id: {'state': 'wait_for_coin', 'data': {}}}

    async def send_signal_notification(self, signal: Dict[str, Any]) -> bool:
        """Метод для отправки уведомления о торговом сигнале"""
        try:
            # Формируем сообщение
            message = self._format_signal_message(signal)
            
            # Выводим в консоль
            logger.info("=== ТОРГОВЫЙ СИГНАЛ ===")
            logger.info(message)
            
            # Отправляем в Telegram, если включено
            if self.telegram_enabled:
                # Получаем все чаты, подписанные на данную монету
                symbol = signal['symbol']
                for chat_id, symbols in self.user_subscriptions.items():
                    # Если пользователь подписан на эту монету или на все монеты
                    if symbol in symbols or 'ALL' in symbols:
                        await self._send_telegram_message(message, chat_id)
                
                # Если нет подписок, отправляем в стандартный чат
                if not self.user_subscriptions:
                    await self._send_telegram_message(message, CONFIG["telegram_chat_id"])
            
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            return False

    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Метод для форматирования сообщения"""
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
        
        # Добавляем силу сигнала
        if signal['signal_type'] != 'HOLD':
            message += f"Сила сигнала: {signal['strength'] * 100:.0f}%\n\n"
            
            # Добавляем рекомендуемые действия
            message += "Рекомендуемые действия:\n"
            message += "\n".join(signal['suggested_actions']) + "\n\n"
            
            # Добавляем причины
            if signal['messages']:
                message += "Причины сигнала:\n"
                message += "\n".join(signal['messages']) + "\n"
        
        return message

    async def _send_telegram_message(self, message: str, chat_id: str) -> bool:
        """Метод для отправки сообщения в Telegram"""
        try:
            if not CONFIG["telegram_bot_token"]:
                logger.info("Отправка в Telegram пропущена: не настроен токен")
                return False
            
            logger.info(f"Отправка сообщения в Telegram (chat_id: {chat_id})...")
            
            url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Сообщение успешно отправлено в Telegram (chat_id: {chat_id})")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False

    async def poll_updates(self) -> None:
        """Метод для периодического опроса обновлений Telegram"""
        if not self.telegram_enabled:
            logger.warning("Telegram не настроен. Опрос обновлений отключен.")
            return
        
        while True:
            try:
                await self._check_telegram_updates()
                # Пауза перед следующей проверкой
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка при опросе Telegram: {e}")
                await asyncio.sleep(10)  # Увеличенная пауза в случае ошибки

    async def _check_telegram_updates(self) -> None:
        """Проверка новых сообщений в Telegram"""
        try:
            url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/getUpdates"
            params = {
                "offset": self.last_update_id + 1,
                "timeout": 30
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            updates = response.json()
            
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    # Обновляем последний update_id
                    self.last_update_id = max(self.last_update_id, update["update_id"])
                    
                    # Обрабатываем сообщение
                    if "message" in update and "text" in update["message"]:
                        await self._process_message(update["message"])
        except Exception as e:
            logger.error(f"Ошибка при получении обновлений Telegram: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Обработка сообщения от пользователя"""
        try:
            chat_id = str(message["chat"]["id"])
            text = message["text"]
            user_name = message["from"].get("username", "Пользователь")
            
            logger.info(f"Получено сообщение от {user_name} ({chat_id}): {text}")
            
            # Инициализируем контекст пользователя, если его нет
            if chat_id not in self.user_context:
                self.user_context[chat_id] = {"state": "idle", "data": {}}
            
            # Если у пользователя не инициализированы подписки, создаем их
            if chat_id not in self.user_subscriptions:
                self.user_subscriptions[chat_id] = []
            
            # Проверяем контекст пользователя (если ожидаем ответа в диалоге)
            if self.user_context[chat_id]["state"] != "idle":
                await self._process_context_dialog(chat_id, text)
                return
            
            # Обработка команд
            if text.startswith("/"):
                await self._process_command(chat_id, text)
            else:
                # Отправляем помощь по использованию бота
                await self._send_help_message(chat_id)
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

    async def _process_command(self, chat_id: str, text: str) -> None:
        """Обработка команды от пользователя"""
        command = text.split()[0].lower()
        
        if command == "/start" or command == "/help":
            await self._send_help_message(chat_id)
        
        elif command == "/subscribe":
            # Переходим в режим выбора монеты для подписки
            self.user_context[chat_id] = {"state": "wait_for_subscribe", "data": {}}
            await self._send_available_coins(chat_id)
        
        elif command == "/unsubscribe":
            # Переходим в режим выбора монеты для отписки
            self.user_context[chat_id] = {"state": "wait_for_unsubscribe", "data": {}}
            await self._send_user_subscriptions(chat_id)
        
        elif command == "/analyze":
            # Переходим в режим выбора монеты для анализа
            self.user_context[chat_id] = {"state": "wait_for_analyze", "data": {}}
            await self._send_available_coins(chat_id)
        
        elif command == "/list":
            # Показываем список доступных монет
            await self._send_available_coins(chat_id)
        
        elif command == "/mycoins":
            # Показываем подписки пользователя
            await self._send_user_subscriptions(chat_id)
        
        else:
            # Неизвестная команда
            await self._send_telegram_message("Неизвестная команда. Используйте /help для получения списка команд.", chat_id)

    async def _process_context_dialog(self, chat_id: str, text: str) -> None:
        """Обработка диалога с пользователем в зависимости от контекста"""
        state = self.user_context[chat_id]["state"]
        
        if state == "wait_for_subscribe":
            # Подписка на монету
            await self._handle_subscribe(chat_id, text)
            
        elif state == "wait_for_unsubscribe":
            # Отписка от монеты
            await self._handle_unsubscribe(chat_id, text)
            
        elif state == "wait_for_analyze":
            # Запрос на анализ монеты
            await self._handle_analyze_request(chat_id, text)
            
        # Сбрасываем состояние диалога
        self.user_context[chat_id] = {"state": "idle", "data": {}}

    async def _handle_subscribe(self, chat_id: str, text: str) -> None:
        """Обработка подписки на монету"""
        if text == "ВСЕ":
            # Подписка на все монеты
            self.user_subscriptions[chat_id] = ["ALL"]
            await self._send_telegram_message("✅ Вы успешно подписались на уведомления по ВСЕМ монетам!", chat_id)
            return
            
        # Проверяем, что монета есть в списке доступных
        coin = text.upper()
        if coin not in CONFIG["available_symbols"]:
            await self._send_telegram_message(f"❌ Монета {coin} не найдена в списке доступных.", chat_id)
            return
        
        # Добавляем монету в подписки пользователя
        if "ALL" in self.user_subscriptions[chat_id]:
            # Если была подписка на все, удаляем ее и добавляем конкретную монету
            self.user_subscriptions[chat_id] = [coin]
        elif coin not in self.user_subscriptions[chat_id]:
            self.user_subscriptions[chat_id].append(coin)
        
        # Отправляем подтверждение
        await self._send_telegram_message(f"✅ Вы успешно подписались на уведомления по {coin}!", chat_id)

    async def _handle_unsubscribe(self, chat_id: str, text: str) -> None:
        """Обработка отписки от монеты"""
        if text == "ВСЕ":
            # Отписываемся от всех монет
            self.user_subscriptions[chat_id] = []
            await self._send_telegram_message("✅ Вы отписались от всех уведомлений!", chat_id)
            return
            
        # Проверяем, что пользователь подписан на эту монету
        coin = text.upper()
        if coin in self.user_subscriptions[chat_id]:
            self.user_subscriptions[chat_id].remove(coin)
            await self._send_telegram_message(f"✅ Вы успешно отписались от уведомлений по {coin}!", chat_id)
        elif "ALL" in self.user_subscriptions[chat_id]:
            # Если была подписка на все, удаляем ее
            self.user_subscriptions[chat_id] = [c for c in CONFIG["available_symbols"] if c != coin]
            await self._send_telegram_message(f"✅ Вы успешно отписались от уведомлений по {coin}!", chat_id)
        else:
            await self._send_telegram_message(f"❓ Вы не были подписаны на {coin}.", chat_id)

    async def _handle_analyze_request(self, chat_id: str, text: str) -> None:
        """Обработка запроса на анализ монеты"""
        coin = text.upper()
        if coin not in CONFIG["available_symbols"]:
            await self._send_telegram_message(f"❌ Монета {coin} не найдена в списке доступных.", chat_id)
            return
        
        # Отправляем сообщение, что запрос на анализ получен
        await self._send_telegram_message(f"⏳ Запрос на анализ {coin} принят. Результаты будут отправлены в ближайшее время.", chat_id)
        
        # Устанавливаем выбранную монету в user_context для дальнейшего использования
        self.user_context[chat_id]["data"]["analyze_symbol"] = coin

    async def _send_help_message(self, chat_id: str) -> None:
        """Отправка справочного сообщения"""
        message = (
            "🤖 *Бот для анализа криптовалют* 🤖\n\n"
            "Команды:\n"
            "/subscribe - Подписаться на уведомления по монете\n"
            "/unsubscribe - Отписаться от уведомлений по монете\n"
            "/analyze - Запросить анализ монеты\n"
            "/list - Показать список доступных монет\n"
            "/mycoins - Показать мои подписки\n"
            "/help - Показать эту справку\n\n"
            "Бот анализирует рынок и отправляет торговые сигналы."
        )
        await self._send_telegram_message(message, chat_id)

    async def _send_available_coins(self, chat_id: str) -> None:
        """Отправка списка доступных монет"""
        message = "📋 Доступные монеты:\n\n"
        
        for symbol in CONFIG["available_symbols"]:
            description = COIN_DESCRIPTIONS.get(symbol, "")
            message += f"• {symbol} - {description}\n"
        
        message += "\nТакже доступен выбор 'ВСЕ' для подписки на все монеты."
        
        await self._send_telegram_message(message, chat_id)

    async def _send_user_subscriptions(self, chat_id: str) -> None:
        """Отправка списка подписок пользователя"""
        if chat_id not in self.user_subscriptions or not self.user_subscriptions[chat_id]:
            await self._send_telegram_message("У вас нет активных подписок.", chat_id)
            return
        
        if "ALL" in self.user_subscriptions[chat_id]:
            await self._send_telegram_message("Вы подписаны на ВСЕ монеты! 🌟", chat_id)
            return
        
        message = "📊 Ваши подписки:\n\n"
        for symbol in self.user_subscriptions[chat_id]:
            description = COIN_DESCRIPTIONS.get(symbol, "")
            message += f"• {symbol} - {description}\n"
        
        await self._send_telegram_message(message, chat_id)

    def get_analyze_requests(self) -> List[Dict[str, Any]]:
        """Получение запросов на анализ от пользователей"""
        requests = []
        
        for chat_id, context in self.user_context.items():
            if context["state"] == "wait_for_analyze_processing" and "analyze_symbol" in context["data"]:
                requests.append({
                    "chat_id": chat_id,
                    "symbol": context["data"]["analyze_symbol"]
                })
                # Сбрасываем состояние после получения запроса
                self.user_context[chat_id] = {"state": "idle", "data": {}}
        
        return requests