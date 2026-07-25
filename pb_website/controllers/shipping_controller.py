# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

class ShippingScheduleController(http.Controller):

    @http.route('/api/v1/website/shipping-schedules', type='json', auth='public', methods=['POST', 'GET'], csrf=False)
    def get_shipping_schedules(self, origin_port=None, dest_port=None, carrier_name=None, trade_lane=None, **kw):
        """Public API endpoint returning active shipping schedules with port calls."""
        domain = [('active', '=', True)]
        if carrier_name:
            domain.append(('carrier_name', '=ilike', carrier_name))
        if trade_lane:
            domain.append(('trade_lane', '=ilike', trade_lane))

        schedules = request.env['shipping.schedule'].sudo().search(domain, order='issue_date desc')
        
        result = []
        for sched in schedules:
            lines_data = []
            matched_origin = False
            matched_dest = False

            for line in sched.line_ids:
                p_code = line.port_code or ''
                p_name = line.port_name or ''
                is_origin = (origin_port and (p_code.upper() == origin_port.upper() or origin_port.upper() in p_name.upper()))
                is_dest = (dest_port and (p_code.upper() == dest_port.upper() or dest_port.upper() in p_name.upper()))
                
                if is_origin:
                    matched_origin = True
                if is_dest:
                    matched_dest = True

                lines_data.append({
                    'id': line.id,
                    'sequence': line.sequence,
                    'call_type': line.call_type,
                    'port_name': line.port_name,
                    'port_code': line.port_code,
                    'eta': line.eta.isoformat() if line.eta else None,
                    'etd': line.etd.isoformat() if line.etd else None,
                    'eta_end': line.eta_end.isoformat() if line.eta_end else None,
                    'etd_end': line.etd_end.isoformat() if line.etd_end else None,
                    'status': line.status,
                    'remarks': line.remarks,
                })

            # If filtering by port, skip schedules that don't match criteria
            if origin_port and not matched_origin:
                continue
            if dest_port and not matched_dest:
                continue

            result.append({
                'id': sched.id,
                'name': sched.name,
                'carrier_name': sched.carrier_name,
                'vessel_name': sched.vessel_name,
                'voyage_no': sched.voyage_no,
                'revision_no': sched.revision_no,
                'issue_date': sched.issue_date.isoformat() if sched.issue_date else None,
                'trade_lane': sched.trade_lane,
                'cargo_restrictions': sched.cargo_restrictions,
                'allow_ev': sched.allow_ev,
                'allow_hybrid': sched.allow_hybrid,
                'require_nkkk': sched.require_nkkk,
                'lock_version': sched.lock_version,
                'port_calls': lines_data,
            })

        return {
            'status': 'success',
            'count': len(result),
            'schedules': result,
        }
