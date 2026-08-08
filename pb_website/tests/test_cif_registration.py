# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase
from odoo.addons.pb_website.controllers import main as main_controller
from odoo.addons.pb_website.controllers.main import WebsiteCatalogController


class TestCifRegistration(TransactionCase):

    def setUp(self):
        super(TestCifRegistration, self).setUp()
        self.controller = WebsiteCatalogController()

        # Create mock request object and patch main_controller.request with new=mock_request
        mock_request = MagicMock()
        mock_request.env = self.env
        mock_request.session = MagicMock(uid=None, sid='test_session_id')

        self.request_patcher = patch.object(main_controller, 'request', new=mock_request)
        self.request_patcher.start()
        self.addCleanup(self.request_patcher.stop)


        # Patch enforce_public_write to pass during tests
        self.pw_patcher = patch.object(main_controller, 'enforce_public_write', return_value=True)
        self.pw_patcher.start()
        self.addCleanup(self.pw_patcher.stop)

        # Ensure test countries exist
        self.country_japan = self.env['res.country'].sudo().search([('code', '=', 'JP')], limit=1)
        if not self.country_japan:
            self.country_japan = self.env['res.country'].sudo().create({'name': 'Japan', 'code': 'JP'})

        self.country_kenya = self.env['res.country'].sudo().search([('code', '=', 'KE')], limit=1)
        if not self.country_kenya:
            self.country_kenya = self.env['res.country'].sudo().create({'name': 'Kenya', 'code': 'KE'})

        self.country_france = self.env['res.country'].sudo().search([('code', '=', 'FR')], limit=1)
        if not self.country_france:
            self.country_france = self.env['res.country'].sudo().create({'name': 'France', 'code': 'FR'})

    def test_01_get_cif_countries(self):
        """Test GET /api/v1/website/cif-countries returns active CIF countries."""
        # Clean existing cif.country for deterministic testing
        self.env['cif.country'].sudo().search([]).unlink()

        # Create active CIF country for Kenya
        cif_ke = self.env['cif.country'].sudo().create({
            'country_id': self.country_kenya.id,
            'active': True,
        })
        # Create inactive CIF country for France
        cif_fr = self.env['cif.country'].sudo().create({
            'country_id': self.country_france.id,
            'active': False,
        })

        res = self.controller.get_cif_countries()
        self.assertEqual(res['status'], 'success')

        data = res['data']
        country_ids = [item['country_id'] for item in data]
        self.assertIn(self.country_kenya.id, country_ids)
        self.assertNotIn(self.country_france.id, country_ids)

        kenya_item = next(item for item in data if item['country_id'] == self.country_kenya.id)
        self.assertEqual(kenya_item['id'], cif_ke.id)
        self.assertEqual(kenya_item['name'], self.country_kenya.name)
        self.assertEqual(kenya_item['code'], 'KE')

    def test_02_registration_with_cif_country_by_name(self):
        """Test registration with CIF country name configures special proforma & fixed fee."""
        cif_ke = self.env['cif.country'].sudo().search([('country_id', '=', self.country_kenya.id)])
        if not cif_ke:
            self.env['cif.country'].sudo().create({
                'country_id': self.country_kenya.id,
                'active': True,
            })
        else:
            cif_ke.sudo().write({'active': True})

        email = 'cif_user_kenya@example.com'
        res = self.controller.register(
            name='Kenya Buyer',
            email=email,
            password='Password123!',
            country='Kenya',
            phone='+254700000000',
        )

        self.assertEqual(res['status'], 'success', msg=str(res))
        partner_id = res['data']['partner_id']
        partner = self.env['res.partner'].sudo().browse(partner_id)

        self.assertTrue(partner.is_special_proforma_invoice)

        settings = self.env['auction.partner.settings'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        self.assertTrue(settings.exists())
        self.assertEqual(settings.fee_type, 'fixed')

    def test_03_registration_with_cif_country_by_code_and_id(self):
        """Test registration resolving CIF country by code ('KE') and numeric ID."""
        cif_ke = self.env['cif.country'].sudo().search([('country_id', '=', self.country_kenya.id)])
        if not cif_ke:
            self.env['cif.country'].sudo().create({
                'country_id': self.country_kenya.id,
                'active': True,
            })

        # By code
        res_code = self.controller.register(
            name='Kenya Buyer Code',
            email='cif_user_code@example.com',
            password='Password123!',
            country='KE',
            phone='+254700000001',
        )
        self.assertEqual(res_code['status'], 'success')
        partner_code = self.env['res.partner'].sudo().browse(res_code['data']['partner_id'])
        self.assertTrue(partner_code.is_special_proforma_invoice)
        settings_code = self.env['auction.partner.settings'].sudo().search([('partner_id', '=', partner_code.id)], limit=1)
        self.assertEqual(settings_code.fee_type, 'fixed')

        # By ID
        res_id = self.controller.register(
            name='Kenya Buyer ID',
            email='cif_user_id@example.com',
            password='Password123!',
            country=str(self.country_kenya.id),
            phone='+254700000002',
        )
        self.assertEqual(res_id['status'], 'success')
        partner_id = self.env['res.partner'].sudo().browse(res_id['data']['partner_id'])
        self.assertTrue(partner_id.is_special_proforma_invoice)
        settings_id = self.env['auction.partner.settings'].sudo().search([('partner_id', '=', partner_id.id)], limit=1)
        self.assertEqual(settings_id.fee_type, 'fixed')

    def test_04_registration_with_non_cif_country(self):
        """Test registration with non-CIF country retains standard defaults."""
        self.env['cif.country'].sudo().search([('country_id', '=', self.country_france.id)]).unlink()

        res = self.controller.register(
            name='France Buyer',
            email='non_cif_user@example.com',
            password='Password123!',
            country='France',
            phone='+33100000000',
        )

        self.assertEqual(res['status'], 'success', msg=str(res))
        partner = self.env['res.partner'].sudo().browse(res['data']['partner_id'])
        self.assertFalse(partner.is_special_proforma_invoice)

        settings = self.env['auction.partner.settings'].sudo().search([('partner_id', '=', partner.id)], limit=1)
        self.assertTrue(settings.exists())
        self.assertEqual(settings.fee_type, 'percentage')
