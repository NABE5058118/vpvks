"""Connection log model for PostgreSQL database"""

from database.db_config import db
from datetime import datetime


class ConnectionLog(db.Model):
    __tablename__ = 'connection_logs'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    connected = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)

    __table_args__ = (
        db.Index('idx_connection_logs_user_id', 'user_id'),
        db.Index('idx_connection_logs_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'connected': self.connected,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

    @classmethod
    def get_by_user_id(cls, user_id, limit=50):
        return cls.query.filter_by(user_id=user_id)\
            .order_by(cls.timestamp.desc())\
            .limit(limit)\
            .all()

    @classmethod
    def add_log(cls, user_id, connected=True, ip_address=None, user_agent=None):
        log = cls(
            user_id=user_id,
            connected=connected,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(log)
        db.session.commit()
        return log

    @classmethod
    def cleanup_old_logs(cls, days=30):
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = cls.query.filter(cls.timestamp < cutoff_date).delete()
        db.session.commit()
        return deleted
