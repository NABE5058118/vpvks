"""
User model for PostgreSQL database
"""

from database.db_config import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid


class User(db.Model):
    __tablename__ = 'users'

    # Using BigInteger for user_id to match Telegram user IDs
    id = db.Column(db.BigInteger, primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    trial_used = db.Column(db.Boolean, default=False)
    last_charge_date = db.Column(db.Date, nullable=True)  # Date of last daily charge
    connection_history = db.Column(db.Text, nullable=True)  # Store as JSON string
    balance = db.Column(db.Integer, default=0)  # User balance in stars

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'subscription_end_date': self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'trial_used': self.trial_used,
            'last_charge_date': self.last_charge_date.isoformat() if self.last_charge_date else None,
            'connection_history': self.connection_history,
            'balance': self.balance
        }

    def add_connection_log(self, connected=True):
        """Add a connection log entry"""
        from datetime import datetime
        import json
        
        timestamp = datetime.utcnow()
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'connected': connected
        }

        # Parse existing history or initialize empty list
        history = []
        if self.connection_history:
            try:
                history = json.loads(self.connection_history)
            except:
                history = []
        
        # Add new entry
        history.append(log_entry)

        # Keep only the last 50 connection logs
        if len(history) > 50:
            history = history[-50:]
        
        # Save back to database
        self.connection_history = json.dumps(history)

    def is_subscription_active(self):
        """Check if user's subscription is active"""
        if self.subscription_end_date is None:
            return False
        return self.subscription_end_date >= datetime.utcnow()

