"""
Business Logic Service
Coordinates the various services to implement business rules
"""

import sys
import os
import logging

# Add the parent directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vpn_service import VPNService
from services.payment_service import PaymentService
from models.user import User
from datetime import datetime, timedelta
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BusinessLogicService:
    def __init__(self):
        self.vpn_service = VPNService()
        self.payment_service = PaymentService()

    def register_new_user(self, user_data):
        """Register a new user and set up their account"""
        try:
            # Create user in the database
            user = User.create(user_data)

            # Set up trial period if applicable
            if not user_data.get('has_paid', False):
                # Grant 7-day trial
                user.subscription_end_date = datetime.now() + timedelta(days=7)
                user.trial_used = True

                # Commit changes to database
                from database.db_config import db
                db.session.commit()

            return {
                'status': 'success',
                'user': user.to_dict()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def initiate_vpn_connection(self, user_id):
        """Handle the process of initiating a VPN connection"""
        try:
            # Get user
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': 'User not found'
                }
            
            # Check if user has active subscription
            if user.subscription_end_date and user.subscription_end_date < datetime.now():
                return {
                    'status': 'error',
                    'message': 'Subscription expired. Please renew your subscription.'
                }
            
            # Connect to VPN
            result = self.vpn_service.connect(user_id)
            
            return result
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def process_subscription_payment(self, user_id, plan_type):
        """Process payment for subscription plans via YooKassa"""
        try:
            from models.user import User
            from config.tariffs import get_tariff_by_id

            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': f'User with ID {user_id} does not exist'
                }

            # Get tariff from configuration
            tariff = get_tariff_by_id(plan_type)
            if not tariff:
                return {
                    'status': 'error',
                    'message': 'Invalid plan type'
                }

            # Create payment via YooKassa
            payment_data = {
                'amount': tariff['price'],
                'currency': tariff['currency'],
                'description': f"{tariff['name']} ({tariff['description']}, {tariff['data_limit_gb']}GB)",
                'user_id': user_id,
                'return_url': 'https://vpvks.ru/payment-success'
            }

            payment_result = self.payment_service.create_payment(payment_data)

            if 'error' in payment_result:
                return payment_result

            return {
                'status': 'success',
                'payment': payment_result,
                'tariff': tariff
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def handle_successful_payment(self, payment_id):
        """Handle the logic when a payment is confirmed"""
        try:
            # Verify payment status
            status = self.payment_service.check_payment_status(payment_id)
            
            if status != 'succeeded':
                return {
                    'status': 'error',
                    'message': f'Payment not successful. Current status: {status}'
                }
            
            # Get payment details to identify user
            # In a real implementation, we'd store payment details in our DB
            # For now, we'll assume the payment service has the user ID
            payment = self.payment_service.confirm_payment(payment_id)
            
            if 'error' in payment:
                return payment
            
            # Extend user subscription based on payment
            # This is simplified - in reality, we'd map payment_id to user and plan
            user_id = payment.get('user_id')  # This would come from our payment records
            if user_id:
                user = User.get_by_id(user_id)
                if user:
                    # Extend subscription (this is simplified)
                    if not user.subscription_end_date or user.subscription_end_date < datetime.now():
                        user.subscription_end_date = datetime.now() + timedelta(days=30)  # Default to 30 days
                    else:
                        user.subscription_end_date += timedelta(days=30)  # Extend by 30 days
                    
                    # Update user in db
                    User.users_db[user.id] = user
            
            return {
                'status': 'success',
                'message': 'Payment processed successfully',
                'payment': payment
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_user_subscription_status(self, user_id):
        """Get the subscription status for a user"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': 'User not found'
                }

            # Determine subscription status
            if not user.subscription_end_date:
                subscription_status = 'no_subscription'
                days_left = 0
            elif user.subscription_end_date < datetime.now():
                subscription_status = 'expired'
                days_left = 0
            else:
                days_left = (user.subscription_end_date - datetime.now()).days
                if days_left <= 0:
                    subscription_status = 'expired'
                    days_left = 0
                else:
                    subscription_status = 'active'

            # Get VPN connection status
            vpn_status = self.vpn_service.get_connection_status(user_id)

            return {
                'status': 'success',
                'subscription': {
                    'status': subscription_status,
                    'expires_at': user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                    'days_left': days_left,
                    'trial_used': user.trial_used,
                    'data_limit_gb': user.data_limit_gb,
                    'used_traffic_gb': user.used_traffic_gb
                },
                'vpn': vpn_status
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def get_available_plans(self):
        """Get available subscription plans"""
        from config.tariffs import get_all_tariffs
        
        tariffs = get_all_tariffs()
        return [
            {
                'id': tariff['id'],
                'name': tariff['name'],
                'price': tariff['price'],
                'currency': tariff['currency'],
                'duration_days': tariff['days'],
                'description': tariff['description'],
                'data_limit_gb': tariff['data_limit_gb'],
                'popular': tariff.get('popular', False)
            }
            for tariff in tariffs
        ]

    def activate_subscription_for_user(self, user_id):
        """Activate subscription for user after successful payment"""
        try:
            # Get user
            user = User.get_by_id(user_id)
            if not user:
                print(f"User with ID {user_id} not found")
                logger.warning(f"User with ID {user_id} not found")
                return {
                    'status': 'error',
                    'message': 'User not found'
                }

            logger.info(f"Activating subscription for user {user_id}")

            # Find the most recent payment for this user to determine plan
            from models.payment import Payment as PaymentModel
            user_payments = PaymentModel.get_payments_by_user(user_id)

            # Find the most recent payment that is not succeeded yet or the most recent succeeded payment
            # We want to find the most recent payment that could trigger subscription activation
            all_payments = [p for p in user_payments]
            if all_payments:
                # Take the most recent payment
                latest_payment = max(all_payments, key=lambda p: p.created_at)

                logger.info(f"Latest payment for user {user_id}: {latest_payment.id}, status: {latest_payment.status}")

                # Only proceed if payment is succeeded or waiting_for_capture
                if latest_payment.status not in ['succeeded', 'waiting_for_capture']:
                    print(f"Latest payment for user {user_id} is not in a valid state for subscription activation: {latest_payment.status}")
                    logger.warning(f"Latest payment for user {user_id} is not in a valid state for subscription activation: {latest_payment.status}")
                    return {
                        'status': 'error',
                        'message': f'Latest payment is not in a valid state for subscription activation: {latest_payment.status}'
                    }

                # Determine subscription duration based on payment amount
                duration_mapping = {
                    99: 30,   # 1 месяц
                    299: 90,  # 3 месяца
                    599: 180  # 6 месяцев
                }

                # Convert Decimal to float/int for mapping
                amount_float = float(latest_payment.amount)
                
                # Get tariff from configuration
                from config.tariffs import get_tariff_by_id
                tariff = get_tariff_by_id('month')  # Только один тариф - 1 месяц
                
                days_to_add = tariff['days']
                data_limit_gb = tariff['data_limit_gb']  # 0 = безлимитно

                logger.info(f"Determined subscription duration: {days_to_add} days")
                logger.info(f"Data limit: {'Безлимитный' if data_limit_gb == 0 else f'{data_limit_gb}GB'}")

                # Update user subscription
                from database.db_config import db
                if not user.subscription_end_date or user.subscription_end_date < datetime.now():
                    user.subscription_end_date = datetime.now() + timedelta(days=days_to_add)
                    print(f"Set new subscription end date for user {user_id}: {user.subscription_end_date}")
                    logger.info(f"Set new subscription end date for user {user_id}: {user.subscription_end_date}")
                else:
                    user.subscription_end_date += timedelta(days=days_to_add)
                    print(f"Extended subscription end date for user {user_id}: {user.subscription_end_date}")
                    logger.info(f"Extended subscription end date for user {user_id}: {user.subscription_end_date}")

                # Update user traffic limit
                user.data_limit_gb = data_limit_gb
                print(f"Set data limit for user {user_id}: {data_limit_gb}GB")
                logger.info(f"Set data limit for user {user_id}: {data_limit_gb}GB")

                # Update payment status to succeeded if it wasn't already
                if latest_payment.status != 'succeeded':
                    latest_payment.update_status('succeeded')
                    print(f"Updated payment {latest_payment.id} status to succeeded")
                    logger.info(f"Updated payment {latest_payment.id} status to succeeded")

                # Ensure payment status is set to succeeded for test payments
                latest_payment.status = 'succeeded'
                latest_payment.paid = True
                print(f"Ensured payment {latest_payment.id} is marked as succeeded and paid")
                logger.info(f"Ensured payment {latest_payment.id} is marked as succeeded and paid")

                # If this payment included stars, update user balance
                if hasattr(latest_payment, 'stars_amount') and latest_payment.stars_amount > 0:
                    # Add stars to user balance
                    current_balance = user.balance if user.balance else 0
                    new_balance = current_balance + latest_payment.stars_amount
                    user.balance = new_balance
                    print(f"Added {latest_payment.stars_amount} stars to user {user_id} balance. New balance: {new_balance}")
                    logger.info(f"Added {latest_payment.stars_amount} stars to user {user_id} balance. New balance: {new_balance}")

                # Commit changes to database
                db.session.commit()
                print(f"Committed changes to database for user {user_id}. Subscription end date: {user.subscription_end_date}")
                logger.info(f"Committed changes to database for user {user_id}. Subscription end date: {user.subscription_end_date}")

                # 🔴 СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ В MARZBAN
                try:
                    from services.vpn_service import VPNService
                    vpn_service = VPNService()

                    # Вычисляем expire timestamp
                    expire_date = user.subscription_end_date
                    expire_timestamp = int(expire_date.timestamp())

                    # Создаём username для Marzban
                    username = f"user_{user_id}"

                    # 🔴 Формируем payload с inbounds и лимитом трафика
                    data_limit_bytes = data_limit_gb * 1024**3
                    
                    protocols = ["VLESS Reality", "Trojan TLS"]
                    payload = {
                        "username": username,
                        "proxies": protocols,
                        "data_limit": data_limit_bytes,
                        "expire": expire_timestamp,
                        "inbounds": {
                            "vless": ["VLESS Reality"],
                            "trojan": ["Trojan TLS"]
                        }
                    }

                    logger.info(f"Creating Marzban user {username} with payload: {payload}")
                    logger.info(f"Data limit: {data_limit_gb}GB ({data_limit_bytes} bytes)")

                    # Создаём пользователя через VPN Service
                    result = vpn_service.create_marzban_user_with_payload(user_id, payload)

                    if result.get('status') == 'success':
                        logger.info(f"✅ Marzban user created: {username}")
                        print(f"✅ Marzban user created: {username}")
                    else:
                        logger.warning(f"⚠️ Marzban user creation failed: {result.get('message', 'Unknown error')}")
                        print(f"⚠️ Marzban user creation failed: {result.get('message', 'Unknown error')}")

                except Exception as e:
                    logger.error(f"❌ Error creating Marzban user: {e}")
                    print(f"❌ Error creating Marzban user: {e}")

                # Send notification to user about subscription activation
                try:
                    from notifications import send_payment_success_notification_sync
                    logger.info(f"Sending payment success notification to user {user_id}")
                    send_payment_success_notification_sync(user_id, amount_float, days_to_add)
                    logger.info(f"Payment success notification sent to user {user_id}")
                except Exception as e:
                    print(f"Error sending payment notification to user {user_id}: {e}")
                    logger.error(f"Error sending payment notification to user {user_id}: {e}")

                return {
                    'status': 'success',
                    'message': 'Subscription activated successfully',
                    'user_id': user_id,
                    'subscription_end_date': user.subscription_end_date.isoformat()
                }
            else:
                print(f"No payments found for user {user_id}")
                logger.warning(f"No payments found for user {user_id}")
                return {
                    'status': 'error',
                    'message': 'No payments found for user'
                }

        except Exception as e:
            print(f"Error activating subscription for user {user_id}: {str(e)}")
            logger.error(f"Error activating subscription for user {user_id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }