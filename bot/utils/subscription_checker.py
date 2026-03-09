"""
Утилиты для проверки подписки на каналы
"""

import logging
from telegram import Bot
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
        
        logger.info(f"Проверка подписки user_{user_id}: {'✅ подписан' if is_subscribed else '❌ не подписан'} (статус: {member.status})")
        
        return is_subscribed
        
    except Exception as e:
        logger.error(f"Ошибка проверки подписки user_{user_id}: {e}")
        # Если ошибка (например, бот не админ в канале), считаем что пользователь подписан
        # Чтобы не блокировать доступ
        return True


def is_user_admin(user_id: int) -> bool:
    """
    Проверка является ли пользователь администратором
    
    :param user_id: ID пользователя
    :return: True если админ
    """
    return user_id in ADMIN_IDS
