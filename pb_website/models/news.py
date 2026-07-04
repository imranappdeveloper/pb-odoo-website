# -*- coding: utf-8 -*-

from odoo import models, fields

class PbNews(models.Model):
    _name = 'pb.news'
    _description = 'Latest News'
    _order = 'date desc, id desc'

    title = fields.Char(string='Title', required=True)
    body = fields.Html(string='Body')
    thumbnail = fields.Image(string='Thumbnail')
    date = fields.Date(string='Published Date', default=fields.Date.context_today)
    published = fields.Boolean(string='Published', default=True)
