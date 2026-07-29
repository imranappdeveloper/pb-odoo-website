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

    def _get_email_params(self):
        """
        Helper to fetch email system parameters with proper fallbacks:
        - default_email (sender address & default fallback)
        - default_email_sales (inbound sales/contact inquiries)
        - default_email_job (inbound job/recruitment inquiries)
        """
        ir_config = request.env['ir.config_parameter'].sudo()
        default_email = ir_config.get_param('pb_website.default_email') or 'info@pacificboeki.jp'
        default_email_sales = ir_config.get_param('pb_website.default_email_sales') or default_email
        default_email_job = ir_config.get_param('pb_website.default_email_job') or default_email

        # Sync mail.default.from with default_email
        current_default_from = ir_config.get_param('mail.default.from')
        if current_default_from != default_email:
            ir_config.set_param('mail.default.from', default_email)

        return {
            'default_email': default_email,
            'default_email_sales': default_email_sales,
            'default_email_job': default_email_job,
        }

    def _get_common_mail_footer(self, email_sender=None):
        """
        Returns standard common email footer HTML consistent with auction module.
        """
        if not email_sender:
            email_params = self._get_email_params()
            email_sender = email_params['default_email']

        return f"""
        <div style="margin-top: 25px; color: #34495E; font-size: 13px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
            <strong>Thanks &amp; Regards,</strong><br/>
            Pacific Boeki Sales Team<br/>
        </div>
        <div style="margin-top: 15px; border-left: 4px solid #BA3308; padding-left: 15px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
            <div style="margin-bottom: 15px;">
                <a href="https://www.pacificboeki.jp" target="_blank">
                    <img src="https://pacificboekiac.jp/web/image/website/1/logo/My%20Website?unique=9e28042" style="max-height: 60px; width: auto;"/>
                </a>
                <br/>
            </div>
            
            <div style="color: #34495E; font-size: 13px; line-height: 1.6;">
                Pacific Boeki Co. Ltd.<br/>
                Shibuya-Ku, Hiroo 1-8-9, Matsuishi Building 201,<br/>
                Tokyo, 150-0012 Tokyo Japan<br/>
                <strong>Phone:</strong> +81-3-5798-7681 | <strong>Fax:</strong> +81-3-5798-7682<br/>
                <strong>E-Mail:</strong> <a href="mailto:{email_sender}" style="text-decoration:none; color: #BA3308;">{email_sender}</a><br/>
                <strong>Web:</strong> <a href="http://www.pacificboeki.jp" target="_blank" style="text-decoration:none; color: #BA3308;">www.pacificboeki.jp</a>
            </div>
        </div>
        """


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

            # Model codes (chassis prefixes before hyphen)
            model_codes_set = set()
            try:
                templates = request.env['product.template'].sudo().search([('state', '=', '1_draft')])
                for tmpl in templates:
                    raw_name = tmpl.name or ''
                    if '-' in raw_name:
                        code = raw_name.split('-')[0].strip()
                        if code:
                            model_codes_set.add(code)
            except Exception:
                pass

            options = {
                "makes": sorted(makes),
                "models": models_mapping,
                "model_codes": sorted(list(model_codes_set)),
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
                    "photoUrl": f"data:image/jpeg;base64,{record.photo.decode('utf-8')}" if record.photo else "/images/default-avatar.png"
                })
            return self._make_json_response(testimonials)
        except Exception as e:
            _logger.exception("Unexpected error in get_testimonials")
            return self._make_error_response(_("An unexpected error occurred while fetching testimonials."), status=500)

    @http.route(['/api/v1/website/banner/image/<int:banner_id>', '/web/image/pb.banner/<int:banner_id>/image'], type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_banner_image(self, banner_id, **kwargs):
        try:
            banner = request.env['pb.banner'].sudo().browse(banner_id)
            if banner.exists() and banner.image:
                image_data = base64.b64decode(banner.image)
                return request.make_response(image_data, [
                    ('Content-Type', 'image/jpeg'),
                    ('Cache-Control', 'public, max-age=86400')
                ])
        except Exception:
            _logger.exception("Error serving banner image")
        return request.not_found()

    @http.route(['/api/v1/website/news/image/<int:news_id>', '/web/image/pb.news/<int:news_id>/thumbnail'], type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_news_image(self, news_id, **kwargs):
        try:
            news = request.env['pb.news'].sudo().browse(news_id)
            if news.exists() and news.thumbnail:
                image_data = base64.b64decode(news.thumbnail)
                return request.make_response(image_data, [
                    ('Content-Type', 'image/jpeg'),
                    ('Cache-Control', 'public, max-age=86400')
                ])
        except Exception:
            _logger.exception("Error serving news image")
        return request.not_found()

    @http.route('/api/v1/website/banners', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_banners(self, **kwargs):
        """
        API Endpoint: Returns list of active hero banners.
        """
        try:
            records = request.env['pb.banner'].sudo().search([('is_active', '=', True)], order='sequence, id')
            banners = []
            for record in records:
                banners.append({
                    "id": record.id,
                    "name": record.name,
                    "imageUrl": f"data:image/jpeg;base64,{record.image.decode('utf-8')}" if record.image else "",
                    "sequence": record.sequence,
                    "isActive": record.is_active,
                    "title": record.title or "",
                    "subtitle": record.subtitle or "",
                    "url": record.url or ""
                })
            return self._make_json_response(banners)
        except Exception as e:
            _logger.exception("Unexpected error in get_banners")
            return self._make_error_response(_("An unexpected error occurred while fetching banners."), status=500)

    @http.route('/api/v1/website/gallery', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_gallery(self, **kwargs):
        """
        API Endpoint: Returns list of active photo gallery images.
        """
        try:
            records = request.env['pb.gallery'].sudo().search([('is_active', '=', True)], order='sequence, id')
            images = []
            for record in records:
                images.append({
                    "id": record.id,
                    "name": record.name,
                    "imageUrl": f"data:image/jpeg;base64,{record.image.decode('utf-8')}" if record.image else "",
                    "mediumUrl": f"data:image/jpeg;base64,{record.image_medium.decode('utf-8')}" if record.image_medium else "",
                    "sequence": record.sequence,
                    "isActive": record.is_active
                })
            return self._make_json_response(images)
        except Exception as e:
            _logger.exception("Unexpected error in get_gallery")
            return self._make_error_response(_("An unexpected error occurred while fetching gallery images."), status=500)

    @http.route('/api/v1/website/model-discounts', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_model_discounts(self, **kwargs):
        """
        API Endpoint: Returns list of active model discounts where discount_percent > 0.
        """
        try:
            records = request.env['pb.model.discount'].sudo().search([
                ('active', '=', True),
                ('discount_percent', '>', 0)
            ])
            data = [
                {
                    "model_name": rec.model_name,
                    "discount_percent": rec.discount_percent
                }
                for rec in records
            ]
            return self._make_json_response(data)
        except Exception as e:
            _logger.exception("Unexpected error in get_model_discounts")
            return self._make_error_response(_("An unexpected error occurred while fetching model discounts."), status=500)

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

            # Send recruitment emails (HR notification & candidate confirmation)
            try:
                email_params = self._get_email_params()
                job_email = email_params['default_email_job']
                from_email = email_params['default_email']

                recruitment_labels = {
                    'career': 'Career Recruitment',
                    'local': 'Local Career Recruitment',
                    'agent': 'Local Agent / Contract'
                }
                category_label = recruitment_labels.get(recruitment_type, recruitment_type)

                # Create PDF attachment for HR email if resume exists
                attachment_ids = []
                if resume_base64:
                    try:
                        attachment = request.env['ir.attachment'].sudo().create({
                            'name': resume_filename or 'resume.pdf',
                            'datas': resume_base64,
                            'res_model': 'mail.mail',
                            'res_id': 0,
                            'type': 'binary',
                            'mimetype': 'application/pdf',
                        })
                        attachment_ids.append(attachment.id)
                    except Exception as att_err:
                        _logger.warning("Failed to attach resume PDF for job application: %s", att_err)

                # 1. Internal HR Notification Email (To: default_email_job)
                hr_mail_vals = {
                    'subject': f"新規求人応募: {name} 様 ({category_label})",
                    'body_html': f"""
                        <div style="font-family: Arial, sans-serif; padding: 15px;">
                            <h3 style="color: #c8102e;">新規求人応募を受信しました</h3>
                            <p><strong>氏名:</strong> {name}</p>
                            <p><strong>メールアドレス:</strong> {email}</p>
                            <p><strong>電話番号:</strong> {phone}</p>
                            <p><strong>生年月日:</strong> {dob or '未入力'}</p>
                            <p><strong>住所:</strong> {street_address or '未入力'}</p>
                            <p><strong>応募区分:</strong> {category_label}</p>
                            <p><strong>メッセージ:</strong></p>
                            <blockquote style="background: #f9f9f9; border-left: 3px solid #c8102e; padding: 10px; margin: 0;">
                                {message}
                            </blockquote>
                        </div>
                        {self._get_common_mail_footer(from_email)}
                    """,
                    'email_to': job_email,
                    'email_from': f"Pacific Boeki <{from_email}>",
                    'reply_to': email,
                    'state': 'outgoing',
                }
                if attachment_ids:
                    hr_mail_vals['attachment_ids'] = [(6, 0, attachment_ids)]

                hr_mail = request.env['mail.mail'].sudo().create(hr_mail_vals)
                hr_mail.send()

                # 2. Candidate Confirmation Email (To: Candidate email)
                candidate_mail_vals = {
                    'subject': "求人応募を受け付けました",
                    'body_html': f"""
                    <div style="font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif; padding: 20px; line-height: 1.8; color: #333333;">
                        <p style="font-size: 16px; font-weight: bold;">{name} 様</p>
                        <p>この度は、Pacific Boeki の求人にご応募いただき、誠にありがとうございます。</p>
                        <p>ご応募内容および履歴書を正常に受け付けました。<br />
                        採用担当者が内容を確認し、選考を進めさせていただきます。応募内容が募集条件に適している場合は、次の選考についてご連絡いたします。</p>
                        <div style="background: #f9f9f9; border: 1px solid #eeeeee; padding: 16px; border-radius: 6px; margin: 20px 0;">
                            <h4 style="margin-top: 0; color: #c8102e; border-bottom: 1px solid #ddd; padding-bottom: 8px;">応募内容</h4>
                            <p style="margin: 6px 0;"><strong>氏名:</strong> {name}</p>
                            <p style="margin: 6px 0;"><strong>メールアドレス:</strong> {email}</p>
                            <p style="margin: 6px 0;"><strong>電話番号:</strong> {phone}</p>
                            <p style="margin: 6px 0;"><strong>生年月日:</strong> {dob or '未入力'}</p>
                            <p style="margin: 6px 0;"><strong>住所:</strong> {street_address or '未入力'}</p>
                            <p style="margin: 6px 0;"><strong>応募区分:</strong> {category_label}</p>
                            <p style="margin: 6px 0;"><strong>メッセージ:</strong> {message}</p>
                            <p style="margin: 6px 0;"><strong>履歴書（PDF）:</strong> 正常に受領しております。</p>
                        </div>
                        <p>この度は、Pacific Boeki にご関心をお寄せいただき、誠にありがとうございます。<br />
                        今後ともどうぞよろしくお願いいたします。</p>
                    </div>
                    {self._get_common_mail_footer(from_email)}
                    """,
                    'email_to': email,
                    'email_from': f"Pacific Boeki <{from_email}>",
                    'reply_to': job_email,
                    'state': 'outgoing',
                }
                cand_mail = request.env['mail.mail'].sudo().create(candidate_mail_vals)
                cand_mail.send()
            except Exception as mail_err:
                _logger.warning("Failed to dispatch recruitment notification emails: %s", mail_err)

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
                    "thumbnail": f"data:image/jpeg;base64,{record.thumbnail.decode('utf-8')}" if record.thumbnail else "",
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
                    "thumbnail": f"data:image/jpeg;base64,{record.thumbnail.decode('utf-8')}" if record.thumbnail else "",
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
                    "priceCurrency": "JPY",
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
                    "priceCurrency": "JPY",
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
                "priceCurrency": "JPY",
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
            # Fetch port destination rates from the live database
            ports = request.env['port.destination'].sudo().search([])
            rates = []
            for port in ports:
                rates.append({
                    "id": port.id,
                    "country": port.country_of_port.name if port.country_of_port else "",
                    "port": port.name,
                    "ratePerM3": port.default_cost or 0.0,
                    "currency": "USD"
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
            email = (kwargs.get('email') or kwargs.get('login') or '').strip()
            if not email:
                return self._make_error_response(_("Email ID/Login ID is required."), status=400)

            # Search user by login or email address case-insensitively
            user = request.env['res.users'].sudo().search([
                '|', ('login', '=ilike', email), ('email', '=ilike', email)
            ], limit=1)

            if not user:
                return self._make_error_response(_("No member account found with this email ID."), status=404)

            partner = user.partner_id
            if partner and not partner.email:
                partner.sudo().write({'email': email})

            reset_url = False
            email_sent = False

            # Generate Odoo reset password token & URL
            try:
                if partner:
                    partner.sudo().signup_prepare(signup_type='reset')
                    reset_url = getattr(partner, 'signup_url', False)
            except Exception as token_err:
                _logger.warning("Token preparation note: %s", str(token_err))

            # Attempt sending reset password email natively via Odoo
            try:
                user.sudo().action_reset_password()
                email_sent = True
            except Exception as mail_err:
                _logger.warning("Failed to send reset email via SMTP: %s.", str(mail_err))
                email_sent = False

            return self._make_json_response({
                'message': _("Your password reset link has been sent to your email ID !!"),
                'email': email,
                'reset_url': reset_url,
                'email_sent': email_sent
            })

        except Exception as e:
            _logger.exception("Unexpected error in forgot_password: %s", str(e))
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

            # Get configured sales email and sender email
            email_params = self._get_email_params()
            sales_email = email_params['default_email_sales']
            from_email = email_params['default_email']

            # Create mail.mail email record for contact inquiry
            try:
                mail_vals = {
                    'subject': f"Website Contact: {name}",
                    'body_html': f"""
                        <div style="font-family: Arial, sans-serif; padding: 15px;">
                            <h3 style="color: #c8102e;">New Website Contact Inquiry</h3>
                            <p><strong>Name:</strong> {contact_name}</p>
                            <p><strong>Email:</strong> {email}</p>
                            <p><strong>Phone:</strong> {phone or 'N/A'}</p>
                            <p><strong>Country:</strong> {country_name or 'N/A'}</p>
                            <p><strong>Message:</strong></p>
                            <blockquote style="background: #f9f9f9; border-left: 3px solid #c8102e; padding: 10px; margin: 0;">
                                {msg}
                            </blockquote>
                        </div>
                        {self._get_common_mail_footer(from_email)}
                    """,
                    'email_to': sales_email,
                    'email_from': f"Pacific Boeki <{from_email}>",
                    'reply_to': email,
                    'state': 'outgoing',
                }
                mail = request.env['mail.mail'].sudo().create(mail_vals)
                mail.send()
            except Exception as mail_err:
                _logger.warning("Failed to create mail.mail record for contact lead: %s", mail_err)

            return self._make_json_response({
                'message': _("Thank you for contacting us! We will get back to you soon."),
                'lead_id': lead.id
            })

        except Exception as e:
            _logger.exception("Unexpected error in contact")
            return self._make_error_response(_("An unexpected error occurred while submitting contact form."), status=500)

    @http.route('/api/v1/website/email/send', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def send_email(self, **kwargs):
        """
        API Endpoint: Common setup for sending emails via Odoo.
        Creates mail.mail records for outbound processing and tracking.
        """
        try:
            template_code = kwargs.get('template')
            recipient_email = kwargs.get('recipient_email')
            reply_to = kwargs.get('reply_to')
            data = kwargs.get('data') or {}

            if not template_code or not data:
                return self._make_error_response(_("Template code and data are required."), status=400)

            # Retrieve dynamic notification email system parameters
            email_params = self._get_email_params()
            default_email = email_params['default_email']
            sales_email = email_params['default_email_sales']
            job_email = email_params['default_email_job']

            subject = data.get('subject') or f"Website Notification: {template_code.replace('_', ' ').title()}"

            if data.get('is_applicant_confirmation'):
                subject = "求人応募を受け付けました"
                name = data.get('name', '')
                email_val = data.get('email', '')
                phone_val = data.get('phone', '')
                dob_val = data.get('dob', '') or '未入力'
                address_val = data.get('street_address', '') or '未入力'
                category_val = data.get('recruitment_type_label') or data.get('position') or '採用応募'
                message_val = data.get('cover_letter') or data.get('message') or ''

                body_html = f"""
                <div style="font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif; padding: 20px; line-height: 1.8; color: #333333;">
                    <p style="font-size: 16px; font-weight: bold;">{name} 様</p>
                    <p>この度は、Pacific Boeki の求人にご応募いただき、誠にありがとうございます。</p>
                    <p>ご応募内容および履歴書を正常に受け付けました。<br />
                    採用担当者が内容を確認し、選考を進めさせていただきます。応募内容が募集条件に適している場合は、次の選考についてご連絡いたします。</p>
                    <div style="background: #f9f9f9; border: 1px solid #eeeeee; padding: 16px; border-radius: 6px; margin: 20px 0;">
                        <h4 style="margin-top: 0; color: #c8102e; border-bottom: 1px solid #ddd; padding-bottom: 8px;">応募内容</h4>
                        <p style="margin: 6px 0;"><strong>氏名:</strong> {name}</p>
                        <p style="margin: 6px 0;"><strong>メールアドレス:</strong> {email_val}</p>
                        <p style="margin: 6px 0;"><strong>電話番号:</strong> {phone_val}</p>
                        <p style="margin: 6px 0;"><strong>生年月日:</strong> {dob_val}</p>
                        <p style="margin: 6px 0;"><strong>住所:</strong> {address_val}</p>
                        <p style="margin: 6px 0;"><strong>応募区分:</strong> {category_val}</p>
                        <p style="margin: 6px 0;"><strong>メッセージ:</strong> {message_val}</p>
                        <p style="margin: 6px 0;"><strong>履歴書（PDF）:</strong> 正常に受領しております。</p>
                    </div>
                    <p>この度は、Pacific Boeki にご関心をお寄せいただき、誠にありがとうございます。<br />
                    今後ともどうぞよろしくお願いいたします。</p>
                </div>
                """
            else:
                excluded_keys = ['subject', 'is_applicant_confirmation', 'resume_base64']
                body_html = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px; line-height: 1.6;">
                    <h2 style="color: #c8102e;">Pacific Boeki — {template_code.replace('_', ' ').title()}</h2>
                    <hr style="border: 0; border-top: 1px solid #eeeeee;" />
                    <table style="width: 100%; border-collapse: collapse;">
                """
                for key, val in data.items():
                    if val and key not in excluded_keys:
                        label = key.replace('_', ' ').title()
                        body_html += f"<tr><td style='padding: 8px; font-weight: bold; width: 30%; border-bottom: 1px solid #f0f0f0;'>{label}:</td><td style='padding: 8px; border-bottom: 1px solid #f0f0f0;'>{val}</td></tr>"
                body_html += f"""
                    </table>
                </div>
                {self._get_common_mail_footer(default_email)}
                """

            # Determine email recipient based on template context
            is_customer_facing = template_code in ['welcome_member'] or data.get('is_applicant_confirmation')
            is_job_template = 'job' in template_code or 'recruitment' in template_code

            if recipient_email:
                email_to = recipient_email
            elif is_customer_facing:
                email_to = data.get('email') or default_email
            elif is_job_template:
                email_to = job_email
            else:
                email_to = sales_email

            email_from = f"Pacific Boeki <{default_email}>"
            customer_reply_to = reply_to or data.get('email') or default_email


            attachment_ids = []
            resume_base64 = data.get('resume_base64')
            resume_filename = data.get('resume_filename') or 'resume.pdf'
            if resume_base64:
                try:
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': resume_filename,
                        'datas': resume_base64,
                        'res_model': 'mail.mail',
                        'res_id': 0,
                        'type': 'binary',
                        'mimetype': 'application/pdf',
                    })
                    attachment_ids.append(attachment.id)
                except Exception as att_err:
                    _logger.warning("Failed to create PDF attachment for email: %s", att_err)

            mail_vals = {
                'subject': subject,
                'body_html': body_html,
                'email_to': email_to,
                'email_from': email_from,
                'reply_to': customer_reply_to,
                'state': 'outgoing',
            }

            if attachment_ids:
                mail_vals['attachment_ids'] = [(6, 0, attachment_ids)]

            mail = request.env['mail.mail'].sudo().create(mail_vals)
            mail.send()

            return self._make_json_response({
                'status': 'success',
                'message_id': mail.id,
                'message': _("Email created and queued successfully.")
            })

        except Exception as e:
            _logger.exception("Unexpected error in send_email")
            return self._make_error_response(_("An unexpected error occurred while sending email."), status=500)


    @http.route('/api/v1/website/member/profile', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def member_profile(self, **kwargs):
        """
        API Endpoint: Retrieves or updates the logged-in user's partner profile.
        """
        try:
            if not request.session.uid:
                return self._make_error_response(_("Authentication required."), status=401)

            user = request.env['res.users'].sudo().browse(request.session.uid)
            partner = user.partner_id

            # If request contains parameters, we treat it as an update (matching Next.js POST /api/v1/website/member/profile)
            if kwargs:
                name = kwargs.get('name')
                title = kwargs.get('title')
                company = kwargs.get('company')
                address = kwargs.get('address')
                city = kwargs.get('city')
                province = kwargs.get('province')
                postCode = kwargs.get('postCode')
                country_name = kwargs.get('country')
                phone = kwargs.get('phone')
                is_whatsapp = kwargs.get('isWhatsapp')
                is_viber = kwargs.get('isViber')
                is_line = kwargs.get('isLine')

                partner_vals = {}
                if name:
                    partner_vals['name'] = name
                    user.write({'name': name})
                if phone:
                    partner_vals['phone'] = phone
                    partner_vals['mobile'] = phone
                if address is not None:
                    partner_vals['street'] = address
                if city is not None:
                    partner_vals['city'] = city
                if postCode is not None:
                    partner_vals['zip'] = postCode
                if company is not None:
                    partner_vals['company_name'] = company

                # Map country
                if country_name:
                    country = request.env['res.country'].sudo().search([('name', '=ilike', country_name)], limit=1)
                    if country:
                        partner_vals['country_id'] = country.id

                # Map state (province)
                if province:
                    state_domain = [('name', '=ilike', province)]
                    if partner_vals.get('country_id'):
                        state_domain.append(('country_id', '=', partner_vals['country_id']))
                    elif partner.country_id:
                        state_domain.append(('country_id', '=', partner.country_id.id))
                    state = request.env['res.country.state'].sudo().search(state_domain, limit=1)
                    if state:
                        partner_vals['state_id'] = state.id

                # Map title
                if title:
                    title_rec = request.env['res.partner.title'].sudo().search([('name', '=ilike', title)], limit=1)
                    if title_rec:
                        partner_vals['title'] = title_rec.id

                # Map custom boolean fields
                if 'x_is_whatsapp' in request.env['res.partner']._fields and is_whatsapp is not None:
                    partner_vals['x_is_whatsapp'] = bool(is_whatsapp)
                if 'x_is_viber' in request.env['res.partner']._fields and is_viber is not None:
                    partner_vals['x_is_viber'] = bool(is_viber)
                if 'x_is_line' in request.env['res.partner']._fields and is_line is not None:
                    partner_vals['x_is_line'] = bool(is_line)

                if partner_vals:
                    partner.sudo().write(partner_vals)

            # Return the profile
            return self._make_json_response({
                'name': partner.name or '',
                'title': partner.title.name if partner.title else '',
                'company': partner.company_name or '',
                'address': partner.street or '',
                'city': partner.city or '',
                'province': partner.state_id.name if partner.state_id else '',
                'country': partner.country_id.name if partner.country_id else '',
                'postCode': partner.zip or '',
                'email': partner.email or '',
                'phone': partner.phone or partner.mobile or '',
                'isWhatsapp': getattr(partner, 'x_is_whatsapp', False),
                'isViber': getattr(partner, 'x_is_viber', False),
                'isLine': getattr(partner, 'x_is_line', False),
            })

        except Exception as e:
            _logger.exception("Unexpected error in member_profile")
            return self._make_error_response(_("An unexpected error occurred while processing member profile request."), status=500)

    @http.route('/api/v1/website/member/change-password', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def change_password(self, **kwargs):
        """
        API Endpoint: Updates password for the currently logged-in user.
        """
        try:
            if not request.session.uid:
                return self._make_error_response(_("Authentication required."), status=401)

            old_password = kwargs.get('currentPassword')  # Next.js calls it currentPassword
            new_password = kwargs.get('newPassword')

            if not old_password or not new_password:
                return self._make_error_response(_("Current password and New password are required."), status=400)

            user = request.env['res.users'].sudo().browse(request.session.uid)

            # Check old password
            try:
                user.sudo()._check_credentials(old_password, {'interactive': False})
            except Exception:
                return self._make_error_response(_("Incorrect current password."), status=400)

            # Update password
            user.sudo().write({'password': new_password})

            return self._make_json_response({
                'message': _("Password updated successfully.")
            })

        except Exception as e:
            _logger.exception("Unexpected error in change_password")
            return self._make_error_response(_("An unexpected error occurred while updating password."), status=500)

    @http.route('/api/v1/website/jobs', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def get_jobs(self, **kwargs):
        """
        API Endpoint: Returns active job openings from Odoo pb.job model.
        """
        try:
            records = request.env['pb.job'].sudo().search([('is_active', '=', True)], order='sequence, id')
            jobs = []

            for record in records:
                main_duties = [d.strip() for d in (record.main_duties or "").split('\n') if d.strip()]
                requirements = [r.strip() for r in (record.requirements or "").split('\n') if r.strip()]

                jobs.append({
                    "id": record.id,
                    "title": record.name or "",
                    "description": record.description or record.intro or "",
                    "companyName": record.company_name or "株式会社パシフィック貿易",
                    "address": record.address or "",
                    "industry": record.industry or "自動車",
                    "jobCategory": record.job_category or "full_time",
                    "jobTitle": record.job_title or record.name or "",
                    "employmentType": record.employment_type if hasattr(record, 'employment_type') else ("正社員" if record.job_category == 'full_time' else "パートタイム"),
                    "location": record.location or "東京都渋谷区",
                    "workingHours": record.working_hours or "",
                    "breakTime": record.break_time or "",
                    "salary": record.salary or "",
                    "benefits": record.benefits or "",
                    "workDays": record.work_days or "",
                    "transportAllowance": record.transport_allowance or "",
                    "intro": record.intro or record.description or "",
                    "closingNote": record.closing_note or "",
                    "mainDuties": main_duties,
                    "requirements": requirements
                })

            # If no pb.job records exist in DB yet, fallback to hr.job search or reference jobs
            if not jobs:
                hr_records = request.env['hr.job'].sudo().search([('active', '=', True)])
                for record in hr_records:
                    jobs.append({
                        "id": record.id,
                        "title": record.name or "",
                        "description": record.description or "",
                        "companyName": record.company_id.name if record.company_id else "株式会社パシフィック貿易",
                        "address": record.address_id.contact_address if record.address_id else "東京都渋谷区広尾1-8-9松石ビル201",
                        "industry": "自動車",
                        "jobCategory": "full_time" if "仕入れ" in (record.name or "") else "part_time",
                        "jobTitle": record.name or "",
                        "employmentType": "正社員" if "仕入れ" in (record.name or "") else "パートタイム",
                        "location": record.address_id.city or "東京都渋谷区",
                        "workingHours": "8:00～17:00" if "仕入れ" in (record.name or "") else "10:00～16:00",
                        "salary": "月給20万円～24万円" if "仕入れ" in (record.name or "") else "時給 1,500円",
                        "benefits": "交通費全額支給（上限月20,000円迄） 各種社会保険完備",
                        "intro": record.description or "",
                        "requirements": [
                            "基本的なパソコンスキルとオンラインシステムの使用経験",
                            "社会人経験必須 / 未経験者歓迎"
                        ]
                    })


            # If no hr.job records exist in DB yet, return the standard reference job positions
            if not jobs:
                jobs = [
                    {
                        "id": 1,
                        "title": "仕入れ 募集",
                        "description": "ネットオークションによる中古車の仕入業務を行います。",
                        "requirements": [
                            "簡単なPC操作（インターネットやメールを日頃利用している程度でOK）",
                            "社会人経験必須",
                            "＜学歴不問・未経験者歓迎＞"
                        ],
                        "companyName": "株式会社パシフィック貿易",
                        "address": "東京都渋谷区広尾1-8-9松石ビル201",
                        "industry": "自動車",
                        "jobCategory": "full_time",
                        "jobTitle": "中古車の仕入",
                        "employmentType": "正社員\n＊3か月の試用期間あり。その間はアルバイト雇用（時給1250円）となります。",
                        "location": "東京都渋谷区広尾1-8-9松石ビル201",
                        "workingHours": "8:00～17:00",
                        "salary": "月給20万円～24万円\n※試用期間終了後に、経験、能力などを考慮の上、決定させていただきます。",
                        "benefits": "交通費全額支給（上限月20,000円迄） 各種社会保険完備（雇用、労災等）",
                        "intro": "ネットオークションによる中古車の仕入業務を行います。",
                        "mainDuties": [
                            "ネットオークションによる中古車の仕入業務",
                            "海外クライアントの要望に合った中古車を仕入れていただきます。",
                            "ネット回線によるオークションの為、すべてオフィス内で完結します。",
                            "車種、年式、型番、予算などの要望を受け、出品されている中古車の中から検索していきま"
                        ]
                    },
                    {
                        "id": 2,
                        "title": "パートタイム募集 – 貿易アシスタント",
                        "description": "海外のお客様との取引を担当する貿易部門をサポートするパートタイムスタッフを募集しています。",
                        "requirements": [
                            "基本的なパソコンスキルとオンラインシステムの使用経験",
                            "必要に応じてインターネット検索ができる能力",
                            "細かい作業に注意を払える方、整理整頓が得意な方",
                            "貿易・出荷・物流分野での経験があれば尚可（未経験でも可）"
                        ],
                        "jobCategory": "part_time",
                        "jobTitle": "貿易アシスタント（パートタイム）",
                        "location": "PACIFICBOEKICO., LTD（パシフィック貿易株式会社）東京都渋谷区",
                        "intro": "海外のお客様との取引を担当する貿易部門をサポートするパートタイムスタッフを募集しています。少人数のチームと密に連携しながら、日々の業務を円滑に進め、必要な書類処理を担当していただきます。",
                        "employmentType": "パートタイム",
                        "workingHours": "10:00～16:00（※面接時に柔軟な調整も可能）",
                        "breakTime": "1時間",
                        "salary": "時給 1,500円",
                        "workDays": "週 4日（火曜～金曜）",
                        "transportAllowance": "15,000円/月",
                        "closingNote": "国際的な貿易の現場で実務経験を積みながら、物流・書類作成・顧客対応のスキルを身につける絶好のチャンスです。",
                        "mainDuties": [
                            "輸出車両に関する検査申請をオンラインで提出",
                            "必要書類を海外のお客様へメールで送信",
                            "書類を正確に社内システムへアップロード",
                            "システムでの出荷登録を作成",
                            "陸送会社およびフォワーダーとの配送指示書の確認・フォローアップ",
                            "フォワーダーとの連絡・出荷調整",
                            "その他、一般的な事務業務のサポート"
                        ]
                    }
                ]

            return self._make_json_response(jobs)
        except Exception as e:
            _logger.exception("Unexpected error in get_jobs")
            return self._make_error_response(_("An unexpected error occurred while fetching jobs."), status=500)

    @http.route('/api/v1/website/currencies', type='json', auth='public', methods=['POST', 'GET'], csrf=False, cors='*')
    def get_website_currencies(self, **kwargs):
        """
        API Endpoint: Returns active exchange rates from Odoo res.currency model.
        """
        try:
            currencies = request.env['res.currency'].sudo().search([('active', '=', True)])
            default_live_rates = {
                'USD': 1.0,
                'JPY': 163.83,
                'SLR': 336.21,
                'GBP': 0.75,
                'EUR': 0.88
            }
            rates = dict(default_live_rates)
            currency_list = []

            usd = request.env['res.currency'].sudo().search([('name', '=', 'USD')], limit=1)
            usd_rate = usd.rate if usd and usd.rate > 0 else 1.0

            for curr in currencies:
                code = curr.name.upper()
                if code in ['USD', 'JPY', 'SLR', 'LKR', 'GBP', 'EUR']:
                    rate_val = (curr.rate / usd_rate) if (usd_rate and curr.rate > 0) else 1.0
                    target_code = 'SLR' if code in ['SLR', 'LKR'] else code
                    if rate_val != 1.0 or target_code == 'USD':
                        rates[target_code] = round(rate_val, 4)

            for code, rate in rates.items():
                currency_list.append({
                    'code': code,
                    'symbol': '¥' if code == 'JPY' else ('$' if code == 'USD' else ('SLR ' if code == 'SLR' else ('£' if code == 'GBP' else '€'))),
                    'name': code,
                    'rateToUsd': rate
                })

            return self._make_json_response({
                'base': 'USD',
                'rates': rates,
                'currencies': currency_list
            })
        except Exception as e:
            _logger.exception("Error in get_website_currencies")
            return self._make_error_response(_("An unexpected error occurred while fetching currencies."), status=500)







