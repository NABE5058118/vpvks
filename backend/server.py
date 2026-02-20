from flask import Flask, jsonify, render_template, request
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

import sys
import os

# Add the current directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize database
from database.db_config import init_db, db
init_db(app)

from routes import routes_bp

# Register blueprints
app.register_blueprint(routes_bp)

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({"status": "Backend server is running", "service": "VPN Bot API"})

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({"status": "API is operational", "version": "1.0.0"})

@app.route('/miniapp')
def mini_app():
    """Mini App endpoint"""
    return render_template('miniapp.html')

@app.route('/payment-options')
def payment_options():
    """Payment options page for Mini App"""
    return render_template('payment_options.html')


@app.route('/payment-options-ios')
def payment_options_ios():
    """Payment options page for iOS devices"""
    # Default values
    amount = request.args.get('amount', '0')
    currency = request.args.get('currency', 'RUB')
    payment_id = request.args.get('payment_id', '')
    
    return render_template('payment_ios.html', amount=amount, currency=currency, payment_id=payment_id)

@app.route('/payment-redirect/<payment_id>')
def payment_redirect(payment_id):
    """Payment redirect page that opens payment in new tab/window"""
    from models.payment import Payment as PaymentModel
    
    payment = PaymentModel.get_by_id(payment_id)
    if not payment:
        from flask import jsonify
        return jsonify({'error': 'Payment not found'}), 404
    
    # Get confirmation URL from stored YooKassa response or create a mock one for testing
    confirmation_url = ''
    if payment.yookassa_response and isinstance(payment.yookassa_response, dict):
        confirmation_url = payment.yookassa_response.get('confirmation', {}).get('confirmation_url', '')
    
    # If no confirmation URL found and we're in test mode, create a mock URL
    if not confirmation_url:
        confirmation_url = f"https://yoomoney.ru/checkout/payments/v2/contract?orderId={payment_id}"
    
    return render_template('payment_redirect.html', 
                          payment_url=confirmation_url,
                          amount=float(payment.amount),
                          currency=payment.currency)


@app.route('/mock-payment/<payment_id>')
def mock_payment(payment_id):
    """Mock payment page for testing purposes"""
    return render_template('mock_payment.html', payment_id=payment_id)

# Create tables when the app starts
with app.app_context():
    # Check if we're using SQLite (file-based database)
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"Database URI: {db_uri}")
    if db_uri.startswith('sqlite:///'):
        # For SQLite, create the tables
        db.create_all()
        print("SQLite database tables created successfully!")
    else:
        # For PostgreSQL, create the tables
        try:
            db.create_all()
            print("PostgreSQL database tables created successfully!")
        except Exception as e:
            print(f"Could not create PostgreSQL tables (this is OK if database is managed externally): {e}")
            print("Assuming PostgreSQL database is already set up and managed separately.")

    # Print info about VPN configs table
    from database.models.vpn_config_model import VPNConfig as VPNConfigModel
    try:
        # Try to query the table to see if it exists
        VPNConfigModel.query.first()
        print("VPN configs table is ready!")
    except Exception as e:
        print(f"VPN configs table may need to be created: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))  # Changed from 5001 to 5002 to avoid conflicts
    app.run(host='0.0.0.0', port=port, debug=False)