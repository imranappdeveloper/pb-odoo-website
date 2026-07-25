# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class ShippingSchedule(models.Model):
    _name = 'shipping.schedule'
    _description = 'Vessel Shipping Schedule Header'
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Schedule Title', compute='_compute_name', store=True)
    carrier_id = fields.Many2one('shipping.carrier', string='Carrier', required=True, ondelete='restrict')
    vessel_id = fields.Many2one('shipping.vessel', string='Vessel', required=True, ondelete='restrict')
    voyage_no = fields.Char(string='Voyage Number', required=True)
    revision_no = fields.Char(string='Revision', default='REV00', required=True, help='e.g., REV00, REV01')
    issue_date = fields.Date(string='Issue Date')
    trade_lane = fields.Char(string='Trade Lane', default='Japan to East Africa')
    cargo_restrictions = fields.Text(string='Cargo Restrictions & Notes', help='e.g., No Pure EV/Hydrogen; Hybrid/PHEV allowed; NKKK required for tank trucks.')
    allow_ev = fields.Boolean(string='Allow Pure EV', default=False)
    allow_hybrid = fields.Boolean(string='Allow Hybrid/PHEV', default=True)
    require_nkkk = fields.Boolean(string='Require NKKK/SK Certificate', default=True)
    active = fields.Boolean(default=True)
    
    line_ids = fields.One2many('shipping.schedule.line', 'schedule_id', string='Port Calls', copy=True)
    
    # Concurrency & Lock management
    lock_version = fields.Integer(string='Lock Version', default=1, readonly=True, help='Optimistic concurrency control token')

    _sql_constraints = [
        ('carrier_vessel_voyage_uniq', 'unique(carrier_id, vessel_id, voyage_no)', 
         'A schedule for this Carrier, Vessel, and Voyage Number already exists!')
    ]

    @api.depends('carrier_id.name', 'vessel_id.name', 'voyage_no', 'revision_no')
    def _compute_name(self):
        for rec in self:
            carrier = rec.carrier_id.name if rec.carrier_id else ''
            vessel = rec.vessel_id.name if rec.vessel_id else ''
            voyage = rec.voyage_no or ''
            rev = f"({rec.revision_no})" if rec.revision_no else ''
            rec.name = f"{carrier} - {vessel} {voyage} {rev}".strip()

    def write(self, vals):
        """Override write to increment lock_version for concurrency tracking."""
        if 'lock_version' not in vals:
            vals['lock_version'] = self.lock_version + 1
        return super(ShippingSchedule, self).write(vals)

    def action_open_import_wizard(self):
        """Action button to launch Excel Import Wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Import / Update Schedule from Excel',
            'res_model': 'shipping.schedule.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_schedule_id': self.id,
                'default_carrier_id': self.carrier_id.id,
                'default_vessel_id': self.vessel_id.id,
                'default_voyage_no': self.voyage_no,
            }
        }


class ShippingScheduleLine(models.Model):
    _name = 'shipping.schedule.line'
    _description = 'Shipping Schedule Port Call Line'
    _order = 'sequence asc, id asc'

    schedule_id = fields.Many2one('shipping.schedule', string='Schedule', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    call_type = fields.Selection([
        ('pol', 'Port of Loading (POL)'),
        ('pod', 'Port of Discharge (POD)')
    ], string='Call Type', required=True, default='pol')
    port_id = fields.Many2one('shipping.port', string='Port', required=True, ondelete='restrict')
    
    eta = fields.Date(string='ETA (Estimated Arrival)')
    etd = fields.Date(string='ETD (Estimated Departure)')
    eta_end = fields.Date(string='ETA End Date', help='End date for multi-day window e.g. 08-19 to 08-22')
    etd_end = fields.Date(string='ETD End Date')
    
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped / No Call'),
        ('delayed', 'Delayed')
    ], string='Status', default='scheduled', required=True)
    remarks = fields.Char(string='Remarks')
