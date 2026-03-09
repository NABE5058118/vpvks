"""
Утилиты для проверки подписки на каналы
"""

import logging
from telegram import Bot
from telegram.error import BadRequest
from config import BOT_TOKEN, CHANNEL_NEWS_ID, ADMIN_IDS

logger = logging.getLogger(__name__)


async def check_subscription(user_id: int) -> bool:
    """
    Проверка подписки пользователя на обязательный канал новостей

    :param user_id: ID пользователя в Telegram
    :return: True если подписан, False если не подписан
    """
    try:
        bot = Bot(token=BOT_TOKEN)

        # Получаем статус участника в канале
        member = await bot.get_chat_member(chat_id=CHANNEL_NEWS_ID, user_id=user_id)

        # Проверяем статус
        # member.status может быть: creator, administrator, member, left, kicked
        is_subscribed = member.status in ['creator', 'administrator', 'member']

        logger.info(f"🔍 Проверка подписки user_{user_id}: статус={member.status}, {'✅ подписан' if is_subscribed else '❌ не подписан'}")

        return is_subscribed

    except BadRequest as e:
        # Ошибка Telegram API (бот не админ в канале, неверный ID и т.д.)
        error_msg = str(e)
        logger.error(f"❌ Ошибка проверки подписки user_{user_id}: {error_msg}")
        
        if "bot is not an administrator" in error_msg.lower():
            logger.critical("💣 Бот НЕ является администратором канала!")
            logger.critical("💡 ДОБАВЬТЕ БОТА В АДМИНИСТРАТОРЫ КАНАЛА @vpvks_news")
            logger.critical("   1. Откройте канал @vpvks_news")
            logger.critical("   2. Управление → Администраторы → Добавить")
            logger.critical("   3. Найдите бота, дайте право 'Просмотр сообщений'")
        elif "chat not found" in error_msg.lower() or "private channel" in error_msg.lower():
            logger.error(f"💣 Неверный CHANNEL_NEWS_ID: {CHANNEL_NEWS_ID}")
            logger.critical("💡 Проверьте ID канала в .env (должен быть без @)")
        
        # Возвращаем False — пользователь НЕ подписан
        return False

    except Exception as e:
        # Другие ошибки
        logger.error(f"❌ Неизвестная ошибка проверки подписки user_{user_id}: {e}")
        # Возвращаем False для безопасности
        return False


def is_user_admin(user_id: int) -> bool:
    """
    Проверка является ли пользователь администратором

    :param user_id: ID пользователя
    :return: True если админ
    """
    return user_id in ADMIN_IDS
