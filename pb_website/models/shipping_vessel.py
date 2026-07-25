# -*- coding: utf-8 -*-

from odoo import models, fields

class ShippingVessel(models.Model):
    _name = 'shipping.vessel'
    _description = 'Shipping Vessel'
    _order = 'name asc'

    name = fields.Char(string='Vessel Name', required=True)
    imo_number = fields.Char(string='IMO Number')
    flag = fields.Char(string='Flag / Country')
    carrier_id = fields.Many2one('shipping.carrier', string='Carrier', ondelete='cascade')
    max_deck_height_cm = fields.Integer(string='Max Deck Height (cm)', help='Maximum height limit, e.g. 165-495 cm')
    max_cargo_weight_kt = fields.Float(string='Max Cargo Weight (K/T)', help='Max weight capacity in K/T')
    notes = fields.Text(string='Vessel Specific Notes')
    active = fields.Boolean(default=True)
