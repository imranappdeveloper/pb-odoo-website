# -*- coding: utf-8 -*-

from . import models
from . import controllers

import os
import json
import base64
import logging

_logger = logging.getLogger(__name__)

def post_init_hook(env):
    """
    Automatic seeding function that runs when the pb_website module is installed.
    """
    _logger.info("Executing post_init_hook: Seeding testimonials and news...")

    module_dir = os.path.dirname(__file__)
    workspace_dir = os.path.abspath(os.path.join(module_dir, '..', '..', '..', 'PB-Web'))
    
    if not os.path.exists(workspace_dir):
        workspace_dir = '/Users/imran/Documents/projects/PB/PB-Web'

    # 1. Seed Testimonials
    testimonial_model = env['pb.testimonial']
    if not testimonial_model.search_count([]):
        json_path = os.path.join(workspace_dir, 'public', 'mock', 'testimonials.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        vals = {
                            'name': item['name'],
                            'country': item['country'],
                            'rating': item['rating'],
                            'text': item['text'],
                        }
                        photo_name = os.path.basename(item['photoUrl'])
                        img_path = os.path.join(workspace_dir, 'public', 'images', 'scraped', photo_name)
                        if os.path.exists(img_path):
                            with open(img_path, 'rb') as img_f:
                                vals['photo'] = base64.b64encode(img_f.read())
                        testimonial_model.create(vals)
                _logger.info("Successfully seeded pb.testimonial model")
            except Exception as e:
                _logger.error("Failed to seed testimonials: %s", str(e))
        else:
            _logger.warning("Testimonials mock JSON file not found at %s", json_path)
    else:
        _logger.info("pb.testimonial records already exist, skipping seeding")

    # 2. Seed News
    news_model = env['pb.news']
    if not news_model.search_count([]):
        json_path = os.path.join(workspace_dir, 'public', 'mock', 'news.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        vals = {
                            'title': item['title'],
                            'body': item['body'],
                            'date': item['date'],
                            'published': item['published'],
                        }
                        img_name = os.path.basename(item['thumbnail'])
                        img_path = os.path.join(workspace_dir, 'public', 'images', 'scraped', img_name)
                        if os.path.exists(img_path):
                            with open(img_path, 'rb') as img_f:
                                vals['thumbnail'] = base64.b64encode(img_f.read())
                        news_model.create(vals)
                _logger.info("Successfully seeded pb.news model")
            except Exception as e:
                _logger.error("Failed to seed news: %s", str(e))
        else:
            _logger.warning("News mock JSON file not found at %s", json_path)
    else:
        _logger.info("pb.news records already exist, skipping seeding")
