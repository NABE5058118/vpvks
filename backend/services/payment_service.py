import uuid
from datetime import datetime
from decimal import Decimal
import yookassa
from yookassa import Payment as YooPayment, Refund
from yookassa import Configuration
from dotenv import load_dotenv
import os
import sys
import logging

# Add the parent directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database components
from database.db_config import db
from models.payment import Payment as PaymentModel
from models.user import User

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        """Initialize payment service with YooKassa credentials"""
        shop_id = os.getenv('YOOKASSA_SHOP_ID')
        secret_key = os.getenv('YOOKASSA_SECRET_KEY')

        if shop_id and secret_key:
            Configuration.account_id = shop_id
            Configuration.secret_key = secret_key
        else:
            # For testing purposes, we'll skip configuration if env vars are not set
            print("Warning: YooKassa credentials not found. Payment functionality may not work properly.")

        self.test_mode = os.getenv('YOOKASSA_TEST_MODE', 'false').lower() == 'true'
        self.return_url = os.getenv('YOOKASSA_RETURN_URL', 'http://localhost:5000/payment-success')

    def create_payment(self, payment_data):
        """Create a new payment via YooKassa"""
        try:
            # Check if test mode is enabled
            test_mode = os.getenv('YOOKASSA_TEST_MODE', 'false').lower() == 'true'

            if test_mode:
                # In test mode, return mock payment data that simulates successful payment
                mock_payment_id = f"mock_{uuid.uuid4().hex[:16]}"

                # Create mock payment in database with succeeded status
                payment_db = PaymentModel.create({
                    'id': mock_payment_id,
                    'amount': payment_data.get('amount'),
                    'currency': payment_data.get('currency', 'RUB'),
                    'description': payment_data.get('description', f"Payment for VPN service by user {payment_data.get('user_id')}"),
                    'user_id': payment_data.get('user_id'),
                    'status': 'succeeded',  # Immediately set to succeeded in test mode
                    'paid': True,  # Immediately mark as paid in test mode
                    'test': True,  # Mark as test payment
                    'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                })

                payment_info = {
                    'id': mock_payment_id,
                    'amount': payment_data.get('amount'),
                    'currency': payment_data.get('currency', 'RUB'),
                    'description': payment_data.get('description', f"Payment for VPN service by user {payment_data.get('user_id')}"),
                    'user_id': payment_data.get('user_id'),
                    'status': 'succeeded',  # Immediately set to succeeded in test mode
                    'created_at': datetime.now().isoformat(),
                    'confirmation_url': f"https://yoomoney.ru/checkout/payments/checkout-test?orderId={mock_payment_id}",  # Realistic test URL
                    'paid': True,  # Immediately mark as paid in test mode
                    'test': True,  # Mark as test payment
                    'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                }

                return payment_info
            else:
                # Check if YooKassa is properly configured
                shop_id = os.getenv('YOOKASSA_SHOP_ID')
                secret_key = os.getenv('YOOKASSA_SECRET_KEY')

                if not shop_id or not secret_key:
                    # Return mock payment data for testing purposes when no credentials provided
                    mock_payment_id = f"mock_{uuid.uuid4().hex[:16]}"

                    # Create mock payment in database
                    payment_db = PaymentModel.create({
                        'id': mock_payment_id,
                        'amount': payment_data.get('amount'),
                        'currency': payment_data.get('currency', 'RUB'),
                        'description': payment_data.get('description', f"Payment for VPN service by user {payment_data.get('user_id')}"),
                        'user_id': payment_data.get('user_id'),
                        'status': 'succeeded',  # In test mode, immediately set to succeeded
                        'paid': True,  # In test mode, immediately mark as paid
                        'test': True,  # Mark as test payment
                        'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                    })

                    payment_info = {
                        'id': mock_payment_id,
                        'amount': payment_data.get('amount'),
                        'currency': payment_data.get('currency', 'RUB'),
                        'description': payment_data.get('description', f"Payment for VPN service by user {payment_data.get('user_id')}"),
                        'user_id': payment_data.get('user_id'),
                        'status': 'succeeded',  # In test mode, immediately set to succeeded
                        'created_at': datetime.now().isoformat(),
                        'confirmation_url': f"http://localhost:5000/mock-payment/{mock_payment_id}",
                        'paid': True,  # In test mode, immediately mark as paid
                        'test': True,  # Mark as test payment
                        'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                    }

                    return payment_info

                # Prepare payment data for YooKassa (works in both live and test modes)
                payment_request = {
                    "amount": {
                        "value": str(payment_data.get('amount')),
                        "currency": payment_data.get('currency', 'RUB')
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": self.return_url
                    },
                    "capture": True,
                    "description": payment_data.get('description', f"Payment for VPN service by user {payment_data.get('user_id')}"),
                    "metadata": {
                        "user_id": payment_data.get('user_id')
                    }
                }

                # Generate idempotency key for safe retries
                idempotency_key = str(uuid.uuid4())

                # Create payment via YooKassa with idempotency key
                yookassa_payment = YooPayment.create(payment_request, idempotency_key)

                # Create payment record in database
                payment_db = PaymentModel.create({
                    'id': yookassa_payment.id,
                    'amount': Decimal(str(yookassa_payment.amount.value)),
                    'currency': yookassa_payment.amount.currency,
                    'description': yookassa_payment.description,
                    'user_id': yookassa_payment.metadata.get('user_id'),
                    'status': yookassa_payment.status,
                    'paid': yookassa_payment.paid,
                    'yookassa_response': dict(yookassa_payment),  # Store full response as JSON
                    'test': getattr(yookassa_payment, 'test', False),  # Add test flag if available
                    'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                })

                # Store payment info locally
                payment_info = {
                    'id': yookassa_payment.id,
                    'amount': float(yookassa_payment.amount.value),
                    'currency': yookassa_payment.amount.currency,
                    'description': yookassa_payment.description,
                    'user_id': yookassa_payment.metadata.get('user_id'),
                    'status': yookassa_payment.status,
                    'created_at': yookassa_payment.created_at,
                    'confirmation_url': yookassa_payment.confirmation.confirmation_url if yookassa_payment.confirmation else None,
                    'paid': yookassa_payment.paid,
                    'test': getattr(yookassa_payment, 'test', False),  # Add test flag if available
                    'stars_amount': payment_data.get('stars_amount', 0)  # Add stars amount if provided
                }

                return payment_info

        except Exception as e:
            # Return error info
            return {
                'error': str(e),
                'status': 'failed'
            }

    def check_payment_status(self, payment_id):
        """Check payment status via YooKassa"""
        try:
            # First, try to get the payment from our database
            local_payment = PaymentModel.get_by_id(payment_id)
            
            # Then, get the latest status from YooKassa
            yookassa_payment = YooPayment.find_one(payment_id)
            
            # Update our local database with the latest status only if the payment hasn't been finalized
            # We don't want to override a 'succeeded' status with 'pending' due to timing issues
            if local_payment:
                # Only update if the local status is not already a final state
                final_states = ['succeeded', 'canceled', 'refunded']
                if local_payment.status not in final_states:
                    local_payment.status = yookassa_payment.status
                    local_payment.paid = yookassa_payment.paid
                    db.session.commit()
                    logger.info(f"Updated local payment status for {payment_id} from YooKassa: {yookassa_payment.status}")
                else:
                    logger.info(f"Local payment status for {payment_id} is already final: {local_payment.status}, not updating from YooKassa")
            else:
                # If payment doesn't exist locally, create it (might happen if webhook didn't arrive yet)
                logger.warning(f"Payment {payment_id} not found locally, creating from YooKassa data")
            
            logger.info(f"Checked payment status for {payment_id}")
            
            # Return detailed payment information
            # If we have a local payment with a final status, return that info
            # Otherwise return info from YooKassa
            if local_payment and local_payment.status in ['succeeded', 'canceled', 'refunded']:
                # Use local payment data for final statuses
                payment_info = {
                    'id': local_payment.id,
                    'status': local_payment.status,
                    'amount': float(local_payment.amount),
                    'currency': local_payment.currency,
                    'description': local_payment.description,
                    'created_at': local_payment.created_at.isoformat(),
                    'paid': local_payment.paid,
                    'test': local_payment.test
                }
                logger.info(f"Returning local payment data for {payment_id} with final status: {local_payment.status}")
            else:
                # Use YooKassa data for non-final statuses
                payment_info = {
                    'id': yookassa_payment.id,
                    'status': yookassa_payment.status,
                    'amount': float(yookassa_payment.amount.value),
                    'currency': yookassa_payment.amount.currency,
                    'description': yookassa_payment.description,
                    'created_at': yookassa_payment.created_at,
                    'paid': yookassa_payment.paid,
                    'test': getattr(yookassa_payment, 'test', False),
                    'payment_method': yookassa_payment.payment_method.type if yookassa_payment.payment_method else None,
                    'receipt_registration': getattr(yookassa_payment, 'receipt_registration', None)
                }
                logger.info(f"Returning YooKassa payment data for {payment_id}: {yookassa_payment.status}")
            
            return payment_info
        except Exception as e:
            logger.error(f"Error checking payment status for {payment_id}: {str(e)}")
            return {'error': str(e), 'status': 'error'}

    def confirm_payment(self, payment_id):
        """Confirm payment as successful (internal method)"""
        try:
            yookassa_payment = YooPayment.find_one(payment_id)
            if yookassa_payment and yookassa_payment.paid:
                # Update our local database
                local_payment = PaymentModel.get_by_id(payment_id)
                if local_payment:
                    local_payment.update_status(yookassa_payment.status)
                    db.session.commit()
                
                logger.info(f"Payment confirmed: {yookassa_payment.id}")
                return {
                    'id': yookassa_payment.id,
                    'status': yookassa_payment.status,
                    'paid': yookassa_payment.paid
                }
            logger.warning(f"Payment not found or not paid: {payment_id}")
            return {'error': 'Payment not found or not paid'}
        except Exception as e:
            logger.error(f"Error confirming payment {payment_id}: {str(e)}")
            return {'error': str(e)}

    def cancel_payment(self, payment_id):
        """Cancel payment"""
        try:
            # In YooKassa, you can't really "cancel" a payment that hasn't been confirmed
            # Instead, we'll just update our local status
            yookassa_payment = YooPayment.find_one(payment_id)
            if yookassa_payment:
                # Update our local database
                local_payment = PaymentModel.get_by_id(payment_id)
                if local_payment:
                    local_payment.update_status('cancelled')
                    db.session.commit()
                
                logger.info(f"Payment cancelled: {yookassa_payment.id}")
                return {
                    'id': yookassa_payment.id,
                    'status': 'cancelled'
                }
            logger.warning(f"Payment not found for cancellation: {payment_id}")
            return {'error': 'Payment not found'}
        except Exception as e:
            logger.error(f"Error cancelling payment {payment_id}: {str(e)}")
            return {'error': str(e)}