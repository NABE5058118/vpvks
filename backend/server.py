from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
from dotenv import load_dotenv
import secrets

load_dotenv()

app = Flask(__name__, template_folder='templates')

secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    print("WARNING: SECRET_KEY not set. Using auto-generated key (not for production!)")
    secret_key = secrets.token_hex(32)
app.config['SECRET_KEY'] = secret_key

# Доверенные хосты для Flask (защита от подделки Host header)
trusted_hosts = os.getenv('TRUSTED_HOSTS', 'localhost,127.0.0.1,vpn_backend:8080,backend:8080')
app.config['TRUSTED_HOSTS'] = [h.strip() for h in trusted_hosts.split(',')]

# CORS для Docker-сети
allowed_origins = os.getenv('CORS_ORIGINS', 'http://backend:8080,http://bot:8080,http://localhost:8080')
CORS(app, resources={r"/api/*": {"origins": [o.strip() for o in allowed_origins.split(',')]}})

# Rate Limiting
from utils.limiter import limiter
limiter.init_app(app)

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.db_config import init_db, db
init_db(app)

from routes import routes_bp
app.register_blueprint(routes_bp)

@app.route('/')
def index():
    return jsonify({"status": "Backend server is running", "service": "VPN Bot API"})

@app.route('/api/status')
def api_status():
    return jsonify({"status": "API is operational", "version": "1.0.0"})

@app.route('/miniapp')
def mini_app():
    return render_template('miniapp.html')

@app.route('/payment-options')
def payment_options():
    return render_template('payment_options.html')

@app.route('/payment-options-ios')
def payment_options_ios():
    amount = request.args.get('amount', '0')
    currency = request.args.get('currency', 'RUB')
    payment_id = request.args.get('payment_id', '')
    return render_template('payment_ios.html', amount=amount, currency=currency, payment_id=payment_id)

@app.route('/payment-success', methods=['GET'])
def payment_success():
    payment_id = request.args.get('payment_id')
    return render_template('payment_success.html', payment_id=payment_id)

@app.route('/payment-redirect/<payment_id>')
def payment_redirect(payment_id):
    from models.payment import Payment as PaymentModel

    payment = PaymentModel.get_by_id(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    confirmation_url = payment.confirmation_url or ''
    if not confirmation_url:
        confirmation_url = f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}"

    return render_template('payment_redirect.html',
                          payment_url=confirmation_url,
                          amount=float(payment.amount),
                          currency=payment.currency)

@app.route('/mock-payment/<payment_id>')
def mock_payment(payment_id):
    return render_template('mock_payment.html', payment_id=payment_id)

with app.app_context():
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"Database URI: {db_uri}")
    db.create_all()
    print("Database tables created successfully!")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
