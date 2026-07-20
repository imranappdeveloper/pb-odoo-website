# -*- coding: utf-8 -*-

from odoo import models, fields

class PbBanner(models.Model):
    _name = 'pb.banner'
    _description = 'Website Hero Banner'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    image = fields.Binary(string="Image", required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)
    title = fields.Char(string='Title')
    subtitle = fields.Char(string='Subtitle')
    url = fields.Char(string='URL')
