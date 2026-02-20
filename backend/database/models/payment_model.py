"""
Payment model for PostgreSQL database
"""

from database.db_config import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(100), primary_key=True, unique=True, nullable=False)  # YooKassa payment ID
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Amount with 2 decimal places
    currency = db.Column(db.String(3), default='RUB')  # Currency code
    description = db.Column(db.Text, nullable=True)  # Payment description
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)  # Link to user
    status = db.Column(db.String(20), default='pending')  # Payment status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid = db.Column(db.Boolean, default=False)  # Whether payment was successful
    yookassa_response = db.Column(db.JSON, nullable=True)  # Full response from YooKassa
    test = db.Column(db.Boolean, default=False)  # Whether this is a test payment
    stars_amount = db.Column(db.Integer, default=0)  # Number of stars added to user balance

    def to_dict(self):
        """Convert payment object to dictionary"""
        return {
            'id': self.id,
            'amount': float(self.amount),
            'currency': self.currency,
            'description': self.description,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'paid': self.paid,
            'test': self.test,
            'stars_amount': self.stars_amount
        }

    def update_status(self, new_status):
        """Update payment status"""
        self.status = new_status
        self.updated_at = datetime.utcnow()

        if new_status == 'succeeded':
            self.paid = True