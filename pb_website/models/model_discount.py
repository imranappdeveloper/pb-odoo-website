# -*- coding: utf-8 -*-

from odoo import models, fields

class PbModelDiscount(models.Model):
    _name = 'pb.model.discount'
    _description = 'Model Discount'

    model_name = fields.Char(string='Model Name', required=True, index=True)
    discount_percent = fields.Float(string='Discount Percent (%)', default=0.0, required=True)
    active = fields.Boolean(string='Active', default=True)
