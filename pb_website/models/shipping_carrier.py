# -*- coding: utf-8 -*-

from odoo import models, fields

class ShippingCarrier(models.Model):
    _name = 'shipping.carrier'
    _description = 'Shipping Carrier'
    _order = 'name asc'

    name = fields.Char(string='Carrier Name', required=True)
    code = fields.Char(string='Carrier Code', help='Short code, e.g. KEIHIN, HOEGH, ARMACUP')
    terms_conditions = fields.Text(string='Terms & Restrictions Notes')
    active = fields.Boolean(default=True)
    vessel_ids = fields.One2many('shipping.vessel', 'carrier_id', string='Vessels')
    schedule_ids = fields.One2many('shipping.schedule', 'carrier_id', string='Schedules')
