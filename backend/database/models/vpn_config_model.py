"""
VPN Configuration model for PostgreSQL database
Stores WireGuard configurations for users
"""

from database.db_config import db
from datetime import datetime
import uuid


class VPNConfig(db.Model):
    __tablename__ = 'vpn_configs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False, unique=True)
    private_key = db.Column(db.String(100), nullable=False)
    public_key = db.Column(db.String(100), nullable=False)
    server_ip = db.Column(db.String(50), nullable=False)
    server_port = db.Column(db.Integer, nullable=False)
    dns_server = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_connected = db.Column(db.DateTime, nullable=True)
    connection_count = db.Column(db.Integer, default=0)
    config_file_path = db.Column(db.String(255), nullable=True)

    # Relationship with User
    user = db.relationship('User', backref=db.backref('vpn_config', uselist=False))

    def to_dict(self):
        """Convert VPN config object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'private_key': self.private_key,
            'public_key': self.public_key,
            'server_ip': self.server_ip,
            'server_port': self.server_port,
            'dns_server': self.dns_server,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'last_connected': self.last_connected.isoformat() if self.last_connected else None,
            'connection_count': self.connection_count,
            'config_file_path': self.config_file_path
        }

    def activate(self):
        """Activate the VPN configuration"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self):
        """Deactivate the VPN configuration"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def record_connection(self):
        """Record a connection event"""
        self.last_connected = datetime.utcnow()
        self.connection_count += 1
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_by_id(cls, config_id):
        """Get VPN config by ID"""
        return cls.query.filter_by(id=config_id).first()

    @classmethod
    def get_by_user_id(cls, user_id):
        """Get VPN config by user ID"""
        return cls.query.filter_by(user_id=user_id).first()

    @classmethod
    def create(cls, data):
        """Create a new VPN configuration"""
        config_id = data.get('id') or str(uuid.uuid4())

        config = cls(
            id=config_id,
            user_id=data.get('user_id'),
            private_key=data.get('private_key'),
            public_key=data.get('public_key'),
            server_ip=data.get('server_ip'),
            server_port=data.get('server_port'),
            dns_server=data.get('dns_server'),
            config_file_path=data.get('config_file_path')
        )

        db.session.add(config)
        db.session.commit()
        return config

    @classmethod
    def get_all_configs(cls):
        """Get all VPN configurations"""
        return cls.query.all()
