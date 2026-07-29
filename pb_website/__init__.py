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

    # 5. Seed Job Openings (pb.job)
    job_model = env['pb.job']
    if not job_model.search_count([]):
        try:
            job_model.create({
                'name': '仕入れ 募集',
                'job_title': '中古車の仕入',
                'company_name': '株式会社パシフィック貿易',
                'address': '東京都渋谷区広尾1-8-9松石ビル201',
                'industry': '自動車',
                'job_category': 'full_time',
                'location': '東京都渋谷区広尾1-8-9松石ビル201',
                'working_hours': '8:00～17:00',
                'salary': '月給20万円～24万円',
                'benefits': '交通費全額支給（上限月20,000円迄） 各種社会保険完備（雇用、労災等）',
                'intro': 'ネットオークションによる中古車の仕入業務を行います。',
                'description': 'ネットオークションによる中古車の仕入業務 , 海外クライアントの要望に合った中古車を仕入れていただきます。',
                'main_duties': "ネットオークションによる中古車の仕入業務\n海外クライアントの要望に合った中古車を仕入れていただきます。\nネット回線によるオークションの為、すべてオフィス内で完結します。\n車種、年式、型番、予算などの要望を受け、出品されている中古車の中から検索していきます",
                'requirements': "簡単なPC操作（インターネットやメールを日頃利用している程度でOK）\n社会人経験必須\n＜学歴不問・未経験者歓迎＞",
                'sequence': 10,
                'is_active': True,
            })
            job_model.create({
                'name': 'パートタイム募集 – 貿易アシスタント',
                'job_title': '貿易アシスタント（パートタイム）',
                'company_name': 'PACIFICBOEKICO., LTD（パシフィック貿易株式会社）',
                'industry': '貿易部門',
                'job_category': 'part_time',
                'location': '東京都渋谷区',
                'working_hours': '10:00～16:00（※面接時に柔軟な調整も可能）',
                'break_time': '1時間',
                'salary': '時給 1,500円',
                'work_days': '週 4日（火曜～金曜）',
                'transport_allowance': '15,000円/月',
                'intro': '海外のお客様との取引を担当する貿易部門をサポートするパートタイムスタッフを募集しています。少人数のチームと密に連携しながら、日々の業務を円滑に進め、必要な書類処理を担当していただきます。',
                'main_duties': "輸出車両に関する検査申請をオンラインで提出\n必要書類を海外のお客様へメールで送信\n書類を正確に社内システムへアップロード\nシステムでの出荷登録を作成\n陸送会社およびフォワーダーとの配送指示書の確認・フォローアップ\nフォワーダーとの連絡・出荷調整\nその他、一般的な事務業務のサポート",
                'requirements': "基本的なパソコンスキルとオンラインシステムの使用経験\n必要に応じてインターネット検索ができる能力\n細かい作業に注意を払える方、整理整頓が得意な方\n貿易・出荷・物流分野での経験があれば尚可（未経験でも可）",
                'closing_note': '国際的な貿易の現場で実務経験を積みながら、物流・書類作成・顧客対応のスキルを身につける絶好のチャンスです。',
                'sequence': 20,
                'is_active': True,
            })
            _logger.info("Successfully seeded pb.job model")
        except Exception as e:
            _logger.error("Failed to seed jobs: %s", str(e))
    else:
        _logger.info("pb.job records already exist, skipping seeding")

    # 6. Seed System Parameters
    try:
        config_param = env['ir.config_parameter'].sudo()
        if not config_param.get_param('pb_website.default_email'):
            config_param.set_param('pb_website.default_email', 'info@pacificboeki.jp')
        if not config_param.get_param('pb_website.default_email_sales'):
            config_param.set_param('pb_website.default_email_sales', 'sales@pacificboeki.jp')
        if not config_param.get_param('pb_website.default_email_job'):
            config_param.set_param('pb_website.default_email_job', 'careers@pacificboeki.jp')
        _logger.info("Successfully checked/seeded pb_website email system parameters")
    except Exception as e:
        _logger.error("Failed to seed email system parameters: %s", str(e))





