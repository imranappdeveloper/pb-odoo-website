# -*- coding: utf-8 -*-

from odoo import models, fields

class PbFreightRate(models.Model):
    _name = 'pb.freight.rate'
    _description = 'Freight Rate'
    _order = 'country, port'

    country = fields.Char(string='Country', required=True)
    port = fields.Char(string='Port', required=True)
    rate_per_m3 = fields.Float(string='Rate per m³ (USD)', required=True)
