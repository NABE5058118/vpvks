"""User-related marshmallow schemas"""

from marshmallow import Schema, fields, validate


class CreateUserSchema(Schema):
    """Schema for POST /api/users — user registration"""
    id = fields.Integer(required=True, strict=True)
    username = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    first_name = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    last_name = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    subscription_end_date = fields.DateTime(load_default=None, allow_none=True)
    balance = fields.Integer(load_default=0, strict=True)


class UpdateUserAdminSchema(Schema):
    """Schema for PUT /api/admin/users/<id> — admin user update"""
    subscription_end_date = fields.DateTime(load_default=None, allow_none=True)
    username = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))


class CheckFingerprintSchema(Schema):
    """Schema for POST /api/vpn/check-fingerprint"""
    user_id = fields.Integer(required=True, strict=True)
    ip = fields.String(required=True, validate=validate.Length(max=45))
    user_agent = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))


class ConnectVpnSchema(Schema):
    """Schema for POST /api/vpn/connect and /api/vpn/disconnect"""
    user_id = fields.Integer(required=True, strict=True)
