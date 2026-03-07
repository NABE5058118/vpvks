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
    db.init_app(app)
