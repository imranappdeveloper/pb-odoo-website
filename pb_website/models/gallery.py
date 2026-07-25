# -*- coding: utf-8 -*-

from odoo import models, fields

class PbGallery(models.Model):
    _name = 'pb.gallery'
    _description = 'Website Photo Gallery'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    image = fields.Image(string='Image', required=True)
    image_medium = fields.Image(string='Thumbnail', max_width=300, max_height=300, compute='_compute_image_medium', store=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)

    def _compute_image_medium(self):
        for record in self:
            if record.image:
                record.image_medium = record.image
            else:
                record.image_medium = False
