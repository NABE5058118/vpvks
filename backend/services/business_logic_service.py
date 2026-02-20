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
                
                # Update user in db
                User.users_db[user.id] = user
            
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
            # First, verify that user exists
            from models.user import User
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': f'User with ID {user_id} does not exist'
                }

            # Define pricing based on plan type (in RUB)
            pricing = {
                'month': {'price': 110, 'description': '1 месяц - 110₽', 'days': 30},
                '4months': {'price': 290, 'description': '4 месяца - 290₽', 'days': 120},
                '12months': {'price': 500, 'description': '12 месяцев - 500₽', 'days': 365}
            }

            if plan_type not in pricing:
                return {
                    'status': 'error',
                    'message': 'Invalid plan type'
                }

            plan = pricing[plan_type]

            # Create payment via YooKassa
            payment_data = {
                'amount': plan['price'],
                'currency': 'RUB',
                'description': plan['description'],
                'user_id': user_id,
                'return_url': 'http://localhost:5000/payment-success'
            }

            payment_result = self.payment_service.create_payment(payment_data)

            if 'error' in payment_result:
                return payment_result

            # Check if this is a mock payment (test mode)
            if 'id' in payment_result and 'mock_' in payment_result['id']:
                # In test mode, immediately activate the subscription
                print(f"Detected mock payment {payment_result['id']} for user {user_id}, activating subscription immediately")
                activation_result = self.activate_subscription_for_user(user_id)
                print(f"Subscription activation result for user {user_id}: {activation_result}")

            return {
                'status': 'success',
                'payment': payment_result
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
                    'trial_used': user.trial_used
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
        return [
            {
                'id': 'month',
                'name': '1 месяц',
                'price': 110,
                'currency': 'RUB',
                'duration_days': 30,
                'description': '30 дней подписки'
            },
            {
                'id': '4months',
                'name': '4 месяца',
                'price': 290,
                'currency': 'RUB',
                'duration_days': 120,
                'description': '120 дней подписки'
            },
            {
                'id': '12months',
                'name': '12 месяцев',
                'price': 500,
                'currency': 'RUB',
                'duration_days': 365,
                'description': '365 дней подписки (выгодная цена)'
            }
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
                    110: 30,   # 1 month
                    290: 120,  # 4 months
                    500: 365   # 12 months
                }

                # Convert Decimal to float/int for mapping
                amount_float = float(latest_payment.amount)
                days_to_add = duration_mapping.get(amount_float, 30)  # Default to 30 days

                logger.info(f"Determined subscription duration: {days_to_add} days for amount {amount_float}")

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

                # Send notification to user about subscription activation
                try:
                    from notifications import send_subscription_activated_notification_sync
                    logger.info(f"Sending subscription activation notification to user {user_id}")
                    send_subscription_activated_notification_sync(user_id, days_to_add)
                    logger.info(f"Subscription activation notification sent to user {user_id}")
                except Exception as e:
                    print(f"Error sending subscription activation notification to user {user_id}: {e}")
                    logger.error(f"Error sending subscription activation notification to user {user_id}: {e}")

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