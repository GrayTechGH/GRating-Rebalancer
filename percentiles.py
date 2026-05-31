#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

from bisect import bisect_left, bisect_right
import math


OUTPUT_PERCENTILE = 'percentile'
OUTPUT_DECIMAL = 'decimal'
OUTPUT_RANGE = 'range'
OUTPUT_STARS_WHOLE = 'stars_whole'
OUTPUT_STARS_HALF = 'stars_half'


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def calculate_percentiles(pairs):
    values = [(book_id, float(value)) for book_id, value in pairs]
    count = len(values)
    if count == 0:
        return {}
    if count == 1:
        return {values[0][0]: 50.0}

    indexed = sorted(values, key=lambda item: item[1])
    result = {}
    index = 0
    while index < count:
        value = indexed[index][1]
        end = index
        while end + 1 < count and indexed[end + 1][1] == value:
            end += 1
        percentile = 100.0 * end / (count - 1)
        for tied_index in range(index, end + 1):
            result[indexed[tied_index][0]] = percentile
        index = end + 1
    return result


def convert_percentile(percentile, output_format, number_min=0.0,
                       number_max=100.0, star_granularity='half'):
    percentile = clamp(float(percentile), 0.0, 100.0)
    if output_format == OUTPUT_DECIMAL:
        return percentile / 100.0
    if output_format == OUTPUT_RANGE:
        return float(number_min) + (
            percentile / 100.0
        ) * (float(number_max) - float(number_min))
    if output_format in (OUTPUT_STARS_WHOLE, OUTPUT_STARS_HALF):
        granularity = star_granularity
        if output_format == OUTPUT_STARS_WHOLE:
            granularity = 'whole'
        if percentile > 0.0:
            minimum_percentile = 10.0 if granularity == 'whole' else 5.0
            percentile = max(percentile, minimum_percentile)
        stars = (percentile / 100.0) * 5.0
        if granularity == 'whole':
            stars = _round_half_up(stars)
        else:
            stars = _round_half_up(stars * 2.0) / 2.0
        return clamp(stars, 0.0, 5.0)
    return percentile


def apply_distribution(percentile, settings):
    distribution_type = str(getattr(settings, 'distribution_type', 'uniform') or 'uniform')
    if distribution_type == 'bell_curve':
        return apply_bell_curve_distribution(
            percentile,
            getattr(settings, 'bell_curve_std_dev', 0.85),
            getattr(settings, 'bell_curve_peak_percent', 50.0),
        )
    if distribution_type == 'positive_skew':
        return apply_positive_skew_distribution(
            percentile,
            getattr(settings, 'positive_skew_percent', 75.0),
        )
    if distribution_type == 'j_curve':
        return apply_j_curve_distribution(
            percentile,
            getattr(settings, 'j_curve_power', 3.5),
        )
    return apply_uniform_distribution(
        percentile,
        getattr(settings, 'uniform_step', 1.0),
    )


def apply_uniform_distribution(percentile, step):
    percentile = clamp(float(percentile), 0.0, 100.0)
    step = max(0.01, float(step))
    snapped = step * _round_half_up(percentile / step)
    return clamp(snapped, 0.0, 100.0)


def apply_bell_curve_distribution(percentile, std_dev, peak_percent=50.0):
    p = _normalized_percentile(percentile)
    if p <= 0.0 or p >= 1.0:
        return 100.0 * p
    std_dev = max(0.01, float(std_dev))
    z_score = _inverse_normal_cdf(p) * std_dev
    symmetric = 100.0 * _normal_cdf(z_score)
    return apply_bell_curve_peak(symmetric, peak_percent)


def apply_bell_curve_peak(percentile, peak_percent):
    p = _normalized_percentile(percentile)
    if p <= 0.0 or p >= 1.0:
        return 100.0 * p
    target = clamp(float(peak_percent) / 100.0, 0.10, 0.90)
    if target == 0.5:
        return 100.0 * p
    if target > 0.5:
        exponent = math.log(target) / math.log(0.5)
        return 100.0 * (p ** exponent)

    exponent = math.log(1.0 - target) / math.log(0.5)
    return 100.0 * (1.0 - ((1.0 - p) ** exponent))


def apply_positive_skew_distribution(percentile, midpoint_target_percent):
    p = _normalized_percentile(percentile)
    if p <= 0.0 or p >= 1.0:
        return 100.0 * p
    target = clamp(float(midpoint_target_percent) / 100.0, 0.01, 0.99)
    exponent = math.log(target) / math.log(0.5)
    return 100.0 * (p ** exponent)


def apply_j_curve_distribution(percentile, power):
    p = _normalized_percentile(percentile)
    if p <= 0.0 or p >= 1.0:
        return 100.0 * p
    power = max(0.01, float(power))
    return 100.0 * (p ** power)


def build_score_percentile_curve(scores, anchor_count=21, endpoint_gap_fraction=0.025):
    sorted_scores = sorted(float(score) for score in scores)
    if not sorted_scores:
        return []
    if len(sorted_scores) == 1:
        score = sorted_scores[0]
        return [[score, 50.0]]

    minimum = sorted_scores[0]
    maximum = sorted_scores[-1]
    if minimum == maximum:
        return [[minimum, 50.0]]

    positions = normalized_anchor_positions(anchor_count, endpoint_gap_fraction)
    curve = []
    for position in positions:
        score = minimum + position * (maximum - minimum)
        curve.append([score, percentile_for_score(sorted_scores, score)])
    return curve


def normalized_anchor_positions(anchor_count=21, endpoint_gap_fraction=0.025):
    anchor_count = max(2, int(anchor_count))
    gap = clamp(float(endpoint_gap_fraction), 0.0, 0.49)
    if anchor_count == 2:
        return [0.0, 1.0]
    if anchor_count == 3:
        return [0.0, 0.5, 1.0]

    interior_count = anchor_count - 4
    positions = [0.0, gap]
    if interior_count > 0:
        step = (1.0 - 2.0 * gap) / (interior_count + 1)
        for index in range(interior_count):
            positions.append(gap + step * (index + 1))
    positions.extend([1.0 - gap, 1.0])
    return positions


def percentile_for_score(sorted_scores, score):
    count = len(sorted_scores)
    if count == 0:
        return 50.0
    if count == 1:
        return 50.0

    score = float(score)
    left = bisect_left(sorted_scores, score)
    right = bisect_right(sorted_scores, score)
    if left != right:
        return 100.0 * (right - 1) / (count - 1)

    if left <= 0:
        return 0.0
    if left >= count:
        return 100.0

    lower_score = sorted_scores[left - 1]
    upper_score = sorted_scores[left]
    lower_percentile = 100.0 * (left - 1) / (count - 1)
    upper_percentile = 100.0 * left / (count - 1)
    if upper_score == lower_score:
        return lower_percentile
    ratio = (score - lower_score) / (upper_score - lower_score)
    return lower_percentile + ratio * (upper_percentile - lower_percentile)


def apply_score_percentile_curve(curve, score):
    if not curve:
        raise ValueError('Locked score-to-percentile curve is missing.')

    score = float(score)
    points = sorted((float(item[0]), float(item[1])) for item in curve)
    if len(points) == 1:
        return clamp(points[0][1], 0.0, 100.0)
    if score <= points[0][0]:
        return 0.0
    if score >= points[-1][0]:
        return 100.0

    for index in range(1, len(points)):
        lower_score, lower_percentile = points[index - 1]
        upper_score, upper_percentile = points[index]
        if score <= upper_score:
            if upper_score == lower_score:
                return lower_percentile
            ratio = (score - lower_score) / (upper_score - lower_score)
            return lower_percentile + ratio * (
                upper_percentile - lower_percentile
            )
    return 100.0


def _normalized_percentile(percentile):
    return clamp(float(percentile), 0.0, 100.0) / 100.0


def _round_half_up(value):
    return int(math.floor(float(value) + 0.5))


def _normal_cdf(value):
    return 0.5 * (1.0 + math.erf(float(value) / math.sqrt(2.0)))


def _inverse_normal_cdf(probability):
    probability = clamp(float(probability), 1e-12, 1.0 - 1e-12)
    a = [
        -3.969683028665376e+01,
        2.209460984245205e+02,
        -2.759285104469687e+02,
        1.383577518672690e+02,
        -3.066479806614716e+01,
        2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,
        1.615858368580409e+02,
        -1.556989798598866e+02,
        6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e+00,
        -2.549732539343734e+00,
        4.374664141464968e+00,
        2.938163982698783e+00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e+00,
        3.754408661907416e+00,
    ]
    low = 0.02425
    high = 1.0 - low
    if probability < low:
        q = math.sqrt(-2.0 * math.log(probability))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
        )
    if probability <= high:
        q = probability - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r) + 1.0
        )
    q = math.sqrt(-2.0 * math.log(1.0 - probability))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q) + 1.0
    )
