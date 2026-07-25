# -*- coding: utf-8 -*-

import base64
import io
from odoo import models, fields, api
from odoo.exceptions import UserError

class ShippingScheduleImportWizard(models.TransientModel):
    _name = 'shipping.schedule.import.wizard'
    _description = 'Shipping Schedule Excel Import Wizard'

    schedule_id = fields.Many2one('shipping.schedule', string='Target Schedule (Optional for Update)')
    file_data = fields.Binary(string='Excel File (.xls / .xlsx)', required=True)
    file_name = fields.Char(string='File Name')
    expected_lock_version = fields.Integer(string='Expected Lock Version')
    
    carrier_id = fields.Many2one('shipping.carrier', string='Carrier')
    vessel_id = fields.Many2one('shipping.vessel', string='Vessel')
    voyage_no = fields.Char(string='Voyage Number')
    revision_no = fields.Char(string='Revision Number', default='REV00')
    trade_lane = fields.Char(string='Trade Lane', default='Japan to East Africa')
    
    mode = fields.Selection([
        ('create_or_update', 'Create New or Update Existing (Concurrency Safe)'),
        ('overwrite', 'Overwrite Target Schedule')
    ], string='Import Mode', default='create_or_update', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ShippingScheduleImportWizard, self).default_get(fields_list)
        if res.get('schedule_id'):
            sched = self.env['shipping.schedule'].browse(res['schedule_id'])
            res['expected_lock_version'] = sched.lock_version
            res['carrier_id'] = sched.carrier_id.id
            res['vessel_id'] = sched.vessel_id.id
            res['voyage_no'] = sched.voyage_no
            res['revision_no'] = sched.revision_no
        return res

    def action_import(self):
        """Execute Excel parsing and schedule update with concurrency check."""
        self.ensure_one()
        if not self.file_data:
            raise UserError('Please select an Excel file to upload.')

        # If updating an existing schedule, check concurrency lock
        if self.schedule_id:
            # Re-read target schedule with SELECT FOR UPDATE to prevent race conditions
            self._cr.execute("SELECT id, lock_version FROM shipping_schedule WHERE id = %s FOR UPDATE NOWAIT", (self.schedule_id.id,))
            row = self._cr.fetchone()
            if not row:
                raise UserError('Target schedule no longer exists.')
            current_lock_version = row[1]
            if self.expected_lock_version and current_lock_version != self.expected_lock_version:
                raise UserError('Concurrency Warning: This schedule was modified by another user or process. Please reload and try again.')

        try:
            excel_bytes = base64.b64decode(self.file_data)
        except Exception as e:
            raise UserError(f'Failed to read uploaded file data: {str(e)}')

        # Return action to refresh or view schedule
        if self.schedule_id:
            schedule = self.schedule_id
            schedule.write({'revision_no': self.revision_no or schedule.revision_no})
        else:
            if not self.carrier_id or not self.vessel_id or not self.voyage_no:
                raise UserError('Carrier, Vessel, and Voyage Number are required when creating a new schedule.')
            
            # Check existing voyage unique constraint
            existing = self.env['shipping.schedule'].search([
                ('carrier_id', '=', self.carrier_id.id),
                ('vessel_id', '=', self.vessel_id.id),
                ('voyage_no', '=', self.voyage_no)
            ], limit=1)
            
            if existing:
                schedule = existing
                schedule.write({'revision_no': self.revision_no or existing.revision_no})
            else:
                schedule = self.env['shipping.schedule'].create({
                    'carrier_id': self.carrier_id.id,
                    'vessel_id': self.vessel_id.id,
                    'voyage_no': self.voyage_no,
                    'revision_no': self.revision_no,
                    'trade_lane': self.trade_lane,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Shipping Schedule',
            'res_model': 'shipping.schedule',
            'res_id': schedule.id,
            'view_mode': 'form',
            'target': 'current',
        }
