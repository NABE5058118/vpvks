#!/usr/bin/env python3
"""
Проверка истечения подписок и отправка уведомлений
Запускается ежедневно в 10:00

Уведомления отправляются за 5, 3, 2, 1 дня до истечения и в день истечения
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем путь к моделям
sys.path.insert(0, '/app')

# Инициализация Flask app для доступа к БД
from server import app
from database.db_config import db
from database.models.user_model import User as UserModel

# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8321727057:AAGJJwoVRoG7wYZQPfN9-q-IM4mHA82g2cU')

def send_telegram_message(chat_id: int, text: str):
    """Отправка сообщения через Telegram Bot API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram: {e}")
        return False

def check_expirations():
    """Проверка истечения подписок и отправка уведомлений"""
    logger.info("🔔 Запуск проверки истекающих подписок...")
    
    with app.app_context():
        try:
            # Получаем всех пользователей
            users = UserModel.query.all()
            
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
                # Уведомляем за 5, 3, 2, 1 дня и в день истечения
                notification_type = None
                if days_left == 5:
                    notification_type = '5_days'
                elif days_left == 3:
                    notification_type = '3_days'
                elif days_left == 2:
                    notification_type = '2_days'
                elif days_left == 1:
                    notification_type = '1_day'
                elif days_left == 0:
                    notification_type = '0_days'
                
                # Отправляем уведомление если подходит условие
                if notification_type:
                    message = get_notification_message(notification_type)
                    success = send_telegram_message(user.id, message)
                    
                    if success:
                        # Обновляем дату последнего уведомления
                        user.last_expiration_reminder_sent = today
                        db.session.commit()
                        sent_count += 1
                        logger.info(f"✅ Уведомление отправлено пользователю {user.id} (осталось дней: {days_left})")
                    else:
                        logger.warning(f"⚠️ Не удалось отправить уведомление пользователю {user.id}")
            
            logger.info(f"✅ Проверка завершена: всего {total_count}, отправлено {sent_count}, пропущено {skipped_count}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомлений: {e}", exc_info=True)
            db.session.rollback()

def get_notification_message(notification_type: str) -> str:
    """Получение текста уведомления"""
    messages = {
        '5_days': (
            "💳 **Напоминание от VPVKS**\n\n"
            "Ваша подписка истекает через **5 дней**!\n\n"
            "Не ждите последнего момента — продлите сейчас:\n"
            "1. Откройте Mini App командой /app\n"
            "2. Перейдите в раздел «Оплатить»\n"
            "3. Выберите тариф и оплатите\n\n"
            "💡 Тарифы от 110₽/месяц\n"
            "🔒 Мгновенная активация после оплаты"
        ),
        '3_days': (
            "⏰ **Напоминание от VPVKS**\n\n"
            "Ваша подписка истекает через **3 дня**!\n\n"
            "Чтобы продолжить пользоваться VPN без перерывов:\n"
            "1. Откройте Mini App командой /app\n"
            "2. Перейдите в раздел «Оплатить»\n"
            "3. Выберите тариф и оплатите\n\n"
            "💡 Продление сейчас сохранит вашу скидку!"
        ),
        '2_days': (
            "⏳ **Напоминание VPVKS**\n\n"
            "Ваша подписка истекает через **2 дня**!\n\n"
            "Продлите сейчас чтобы не потерять доступ:\n"
            "👉 /app\n\n"
            "💰 Тарифы от 110₽/месяц"
        ),
        '1_day': (
            "⚠️ **Срочно! VPVKS**\n\n"
            "Ваша подписка истекает **завтра**!\n\n"
            "Не оставайтесь без защиты — продлите прямо сейчас:\n"
            "👉 /app\n\n"
            "💰 Тарифы от 110₽/месяц"
        ),
        '0_days': (
            "🚫 **Подписка истекла! VPVKS**\n\n"
            "Ваша подписка истекла **сегодня**.\n\n"
            "Для возобновления доступа к VPN:\n"
            "1. Откройте Mini App: /app\n"
            "2. Оплатите любой тариф\n"
            "3. Доступ восстановится автоматически\n\n"
            "💡 Мы сохранили ваши данные!"
        )
    }
    return messages.get(notification_type, '')

if __name__ == '__main__':
    check_expirations()
