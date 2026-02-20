import logging
from typing import Dict, Any, Optional
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import make_request
from utils.validation import validate_user_id, validate_plan_id, sanitize_input
from config import BACKEND_URL

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    # Validate user ID
    user_id = update.effective_user.id
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    # Sanitize user data
    username = sanitize_input(update.effective_user.username or "")
    first_name = sanitize_input(update.effective_user.first_name or "")
    last_name = sanitize_input(update.effective_user.last_name or "")

    # Register user with backend
    user_data = {
        'id': user_id,
        'username': username,
        'first_name': first_name,
        'last_name': last_name
    }

    try:
        response = await make_request('POST', f"{BACKEND_URL}/api/users", json=user_data)
        if response and response.status != 201:
            logger.warning(f"Failed to register user {user_id}: {await response.text()}")
    except Exception as e:
        logger.error(f"Error registering user {user_id}: {e}")

    welcome_message = (
        "👋 Добро пожаловать в VPN-бот!\n\n"
        "Я помогу вам управлять вашими VPN-подключениями.\n\n"
        "Доступные команды:\n"
        "/start - главное меню\n"
        "/help - справка по командам\n"
        "/status - проверить статус VPN-подключения\n"
        "/connect - подключиться к VPN\n"
        "/disconnect - отключиться от VPN\n"
        "/payment - управление подпиской и оплата\n"
        "/app - открыть полнофункциональное приложение\n"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    help_text = (
        "📋 Справка по командам бота:\n\n"
        "/start - главное меню\n"
        "/help - эта справка\n"
        "/status - проверить статус VPN-подключения\n"
        "/connect - подключиться к VPN\n"
        "/disconnect - отключиться от VPN\n"
        "/payment - управление подпиской и оплата\n"
        "/app - открыть полнофункциональное приложение\n\n"
        "Для дополнительной помощи свяжитесь с администратором."
    )
    await update.message.reply_text(help_text)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /status command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        response = await make_request('GET', f"{BACKEND_URL}/api/vpn/status/{user_id}")
        if response and response.status == 200:
            data = await response.json()

            if data.get('status') == 'success':
                sub_status = data['subscription']['status']
                days_left = data['subscription']['days_left']

                status_text = (
                    "📊 Статус VPN-подключения:\n\n"
                    f"Статус подписки: {'✅ Активна' if sub_status == 'active' else '❌ Просрочена' if sub_status == 'expired' else '🆓 Пробный период'}\n"
                    f"Осталось дней: {days_left}\n"
                    f"Триал использован: {'Да' if data['subscription']['trial_used'] else 'Нет'}\n"
                    f"VPN подключен: {'Да' if data['vpn']['connected'] else 'Нет'}"
                )
            else:
                status_text = f"⚠️ Ошибка получения статуса: {data.get('message', 'Неизвестная ошибка')}"
        else:
            logger.warning(f"Server returned status {response.status if response else 'None'} for user {user_id}")
            status_text = f"⚠️ Не удалось получить статус из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error getting status for user {user_id}: {e}")
        status_text = f"⚠️ Произошла ошибка при получении статуса"

    await update.message.reply_text(status_text)


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /connect command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        response = await make_request('POST', f"{BACKEND_URL}/api/vpn/connect", json={'user_id': user_id})
        if response and response.status == 200:
            data = await response.json()

            if data.get('status') == 'success':
                connect_text = (
                    "🔌 Подключаюсь к VPN...\n\n"
                    "✅ Подключение успешно инициировано!\n"
                    "Пожалуйста, подождите несколько секунд для установки соединения.\n\n"
                    f"Сервер: {data['connection_details']['server_ip']}:{data['connection_details']['server_port']}"
                )
            else:
                logger.warning(f"Connection failed for user {user_id}: {data.get('message', 'Unknown error')}")
                connect_text = f"❌ Ошибка подключения: {data.get('message', 'Неизвестная ошибка')}"
        else:
            logger.warning(f"Server returned status {response.status if response else 'None'} for connection request from user {user_id}")
            connect_text = "❌ Не удалось подключиться к VPN из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error connecting user {user_id} to VPN: {e}")
        connect_text = "❌ Произошла ошибка при попытке подключения к VPN"

    await update.message.reply_text(connect_text)


async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /disconnect command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        response = await make_request('POST', f"{BACKEND_URL}/api/vpn/disconnect", json={'user_id': user_id})
        if response and response.status == 200:
            disconnect_text = (
                "🔌 Отключаюсь от VPN...\n\n"
                "✅ Отключение успешно инициировано!\n"
                "Соединение будет разорвано в течение нескольких секунд."
            )
        else:
            logger.warning(f"Server returned status {response.status if response else 'None'} for disconnection request from user {user_id}")
            disconnect_text = "❌ Не удалось отключиться от VPN из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error disconnecting user {user_id} from VPN: {e}")
        disconnect_text = "❌ Произошла ошибка при попытке отключения от VPN"

    await update.message.reply_text(disconnect_text)


async def payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /payments command for subscription plans"""
    from utils.cache import get_cached_data, set_cached_data, CACHE_TIMEOUT
    
    user_id = update.effective_user.id
    
    # Try to get plans from cache first
    cache_key = "payment_plans"
    plans = get_cached_data(cache_key)
    
    if plans is None:
        try:
            response = await make_request('GET', f"{BACKEND_URL}/api/payment/plans")
            if response and response.status == 200:
                plans = await response.json()
                # Cache the plans for 10 minutes since they don't change often
                set_cached_data(cache_key, plans, ttl=600)
            else:
                logger.warning(f"Server returned status {response.status if response else 'None'} for payment plans request from user {user_id}")
                await update.message.reply_text(
                    "❌ Не удалось получить тарифные планы из-за ошибки сервера"
                )
                return
        except Exception as e:
            logger.error(f"Error getting payment plans for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при получении тарифных планов"
            )
            return
    
    # Create inline keyboard with subscription options
    keyboard = [
        [InlineKeyboardButton("💳 Тарифы подписки", callback_data="show_subscription_plans")],
    ]

    for plan in plans:
        keyboard.append([InlineKeyboardButton(
            f"{plan['name']} - {plan['price']}₽ ({plan['description']})",
            callback_data=f"plan_{plan['id']}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"💳 Тарифы подписки\n\n"
        f"Выберите тариф для оплаты:",
        reply_markup=reply_markup
    )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /app command to open the Web App"""
    from config import MINI_APP_URL

    # Create inline keyboard with Web App button
    keyboard = [[InlineKeyboardButton(
        "📱 Открыть VPN приложение",
        web_app={"url": MINI_APP_URL}
    )]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть полнофункциональное VPN-приложение:",
        reply_markup=reply_markup
    )