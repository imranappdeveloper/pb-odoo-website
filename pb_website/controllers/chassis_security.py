# -*- coding: utf-8 -*-

import re


CHASSIS_FIELD_NAMES = {
    'chassis',
    'chassis_no',
    'chassis_number',
    'name',
    'vin',
}


def mask_chassis(value):
    """Mask the final four chassis characters without exposing short values."""
    text = str(value or '').strip()
    if not text:
        return ''
    if len(text) <= 4:
        return '*' * len(text)
    return '%s****' % text[:-4]


def protect_serialized_vehicle(value, chassis_number, authorized=False):
    """
    Remove a full chassis value from every string in a serialized response.

    Replacing substrings (rather than selected fields only) also protects nested
    metadata, document names, and URLs.
    """
    chassis = str(chassis_number or '').strip()
    if authorized or not chassis:
        return value

    masked = mask_chassis(chassis)

    if isinstance(value, str):
        return re.sub(re.escape(chassis), masked, value, flags=re.IGNORECASE)
    if isinstance(value, list):
        return [
            protect_serialized_vehicle(item, chassis, authorized=False)
            for item in value
        ]
    if isinstance(value, tuple):
        return tuple(
            protect_serialized_vehicle(item, chassis, authorized=False)
            for item in value
        )
    if isinstance(value, dict):
        return {
            key: protect_serialized_vehicle(item, chassis, authorized=False)
            for key, item in value.items()
        }
    return value
