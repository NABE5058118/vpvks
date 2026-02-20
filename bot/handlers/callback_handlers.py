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
from admin.admin_handlers import handle_admin_callback

logger = logging.getLogger(__name__)


async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle both plan selection and admin panel callbacks from inline keyboard"""
    query = update.callback_query
    await query.answer()

    # Check if this is a payment status check callback
    if query.data.startswith('check_payment_'):
        payment_id = query.data.replace('check_payment_', '')
        user_id = query.from_user.id

        # Validate user ID and payment ID
        if not validate_user_id(user_id):
            logger.warning(f"Invalid user ID attempted payment check: {user_id}")
            await query.edit_message_text(text="❌ Неверный идентификатор пользователя")
            return

        # Basic validation for payment ID (should be alphanumeric)
        if not payment_id.isalnum():
            logger.warning(f"Invalid payment ID format: {payment_id}")
            await query.edit_message_text(text="❌ Неверный формат идентификатора платежа")
            return

        logger.info(f"Checking payment status for payment {payment_id} by user {user_id}")

        try:
            response = await make_request('GET', f"{BACKEND_URL}/api/payment/check/{payment_id}")
            if response and response.status == 200:
                data = await response.json()
                payment_info = data.get('payment_info', {})

                logger.info(f"Payment status for {payment_id}: {payment_info.get('status', 'unknown')}")

                status_messages = {
                    'pending': '⏳ Платёж ожидает оплаты',
                    'waiting_for_capture': '⏳ Платёж авторизован, ожидается подтверждение',
                    'succeeded': '✅ Платёж успешно завершён!',
                    'canceled': '❌ Платёж отменён'
                }

                status_text = status_messages.get(payment_info.get('status'), f"📊 Статус платежа: {payment_info.get('status', 'неизвестен')}")

                # Update message with payment status
                payment_message = (
                    f"💳 Информация о платеже:\n\n"
                    f"ID: {payment_info.get('id', 'N/A')}\n"
                    f"Сумма: {payment_info.get('amount', 'N/A')} {payment_info.get('currency', 'RUB')}\n"
                    f"{status_text}\n\n"
                )

                # Add appropriate buttons based on status
                keyboard = []
                if payment_info.get('status') == 'succeeded':
                    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])
                    payment_message += "\nПодписка будет активирована автоматически."
                elif payment_info.get('status') in ['pending', 'waiting_for_capture']:
                    keyboard.append([InlineKeyboardButton("🔄 Обновить статус", callback_data=query.data)])
                    if payment_info.get('confirmation_url'):
                        payment_message += f"\nСсылка для оплаты: {payment_info.get('confirmation_url')}"
                else:
                    keyboard.append([InlineKeyboardButton("💳 Повторить платёж", callback_data="payment")])

                keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="start")])

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(text=payment_message, reply_markup=reply_markup)
            else:
                logger.warning(f"Server returned status {response.status if response else 'None'} for payment check request from user {user_id}")
                await query.edit_message_text(text="❌ Не удалось получить статус платежа")
        except Exception as e:
            logger.error(f"Error checking payment status for payment {payment_id} by user {user_id}: {e}")
            await query.edit_message_text(text="❌ Произошла ошибка при проверке статуса платежа")

        return

    # Check if this is an admin callback
    if query.data.startswith('admin_'):
        await handle_admin_callback(query)
        return

    # Check if this is a request to show top-up options
    if query.data == "show_topup_options":
        # Show top-up options
        keyboard = [
            [InlineKeyboardButton("⭐ 10 звёзд - 100₽", callback_data="topup_10_100")],
            [InlineKeyboardButton("⭐ 25 звёзд - 225₽", callback_data="topup_25_225")],
            [InlineKeyboardButton("⭐ 50 звёзд - 400₽", callback_data="topup_50_400")],
            [InlineKeyboardButton("⭐ 100 звёзд - 700₽", callback_data="topup_100_700")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"💳 Пополнение баланса\n\n"
            f"Выберите количество звёзд для покупки:",
            reply_markup=reply_markup
        )
        return

    # Check if this is a request to show subscription plans again
    if query.data == "show_subscription_plans":
        from utils.cache import get_cached_data, set_cached_data
        
        # Get available plans from backend
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
                    logger.warning(f"Server returned status {response.status if response else 'None'} for payment plans request from user {query.from_user.id}")
                    await query.edit_message_text(
                        "❌ Не удалось получить тарифные планы из-за ошибки сервера"
                    )
                    return
            except Exception as e:
                logger.error(f"Error getting payment plans for user {query.from_user.id}: {e}")
                await query.edit_message_text(
                    "❌ Произошла ошибка при получении тарифных планов"
                )
                return
        
        # Create inline keyboard with payment options
        keyboard = []
        for plan in plans:
            keyboard.append([InlineKeyboardButton(
                f"{plan['name']} - {plan['price']}₽ ({plan['description']})",
                callback_data=f"plan_{plan['id']}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "💳 Выберите тарифный план:",
            reply_markup=reply_markup
        )
        return

    # Check if this is a top-up request
    if query.data.startswith('topup_'):
        # Format: topup_amount_price (e.g., topup_10_100)
        parts = query.data.split('_')
        if len(parts) == 3:
            try:
                stars_amount = int(parts[1])
                price = int(parts[2])

                # Validate amounts
                if stars_amount <= 0 or price <= 0:
                    logger.warning(f"Invalid top-up amount requested: {stars_amount} stars for {price} RUB")
                    await query.edit_message_text(text="❌ Неверные параметры пополнения")
                    return

                # Create payment for top-up
                user_id = query.from_user.id

                # Validate user ID
                if not validate_user_id(user_id):
                    logger.warning(f"Invalid user ID attempted top-up: {user_id}")
                    await query.edit_message_text(text="❌ Неверный идентификатор пользователя")
                    return

                payment_data = {
                    'user_id': user_id,
                    'stars_amount': stars_amount,
                    'price': price,
                    'description': f'Пополнение баланса: {stars_amount} звёзд за {price}₽'
                }

                response = await make_request('POST', f"{BACKEND_URL}/api/payment/topup", json=payment_data)
                if response and response.status in [200, 201]:
                    data = await response.json()

                    if data.get('status') == 'success':
                        confirmation_url = data['payment'].get('confirmation_url')

                        if confirmation_url:
                            payment_message = (
                                f"💳 Пополнение баланса\n\n"
                                f"Создан платёж на сумму {price}₽ за {stars_amount} звёзд\n\n"
                                f"Для оплаты:\n"
                                f"1. Скопируйте ссылку ниже\n"
                                f"2. Вставьте её в адресную строку браузера\n\n"
                                f"Ссылка для оплаты:\n{confirmation_url}\n\n"
                                f"После оплаты нажмите кнопку 'Проверить статус оплаты'"
                            )

                            keyboard = [
                                [InlineKeyboardButton("🔄 Проверить статус оплаты", callback_data=f"topup_check_{data['payment']['id']}")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await query.edit_message_text(text=payment_message, reply_markup=reply_markup)
                            return
                        else:
                            await query.edit_message_text(text="❌ Не удалось создать платёж для пополнения баланса")
                    else:
                        await query.edit_message_text(text=f"❌ Ошибка создания платежа: {data.get('message', 'Неизвестная ошибка')}")
                else:
                    logger.warning(f"Server returned status {response.status if response else 'None'} for top-up request from user {user_id}")
                    await query.edit_message_text(text="❌ Не удалось создать платёж для пополнения баланса")
            except ValueError:
                await query.edit_message_text(text="❌ Неверный формат данных пополнения")
        else:
            await query.edit_message_text(text="❌ Неверный формат данных пополнения")
        return

    # Handle subscription plan selection
    plan_id = query.data.replace('plan_', '')
    user_id = query.from_user.id

    # Validate user ID and plan ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID attempted plan selection: {user_id}")
        await query.edit_message_text(text="❌ Неверный идентификатор пользователя")
        return

    if not validate_plan_id(plan_id):
        logger.warning(f"Invalid plan ID format: {plan_id}")
        await query.edit_message_text(text="❌ Неверный формат идентификатора тарифа")
        return

    logger.info(f"Processing subscription payment for user {user_id}, plan {plan_id}")

    try:
        # Proceed directly to payment creation without checking balance (since we removed star system)
        # The payment will be processed directly via YooKassa

        # Create payment via backend
        payment_data = {
            'user_id': user_id,
            'plan_type': plan_id
        }

        response = await make_request('POST', f"{BACKEND_URL}/api/payment/create", json=payment_data)
        logger.info(f"Response status code: {response.status if response else 'None'}")

        if response and response.status in [200, 201]:
            data = await response.json()

            if data.get('status') == 'success':
                # For subscription plans, the payment is processed via YooKassa
                message = data.get('message', 'Подписка успешно оформлена!')

                payment_message = (
                    f"✅ Платёж создан успешно!\n\n"
                    f"{message}\n\n"
                    f"Для завершения оплаты перейдите по ссылке в мини-приложении.\n"
                    f"После оплаты статус подписки обновится автоматически."
                )

                # Create inline keyboard with payment confirmation URL if available
                keyboard = [
                    [InlineKeyboardButton("💳 Перейти к оплате", web_app={"url": f"{BACKEND_URL}/miniapp"})],
                    [InlineKeyboardButton("🔄 Проверить статус оплаты", callback_data=f"check_payment_{data['payment']['id']}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(text=payment_message, reply_markup=reply_markup)
                return
            else:
                logger.warning(f"Payment creation failed for user {user_id}, plan {plan_id}: {data.get('message', 'Unknown error')}")
                payment_message = f"❌ Ошибка создания платежа: {data.get('message', 'Неизвестная ошибка')}"
        else:
            logger.warning(f"Server returned status {response.status if response else 'None'} for payment creation request from user {user_id}")
            response_text = await response.text() if response else "No response"
            payment_message = f"❌ Не удалось создать платёж из-за ошибки сервера: {response.status if response else 'None'} - {response_text}"
    except Exception as e:
        logger.error(f"Error creating subscription payment for user {user_id}, plan {plan_id}: {e}")
        payment_message = f"❌ Произошла ошибка при создании платежа: {str(e)}"

    await query.edit_message_text(text=payment_message)