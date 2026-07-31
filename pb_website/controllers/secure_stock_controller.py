# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.addons.auction.controllers.stock_controller import StockController

from .chassis_security import protect_serialized_vehicle


class SecureStockController(StockController):
    """Apply Odoo-session chassis authorization to the shared stock API."""

    def _session_id(self):
        return getattr(request.session, 'sid', '') or ''

    def _authorized(self, vehicle_model, vehicle_ref):
        if request.session.uid:
            return True
        return request.env['pb.chassis.reveal.entitlement'].sudo().has_active(
            self._session_id(),
            vehicle_model,
            str(vehicle_ref or ''),
        )

    def _format_product_template_record(self, record):
        payload = super()._format_product_template_record(record)
        payload['stock_record_id'] = 'P%s' % record.id
        chassis = payload.get('chassis_number') or ''
        return protect_serialized_vehicle(
            payload,
            chassis,
            authorized=self._authorized('product.template', record.id),
        )

    def _format_quick_car_record(self, record):
        payload = super()._format_quick_car_record(record)
        payload['stock_record_id'] = 'Q%s' % record.get('id')
        chassis = payload.get('chassis_number') or ''
        return protect_serialized_vehicle(
            payload,
            chassis,
            authorized=self._authorized('quick.car', record.get('id')),
        )
