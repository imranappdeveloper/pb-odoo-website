# -*- coding: utf-8 -*-

from odoo import models, fields

class PbTeamMember(models.Model):
    _name = 'pb.team_member'
    _description = 'Team Member'
    _order = 'display_order, id'

    name = fields.Char(string='Name', required=True)
    role = fields.Char(string='Role/Position', required=True)
    photo = fields.Image(string='Photo')
    display_order = fields.Integer(string='Display Order', default=10)
    active = fields.Boolean(string='Active', default=True)
