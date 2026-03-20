#!/usr/bin/env python3
"""
Скрипт для синхронизации пользователей, которые оплатили, но не имеют ключей в Marzban
Запускать внутри контейнера backend или с доступом к БД и Marzban
"""

import os
import sys
from datetime import datetime

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_config import db
from database.models.user_model import User as UserModel
from database.models.payment_model import Payment as PaymentModel
from services.vpn_service import VPNService

def sync_paid_users():
    """Найти пользователей с успешными платежами и создать их в Marzban"""
    
    print("=" * 60)
    print("🔍 Синхронизация пользователей с успешными платежами")
    print("=" * 60)
    
    # Получаем все успешные платежи
    successful_payments = PaymentModel.query.filter_by(paid=True, status='succeeded').all()
    
    print(f"\n📊 Найдено успешных платежей: {len(successful_payments)}")
    
    # Группируем по user_id
    user_payments = {}
    for payment in successful_payments:
        if payment.user_id not in user_payments:
            user_payments[payment.user_id] = []
        user_payments[payment.user_id].append(payment)
    
    print(f"👥 Уникальных пользователей с оплатами: {len(user_payments)}")
    
    vpn_service = VPNService()
    synced_count = 0
    error_count = 0
    skipped_count = 0
    
    for user_id, payments in user_payments.items():
        print(f"\n{'-' * 40}")
        print(f"👤 Пользователь: {user_id}")
        
        # Проверяем пользователя в БД
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            print(f"  ❌ Пользователь не найден в БД")
            error_count += 1
            continue
        
        # Проверяем подписку
        if not user.subscription_end_date:
            print(f"  ⚠️ Нет subscription_end_date, вычисляем из платежей...")
            # Вычисляем дату окончания из суммы платежей
            total_amount = sum(float(p.amount) for p in payments)
            
            # Простая логика: 100₽ = 30 дней
            days = int((total_amount / 100) * 30)
            from datetime import timedelta
            user.subscription_end_date = datetime.utcnow() + timedelta(days=days)
            print(f"  💰 Сумма платежей: {total_amount}₽ → {days} дней")
            print(f"  📅 Новая дата окончания: {user.subscription_end_date}")
        
        # Проверяем активна ли подписка
        if user.subscription_end_date < datetime.utcnow():
            print(f"  ⏰ Подписка истекла: {user.subscription_end_date}")
            skipped_count += 1
            continue
        
        print(f"  ✅ Подписка активна до: {user.subscription_end_date}")
        
        # Проверяем, есть ли уже пользователь в Marzban
        username = f"user_{user_id}"
        marzban_result = vpn_service.marzban.get_user(username)
        
        if marzban_result.get('status') == 'success':
            print(f"  ✓ Уже существует в Marzban")
            skipped_count += 1
            continue
        
        # Создаём пользователя в Marzban
        print(f"  🔄 Создание в Marzban...")
        
        # Вычисляем expire timestamp
        expire_timestamp = int(user.subscription_end_date.timestamp())
        
        # Формируем payload
        data_limit_bytes = int(user.data_limit_gb * 1024**3) if user.data_limit_gb and user.data_limit_gb > 0 else 0
        
        payload = {
            "username": username,
            "proxies": ["VLESS Reality", "Trojan TLS"],
            "data_limit": data_limit_bytes,
            "expire": expire_timestamp,
            "inbounds": {
                "vless": ["VLESS Reality"],
                "trojan": ["Trojan TLS"]
            }
        }
        
        result = vpn_service.create_marzban_user_with_payload(user_id, payload)
        
        if result.get('status') == 'success':
            print(f"  ✅ Успешно создан в Marzban")
            synced_count += 1
            
            # Обновляем subscription_url в БД
            subscription_url = vpn_service.marzban.get_subscription_url(username)
            if subscription_url:
                user.subscription_url = subscription_url
                print(f"  🔗 Subscription URL: {subscription_url[:50]}...")
            
            db.session.commit()
        else:
            print(f"  ❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print("📊 ИТОГИ:")
    print(f"  ✅ Синхронизировано: {synced_count}")
    print(f"  ⏭️ Пропущено: {skipped_count}")
    print(f"  ❌ Ошибок: {error_count}")
    print("=" * 60)
    
    return {
        'synced': synced_count,
        'skipped': skipped_count,
        'errors': error_count
    }


if __name__ == '__main__':
    try:
        result = sync_paid_users()
        sys.exit(0 if result['errors'] == 0 else 1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
