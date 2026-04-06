"""Payment-related marshmallow schemas"""

from marshmallow import Schema, fields, validate


class CreatePaymentSchema(Schema):
    """Schema for POST /api/payment/create — subscription payment"""
    user_id = fields.Integer(required=True, strict=True)
    plan_type = fields.String(load_default='month', validate=validate.OneOf(['month', 'quarter', 'year']))


class CreateTopupPaymentSchema(Schema):
    """Schema for POST /api/payment/topup — balance top-up"""
    user_id = fields.Integer(required=True, strict=True)
    amount = fields.Decimal(required=True, places=2, as_string=False)
    stars_amount = fields.Integer(load_default=0, strict=True)


class ManualPaymentSchema(Schema):
    """Schema for POST /api/admin/payments — manual payment creation"""
    user_id = fields.Integer(required=True, strict=True)
    amount = fields.Decimal(required=True, places=2, as_string=False)
    currency = fields.String(load_default='RUB', validate=validate.Length(equal=3))
    description = fields.String(load_default=None, allow_none=True)
