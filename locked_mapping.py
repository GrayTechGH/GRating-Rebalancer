#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

from datetime import datetime
import os

from calibre_plugins.GRating_Rebalancer.percentiles import (
    build_score_percentile_curve,
)
from calibre_plugins.GRating_Rebalancer.scoring import encode_position_inflation


MAPPING_VERSION = 1
LOCKED_MAPPING_PREF = 'locked_percentile_mapping'
LOCKED_MAPPINGS_BY_LIBRARY_PREF = 'locked_percentile_mappings_by_library'
MAPPING_MODE_PREF = 'percentile_mapping_mode'
MAPPING_MODES_BY_LIBRARY_PREF = 'percentile_mapping_modes_by_library'
PER_LIBRARY_MAPPING_PREF = 'per_library_mapping_enabled'
DEFAULT_MAPPING_MODE = 'recalculate_each_run'
USE_LOCKED_MAPPING_MODE = 'use_locked_mapping'
REBUILD_AND_LOCK_MODE = 'rebuild_and_lock'


def load_locked_mapping(prefs, db=None):
    mapping = raw_locked_mapping(prefs, db)
    if isinstance(mapping, dict) and mapping.get('mapping_version') == MAPPING_VERSION:
        return mapping
    return None


def raw_locked_mapping(prefs, db=None):
    library_key = active_library_mapping_key(prefs, db)
    if library_key:
        mappings = pref_dict(prefs, LOCKED_MAPPINGS_BY_LIBRARY_PREF)
        return mappings.get(library_key, None)
    return pref_get(prefs, LOCKED_MAPPING_PREF, None)


def clear_locked_mapping(prefs, db=None):
    set_locked_mapping(prefs, {}, db)


def set_locked_mapping(prefs, mapping, db=None):
    library_key = active_library_mapping_key(prefs, db)
    if library_key:
        mappings = dict(pref_dict(prefs, LOCKED_MAPPINGS_BY_LIBRARY_PREF))
        mappings[library_key] = mapping
        prefs[LOCKED_MAPPINGS_BY_LIBRARY_PREF] = mappings
        return
    prefs[LOCKED_MAPPING_PREF] = mapping


def locked_mapping_is_present(prefs, db=None):
    return load_locked_mapping(prefs, db) is not None


def get_percentile_mapping_mode(prefs, db=None):
    library_key = active_library_mapping_key(prefs, db)
    if library_key:
        modes = pref_dict(prefs, MAPPING_MODES_BY_LIBRARY_PREF)
        return clean_mapping_mode(modes.get(library_key, DEFAULT_MAPPING_MODE))
    return clean_mapping_mode(pref_get(prefs, MAPPING_MODE_PREF, DEFAULT_MAPPING_MODE))


def set_percentile_mapping_mode(prefs, mode, db=None):
    mode = clean_mapping_mode(mode)
    library_key = active_library_mapping_key(prefs, db)
    if library_key:
        modes = dict(pref_dict(prefs, MAPPING_MODES_BY_LIBRARY_PREF))
        modes[library_key] = mode
        prefs[MAPPING_MODES_BY_LIBRARY_PREF] = modes
        return
    prefs[MAPPING_MODE_PREF] = mode


def active_library_mapping_key(prefs, db=None):
    if not bool(pref_get(prefs, PER_LIBRARY_MAPPING_PREF, False)):
        return ''
    return library_mapping_key(db)


def library_mapping_key(db):
    for source in library_path_sources(db):
        path = path_value(source)
        if path:
            return normalize_library_path(path)
    return ''


def library_path_sources(db):
    if db is None:
        return []
    sources = [db]
    for parent_name in ('new_api', 'backend'):
        parent = getattr(db, parent_name, None)
        if parent is not None:
            sources.append(parent)
            backend = getattr(parent, 'backend', None)
            if backend is not None:
                sources.append(backend)
    return sources


def path_value(source):
    for name in ('library_path',):
        value = getattr(source, name, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if value:
            return value
    return ''


def normalize_library_path(path):
    text = str(path or '').strip()
    if not text:
        return ''
    try:
        text = os.path.abspath(os.path.normpath(text))
    except Exception:
        text = os.path.normpath(text)
    return os.path.normcase(text)


def seed_library_mapping_from_global(prefs, db=None):
    library_key = active_library_mapping_key(prefs, db)
    if not library_key:
        return False
    global_mapping = load_locked_mapping(prefs, None)
    if not global_mapping:
        return False
    mappings = dict(pref_dict(prefs, LOCKED_MAPPINGS_BY_LIBRARY_PREF))
    if library_key in mappings and mappings.get(library_key):
        return False
    mappings[library_key] = dict(global_mapping)
    prefs[LOCKED_MAPPINGS_BY_LIBRARY_PREF] = mappings
    modes = dict(pref_dict(prefs, MAPPING_MODES_BY_LIBRARY_PREF))
    modes[library_key] = USE_LOCKED_MAPPING_MODE
    prefs[MAPPING_MODES_BY_LIBRARY_PREF] = modes
    return True


def build_mapping(scores, position_inflation, settings, source):
    source_scores = []
    for score in scores.values():
        if source == 'raw_rating':
            source_scores.append(score.rating)
        else:
            source_scores.append(score.series_adjusted_rating)

    return {
        'mapping_version': MAPPING_VERSION,
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'source': source,
        'series_correction_enabled': settings.series_correction_enabled,
        'correction_strength': settings.correction_strength,
        'retention_factor': settings.retention_factor,
        'max_retention_penalty': settings.max_retention_penalty,
        'book_count': len(source_scores),
        'locked_curve_anchor_count': settings.locked_curve_anchor_count,
        'locked_curve_endpoint_gap_fraction': (
            settings.locked_curve_endpoint_gap_fraction
        ),
        'score_percentile_curve': build_score_percentile_curve(
            source_scores,
            settings.locked_curve_anchor_count,
            settings.locked_curve_endpoint_gap_fraction,
        ),
        'position_inflation': encode_position_inflation(position_inflation),
        'settings_fingerprint': settings_fingerprint(settings, source),
    }


def save_locked_mapping(prefs, scores, position_inflation, settings, source, db=None):
    mapping = build_mapping(scores, position_inflation, settings, source)
    set_locked_mapping(prefs, mapping, db)
    return mapping


def settings_fingerprint(settings, source):
    return '|'.join([
        str(MAPPING_VERSION),
        str(source),
        '{:.6f}'.format(settings.retention_factor),
        '{:.6f}'.format(settings.max_retention_penalty),
    ])


def locked_mapping_is_compatible(mapping, settings, source):
    if not mapping:
        return False
    if mapping.get('mapping_version') != MAPPING_VERSION:
        return False
    if not mapping.get('score_percentile_curve'):
        return False
    return True


def pref_get(prefs, key, default=None):
    try:
        return prefs[key]
    except Exception:
        pass
    if hasattr(prefs, 'get'):
        try:
            return prefs.get(key, default)
        except Exception:
            return default
    return default


def pref_dict(prefs, key):
    value = pref_get(prefs, key, {})
    if isinstance(value, dict):
        return value
    return {}


def clean_mapping_mode(value):
    value = str(value or '').strip()
    if value in (
        DEFAULT_MAPPING_MODE,
        USE_LOCKED_MAPPING_MODE,
        REBUILD_AND_LOCK_MODE,
    ):
        return value
    return DEFAULT_MAPPING_MODE
