"""
Database configuration for the VPN bot backend
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create database instance
db = SQLAlchemy()

# Database URL - using PostgreSQL by default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:563478@localhost/vpn_bot_db')

def init_db(app):
    """Initialize database with app"""
    # Use PostgreSQL for production or SQLite for local development
    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:563478@localhost/vpn_bot_db')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)