"""
Скрипт для проверки настройки подписки на канал
Запустить: python bot/utils/test_subscription.py
"""

import asyncio
import sys
import os

# Add bot to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BOT_TOKEN, CHANNEL_NEWS_ID
from telegram import Bot
from telegram.error import BadRequest


async def test_subscription():
    """Тест проверки подписки"""
    print("=" * 60)
    print("🔍 ТЕСТ ПРОВЕРКИ ПОДПИСКИ НА КАНАЛ")
    print("=" * 60)

    # 1. Проверка токена
    print("\n1️⃣ Проверка токена бота...")
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    print(f"✅ Токен найден: {BOT_TOKEN[:20]}...")

    # 2. Проверка ID канала
    print(f"\n2️⃣ Проверка ID канала...")
    print(f"   CHANNEL_NEWS_ID: {CHANNEL_NEWS_ID}")
    if not CHANNEL_NEWS_ID:
        print("❌ CHANNEL_NEWS_ID не установлен!")
        return
    print(f"✅ ID канала найден")

    # 3. Проверка доступа бота к каналу
    print(f"\n3️⃣ Проверка доступа бота к каналу @{CHANNEL_NEWS_ID}...")
    try:
        bot = Bot(token=BOT_TOKEN)
        chat = await bot.get_chat(chat_id=CHANNEL_NEWS_ID)
        print(f"✅ Бот имеет доступ к каналу!")
        print(f"   Название: {chat.title}")
        print(f"   Тип: {chat.type}")
        print(f"   Username: @{chat.username}")

        # Проверка, является ли бот администратором
        print(f"\n4️⃣ Проверка прав бота в канале...")
        bot_member = await bot.get_chat_member(chat_id=CHANNEL_NEWS_ID, user_id=bot.id)
        print(f"   Статус бота: {bot_member.status}")

        if bot_member.status == 'administrator':
            print(f"✅ Бот является АДМИНИСТРАТОРОМ канала")
        else:
            print(f"❌ Бот НЕ является администратором!")
            print(f"💡 ДОБАВЬТЕ БОТА В АДМИНИСТРАТОРЫ КАНАЛА!")
            print(f"   1. Откройте канал @{CHANNEL_NEWS_ID}")
            print(f"   2. Управление каналом → Администраторы")
            print(f"   3. Добавить администратора → найдите @{(await bot.get_me()).username}")
            print(f"   4. Дайте право 'Просмотр сообщений'")
            print(f"   5. Сохраните")

        # 5. Тест проверки пользователя
        print(f"\n5️⃣ Тест проверки подписки...")
        print(f"   Введите ваш Telegram ID (или нажмите Enter для пропуска):")

        try:
            user_id_input = input("   Ваш ID: ")
            if user_id_input.strip():
                user_id = int(user_id_input)
                member = await bot.get_chat_member(chat_id=CHANNEL_NEWS_ID, user_id=user_id)
                is_subscribed = member.status in ['creator', 'administrator', 'member']

                print(f"\n   Результат для user_{user_id}:")
                print(f"   Статус: {member.status}")
                print(f"   {'✅ ПОДПИСАН' if is_subscribed else '❌ НЕ ПОДПИСАН'}")
        except ValueError:
            print("   ❌ Неверный формат ID")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

    except BadRequest as e:
        print(f"❌ Ошибка доступа к каналу: {e}")
        print(f"💡 Возможные причины:")
        print(f"   • Бот не является администратором канала")
        print(f"   • Неверный CHANNEL_NEWS_ID")
        print(f"   • Канал приватный и бот не добавлен")
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")

    print("\n" + "=" * 60)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_subscription())
