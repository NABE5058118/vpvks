"""
VPN Key Handler
Обработчики для получения ключей VPN (WireGuard и V2Ray/Marzban)
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from config import BACKEND_URL
import aiohttp

logger = logging.getLogger(__name__)


async def get_vpn_key(update: Update, context):
    """Получение ключа VPN (WireGuard или V2Ray)"""
    user_id = update.effective_user.id

    keyboard = [
        [
            InlineKeyboardButton("🔒 V2Ray (VLESS/Trojan)", callback_data="vpn_v2ray"),
            InlineKeyboardButton("🛡️ WireGuard", callback_data="vpn_wireguard"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔑 Выберите тип VPN подключения:\n\n"
        "🔒 V2Ray (VLESS/Trojan) — лучше обходит блокировки\n"
        "🛡️ WireGuard — выше скорость и стабильность\n\n"
        "Оба протокола работают на наших серверах.",
        reply_markup=reply_markup
    )


async def handle_vpn_selection(update: Update, context):
    """Обработка выбора VPN протокола"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    vpn_type = query.data

    await query.edit_message_text("⏳ Генерирую ключ...")

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            if vpn_type == "vpn_v2ray":
                async with session.post(
                    f"{BACKEND_URL}/api/marzban/create",
                    json={'user_id': user_id, 'tariff': 'standard'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            subscription_url = data.get('subscription_url', '')
                            username = data.get('username', '')

                            if not subscription_url:
                                # Пробуем получить подписку отдельно
                                await query.edit_message_text(
                                    f"✅ Ваш ключ V2Ray готов!\n\n"
                                    f"👤 Логин: {username}\n\n"
                                    f"⏳ Ссылка генерируется...\n"
                                    f"Попробуйте получить ключ ещё раз."
                                )
                            else:
                                await query.edit_message_text(
                                    f"✅ Ваш ключ V2Ray готов!\n\n"
                                    f"🔑 Ссылка подписки:\n{subscription_url}\n\n"
                                    f"📱 Инструкция:\n"
                                    f"1. Скачайте v2rayNG (Android) или V2Box (iOS)\n"
                                    f"2. Добавьте подписку\n"
                                    f"3. Подключитесь\n\n"
                                    f"👤 Логин: {username}"
                                )
                        else:
                            await query.edit_message_text(
                                f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}"
                            )
                    else:
                        await query.edit_message_text(f"❌ Ошибка сервера (код: {response.status})")

            elif vpn_type == "vpn_wireguard":
                async with session.get(f"{BACKEND_URL}/api/wireguard/qr/{user_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        config_text = data.get('config_text', '')
                        await query.edit_message_text(
                            f"✅ Ваш ключ WireGuard готов!\n\n"
                            f"🔑 Конфигурация:\n{config_text}\n\n"
                            f"📱 Скачайте WireGuard и импортируйте конфиг"
                        )
                    else:
                        await query.edit_message_text("❌ Ошибка получения конфига")

    except Exception as e:
        logger.error(f"Error in handle_vpn_selection: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при генерации ключа.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )


async def renew_vpn_key(update: Update, context):
    """Перевыпуск ключа VPN"""
    user_id = update.effective_user.id

    keyboard = [
        [
            InlineKeyboardButton("🔒 V2Ray", callback_data="renew_v2ray"),
            InlineKeyboardButton("🛡️ WireGuard", callback_data="renew_wireguard"),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="renew_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ Перевыпуск ключа VPN\n\n"
        "Это действие создаст новый ключ и аннулирует старый.\n\n"
        "Выберите протокол:",
        reply_markup=reply_markup
    )


async def handle_renew_selection(update: Update, context):
    """Обработка выбора перевыпуска ключа"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    action = query.data

    if action == "renew_cancel":
        await query.edit_message_text("❌ Перевыпуск ключа отменён.")
        return

    await query.edit_message_text("⏳ Перевыпускаю ключ...")

    try:
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            if action == "renew_v2ray":
                async with session.post(
                    f"{BACKEND_URL}/api/marzban/remove/{user_id}"
                ) as remove_response:
                    async with session.post(
                        f"{BACKEND_URL}/api/marzban/create",
                        json={'user_id': user_id, 'tariff': 'standard'}
                    ) as create_response:
                        if create_response.status == 200:
                            data = await create_response.json()
                            if data.get('status') == 'success':
                                subscription_url = data.get('subscription_url', '')
                                await query.edit_message_text(
                                    f"✅ Ключ V2Ray перевыпущен!\n\n"
                                    f"🔑 Новая ссылка:\n{subscription_url}\n\n"
                                    f"⚠️ Старый ключ больше не работает!"
                                )
                            else:
                                await query.edit_message_text(f"❌ Ошибка: {data.get('message')}")
                        else:
                            await query.edit_message_text(f"❌ Ошибка сервера")

            elif action == "renew_wireguard":
                await query.edit_message_text(
                    "⚠️ Перевыпуск WireGuard временно недоступен.\n"
                    "Обратитесь в поддержку."
                )

    except Exception as e:
        logger.error(f"Error in handle_renew_selection: {e}")
        await query.edit_message_text("❌ Ошибка при перевыпуске ключа.")
