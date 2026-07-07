# -*- coding: utf-8 -*-
{
    'name': 'Pacific Boeki Website API & Core',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'API endpoints and custom models for Pacific Boeki Next.js website integration.',
    'description': """
This module defines custom Odoo models (news, testimonials, shipping rates/schedules)
and JSON-RPC controllers to expose catalog data to the Next.js static website.
""",
    'author': 'Antigravity / Pacific Boeki',
    'depends': ['product', 'ls_product', 'ls_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/testimonial_views.xml',
        'views/news_views.xml',
        'views/freight_rate_views.xml',
        'views/team_member_views.xml',
        'views/recruitment_inquiry_views.xml',
        'views/menus.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
