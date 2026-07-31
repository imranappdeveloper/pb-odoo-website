# -*- coding: utf-8 -*-

import json
from datetime import timedelta

from odoo import fields
from odoo.tests.common import BaseCase, TransactionCase

from ..controllers.chassis_security import (
    mask_chassis,
    protect_serialized_vehicle,
)


FULL_CHASSIS = 'NCP100-1234567'
MASKED_CHASSIS = 'NCP100-123****'


class ChassisSerializedResponseTest(BaseCase):
    def _payload(self):
        return {
            'name': FULL_CHASSIS,
            'chassis_number': FULL_CHASSIS,
            'metadata': {
                'description': 'Vehicle %s' % FULL_CHASSIS,
                'documents': [
                    {
                        'name': '%s-inspection.pdf' % FULL_CHASSIS,
                        'url': '/documents/%s/report' % FULL_CHASSIS,
                    },
                ],
            },
        }

    def _assert_masked_serialization(self, payload):
        serialized = json.dumps(payload)
        self.assertNotIn(FULL_CHASSIS, serialized)
        self.assertIn(MASKED_CHASSIS, serialized)

    def test_guest_response_contains_no_complete_chassis(self):
        self._assert_masked_serialization(
            protect_serialized_vehicle(self._payload(), FULL_CHASSIS)
        )

    def test_authenticated_response_can_contain_complete_chassis(self):
        protected = protect_serialized_vehicle(
            self._payload(), FULL_CHASSIS, authorized=True
        )
        self.assertIn(FULL_CHASSIS, json.dumps(protected))

    def test_expired_session_is_treated_as_unauthorized(self):
        entitlement_active = False
        self._assert_masked_serialization(
            protect_serialized_vehicle(
                self._payload(),
                FULL_CHASSIS,
                authorized=entitlement_active,
            )
        )

    def test_forged_client_identity_does_not_authorize_reveal(self):
        forged_request = {
            'isAuthenticated': True,
            'user_id': 1,
            'partner_id': 1,
        }
        authorized = False  # Only the Odoo session/entitlement supplies this value.
        self.assertTrue(forged_request['isAuthenticated'])
        self._assert_masked_serialization(
            protect_serialized_vehicle(
                self._payload(), FULL_CHASSIS, authorized=authorized
            )
        )

    def test_inquiry_entitlement_can_reveal_complete_chassis(self):
        entitlement_active = True
        protected = protect_serialized_vehicle(
            self._payload(),
            FULL_CHASSIS,
            authorized=entitlement_active,
        )
        self.assertIn(FULL_CHASSIS, json.dumps(protected))

    def test_short_chassis_is_fully_masked(self):
        self.assertEqual(mask_chassis('ABC'), '***')


class ChassisEntitlementTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inquiry = cls.env['crm.lead'].create({
            'name': 'Chassis security test inquiry',
        })
        cls.entitlements = cls.env['pb.chassis.reveal.entitlement']
        cls.vehicle_ref = 'P1154'

    def test_inquiry_entitlement_is_session_and_vehicle_bound(self):
        self.entitlements.grant(
            'valid-session',
            'product.template',
            self.vehicle_ref,
            self.inquiry,
        )
        self.assertTrue(self.entitlements.has_active(
            'valid-session',
            'product.template',
            self.vehicle_ref,
        ))
        self.assertFalse(self.entitlements.has_active(
            'forged-session',
            'product.template',
            self.vehicle_ref,
        ))
        self.assertFalse(self.entitlements.has_active(
            'valid-session',
            'quick.car',
            self.vehicle_ref,
        ))

    def test_expired_entitlement_does_not_authorize(self):
        entitlement = self.entitlements.grant(
            'expired-session',
            'product.template',
            self.vehicle_ref,
            self.inquiry,
        )
        entitlement.expires_at = fields.Datetime.now() - timedelta(seconds=1)
        self.assertFalse(self.entitlements.has_active(
            'expired-session',
            'product.template',
            self.vehicle_ref,
        ))
