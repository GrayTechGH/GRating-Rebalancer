#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

from calibre_plugins.GRating_Rebalancer.results import BookInput, RunReport


READ_ONLY_IDENTIFIERS = {'grrating', 'grvotes'}
GRATING_IDENTIFIER_SEARCH = 'identifiers:=grrating:'
NO_GRATING_IDENTIFIER_WARNING = (
    'No grrating identifiers were found in this library.',
    'To enable them, open Preferences > Metadata download, select the '
    'Goodreads metadata source, and click Configure selected source.',
    'In the Goodreads source options, enable "Get precise rating into '
    '\'grrating\' identifier" and "Get #votes for rating into \'grvotes\' '
    'identifier", then download metadata again for the affected books.',
)
OUTPUT_FIELD_DATATYPES = {
    'percentile': {'float', 'int', 'text'},
}
RATING_FIELD_DATATYPES = {
    'percentile': {'float', 'int', 'text'},
    'decimal': {'float', 'text'},
    'range': {'float', 'int', 'text'},
    'stars_whole': {'rating'},
    'stars_half': {'rating'},
}
BLOCKED_CUSTOM_COLUMN_DATATYPES = {'bool', 'composite', 'datetime', 'series'}


def selected_book_ids(gui):
    library_view = getattr(gui, 'library_view', None)
    if library_view is None:
        return []
    selection_model = library_view.selectionModel()
    if selection_model is None:
        return []
    rows = selection_model.selectedRows()
    if not rows:
        return []
    model = library_view.model()
    return [model.id(row) for row in rows]


def selected_books_are_selected(gui):
    library_view = getattr(gui, 'library_view', None)
    if library_view is None:
        return False
    selection_model = library_view.selectionModel()
    if selection_model is None:
        return False
    has_selection = getattr(selection_model, 'hasSelection', None)
    if callable(has_selection):
        try:
            return bool(has_selection())
        except Exception:
            pass
    try:
        return bool(selection_model.selectedRows())
    except Exception:
        return False


def all_book_ids(db):
    if hasattr(db, 'all_book_ids'):
        return list(db.all_book_ids())
    new_api = getattr(db, 'new_api', None)
    if new_api is not None and hasattr(new_api, 'all_book_ids'):
        return list(new_api.all_book_ids())
    data = getattr(db, 'data', None)
    if data is not None and hasattr(data, 'books'):
        return list(data.books)
    return []


def get_metadata(db, book_id):
    if hasattr(db, 'get_proxy_metadata'):
        return db.get_proxy_metadata(book_id)
    new_api = getattr(db, 'new_api', None)
    if new_api is not None and hasattr(new_api, 'get_proxy_metadata'):
        return new_api.get_proxy_metadata(book_id)
    return db.get_metadata(book_id, index_is_id=True)


def has_grating_identifier(db):
    search_ids = grating_identifier_search_ids(db)
    return bool(search_ids)


def grating_identifier_search_ids(db):
    for source in search_sources(db):
        method = getattr(source, 'search_getting_ids', None)
        if not callable(method):
            continue
        ids = call_search_getting_ids(method, GRATING_IDENTIFIER_SEARCH)
        if ids is not None:
            return ids
    return None


def search_sources(db):
    sources = [db]
    new_api = getattr(db, 'new_api', None)
    if new_api is not None:
        sources.append(new_api)
    data = getattr(db, 'data', None)
    if data is not None:
        sources.append(data)
    return sources


def call_search_getting_ids(method, query):
    call_shapes = (
        lambda: method(
            query,
            restriction='',
            sort_results=False,
            use_virtual_library=False,
        ),
        lambda: method(query, '', False, False),
        lambda: method(query, ''),
        lambda: method(query),
    )
    for call in call_shapes:
        try:
            return set(call())
        except TypeError:
            continue
        except Exception:
            return None
    return None


def load_library_inputs(db, debug_callback=None):
    books = []
    report = RunReport()
    series_keys = series_search_keys(db)
    debug_enabled = debug_callback is not None
    series_source_counts = {} if debug_enabled else None
    series_index_counts = {} if debug_enabled else None
    for book_id in all_book_ids(db):
        mi = get_metadata(db, book_id)
        rating = parse_float(identifier_value(mi, 'grrating'))
        if rating is None:
            report.skipped_missing_ratings += 1
            continue
        if rating < 0.0 or rating > 5.0:
            report.skipped_invalid_ratings += 1
            continue
        votes = parse_int(identifier_value(mi, 'grvotes'))
        series_value, series_index, series_source = series_value_and_index_with_source(
            mi,
            series_keys,
        )
        if debug_enabled and series_source:
            series_source_counts[series_source] = (
                series_source_counts.get(series_source, 0) + 1
            )
            if series_index is not None:
                series_index_counts[series_source] = (
                    series_index_counts.get(series_source, 0) + 1
                )
        books.append(BookInput(
            book_id=book_id,
            rating=rating,
            votes=votes,
            series=series_value,
            series_index=series_index,
        ))
    report.processed_books = len(all_book_ids(db))
    report.valid_ratings = len(books)
    if (
        report.processed_books > 0
        and report.skipped_missing_ratings == report.processed_books
    ):
        report.warnings.extend(NO_GRATING_IDENTIFIER_WARNING)
    if debug_callback:
        debug_callback(
            'input processed={} valid={} missing={} invalid={} series_keys={} '
            'series_sources={} indexed_sources={}'.format(
                report.processed_books,
                report.valid_ratings,
                report.skipped_missing_ratings,
                report.skipped_invalid_ratings,
                ','.join(series_keys) or '-',
                compact_counts(series_source_counts),
                compact_counts(series_index_counts),
            )
        )
    return books, report


def identifier_value(mi, key):
    identifiers = metadata_identifiers(mi)
    if identifiers is None:
        return None
    normalized = str(key).strip().lower()
    for candidate in (key, normalized):
        try:
            value = identifiers.get(candidate, None)
        except Exception:
            value = None
        if value is not None:
            return value
    return None


def metadata_identifiers(mi):
    if mi is None:
        return None
    if hasattr(mi, 'get_identifiers'):
        try:
            identifiers = mi.get_identifiers()
        except Exception:
            identifiers = None
        if identifiers is not None:
            return identifiers
    identifiers = getattr(mi, 'identifiers', None)
    if callable(identifiers):
        try:
            identifiers = identifiers()
        except Exception:
            return None
    return identifiers


def metadata_value(mi, key):
    if mi is None:
        return None
    if hasattr(mi, 'get'):
        try:
            value = mi.get(key, None)
        except TypeError:
            try:
                value = mi.get(key)
            except Exception:
                value = None
        if value is not None:
            return value
    if hasattr(mi, key):
        return getattr(mi, key)
    if hasattr(mi, 'metadata_for_field'):
        try:
            return mi.metadata_for_field(key)
        except Exception:
            return None
    return None


def series_search_key(db):
    prefs = getattr(db, 'prefs', None)
    if prefs is None:
        return 'series'
    if hasattr(prefs, 'get'):
        try:
            value = prefs.get('similar_series_search_key', 'series')
        except Exception:
            return 'series'
        if value is None or value == '':
            return 'series'
        return value
    return 'series'


def series_search_keys(db):
    keys = []

    def add_key(key):
        if key and key not in keys:
            keys.append(key)

    preferred_key = series_search_key(db)
    expanded_keys = grouped_search_key_members(db, preferred_key)
    if expanded_keys:
        for key in expanded_keys:
            add_key(key)
    else:
        add_key(preferred_key)
    add_key('series')

    field_metadata = get_field_metadata(db)
    if field_metadata is None:
        return keys
    for lookup_name in iter_field_keys(field_metadata):
        try:
            metadata = field_metadata[lookup_name]
        except Exception:
            continue
        if clean_datatype(metadata) == 'series':
            add_key(lookup_name)
    return keys


def grouped_search_key_members(db, key):
    if not key:
        return []
    prefs = getattr(db, 'prefs', None)
    if prefs is None or not hasattr(prefs, 'get'):
        return []
    grouped_terms = None
    for pref_key in ('grouped_search_terms', 'grouped_search_terms_map'):
        try:
            grouped_terms = prefs.get(pref_key, None)
        except Exception:
            grouped_terms = None
        if grouped_terms is not None and hasattr(grouped_terms, 'get'):
            break
    if not hasattr(grouped_terms, 'get'):
        return []
    value = grouped_terms.get(key, None)
    if value is None:
        value = grouped_terms.get(str(key).lower(), None)
    return split_grouped_search_value(value)


def split_grouped_search_value(value):
    if value is None:
        return []
    if isinstance(value, str):
        candidates = value.split(',')
    elif isinstance(value, (tuple, list)):
        candidates = value
    else:
        return []
    keys = []
    for candidate in candidates:
        key = str(candidate).strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def series_value_and_index(mi, series_key):
    value, index, source = series_value_and_index_with_source(mi, series_key)
    return value, index


def series_value_and_index_with_source(mi, series_key):
    if isinstance(series_key, (tuple, list)):
        return best_series_value_and_index(mi, series_key)
    value, index = series_value_and_index_for_key(mi, series_key)
    source = series_key if value is not None or index is not None else None
    return value, index, source


def best_series_value_and_index(mi, series_keys):
    first_partial = (None, None, None)
    for key in series_keys:
        value, index = series_value_and_index_for_key(mi, key)
        if value is not None and index is not None:
            return value, index, key
        if (
            first_partial == (None, None, None)
            and (value is not None or index is not None)
        ):
            first_partial = (value, index, key)
    return first_partial


def series_value_and_index_for_key(mi, series_key):
    if not series_key:
        return None, None
    if series_key == 'series':
        value, bundled_index = split_series_value(metadata_value(mi, 'series'))
        index = parse_float(metadata_value(mi, 'series_index'))
        if index is None:
            index = bundled_index
        return cleanup_series(value), index

    value, bundled_index = split_series_value(metadata_value(mi, series_key))
    index = parse_float(metadata_value(mi, series_key + '_index'))
    if index is None:
        index = bundled_index
    if index is None and series_key.startswith('#'):
        index = parse_float(metadata_value(mi, series_key[1:] + '_index'))
    return cleanup_series(value), index


def split_series_value(value):
    if isinstance(value, (tuple, list)):
        series = value[0] if len(value) > 0 else None
        index = parse_float(value[1]) if len(value) > 1 else None
        return series, index
    if isinstance(value, dict):
        series = (
            value.get('series')
            or value.get('name')
            or value.get('value')
            or value.get('#value#')
        )
        index = parse_float(
            value.get('series_index')
            or value.get('index')
            or value.get('#extra#')
        )
        return series, index
    if isinstance(value, str):
        return split_series_text(value)
    return value, None


def split_series_text(value):
    text = value.strip()
    if text.endswith(']') and '[' in text:
        series, possible_index = text.rsplit('[', 1)
        index = parse_float(possible_index[:-1])
        if index is not None:
            return series.strip(), index
    return value, None


def validate_output_fields(db, settings):
    errors = []
    output_fields = [
        settings.output_percentile_field,
        settings.adjusted_rating_field,
    ]
    if not settings.output_percentile_field:
        errors.append('Select an output field.')
    if (
        settings.output_percentile_field
        and settings.adjusted_rating_field
        and settings.output_percentile_field == settings.adjusted_rating_field
    ):
        errors.append('Select different fields for Output and Rating.')

    for field in output_fields:
        if not field:
            continue
        normalized = field.strip().lower()
        if normalized in READ_ONLY_IDENTIFIERS:
            errors.append('{} is a read-only input identifier.'.format(field))
        if field_exists(db, field) is False:
            errors.append('{} does not exist in the current library.'.format(field))
    if field_is_compatible(
        db,
        settings.output_percentile_field,
        'output',
        'percentile',
    ) is False:
        errors.append(
            '{} is not compatible with raw percentile output.'.format(
                settings.output_percentile_field
            )
        )
    if field_is_compatible(
        db,
        settings.adjusted_rating_field,
        'rating',
        settings.output_format,
    ) is False:
        errors.append(
            '{} is not compatible with the selected Rating type.'.format(
                settings.adjusted_rating_field
            )
        )
    if settings.output_format == 'range' and settings.number_max <= settings.number_min:
        errors.append('The output range maximum must be greater than the minimum.')
    return errors


def field_exists(db, field):
    field_metadata = getattr(db, 'field_metadata', None)
    if field_metadata is None:
        new_api = getattr(db, 'new_api', None)
        field_metadata = getattr(new_api, 'field_metadata', None)
    if field_metadata is None:
        return None
    try:
        return field in field_metadata
    except Exception:
        return None


def field_is_compatible(db, field, role, output_format):
    if not field:
        return None
    field_metadata = get_field_metadata(db)
    if field_metadata is None:
        return None
    try:
        metadata = field_metadata[field]
    except Exception:
        return None
    datatype = clean_datatype(metadata)
    if not datatype:
        return None
    return (
        datatype in compatible_datatypes(role, output_format)
        and not field_is_blocked_custom_target(
            metadata,
            role,
            output_format,
            field,
            field_metadata,
        )
    )


def field_datatype(db, field):
    if not field:
        return ''
    metadata = field_metadata_for(db, field)
    if metadata is None:
        return ''
    return clean_datatype(metadata)


def field_metadata_for(db, field):
    field_metadata = get_field_metadata(db)
    if field_metadata is None:
        return None
    try:
        return field_metadata[field]
    except Exception:
        return None


def field_display_name(db, field):
    field = str(field or '').strip()
    if not field:
        return ''
    metadata = field_metadata_for(db, field)
    if metadata is None:
        return field
    return clean_field_heading(field, metadata)


def rating_field_supports_half_stars(db, field):
    metadata = field_metadata_for(db, field)
    if metadata is None or clean_datatype(metadata) != 'rating':
        return True
    value = metadata_value_from_mapping(metadata, 'allow_half_stars', None)
    if value is None:
        display = metadata_value_from_mapping(metadata, 'display', {})
        value = metadata_value_from_mapping(display, 'allow_half_stars', None)
    if value is None:
        return True
    return bool_from_metadata(value)


def compatible_custom_columns(db, role, output_format):
    field_metadata = get_field_metadata(db)
    if field_metadata is None:
        return []

    fields = []
    for lookup_name in iter_field_keys(field_metadata):
        try:
            metadata = field_metadata[lookup_name]
        except Exception:
            continue
        if (
            not is_custom_field(lookup_name, metadata)
            and not is_builtin_rating_target(lookup_name, metadata, role)
        ):
            continue
        if str(lookup_name).strip().lower() in READ_ONLY_IDENTIFIERS:
            continue
        datatype = clean_datatype(metadata)
        if datatype not in compatible_datatypes(role, output_format):
            continue
        if field_is_blocked_custom_target(
            metadata,
            role,
            output_format,
            lookup_name,
            field_metadata,
        ):
            continue
        fields.append({
            'lookup_name': lookup_name,
            'label': field_label(lookup_name, metadata),
            'datatype': datatype,
        })
    return sorted(fields, key=compatible_field_sort_key)


def compatible_field_sort_key(field):
    if str(field.get('lookup_name', '')).strip().lower() == 'rating':
        return (0, '')
    return (1, str(field.get('label', '')).lower())


def is_builtin_rating_target(lookup_name, metadata, role):
    return (
        role == 'rating'
        and str(lookup_name).strip().lower() == 'rating'
        and clean_datatype(metadata) == 'rating'
    )


def get_field_metadata(db):
    field_metadata = getattr(db, 'field_metadata', None)
    if field_metadata is None:
        new_api = getattr(db, 'new_api', None)
        field_metadata = getattr(new_api, 'field_metadata', None)
    return field_metadata


def iter_field_keys(field_metadata):
    try:
        return list(field_metadata)
    except Exception:
        try:
            return list(field_metadata.keys())
        except Exception:
            return []


def is_custom_field(lookup_name, metadata):
    if str(lookup_name).startswith('#'):
        return True
    if hasattr(metadata, 'get'):
        return bool(metadata.get('is_custom', False))
    return False


def clean_datatype(metadata):
    if hasattr(metadata, 'get'):
        return str(metadata.get('datatype', '') or '').strip().lower()
    return str(getattr(metadata, 'datatype', '') or '').strip().lower()


def metadata_value_from_mapping(metadata, key, default=None):
    if metadata is None:
        return default
    if hasattr(metadata, 'get'):
        try:
            return metadata.get(key, default)
        except Exception:
            return default
    return getattr(metadata, key, default)


def bool_from_metadata(value):
    if isinstance(value, str):
        return value.strip().lower() not in ('', '0', 'false', 'no', 'none')
    return bool(value)


def field_is_blocked_custom_target(
    metadata,
    role,
    output_format,
    lookup_name=None,
    field_metadata=None,
):
    datatype = clean_datatype(metadata)
    if datatype in BLOCKED_CUSTOM_COLUMN_DATATYPES:
        return True
    if field_is_series_index_column(lookup_name, field_metadata):
        return True
    if role == 'output' and datatype == 'rating':
        return True
    if role == 'rating' and datatype == 'rating':
        return output_format not in ('stars_whole', 'stars_half')
    if role == 'rating' and datatype == 'int':
        return output_format == 'stars_half'
    if datatype == 'text' and field_is_multiple_text_column(metadata):
        return True
    return False


def field_is_series_index_column(lookup_name, field_metadata):
    lookup = str(lookup_name or '').strip()
    if not lookup:
        return False
    normalized = lookup.lower()
    if normalized == 'series_index':
        return True
    if not normalized.endswith('_index'):
        return False
    base_lookup = lookup[:-6]
    candidates = [base_lookup]
    if base_lookup.startswith('#'):
        candidates.append(base_lookup[1:])
    else:
        candidates.append('#' + base_lookup)
    for candidate in candidates:
        metadata = metadata_for_lookup(field_metadata, candidate)
        if metadata is not None and clean_datatype(metadata) == 'series':
            return True
    return False


def metadata_for_lookup(field_metadata, lookup_name):
    if field_metadata is None:
        return None
    try:
        return field_metadata[lookup_name]
    except Exception:
        return None


def field_is_multiple_text_column(metadata):
    if hasattr(metadata, 'get'):
        return bool(metadata.get('is_multiple', False))
    return bool(getattr(metadata, 'is_multiple', False))


def compatible_datatypes(role, output_format):
    if role == 'output':
        return OUTPUT_FIELD_DATATYPES['percentile']
    if role == 'rating':
        return RATING_FIELD_DATATYPES.get(
            output_format,
            RATING_FIELD_DATATYPES['percentile'],
        )
    return OUTPUT_FIELD_DATATYPES.get(
        output_format,
        OUTPUT_FIELD_DATATYPES['percentile'],
    )


def field_label(lookup_name, metadata):
    heading = clean_field_heading(lookup_name, metadata)
    if heading != str(lookup_name):
        return '{} ({})'.format(heading, lookup_name)
    return heading


def clean_field_heading(lookup_name, metadata):
    name = None
    if hasattr(metadata, 'get'):
        name = (
            metadata.get('name')
            or metadata.get('label')
            or metadata.get('column_heading')
        )
    else:
        name = (
            getattr(metadata, 'name', None)
            or getattr(metadata, 'label', None)
            or getattr(metadata, 'column_heading', None)
        )
    if name:
        return str(name)
    return str(lookup_name)


def write_outputs(db, output_by_field):
    failures = []
    for field, values in output_by_field.items():
        if not field or not values:
            continue
        try:
            set_field(db, field, values_for_field_write(db, field, values))
        except Exception as err:
            for book_id in values:
                failures.append((book_id, '{}: {}'.format(field, err)))
    return failures


def values_for_field_write(db, field, values):
    if field_datatype(db, field) != 'rating':
        return values
    return {
        book_id: calibre_rating_value(value)
        for book_id, value in values.items()
    }


def calibre_rating_value(value):
    try:
        stars = float(value)
    except (TypeError, ValueError):
        return None
    stars = max(0.0, min(5.0, stars))
    return int(round(stars * 2.0))


def set_field(db, field, values):
    if hasattr(db, 'set_field'):
        return db.set_field(field, values)
    new_api = getattr(db, 'new_api', None)
    if new_api is not None and hasattr(new_api, 'set_field'):
        return new_api.set_field(field, values)
    raise RuntimeError('Calibre database does not support set_field().')


def parse_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value):
    if value is None:
        return None
    text = str(value).strip().replace(',', '')
    if not text:
        return None
    try:
        number = int(float(text))
    except ValueError:
        return None
    if number < 0:
        return None
    return number


def cleanup_series(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def compact_counts(counts):
    if not counts:
        return '-'
    parts = []
    for key in sorted(counts):
        parts.append('{}:{}'.format(key, counts[key]))
    return ','.join(parts)
