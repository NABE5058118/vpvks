"""
Автоматические уведомления пользователей
"""

import logging
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import ContextTypes
from config import BOT_TOKEN, ADMIN_USER_IDS

logger = logging.getLogger(__name__)

# Инициализация бота для уведомлений
notification_bot = Bot(token=BOT_TOKEN)


async def send_expiration_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    Ежедневная проверка и отправка уведомлений об истечении подписки
    Запускается каждый день в 10:00
    """
    logger.info("🔔 Запуск проверки истекающих подписок...")
    
    try:
        # Импортируем модель пользователя
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.models.user import User as UserModel
        
        # Получаем всех пользователей
        users = UserModel.get_all_users()
        
        now = datetime.utcnow()
        sent_count = 0
        
        for user in users:
            if not user.subscription_end_date:
                continue
            
            days_left = (user.subscription_end_date - now).days
            
            # Уведомляем за 3 дня, 1 день и в день истечения
            if days_left == 3:
                await send_expiration_notification(
                    user_id=user.id,
                    days_left=days_left,
                    context=context
                )
                sent_count += 1
                
            elif days_left == 1:
                await send_expiration_notification(
                    user_id=user.id,
                    days_left=days_left,
                    context=context
                )
                sent_count += 1
                
            elif days_left == 0:
                await send_expiration_notification(
                    user_id=user.id,
                    days_left=days_left,
                    context=context
                )
                sent_count += 1
        
        logger.info(f"✅ Отправлено {sent_count} уведомлений об истечении")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомлений: {e}")


async def send_expiration_notification(user_id: int, days_left: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправка уведомления об истечении подписки"""
    try:
        if days_left == 3:
            message = (
                "⏰ **Напоминание от VPVKS**\n\n"
                "Ваша подписка истекает через **3 дня**!\n\n"
                "Чтобы продолжить пользоваться VPN без перерывов:\n"
                "1. Откройте Mini App командой /app\n"
                "2. Перейдите в раздел «Поддержка»\n"
                "3. Выберите тариф и оплатите\n\n"
                "💡 Продление сейчас сохранит вашу скидку!"
            )
        elif days_left == 1:
            message = (
                "⚠️ **Срочно! VPVKS**\n\n"
                "Ваша подписка истекает **завтра**!\n\n"
                "Не оставайтесь без защиты — продлите прямо сейчас:\n"
                "👉 /app\n\n"
                "💰 Тарифы от 110₽/месяц"
            )
        elif days_left == 0:
            message = (
                "🚫 **Подписка истекла! VPVKS**\n\n"
                "Ваша подписка истекла **сегодня**.\n\n"
                "Для возобновления доступа к VPN:\n"
                "1. Откройте Mini App: /app\n"
                "2. Оплатите любой тариф\n"
                "3. Доступ восстановится автоматически\n\n"
                "💡 Мы сохранили ваши данные!"
            )
        else:
            return
        
        await notification_bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"📤 Уведомление отправлено пользователю {user_id} (осталось дней: {days_left})")
        
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление пользователю {user_id}: {e}")


async def send_payment_success_notification(user_id: int, amount: float, days: int):
    """Уведомление об успешной оплате"""
    try:
        message = (
            "✅ **Оплата прошла успешно! VPVKS**\n\n"
            f"💰 Сумма: {amount}₽\n"
            f"📅 Подписка продлена на {days} дн.\n\n"
            "Спасибо за оплату! Ваш VPN доступен.\n\n"
            "🔑 Открыть ключи: /app"
        )
        
        await notification_bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"📤 Уведомление об оплате отправлено пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление об оплате: {e}")


async def send_welcome_notification(user_id: int, username: str):
    """Приветственное уведомление новому пользователю"""
    try:
        message = (
            "👋 **Добро пожаловать в VPVKS!**\n\n"
            f"Привет, {username or 'друг'}!\n\n"
            "🎁 Вам доступен **бесплатный пробный период 7 дней**!\n\n"
            "Что для этого нужно:\n"
            "1. Нажмите /app\n"
            "2. Перейдите в раздел «Ключи»\n"
            "3. Получите ваш персональный ключ\n"
            "4. Подключитесь и пользуйтесь!\n\n"
            "🚀 Протоколы: VLESS Reality + Trojan TLS\n"
            "🌍 Сервер: Стокгольм, Швеция\n"
            "♾️ Лимит: безлимитный трафик\n\n"
            "Если есть вопросы — напишите в поддержку."
        )
        
        await notification_bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode='Markdown'
        )
        
        logger.info(f"📤 Приветственное уведомление отправлено пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Не удалось отправить приветствие: {e}")


async def send_broadcast_message(message_text: str, exclude_admins: bool = True):
    """
    Рассылка сообщения всем пользователям
    :param message_text: Текст сообщения
    :param exclude_admins: Исключить админов из рассылки
    """
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.models.user import User as UserModel
        
        users = UserModel.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            # Исключаем админов если нужно
            if exclude_admins and user.id in ADMIN_USER_IDS:
                continue
            
            try:
                await notification_bot.send_message(
                    chat_id=user.id,
                    text=message_text,
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Не удалось отправить пользователю {user.id}: {e}")
                failed_count += 1
        
        logger.info(f"✅ Рассылка завершена: отправлено {sent_count}, ошибок {failed_count}")
        return {'sent': sent_count, 'failed': failed_count}
        
    except Exception as e:
        logger.error(f"❌ Ошибка рассылки: {e}")
        return {'sent': 0, 'failed': 0}


# Синхронные версии для вызова из синхронного кода
def send_payment_success_notification_sync(user_id: int, amount: float, days: int):
    """Синхронная версия уведомления об оплате"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_payment_success_notification(user_id, amount, days))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка в sync wrapper payment notification: {e}")


def send_welcome_notification_sync(user_id: int, username: str):
    """Синхронная версия приветственного уведомления"""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(send_welcome_notification(user_id, username))
        loop.close()
    except Exception as e:
        logger.error(f"Ошибка в sync wrapper welcome notification: {e}")
