"""User model for PostgreSQL database"""

from database.db_config import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.BigInteger, primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(100), nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_charge_date = db.Column(db.Date, nullable=True)
    balance = db.Column(db.Integer, default=0)
    is_tester = db.Column(db.Boolean, default=False)
    last_expiration_reminder_sent = db.Column(db.Date, nullable=True)
    data_limit_gb = db.Column(db.Float, nullable=True)
    used_traffic_gb = db.Column(db.Float, default=0.0)
    subscription_url = db.Column(db.Text, nullable=True)
    vpn_key_generated = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index('idx_users_deleted_at', 'deleted_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'subscription_end_date': self.subscription_end_date.isoformat() if self.subscription_end_date else None,
            'created_at': self.created_at.isoformat(),
            'last_charge_date': self.last_charge_date.isoformat() if self.last_charge_date else None,
            'balance': self.balance,
            'is_tester': self.is_tester,
            'last_expiration_reminder_sent': self.last_expiration_reminder_sent.isoformat() if self.last_expiration_reminder_sent else None,
            'data_limit_gb': self.data_limit_gb,
            'used_traffic_gb': self.used_traffic_gb,
            'subscription_url': self.subscription_url,
            'vpn_key_generated': self.vpn_key_generated,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None
        }

    def is_subscription_active(self):
        if self.is_tester:
            return True
        if self.subscription_end_date is None:
            return False
        return self.subscription_end_date >= datetime.utcnow()

    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.deleted_at = None

    def is_deleted(self):
        return self.deleted_at is not None

    @classmethod
    def get_active_users(cls):
        return cls.query.filter_by(deleted_at=None).all()

    @classmethod
    def get_deleted_users(cls):
        return cls.query.filter(cls.deleted_at.isnot(None)).all()
