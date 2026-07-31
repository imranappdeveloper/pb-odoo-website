# -*- coding: utf-8 -*-

import hashlib
from datetime import timedelta

from odoo import api, fields, models


class PbChassisRevealEntitlement(models.Model):
    _name = 'pb.chassis.reveal.entitlement'
    _description = 'Time-bounded chassis reveal entitlement'
    _order = 'expires_at desc'

    session_hash = fields.Char(required=True, index=True)
    vehicle_model = fields.Selection(
        [('product.template', 'Sales Stock'), ('quick.car', 'One Price')],
        required=True,
        index=True,
    )
    vehicle_ref = fields.Char(required=True, index=True)
    inquiry_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    expires_at = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        (
            'session_vehicle_inquiry_unique',
            'unique(session_hash, vehicle_model, vehicle_ref, inquiry_id)',
            'This inquiry entitlement already exists.',
        ),
    ]

    @api.model
    def hash_session(self, session_id):
        value = str(session_id or '').encode('utf-8')
        return hashlib.sha256(value).hexdigest() if value else ''

    @api.model
    def grant(self, session_id, vehicle_model, vehicle_ref, inquiry, hours=24):
        session_hash = self.hash_session(session_id)
        normalized_ref = str(vehicle_ref or '').strip()
        if not session_hash or not vehicle_model or not normalized_ref or not inquiry:
            return self.browse()
        return self.sudo().create({
            'session_hash': session_hash,
            'vehicle_model': vehicle_model,
            'vehicle_ref': normalized_ref,
            'inquiry_id': inquiry.id,
            'expires_at': fields.Datetime.now() + timedelta(hours=hours),
        })

    @api.model
    def has_active(self, session_id, vehicle_model, vehicle_ref):
        session_hash = self.hash_session(session_id)
        normalized_ref = str(vehicle_ref or '').strip()
        if not session_hash or not vehicle_model or not normalized_ref:
            return False
        return bool(self.sudo().search_count([
            ('session_hash', '=', session_hash),
            ('vehicle_model', '=', vehicle_model),
            ('vehicle_ref', '=', normalized_ref),
            ('expires_at', '>', fields.Datetime.now()),
        ]))
