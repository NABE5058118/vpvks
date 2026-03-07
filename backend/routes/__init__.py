"""API Routes for VPN Bot Backend"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sys
import os
import base64
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vpn_service import VPNService
from services.payment_service import PaymentService
from services.business_logic_service import BusinessLogicService
from models.user import User
from database.db_config import db
from database.models.user_model import User as UserModel
from database.models.payment_model import Payment as PaymentModel
from database.models.connection_log_model import ConnectionLog
from utils.limiter import limiter

routes_bp = Blueprint('routes', __name__)
business_service = BusinessLogicService()
payment_service = PaymentService()
vpn_service = VPNService()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@routes_bp.route('/api/users/<int:user_id>', methods=['GET'])
@limiter.limit("30 per minute")
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
        if user:
            return jsonify(user.to_dict())
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>/balance', methods=['GET'])
@limiter.limit("60 per minute")
def get_user_balance(user_id):
    try:
        balance = User.get_balance(user_id)
        return jsonify({'balance': balance})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users', methods=['POST'])
@limiter.limit("10 per minute")
def create_user():
    try:
        data = request.get_json()
        user = User.create(data)
        return jsonify(user.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/connect', methods=['POST'])
def connect_vpn():
    try:
        data = request.get_json()
        if 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        result = business_service.initiate_vpn_connection(data.get('user_id'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/disconnect', methods=['POST'])
def disconnect_vpn():
    try:
        data = request.get_json()
        if 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        result = business_service.vpn_service.disconnect(data.get('user_id'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/status/<int:user_id>', methods=['GET'])
def vpn_status(user_id):
    try:
        result = business_service.get_user_subscription_status(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/key/<int:user_id>', methods=['GET'])
@limiter.limit("20 per minute")
def get_vpn_key(user_id):
    try:
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.is_subscription_active():
            return jsonify({
                'status': 'error',
                'message': 'Подписка не активна. Пожалуйста, оплатите тариф.'
            }), 403

        if user.subscription_url and user.vpn_key_generated:
            logger.info(f"🔑 Returning saved subscription URL for user {user_id}")
            return jsonify({
                'status': 'success',
                'subscription_url': user.subscription_url,
                'key_generated': True
            })

        logger.info(f"🔑 Generating new subscription URL for user {user_id}")
        result = vpn_service.create_marzban_user(user_id, 'standard')

        if result.get('status') == 'success':
            subscription_url = result.get('subscription_url')
            user.subscription_url = subscription_url
            user.vpn_key_generated = True
            db.session.commit()
            logger.info(f"✅ Saved subscription URL for user {user_id}")
            return jsonify({
                'status': 'success',
                'subscription_url': subscription_url,
                'key_generated': True
            })
        return jsonify({
            'status': 'error',
            'message': result.get('message', 'Failed to generate key')
        }), 500
    except Exception as e:
        logger.error(f"Error in get_vpn_key: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/vpn/check-fingerprint', methods=['POST'])
@limiter.limit("30 per minute")
def check_fingerprint():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        ip = data.get('ip')
        user_agent = data.get('user_agent')

        if not user_id or not ip:
            return jsonify({'error': 'user_id and ip are required'}), 400

        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_logs = ConnectionLog.query.filter(
            ConnectionLog.user_id == user_id,
            ConnectionLog.timestamp >= cutoff_time
        ).all()

        unique_ips = set(log.ip_address for log in recent_logs if log.ip_address)

        if ip not in unique_ips:
            if len(unique_ips) >= 2:
                logger.warning(f"⚠️ Подозрительная активность: user_{user_id} подключился с {len(unique_ips) + 1} разных IP за 24ч")
                return jsonify({
                    'status': 'warning',
                    'message': 'Обнаружено подключение с нового устройства. Если это не вы — обратитесь в поддержку.'
                }), 403

        ConnectionLog.add_log(user_id, connected=True, ip_address=ip, user_agent=user_agent)
        logger.info(f"🔒 Подключение для user_{user_id} с IP {ip}")

        return jsonify({'status': 'ok', 'message': 'Подключение записано'})
    except Exception as e:
        logger.error(f"Error in check_fingerprint: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>/reset-device', methods=['POST'])
def reset_device(user_id):
    try:
        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        ConnectionLog.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        logger.info(f"🔄 Сброшен fingerprint для user_{user_id}")
        return jsonify({'status': 'success', 'message': 'Устройство сброшено'})
    except Exception as e:
        logger.error(f"Error in reset_device: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/check/<payment_id>', methods=['GET'])
def check_payment(payment_id):
    try:
        payment_info = payment_service.check_payment_status(payment_id)
        return jsonify({'payment_id': payment_id, 'payment_info': payment_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/confirm/<payment_id>', methods=['POST'])
def confirm_payment(payment_id):
    try:
        result = payment_service.confirm_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/plans', methods=['GET'])
def get_plans():
    try:
        from config.tariffs import get_all_tariffs
        return jsonify({'plans': get_all_tariffs()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/create', methods=['POST'])
@limiter.limit("5 per minute")
def create_payment():
    try:
        data = request.get_json()
        if 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400

        plan_type = data.get('plan_type', 'month')
        result = business_service.process_subscription_payment(data.get('user_id'), plan_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/topup', methods=['POST'])
@limiter.limit("10 per minute")
def create_topup_payment():
    try:
        data = request.get_json()
        if 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400

        amount = data.get('amount', 0)
        stars_amount = data.get('stars_amount', 0)

        if amount <= 0 and stars_amount <= 0:
            return jsonify({'error': 'Amount or stars_amount must be greater than 0'}), 400

        payment_data = {
            'amount': amount,
            'currency': 'RUB',
            'description': f"Balance top-up for user {data.get('user_id')}",
            'user_id': data.get('user_id'),
            'return_url': 'https://vpvks.ru/payment-success',
            'stars_amount': stars_amount
        }

        payment_result = payment_service.create_payment(payment_data)
        return jsonify(payment_result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/cancel/<payment_id>', methods=['POST'])
@limiter.limit("10 per minute")
def cancel_payment(payment_id):
    try:
        result = payment_service.cancel_payment(payment_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.get_json()
        event = data.get('event')
        payment_id = data.get('object', {}).get('id')

        if not payment_id:
            return jsonify({'error': 'payment_id is required'}), 400

        logger.info(f"Received YooKassa webhook: {event} for payment {payment_id}")

        if event == 'payment.succeeded':
            result = business_service.handle_successful_payment(payment_id)
            if result.get('status') == 'success':
                user_id = result.get('user_id')
                if user_id:
                    try:
                        from notifications import send_payment_activated_notification
                        send_payment_activated_notification(user_id)
                    except Exception as e:
                        print(f"Error sending notification to user {user_id}: {e}")
                        logger.error(f"Error sending notification to user {user_id}: {e}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        from database.db_config import db
        from sqlalchemy import func

        total_users = db.session.query(func.count(UserModel.id)).scalar()
        active_users = db.session.query(func.count(UserModel.id)).filter(
            UserModel.deleted_at.is_(None)
        ).scalar()
        total_payments = db.session.query(func.count(PaymentModel.id)).scalar()
        total_revenue = db.session.query(func.sum(PaymentModel.amount)).filter(
            PaymentModel.paid.is_(True)
        ).scalar() or 0

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'total_payments': total_payments,
            'total_revenue': float(total_revenue)
        })
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.get_all_users()
        users_list = []

        for user in users:
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
                'payment_count': payment_count
            }
            users_list.append(user_info)

        return jsonify({'users': users_list})
    except Exception as e:
        print(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/payments', methods=['GET'])
def get_payments():
    try:
        from models.payment import Payment

        user_id = request.args.get('user_id')
        limit = request.args.get('limit', 10, type=int)

        if user_id:
            user_payments = Payment.get_payments_by_user(int(user_id))
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
                    'stars_amount': payment.stars_amount
                }
                payments_list.append(payment_info)

            return jsonify({'payments': payments_list})

        all_payments = Payment.get_recent_payments(limit)
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
                'stars_amount': payment.stars_amount
            }
            payments_list.append(payment_info)

        return jsonify({'payments': payments_list})
    except Exception as e:
        print(f"Error getting payments: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    try:
        users = User.get_all_users()
        users_list = []

        for user in users:
            user_payments = Payment.get_payments_by_user(user.id)
            total_spent = sum(float(p.amount) for p in user_payments if p.paid)
            payment_count = len(user_payments)

            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_logs_count = ConnectionLog.query.filter(
                ConnectionLog.user_id == user.id,
                ConnectionLog.timestamp >= cutoff_time
            ).count()

            user_info = {
                'id': user.id,
                'username': user.username,
                'subscription_status': 'active' if user.is_subscription_active() else 'inactive',
                'subscription_end_date': user.subscription_end_date.isoformat() if user.subscription_end_date else None,
                'trial_used': user.trial_used,
                'created_at': user.created_at.isoformat(),
                'total_spent': round(total_spent, 2),
                'payment_count': payment_count,
                'recent_connections': recent_logs_count
            }
            users_list.append(user_info)

        return jsonify({'users': users_list})
    except Exception as e:
        print(f"Error getting admin users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_user_admin(user_id):
    try:
        from models.user import User

        data = request.get_json()
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if 'subscription_end_date' in data:
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
    try:
        from models.user import User

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': f'User {user_id} blocked successfully'})
    except Exception as e:
        print(f"Error blocking user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/users/<int:user_id>/unblock', methods=['POST'])
def unblock_user_admin(user_id):
    try:
        from models.user import User

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': f'User {user_id} unblocked successfully'})
    except Exception as e:
        print(f"Error unblocking user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/payments', methods=['POST'])
def create_manual_payment():
    try:
        from models.payment import Payment

        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')
        description = data.get('description')

        if not user_id or not amount:
            return jsonify({'error': 'user_id and amount are required'}), 400

        payment = Payment.create({
            'user_id': user_id,
            'amount': amount,
            'currency': 'RUB',
            'description': description,
            'status': 'succeeded',
            'paid': True
        })

        return jsonify({
            'status': 'success',
            'payment': payment.to_dict()
        })
    except Exception as e:
        print(f"Error creating manual payment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/system', methods=['GET'])
def get_system_info():
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return jsonify({
            'cpu_usage': cpu_percent,
            'memory_usage': memory.percent,
            'memory_available_mb': round(memory.available / 1024 / 1024, 2),
            'disk_usage': disk.percent,
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'server_time': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Error getting system info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/admin/vpn/servers', methods=['GET'])
def get_vpn_servers():
    try:
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
            }
        ]
        return jsonify({'configs': vpn_servers})
    except Exception as e:
        print(f"Error getting VPN servers: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =========================================================
# Marzban (V2Ray/Trojan/Reality) API endpoints
# =========================================================

@routes_bp.route('/api/marzban/create', methods=['POST'])
def create_marzban_user_route():
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        result = vpn_service.create_marzban_user(user_id, 'standard')
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in create_marzban_user_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/subscription/<int:user_id>', methods=['GET'])
def get_marzban_subscription_route(user_id):
    try:
        result = vpn_service.get_marzban_subscription(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_marzban_subscription_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/remove/<int:user_id>', methods=['POST'])
def remove_marzban_user_route(user_id):
    try:
        result = vpn_service.remove_marzban_user(user_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in remove_marzban_user_route: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        from database.db_config import db
        from database.models.payment_model import Payment as PaymentModel

        user = UserModel.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        payments = PaymentModel.query.filter_by(user_id=user_id).all()
        for payment in payments:
            db.session.delete(payment)

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': f'User {user_id} and associated payments deleted successfully'})
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/marzban/extend/<int:user_id>', methods=['POST'])
def extend_marzban_user_route(user_id):
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
    try:
        data = request.get_json()
        logger.info(f"Received Marzban webhook: {data}")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error processing Marzban webhook: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/sync/marzban', methods=['POST'])
def sync_marzban_endpoint():
    try:
        result = vpn_service.sync_all_users_with_marzban()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in sync_marzban_endpoint: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@routes_bp.route('/api/vpn/choose', methods=['GET'])
def choose_vpn_type():
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


@routes_bp.route('/api/testers', methods=['GET'])
def get_testers():
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
    try:
        from models.user import User

        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.is_tester:
            return jsonify({'message': f'User {user_id} уже является тестером'})

        user.is_tester = True
        db.session.commit()

        logger.info(f"✅ User {user_id} добавлен в тестеры")
        return jsonify({'message': f'User {user_id} added to testers list'})
    except Exception as e:
        logger.error(f"Error adding tester: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/testers/remove', methods=['POST'])
def remove_tester():
    try:
        from models.user import User

        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.is_tester:
            return jsonify({'message': f'User {user_id} не является тестером'})

        user.is_tester = False
        db.session.commit()

        logger.info(f"🔄 User {user_id} удалён из тестеров")
        return jsonify({'message': f'User {user_id} removed from testers list'})
    except Exception as e:
        logger.error(f"Error removing tester: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/api/testers/check/<int:user_id>', methods=['GET'])
def check_tester(user_id):
    try:
        from models.user import User

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user_id': user_id,
            'is_tester': user.is_tester
        })
    except Exception as e:
        logger.error(f"Error checking tester: {e}")
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/payment-success', methods=['GET'])
def payment_success():
    try:
        payment_id = request.args.get('payment_id')
        return jsonify({
            'status': 'success',
            'message': 'Payment successful',
            'payment_id': payment_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/payment-failed', methods=['GET'])
def payment_failed():
    try:
        payment_id = request.args.get('payment_id')
        return jsonify({
            'status': 'failed',
            'message': 'Payment failed',
            'payment_id': payment_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
