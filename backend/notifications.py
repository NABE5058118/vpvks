"""
Module for sending notifications to Telegram users
"""

import asyncio
import logging
from telegram import Bot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        if not BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set in environment variables!")
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables!")
        
        self.bot = Bot(token=BOT_TOKEN)

    async def send_payment_success_notification(self, user_id: int):
        """Send notification to user about successful payment"""
        logger.info(f"Attempting to send payment success notification to user {user_id}")
        try:
            message = (
                "🎉 Поздравляем! Ваша оплата прошла успешно!\n\n"
                "✅ Ваша подписка активирована.\n"
                "🔒 Теперь вы можете использовать VPN без ограничений.\n\n"
                "Для проверки статуса подписки используйте команду /status"
            )
            
            await self.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Payment success notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending payment success notification to user {user_id}: {e}")

    async def send_subscription_activated_notification(self, user_id: int, days_added: int = None):
        """Send notification to user about subscription activation"""
        logger.info(f"Attempting to send subscription activated notification to user {user_id}, days added: {days_added}")
        try:
            if days_added:
                message = (
                    f"✅ Ваша подписка продлена на {days_added} дней!\n\n"
                    "🔒 Теперь вы можете использовать VPN без ограничений.\n\n"
                    "Для проверки статуса подписки используйте команду /status"
                )
            else:
                message = (
                    "✅ Ваша подписка активирована!\n\n"
                    "🔒 Теперь вы можете использовать VPN без ограничений.\n\n"
                    "Для проверки статуса подписки используйте команду /status"
                )
                
            await self.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Subscription activated notification sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error sending subscription activated notification to user {user_id}: {e}")

# Global instance of notification service
notification_service = NotificationService()

def send_payment_success_notification_sync(user_id: int):
    """Synchronous wrapper for sending payment success notification"""
    logger.info(f"Calling synchronous payment success notification for user {user_id}")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(notification_service.send_payment_success_notification(user_id))
        loop.close()
        logger.info(f"Synchronous payment success notification completed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in sync wrapper for payment notification: {e}")

def send_subscription_activated_notification_sync(user_id: int, days_added: int = None):
    """Synchronous wrapper for sending subscription activated notification"""
    logger.info(f"Calling synchronous subscription activated notification for user {user_id}, days added: {days_added}")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(notification_service.send_subscription_activated_notification(user_id, days_added))
        loop.close()
        logger.info(f"Synchronous subscription activated notification completed for user {user_id}")
    except Exception as e:
        logger.error(f"Error in sync wrapper for subscription notification: {e}")