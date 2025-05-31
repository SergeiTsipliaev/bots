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

from config import CONFIG, COIN_DESCRIPTIONS, SIGNAL_TYPE_DESCRIPTIONS
from cati_bot.utils import logger


class NotificationSender:
    """Класс для отправки уведомлений и обработки Telegram-команд"""

    def __init__(self):
        self.coin_descriptions = COIN_DESCRIPTIONS
        self.signal_type_descriptions = SIGNAL_TYPE_DESCRIPTIONS

        # Проверяем, что настроены Telegram-параметры
        self.telegram_enabled = bool(CONFIG["telegram_bot_token"] and CONFIG["telegram_chat_id"])

        if self.telegram_enabled:
            logger.info(
                f"Telegram включен. Токен: {CONFIG['telegram_bot_token'][:5]}... Чат ID: {CONFIG['telegram_chat_id']}")
        else:
            logger.warning("Telegram отключен. Проверьте настройки telegram_bot_token и telegram_chat_id в config.py")

        # Отслеживание последнего update_id
        self.last_update_id = 0

        # Словарь для отслеживания подписок пользователей на монеты
        # Инициализируем с правильной структурой
        self.user_subscriptions = {
            str(CONFIG["telegram_chat_id"]): {
                "coins": ["ALL"],
                "signal_type": CONFIG["default_signal_type"]
            }
        }

        # Временные данные для поддержки диалога с пользователем
        self.user_context = {}  # {chat_id: {'state': 'wait_for_coin', 'data': {}}}

        # Проверяем соединение с Telegram API
        self._check_telegram_connection()

    def _check_telegram_connection(self) -> bool:
        """Проверка соединения с Telegram API"""
        if not self.telegram_enabled:
            logger.warning("Telegram отключен. Проверка соединения пропущена.")
            return False

        try:
            # Проверяем токен бота
            url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/getMe"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("ok"):
                bot_username = data.get("result", {}).get("username", "Unknown")
                bot_name = data.get("result", {}).get("first_name", "Unknown")
                logger.info(f"Соединение с Telegram API успешно установлено. Бот: {bot_name} (@{bot_username})")

                # Отправляем тестовое сообщение
                test_message = f"🤖 Бот для анализа криптовалют запущен и готов к работе!"
                try:
                    send_url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
                    payload = {
                        "chat_id": CONFIG["telegram_chat_id"],
                        "text": test_message
                    }

                    send_response = requests.post(send_url, json=payload, timeout=10)
                    send_data = send_response.json()

                    if send_data.get("ok"):
                        logger.info(f"Тестовое сообщение успешно отправлено в чат {CONFIG['telegram_chat_id']}")
                    else:
                        error_msg = send_data.get("description", "Неизвестная ошибка")
                        logger.error(f"Не удалось отправить тестовое сообщение: {error_msg}")

                        if "chat not found" in error_msg.lower():
                            logger.error(f"Проверьте правильность указанного ID чата: {CONFIG['telegram_chat_id']}")
                        elif "blocked" in error_msg.lower():
                            logger.error("Бот заблокирован пользователем. Разблокируйте бота в Telegram.")

                        return False
                except Exception as e:
                    logger.error(f"Ошибка при отправке тестового сообщения: {e}")
                    return False

                return True
            else:
                error_msg = data.get("description", "Неизвестная ошибка")
                logger.error(f"Ошибка соединения с Telegram API: {error_msg}")

                if "unauthorized" in error_msg.lower():
                    logger.error("Указан неверный токен Telegram бота. Проверьте токен в файле config.py.")

                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке соединения с Telegram API: {e}")
            return False

    async def send_signal_notification(self, signal: Dict[str, Any]) -> bool:
        """Метод для отправки уведомления о торговом сигнале"""
        try:
            # Добавляем отладочный вывод структуры сигнала
            logger.info(f"Получен сигнал для отправки: {type(signal)}")
            if signal is not None:
                logger.info(f"Ключи сигнала: {list(signal.keys())}")

                # Проверяем тип сигнала и игнорируем HOLD
                if signal.get('signal_type') == "HOLD":
                    logger.info(f"Игнорируем сигнал типа HOLD для {signal.get('symbol')}")
                    return False

                # Проверяем уверенность в сигнале
                confidence = signal.get('confidence', 0)
                if confidence < 0.6:  # Порог 60%
                    logger.info(
                        f"Игнорируем сигнал с низкой уверенностью ({confidence * 100:.2f}%) для {signal.get('symbol')}")
                    return False

                # Получаем тип срока сигнала, по умолчанию ALL
                signal_term_type = signal.get('term_type', 'ALL')
                logger.info(f"Тип сигнала для отправки: {signal_term_type}")
            else:
                logger.error("Сигнал равен None")
                return False

            # Формируем сообщение
            message = self._format_signal_message(signal)

            # Отправляем в Telegram, если включено
            if self.telegram_enabled:
                logger.info(f"Телеграм включен, отправляем сигнал для {signal['symbol']}")

                # Получаем все чаты, подписанные на данную монету и тип сигнала
                symbol = signal['symbol']
                signal_term_type = signal.get('term_type', 'ALL')
                subscribers_found = False
                sent_to_main_chat = False

                # Отладочная информация о подписках
                logger.info(f"Текущие подписки пользователей: {self.user_subscriptions}")

                for chat_id, subscription in self.user_subscriptions.items():
                    coins = subscription.get("coins", [])
                    user_signal_type = subscription.get("signal_type", "ALL")

                    # Проверяем соответствие монеты
                    coin_match = symbol in coins or 'ALL' in coins

                    # Проверяем соответствие типа сигнала
                    signal_type_match = (
                            user_signal_type == signal_term_type or
                            user_signal_type == "ALL" or
                            signal_term_type == "ALL"
                    )

                    logger.info(
                        f"Проверка подписки для {chat_id}: монета {symbol} ({coin_match}), тип {signal_term_type} ({signal_type_match})")

                    if coin_match and signal_type_match:
                        logger.info(f"Найден подписчик {chat_id} для {symbol} с типом сигнала {signal_term_type}")
                        subscribers_found = True
                        success = await self._send_telegram_message(message, chat_id)
                        # Отмечаем, если сообщение было отправлено в основной чат
                        if str(chat_id) == str(CONFIG["telegram_chat_id"]):
                            sent_to_main_chat = True
                        if not success:
                            logger.error(f"Не удалось отправить сообщение подписчику {chat_id}")

                # Если нет подписок или никто не подписан на эту монету и тип сигнала, отправляем в стандартный чат
                if not subscribers_found:
                    logger.info(
                        f"Подписчики для {symbol} с типом {signal_term_type} не найдены, отправляем в стандартный чат {CONFIG['telegram_chat_id']}")
                    await self._send_telegram_message(message, str(CONFIG["telegram_chat_id"]))
                    sent_to_main_chat = True

                # Отправляем копию в стандартный чат для отладки только если он ещё не получил это сообщение
                if CONFIG["telegram_chat_id"] and CONFIG.get("always_send_to_main_chat",
                                                             True) and not sent_to_main_chat:
                    logger.info(f"Отправляем копию сигнала в основной чат {CONFIG['telegram_chat_id']}")
                    await self._send_telegram_message(message, str(CONFIG["telegram_chat_id"]))
            else:
                logger.warning("Телеграм отключен, уведомления не отправляются")

            return True
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return False

    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Метод для форматирования сообщения"""
        try:
            emoji_map = {
                'BUY': '🟢 ПОКУПКА',
                'SELL': '🔴 ПРОДАЖА',
                'HOLD': '⚪ ОЖИДАНИЕ'
            }

            term_type_emoji = {
                'SHORT': '⚡',  # Краткосрочный
                'LONG': '🔮',  # Долгосрочный
                'ALL': '📊'  # Все типы
            }

            # Добавляем эмодзи типа сигнала
            term_type = signal.get('term_type', 'ALL')
            term_emoji = term_type_emoji.get(term_type, '')

            message = f"{emoji_map.get(signal['signal_type'], signal['signal_type'])} | {signal['symbol']} {term_emoji}\n\n"

            # Добавляем информацию о типе сигнала
            if term_type != "ALL":
                message += f"Тип сигнала: {self.signal_type_descriptions.get(term_type, term_type)}\n\n"

            # Добавляем информацию о рынке
            market_info = signal.get('market_info', [])
            if market_info:
                message += "\n".join(market_info) + "\n\n"

            # Добавляем тренды
            trend = signal.get('trend', {})
            if trend:
                message += "Тренды:\n"
                for timeframe, trend_val in trend.items():
                    if timeframe == 'общий':
                        continue
                    message += f"- {timeframe}: {trend_val}\n"
                message += "\n"

            # Добавляем информацию о рыночной фазе
            market_cycles = signal.get('market_cycles', {})
            if market_cycles and market_cycles.get('phase'):
                market_phase = market_cycles.get('phase')
                confidence = market_cycles.get('confidence', 0) * 100
                message += f"Рыночная фаза: {market_phase} (уверенность: {confidence:.0f}%)\n\n"

                # Добавляем замеченные паттерны, если они есть
                patterns = market_cycles.get('patterns', [])
                if patterns:
                    message += "Замеченные паттерны:\n"
                    for pattern in patterns:
                        message += f"- {pattern['pattern']} ({pattern['confidence'] * 100:.0f}%)\n"
                    message += "\n"

            # Добавляем силу сигнала и уверенность
            if signal['signal_type'] != 'HOLD':
                strength = signal.get('strength', 0)
                message += f"Сила сигнала: {strength * 100:.0f}%\n"
                # Добавляем уверенность в сигнале
                confidence = signal.get('confidence', 0)
                if confidence > 0:
                    message += f"Уверенность: {confidence * 100:.0f}%\n\n"
                else:
                    message += "\n"

            # Добавляем рекомендуемые действия
            suggested_actions = signal.get('suggested_actions', [])
            if suggested_actions:
                message += "Рекомендуемые действия:\n"
                message += "\n".join(suggested_actions) + "\n\n"

            # Добавляем причины сигнала
            messages = signal.get('messages', [])
            if messages:
                message += "Причины сигнала:\n"
                message += "\n".join(messages) + "\n"

            return message
        except Exception as e:
            logger.error(f"Ошибка форматирования сообщения: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
            return f"Ошибка форматирования сообщения для {signal.get('symbol', 'Unknown')}"

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
                "text": message
            }

            # Обработка длинных сообщений
            if len(message) > 4000:
                # Разделение длинного сообщения на части
                chunks = [message[i:i + 4000] for i in range(0, len(message), 4000)]
                logger.info(f"Сообщение слишком длинное ({len(message)} символов), разделено на {len(chunks)} частей")

                success = True
                for i, chunk in enumerate(chunks):
                    chunk_payload = {
                        "chat_id": chat_id,
                        "text": f"(Часть {i + 1}/{len(chunks)}) {chunk}"
                    }

                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            response = requests.post(url, json=chunk_payload, timeout=30)
                            response.raise_for_status()

                            data = response.json()
                            if not data.get("ok"):
                                error_msg = data.get("description", "Неизвестная ошибка")
                                logger.error(f"Ошибка API Telegram: {error_msg}")
                                return False

                            break  # Выходим из цикла попыток, если запрос успешен
                        except Exception as e:
                            logger.error(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                            else:
                                success = False
                                logger.error(
                                    f"Не удалось отправить часть {i + 1} сообщения после {max_retries} попыток")

                return success
            else:
                # Обычная отправка для коротких сообщений
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(url, json=payload, timeout=30)

                        data = response.json()
                        if not data.get("ok"):
                            error_msg = data.get("description", "Неизвестная ошибка")
                            logger.error(f"Ошибка API Telegram: {error_msg}")

                            if "chat not found" in error_msg.lower():
                                logger.error(f"Проверьте правильность указанного ID чата: {chat_id}")
                            elif "blocked" in error_msg.lower():
                                logger.error(f"Бот заблокирован пользователем в чате {chat_id}")

                            return False

                        response.raise_for_status()
                        break  # Выходим из цикла попыток, если запрос успешен
                    except Exception as e:
                        logger.error(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                        else:
                            import traceback
                            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
                            return False

            logger.info(f"Сообщение успешно отправлено в Telegram (chat_id: {chat_id})")
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")
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

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    updates = response.json()

                    if updates.get("ok") and updates.get("result"):
                        for update in updates["result"]:
                            # Обновляем последний update_id
                            self.last_update_id = max(self.last_update_id, update["update_id"])

                            # Обрабатываем сообщение
                            if "message" in update and "text" in update["message"]:
                                await self._process_message(update["message"])
                    break  # Выходим из цикла попыток, если запрос успешен
                except Exception as e:
                    logger.error(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                    else:
                        raise
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
                self.user_subscriptions[chat_id] = {
                    "coins": [],
                    "signal_type": CONFIG["default_signal_type"]
                }

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
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")

    async def _process_command(self, chat_id: str, text: str) -> None:
        """Обработка команды от пользователя"""
        try:
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

            elif command == "/signaltype":
                # Переходим в режим выбора типа сигнала
                self.user_context[chat_id] = {"state": "wait_for_signal_type", "data": {}}
                await self._send_available_signal_types(chat_id)

            elif command == "/mysignaltype":
                # Показываем текущий тип сигнала для пользователя
                await self._send_user_signal_type(chat_id)

            elif command == "/test":
                # Отправляем тестовое сообщение для проверки соединения
                await self._send_telegram_message("🧪 Тестовое сообщение. Соединение с ботом работает корректно.",
                                                  chat_id)

            else:
                # Неизвестная команда
                await self._send_telegram_message("Неизвестная команда. Используйте /help для получения списка команд.",
                                                  chat_id)
        except Exception as e:
            logger.error(f"Ошибка обработки команды: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")

    async def _process_context_dialog(self, chat_id: str, text: str) -> None:
        """Обработка диалога с пользователем в зависимости от контекста"""
        try:
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

            elif state == "wait_for_signal_type":
                # Выбор типа сигнала
                await self._handle_signal_type_selection(chat_id, text)

            # Сбрасываем состояние диалога
            self.user_context[chat_id] = {"state": "idle", "data": {}}
        except Exception as e:
            logger.error(f"Ошибка обработки диалога: {e}")
            import traceback
            logger.error(f"Трассировка ошибки: {traceback.format_exc()}")

    async def _handle_subscribe(self, chat_id: str, text: str) -> None:
        """Обработка подписки на монету"""
        try:
            if text == "ВСЕ":
                # Подписка на все монеты
                if chat_id in self.user_subscriptions:
                    self.user_subscriptions[chat_id]["coins"] = ["ALL"]
                else:
                    self.user_subscriptions[chat_id] = {
                        "coins": ["ALL"],
                        "signal_type": CONFIG["default_signal_type"]
                    }
                await self._send_telegram_message("✅ Вы успешно подписались на уведомления по ВСЕМ монетам!", chat_id)
                return

            # Проверяем, что монета есть в списке доступных
            coin = text.upper()
            if coin not in CONFIG["available_symbols"]:
                await self._send_telegram_message(f"❌ Монета {coin} не найдена в списке доступных.", chat_id)
                return

            # Добавляем монету в подписки пользователя
            if chat_id in self.user_subscriptions:
                if "ALL" in self.user_subscriptions[chat_id]["coins"]:
                    # Если была подписка на все, удаляем ее и добавляем конкретную монету
                    self.user_subscriptions[chat_id]["coins"] = [coin]
                elif coin not in self.user_subscriptions[chat_id]["coins"]:
                    self.user_subscriptions[chat_id]["coins"].append(coin)
            else:
                self.user_subscriptions[chat_id] = {
                    "coins": [coin],
                    "signal_type": CONFIG["default_signal_type"]
                }

            # Отправляем подтверждение
            await self._send_telegram_message(f"✅ Вы успешно подписались на уведомления по {coin}!", chat_id)
        except Exception as e:
            logger.error(f"Ошибка подписки: {e}")

    async def _handle_unsubscribe(self, chat_id: str, text: str) -> None:
        """Обработка отписки от монеты"""
        try:
            if text == "ВСЕ":
                # Отписываемся от всех монет
                if chat_id in self.user_subscriptions:
                    self.user_subscriptions[chat_id]["coins"] = []
                else:
                    self.user_subscriptions[chat_id] = {
                        "coins": [],
                        "signal_type": CONFIG["default_signal_type"]
                    }
                await self._send_telegram_message("✅ Вы отписались от всех уведомлений!", chat_id)
                return

            # Проверяем, что пользователь подписан на эту монету
            coin = text.upper()
            if chat_id in self.user_subscriptions:
                if coin in self.user_subscriptions[chat_id]["coins"]:
                    self.user_subscriptions[chat_id]["coins"].remove(coin)
                    await self._send_telegram_message(f"✅ Вы успешно отписались от уведомлений по {coin}!", chat_id)
                elif "ALL" in self.user_subscriptions[chat_id]["coins"]:
                    # Если была подписка на все, удаляем ее и добавляем все монеты кроме указанной
                    self.user_subscriptions[chat_id]["coins"] = [c for c in CONFIG["available_symbols"] if c != coin]
                    await self._send_telegram_message(f"✅ Вы успешно отписались от уведомлений по {coin}!", chat_id)
                else:
                    await self._send_telegram_message(f"❓ Вы не были подписаны на {coin}.", chat_id)
            else:
                await self._send_telegram_message(f"❓ У вас нет активных подписок.", chat_id)
        except Exception as e:
            logger.error(f"Ошибка отписки: {e}")

    async def _handle_analyze_request(self, chat_id: str, text: str) -> None:
        """Обработка запроса на анализ монеты"""
        try:
            coin = text.upper()
            if coin not in CONFIG["available_symbols"]:
                await self._send_telegram_message(f"❌ Монета {coin} не найдена в списке доступных.", chat_id)
                return

            # Отправляем сообщение, что запрос на анализ получен
            await self._send_telegram_message(
                f"⏳ Запрос на анализ {coin} принят. Результаты будут отправлены в ближайшее время.", chat_id)

            # Устанавливаем выбранную монету в user_context для дальнейшего использования
            self.user_context[chat_id]["data"]["analyze_symbol"] = coin
            # Переводим состояние для обработки запроса анализа
            self.user_context[chat_id]["state"] = "wait_for_analyze_processing"
        except Exception as e:
            logger.error(f"Ошибка запроса анализа: {e}")

    async def _handle_signal_type_selection(self, chat_id: str, text: str) -> None:
        """Обработка выбора типа сигнала"""
        try:
            signal_type = text.upper()
            if signal_type not in CONFIG["signal_types"]:
                await self._send_telegram_message(f"❌ Тип сигнала {signal_type} не найден в списке доступных.", chat_id)
                return

            # Обновляем тип сигнала для пользователя
            if chat_id in self.user_subscriptions:
                self.user_subscriptions[chat_id]["signal_type"] = signal_type
            else:
                self.user_subscriptions[chat_id] = {
                    "coins": [],
                    "signal_type": signal_type
                }

            # Отправляем подтверждение
            signal_description = self.signal_type_descriptions.get(signal_type, signal_type)
            await self._send_telegram_message(f"✅ Вы успешно изменили тип сигналов на: {signal_description}", chat_id)
        except Exception as e:
            logger.error(f"Ошибка выбора типа сигнала: {e}")

    async def _send_help_message(self, chat_id: str) -> None:
        """Отправка справочного сообщения"""
        try:
            message = (
                "🤖 *Бот для анализа криптовалют* 🤖\n\n"
                "Команды:\n"
                "/subscribe - Подписаться на уведомления по монете\n"
                "/unsubscribe - Отписаться от уведомлений по монете\n"
                "/analyze - Запросить анализ монеты\n"
                "/list - Показать список доступных монет\n"
                "/mycoins - Показать мои подписки\n"
                "/signaltype - Выбрать тип сигналов (краткосрочные/долгосрочные/все)\n"
                "/mysignaltype - Показать текущий тип сигналов\n"
                "/test - Проверить соединение с ботом\n"
                "/help - Показать эту справку\n\n"
                "Бот анализирует рынок и отправляет торговые сигналы с прогнозами."
            )
            await self._send_telegram_message(message, chat_id)
        except Exception as e:
            logger.error(f"Ошибка отправки справки: {e}")

    async def _send_available_coins(self, chat_id: str) -> None:
        """Отправка списка доступных монет"""
        try:
            message = "📋 Доступные монеты:\n\n"

            for symbol in CONFIG["available_symbols"]:
                description = self.coin_descriptions.get(symbol, "")
                message += f"• {symbol} - {description}\n"

            message += "\nТакже доступен выбор 'ВСЕ' для подписки на все монеты."

            await self._send_telegram_message(message, chat_id)
        except Exception as e:
            logger.error(f"Ошибка отправки списка монет: {e}")

    async def _send_available_signal_types(self, chat_id: str) -> None:
        """Отправка списка доступных типов сигналов"""
        try:
            message = "📊 Доступные типы сигналов:\n\n"

            for signal_type in CONFIG["signal_types"]:
                description = self.signal_type_descriptions.get(signal_type, signal_type)
                message += f"• {signal_type} - {description}\n"

            message += "\nВыберите один из доступных типов сигналов."

            await self._send_telegram_message(message, chat_id)
        except Exception as e:
            logger.error(f"Ошибка отправки типов сигналов: {e}")

    async def _send_user_subscriptions(self, chat_id: str) -> None:
        """Отправка списка подписок пользователя"""
        try:
            if chat_id not in self.user_subscriptions or not self.user_subscriptions[chat_id]["coins"]:
                await self._send_telegram_message("У вас нет активных подписок на монеты.", chat_id)
                return

            if "ALL" in self.user_subscriptions[chat_id]["coins"]:
                await self._send_telegram_message("Вы подписаны на ВСЕ монеты! 🌟", chat_id)
                return

            message = "📊 Ваши подписки:\n\n"
            for symbol in self.user_subscriptions[chat_id]["coins"]:
                # Получаем описание монеты, если оно есть в словаре
                description = self.coin_descriptions.get(symbol, "")
                message += f"• {symbol} - {description}\n"

            await self._send_telegram_message(message, chat_id)
        except Exception as e:
            logger.error(f"Ошибка отправки подписок: {e}")

    async def _send_user_signal_type(self, chat_id: str) -> None:
        """Отправка информации о текущем типе сигналов пользователя"""
        try:
            if chat_id not in self.user_subscriptions:
                # Используем тип сигнала по умолчанию
                signal_type = CONFIG["default_signal_type"]
                self.user_subscriptions[chat_id] = {
                    "coins": [],
                    "signal_type": signal_type
                }
            else:
                signal_type = self.user_subscriptions[chat_id].get("signal_type", CONFIG["default_signal_type"])

            # Получаем описание типа сигнала
            signal_description = self.signal_type_descriptions.get(signal_type, signal_type)

            message = f"🔔 Ваш текущий тип сигналов: {signal_type} - {signal_description}\n\n"
            message += "Для изменения типа сигналов используйте команду /signaltype"

            await self._send_telegram_message(message, chat_id)
        except Exception as e:
            logger.error(f"Ошибка отправки типа сигнала: {e}")

    def get_analyze_requests(self) -> List[Dict[str, Any]]:
        """Получение запросов на анализ от пользователей"""
        try:
            requests = []

            for chat_id, context in self.user_context.items():
                if context["state"] == "wait_for_analyze_processing" and "analyze_symbol" in context["data"]:
                    # Определяем тип сигнала пользователя
                    signal_type = "ALL"
                    if chat_id in self.user_subscriptions:
                        signal_type = self.user_subscriptions[chat_id].get("signal_type", "ALL")

                    requests.append({
                        "chat_id": chat_id,
                        "symbol": context["data"]["analyze_symbol"],
                        "signal_type": signal_type
                    })
                    # Сбрасываем состояние после получения запроса
                    self.user_context[chat_id] = {"state": "idle", "data": {}}

            return requests
        except Exception as e:
            logger.error(f"Ошибка получения запросов на анализ: {e}")
            return []
