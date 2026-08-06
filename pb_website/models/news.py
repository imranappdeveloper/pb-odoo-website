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
    is_special = fields.Boolean(string='Special News / Hero Headline', default=False, help='If checked, this article headline will render prominently in the homepage search hero header banner.')

