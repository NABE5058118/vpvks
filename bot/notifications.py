"""
Автоматические уведомления пользователей
"""

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Bot
from telegram.ext import ContextTypes
from config import BOT_TOKEN, ADMIN_IDS
import sys
import os

logger = logging.getLogger(__name__)

# Инициализация бота для уведомлений
notification_bot = Bot(token=BOT_TOKEN)


async def send_expiration_reminder(context: ContextTypes.DEFAULT_TYPE):
    """
    Ежедневная проверка и отправка уведомлений об истечении подписки
    Запускается каждый день в 10:00

    Уведомления отправляются за 3, 2, 1 дня и в день истечения
    """
    logger.info("🔔 Запуск проверки истекающих подписок...")

    try:
        # Импортируем модель пользователя через backend
        import sys
        import os
        sys.path.append('/app/backend')
        os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://vpn_bot_user:vp62RofV5h@postgres:5432/vpn_bot_db')
        
        from database.models.user_model import User as UserModel
        from database.db_config import db

        # Получаем всех пользователей
        users = UserModel.get_all_users()

        now = datetime.utcnow()
        today = datetime.utcnow().date()
        sent_count = 0
        skipped_count = 0
        total_count = len(users)

        for user in users:
            # Пропускаем если нет даты окончания подписки
            if not user.subscription_end_date:
                continue

            # Пропускаем если уже отправляли уведомление сегодня
            if user.last_expiration_reminder_sent == today:
                skipped_count += 1
                continue

            # Вычисляем сколько дней осталось (не меньше 0)
            delta = user.subscription_end_date - now
            days_left = max(0, delta.days)

            # Определяем тип уведомления
            notification_type = None
            if days_left == 3:
                notification_type = '3_days'
            elif days_left == 2:
                notification_type = '2_days'
            elif days_left == 1:
                notification_type = '1_day'
            elif days_left == 0:
                notification_type = '0_days'

            # Отправляем уведомление если подходит условие
            if notification_type:
                await send_expiration_notification(
                    user_id=user.id,
                    days_left=days_left,
                    notification_type=notification_type,
                    context=context
                )
                
                # Обновляем дату последнего уведомления
                user.last_expiration_reminder_sent = today
                db.session.commit()
                
                sent_count += 1
                logger.info(f"✅ Уведомление отправлено пользователю {user.id} (осталось дней: {days_left})")

        logger.info(f"✅ Проверка завершена: всего {total_count}, отправлено {sent_count}, пропущено {skipped_count}")

    except Exception as e:
        logger.error(f"❌ Ошибка при отправке уведомлений: {e}", exc_info=True)


async def send_expiration_notification(user_id: int, days_left: int, notification_type: str, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправка уведомления об истечении подписки
    
    :param user_id: ID пользователя в Telegram
    :param days_left: Сколько дней осталось до истечения
    :param notification_type: Тип уведомления ('3_days', '2_days', '1_day', '0_days')
    :param context: Контекст бота
    """
    try:
        if notification_type == '3_days':
            message = (
                "⏰ **Напоминание от VPVKS**\n\n"
                "Ваша подписка истекает через **3 дня**!\n\n"
                "Чтобы продолжить пользоваться VPN без перерывов:\n"
                "1. Откройте Mini App командой /app\n"
                "2. Перейдите в раздел «Поддержка»\n"
                "3. Выберите тариф и оплатите\n\n"
                "💡 Продление сейчас сохранит вашу скидку!"
            )
        elif notification_type == '2_days':
            message = (
                "⏳ **Напоминание VPVKS**\n\n"
                "Ваша подписка истекает через **2 дня**!\n\n"
                "Продлите сейчас чтобы не потерять доступ:\n"
                "👉 /app\n\n"
                "💰 Тарифы от 110₽/месяц"
            )
        elif notification_type == '1_day':
            message = (
                "⚠️ **Срочно! VPVKS**\n\n"
                "Ваша подписка истекает **завтра**!\n\n"
                "Не оставайтесь без защиты — продлите прямо сейчас:\n"
                "👉 /app\n\n"
                "💰 Тарифы от 110₽/месяц"
            )
        elif notification_type == '0_days':
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

        logger.info(f"📤 Уведомление отправлено пользователю {user_id} (осталось дней: {days_left}, тип: {notification_type})")

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
        from database.models.user_model import User as UserModel
        
        users = UserModel.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        for user in users:
            # Исключаем админов если нужно
            if exclude_admins and user.id in ADMIN_IDS:
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
    try:
        try:
            loop = asyncio.get_running_loop()
            # Loop запущен (бот) — создаём отдельный
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(send_payment_success_notification(user_id, amount, days))
            new_loop.close()
        except RuntimeError:
            # Loop не запущен — можно использовать asyncio.run
            asyncio.run(send_payment_success_notification(user_id, amount, days))
    except Exception as e:
        logger.error(f"Ошибка в sync wrapper payment notification: {e}")


def send_welcome_notification_sync(user_id: int, username: str):
    """Синхронная версия приветственного уведомления"""
    try:
        try:
            loop = asyncio.get_running_loop()
            # Loop запущен (бот) — создаём отдельный
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(send_welcome_notification(user_id, username))
            new_loop.close()
        except RuntimeError:
            # Loop не запущен — можно использовать asyncio.run
            asyncio.run(send_welcome_notification(user_id, username))
    except Exception as e:
        logger.error(f"Ошибка в sync wrapper welcome notification: {e}")
