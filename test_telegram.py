#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для тестирования соединения с Telegram API.
Используйте этот скрипт, если у вас возникли проблемы с отправкой уведомлений.
"""

import requests
import sys
import json
import argparse
import time


def test_bot_token(token):
    """Проверяет валидность токена Telegram бота"""
    print(f"Проверка токена бота...")
    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("ok"):
            bot_name = data["result"]["first_name"]
            bot_username = data["result"]["username"]
            print(f"✅ Токен действителен. Бот: {bot_name} (@{bot_username})")
            return True
        else:
            error = data.get("description", "Неизвестная ошибка")
            print(f"❌ Неверный токен: {error}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {e}")
        return False


def test_send_message(token, chat_id):
    """Пытается отправить тестовое сообщение"""
    print(f"Попытка отправки тестового сообщения в чат {chat_id}...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    message = f"🤖 Тестовое сообщение от бота для анализа криптовалют.\nВремя: {time.strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": message},
            timeout=10
        )
        data = response.json()

        if data.get("ok"):
            print(f"✅ Сообщение успешно отправлено!")
            return True
        else:
            error = data.get("description", "Неизвестная ошибка")
            print(f"❌ Ошибка отправки сообщения: {error}")
            print("Подробная информация об ошибке:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return False
    except Exception as e:
        print(f"❌ Исключение при отправке сообщения: {e}")
        return False


def get_updates(token):
    """Получает последние обновления для бота"""
    print("Получение последних обновлений для бота...")
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("ok"):
            updates = data.get("result", [])
            if not updates:
                print("Обновлений не найдено. Возможно, бот не получал сообщений или обновления устарели.")
                print("Отправьте боту сообщение и запустите скрипт снова с флагом --updates.")
                return None

            print(f"Найдено {len(updates)} обновлений.")

            for update in updates:
                if "message" in update:
                    message = update["message"]
                    chat_id = message["chat"]["id"]
                    chat_type = message["chat"]["type"]
                    if "username" in message["chat"]:
                        chat_name = f"@{message['chat']['username']}"
                    elif "title" in message["chat"]:
                        chat_name = message["chat"]["title"]
                    else:
                        chat_name = f"{message['chat'].get('first_name', '')} {message['chat'].get('last_name', '')}".strip()

                    print(f"Chat ID: {chat_id} ({chat_type}: {chat_name})")

            return updates
        else:
            error = data.get("description", "Неизвестная ошибка")
            print(f"❌ Ошибка получения обновлений: {error}")
            return None
    except Exception as e:
        print(f"❌ Исключение при получении обновлений: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Тест соединения с Telegram API")
    parser.add_argument("--token", help="Токен Telegram бота")
    parser.add_argument("--chat_id", help="ID чата для отправки тестового сообщения")
    parser.add_argument("--updates", action="store_true", help="Получить последние обновления для бота")
    parser.add_argument("--from_config", action="store_true", help="Использовать токен и chat_id из config.py")
    args = parser.parse_args()

    token = None
    chat_id = None

    # Загружаем токен и chat_id из config.py, если запрошено
    if args.from_config:
        try:
            sys.path.append('.')
            from config import CONFIG
            token = CONFIG.get("telegram_bot_token")
            chat_id = CONFIG.get("telegram_chat_id")
            print(f"Загружены настройки из config.py")
        except Exception as e:
            print(f"Ошибка загрузки настроек из config.py: {e}")

    # Приоритет имеют аргументы командной строки
    if args.token:
        token = args.token

    if args.chat_id:
        chat_id = args.chat_id

    # Проверяем, что токен указан
    if not token:
        print("Ошибка: не указан токен бота. Используйте --token или --from_config.")
        return 1

    # Проверяем токен
    if not test_bot_token(token):
        return 1

    # Получаем обновления, если запрошено
    if args.updates:
        updates = get_updates(token)
        if not updates:
            return 1

    # Отправляем тестовое сообщение, если указан chat_id
    if chat_id:
        if not test_send_message(token, chat_id):
            return 1
    else:
        print("Для отправки тестового сообщения укажите chat_id с помощью --chat_id или --from_config.")

    print("\n✅ Все тесты пройдены успешно!")
    return 0


if __name__ == "__main__":
    sys.exit(main())