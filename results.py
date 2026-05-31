#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class BookInput:
    book_id: int
    rating: float
    votes: Optional[int] = None
    series: Optional[str] = None
    series_index: Optional[float] = None


@dataclass
class BookScore:
    book_id: int
    rating: float
    votes: Optional[int]
    raw_percentile: float
    series_adjusted_rating: float
    adjusted_percentile: float
    penalty_adjusted_percentile: float = 0.0
    distributed_percentile: float = 0.0
    rating_output_value: Optional[float] = None
    series_bias_penalty: float = 0.0
    expected_position_inflation: float = 0.0
    retention_penalty: float = 0.0
    retention_ratio: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class RunSettings:
    output_percentile_field: str
    raw_percentile_field: str = ''
    adjusted_rating_field: str = ''
    output_format: str = 'percentile'
    percentile_adjustment_mode: str = 'direct_penalty'
    number_min: float = 0.0
    number_max: float = 100.0
    star_granularity: str = 'half'
    distribution_type: str = 'uniform'
    uniform_step: float = 0.01
    bell_curve_variety: int = 103
    bell_curve_std_dev: float = 0.85
    bell_curve_peak_percent: float = 50.0
    positive_skew_level: int = 203
    positive_skew_percent: float = 75.0
    j_curve_exclusivity: int = 303
    j_curve_power: float = 3.5
    series_correction_enabled: bool = True
    correction_strength: float = 0.50
    retention_factor: float = 0.0
    max_retention_penalty: float = 0.0
    minimum_valid_ratings_warning: int = 20
    minimum_series_pairs_warning: int = 10
    percentile_mapping_mode: str = 'recalculate_each_run'
    locked_curve_anchor_count: int = 21
    locked_curve_endpoint_gap_fraction: float = 0.025
    debug_diagnostics: bool = False


@dataclass
class RunReport:
    selected_count: int = 0
    processed_books: int = 0
    valid_ratings: int = 0
    skipped_missing_ratings: int = 0
    skipped_invalid_ratings: int = 0
    books_with_series_correction: int = 0
    books_without_series_correction: int = 0
    books_with_retention_correction: int = 0
    write_failures: List[Tuple[int, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def write_failure_count(self):
        return len(self.write_failures)
