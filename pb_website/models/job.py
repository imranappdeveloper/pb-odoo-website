# -*- coding: utf-8 -*-

from odoo import models, fields

class PbJob(models.Model):
    _name = 'pb.job'
    _description = 'Website Job Opening'
    _order = 'sequence, id'

    name = fields.Char(string='Listing Title', required=True)
    job_title = fields.Char(string='Job Title / Position')
    company_name = fields.Char(string='Company Name', default='株式会社パシフィック貿易')
    address = fields.Char(string='Address')
    industry = fields.Char(string='Industry', default='自動車')
    job_category = fields.Selection([
        ('full_time', 'Full Time (正社員)'),
        ('part_time', 'Part Time (パートタイム)'),
    ], string='Job Category', default='full_time', required=True)
    location = fields.Char(string='Work Location')
    working_hours = fields.Char(string='Working Hours')
    break_time = fields.Char(string='Break Time')
    salary = fields.Char(string='Salary')
    benefits = fields.Text(string='Benefits & Welfare')
    work_days = fields.Char(string='Work Days')
    transport_allowance = fields.Char(string='Transportation Allowance')
    intro = fields.Text(string='Introduction / Overview')
    description = fields.Text(string='Description')
    main_duties = fields.Text(string='Main Duties (One per line)')
    requirements = fields.Text(string='Requirements (One per line)')
    closing_note = fields.Text(string='Closing Note')
    is_active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
