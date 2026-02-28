"""
VPN Key Handler
Обработчики для получения ключей VPN (V2Ray/Marzban)
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from config import BACKEND_URL
import aiohttp

logger = logging.getLogger(__name__)


async def get_vpn_key(update: Update, context):
    """Получение ключа VPN (V2Ray) - сразу открываем Mini App"""
    user_id = update.effective_user.id
    
    from config import MINI_APP_URL
    from telegram import WebAppInfo
    
    # Создаём клавиатуру с кнопкой открытия Mini App
    keyboard = [
        [
            InlineKeyboardButton("🔑 Открыть экран получения ключа", web_app=WebAppInfo(url=MINI_APP_URL)),
        ],
        [
            InlineKeyboardButton("📱 Инструкция", callback_data="vpn_instruction"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔑 **Ключ V2Ray**\n\n"
        "🚀 VLESS Reality + Trojan TLS\n"
        "Лучшее решение для обхода блокировок\n\n"
        "Нажмите кнопку ниже, чтобы получить ключ:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_vpn_instruction(update: Update, context):
    """Показать инструкцию по использованию ключа"""
    query = update.callback_query
    await query.answer()
    
    instruction_text = (
        "📱 **Инструкция по подключению**\n\n"
        "**1. Скачайте приложение:**\n"
        "• Android: v2rayNG, Hiddify\n"
        "• iOS: V2Box, Hiddify, Streisand\n"
        "• Все платформы: Hiddify\n\n"
        "**2. Добавьте подписку:**\n"
        "• Откройте приложение\n"
        "• Нажмите «Добавить подписку» или «Import from URL»\n"
        "• Вставьте ссылку из Mini App\n\n"
        "**3. Подключитесь:**\n"
        "• Выберите сервер\n"
        "• Нажмите кнопку подключения\n"
        "• Пользуйтесь! ✅\n\n"
        "🔒 Протоколы: VLESS Reality + Trojan TLS\n"
        "🌍 Сервер: Стокгольм, Швеция"
    )
    
    await query.edit_message_text(instruction_text, parse_mode='Markdown')


async def renew_vpn_key(update: Update, context):
    """Перевыпуск ключа VPN - сразу открываем Mini App"""
    user_id = update.effective_user.id
    
    from config import MINI_APP_URL
    from telegram import WebAppInfo
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Перевыпустить ключ", web_app=WebAppInfo(url=MINI_APP_URL)),
        ],
        [
            InlineKeyboardButton("❌ Отмена", callback_data="renew_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ **Перевыпуск ключа V2Ray**\n\n"
        "Это действие создаст новый ключ и аннулирует старый.\n\n"
        "Нажмите кнопку для перевыпуска:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_renew_selection(update: Update, context):
    """Обработка перевыпуска ключа"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "renew_cancel":
        await query.edit_message_text("❌ Перевыпуск ключа отменён.")
        return
    
    # Перевыпуск через Mini App
    from config import MINI_APP_URL
    from telegram import WebAppInfo
    
    keyboard = [
        [
            InlineKeyboardButton("🔑 Открыть для перевыпуска", web_app=WebAppInfo(url=MINI_APP_URL)),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔄 **Перевыпуск ключа**\n\n"
        "Откройте Mini App для перевыпуска ключа:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
