# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class WebsiteCatalogController(http.Controller):
    """
    Controller for Pacific Boeki Website API Integration.
    Exposes endpoints for stock search, filters, testimonials, news, shipping schedules, and forms.
    """

    def _make_json_response(self, data, status=200, meta=None):
        """
        Standardized JSON response wrapper conforming to requirement-lock specs.
        """
        response_data = {
            'status': 'success' if status < 400 else 'error',
            'data': data,
        }
        if meta:
            response_data['meta'] = meta
        
        class OdooJsonEncoder(json.JSONEncoder):
            def default(self, obj):
                import datetime
                if isinstance(obj, (datetime.date, datetime.datetime)):
                    return obj.isoformat()
                if isinstance(obj, (bytes, bytearray)):
                    return obj.decode('utf-8', errors='ignore')
                if hasattr(obj, 'ids') and hasattr(obj, '_name'):
                    return obj.ids
                return super().default(obj)

        json_str = json.dumps(response_data, cls=OdooJsonEncoder)
        return json.loads(json_str)

    def _make_error_response(self, message, status=400):
        """
        Standardized Error response wrapper.
        """
        return self._make_json_response({'message': message}, status=status)

    @http.route('/api/v1/website/search-options', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_search_options(self, **kwargs):
        """
        API Endpoint: Returns options for filtering dropdowns (makes, models, categories/body types, etc.).
        """
        try:
            # Placeholder data - to be connected to model data queries in subsequent tasks
            options = {
                "makes": [],
                "body_types": [],
                "transmissions": [],
                "fuel_types": [],
                "locations": [],
                "years": []
            }
            return self._make_json_response(options)
        except Exception as e:
            _logger.exception("Unexpected error in get_search_options")
            return self._make_error_response(_("An unexpected error occurred while fetching search options."), status=500)
