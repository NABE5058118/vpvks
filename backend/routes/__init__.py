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
from models.vpn_config import VPNConfig
from database.models.vpn_config_model import VPNConfig as VPNConfigModel

import logging
import base64

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


@routes_bp.route('/api/wireguard/config/<int:user_id>', methods=['GET'])
def get_wireguard_config(user_id):
    """Get WireGuard configuration file for user"""
    try:
        # Check if user exists
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user has active subscription
        if not user.is_subscription_active():
            return jsonify({
                'error': 'Subscription is not active',
                'message': 'Please purchase a subscription to download VPN config'
            }), 403

        # Get or generate user's VPN config
        vpn_config = VPNConfig.get_by_user_id(user_id)

        if not vpn_config:
            # Generate new config
            config_result = vpn_service._get_or_create_user_config(user_id)
            if not config_result:
                return jsonify({'error': 'Failed to generate VPN config'}), 500

            vpn_config = VPNConfigModel.get_by_user_id(user_id)

        if not vpn_config:
            return jsonify({'error': 'VPN config not found'}), 500

        # Generate WireGuard config content
        server_public_key = os.getenv('WG_SERVER_PUBLIC_KEY')
        server_ip = os.getenv('WG_SERVER_IP', '10.0.0.1')
        server_port = os.getenv('WG_PORT', '51820')
        dns_server = os.getenv('WG_DNS', '8.8.8.8')

        # Generate client IP based on user_id
        client_ip = f"10.0.0.{(user_id % 250) + 2}/32"

        config_content = f"""[Interface]
PrivateKey = {vpn_config.private_key}
Address = {client_ip}
DNS = {dns_server}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

        # Return as file download
        from flask import make_response
        response = make_response(config_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=vpn_config_{user_id}.conf'
        return response

    except Exception as e:
        logger.error(f"Error getting WireGuard config: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/wireguard/qr/<int:user_id>', methods=['GET'])
def get_wireguard_qr(user_id):
    """Get QR code with WireGuard configuration for user"""
    try:
        # Check if user exists
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check if user has active subscription
        if not user.is_subscription_active():
            return jsonify({
                'error': 'Subscription is not active',
                'message': 'Please purchase a subscription to download VPN config'
            }), 403

        # Get or generate user's VPN config
        vpn_config = VPNConfig.get_by_user_id(user_id)

        if not vpn_config:
            # Generate new config
            config_result = vpn_service._get_or_create_user_config(user_id)
            if not config_result:
                logger.error("Failed to generate VPN config: config_result is None")
                return jsonify({'error': 'Failed to generate VPN config'}), 500

            vpn_config = VPNConfigModel.get_by_user_id(user_id)

        if not vpn_config:
            logger.error("VPN config not found after generation")
            return jsonify({'error': 'VPN config not found'}), 500

        # Generate WireGuard config content for QR code
        server_public_key = os.getenv('WG_SERVER_PUBLIC_KEY')
        server_ip = os.getenv('WG_SERVER_IP', '10.0.0.1')
        server_port = os.getenv('WG_PORT', '51820')
        dns_server = os.getenv('WG_DNS', '8.8.8.8')

        # Generate client IP based on user_id
        client_ip = f"10.0.0.{(user_id % 250) + 2}/32"

        # WireGuard QR code format
        wg_config = f"""[Interface]
PrivateKey = {vpn_config.private_key}
Address = {client_ip}
DNS = {dns_server}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

        # Encode config as base64 for QR code
        import base64
        config_base64 = base64.b64encode(wg_config.encode('utf-8')).decode('utf-8')

        # Return config data for QR code generation on frontend
        response = jsonify({
            'status': 'success',
            'user_id': user_id,
            'config_base64': config_base64,
            'config_text': wg_config
        })
        
        # Ensure correct content type
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        return response

    except Exception as e:
        logger.error(f"Error getting WireGuard QR: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/wireguard/status/<int:user_id>', methods=['GET'])
def get_wireguard_status(user_id):
    """Get WireGuard connection status for user"""
    try:
        # Check if user exists
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({
                'user_id': user_id,
                'has_config': False,
                'subscription_active': False,
                'error': 'User not found'
            }), 404

        # Check subscription status
        subscription_active = user.is_subscription_active()

        # Check if user has VPN config
        vpn_config = VPNConfig.get_by_user_id(user_id)
        has_config = vpn_config is not None

        # Get connection info
        connection_info = None
        if vpn_config:
            connection_info = {
                'has_config': True,
                'created_at': vpn_config.created_at.isoformat() if vpn_config.created_at else None,
                'last_connected': vpn_config.last_connected.isoformat() if vpn_config.last_connected else None,
                'connection_count': vpn_config.connection_count,
                'is_active': vpn_config.is_active
            }

        return jsonify({
            'user_id': user_id,
            'subscription_active': subscription_active,
            'has_config': has_config,
            'connection_info': connection_info
        })

    except Exception as e:
        logger.error(f"Error getting WireGuard status: {str(e)}")
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

        # If iOS device, modify the response to include iOS-specific payment URL
        if is_ios and result.get('status') == 'success' and result.get('payment'):
            payment_data = result['payment']
            # For iOS, we might want to return a different confirmation URL
            # that points to the iOS-specific payment page
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
    """Get list of all payments for admin panel"""
    try:
        from models.payment import Payment
        
        all_payments = Payment.get_recent_payments(limit=100)  # Last 100 payments
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
        
        result = vpn_service.create_marzban_user(user_id, tariff)
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
# Payment success/error pages
# =========================================================

@routes_bp.route('/payment-success', methods=['GET'])
def payment_success():
    """Page shown after successful payment return from YooKassa"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Оплата прошла успешно!</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background-color: #f0f8ff;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }
            .success-icon {
                font-size: 60px;
                color: #4CAF50;
                margin-bottom: 20px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin-top: 20px;
            }
            button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✓</div>
            <h1>Оплата прошла успешно!</h1>
            <p>Ваша подписка активирована. Спасибо за покупку!</p>
            <p>Вернитесь в бота, чтобы проверить статус подписки.</p>
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
            
            // Auto-close after 5 seconds if in Telegram Web App
            setTimeout(function() {
                if(tg.isClosingConfirmationEnabled) {
                    tg.enableClosingConfirmation();
                }
            }, 5000);
        </script>
    </body>
    </html>
    '''


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
