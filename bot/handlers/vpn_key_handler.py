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
    
    # Создаём inline клавиатуру с выбором протокола
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
                # Запрос к Marzban через backend
                async with session.post(
                    f"{BACKEND_URL}/api/marzban/create",
                    json={'user_id': user_id, 'tariff': 'standard'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status') == 'success':
                            subscription_url = data.get('subscription_url', '')
                            username = data.get('username', '')
                            
                            await query.edit_message_text(
                                f"✅ Ваш ключ V2Ray готов!\n\n"
                                f"🔑 Ссылка подписки:\n"
                                f"```\n{subscription_url}\n```\n\n"
                                f"📱 Инструкция по подключению:\n"
                                f"1. Скачайте клиент:\n"
                                f"   • Android: v2rayNG\n"
                                f"   • iOS: V2Box, Streisand\n"
                                f"   • Desktop: Hiddify, Nekoray\n\n"
                                f"2. Добавьте подписку из буфера\n"
                                f"3. Подключитесь к серверу\n\n"
                                f"👤 Ваш логин: {username}",
                                parse_mode='Markdown'
                            )
                        else:
                            await query.edit_message_text(
                                f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}"
                            )
                    else:
                        await query.edit_message_text(
                            f"❌ Ошибка сервера (код: {response.status})\n"
                            f"Попробуйте позже или обратитесь в поддержку."
                        )
            
            elif vpn_type == "vpn_wireguard":
                # Запрос к WireGuard через backend
                async with session.get(
                    f"{BACKEND_URL}/api/wireguard/qr/{user_id}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        config_text = data.get('config_text', '')
                        
                        # Формируем QR code URL для WireGuard
                        # В реальном приложении лучше использовать API для генерации QR
                        await query.edit_message_text(
                            f"✅ Ваш ключ WireGuard готов!\n\n"
                            f"🔑 Конфигурация:\n"
                            f"```\n{config_text}\n```\n\n"
                            f"📱 Инструкция по подключению:\n"
                            f"1. Скачайте WireGuard:\n"
                            f"   • Android: WireGuard (Google Play)\n"
                            f"   • iOS: WireGuard (App Store)\n\n"
                            f"2. Добавьте туннель вручную\n"
                            f"3. Скопируйте конфиг выше\n"
                            f"4. Подключитесь",
                            parse_mode='Markdown'
                        )
                    else:
                        # Пробуем получить просто статус
                        async with session.get(
                            f"{BACKEND_URL}/api/wireguard/status/{user_id}"
                        ) as status_response:
                            if status_response.status == 200:
                                status_data = await status_response.json()
                                if not status_data.get('has_config'):
                                    await query.edit_message_text(
                                        "⚠️ У вас нет конфигурации WireGuard.\n\n"
                                        "Сначала подключитесь к VPN через команду /connect\n"
                                        "или обратитесь в поддержку."
                                    )
                                else:
                                    await query.edit_message_text(
                                        "❌ Ошибка получения конфига. Попробуйте позже."
                                    )
                            else:
                                await query.edit_message_text(
                                    "❌ Ошибка сервера. Попробуйте позже."
                                )
    
    except aiohttp.ClientError as e:
        logger.error(f"Client error in handle_vpn_selection: {e}")
        await query.edit_message_text(
            "❌ Ошибка подключения к серверу.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )
    except Exception as e:
        logger.error(f"Error in handle_vpn_selection: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ Произошла ошибка при генерации ключа.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )


async def renew_vpn_key(update: Update, context):
    """Перевыпуск ключа VPN (сброс и генерация нового)"""
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
        "Это действие создаст новый ключ и аннулирует старый.\n"
        "Старый ключ перестанет работать immediately.\n\n"
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
                # Сначала удаляем старого пользователя, затем создаём нового
                async with session.post(
                    f"{BACKEND_URL}/api/marzban/remove/{user_id}"
                ) as remove_response:
                    # Игнорируем ошибку, если пользователь не найден
                    
                    # Создаём нового пользователя
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
                                    f"🔑 Новая ссылка подписки:\n"
                                    f"```\n{subscription_url}\n```\n\n"
                                    f"⚠️ Старый ключ больше не работает!",
                                    parse_mode='Markdown'
                                )
                            else:
                                await query.edit_message_text(
                                    f"❌ Ошибка: {data.get('message', 'Неизвестная ошибка')}"
                                )
                        else:
                            await query.edit_message_text(
                                f"❌ Ошибка сервера (код: {create_response.status})"
                            )
            
            elif action == "renew_wireguard":
                # Для WireGuard нужно удалить старый конфиг и создать новый
                # Это требует дополнительной логики на backend
                await query.edit_message_text(
                    "⚠️ Перевыпуск WireGuard ключа временно недоступен.\n"
                    "Обратитесь в поддержку для помощи."
                )
    
    except Exception as e:
        logger.error(f"Error in handle_renew_selection: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при перевыпуске ключа.\n"
            "Обратитесь в поддержку."
        )
