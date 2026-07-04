# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_featured = fields.Boolean(string='Featured on Website', default=False)
    is_kenya_stock = fields.Boolean(string='Kenya Stock', default=False)
    is_discounted = fields.Boolean(string='Is Discounted', compute='_compute_is_discounted', store=True)

    @api.depends('fob_price', 'proforma_fob_price')
    def _compute_is_discounted(self):
        for rec in self:
            # Safe boundary checks for cases where fields might be undefined or None
            fob = rec.fob_price or 0
            proforma = rec.proforma_fob_price or 0
            rec.is_discounted = proforma > fob
