# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

def get_dummy_vehicle_image(record_id):
    dummy_images = [
        '/images/scraped/234260.png',
        '/images/scraped/234264.png',
        '/images/scraped/234270.png',
        '/images/scraped/234274.png',
        '/images/scraped/234687.png',
        '/images/scraped/234691.png',
        '/images/scraped/234695.png',
        '/images/scraped/234699.png',
        '/images/scraped/1.jpg',
        '/images/scraped/2.jpg'
    ]
    idx = abs(int(record_id or 0)) % len(dummy_images)
    return dummy_images[idx]

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

    @http.route('/api/v1/website/team-members', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_team_members(self, **kwargs):
        """
        API Endpoint: Returns list of team members.
        """
        try:
            records = request.env['pb.team_member'].sudo().search([('active', '=', True)], order='display_order, id')
            members = []
            for record in records:
                members.append({
                    "id": record.id,
                    "name": record.name,
                    "role": record.role,
                    "photoUrl": f"/web/image/pb.team_member/{record.id}/photo" if record.photo else "/images/default-avatar.png",
                    "displayOrder": record.display_order
                })
            return self._make_json_response(members)
        except Exception as e:
            _logger.exception("Unexpected error in get_team_members")
            return self._make_error_response(_("An unexpected error occurred while fetching team members."), status=500)

    @http.route('/api/v1/website/recruitment-inquiry', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def submit_recruitment_inquiry(self, **kwargs):
        """
        API Endpoint: Submits a new recruitment inquiry.
        """
        try:
            name = kwargs.get('name')
            phone = kwargs.get('phone')
            email = kwargs.get('email')
            dob = kwargs.get('dob')
            street_address = kwargs.get('street_address')
            message = kwargs.get('message')
            recruitment_type = kwargs.get('recruitment_type')
            resume_base64 = kwargs.get('resume_base64')
            resume_filename = kwargs.get('resume_filename')

            # Validation
            if not all([name, phone, email, message, recruitment_type, resume_base64]):
                return self._make_error_response(_("Missing required fields."))

            vals = {
                'name': name,
                'phone': phone,
                'email': email,
                'street_address': street_address,
                'message': message,
                'recruitment_type': recruitment_type,
                'resume': resume_base64,
                'resume_filename': resume_filename or 'resume.pdf'
            }

            if dob:
                vals['dob'] = dob

            inquiry = request.env['pb.recruitment_inquiry'].sudo().create(vals)
            return self._make_json_response({'success': True, 'id': inquiry.id})
        except Exception as e:
            _logger.exception("Unexpected error in submit_recruitment_inquiry")
            return self._make_error_response(_("An unexpected error occurred while submitting recruitment inquiry."), status=500)

    @http.route('/api/v1/website/news', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_news(self, **kwargs):
        """
        API Endpoint: Returns seeded list of news articles or single article detail.
        """
        try:
            article_id = kwargs.get('id')
            if article_id:
                record = request.env['pb.news'].sudo().browse(int(article_id))
                if not record.exists() or not record.published:
                    return self._make_error_response(_("News article not found."), status=404)
                return self._make_json_response({
                    "id": record.id,
                    "title": record.title,
                    "body": record.body or "",
                    "thumbnail": f"/web/image/pb.news/{record.id}/thumbnail" if record.thumbnail else "",
                    "date": record.date,
                    "published": record.published
                })

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
                    image_urls.append(get_dummy_vehicle_image(record.id))

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

    @http.route('/api/v1/website/vehicles', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_vehicles(self, **kwargs):
        """
        API Endpoint: Returns a paginated, filtered list of vehicles from product.template.
        """
        try:
            page = int(kwargs.get('page', 1))
            limit = int(kwargs.get('limit', 10))
            sort_key = kwargs.get('sort') or kwargs.get('sort_by')
            
            filters = kwargs.get('filters', {})
            if not isinstance(filters, dict):
                filters = {}

            # Fall back to root-level params if not nested in filters
            maker = filters.get('maker') or kwargs.get('maker')
            model = filters.get('model') or kwargs.get('model')
            year_from = filters.get('year_from') or kwargs.get('year_from')
            year_to = filters.get('year_to') or kwargs.get('year_to')
            transmission = filters.get('transmission') or kwargs.get('transmission')
            fuel = filters.get('fuel') or kwargs.get('fuel')
            keyword = filters.get('keyword') or kwargs.get('keyword')
            price_min = filters.get('price_min') or kwargs.get('price_min')
            price_max = filters.get('price_max') or kwargs.get('price_max')
            drive_type = filters.get('drive_type') or kwargs.get('drive_type')
            km_min = filters.get('km_min') or kwargs.get('km_min')
            km_max = filters.get('km_max') or kwargs.get('km_max')

            domain = [('state', '=', '1_draft')]

            if maker:
                domain.append(('maker.name', '=ilike', maker))
            if model:
                domain.append(('car_name.name', '=ilike', model))
            if year_from:
                try:
                    domain.append(('year', '>=', int(year_from)))
                except ValueError:
                    pass
            if year_to:
                try:
                    domain.append(('year', '<=', int(year_to)))
                except ValueError:
                    pass
            if transmission:
                domain.append(('transmission.name', '=ilike', transmission))
            if fuel:
                domain.append(('fuel_type.name', '=ilike', fuel))
            if drive_type:
                domain.append(('drive_type', '=', drive_type))
            if price_min:
                try:
                    domain.append(('fob_price', '>=', float(price_min)))
                except ValueError:
                    pass
            if price_max:
                try:
                    domain.append(('fob_price', '<=', float(price_max)))
                except ValueError:
                    pass
            if km_min:
                try:
                    domain.append(('km', '>=', int(km_min)))
                except ValueError:
                    pass
            if km_max:
                try:
                    domain.append(('km', '<=', int(km_max)))
                except ValueError:
                    pass
            if keyword:
                kw = keyword.strip()
                domain.extend([
                    '|', '|', '|', '|',
                    ('name', 'ilike', kw),
                    ('car_name.name', 'ilike', kw),
                    ('maker.name', 'ilike', kw),
                    ('stock_id', 'ilike', kw),
                    ('barcode', 'ilike', kw)
                ])

            sort_map = {
                'price_asc': 'fob_price asc',
                'price_desc': 'fob_price desc',
                'year_asc': 'year asc',
                'year_desc': 'year desc',
                'km_asc': 'km asc',
                'km_desc': 'km desc',
                'newest': 'create_date desc',
            }
            order = sort_map.get(sort_key, 'create_date desc, id desc')

            offset = (page - 1) * limit
            total_count = request.env['product.template'].sudo().search_count(domain)
            records = request.env['product.template'].sudo().search(domain, order=order, limit=limit, offset=offset)

            vehicles = []
            for record in records:
                image_urls = []
                if record.image_1920:
                    image_urls.append(f"/web/image/product.template/{record.id}/image_1920")
                
                if hasattr(record, 'product_template_image_ids') and record.product_template_image_ids:
                    for img in record.product_template_image_ids:
                        image_urls.append(f"/web/image/product.image/{img.id}/image_1920")
                
                if not image_urls:
                    image_urls.append(get_dummy_vehicle_image(record.id))

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

            return self._make_json_response({
                "vehicles": vehicles,
                "total": total_count
            })
        except Exception as e:
            _logger.exception("Unexpected error in get_vehicles")
            return self._make_error_response(_("An unexpected error occurred while fetching vehicles."), status=500)

    @http.route('/api/v1/website/vehicles/detail', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_vehicle_detail(self, **kwargs):
        """
        API Endpoint: Returns detailed specifications for a single vehicle template by ID.
        """
        try:
            vehicle_id = int(kwargs.get('vehicle_id') or kwargs.get('id') or 0)
            if not vehicle_id:
                return self._make_error_response(_("Vehicle ID is required."), status=400)

            record = request.env['product.template'].sudo().browse(vehicle_id)
            if not record.exists():
                return self._make_error_response(_("Vehicle not found."), status=404)

            image_urls = []
            if record.image_1920:
                image_urls.append(f"/web/image/product.template/{record.id}/image_1920")

            if hasattr(record, 'product_template_image_ids') and record.product_template_image_ids:
                for img in record.product_template_image_ids:
                    image_urls.append(f"/web/image/product.image/{img.id}/image_1920")

            if not image_urls:
                image_urls.append(get_dummy_vehicle_image(record.id))

            # Extract model code
            model_code = getattr(record, 'model_code', getattr(record, 'x_model_code', ''))
            if hasattr(model_code, 'name'):
                model_code = model_code.name
            if not model_code:
                model_code = record.name.split('-')[0] if record.name and '-' in record.name else 'DBA-XYZ'

            # Extract chassis number and mask it
            chassis_no = record.name or ""
            chassis_no_masked = chassis_no
            if len(chassis_no) > 4:
                chassis_no_masked = chassis_no[:-4] + "****"

            # Parse accessories checklist
            accessories = []
            opt_fields = {
                'x_opt_ac': 'Air Conditioning',
                'x_opt_ps': 'Power Steering',
                'x_opt_pw': 'Power Windows',
                'x_opt_airbag': 'Air Bags',
                'x_opt_abs': 'ABS Brakes',
                'x_opt_nav': 'Navigation',
                'x_opt_sunroof': 'Sunroof',
                'x_opt_leather': 'Leather Seats',
                'x_opt_alloy': 'Alloy Wheels',
                'opt_ac': 'Air Conditioning',
                'opt_ps': 'Power Steering',
                'opt_pw': 'Power Windows',
                'opt_airbag': 'Air Bags',
                'opt_abs': 'ABS Brakes',
                'opt_nav': 'Navigation',
                'opt_sunroof': 'Sunroof',
                'opt_leather': 'Leather Seats',
                'opt_alloy': 'Alloy Wheels',
            }
            for field, label in opt_fields.items():
                if hasattr(record, field) and getattr(record, field):
                    if label not in accessories:
                        accessories.append(label)

            vehicle = {
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
                "isDiscounted": record.is_discounted or False,
                "modelCode": model_code,
                "chassisNoMasked": chassis_no_masked,
                "accessories": accessories,
            }
            return self._make_json_response(vehicle)
        except Exception as e:
            _logger.exception("Unexpected error in get_vehicle_detail")
            return self._make_error_response(_("An unexpected error occurred while fetching vehicle detail."), status=500)

    @http.route('/api/v1/website/shipping/rates', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_shipping_rates(self, **kwargs):
        """
        API Endpoint: Returns list of ports and shipping rate per cubic meter (m³) by destination.
        """
        try:
            records = request.env['pb.freight.rate'].sudo().search([])
            rates = []
            for record in records:
                rates.append({
                    "id": record.id,
                    "country": record.country or "",
                    "port": record.port or "",
                    "ratePerM3": record.rate_per_m3 or 0.0,
                })
            return self._make_json_response(rates)
        except Exception as e:
            _logger.exception("Unexpected error in get_shipping_rates")
            return self._make_error_response(_("An unexpected error occurred while fetching shipping rates."), status=500)

    @http.route('/api/v1/website/register', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def register(self, **kwargs):
        """
        API Endpoint: Registers a new portal user and maps name, email, phone, country, and company details to res.partner.
        """
        try:
            name = kwargs.get('name')
            email = kwargs.get('email')
            password = kwargs.get('password')
            country_name = kwargs.get('country')
            phone = kwargs.get('phone')
            company_type = kwargs.get('company_type', 'person')
            company_name = kwargs.get('company_name')

            if not name or not email or not password or not country_name or not phone:
                return self._make_error_response(_("Name, Email, Password, Country, and Phone are required fields."), status=400)

            # Check if login already exists
            existing_user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if existing_user:
                return self._make_error_response(_("A member account with this email already exists."), status=400)

            # Resolve Country ID
            country_id = False
            if country_name:
                country = request.env['res.country'].sudo().search([('name', '=ilike', country_name)], limit=1)
                if country:
                    country_id = country.id

            # Retrieve base portal group XML ref
            portal_group = request.env.ref('base.group_portal')

            # Create standard Portal user
            user_vals = {
                'name': name,
                'login': email,
                'email': email,
                'password': password,
                'groups_id': [(6, 0, [portal_group.id])],
            }
            new_user = request.env['res.users'].sudo().create(user_vals)

            # Write details directly to associated partner record
            partner = new_user.partner_id
            partner_vals = {
                'phone': phone,
                'mobile': phone,
                'country_id': country_id,
                'company_type': company_type,
                'is_company': company_type == 'company',
            }
            if company_name:
                partner_vals['company_name'] = company_name

            partner.sudo().write(partner_vals)

            return self._make_json_response({
                'uid': new_user.id,
                'name': new_user.name,
                'email': new_user.email,
                'partner_id': partner.id
            })

        except Exception as e:
            _logger.exception("Unexpected error in register")
            return self._make_error_response(_("An unexpected error occurred during user registration."), status=500)


    @http.route('/api/v1/website/forgot-password', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def forgot_password(self, **kwargs):
        """
        API Endpoint: Initiates Odoo password reset flow and returns standard or offline reset link.
        """
        try:
            email = kwargs.get('email')
            if not email:
                return self._make_error_response(_("Email ID/Login ID is required."), status=400)

            user = request.env['res.users'].sudo().search([('login', '=', email)], limit=1)
            if not user:
                return self._make_error_response(_("No member account found with this email ID."), status=404)

            # Generate Odoo reset password token and URL
            partner = user.partner_id
            partner.sudo().signup_prepare(signup_type='reset')
            reset_url = partner.signup_url

            # Attempt sending reset password email
            try:
                user.sudo().action_reset_password()
                email_sent = True
            except Exception as mail_err:
                _logger.warning("Failed to send reset email: %s. Proceeding with local token response.", str(mail_err))
                email_sent = False

            return self._make_json_response({
                'message': _("Your password reset link has been sent to your email ID !!"),
                'email': email,
                'reset_url': reset_url,  # Local dev utility
                'email_sent': email_sent
            })

        except Exception as e:
            _logger.exception("Unexpected error in forgot_password")
            return self._make_error_response(_("An unexpected error occurred while processing password reset request."), status=500)

    @http.route('/api/v1/website/contact', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def contact(self, **kwargs):
        """
        API Endpoint: Creates a new lead in CRM (crm.lead) from contact form submission.
        """
        try:
            tlt = kwargs.get('tlt')
            name = kwargs.get('name')
            country_name = kwargs.get('country')
            email = kwargs.get('email')
            phone = kwargs.get('phone')
            is_whatsapp = kwargs.get('is_whatsapp', False)
            is_viber = kwargs.get('is_viber', False)
            is_line = kwargs.get('is_line', False)
            msg = kwargs.get('msg')

            if not name or not email or not msg:
                return self._make_error_response(_("Name, Email, and Message are required fields."), status=400)

            # Resolve Country ID
            country_id = False
            if country_name:
                country = request.env['res.country'].sudo().search([('name', '=ilike', country_name)], limit=1)
                if country:
                    country_id = country.id

            # Assemble full contact name
            contact_name = name
            if tlt:
                contact_name = f"{tlt} {name}"

            # Create the lead
            lead_vals = {
                'name': f"Website Contact: {name}",
                'contact_name': contact_name,
                'email_from': email,
                'phone': phone,
                'description': msg,
                'country_id': country_id,
                'x_is_whatsapp': bool(is_whatsapp),
                'x_is_viber': bool(is_viber),
                'x_is_line': bool(is_line),
            }
            lead = request.env['crm.lead'].sudo().create(lead_vals)

            return self._make_json_response({
                'message': _("Thank you for contacting us! We will get back to you soon."),
                'lead_id': lead.id
            })

        except Exception as e:
            _logger.exception("Unexpected error in contact")
            return self._make_error_response(_("An unexpected error occurred while submitting contact form."), status=500)





