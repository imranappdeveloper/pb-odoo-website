# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PbStockWishlist(models.Model):
    _name = 'pb.stock.wishlist'
    _description = 'Pacific Boeki Stock Wishlist'
    _order = 'id desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        help='Customer who saved this vehicle to their wishlist',
    )
    stock_ref = fields.Char(
        string='Stock Reference',
        required=True,
        index=True,
        help='Stock vehicle ID or reference code',
    )
    stock_type = fields.Selection(
        [
            ('sales_stock', 'Sales Stock'),
            ('one_price', 'One Price'),
            ('auction', 'Auction'),
        ],
        string='Stock Type',
        default='sales_stock',
        required=True,
    )

    _sql_constraints = [
        (
            'unique_partner_stock',
            'unique(partner_id, stock_ref)',
            'This vehicle is already saved to your wishlist.'
        )
    ]
