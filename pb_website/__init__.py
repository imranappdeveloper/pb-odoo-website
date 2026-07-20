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
    _logger.info("Executing post_init_hook: Seeding testimonials, news, and team members...")

    module_dir = os.path.dirname(__file__)
    seed_dir = os.path.join(module_dir, 'data', 'seed')

    # 1. Seed Testimonials
    testimonial_model = env['pb.testimonial']
    if not testimonial_model.search_count([]):
        json_path = os.path.join(seed_dir, 'testimonials.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        vals = {
                            'name': item['name'] or "Anonymous Customer",
                            'country': item['country'],
                            'rating': item['rating'],
                            'text': item['text'],
                        }
                        photo_name = os.path.basename(item['photoUrl'])
                        img_path = os.path.join(seed_dir, 'images', photo_name)
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
        json_path = os.path.join(seed_dir, 'news.json')
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
                        img_path = os.path.join(seed_dir, 'images', img_name)
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

    # 3. Seed Team Members
    team_model = env['pb.team_member']
    if not team_model.search_count([]):
        try:
            team_model.create({
                'name': 'Kenji Tanaka',
                'role': 'Sales Director',
                'display_order': 10
            })
            team_model.create({
                'name': 'Sarah Jenkins',
                'role': 'Customer Relationship Manager',
                'display_order': 20
            })
            team_model.create({
                'name': 'Muhammad Ali',
                'role': 'Logistics Coordinator',
                'display_order': 30
            })
            _logger.info("Successfully seeded pb.team_member model")
        except Exception as e:
            _logger.error("Failed to seed team members: %s", str(e))
    else:
        _logger.info("pb.team_member records already exist, skipping seeding")

    # 4. Seed Banners
    banner_model = env['pb.banner']
    if not banner_model.search_count([]):
        json_path = os.path.join(seed_dir, 'banners.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        vals = {
                            'name': item['name'],
                            'sequence': item.get('sequence', 10),
                            'is_active': item.get('is_active', True),
                            'title': item.get('title'),
                            'subtitle': item.get('subtitle'),
                            'url': item.get('url'),
                        }
                        img_name = item.get('image')
                        if img_name:
                            img_path = os.path.join(seed_dir, 'images', img_name)
                            if os.path.exists(img_path):
                                with open(img_path, 'rb') as img_f:
                                    vals['image'] = base64.b64encode(img_f.read())
                        banner_model.create(vals)
                _logger.info("Successfully seeded pb.banner model")
            except Exception as e:
                _logger.error("Failed to seed banners: %s", str(e))
        else:
            _logger.warning("Banners mock JSON file not found at %s", json_path)
    else:
        _logger.info("pb.banner records already exist, skipping seeding")



