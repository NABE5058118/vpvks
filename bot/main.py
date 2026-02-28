import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, JobQueue

from config import BOT_TOKEN, BACKEND_URL, MINI_APP_URL, ADMIN_IDS

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Импорты для асинхронной работы
import aiohttp
from utils.validation import validate_user_id, sanitize_input

# Импорты обработчиков VPN ключей
from handlers.vpn_key_handler import get_vpn_key, renew_vpn_key, handle_renew_selection

# Импорты уведомлений
from notifications import send_expiration_reminder, send_welcome_notification_sync


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command - register user and show menu with Mini App"""
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
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(f"{BACKEND_URL}/api/users", json=user_data) as response:
                if response.status != 201:
                    logger.warning(f"Failed to register user {user_id}: {await response.text()}")
    except Exception as e:
        logger.error(f"Error registering user {user_id}: {e}")

    # Get user balance from backend
    balance = 0
    try:
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(f"{BACKEND_URL}/api/users/{user_id}/balance") as response:
                if response.status == 200:
                    data = await response.json()
                    balance = data.get('balance', 0)
    except Exception as e:
        logger.error(f"Error getting balance: {e}")

    # Create inline keyboard with Mini App button
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    keyboard = [
        [
            InlineKeyboardButton("🚀 Открыть VPN приложение", web_app=WebAppInfo(url=MINI_APP_URL)),
        ],
        [
            InlineKeyboardButton("💰 Баланс", callback_data="menu_balance"),
            InlineKeyboardButton("💜 Поддержка", callback_data="menu_tariff"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Welcome message
    username_display = f"@{username}" if username else first_name or "Пользователь"

    welcome_message = (
        f"👋 Привет, {username_display}!\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Баланс: {balance} ₽\n\n"
        "🎉 Все ключи бесплатные и бессрочные!\n\n"
        "Нажми кнопку ниже чтобы открыть приложение 👇"
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')
    
    # Отправляем приветственное уведомление
    try:
        send_welcome_notification_sync(user_id, username_display)
    except Exception as e:
        logger.error(f"Не удалось отправить приветственное уведомление: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command"""
    help_text = (
        "📋 Справка по командам бота:\n\n"
        "/start - главное меню\n"
        "/help - эта справка\n"
        "/status - проверить статус VPN-подключения\n"
        "/key - получить ключ VPN (V2Ray)\n"
        "/connect - подключиться к VPN\n"
        "/disconnect - отключиться от VPN\n"
        "/payment - управление подпиской и оплата\n"
        "/app - открыть полнофункциональное приложение\n\n"
        "Для дополнительной помощи свяжитесь с администратором."
    )
    await update.message.reply_text(help_text)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /status command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(f"{BACKEND_URL}/api/vpn/status/{user_id}") as response:
                if response.status == 200:
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
                    logger.warning(f"Server returned status {response.status} for user {user_id}")
                    status_text = f"⚠️ Не удалось получить статус из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error getting status for user {user_id}: {e}")
        status_text = f"⚠️ Произошла ошибка при получении статуса"

    await update.message.reply_text(status_text)


async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /connect command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(f"{BACKEND_URL}/api/vpn/connect", json={'user_id': user_id}) as response:
                if response.status == 200:
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
                    logger.warning(f"Server returned status {response.status} for connection request from user {user_id}")
                    connect_text = "❌ Не удалось подключиться к VPN из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error connecting user {user_id} to VPN: {e}")
        connect_text = "❌ Произошла ошибка при попытке подключения к VPN"

    await update.message.reply_text(connect_text)


async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /disconnect command"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.post(f"{BACKEND_URL}/api/vpn/disconnect", json={'user_id': user_id}) as response:
                if response.status == 200:
                    disconnect_text = (
                        "🔌 Отключаюсь от VPN...\n\n"
                        "✅ Отключение успешно инициировано!\n"
                        "Соединение будет разорвано в течение нескольких секунд."
                    )
                else:
                    logger.warning(f"Server returned status {response.status} for disconnection request from user {user_id}")
                    disconnect_text = "❌ Не удалось отключиться от VPN из-за ошибки сервера"
    except Exception as e:
        logger.error(f"Error disconnecting user {user_id} from VPN: {e}")
        disconnect_text = "❌ Произошла ошибка при попытке отключения от VPN"

    await update.message.reply_text(disconnect_text)


async def payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /payments command for subscription plans"""
    user_id = update.effective_user.id

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(f"{BACKEND_URL}/api/payment/plans") as response:
                if response.status == 200:
                    plans = await response.json()

                    # Create inline keyboard with subscription options
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
                else:
                    await update.message.reply_text(
                        "❌ Не удалось получить тарифные планы из-за ошибки сервера"
                    )
    except Exception as e:
        logger.error(f"Error in payments command for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при открытии меню оплаты"
        )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /app command to open the Web App"""
    from config import MINI_APP_URL

    # Create inline keyboard with Web App button
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [[InlineKeyboardButton(
        "📱 Открыть VPN приложение",
        web_app={"url": MINI_APP_URL}
    )]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Нажмите кнопку ниже, чтобы открыть полнофункциональное VPN-приложение:",
        reply_markup=reply_markup
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /admin command for administrators"""
    from config import is_admin
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🛡️ АДМИН-ПАНЕЛЬ\n\nВыберите раздел:",
        reply_markup=reply_markup
    )


async def key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /key command for getting VPN keys"""
    await get_vpn_key(update, context)


async def renew_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /renew command for renewing VPN keys"""
    await renew_vpn_key(update, context)


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu callbacks from inline keyboard"""
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    user_id = update.effective_user.id

    # Import here to avoid scope issues
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    # Обработка инструкции по VPN
    if callback_data == "vpn_instruction":
        from handlers.vpn_key_handler import show_vpn_instruction
        await show_vpn_instruction(update, context)
        return

    if callback_data == "menu_balance":
        # Get balance from backend
        balance = 0
        try:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            connector = aiohttp.TCPConnector(ssl=False)

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(f"{BACKEND_URL}/api/users/{user_id}/balance") as response:
                    if response.status == 200:
                        data = await response.json()
                        balance = data.get('balance', 0)
        except Exception as e:
            logger.error(f"Error getting balance: {e}")

        await query.edit_message_text(
            f"💰 Ваш баланс\n\n"
            f"ID: {user_id}\n"
            f"Баланс: {balance} ₽\n\n"
            f"🎉 Все ключи бесплатные и бессрочные!\n"
            f"💜 Вы можете поддержать проект в Mini App"
        )
        return

    if callback_data == "menu_tariff":
        await query.edit_message_text(
            f"💜 Поддержка проекта\n\n"
            f"🎉 Все ключи бесплатные и бессрочные!\n\n"
            f"Откройте Mini App чтобы поддержать проект 👇"
        )
        return

    # По умолчанию
    await query.edit_message_text(text="⚠️ Функция в разработке.")


def main():
    """Start the bot"""
    logger.info("Initializing VPN Bot...")

    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment variables!")
        return
    else:
        logger.info("Bot token loaded successfully")

    if not BACKEND_URL:
        logger.warning("BACKEND_URL not set, using default")

    try:
        logger.info("Creating application with bot token...")
        application = Application.builder().token(BOT_TOKEN).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("key", key_command))
        application.add_handler(CommandHandler("app", app_command))
        application.add_handler(CommandHandler("admin", admin_command))
        
        # Register callback query handler for menu
        application.add_handler(CallbackQueryHandler(handle_plan_selection))

        # Setup JobQueue for automatic notifications
        logger.info("Setting up JobQueue for automatic notifications...")
        job_queue = JobQueue()
        job_queue.application = application
        
        # Ежедневная проверка подписок в 10:00
        job_queue.run_daily(
            send_expiration_reminder,
            time=datetime.time(10, 0),  # 10:00 утра
            name="expiration_reminder"
        )
        logger.info("✅ JobQueue настроен: уведомления об истечении в 10:00")

        # Start the bot
        logger.info("Starting VPN Bot polling...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()