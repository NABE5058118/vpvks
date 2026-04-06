"""Database configuration"""

from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

if not os.getenv('DATABASE_URL'):
    load_dotenv()

db = SQLAlchemy()

def init_db(app):
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:563478@localhost/vpn_bot_db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Connection pool settings for production
    # По принципу Database Optimizer: "Use Connection Pooling"
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
        }
    }

    db.init_app(app)
