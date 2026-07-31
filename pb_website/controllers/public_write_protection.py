# -*- coding: utf-8 -*-
"""
Shared public-write protection boundary for pb_website controllers.

Contact is the first complete consumer. Other public write endpoints should call
``enforce_public_write`` before CRM / email / account side effects.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from odoo.http import request

_logger = logging.getLogger(__name__)

# Risk-appropriate defaults: shared NAT offices can submit a few times; abuse is capped.
DEFAULT_RATE_LIMIT = 8
DEFAULT_RATE_WINDOW_SECONDS = 3600  # 1 hour
DEFAULT_MIN_SCORE = 0.5
SITEVERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'

# In-process token replay ledger (per worker). DB ledger supplements multi-worker.
_TOKEN_REPLAY_CACHE = {}
_TOKEN_REPLAY_TTL = 600  # 10 minutes


class PublicWriteError(Exception):
    def __init__(self, code, message, retry_after_seconds=None, http_status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retry_after_seconds = retry_after_seconds
        self.http_status = http_status

    def to_response_payload(self):
        payload = {
            'message': self.message,
            'code': self.code,
        }
        if self.retry_after_seconds is not None:
            payload['retry_after_seconds'] = self.retry_after_seconds
        return payload


def _icp():
    return request.env['ir.config_parameter'].sudo()


def _get_param(key, default=None):
    value = _icp().get_param(key)
    if value is None or value == '':
        return default
    return value


def _client_ip():
    httpreq = request.httprequest
    forwarded = httpreq.headers.get('X-Forwarded-For') or httpreq.headers.get('X-Real-Ip')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return httpreq.remote_addr or 'unknown'


def _token_fingerprint(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _purge_replay_cache(now=None):
    now = now or time.time()
    expired = [k for k, exp in _TOKEN_REPLAY_CACHE.items() if exp <= now]
    for k in expired:
        _TOKEN_REPLAY_CACHE.pop(k, None)


def _assert_token_not_replayed(token):
    fp = _token_fingerprint(token)
    now = time.time()
    _purge_replay_cache(now)
    if fp in _TOKEN_REPLAY_CACHE:
        raise PublicWriteError(
            'RECAPTCHA_REPLAYED',
            'This verification was already used. Please complete a new check and resubmit.',
        )
    try:
        raw = _get_param('pb_website.recaptcha_used_tokens_json', '{}') or '{}'
        ledger = json.loads(raw)
        if isinstance(ledger, dict):
            ledger = {k: v for k, v in ledger.items() if isinstance(v, (int, float)) and v > now}
            if fp in ledger:
                raise PublicWriteError(
                    'RECAPTCHA_REPLAYED',
                    'This verification was already used. Please complete a new check and resubmit.',
                )
    except PublicWriteError:
        raise
    except Exception as err:
        _logger.debug('Token ledger read skipped: %s', err)


def _mark_token_used(token):
    fp = _token_fingerprint(token)
    now = time.time()
    _purge_replay_cache(now)
    _TOKEN_REPLAY_CACHE[fp] = now + _TOKEN_REPLAY_TTL
    try:
        raw = _get_param('pb_website.recaptcha_used_tokens_json', '{}') or '{}'
        ledger = json.loads(raw)
        if not isinstance(ledger, dict):
            ledger = {}
        ledger = {k: v for k, v in ledger.items() if isinstance(v, (int, float)) and v > now}
        ledger[fp] = now + _TOKEN_REPLAY_TTL
        if len(ledger) > 500:
            items = sorted(ledger.items(), key=lambda kv: kv[1])
            ledger = dict(items[-400:])
        _icp().set_param('pb_website.recaptcha_used_tokens_json', json.dumps(ledger))
    except Exception as err:
        _logger.debug('Token ledger update skipped: %s', err)


def _check_rate_limit(workflow, limit=None, window_seconds=None):
    limit = int(limit if limit is not None else (
        _get_param('pb_website.contact_rate_limit', DEFAULT_RATE_LIMIT) or DEFAULT_RATE_LIMIT
    ))
    window_seconds = int(window_seconds if window_seconds is not None else (
        _get_param('pb_website.contact_rate_window_seconds', DEFAULT_RATE_WINDOW_SECONDS)
        or DEFAULT_RATE_WINDOW_SECONDS
    ))
    ip = _client_ip()
    bucket_key = f'{workflow}:{ip}'
    now = time.time()
    window_start = now - window_seconds

    try:
        raw = _get_param('pb_website.public_write_rate_json', '{}') or '{}'
        store = json.loads(raw)
        if not isinstance(store, dict):
            store = {}
        entries = store.get(bucket_key) or []
        if not isinstance(entries, list):
            entries = []
        entries = [ts for ts in entries if isinstance(ts, (int, float)) and ts >= window_start]
        if len(entries) >= limit:
            oldest = min(entries) if entries else now
            retry_after = max(1, int(oldest + window_seconds - now))
            raise PublicWriteError(
                'RATE_LIMITED',
                'Too many submissions from your network. Please wait a few minutes and try again.',
                retry_after_seconds=retry_after,
                http_status=429,
            )
        entries.append(now)
        store[bucket_key] = entries
        # Prune other stale keys lightly
        if len(store) > 2000:
            store = {k: v for k, v in store.items() if isinstance(v, list) and any(
                isinstance(ts, (int, float)) and ts >= window_start for ts in v
            )}
        _icp().set_param('pb_website.public_write_rate_json', json.dumps(store))
    except PublicWriteError:
        raise
    except Exception as err:
        _logger.warning('Rate limit check failed open to avoid total outage: %s', err)


def _siteverify(token, remoteip=None):
    secret = _get_param('pb_website.recaptcha_secret_key') or _get_param(
        'pb_website.recaptcha_secret'
    )
    if not secret:
        # Fail closed when not configured, unless explicit dev bypass is enabled.
        if _dev_bypass_enabled():
            return {'success': True, 'hostname': 'localhost', 'action': None, 'score': 1.0, 'dev_bypass': True}
        raise PublicWriteError(
            'RECAPTCHA_UNAVAILABLE',
            'Human verification is not configured. Please try again later or use an alternate contact method.',
            http_status=503,
        )

    payload = {'secret': secret, 'response': token}
    if remoteip:
        payload['remoteip'] = remoteip
    data = urlencode(payload).encode('utf-8')
    req = Request(SITEVERIFY_URL, data=data, method='POST')
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    try:
        with urlopen(req, timeout=8) as resp:
            body = resp.read().decode('utf-8')
            return json.loads(body)
    except Exception as err:
        _logger.warning('reCAPTCHA siteverify failed: %s', err)
        raise PublicWriteError(
            'RECAPTCHA_UNAVAILABLE',
            'Human verification service is unavailable. Please retry or use an alternate contact method.',
            http_status=503,
        )


def _dev_bypass_enabled():
    flag = (_get_param('pb_website.recaptcha_dev_bypass') or '').strip().lower()
    return flag in ('1', 'true', 'yes', 'on')


def verify_recaptcha_token(token, expected_action, expected_hostnames=None):
    """
    Verify reCAPTCHA token (v2 checkbox or v3). Raises PublicWriteError on failure.
    """
    token = (token or '').strip()
    if not token:
        raise PublicWriteError(
            'RECAPTCHA_MISSING',
            'Please complete the human verification check and try again.',
        )

    if token in ('BYPASSED', 'DEV_BYPASS'):
        if _dev_bypass_enabled():
            _logger.info('public_write: accepting dev bypass token for action=%s', expected_action)
            return {'success': True, 'dev_bypass': True}
        raise PublicWriteError(
            'RECAPTCHA_MISSING',
            'Please complete the human verification check and try again.',
        )

    # Local replay guard before external call (do not mark until success)
    _assert_token_not_replayed(token)

    result = _siteverify(token, remoteip=_client_ip())
    if not result.get('success'):
        error_codes = result.get('error-codes') or []
        if 'timeout-or-duplicate' in error_codes:
            raise PublicWriteError(
                'RECAPTCHA_REPLAYED',
                'This verification was already used. Please complete a new check and resubmit.',
            )
        if 'invalid-input-response' in error_codes:
            raise PublicWriteError(
                'RECAPTCHA_INVALID',
                'Human verification failed. Please complete the check again and resubmit.',
            )
        raise PublicWriteError(
            'RECAPTCHA_INVALID',
            'Human verification failed. Please complete the check again and resubmit.',
        )

    # Mark only after Google accepted the token (one-time use)
    _mark_token_used(token)

    # Hostname check (v2 + v3)
    hostname = (result.get('hostname') or '').lower()
    allowed = expected_hostnames
    if allowed is None:
        raw_hosts = _get_param('pb_website.recaptcha_allowed_hostnames', '') or ''
        allowed = [h.strip().lower() for h in raw_hosts.split(',') if h.strip()]
    if allowed and hostname and hostname not in allowed and hostname not in (
        'localhost', '127.0.0.1'
    ):
        raise PublicWriteError(
            'RECAPTCHA_WRONG_HOST',
            'Human verification could not be validated for this site. Please refresh and try again.',
        )

    # Action / score (v3); v2 has no action — enforce client-declared action separately
    action = result.get('action')
    if action is not None and expected_action and action != expected_action:
        raise PublicWriteError(
            'RECAPTCHA_WRONG_ACTION',
            'Human verification did not match this form. Please refresh and try again.',
        )

    score = result.get('score')
    if score is not None:
        try:
            min_score = float(_get_param('pb_website.recaptcha_min_score', DEFAULT_MIN_SCORE) or DEFAULT_MIN_SCORE)
        except (TypeError, ValueError):
            min_score = DEFAULT_MIN_SCORE
        if float(score) < min_score:
            raise PublicWriteError(
                'RECAPTCHA_INVALID',
                'Human verification failed. Please complete the check again and resubmit.',
            )

    return result


def enforce_public_write(kwargs, expected_action, rate_limit=None, rate_window_seconds=None):
    """
    Shared gate for public write endpoints.

    Reads ``recaptcha_token`` / ``g-recaptcha-response`` and ``recaptcha_action``
    from kwargs. Raises PublicWriteError on failure (caller maps to error response).
    """
    token = (
        kwargs.get('recaptcha_token')
        or kwargs.get('g-recaptcha-response')
        or kwargs.get('captcha_token')
        or ''
    )
    action = (kwargs.get('recaptcha_action') or expected_action or '').strip()
    if expected_action and action and action != expected_action:
        raise PublicWriteError(
            'RECAPTCHA_WRONG_ACTION',
            'Human verification did not match this form. Please refresh and try again.',
        )

    _check_rate_limit(
        workflow=expected_action or 'public_write',
        limit=rate_limit,
        window_seconds=rate_window_seconds,
    )
    verify_recaptcha_token(token, expected_action=expected_action)
    return True


def resolve_contact_email_policy():
    """
    Server-owned Contact email template + internal recipient.
    Client-provided recipient / template values must be ignored by callers.
    """
    ir_config = _icp()
    default_email = ir_config.get_param('pb_website.default_email') or 'info@pacificboeki.jp'
    sales_email = ir_config.get_param('pb_website.default_email_sales') or default_email
    return {
        'template_code': 'contact_us',
        'email_to': sales_email,
        'email_from': default_email,
        # Client may not override these
        'allow_client_recipient': False,
        'allow_client_template': False,
    }
