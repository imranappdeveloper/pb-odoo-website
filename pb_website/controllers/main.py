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
            # Query unique values from database models
            makers = request.env['car.maker'].sudo().search([])
            makes = [m.name for m in makers if m.name]

            categories = request.env['car.category'].sudo().search([])
            body_types = [c.name for c in categories if c.name]

            transmissions_records = request.env['car.transmission'].sudo().search([])
            transmissions = [t.name for t in transmissions_records if t.name]

            fuels = request.env['fuel.type'].sudo().search([])
            fuel_types = [f.name for f in fuels if f.name]

            locations_records = request.env['stock.route'].sudo().search([])
            locations = [l.name for l in locations_records if l.name]

            # Years: standard range
            import datetime
            current_year = datetime.date.today().year
            years = list(range(current_year, 1980, -1))

            # Models group mapping: { maker_name: [model_names] }
            models_mapping = {}
            cars = request.env['res.car'].sudo().search([])
            for car in cars:
                if car.maker_id and car.maker_id.name and car.name:
                    maker_name = car.maker_id.name
                    if maker_name not in models_mapping:
                        models_mapping[maker_name] = []
                    if car.name not in models_mapping[maker_name]:
                        models_mapping[maker_name].append(car.name)

            options = {
                "makes": sorted(makes),
                "models": models_mapping,
                "categories": sorted(body_types),
                "body_types": sorted(body_types),
                "transmissions": sorted(transmissions),
                "fuel_types": sorted(fuel_types),
                "locations": sorted(locations),
                "years": years
            }
            return self._make_json_response(options)
        except Exception as e:
            _logger.exception("Unexpected error in get_search_options")
            return self._make_error_response(_("An unexpected error occurred while fetching search options."), status=500)

    @http.route('/api/v1/website/testimonials', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_testimonials(self, **kwargs):
        """
        API Endpoint: Returns seeded list of customer testimonials.
        """
        try:
            records = request.env['pb.testimonial'].sudo().search([])
            testimonials = []
            for record in records:
                testimonials.append({
                    "id": record.id,
                    "name": record.name,
                    "country": record.country or "",
                    "rating": record.rating,
                    "text": record.text or "",
                    "photoUrl": f"/web/image/pb.testimonial/{record.id}/photo" if record.photo else "/images/default-avatar.png"
                })
            return self._make_json_response(testimonials)
        except Exception as e:
            _logger.exception("Unexpected error in get_testimonials")
            return self._make_error_response(_("An unexpected error occurred while fetching testimonials."), status=500)

    @http.route('/api/v1/website/news', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_news(self, **kwargs):
        """
        API Endpoint: Returns seeded list of news articles.
        """
        try:
            records = request.env['pb.news'].sudo().search([('published', '=', True)])
            news = []
            for record in records:
                news.append({
                    "id": record.id,
                    "title": record.title,
                    "body": record.body or "",
                    "thumbnail": f"/web/image/pb.news/{record.id}/thumbnail" if record.thumbnail else "",
                    "date": record.date,
                    "published": record.published
                })
            return self._make_json_response(news)
        except Exception as e:
            _logger.exception("Unexpected error in get_news")
            return self._make_error_response(_("An unexpected error occurred while fetching news."), status=500)

    @http.route('/api/v1/website/new-arrivals', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_new_arrivals(self, **kwargs):
        """
        API Endpoint: Returns the latest 8 vehicles in draft state from product.template.
        """
        try:
            domain = [('state', '=', '1_draft')]
            records = request.env['product.template'].sudo().search(domain, order='create_date desc', limit=8)
            vehicles = []
            for record in records:
                image_urls = []
                if record.image_1920:
                    image_urls.append(f"/web/image/product.template/{record.id}/image_1920")
                
                if hasattr(record, 'product_template_image_ids') and record.product_template_image_ids:
                    for img in record.product_template_image_ids:
                        image_urls.append(f"/web/image/product.image/{img.id}/image_1920")
                
                if not image_urls:
                    image_urls.append("/images/placeholder-car.jpg")

                vehicles.append({
                    "id": record.id,
                    "name": record.name or "",
                    "title": f"{record.car_name.name or ''} {record.name or ''}".strip(),
                    "maker": record.maker.name if hasattr(record, 'maker') and record.maker else "",
                    "model": record.car_name.name if hasattr(record, 'car_name') and record.car_name else "",
                    "stockId": record.stock_id or "",
                    "year": record.year or 0,
                    "km": f"{record.km or ''} km" if record.km else "0 km",
                    "engineCc": f"{record.engine_cc.name or ''} cc" if hasattr(record, 'engine_cc') and record.engine_cc else "",
                    "transmission": record.transmission.name if hasattr(record, 'transmission') and record.transmission else "",
                    "fuelType": record.fuel_type.name if hasattr(record, 'fuel_type') and record.fuel_type else "",
                    "carCategory": record.car_category.name if hasattr(record, 'car_category') and record.car_category else "",
                    "driveType": record.drive_type or "right_hand",
                    "doors": record.doors or "5",
                    "seatingCapacity": record.seating_capacity or 5,
                    "exteriorColor": record.exterior_color.name if hasattr(record, 'exterior_color') and record.exterior_color else "",
                    "grade": record.grade or "4.5",
                    "fobPriceUsd": record.fob_price or 0,
                    "fobPriceJpy": record.final_fob_price or 0,
                    "stockLocation": record.stock_location.name if hasattr(record, 'stock_location') and record.stock_location else "Yokohama, Japan",
                    "imageUrls": image_urls,
                    "isFeatured": record.is_featured or False,
                    "isKenyaStock": record.is_kenya_stock or False,
                    "isDiscounted": record.is_discounted or False
                })
            return self._make_json_response(vehicles)
        except Exception as e:
            _logger.exception("Unexpected error in get_new_arrivals")
            return self._make_error_response(_("An unexpected error occurred while fetching new arrivals."), status=500)
