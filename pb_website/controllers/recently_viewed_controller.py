# -*- coding: utf-8 -*-

import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class PbRecentlyViewedController(http.Controller):

    @http.route(['/api/v1/website/member/recently-viewed'], type='json', auth='user', methods=['POST', 'GET'], csrf=False)
    def get_recently_viewed(self, **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found', 'recently_viewed': []}

            records = request.env['pb.recently.viewed'].sudo().search(
                [('partner_id', '=', partner.id)],
                order='viewed_at desc',
                limit=4
            )
            recently_viewed_data = [
                {
                    'id': rec.id,
                    'stock_id': rec.stock_ref,
                    'stock_ref': rec.stock_ref,
                    'stock_type': rec.stock_type,
                    'viewed_at': fields_to_string(rec.viewed_at),
                }
                for rec in records
            ]

            return {
                'status': 'success',
                'recently_viewed': recently_viewed_data,
            }
        except Exception as e:
            _logger.exception("Error in get_recently_viewed")
            return {'status': 'error', 'message': str(e), 'recently_viewed': []}

    @http.route(['/api/v1/website/member/recently-viewed/add'], type='json', auth='user', methods=['POST'], csrf=False)
    def add_to_recently_viewed(self, stock_id=None, stock_ref=None, stock_type='sales_stock', **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found'}

            s_id = str(stock_id or stock_ref or '').strip()
            if not s_id:
                return {'status': 'error', 'message': 'Missing stock_id parameter'}

            existing = request.env['pb.recently.viewed'].sudo().search([
                ('partner_id', '=', partner.id),
                ('stock_ref', '=', s_id)
            ], limit=1)

            now = fields.Datetime.now()
            if existing:
                existing.sudo().write({
                    'viewed_at': now,
                    'stock_type': stock_type or 'sales_stock',
                })
            else:
                request.env['pb.recently.viewed'].sudo().create({
                    'partner_id': partner.id,
                    'stock_ref': s_id,
                    'stock_type': stock_type or 'sales_stock',
                    'viewed_at': now,
                })

            all_records = request.env['pb.recently.viewed'].sudo().search(
                [('partner_id', '=', partner.id)],
                order='viewed_at desc'
            )
            if len(all_records) > 4:
                excess = all_records[4:]
                excess.sudo().unlink()

            return self.get_recently_viewed()
        except Exception as e:
            _logger.exception("Error in add_to_recently_viewed")
            return {'status': 'error', 'message': str(e)}

    @http.route(['/api/v1/website/member/recently-viewed/sync'], type='json', auth='user', methods=['POST'], csrf=False)
    def sync_recently_viewed(self, items=None, **kwargs):
        try:
            user = request.env.user
            partner = user.partner_id
            if not partner:
                return {'status': 'error', 'message': 'User partner not found'}

            raw_items = items if isinstance(items, list) else []
            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                s_id = str(item.get('stock_id') or item.get('stock_ref') or '').strip()
                if not s_id:
                    continue
                s_type = item.get('stock_type') or 'sales_stock'
                v_at_raw = item.get('viewed_at')
                try:
                    v_at = fields.Datetime.to_datetime(v_at_raw) if v_at_raw else fields.Datetime.now()
                except Exception:
                    v_at = fields.Datetime.now()

                existing = request.env['pb.recently.viewed'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('stock_ref', '=', s_id)
                ], limit=1)
                if existing:
                    if v_at and v_at > existing.viewed_at:
                        existing.sudo().write({
                            'viewed_at': v_at,
                            'stock_type': s_type,
                        })
                else:
                    request.env['pb.recently.viewed'].sudo().create({
                        'partner_id': partner.id,
                        'stock_ref': s_id,
                        'stock_type': s_type,
                        'viewed_at': v_at,
                    })

            all_records = request.env['pb.recently.viewed'].sudo().search(
                [('partner_id', '=', partner.id)],
                order='viewed_at desc'
            )
            if len(all_records) > 4:
                excess = all_records[4:]
                excess.sudo().unlink()

            return self.get_recently_viewed()
        except Exception as e:
            _logger.exception("Error in sync_recently_viewed")
            return {'status': 'error', 'message': str(e)}

def fields_to_string(val):
    if not val:
        return ''
    return str(val)

