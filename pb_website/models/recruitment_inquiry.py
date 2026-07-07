# -*- coding: utf-8 -*-

from odoo import models, fields

class PbRecruitmentInquiry(models.Model):
    _name = 'pb.recruitment_inquiry'
    _description = 'Recruitment Inquiry'
    _order = 'submission_date desc, id desc'

    name = fields.Char(string='Name', required=True)
    phone = fields.Char(string='Phone No.', required=True)
    email = fields.Char(string='Email', required=True)
    dob = fields.Date(string='Date of Birth')
    street_address = fields.Char(string='Street Address')
    message = fields.Text(string='Message', required=True)
    recruitment_type = fields.Selection([
        ('career', 'Career Recruitment'),
        ('local', 'Local Career Recruitment'),
        ('agent', 'Local Agent / Contract')
    ], string='Recruitment Type', default='career', required=True)
    resume = fields.Binary(string='Resume (PDF)', required=True)
    resume_filename = fields.Char(string='Resume Filename')
    state = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('closed', 'Closed')
    ], string='Status', default='new')
    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now)
