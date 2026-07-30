# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class PbWishlistController(http.Controller):

    @http.route(['/api/v1/website/member/wishlist'], type='json', auth='user', methods=['POST', 'GET'], csrf=False)
    def get_wishlist(self, **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found', 'ids': [], 'wishlist': []}

            wishlist_records = request.env['pb.stock.wishlist'].sudo().search([('partner_id', '=', partner.id)])
            wishlist_data = [
                {
                    'id': rec.id,
                    'stock_id': rec.stock_ref,
                    'stock_ref': rec.stock_ref,
                    'stock_type': rec.stock_type,
                    'create_date': fields_to_string(rec.create_date),
                }
                for rec in wishlist_records
            ]
            ids = [rec.stock_ref for rec in wishlist_records]

            return {
                'status': 'success',
                'ids': ids,
                'wishlist': wishlist_data,
            }
        except Exception as e:
            _logger.exception("Error in get_wishlist")
            return {'status': 'error', 'message': str(e), 'ids': [], 'wishlist': []}

    @http.route(['/api/v1/website/member/wishlist/add'], type='json', auth='user', methods=['POST'], csrf=False)
    def add_to_wishlist(self, stock_id=None, stock_ref=None, vehicle_id=None, stock_type='sales_stock', **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found'}

            s_id = str(stock_id or stock_ref or vehicle_id or '').strip()
            if not s_id:
                return {'status': 'error', 'message': 'Missing stock_id parameter'}

            existing = request.env['pb.stock.wishlist'].sudo().search([
                ('partner_id', '=', partner.id),
                ('stock_ref', '=', s_id)
            ], limit=1)

            if not existing:
                request.env['pb.stock.wishlist'].sudo().create({
                    'partner_id': partner.id,
                    'stock_ref': s_id,
                    'stock_type': stock_type or 'sales_stock',
                })

            return self.get_wishlist()
        except Exception as e:
            _logger.exception("Error in add_to_wishlist")
            return {'status': 'error', 'message': str(e)}

    @http.route(['/api/v1/website/member/wishlist/remove'], type='json', auth='user', methods=['POST'], csrf=False)
    def remove_from_wishlist(self, stock_id=None, stock_ref=None, vehicle_id=None, **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found'}

            s_id = str(stock_id or stock_ref or vehicle_id or '').strip()
            if not s_id:
                return {'status': 'error', 'message': 'Missing stock_id parameter'}

            existing = request.env['pb.stock.wishlist'].sudo().search([
                ('partner_id', '=', partner.id),
                ('stock_ref', '=', s_id)
            ])

            if existing:
                existing.sudo().unlink()

            return self.get_wishlist()
        except Exception as e:
            _logger.exception("Error in remove_from_wishlist")
            return {'status': 'error', 'message': str(e)}

    @http.route(['/api/v1/website/member/wishlist/sync'], type='json', auth='user', methods=['POST'], csrf=False)
    def sync_wishlist(self, stock_ids=None, **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found'}

            s_ids = stock_ids if isinstance(stock_ids, list) else []
            for s_id in s_ids:
                str_id = str(s_id).strip()
                if not str_id:
                    continue
                existing = request.env['pb.stock.wishlist'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('stock_ref', '=', str_id)
                ], limit=1)
                if not existing:
                    request.env['pb.stock.wishlist'].sudo().create({
                        'partner_id': partner.id,
                        'stock_ref': str_id,
                        'stock_type': 'sales_stock',
                    })

            return self.get_wishlist()
        except Exception as e:
            _logger.exception("Error in sync_wishlist")
            return {'status': 'error', 'message': str(e)}

def fields_to_string(val):
    if not val:
        return ''
    return str(val)

