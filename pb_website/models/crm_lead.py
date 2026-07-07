# -*- coding: utf-8 -*-
from odoo import models, fields

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    x_is_whatsapp = fields.Boolean(string='Has WhatsApp', default=False)
    x_is_viber = fields.Boolean(string='Has Viber', default=False)
    x_is_line = fields.Boolean(string='Has LINE', default=False)
