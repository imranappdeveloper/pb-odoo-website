# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PbRecentlyViewed(models.Model):
    _name = 'pb.recently.viewed'
    _description = 'Pacific Boeki Recently Viewed Vehicles'
    _order = 'viewed_at desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
        help='Customer who viewed this vehicle',
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
    viewed_at = fields.Datetime(
        string='Viewed At',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    _sql_constraints = [
        (
            'unique_partner_stock_recently_viewed',
            'unique(partner_id, stock_ref)',
            'This vehicle is already in recently viewed.'
        )
    ]
