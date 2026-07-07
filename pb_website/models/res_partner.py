# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_is_whatsapp = fields.Boolean(string='Has WhatsApp', default=False)
    x_is_viber = fields.Boolean(string='Has Viber', default=False)
    x_is_line = fields.Boolean(string='Has LINE', default=False)
    x_access_live_auction = fields.Boolean(string='Access Live Auction', default=False)
