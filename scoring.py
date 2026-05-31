#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

import math
from collections import defaultdict

from calibre_plugins.GRating_Rebalancer.percentiles import calculate_percentiles
from calibre_plugins.GRating_Rebalancer.results import BookScore, RunReport


RETENTION_75_100 = 0
RETENTION_50_75 = 1
RETENTION_25_50 = 2
RETENTION_0_25 = 3
RETENTION_BUCKETS = (
    RETENTION_75_100,
    RETENTION_50_75,
    RETENTION_25_50,
    RETENTION_0_25,
)
RETENTION_BUCKET_LABELS = {
    RETENTION_75_100: '75-100',
    RETENTION_50_75: '50-75',
    RETENTION_25_50: '25-50',
    RETENTION_0_25: '0-25',
}
HIGH_BOOK1_RETENTION_MULTIPLIER = 0.75
MID_BOOK1_RETENTION_MULTIPLIER = 1.50
LOW_BOOK1_RETENTION_MULTIPLIER = 1.75
VERY_LOW_LATER_BOOK1_RETENTION_MULTIPLIER = 1.25
VERY_LOW_PREVIOUS_RETENTION_MULTIPLIER = 0.25
MAX_POSITION_BIAS_MULTIPLIER = LOW_BOOK1_RETENTION_MULTIPLIER


def bucket_series_index(series_index):
    if series_index is None:
        return None
    value = float(series_index)
    if value < 1.0:
        return None
    if value >= 6.0:
        return 6
    if value == int(value):
        return int(value)
    return min(6, int(math.floor(value)) + 1)


def previous_whole_bucket(series_index):
    if series_index is None:
        return None
    value = float(series_index)
    if value < 1.0:
        return None
    return max(1, min(6, int(math.floor(value))))


def has_vote_count(book):
    return book.votes is not None and book.votes > 0


def group_by_series(books):
    groups = defaultdict(list)
    for book in books:
        if book.series:
            groups[book.series].append(book)
    return groups


def choose_book_one(series_books):
    candidates = [
        book for book in series_books
        if book.series_index is not None and float(book.series_index) == 1.0
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda book: book.votes if book.votes is not None else -1,
        reverse=True,
    )[0]


def choose_previous_whole_book(series_books, book):
    if book.series_index is None:
        return None
    value = float(book.series_index)
    if value <= 1.0:
        return None
    target = int(math.floor(value))
    if value == float(target):
        target -= 1
    if target < 1:
        return None
    candidates = [
        candidate for candidate in series_books
        if (
            candidate.series_index is not None
            and float(candidate.series_index) == float(target)
        )
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.votes if candidate.votes is not None else -1
        ),
        reverse=True,
    )[0]


def learn_position_inflation(series_groups, raw_percentiles, debug_callback=None):
    debug_enabled = debug_callback is not None
    weighted_deltas = defaultdict(float)
    weights = defaultdict(float)
    bucket_pairs = defaultdict(int)
    bucket_delta_stats = defaultdict(new_delta_stats) if debug_enabled else None
    book1_retention_delta_stats = (
        defaultdict(new_delta_stats) if debug_enabled else None
    )
    book1_retention_weighted_deltas = defaultdict(float) if debug_enabled else None
    book1_retention_weights = defaultdict(float) if debug_enabled else None
    book1_retention_missing = defaultdict(int) if debug_enabled else None
    prev_retention_delta_stats = (
        defaultdict(new_delta_stats) if debug_enabled else None
    )
    prev_retention_weighted_deltas = defaultdict(float) if debug_enabled else None
    prev_retention_weights = defaultdict(float) if debug_enabled else None
    prev_retention_missing = defaultdict(int) if debug_enabled else None
    groups_with_book_one = 0
    usable_pairs = 0

    for series_books in series_groups.values():
        book_one = choose_book_one(series_books)
        if book_one is None:
            continue
        groups_with_book_one += 1
        for book in series_books:
            bucket = bucket_series_index(book.series_index)
            if bucket is None or bucket <= 1:
                continue
            delta = raw_percentiles[book.book_id] - raw_percentiles[book_one.book_id]
            if book_one.votes is not None and book.votes is not None:
                weight = math.log1p(min(book_one.votes, book.votes))
            else:
                weight = 1.0
            weighted_deltas[bucket] += delta * weight
            weights[bucket] += weight
            bucket_pairs[bucket] += 1
            if debug_enabled:
                update_delta_stats(bucket_delta_stats[bucket], delta)
                update_retention_delta_stats(
                    book1_retention_delta_stats,
                    book1_retention_weighted_deltas,
                    book1_retention_weights,
                    book1_retention_missing,
                    bucket,
                    retention_ratio(book, book_one),
                    delta,
                    weight,
                )
                update_retention_delta_stats(
                    prev_retention_delta_stats,
                    prev_retention_weighted_deltas,
                    prev_retention_weights,
                    prev_retention_missing,
                    bucket,
                    retention_ratio(
                        book,
                        choose_previous_whole_book(series_books, book),
                    ),
                    delta,
                    weight,
                )
            usable_pairs += 1

    inflation = {1: 0.0}
    for bucket, total in weighted_deltas.items():
        if weights[bucket] > 0:
            inflation[bucket] = max(0.0, total / weights[bucket])
    if debug_callback:
        debug_callback(
            'series groups={} groups_with_book1={} usable_pairs={} '
            'pair_buckets={} bias_buckets={}'.format(
                len(series_groups),
                groups_with_book_one,
                usable_pairs,
                compact_bucket_counts(bucket_pairs),
                compact_bias_buckets(inflation),
            )
        )
        debug_callback(
            'series delta_stats={}'.format(
                compact_delta_stats(
                    bucket_delta_stats,
                    weighted_deltas,
                    weights,
                )
            )
        )
        debug_callback(
            'series book1_retention_delta={}'.format(
                compact_retention_delta_stats(
                    book1_retention_delta_stats,
                    book1_retention_weighted_deltas,
                    book1_retention_weights,
                    book1_retention_missing,
                )
            )
        )
        debug_callback(
            'series prev_retention_delta={}'.format(
                compact_retention_delta_stats(
                    prev_retention_delta_stats,
                    prev_retention_weighted_deltas,
                    prev_retention_weights,
                    prev_retention_missing,
                )
            )
        )
    return inflation, usable_pairs


def new_delta_stats():
    return {
        'count': 0,
        'sum': 0.0,
        'positive': 0,
        'zero': 0,
        'negative': 0,
        'minimum': None,
        'maximum': None,
    }


def update_delta_stats(stats, delta):
    delta = float(delta)
    stats['count'] += 1
    stats['sum'] += delta
    if delta > 0.0:
        stats['positive'] += 1
    elif delta < 0.0:
        stats['negative'] += 1
    else:
        stats['zero'] += 1
    if stats['minimum'] is None or delta < stats['minimum']:
        stats['minimum'] = delta
    if stats['maximum'] is None or delta > stats['maximum']:
        stats['maximum'] = delta


def retention_ratio(book, reference_book):
    if reference_book is None:
        return None
    if reference_book.votes is None or reference_book.votes <= 0:
        return None
    if book.votes is None or book.votes <= 0:
        return None
    return min(1.0, float(book.votes) / float(reference_book.votes))


def retention_bucket(ratio):
    if ratio is None:
        return None
    ratio = max(0.0, min(1.0, float(ratio)))
    if ratio >= 0.75:
        return RETENTION_75_100
    if ratio >= 0.50:
        return RETENTION_50_75
    if ratio >= 0.25:
        return RETENTION_25_50
    return RETENTION_0_25


def position_bias_multiplier(book1_ratio, previous_ratio, series_bucket=None):
    multiplier = 1.0
    book1_bucket = retention_bucket(book1_ratio)
    previous_bucket = retention_bucket(previous_ratio)

    if book1_bucket == RETENTION_75_100:
        multiplier *= HIGH_BOOK1_RETENTION_MULTIPLIER
    elif book1_bucket == RETENTION_50_75:
        multiplier *= MID_BOOK1_RETENTION_MULTIPLIER
    elif book1_bucket == RETENTION_25_50:
        multiplier *= LOW_BOOK1_RETENTION_MULTIPLIER
    elif book1_bucket == RETENTION_0_25 and series_bucket is not None and series_bucket >= 4:
        multiplier *= VERY_LOW_LATER_BOOK1_RETENTION_MULTIPLIER

    if previous_bucket == RETENTION_0_25:
        multiplier *= VERY_LOW_PREVIOUS_RETENTION_MULTIPLIER

    return multiplier


def update_retention_delta_stats(stats_by_key, weighted_deltas, weights,
                                 missing_counts, bucket, ratio, delta, weight):
    retention_key = retention_bucket(ratio)
    if retention_key is None:
        missing_counts[bucket] += 1
        return
    key = (bucket, retention_key)
    update_delta_stats(stats_by_key[key], delta)
    weighted_deltas[key] += float(delta) * float(weight)
    weights[key] += float(weight)


def new_applied_setting_stats():
    return {
        'count': 0,
        'base_expected_sum': 0.0,
        'conditional_expected_sum': 0.0,
        'multiplier_sum': 0.0,
        'retention_sum': 0.0,
        'cap_sum': 0.0,
        'cap_limited': 0,
        'applied_sum': 0.0,
        'book1_ratio_count': 0,
        'book1_ratio_sum': 0.0,
        'previous_ratio_count': 0,
        'previous_ratio_sum': 0.0,
    }


def update_applied_setting_stats(stats_by_bucket, book, base_expected,
                                 multiplier, conditional_expected, retention,
                                 cap, uncapped_penalty, applied_penalty, book1_ratio,
                                 previous_ratio):
    bucket = bucket_series_index(book.series_index)
    if bucket is None or bucket <= 1:
        return
    stats = stats_by_bucket[bucket]
    stats['count'] += 1
    stats['base_expected_sum'] += float(base_expected)
    stats['conditional_expected_sum'] += float(conditional_expected)
    stats['multiplier_sum'] += float(multiplier)
    stats['retention_sum'] += float(retention)
    stats['cap_sum'] += float(cap)
    if cap < float(uncapped_penalty):
        stats['cap_limited'] += 1
    stats['applied_sum'] += float(applied_penalty)
    if book1_ratio is not None:
        stats['book1_ratio_count'] += 1
        stats['book1_ratio_sum'] += float(book1_ratio)
    if previous_ratio is not None:
        stats['previous_ratio_count'] += 1
        stats['previous_ratio_sum'] += float(previous_ratio)


def expected_inflation_for_book(book, position_inflation):
    bucket = bucket_series_index(book.series_index)
    if bucket is None or bucket <= 1:
        return 0.0
    if not has_vote_count(book):
        return 0.0
    return position_inflation.get(bucket, 0.0)


def calculate_scores(books, settings, locked_mapping=None, debug_callback=None):
    raw_percentiles = calculate_percentiles(
        [(book.book_id, book.rating) for book in books]
    )
    series_groups = group_by_series(books)

    learned_position_inflation = not (
        locked_mapping and locked_mapping.get('position_inflation')
    )
    if not learned_position_inflation:
        position_inflation = {
            _decode_bucket(key): float(value)
            for key, value in locked_mapping.get('position_inflation').items()
        }
        usable_pairs = 0
        if debug_callback:
            debug_callback(
                'series using_locked_map bias_buckets={}'.format(
                    compact_bias_buckets(position_inflation)
                )
            )
    else:
        position_inflation, usable_pairs = learn_position_inflation(
            series_groups,
            raw_percentiles,
            debug_callback=debug_callback,
        )

    adjusted = []
    scores_by_id = {}
    applied_setting_stats = (
        defaultdict(new_applied_setting_stats) if debug_callback else None
    )
    report = RunReport(valid_ratings=len(books))
    if len(books) < settings.minimum_valid_ratings_warning:
        report.warnings.append(
            'Only {} valid Goodreads ratings were found.'.format(len(books))
        )
    if (
        settings.series_correction_enabled
        and learned_position_inflation
        and usable_pairs < settings.minimum_series_pairs_warning
    ):
        report.warnings.append(
            'Only {} usable series-position pairs were found.'.format(usable_pairs)
        )

    for book in books:
        if settings.series_correction_enabled:
            series_books = series_groups.get(book.series, [])
            book_one = choose_book_one(series_books)
            previous_book = choose_previous_whole_book(series_books, book)
            book1_ratio = retention_ratio(book, book_one)
            previous_ratio = retention_ratio(book, previous_book)
            base_expected = expected_inflation_for_book(book, position_inflation)
            if base_expected:
                multiplier = position_bias_multiplier(
                    book1_ratio,
                    previous_ratio,
                    bucket_series_index(book.series_index),
                )
            else:
                multiplier = 0.0
            expected = base_expected * multiplier
            retention = 0.0
            ratio = book1_ratio
            if (
                book_one is not None
                and book_one.book_id in raw_percentiles
            ):
                cap = max(
                    0.0,
                    raw_percentiles[book.book_id]
                    - raw_percentiles[book_one.book_id],
                )
            else:
                cap = 0.0
        else:
            base_expected = 0.0
            multiplier = 0.0
            expected = 0.0
            retention = 0.0
            cap = 0.0
            ratio = None
            book1_ratio = None
            previous_ratio = None
        estimated_bias = expected + retention
        uncapped_penalty = settings.correction_strength * estimated_bias
        applied_penalty = min(uncapped_penalty, cap)
        penalty_adjusted_percentile = max(
            0.0,
            min(100.0, raw_percentiles[book.book_id] - applied_penalty),
        )
        adjusted.append((book.book_id, penalty_adjusted_percentile))
        if applied_penalty > 0.0:
            report.books_with_series_correction += 1
        else:
            report.books_without_series_correction += 1
        if (
            applied_penalty > 0.0
            and base_expected
            and multiplier
            and abs(multiplier - 1.0) > 0.0000001
        ):
            report.books_with_retention_correction += 1
        if applied_setting_stats is not None:
            update_applied_setting_stats(
                applied_setting_stats,
                book,
                base_expected,
                multiplier,
                expected,
                retention,
                cap,
                uncapped_penalty,
                applied_penalty,
                ratio,
                previous_ratio,
            )
        scores_by_id[book.book_id] = {
            'penalty_adjusted_percentile': penalty_adjusted_percentile,
            'base_expected': base_expected,
            'multiplier': multiplier,
            'expected': expected,
            'retention': retention,
            'cap': cap,
            'ratio': ratio,
            'previous_ratio': previous_ratio,
            'applied_penalty': applied_penalty,
        }

    adjusted_percentiles = calculate_percentiles(adjusted)
    scores = {}
    for book in books:
        data = scores_by_id[book.book_id]
        scores[book.book_id] = BookScore(
            book_id=book.book_id,
            rating=book.rating,
            votes=book.votes,
            raw_percentile=raw_percentiles[book.book_id],
            series_adjusted_rating=book.rating,
            adjusted_percentile=adjusted_percentiles[book.book_id],
            penalty_adjusted_percentile=data['penalty_adjusted_percentile'],
            distributed_percentile=adjusted_percentiles[book.book_id],
            series_bias_penalty=data['applied_penalty'],
            expected_position_inflation=data['expected'],
            retention_penalty=data['retention'],
            retention_ratio=data['ratio'],
        )
    if debug_callback:
        debug_callback(
            'series current_settings enabled={} strength={:.4f} '
            'retention_factor={:.4f} max_retention={:.4f} buckets={}'.format(
                1 if settings.series_correction_enabled else 0,
                float(settings.correction_strength),
                float(settings.retention_factor),
                float(settings.max_retention_penalty),
                compact_applied_setting_stats(applied_setting_stats),
            )
        )
    return scores, position_inflation, report


def encode_position_inflation(position_inflation):
    encoded = {}
    for key, value in position_inflation.items():
        encoded['6+' if int(key) >= 6 else str(int(key))] = float(value)
    return encoded


def _decode_bucket(key):
    if key == '6+':
        return 6
    return int(key)


def compact_bucket_counts(counts):
    if not counts:
        return '-'
    return ','.join(
        '{}:{}'.format(_encode_bucket(key), counts[key])
        for key in sorted(counts)
    )


def compact_bias_buckets(position_inflation):
    if not position_inflation:
        return '-'
    return ','.join(
        '{}:{:.4f}'.format(_encode_bucket(key), float(position_inflation[key]))
        for key in sorted(position_inflation)
    )


def compact_delta_stats(bucket_delta_stats, weighted_deltas, weights):
    if not bucket_delta_stats:
        return '-'
    parts = []
    for key in sorted(bucket_delta_stats):
        stats = bucket_delta_stats[key]
        count = int(stats.get('count', 0))
        if count <= 0:
            continue
        average = float(stats.get('sum', 0.0)) / float(count)
        weight = float(weights.get(key, 0.0))
        if weight > 0.0:
            weighted_average = float(weighted_deltas.get(key, 0.0)) / weight
        else:
            weighted_average = 0.0
        parts.append(
            '{}:n={},pos={},zero={},neg={},avg={:.4f},wavg={:.4f},'
            'min={:.4f},max={:.4f}'.format(
                _encode_bucket(key),
                count,
                int(stats.get('positive', 0)),
                int(stats.get('zero', 0)),
                int(stats.get('negative', 0)),
                average,
                weighted_average,
                float(stats.get('minimum', 0.0)),
                float(stats.get('maximum', 0.0)),
            )
        )
    return ';'.join(parts) or '-'


def compact_retention_delta_stats(stats_by_key, weighted_deltas, weights,
                                  missing_counts):
    buckets = sorted({
        key[0] for key in stats_by_key
    } | set(missing_counts))
    if not buckets:
        return '-'
    bucket_parts = []
    for bucket in buckets:
        segment_parts = []
        for retention_key in RETENTION_BUCKETS:
            key = (bucket, retention_key)
            stats = stats_by_key.get(key)
            if not stats:
                continue
            count = int(stats.get('count', 0))
            if count <= 0:
                continue
            average = float(stats.get('sum', 0.0)) / float(count)
            weight = float(weights.get(key, 0.0))
            if weight > 0.0:
                weighted_average = float(weighted_deltas.get(key, 0.0)) / weight
            else:
                weighted_average = 0.0
            segment_parts.append(
                '{}:n={},pos={},zero={},neg={},avg={:.4f},wavg={:.4f}'.format(
                    retention_bucket_label(retention_key),
                    count,
                    int(stats.get('positive', 0)),
                    int(stats.get('zero', 0)),
                    int(stats.get('negative', 0)),
                    average,
                    weighted_average,
                )
            )
        missing = int(missing_counts.get(bucket, 0))
        if missing:
            segment_parts.append('missing:n={}'.format(missing))
        if segment_parts:
            bucket_parts.append(
                '{}[{}]'.format(_encode_bucket(bucket), '|'.join(segment_parts))
            )
    return ';'.join(bucket_parts) or '-'


def retention_bucket_label(retention_key):
    return RETENTION_BUCKET_LABELS.get(retention_key, str(retention_key))


def compact_applied_setting_stats(stats_by_bucket):
    if not stats_by_bucket:
        return '-'
    parts = []
    for bucket in sorted(stats_by_bucket):
        stats = stats_by_bucket[bucket]
        count = int(stats.get('count', 0))
        if count <= 0:
            continue
        base_expected = float(stats.get('base_expected_sum', 0.0)) / float(count)
        multiplier = float(stats.get('multiplier_sum', 0.0)) / float(count)
        conditional_expected = (
            float(stats.get('conditional_expected_sum', 0.0)) / float(count)
        )
        retention = float(stats.get('retention_sum', 0.0)) / float(count)
        cap = float(stats.get('cap_sum', 0.0)) / float(count)
        cap_limited = int(stats.get('cap_limited', 0))
        applied = float(stats.get('applied_sum', 0.0)) / float(count)
        book1_ratio_count = int(stats.get('book1_ratio_count', 0))
        if book1_ratio_count > 0:
            book1_ratio = (
                float(stats.get('book1_ratio_sum', 0.0)) / float(book1_ratio_count)
            )
            book1_ratio_text = '{:.4f}'.format(book1_ratio)
        else:
            book1_ratio_text = '-'
        previous_ratio_count = int(stats.get('previous_ratio_count', 0))
        if previous_ratio_count > 0:
            previous_ratio = (
                float(stats.get('previous_ratio_sum', 0.0))
                / float(previous_ratio_count)
            )
            previous_ratio_text = '{:.4f}'.format(previous_ratio)
        else:
            previous_ratio_text = '-'
        parts.append(
            '{}:n={},base={:.4f},mult={:.4f},pos={:.4f},ret={:.4f},'
            'total={:.4f},cap={:.4f},capped={},applied={:.4f},'
            'book1_ret={},prev_ret={}'.format(
                _encode_bucket(bucket),
                count,
                base_expected,
                multiplier,
                conditional_expected,
                retention,
                conditional_expected + retention,
                cap,
                cap_limited,
                applied,
                book1_ratio_text,
                previous_ratio_text,
            )
        )
    return ';'.join(parts) or '-'


def _encode_bucket(key):
    return '6+' if int(key) >= 6 else str(int(key))
