"""
API Routes for VPN Bot Backend
"""

from flask import Blueprint, request, jsonify
import sys
import os
import base64

# Add the parent directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vpn_service import VPNService
from services.payment_service import PaymentService
from services.business_logic_service import BusinessLogicService
from models.user import User

import logging

routes_bp = Blueprint('routes', __name__)
business_service = BusinessLogicService()
payment_service = PaymentService()
vpn_service = VPNService()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@routes_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user information"""
    try:
        user = User.get_by_id(user_id)
        if user:
            return jsonify(user.to_dict())
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>/balance', methods=['GET'])
def get_user_balance(user_id):
    """Get user balance"""
    try:
        from models.user import User
        balance = User.get_balance(user_id)
        return jsonify({'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@routes_bp.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        user = User.create(data)
        return jsonify(user.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/vpn/connect', methods=['POST'])
def connect_vpn():
    """Initiate VPN connection"""
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        
        result = business_service.initiate_vpn_connection(data.get('user_id'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/vpn/disconnect', methods=['POST'])
def disconnect_vpn():
    """Disconnect VPN connection"""
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Using VPN service directly for disconnection
        result = business_service.vpn_service.disconnect(data.get('user_id'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/vpn/status/<int:user_id>', methods=['GET'])
def vpn_status(user_id):
    """Get VPN connection status for user"""
    try:
        result = business_service.get_user_subscription_status(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/vpn/key/<int:user_id>', methods=['GET'])
def get_vpn_key(user_id):
    """Get or generate VPN subscription key for user"""
    try:
        from database.db_config import db
        from database.models.user_model import User as UserModel
        from services.vpn_service import VPNService
        
        # Получаем пользователя
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Проверяем активную подписку
        if not user.is_subscription_active():
            return jsonify({
                'status': 'error',
                'message': 'Подписка не активна. Пожалуйста, оплатите тариф.'
            }), 403
        
        # Если ключ уже сохранён - возвращаем его
        if user.subscription_url and user.vpn_key_generated:
            logger.info(f"🔑 Returning saved subscription URL for user {user_id}")
            return jsonify({
                'status': 'success',
                'subscription_url': user.subscription_url,
                'key_generated': True
            })
        
        # Генерируем новый ключ через Marzban
        logger.info(f"🔑 Generating new subscription URL for user {user_id}")
        vpn_service = VPNService()
        result = vpn_service.create_marzban_user(user_id, 'standard')
        
        if result.get('status') == 'success':
            subscription_url = result.get('subscription_url')
            
            # Сохраняем в БД
            user.subscription_url = subscription_url
            user.vpn_key_generated = True
            db.session.commit()
            
            logger.info(f"✅ Saved subscription URL for user {user_id}")
            
            return jsonify({
                'status': 'success',
                'subscription_url': subscription_url,
                'key_generated': True
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('message', 'Failed to generate key')
            }), 500
            
    except Exception as e:
        logger.error(f"Error in get_vpn_key: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/check-fingerprint', methods=['POST'])
def check_fingerprint():
    """
    Проверка device fingerprint для защиты от шаринга
    Возвращает warning если обнаружено подключение с нового устройства
    """
    try:
        from database.db_config import db
        from database.models.user_model import User as UserModel
        
        data = request.get_json()
        user_id = data.get('user_id')
        ip = data.get('ip')
        user_agent = data.get('user_agent')
        
        if not user_id or not ip:
            return jsonify({'error': 'user_id and ip are required'}), 400
        
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Первое подключение
        if not user.last_connected_ip:
            user.last_connected_ip = ip
            user.last_connected_user_agent = user_agent
            user.connection_count = 1
            db.session.commit()
            logger.info(f"🔒 Первое подключение для user_{user_id} с IP {ip}")
            return jsonify({
                'status': 'ok',
                'message': 'Первое подключение'
            })
        
        # Проверка совпадения
        if user.last_connected_ip != ip or user.last_connected_user_agent != user_agent:
            user.connection_count += 1
            
            # Если 3+ разных устройства — подозрительно
            if user.connection_count >= 3:
                user.suspicious_activity = True
                db.session.commit()
                logger.warning(f"⚠️ Подозрительная активность: user_{user_id} подключился с {user.connection_count} разных устройств")
                return jsonify({
                    'status': 'warning',
                    'message': 'Обнаружено подключение с нового устройства. Если это не вы — обратитесь в поддержку.'
                }), 403
            
            # Обновляем fingerprint
            user.last_connected_ip = ip
            user.last_connected_user_agent = user_agent
            user.connection_count = 1
            db.session.commit()
            logger.info(f"🔒 Обновлён fingerprint для user_{user_id}: новый IP {ip}")
            return jsonify({
                'status': 'ok',
                'message': 'Fingerprint обновлён'
            })
        
        # Всё совпадает - обычное подключение
        user.connection_count = 1
        db.session.commit()
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Error in check_fingerprint: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>/reset-device', methods=['POST'])
def reset_device(user_id):
    """Сброс fingerprint устройства пользователя"""
    try:
        from database.db_config import db
        from database.models.user_model import User as UserModel
        
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.last_connected_ip = None
        user.last_connected_user_agent = None
        user.connection_count = 0
        user.suspicious_activity = False
        db.session.commit()
        
        logger.info(f"🔄 Сброшен fingerprint для user_{user_id}")
        return jsonify({'status': 'success', 'message': 'Устройство сброшено'})
        
    except Exception as e:
        logger.error(f"Error in reset_device: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/check/<payment_id>', methods=['GET'])
def check_payment(payment_id):
    """Check payment status"""
    try:
        payment_info = payment_service.check_payment_status(payment_id)
        return jsonify({'payment_id': payment_id, 'payment_info': payment_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/payment/confirm/<payment_id>', methods=['POST'])
def confirm_payment(payment_id):
    """Confirm payment"""
    try:
        result = payment_service.confirm_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/payment/plans', methods=['GET'])
def get_plans():
    """Get available subscription plans"""
    try:
        plans = business_service.get_available_plans()
        return jsonify(plans)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/create', methods=['POST'])
def create_payment():
    """Create a new payment"""
    try:
        data = request.get_json()

        if not data or 'plan_type' not in data or 'user_id' not in data:
            return jsonify({'error': 'plan_type and user_id are required'}), 400

        # Detect if the request is coming from iOS device
        user_agent = request.headers.get('User-Agent', '').lower()
        is_ios = 'iphone' in user_agent or 'ipad' in user_agent or 'ipod' in user_agent

        result = business_service.process_subscription_payment(data.get('user_id'), data.get('plan_type'))

        # If payment was created successfully, add payment_id to the confirmation URL
        # This allows the Mini App to show payment status after redirect from YooKassa
        if result.get('status') == 'success' and result.get('payment'):
            payment_data = result['payment']
            payment_id = payment_data.get('id')

            if payment_id and payment_data.get('confirmation_url'):
                # Add payment_id to the confirmation URL as a query parameter
                # YooKassa will redirect to: return_url?payment_id=xxx
                # But we also want to preserve the original confirmation_url for YooKassa
                # The payment_id is already in the URL from YooKassa's return_url
                pass

            # For iOS, add iOS-specific payment URL
            if is_ios:
                ios_payment_url = f"http://localhost:5000/payment-options-ios"
                payment_data['ios_payment_url'] = ios_payment_url

        return jsonify(result), 201 if result.get('status') == 'success' else 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/topup', methods=['POST'])
def create_topup_payment():
    """Create a payment for balance top-up"""
    try:
        data = request.get_json()

        if not data or 'user_id' not in data or 'stars_amount' not in data or 'price' not in data:
            return jsonify({'error': 'user_id, stars_amount, and price are required'}), 400

        # Detect if the request is coming from iOS device
        user_agent = request.headers.get('User-Agent', '').lower()
        is_ios = 'iphone' in user_agent or 'ipad' in user_agent or 'ipod' in user_agent

        # Create payment for top-up
        payment_data = {
            'amount': data.get('price'),
            'currency': 'RUB',
            'description': data.get('description', f"Top-up: {data.get('stars_amount')} stars for {data.get('price')}₽"),
            'user_id': data.get('user_id'),
            'stars_amount': data.get('stars_amount')  # Add stars amount for top-up
        }

        result = payment_service.create_payment(payment_data)

        if 'error' in result:
            return jsonify(result), 400

        # If iOS device, modify the response to include iOS-specific payment URL
        if is_ios:
            result['ios_payment_url'] = f"http://localhost:5000/payment-options-ios"

        return jsonify({
            'status': 'success',
            'payment': result
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@routes_bp.route('/api/payment/cancel/<payment_id>', methods=['POST'])
def cancel_payment(payment_id):
    """Cancel payment"""
    try:
        result = payment_service.cancel_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@routes_bp.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    """
    Handle YooKassa webhook notifications
    This endpoint receives payment status updates from YooKassa
    """
    try:
        # Get JSON payload from YooKassa
        payload = request.get_json()

        # Log the received webhook
        print(f"Received YooKassa webhook: {payload}")
        logger.info(f"Received YooKassa webhook: {payload}")

        # Verify webhook source (optional but recommended)
        # You can add additional validation here

        # Extract payment information
        event_type = payload.get('event')
        object_data = payload.get('object', {})
        payment_id = object_data.get('id')
        status = object_data.get('status')

        print(f"Webhook event: {event_type}, Payment ID: {payment_id}, Status: {status}")
        logger.info(f"Webhook event: {event_type}, Payment ID: {payment_id}, Status: {status}")

        # Process different event types
        if event_type == 'payment.succeeded':
            # Payment was successful
            print(f"Payment {payment_id} succeeded")
            logger.info(f"Payment {payment_id} succeeded")

            # Update payment status in our database FIRST
            from models.payment import Payment as PaymentModel
            from database.db_config import db

            # Update payment status in our database
            payment = PaymentModel.get_by_id(payment_id)
            if payment:
                payment.update_status('succeeded')
                db.session.commit()
                print(f"Payment {payment_id} status updated in database to 'succeeded'")
                logger.info(f"Payment {payment_id} status updated in database to 'succeeded'")
            else:
                print(f"Payment {payment_id} not found in database")
                logger.warning(f"Payment {payment_id} not found in database")

            # Then update user account based on payment type
            user_id = object_data.get('metadata', {}).get('user_id')
            if user_id:
                # This is a subscription payment - activate subscription
                print(f"Activating subscription for user {user_id}")
                logger.info(f"Activating subscription for user {user_id}")
                
                result = business_service.activate_subscription_for_user(int(user_id))
                
                # Send notification to user about successful payment
                try:
                    from notifications import send_payment_success_notification_sync
                    print(f"Sending payment success notification to user {user_id}")
                    logger.info(f"Sending payment success notification to user {user_id}")
                    send_payment_success_notification_sync(int(user_id))
                    print(f"Notification sent successfully to user {user_id}")
                    logger.info(f"Notification sent successfully to user {user_id}")
                except Exception as e:
                    print(f"Error sending notification to user {user_id}: {e}")
                    logger.error(f"Error sending notification to user {user_id}: {e}")

        elif event_type == 'payment.waiting_for_capture':
            # Payment authorized but needs capture (for manual capture mode)
            print(f"Payment {payment_id} waiting for capture")
            logger.info(f"Payment {payment_id} waiting for capture")

            # Update payment status in our database
            from models.payment import Payment as PaymentModel
            from database.db_config import db

            # Update payment status in our database
            payment = PaymentModel.get_by_id(payment_id)
            if payment:
                payment.update_status('waiting_for_capture')
                db.session.commit()
                print(f"Payment {payment_id} status updated in database to 'waiting_for_capture'")
                logger.info(f"Payment {payment_id} status updated in database to 'waiting_for_capture'")

        elif event_type == 'payment.canceled':
            # Payment was canceled
            print(f"Payment {payment_id} was canceled")
            logger.info(f"Payment {payment_id} was canceled")

            # Update payment status in our database
            from models.payment import Payment as PaymentModel
            from database.db_config import db

            # Update payment status in our database
            payment = PaymentModel.get_by_id(payment_id)
            if payment:
                payment.update_status('canceled')
                db.session.commit()
                print(f"Payment {payment_id} status updated in database to 'canceled'")
                logger.info(f"Payment {payment_id} status updated in database to 'canceled'")

        elif event_type == 'refund.succeeded':
            # Refund was processed
            print(f"Refund for payment {payment_id} succeeded")
            logger.info(f"Refund for payment {payment_id} succeeded")

            # Update payment status in our database
            from models.payment import Payment as PaymentModel
            from database.db_config import db

            # Update payment status in our database
            payment = PaymentModel.get_by_id(payment_id)
            if payment:
                payment.update_status('refunded')
                db.session.commit()
                print(f"Payment {payment_id} status updated in database to 'refunded'")
                logger.info(f"Payment {payment_id} status updated in database to 'refunded'")

        # Return success response to acknowledge receipt
        print(f"Webhook processed successfully for payment {payment_id}")
        logger.info(f"Webhook processed successfully for payment {payment_id}")
        return jsonify({'status': 'OK'}), 200

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': str(e)}), 400


@routes_bp.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics for admin panel"""
    try:
        from models.user import User
        from models.payment import Payment
        from database.db_config import db
        from datetime import datetime
        
        # Count total users
        total_users = len(User.get_all_users())
        
        # Count active subscriptions
        all_users = User.get_all_users()
        active_subscriptions = sum(1 for user in all_users if user.is_subscription_active())
        
        # Count total payments
        all_payments = Payment.get_recent_payments(limit=1000)  # Last 1000 payments
        total_payments = len(all_payments)
        
        # Calculate total revenue
        total_revenue = sum(float(payment.amount) for payment in all_payments if payment.paid)
        
        stats = {
            'total_users': total_users,
            'active_subscriptions': active_subscriptions,
            'total_payments': total_payments,
            'total_revenue': round(total_revenue, 2)
        }
        
        return jsonify(stats)
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users', methods=['GET'])
def get_users():
    """Get list of all users for admin panel"""
    try:
        from models.user import User
        
        all_users = User.get_all_users()
        users_list = []
        
        for user in all_users:
            user_info = {
                'id': user.id,
                'username': user.username,
                'subscription_status': 'active' if user.is_subscription_active() else 'inactive',
                'subscription_end_date': user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                'trial_used': user.trial_used,
                'created_at': user.created_at.isoformat()
            }
            users_list.append(user_info)
        
        return jsonify({'users': users_list})
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payments', methods=['GET'])
def get_payments():
    """Get list of all payments for admin panel, or payments for specific user"""
    try:
        from models.payment import Payment

        # Check if user_id is provided (for user-specific payments)
        user_id = request.args.get('user_id')
        limit = request.args.get('limit', 10, type=int)

        if user_id:
            # Get payments for specific user
            user_payments = Payment.get_payments_by_user(int(user_id))
            # Sort by created_at descending and limit
            user_payments = sorted(user_payments, key=lambda p: p.created_at, reverse=True)[:limit]
            payments_list = []

            for payment in user_payments:
                payment_info = {
                    'id': payment.id,
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'description': payment.description,
                    'user_id': payment.user_id,
                    'status': payment.status,
                    'paid': payment.paid,
                    'created_at': payment.created_at.isoformat(),
                    'test': payment.test
                }
                payments_list.append(payment_info)

            return jsonify({'payments': payments_list})
        else:
            # Get all payments (admin)
            all_payments = Payment.get_recent_payments(limit=limit)
            payments_list = []

            for payment in all_payments:
                payment_info = {
                    'id': payment.id,
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'description': payment.description,
                    'user_id': payment.user_id,
                    'status': payment.status,
                    'paid': payment.paid,
                    'created_at': payment.created_at.isoformat(),
                    'test': payment.test
                }
                payments_list.append(payment_info)

            return jsonify({'payments': payments_list})
    except Exception as e:
        print(f"Error getting payments: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """Get list of all users with detailed information for admin panel"""
    try:
        from models.user import User
        from models.payment import Payment
        from database.db_config import db
        from datetime import datetime
        
        all_users = User.get_all_users()
        users_list = []
        
        for user in all_users:
            # Get user's payments
            user_payments = Payment.get_payments_by_user(user.id)
            total_spent = sum(float(p.amount) for p in user_payments if p.paid)
            payment_count = len(user_payments)
            
            user_info = {
                'id': user.id,
                'username': user.username,
                'subscription_status': 'active' if user.is_subscription_active() else 'inactive',
                'subscription_end_date': user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                'trial_used': user.trial_used,
                'created_at': user.created_at.isoformat(),
                'total_spent': round(total_spent, 2),
                'payment_count': payment_count,
                'connection_history': getattr(user, 'connection_history', [])
            }
            users_list.append(user_info)
        
        return jsonify({'users': users_list})
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_user_admin(user_id):
    """Update user information through admin panel"""
    try:
        from models.user import User
        from database.db_config import db
        
        data = request.get_json()
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update user fields if provided
        if 'subscription_end_date' in data:
            from datetime import datetime
            import dateutil.parser
            try:
                new_date = dateutil.parser.parse(data['subscription_end_date'])
                user.subscription_end_date = new_date
            except:
                return jsonify({'error': 'Invalid date format'}), 400
        
        if 'trial_used' in data:
            user.trial_used = bool(data['trial_used'])
        
        if 'username' in data:
            user.username = data['username']
        
        db.session.commit()
        
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
def block_user_admin(user_id):
    """Block a user account through admin panel"""
    try:
        from models.user import User
        from database.db_config import db
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # In a real system, you might want to add a 'blocked' field to the User model
        # For now, we'll just return a success message
        return jsonify({'message': f'User {user_id} blocked successfully'})
    except Exception as e:
        print(f"Error blocking user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user_admin(user_id):
    """Unblock a user account through admin panel"""
    try:
        from models.user import User
        from database.db_config import db
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'message': f'User {user_id} unblocked successfully'})
    except Exception as e:
        print(f"Error unblocking user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/payments', methods=['POST'])
def create_manual_payment():
    """Create a manual payment for a user (e.g., for refunds or adjustments)"""
    try:
        from models.payment import Payment as PaymentModel
        from models.user import User
        from database.db_config import db
        import uuid
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'amount', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Verify user exists
        user = User.get_by_id(data['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create manual payment
        payment_data = {
            'id': f"manual_{uuid.uuid4().hex[:16]}",
            'amount': data['amount'],
            'currency': data.get('currency', 'RUB'),
            'description': data['description'],
            'user_id': data['user_id'],
            'status': data.get('status', 'succeeded'),  # Default to succeeded for manual payments
        }
        
        payment = PaymentModel.create(payment_data)
        
        return jsonify({
            'message': 'Manual payment created successfully',
            'payment': {
                'id': payment.id,
                'amount': float(payment.amount),
                'status': payment.status
            }
        })
    except Exception as e:
        print(f"Error creating manual payment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/system', methods=['GET'])
def get_system_info():
    """Get system information and statistics for admin panel"""
    try:
        import psutil
        import platform
        from datetime import datetime
        
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')
        
        # Get basic system info
        system_info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': platform.node(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': cpu_percent,
            'memory_total': memory.total,
            'memory_available': memory.available,
            'memory_percent': memory.percent,
            'disk_total': disk_usage.total,
            'disk_used': disk_usage.used,
            'disk_percent': (disk_usage.used / disk_usage.total) * 100,
            'server_time': datetime.now().isoformat()
        }
        
        return jsonify({'system_info': system_info})
    except Exception as e:
        print(f"Error getting system info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/vpn/servers', methods=['GET'])
def get_vpn_servers():
    """Get VPN server information and status"""
    try:
        # This would connect to your VPN server management system
        # For now, returning mock data
        vpn_servers = [
            {
                'id': 1,
                'name': 'Primary Server',
                'ip_address': '10.0.0.1',
                'port': 51820,
                'protocol': 'WireGuard',
                'status': 'online',
                'connected_users': 5,
                'bandwidth': '1Gbps',
                'location': 'Frankfurt, DE',
                'last_updated': '2026-02-09T09:30:00Z'
            },
            {
                'id': 2,
                'name': 'Backup Server',
                'ip_address': '10.0.0.2',
                'port': 51820,
                'protocol': 'WireGuard',
                'status': 'online',
                'connected_users': 2,
                'bandwidth': '1Gbps',
                'location': 'Amsterdam, NL',
                'last_updated': '2026-02-09T09:30:00Z'
            }
        ]
        
        return jsonify({'servers': vpn_servers})
    except Exception as e:
        print(f"Error getting VPN servers: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/vpn/configs', methods=['GET'])
def get_vpn_configs():
    """Get VPN configurations for users"""
    try:
        # This would return VPN configurations for users
        # For now, returning mock data
        vpn_configs = [
            {
                'user_id': 699469085,
                'username': 'test_user',
                'config_name': 'user_config_699469085.conf',
                'created_at': '2026-02-08T10:00:00Z',
                'last_used': '2026-02-09T08:00:00Z',
                'enabled': True
            }
        ]

        return jsonify({'configs': vpn_configs})
    except Exception as e:
        print(f"Error getting VPN configs: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =========================================================
# Marzban (V2Ray/Trojan/Reality) API endpoints
# =========================================================

@routes_bp.route('/api/marzban/create', methods=['POST'])
def create_marzban_user_route():
    """Создание пользователя в Marzban (V2Ray/Trojan)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        tariff = data.get('tariff', 'standard')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        logger.info(f"🔧 Создание Marzban пользователя: user_id={user_id}, tariff={tariff}")
        result = vpn_service.create_marzban_user(user_id, tariff)
        
        if result.get("status") == "success":
            logger.info(f"✅ Успешно создано: {result.get('username')}")
        else:
            logger.warning(f"⚠️ Ошибка: {result.get('message')}")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in create_marzban_user_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/subscription/<int:user_id>', methods=['GET'])
def get_marzban_subscription_route(user_id):
    """Получение подписки пользователя из Marzban"""
    try:
        result = vpn_service.get_marzban_subscription(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_marzban_subscription_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/remove/<int:user_id>', methods=['POST'])
def remove_marzban_user_route(user_id):
    """Удаление пользователя из Marzban"""
    try:
        result = vpn_service.remove_marzban_user(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in remove_marzban_user_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Удаление пользователя из БД (сначала платежи, потом пользователь)"""
    try:
        from database.db_config import db
        from database.models.payment_model import Payment as PaymentModel
        from database.models.user_model import User as UserModel
        
        # Сначала удаляем все платежи пользователя
        payments = PaymentModel.query.filter_by(user_id=user_id).all()
        payments_count = len(payments)
        for payment in payments:
            db.session.delete(payment)
        
        # Теперь удаляем пользователя
        user = UserModel.query.filter_by(id=user_id).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            logger.info(f"✅ Пользователь {user_id} удалён (включая {payments_count} платежей)")
            return jsonify({
                'status': 'success',
                'message': f'Пользователь {user_id} удалён',
                'deleted_payments': payments_count
            })
        else:
            return jsonify({'error': 'User not found'}), 404
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error deleting user {user_id}: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/extend/<int:user_id>', methods=['POST'])
def extend_marzban_user_route(user_id):
    """Продление подписки пользователя в Marzban"""
    try:
        data = request.get_json()
        days = data.get('days', 30)
        result = vpn_service.extend_marzban_user(user_id, days)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in extend_marzban_user_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/webhook', methods=['POST'])
def marzban_webhook():
    """Webhook для синхронизации изменений из Marzban"""
    try:
        data = request.get_json()
        
        # Тип события (user_created, user_updated, user_deleted)
        event_type = data.get('event_type', 'user_updated')
        username = data.get('username')
        
        if not username or not username.startswith('user_'):
            return jsonify({'status': 'ignored'})

        user_id = int(username.replace('user_', ''))

        # Получаем актуальные данные из Marzban (используем глобальный vpn_service)
        marzban_user = vpn_service.marzban.get_user(username)
        
        if marzban_user.get('status') == 'success':
            user_data = marzban_user.get('data', {})
            expire_timestamp = user_data.get('expire')
            
            # Обновляем в PostgreSQL
            from database.db_config import db
            from database.models.user_model import User as UserModel
            
            user = UserModel.query.filter_by(id=user_id).first()
            if user:
                if expire_timestamp and expire_timestamp > 0:
                    user.subscription_end_date = datetime.fromtimestamp(expire_timestamp)
                else:
                    user.subscription_end_date = None
                
                db.session.commit()
                logger.info(f"✅ Синхронизировано из Marzban: {username}")
            else:
                logger.warning(f"⏭️ Пользователь не найден в БД: {username}")
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        logger.error(f"Error in marzban_webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes_bp.route('/api/sync/marzban', methods=['POST'])
def sync_marzban_endpoint():
    """Endpoint для ручной синхронизации Marzban → PostgreSQL"""
    try:
        from database.db_config import db
        from database.models.user_model import User as UserModel
        from datetime import datetime
        
        # Получить всех пользователей из БД
        users = UserModel.query.all()
        
        updated = 0
        for user in users:
            username = f"user_{user.id}"
            
            # Проверить в Marzban через vpn_service (экземпляр)
            marzban_user = vpn_service.marzban.get_user(username)
            
            if marzban_user.get('status') == 'success':
                user_data = marzban_user.get('data', {})
                expire_timestamp = user_data.get('expire')
                
                # Обновить если отличается
                if expire_timestamp and expire_timestamp > 0:
                    new_date = datetime.fromtimestamp(expire_timestamp)
                    if user.subscription_end_date != new_date:
                        user.subscription_end_date = new_date
                        updated += 1
                        logger.info(f"🔄 Синхронизировано: {username} → {new_date}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'updated': updated,
            'message': f'Синхронизировано {updated} пользователей'
        })
    
    except Exception as e:
        logger.error(f"Error in sync_marzban_endpoint: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes_bp.route('/api/vpn/choose', methods=['GET'])
def choose_vpn_type():
    """Выбор типа VPN (WireGuard или V2Ray)"""
    try:
        return jsonify({
            'status': 'success',
            'vpn_types': [
                {
                    'type': 'v2ray',
                    'name': 'V2Ray (VLESS/Trojan)',
                    'description': 'Лучше обходит блокировки',
                    'protocols': ['VLESS Reality', 'Trojan TLS']
                },
                {
                    'type': 'wireguard',
                    'name': 'WireGuard',
                    'description': 'Высокая скорость',
                    'protocols': ['WireGuard']
                }
            ]
        })
    except Exception as e:
        logger.error(f"Error in choose_vpn_type: {e}")
        return jsonify({'error': str(e)}), 500


# =========================================================
# Testers Management (6 free unlimited keys)
# =========================================================

@routes_bp.route('/api/testers', methods=['GET'])
def get_testers():
    """Get list of all testers"""
    try:
        from models.user import User
        
        all_users = User.get_all_users()
        testers_list = [user.to_dict() for user in all_users if user.is_tester]
        
        return jsonify({
            'status': 'success',
            'testers': testers_list,
            'count': len(testers_list)
        })
    except Exception as e:
        print(f"Error getting testers: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/testers/add', methods=['POST'])
def add_tester():
    """Add a user to testers list (unlimited access)"""
    try:
        from models.user import User
        from database.db_config import db
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if already a tester
        if user.is_tester:
            return jsonify({'message': 'User is already a tester'})
        
        # Mark as tester
        user.is_tester = True
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'User {user_id} added to testers'
        })
    except Exception as e:
        print(f"Error adding tester: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/testers/remove', methods=['POST'])
def remove_tester():
    """Remove a user from testers list"""
    try:
        from models.user import User
        from database.db_config import db
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Remove tester status
        user.is_tester = False
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'User {user_id} removed from testers'
        })
    except Exception as e:
        print(f"Error removing tester: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/testers/check/<int:user_id>', methods=['GET'])
def check_tester(user_id):
    """Check if user is a tester"""
    try:
        from models.user import User
        
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'is_tester': user.is_tester
        })
    except Exception as e:
        print(f"Error checking tester: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =========================================================
# Payment success/error pages
# =========================================================

@routes_bp.route('/payment-success', methods=['GET'])
def payment_success():
    """Page shown after successful payment return from YooKassa"""
    from flask import render_template

    # Get payment info from query params
    payment_id = request.args.get('payment_id')
    amount = request.args.get('amount')
    days = request.args.get('days')

    return render_template('payment_success.html',
                          payment_id=payment_id,
                          amount=amount,
                          days=days)


@routes_bp.route('/payment-failed', methods=['GET'])
def payment_failed():
    """Page shown after failed payment return from YooKassa"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ошибка оплаты</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background-color: #ffebee;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }
            .error-icon {
                font-size: 60px;
                color: #f44336;
                margin-bottom: 20px;
            }
            button {
                background-color: #f44336;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 20px;
            }
            button:hover {
                background-color: #d32f2f;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">✗</div>
            <h1>Ошибка оплаты</h1>
            <p>К сожалению, произошла ошибка при обработке платежа.</p>
            <p>Пожалуйста, попробуйте снова или свяжитесь с поддержкой.</p>
            <button onclick="returnToBot()">Вернуться в бот</button>
        </div>

        <script>
            // Initialize Telegram WebApp
            const tg = window.Telegram.WebApp;
            tg.ready();
            
            function returnToBot() {
                // Close the web app to return to the bot
                tg.close();
            }
        </script>
    </body>
    </html>
    '''
