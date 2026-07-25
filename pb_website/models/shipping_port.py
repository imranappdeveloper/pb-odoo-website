# -*- coding: utf-8 -*-

from odoo import models, fields

class ShippingPort(models.Model):
    _name = 'shipping.port'
    _description = 'Shipping Sea Port'
    _order = 'name asc'

    name = fields.Char(string='Port Name', required=True)
    code = fields.Char(string='Port Code (UN/LOCODE)', required=True, help='e.g. JPYOK, JPNGA, TZDAR, KEMBA')
    country_id = fields.Many2one('res.country', string='Country')
    default_role = fields.Selection([
        ('pol', 'Port of Loading (POL)'),
        ('pod', 'Port of Discharge (POD)'),
        ('both', 'Both POL & POD')
    ], string='Default Role', default='both', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Port Code must be unique!')
    ]
