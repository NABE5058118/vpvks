"""
Module containing administrative functions for the VPN bot
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BACKEND_URL, is_admin
from utils.api_client import make_request
from utils.validation import validate_user_id
from utils.cache import get_cached_data, set_cached_data

logger = logging.getLogger(__name__)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /admin command for administrators"""
    user_id = update.effective_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID attempted admin access: {user_id}")
        await update.message.reply_text("❌ Неверный идентификатор пользователя")
        return

    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав администратора для доступа к этой команде.")
        return

    # Create inline keyboard for admin panel
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("💳 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton("📡 VPN Серверы", callback_data="admin_vpn_servers")],
        [InlineKeyboardButton("🖥️ Система", callback_data="admin_system")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🛡️ АДМИН-ПАНЕЛЬ VPN СИСТЕМЫ\n\n"
        "Выберите интересующий раздел:",
        reply_markup=reply_markup
    )


async def handle_admin_callback(query) -> None:
    """Handle admin panel callbacks from inline keyboard"""
    logger.info(f"Admin callback received: {query.data}")
    # Handle admin callback
    user_id = query.from_user.id

    # Validate user ID
    if not validate_user_id(user_id):
        logger.warning(f"Invalid user ID attempted admin access: {user_id}")
        await query.edit_message_text(text="❌ Неверный идентификатор пользователя")
        return

    if not is_admin(user_id):
        await query.edit_message_text(text="❌ У вас нет прав администратора.")
        return

    callback_data = query.data

    if callback_data == "admin_stats":
        # Get statistics from backend
        try:
            # Parallel requests for different stats
            async def get_basic_stats():
                response = await make_request('GET', f"{BACKEND_URL}/api/stats")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            async def get_additional_stats():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/stats/extended")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            # Run requests concurrently
            basic_task = asyncio.create_task(get_basic_stats())
            extended_task = asyncio.create_task(get_additional_stats())
            
            basic_stats = await basic_task
            extended_stats = await extended_task
            
            if basic_stats:
                stats_text = f"""
📊 СТАТИСТИКА СИСТЕМЫ

Всего пользователей: {basic_stats.get('total_users', 'N/A')}
Активных подписок: {basic_stats.get('active_subscriptions', 'N/A')}
Всего платежей: {basic_stats.get('total_payments', 'N/A')}
Выручка: {basic_stats.get('total_revenue', 'N/A')} ₽
                """
                
                # Add extended stats if available
                if extended_stats:
                    stats_text += f"""
                    
Дополнительная информация:
Новые за сегодня: {extended_stats.get('new_users_today', 'N/A')}
Активных за 24ч: {extended_stats.get('active_users_24h', 'N/A')}
Средний чек: {extended_stats.get('avg_payment', 'N/A')} ₽
                """
            else:
                stats_text = "📊 Статистика временно недоступна"
        except Exception as e:
            logger.error(f"Error getting stats for admin {user_id}: {e}")
            stats_text = "📊 Статистика временно недоступна"

        # Add back button
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=stats_text, reply_markup=reply_markup)

    elif callback_data == "admin_users":
        # Get user list and additional stats from backend
        try:
            # Parallel requests for user list and stats
            async def get_user_list():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/users")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            async def get_user_stats():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/users/stats")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            # Run requests concurrently
            users_task = asyncio.create_task(get_user_list())
            stats_task = asyncio.create_task(get_user_stats())
            
            users_response = await users_task
            stats_response = await stats_task
            
            if users_response:
                user_list = users_response.get('users', [])
                user_text = f"👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ ({len(user_list)}):\n\n"

                for user in user_list[:10]:  # Show first 10 users
                    user_text += f"• ID: {user.get('id', 'N/A')}\n"
                    user_text += f"  Имя: {user.get('username', 'N/A')}\n"
                    user_text += f"  Подписка: {user.get('subscription_status', 'N/A')}\n"
                    user_text += f"  Потрачено: {user.get('total_spent', 'N/A')} ₽\n\n"
                
                # Add stats if available
                if stats_response:
                    user_text += f"""
                    
📊 ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:
Всего пользователей: {stats_response.get('total_users', 'N/A')}
Активных: {stats_response.get('active_users', 'N/A')}
Новых за 24ч: {stats_response.get('new_users_24h', 'N/A')}
                """
            else:
                user_text = "👥 Список пользователей временно недоступен"
        except Exception as e:
            logger.error(f"Error getting users for admin {user_id}: {e}")
            user_text = "👥 Список пользователей временно недоступен"

        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔍 Найти пользователя", callback_data="admin_find_user")],
            [InlineKeyboardButton("📧 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=user_text, reply_markup=reply_markup)

    elif callback_data == "admin_payments":
        # Get payment list and additional stats from backend
        try:
            # Parallel requests for payments and stats
            async def get_payments_list():
                response = await make_request('GET', f"{BACKEND_URL}/api/payments")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            async def get_payment_stats():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/payments/stats")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            # Run requests concurrently
            payments_task = asyncio.create_task(get_payments_list())
            stats_task = asyncio.create_task(get_payment_stats())
            
            payments_response = await payments_task
            stats_response = await stats_task
            
            if payments_response:
                payment_list = payments_response.get('payments', [])
                payment_text = f"💳 СПИСОК ПЛАТЕЖЕЙ ({len(payment_list)}):\n\n"

                for payment in payment_list[:10]:  # Show first 10 payments
                    payment_text += f"• ID: {payment.get('id', 'N/A')}\n"
                    payment_text += f"  Сумма: {payment.get('amount', 'N/A')} ₽\n"
                    payment_text += f"  Статус: {payment.get('status', 'N/A')}\n"
                    payment_text += f"  Пользователь: {payment.get('user_id', 'N/A')}\n\n"
                
                # Add stats if available
                if stats_response:
                    payment_text += f"""
                    
📊 ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:
Всего платежей: {stats_response.get('total_payments', 'N/A')}
Успешных: {stats_response.get('successful_payments', 'N/A')}
На сумму: {stats_response.get('total_revenue', 'N/A')} ₽
                    """
            else:
                payment_text = "💳 Список платежей временно недоступен"
        except Exception as e:
            logger.error(f"Error getting payments for admin {user_id}: {e}")
            payment_text = "💳 Список платежей временно недоступен"

        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("➕ Создать ручной платёж", callback_data="admin_create_manual_payment")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=payment_text, reply_markup=reply_markup)

    elif callback_data == "admin_vpn_servers":
        # Get VPN server information and additional stats
        try:
            # Parallel requests for servers and stats
            async def get_servers_list():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/vpn/servers")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            async def get_server_stats():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/vpn/servers/stats")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            # Run requests concurrently
            servers_task = asyncio.create_task(get_servers_list())
            stats_task = asyncio.create_task(get_server_stats())
            
            servers_response = await servers_task
            stats_response = await stats_task
            
            if servers_response:
                server_list = servers_response.get('servers', [])
                server_text = "📡 СТАТУС VPN СЕРВЕРОВ:\n\n"

                for server in server_list:
                    status_emoji = "🟢" if server.get('status') == 'online' else "🔴"
                    server_text += f"{status_emoji} {server.get('name', 'N/A')}\n"
                    server_text += f"  IP: {server.get('ip_address', 'N/A')}:{server.get('port', 'N/A')}\n"
                    server_text += f"  Протокол: {server.get('protocol', 'N/A')}\n"
                    server_text += f"  Пользователей: {server.get('connected_users', 'N/A')}\n"
                    server_text += f"  Локация: {server.get('location', 'N/A')}\n\n"
                
                # Add stats if available
                if stats_response:
                    server_text += f"""
                    
📊 ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:
Всего серверов: {stats_response.get('total_servers', 'N/A')}
Онлайн: {stats_response.get('online_servers', 'N/A')}
Общее подключений: {stats_response.get('total_connections', 'N/A')}
                    """
            else:
                server_text = "📡 Информация о VPN серверах временно недоступна"
        except Exception as e:
            logger.error(f"Error getting VPN servers for admin {user_id}: {e}")
            server_text = "📡 Информация о VPN серверах временно недоступна"

        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить статус", callback_data="admin_refresh_servers")],
            [InlineKeyboardButton("🔧 Настроить", callback_data="admin_configure_server")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=server_text, reply_markup=reply_markup)

    elif callback_data == "admin_system":
        # Get system information and additional metrics
        try:
            # Parallel requests for system info and metrics
            async def get_system_info():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/system")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            async def get_system_metrics():
                response = await make_request('GET', f"{BACKEND_URL}/api/admin/system/metrics")
                if response and response.status == 200:
                    return await response.json()
                return None
            
            # Run requests concurrently
            info_task = asyncio.create_task(get_system_info())
            metrics_task = asyncio.create_task(get_system_metrics())
            
            info_response = await info_task
            metrics_response = await metrics_task
            
            if info_response:
                sys = info_response.get('system_info', {})
                system_text = f"""
🖥️ ИНФОРМАЦИЯ О СИСТЕМЕ

Платформа: {sys.get('platform', 'N/A')} {sys.get('platform_release', '')}
Архитектура: {sys.get('architecture', 'N/A')}
Процессор: {sys.get('processor', 'N/A')}
Ядер CPU: {sys.get('cpu_count', 'N/A')} | Загрузка: {sys.get('cpu_percent', 'N/A')}%
Память: {(sys.get('memory_total', 0) / (1024**3)):,.1f} ГБ | Использовано: {sys.get('memory_percent', 'N/A')}%
Диск: {(sys.get('disk_total', 0) / (1024**3)):,.1f} ГБ | Использовано: {sys.get('disk_percent', 'N/A')}%
Время сервера: {sys.get('server_time', 'N/A')}
                """
                
                # Add metrics if available
                if metrics_response:
                    system_text += f"""
                    
📊 ДОПОЛНИТЕЛЬНЫЕ МЕТРИКИ:
Загрузка сети: {metrics_response.get('network_load', 'N/A')}%
Температура CPU: {metrics_response.get('cpu_temp', 'N/A')}°C
Количество процессов: {metrics_response.get('process_count', 'N/A')}
                    """
            else:
                system_text = "🖥️ Системная информация временно недоступна"
        except Exception as e:
            logger.error(f"Error getting system info for admin {user_id}: {e}")
            system_text = "🖥️ Системная информация временно недоступна"

        # Add navigation buttons
        keyboard = [
            [InlineKeyboardButton("📈 Мониторинг", callback_data="admin_monitoring")],
            [InlineKeyboardButton("💾 Бэкап", callback_data="admin_backup")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=system_text, reply_markup=reply_markup)

    elif callback_data == "admin_settings":
        settings_text = """
⚙️ НАСТРОЙКИ АДМИНИСТРАТОРА

• Управление пользователями
• Настройка тарифов
• Мониторинг системы
• Настройки уведомлений
• Резервное копирование
• Логирование
        """

        # Add configuration buttons
        keyboard = [
            [InlineKeyboardButton("📋 Тарифы", callback_data="admin_plans")],
            [InlineKeyboardButton("📢 Уведомления", callback_data="admin_notifications")],
            [InlineKeyboardButton("🔒 Безопасность", callback_data="admin_security")],
            [InlineKeyboardButton("🔙 Назад", callback_data="admin_main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=settings_text, reply_markup=reply_markup)

    elif callback_data == "admin_main_menu":
        # Return to main admin menu
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton("💳 Платежи", callback_data="admin_payments")],
            [InlineKeyboardButton("📡 VPN Серверы", callback_data="admin_vpn_servers")],
            [InlineKeyboardButton("🖥️ Система", callback_data="admin_system")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="🛡️ АДМИН-ПАНЕЛЬ VPN СИСТЕМЫ\n\n"
                 "Выберите интересующий раздел:",
            reply_markup=reply_markup
        )