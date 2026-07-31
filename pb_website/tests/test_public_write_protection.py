# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests.common import BaseCase

from ..controllers import main as main_controller
from ..controllers import public_write_protection
from ..controllers.main import WebsiteCatalogController
from ..controllers.public_write_protection import (
    PublicWriteError,
    enforce_public_write,
)


class PublicWriteProtectionTest(BaseCase):
    def test_contact_controller_gates_before_validation_side_effects(self):
        controller = WebsiteCatalogController()
        blocked = PublicWriteError(
            'RECAPTCHA_MISSING',
            'Please complete the human verification check and try again.',
        )
        with patch.object(main_controller, 'enforce_public_write', side_effect=blocked) as gate:
            result = controller.contact(
                name='Test Buyer',
                email='buyer@example.com',
                msg='Hello',
                recaptcha_action='contact',
            )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['data']['code'], 'RECAPTCHA_MISSING')
        gate.assert_called_once_with({'name': 'Test Buyer', 'email': 'buyer@example.com', 'msg': 'Hello', 'recaptcha_action': 'contact'}, expected_action='contact')

    def test_inquiry_controller_gates_before_lead_creation(self):
        controller = WebsiteCatalogController()
        blocked = PublicWriteError(
            'RECAPTCHA_MISSING',
            'Please complete the human verification check and try again.',
        )
        with patch.object(main_controller, 'enforce_public_write', side_effect=blocked) as gate, patch.object(
            controller,
            '_find_inquiry_vehicle',
            side_effect=AssertionError('lead path reached before public-write gate'),
        ):
            result = controller.submit_vehicle_inquiry(
                name='Test Buyer',
                email='buyer@example.com',
                message='Interested',
                vehicleRef='P123',
                recaptcha_action='vehicle_inquiry',
            )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['data']['code'], 'RECAPTCHA_MISSING')
        gate.assert_called_once_with(
            {
                'name': 'Test Buyer',
                'email': 'buyer@example.com',
                'message': 'Interested',
                'vehicleRef': 'P123',
                'recaptcha_action': 'vehicle_inquiry',
            },
            expected_action='vehicle_inquiry',
        )

    def test_quote_controller_uses_server_owned_quote_action(self):
        controller = WebsiteCatalogController()
        blocked = PublicWriteError(
            'RECAPTCHA_MISSING',
            'Please complete the human verification check and try again.',
        )
        with patch.object(main_controller, 'enforce_public_write', side_effect=blocked) as gate:
            result = controller.submit_vehicle_quote(
                name='Test Buyer',
                email='buyer@example.com',
                message='Quote please',
                vehicleRef='P123',
                recaptcha_action='vehicle_inquiry',
            )

        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['data']['code'], 'RECAPTCHA_MISSING')
        gate.assert_called_once_with(
            {
                'name': 'Test Buyer',
                'email': 'buyer@example.com',
                'message': 'Quote please',
                'vehicleRef': 'P123',
                'recaptcha_action': 'vehicle_inquiry',
            },
            expected_action='quote',
        )

    def test_missing_token_is_rejected(self):
        with patch.object(public_write_protection, '_check_rate_limit'):
            with self.assertRaisesRegex(PublicWriteError, 'human verification') as ctx:
                enforce_public_write({}, expected_action='contact')

        self.assertEqual(ctx.exception.code, 'RECAPTCHA_MISSING')

    def test_wrong_action_is_rejected_before_side_effect_gate(self):
        with patch.object(public_write_protection, '_check_rate_limit') as rate_limit, patch.object(
            public_write_protection, 'verify_recaptcha_token'
        ) as verify:
            with self.assertRaises(PublicWriteError) as ctx:
                enforce_public_write(
                    {
                        'recaptcha_token': 'valid-token',
                        'recaptcha_action': 'quote',
                    },
                    expected_action='contact',
                )

        self.assertEqual(ctx.exception.code, 'RECAPTCHA_WRONG_ACTION')
        rate_limit.assert_not_called()
        verify.assert_not_called()

    def test_verified_token_passes_contact_boundary(self):
        with patch.object(public_write_protection, '_check_rate_limit') as rate_limit, patch.object(
            public_write_protection, 'verify_recaptcha_token'
        ) as verify:
            self.assertTrue(
                enforce_public_write(
                    {
                        'recaptcha_token': 'valid-token',
                        'recaptcha_action': 'contact',
                    },
                    expected_action='contact',
                )
            )

        rate_limit.assert_called_once_with(
            workflow='contact', limit=None, window_seconds=None
        )
        verify.assert_called_once_with('valid-token', expected_action='contact')
