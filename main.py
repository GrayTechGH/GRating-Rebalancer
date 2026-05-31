#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

try:
    load_translations()
except NameError:
    pass

try:
    _
except NameError:
    def _(text):
        return text

from calibre_plugins.GRating_Rebalancer.config import prefs, settings_from_prefs
from calibre_plugins.GRating_Rebalancer.locked_mapping import (
    build_mapping,
    load_locked_mapping,
    locked_mapping_is_compatible,
    save_locked_mapping,
    set_percentile_mapping_mode,
    USE_LOCKED_MAPPING_MODE,
)
from calibre_plugins.GRating_Rebalancer.metadata_io import (
    NO_GRATING_IDENTIFIER_WARNING,
    field_display_name,
    has_grating_identifier,
    load_library_inputs,
    selected_book_ids,
    selected_books_are_selected,
    validate_output_fields,
    write_outputs,
)
from calibre_plugins.GRating_Rebalancer.percentiles import (
    apply_distribution,
    convert_percentile,
)
from calibre_plugins.GRating_Rebalancer.scoring import calculate_scores


class GRatingActionRunner(object):
    '''
    Orchestrates the GUI workflow only.

    Formula math, Calibre metadata I/O, locked mapping persistence, and report
    models live in their own modules to keep this file from becoming the plugin.
    '''

    def __init__(self, gui, finished_callback=None):
        self.gui = gui
        self.finished_callback = finished_callback

    def run_for_selection(self):
        try:
            self.perform_action()
        finally:
            self.finish()

    def perform_action(self):
        db = self.gui.current_db
        if not selected_books_are_selected(self.gui):
            self.show_status(_('No books selected.'))
            return

        settings = settings_from_prefs(db)
        errors = validate_output_fields(db, settings)
        if errors:
            show_error(
                self.gui,
                _('GRating Rebalancer cannot run'),
                '\n'.join(errors),
            )
            return

        self.show_status(_('Checking GRating identifiers...'), 10000)
        if not has_grating_identifier(db):
            show_error(
                self.gui,
                _('GRating identifiers not found'),
                '\n'.join(NO_GRATING_IDENTIFIER_WARNING),
            )
            self.show_status(_('GRating Rebalancer cancelled.'))
            return

        if not confirm_write(self.gui, db, settings):
            self.show_status(_('GRating Rebalancer cancelled.'))
            return

        selected_ids = selected_book_ids(self.gui)
        if not selected_ids:
            self.show_status(_('No books selected.'))
            return

        debug_callback = debug_printer(settings.debug_diagnostics)
        if debug_callback:
            debug_callback(
                'start selected={} mode={} output={} rating={} format={} '
                'adjustment={}'.format(
                    len(selected_ids),
                    settings.percentile_mapping_mode,
                    settings.output_percentile_field,
                settings.adjusted_rating_field or '-',
                settings.output_format,
                settings.percentile_adjustment_mode,
                )
            )

        books, input_report = load_library_inputs(
            db,
            debug_callback=debug_callback,
        )
        locked_mapping_was_present = load_locked_mapping(prefs, db) is not None
        locked_mapping = self.compatible_locked_mapping(settings)
        scores, position_inflation, score_report = calculate_scores(
            books,
            settings,
            locked_mapping=locked_mapping,
            debug_callback=debug_callback,
        )
        if (
            settings.percentile_mapping_mode == 'use_locked_mapping'
            and locked_mapping is None
        ):
            return
        percentile_mapping = self.percentile_mapping_for_run(
            settings,
            scores,
            position_inflation,
            locked_mapping,
        )
        if debug_callback:
            debug_callback(
                'mapping {} curve_points={} book_count={}'.format(
                    'locked' if locked_mapping else 'built',
                    len(percentile_mapping.get('score_percentile_curve', [])),
                    percentile_mapping.get('book_count', len(scores)),
                )
            )
        self.apply_locked_mapping(scores, percentile_mapping)

        output_by_field = self.output_values_for_selection(
            selected_ids,
            scores,
            settings,
            percentile_mapping,
        )
        failures = write_outputs(db, output_by_field)
        successful_writes = successful_write_count(output_by_field, failures)
        if debug_callback:
            debug_callback(
                'writes attempted={} succeeded={} failed={}'.format(
                    attempted_write_count(output_by_field),
                    successful_writes,
                    len(failures),
                )
            )
        if (
            settings.percentile_mapping_mode == 'rebuild_and_lock'
            and successful_writes > 0
        ):
            self.save_locked_mapping(
                scores,
                position_inflation,
                settings,
                debug_callback=debug_callback,
            )
        elif should_prompt_to_lock_mapping(
            settings,
            locked_mapping_was_present,
            successful_writes,
        ) and confirm_lock_mapping(self.gui):
            self.save_locked_mapping(
                scores,
                position_inflation,
                settings,
                debug_callback=debug_callback,
            )

        report = input_report
        report.selected_count = len(selected_ids)
        report.books_with_series_correction = (
            score_report.books_with_series_correction
        )
        report.books_without_series_correction = (
            score_report.books_without_series_correction
        )
        report.books_with_retention_correction = (
            score_report.books_with_retention_correction
        )
        report.warnings.extend(score_report.warnings)
        report.write_failures.extend(failures)

        self.show_summary(report)

    def compatible_locked_mapping(self, settings):
        if settings.percentile_mapping_mode != 'use_locked_mapping':
            return None
        mapping = load_locked_mapping(prefs, self.current_db())
        if locked_mapping_is_compatible(
            mapping,
            settings,
            'raw_rating',
        ):
            return mapping
        show_error(
            self.gui,
            _('Locked mapping unavailable'),
            _('The locked mapping is missing or incompatible. Rebuild it first.'),
        )
        return None

    def percentile_mapping_for_run(
        self,
        settings,
        scores,
        position_inflation,
        locked_mapping=None,
    ):
        if locked_mapping:
            return locked_mapping
        return build_mapping(
            scores,
            position_inflation,
            settings,
            'raw_rating',
        )

    def save_locked_mapping(
        self,
        scores,
        position_inflation,
        settings,
        debug_callback=None,
    ):
        mapping = save_locked_mapping(
            prefs,
            scores,
            position_inflation,
            settings,
            'raw_rating',
            self.current_db(),
        )
        set_percentile_mapping_mode(
            prefs,
            USE_LOCKED_MAPPING_MODE,
            self.current_db(),
        )
        if debug_callback:
            debug_callback(
                'mapping_saved curve_points={} book_count={} bias_buckets={}'.format(
                    len(mapping.get('score_percentile_curve', [])),
                    mapping.get('book_count', len(scores)),
                    compact_mapping_bias(mapping),
                )
            )
        return mapping

    def apply_locked_mapping(self, scores, mapping):
        return

    def current_db(self):
        return getattr(self.gui, 'current_db', None)

    def output_values_for_selection(self, selected_ids, scores, settings,
                                    percentile_mapping=None):
        output = {}
        main_values = {}
        rating_values = {}
        selected = set(selected_ids)
        for book_id, score in scores.items():
            if book_id not in selected:
                continue
            main_values[book_id] = float(score.raw_percentile)
            if settings.adjusted_rating_field:
                source_percentile = rating_source_percentile(
                    score,
                    settings,
                    percentile_mapping,
                )
                score.distributed_percentile = apply_distribution(
                    source_percentile,
                    settings,
                )
                score.rating_output_value = convert_percentile(
                    score.distributed_percentile,
                    settings.output_format,
                    settings.number_min,
                    settings.number_max,
                    settings.star_granularity,
                )
                rating_values[book_id] = score.rating_output_value

        output[settings.output_percentile_field] = main_values
        if settings.adjusted_rating_field:
            output[settings.adjusted_rating_field] = rating_values
        return output

    def show_summary(self, report):
        lines = [
            _('Processed books: {}').format(report.processed_books),
            _('Valid Goodreads ratings: {}').format(report.valid_ratings),
            _('Skipped missing ratings: {}').format(
                report.skipped_missing_ratings
            ),
            _('Skipped invalid ratings: {}').format(
                report.skipped_invalid_ratings
            ),
            _('Books with series correction: {}').format(
                report.books_with_series_correction
            ),
            _('Books without series correction: {}').format(
                report.books_without_series_correction
            ),
            _('Books with vote-retention adjustment: {}').format(
                report.books_with_retention_correction
            ),
            _('Write failures: {}').format(report.write_failure_count()),
        ]
        if report.warnings:
            lines.append('')
            lines.extend(report.warnings)
        text = '\n'.join(lines)
        if prefs['debug_diagnostics']:
            print(text, flush=True)
        show_info(self.gui, _('GRating Rebalancer finished'), text)
        self.show_status(_('GRating Rebalancer finished.'))

    def show_status(self, message, timeout=5000):
        status_bar = getattr(self.gui, 'status_bar', None)
        if status_bar is not None and hasattr(status_bar, 'show_message'):
            status_bar.show_message(message, timeout)

    def finish(self):
        if callable(self.finished_callback):
            callback = self.finished_callback
            self.finished_callback = None
            callback()


def confirm_write(gui, db, settings):
    message = _(
        'Write calculated GRating output for the selected book(s) to {}?'
    ).format(confirm_write_field_text(db, settings))
    try:
        from calibre.gui2 import question_dialog
        return question_dialog(
            gui,
            _('Confirm GRating Rebalancer write'),
            message,
        )
    except Exception:
        return True


def confirm_write_field_text(db, settings):
    fields = [
        field_display_name(db, settings.output_percentile_field),
    ]
    if settings.adjusted_rating_field:
        fields.append(field_display_name(db, settings.adjusted_rating_field))
    return ', '.join(field for field in fields if field)


def rating_source_percentile(score, settings, percentile_mapping=None):
    if settings.percentile_adjustment_mode == 'direct_penalty':
        return score.penalty_adjusted_percentile
    return score.adjusted_percentile


def direct_penalty_percentile(score, percentile_mapping=None):
    return score.penalty_adjusted_percentile


def successful_write_count(output_by_field, failures):
    attempted = attempted_write_count(output_by_field)
    return max(0, attempted - len(failures))


def attempted_write_count(output_by_field):
    attempted = 0
    for values in output_by_field.values():
        if values:
            attempted += len(values)
    return attempted


def should_prompt_to_lock_mapping(settings, locked_mapping_was_present,
                                  successful_writes):
    return (
        successful_writes > 0
        and not locked_mapping_was_present
        and settings.percentile_mapping_mode != 'rebuild_and_lock'
    )


def confirm_lock_mapping(gui):
    try:
        from calibre.gui2 import question_dialog
        return question_dialog(
            gui,
            _('Lock GRating map'),
            _(
                'Lock the GRating map from this run? Future runs will use this '
                'rating-to-percentile map until you unlock it.'
            ),
        )
    except Exception:
        return False


def show_error(gui, title, message):
    try:
        from calibre.gui2 import error_dialog
        error_dialog(gui, title, message, show=True)
    except Exception:
        print('{}: {}'.format(title, message), flush=True)


def show_info(gui, title, message):
    try:
        from calibre.gui2 import info_dialog
        info_dialog(gui, title, message, show=True)
    except Exception:
        print('{}: {}'.format(title, message), flush=True)


def debug_printer(enabled):
    if not enabled:
        return None

    def print_debug(message):
        print('GRating debug: {}'.format(message), flush=True)

    return print_debug


def compact_mapping_bias(mapping):
    position_inflation = mapping.get('position_inflation', {})
    if not position_inflation:
        return '-'
    parts = []
    for key in sorted(position_inflation, key=bias_sort_key):
        try:
            value = float(position_inflation[key])
        except (TypeError, ValueError):
            continue
        parts.append('{}:{:.4f}'.format(key, value))
    return ','.join(parts) or '-'


def bias_sort_key(key):
    if key == '6+':
        return 6
    try:
        return int(key)
    except (TypeError, ValueError):
        return 99
