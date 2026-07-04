# -*- coding: utf-8 -*-

from odoo import models, fields

class PbTestimonial(models.Model):
    _name = 'pb.testimonial'
    _description = 'Customer Testimonial'
    _order = 'id desc'

    name = fields.Char(string='Name', required=True)
    country = fields.Char(string='Country')
    rating = fields.Integer(string='Rating', default=5)
    text = fields.Text(string='Text')
    photo = fields.Image(string='Photo')
