# -*- coding: utf-8 -*-

import json
from odoo import http
from odoo.http import request

class ShippingScheduleController(http.Controller):

    def _build_schedule_payload(self, schedules, origin_port=None, dest_port=None):
        """Helper to format schedule models into clean dictionary list."""
        result = []
        for sched in schedules:
            lines_data = []
            matched_origin = False
            matched_dest = False

            for line in sched.line_ids:
                p_code = line.port_code or ''
                p_name = line.port_name or ''
                
                if origin_port:
                    if p_code.upper() == origin_port.upper() or origin_port.upper() in p_name.upper():
                        matched_origin = True
                if dest_port:
                    if p_code.upper() == dest_port.upper() or dest_port.upper() in p_name.upper():
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
        return result

    # --------------------------------------------------------------------------
    # 1. JSON-RPC API Endpoint (POST/GET)
    # --------------------------------------------------------------------------
    @http.route('/api/v1/website/shipping-schedules', type='json', auth='public', methods=['POST', 'GET'], csrf=False)
    def get_shipping_schedules_json(self, origin_port=None, dest_port=None, carrier_name=None, trade_lane=None, **kw):
        """JSON-RPC API endpoint returning active shipping schedules."""
        domain = [('active', '=', True)]
        if carrier_name:
            domain.append(('carrier_name', '=ilike', f'%{carrier_name}%'))
        if trade_lane:
            domain.append(('trade_lane', '=ilike', f'%{trade_lane}%'))

        schedules = request.env['shipping.schedule'].sudo().search(domain, order='issue_date desc, id desc')
        result = self._build_schedule_payload(schedules, origin_port=origin_port, dest_port=dest_port)

        return {
            'status': 'success',
            'count': len(result),
            'schedules': result,
        }

    # --------------------------------------------------------------------------
    # 2. REST HTTP GET Endpoint (Returns direct JSON for standard fetch/axios)
    # --------------------------------------------------------------------------
    @http.route('/api/v1/website/shipping-schedules/rest', type='http', auth='public', methods=['GET'], csrf=False)
    def get_shipping_schedules_rest(self, **kw):
        """REST HTTP GET endpoint for static website frontend integration."""
        origin_port = kw.get('origin_port')
        dest_port = kw.get('dest_port')
        carrier_name = kw.get('carrier_name')
        trade_lane = kw.get('trade_lane')

        domain = [('active', '=', True)]
        if carrier_name:
            domain.append(('carrier_name', '=ilike', f'%{carrier_name}%'))
        if trade_lane:
            domain.append(('trade_lane', '=ilike', f'%{trade_lane}%'))

        schedules = request.env['shipping.schedule'].sudo().search(domain, order='issue_date desc, id desc')
        result = self._build_schedule_payload(schedules, origin_port=origin_port, dest_port=dest_port)

        response_data = {
            'status': 'success',
            'count': len(result),
            'schedules': result,
        }
        return request.make_response(
            json.dumps(response_data),
            headers=[('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')]
        )

    # --------------------------------------------------------------------------
    # 3. Calendar & Region Grid Endpoint (Formatted for UI Calendar Cards/Tabs)
    # --------------------------------------------------------------------------
    @http.route('/api/v1/website/shipping-schedules/calendar', type='http', auth='public', methods=['GET'], csrf=False)
    def get_shipping_calendar_ui(self, **kw):
        """REST HTTP GET endpoint formatted specifically for UI Calendar / Region Tabs."""
        selected_region = kw.get('region')

        domain = [('active', '=', True)]
        if selected_region and selected_region.lower() != 'all regions':
            domain.append(('trade_lane', '=ilike', f'%{selected_region}%'))

        schedules = request.env['shipping.schedule'].sudo().search(domain, order='issue_date desc, id desc')
        
        # Get all distinct region/trade lane names for tabs
        all_active_schedules = request.env['shipping.schedule'].sudo().search([('active', '=', True)])
        distinct_regions = list(set([s.trade_lane for s in all_active_schedules if s.trade_lane]))
        distinct_regions.sort()
        region_tabs = ['All Regions'] + distinct_regions

        calendar_grid = []
        for sched in schedules:
            pol_list = []
            pod_list = []

            for line in sched.line_ids:
                item = {
                    'id': line.id,
                    'port_name': line.port_name,
                    'port_code': line.port_code,
                    'eta': line.eta.isoformat() if line.eta else None,
                    'etd': line.etd.isoformat() if line.etd else None,
                    'eta_end': line.eta_end.isoformat() if line.eta_end else None,
                    'etd_end': line.etd_end.isoformat() if line.etd_end else None,
                    'status': line.status,
                    'remarks': line.remarks,
                }
                if line.call_type == 'pol':
                    pol_list.append(item)
                else:
                    pod_list.append(item)

            calendar_grid.append({
                'schedule_id': sched.id,
                'title': sched.name,
                'carrier': sched.carrier_name,
                'vessel': sched.vessel_name,
                'voyage': sched.voyage_no,
                'trade_lane': sched.trade_lane,
                'revision': sched.revision_no,
                'issue_date': sched.issue_date.isoformat() if sched.issue_date else None,
                'cargo_restrictions': sched.cargo_restrictions,
                'loading_ports (POL)': pol_list,
                'discharge_ports (POD)': pod_list,
            })

        response_payload = {
            'status': 'success',
            'available_region_tabs': region_tabs,
            'selected_region': selected_region or 'All Regions',
            'count': len(calendar_grid),
            'schedules': calendar_grid,
        }

        return request.make_response(
            json.dumps(response_payload),
            headers=[('Content-Type', 'application/json'), ('Access-Control-Allow-Origin', '*')]
        )
