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

from qt.core import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPainter,
    QPalette,
    QSize,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from calibre.utils.config import JSONConfig

from calibre_plugins.GRating_Rebalancer.locked_mapping import (
    clear_locked_mapping,
    get_percentile_mapping_mode,
    load_locked_mapping,
    locked_mapping_is_present as active_locked_mapping_is_present,
    raw_locked_mapping,
    REBUILD_AND_LOCK_MODE,
    seed_library_mapping_from_global,
    set_percentile_mapping_mode,
)
from calibre_plugins.GRating_Rebalancer.metadata_io import (
    compatible_custom_columns,
    field_datatype,
    rating_field_supports_half_stars,
)
from calibre_plugins.GRating_Rebalancer.percentiles import (
    apply_distribution,
)
from calibre_plugins.GRating_Rebalancer.results import RunSettings

DISTRIBUTION_UNIFORM = 'uniform'
DISTRIBUTION_BELL_CURVE = 'bell_curve'
DISTRIBUTION_POSITIVE_SKEW = 'positive_skew'
DISTRIBUTION_J_CURVE = 'j_curve'
ADJUSTMENT_ADJUSTED_RANK = 'adjusted_rank'
ADJUSTMENT_DIRECT_PENALTY = 'direct_penalty'
BELL_CURVE_STRICT = 101
BELL_CURVE_CENTRED = 102
BELL_CURVE_BALANCED = 103
BELL_CURVE_SPREAD_OUT = 104
BELL_CURVE_DIVERSE = 105
POSITIVE_SKEW_CRITICAL = 201
POSITIVE_SKEW_GENEROUS = 202
POSITIVE_SKEW_MAINSTREAM = 203
POSITIVE_SKEW_HIGH = 204
POSITIVE_SKEW_INFLATED = 205
J_CURVE_ACCESSIBLE = 301
J_CURVE_SELECTIVE = 302
J_CURVE_PRESTIGIOUS = 303
J_CURVE_ELITE = 304
J_CURVE_MASTERPIECES = 305

prefs = JSONConfig('plugins/GRating_Rebalancer')

prefs.defaults['output_percentile_field'] = ''
prefs.defaults['raw_percentile_field'] = ''
prefs.defaults['adjusted_rating_field'] = ''
prefs.defaults['output_format'] = 'percentile'
prefs.defaults['percentile_adjustment_mode'] = 'direct_penalty'
prefs.defaults['number_min'] = 0.0
prefs.defaults['number_max'] = 100.0
prefs.defaults['star_granularity'] = 'half'
prefs.defaults['distribution_type'] = 'uniform'
prefs.defaults['uniform_step'] = 0.01
prefs.defaults['bell_curve_variety'] = BELL_CURVE_BALANCED
prefs.defaults['bell_curve_std_dev'] = 0.85
prefs.defaults['bell_curve_peak_percent'] = 50.0
prefs.defaults['positive_skew_level'] = POSITIVE_SKEW_MAINSTREAM
prefs.defaults['positive_skew_percent'] = 75.0
prefs.defaults['j_curve_exclusivity'] = J_CURVE_PRESTIGIOUS
prefs.defaults['j_curve_power'] = 3.5
prefs.defaults['series_correction_enabled'] = True
prefs.defaults['correction_strength'] = 0.50
prefs.defaults['retention_factor'] = 0.0
prefs.defaults['max_retention_penalty'] = 0.0
prefs.defaults['minimum_valid_ratings_warning'] = 20
prefs.defaults['minimum_series_pairs_warning'] = 10
prefs.defaults['percentile_mapping_mode'] = 'recalculate_each_run'
prefs.defaults['locked_curve_anchor_count'] = 21
prefs.defaults['locked_curve_endpoint_gap_fraction'] = 0.025
prefs.defaults['debug_diagnostics'] = False
prefs.defaults['locked_percentile_mapping'] = {}
prefs.defaults['per_library_mapping_enabled'] = False
prefs.defaults['locked_percentile_mappings_by_library'] = {}
prefs.defaults['percentile_mapping_modes_by_library'] = {}
prefs.defaults['config_dialog_width'] = 760
prefs.defaults['config_dialog_height'] = 640

CONFIG_DIALOG_DEFAULT_SIZE = QSize(760, 640)
CONFIG_DIALOG_MINIMUM_SIZE = QSize(620, 400)
RATING_TYPE_TABS_MAXIMUM_HEIGHT = 150
LOCKED_MAP_STATUS_WIDTH = 88
SERIES_BIAS_TABLE_FALLBACK_ROW_HEIGHT = 30
SERIES_BIAS_TABLE_FALLBACK_HEADER_HEIGHT = 24
SERIES_BIAS_TABLE_VERTICAL_PADDING = 12
SERIES_BIAS_COLUMN_EXTRA_WIDTH = 16
OUTPUT_FORMAT_STARS = 'stars'
SESSION_CONFIG_DIALOG_POSITION = None
DISTRIBUTION_PREVIEW_BAR_COUNT = 9
DISTRIBUTION_PREVIEW_SAMPLE_COUNT = 101
UNIFORM_STEP_PRESETS = [
    ('0.01', 0.01),
    ('0.1', 0.1),
    ('1', 1.0),
    ('5', 5.0),
    ('10', 10.0),
    ('20', 20.0),
    ('25', 25.0),
]
BELL_CURVE_PRESETS = [
    ('Strict', BELL_CURVE_STRICT, 0.45),
    ('Centred', BELL_CURVE_CENTRED, 0.65),
    ('Balanced', BELL_CURVE_BALANCED, 0.85),
    ('Spread Out', BELL_CURVE_SPREAD_OUT, 1.15),
    ('Diverse', BELL_CURVE_DIVERSE, 1.50),
]
BELL_CURVE_PEAK_PRESETS = [
    ('Left 35', 35.0),
    ('Centered 50', 50.0),
    ('Right 65', 65.0),
]
POSITIVE_SKEW_PRESETS = [
    ('Critical', POSITIVE_SKEW_CRITICAL, 65.0),
    ('Generous', POSITIVE_SKEW_GENEROUS, 70.0),
    ('Mainstream', POSITIVE_SKEW_MAINSTREAM, 75.0),
    ('High', POSITIVE_SKEW_HIGH, 80.0),
    ('Inflated', POSITIVE_SKEW_INFLATED, 85.0),
]
J_CURVE_PRESETS = [
    ('Accessible', J_CURVE_ACCESSIBLE, 1.8),
    ('Selective', J_CURVE_SELECTIVE, 2.5),
    ('Prestigious', J_CURVE_PRESTIGIOUS, 3.5),
    ('Elite', J_CURVE_ELITE, 5.0),
    ('Masterpieces', J_CURVE_MASTERPIECES, 7.0),
]


class DistributionPreviewWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._bars = [0.0] * DISTRIBUTION_PREVIEW_BAR_COUNT
        if hasattr(self, 'setMinimumHeight'):
            self.setMinimumHeight(74)
        if hasattr(self, 'setMaximumHeight'):
            self.setMaximumHeight(96)

    def set_bars(self, bars):
        self._bars = [
            max(0.0, min(1.0, float(value)))
            for value in list(bars)[:DISTRIBUTION_PREVIEW_BAR_COUNT]
        ]
        while len(self._bars) < DISTRIBUTION_PREVIEW_BAR_COUNT:
            self._bars.append(0.0)
        if hasattr(self, 'update'):
            self.update()

    def paintEvent(self, event):
        try:
            QWidget.paintEvent(self, event)
        except AttributeError:
            pass

        bars = list(self._bars)
        if not bars:
            return

        painter = QPainter(self)
        color = active_text_color(self)
        width = int(widget_dimension(self, 'width', 260))
        height = int(widget_dimension(self, 'height', 82))
        margin = 8
        baseline = max(margin + 1, height - margin)
        available_height = max(1, height - (margin * 2))
        available_width = max(1, width - (margin * 2))
        bar_width = max(3, min(10, available_width // (len(bars) * 3)))
        gap = 0
        if len(bars) > 1:
            gap = max(3, (available_width - (bar_width * len(bars))) // (len(bars) - 1))
            gap = min(gap, 18)
        total_width = (bar_width * len(bars)) + (gap * (len(bars) - 1))
        x_pos = margin + max(0, (available_width - total_width) // 2)

        for value in bars:
            bar_height = max(2, int(round(value * available_height)))
            y_pos = baseline - bar_height
            painter.fillRect(int(x_pos), int(y_pos), int(bar_width), int(bar_height), color)
            x_pos += bar_width + gap

        if hasattr(painter, 'end'):
            painter.end()


class ConfigWidget(QWidget):
    validate_before_accept = True

    def __init__(self, db=None):
        QWidget.__init__(self)
        self.db = db
        self.setMinimumSize(CONFIG_DIALOG_MINIMUM_SIZE)
        self._position_restored = False
        self.resize(config_dialog_size_from_prefs())

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget(self)
        layout.addWidget(tabs, 1)

        main_tab = QWidget(self)
        main_layout = QVBoxLayout()
        main_form = QFormLayout()
        main_layout.addLayout(main_form)
        main_tab.setLayout(main_layout)
        tabs.addTab(main_tab, _('Main'))

        series_tab = QWidget(self)
        series_layout = QVBoxLayout()
        series_tab.setLayout(series_layout)
        series_form = QFormLayout()
        series_layout.addLayout(series_form)
        tabs.addTab(series_tab, _('Series'))

        distribution_tab = QWidget(self)
        distribution_layout = QVBoxLayout()
        distribution_tab.setLayout(distribution_layout)
        tabs.addTab(distribution_tab, _('Distribution'))

        self.output_percentile_field = QComboBox(self)
        main_form.addRow(_('Output:'), self.output_percentile_field)

        self.output_format = QComboBox(self)
        add_combo_item(self.output_format, _('Percentile 0.0-100.0'), 'percentile')
        add_combo_item(self.output_format, _('Decimal 0.0-1.0'), 'decimal')
        add_combo_item(self.output_format, _('User-defined range'), 'range')
        add_combo_item(self.output_format, _('Star rating'), OUTPUT_FORMAT_STARS)
        set_combo_data(
            self.output_format,
            output_format_for_ui(prefs['output_format']),
        )
        main_form.addRow(_('Rating type:'), self.output_format)

        self.adjusted_rating_field = QComboBox(self)
        main_form.addRow(_('Rating:'), self.adjusted_rating_field)

        self.per_library_mapping_enabled = QCheckBox(
            _('Use a separate map per library'),
            self,
        )
        self.per_library_mapping_enabled.setChecked(
            bool(prefs['per_library_mapping_enabled'])
        )
        set_tool_tip(
            self.per_library_mapping_enabled,
            _(
                'When enabled, each Calibre library has its own locked '
                'rating-to-percentile map.'
            ),
        )
        main_form.addRow(_('Mapping scope:'), self.per_library_mapping_enabled)

        self.locked_map_status = QLabel('', self)
        set_fixed_widget_width(self.locked_map_status, LOCKED_MAP_STATUS_WIDTH)
        self.unlock_map_button = QToolButton(self)
        self.locked_map_detail = QLabel('', self)
        locked_map_row = QWidget(self)
        locked_map_layout = QHBoxLayout()
        locked_map_row.setLayout(locked_map_layout)
        if hasattr(locked_map_layout, 'setContentsMargins'):
            locked_map_layout.setContentsMargins(0, 0, 0, 0)
        locked_map_layout.addWidget(self.locked_map_status)
        locked_map_layout.addWidget(self.unlock_map_button)
        locked_map_layout.addWidget(self.locked_map_detail, 1)
        main_form.addRow(_('Locked map:'), locked_map_row)

        self.rating_type_tabs = QTabWidget(self)
        if hasattr(self.rating_type_tabs, 'setMaximumHeight'):
            self.rating_type_tabs.setMaximumHeight(RATING_TYPE_TABS_MAXIMUM_HEIGHT)
        main_layout.addWidget(self.rating_type_tabs)
        main_layout.addStretch(1)

        percentile_tab = QWidget(self)
        percentile_layout = QVBoxLayout()
        percentile_tab.setLayout(percentile_layout)
        percentile_layout.addStretch(1)
        self.rating_type_tabs.addTab(percentile_tab, _('Percentile'))

        decimal_tab = QWidget(self)
        decimal_layout = QVBoxLayout()
        decimal_tab.setLayout(decimal_layout)
        decimal_layout.addStretch(1)
        self.rating_type_tabs.addTab(decimal_tab, _('Decimal'))

        range_tab = QWidget(self)
        range_layout = QVBoxLayout()
        range_tab.setLayout(range_layout)
        range_form = QFormLayout()
        range_layout.addLayout(range_form)
        range_layout.addStretch(1)
        self.rating_type_tabs.addTab(range_tab, _('Range'))

        self.range_minimum_label = QLabel(_('Range minimum:'), self)
        self.number_min = QLineEdit(self)
        self.number_min.setText(str(prefs['number_min']))
        range_form.addRow(self.range_minimum_label, self.number_min)

        self.range_maximum_label = QLabel(_('Range maximum:'), self)
        self.number_max = QLineEdit(self)
        self.number_max.setText(str(prefs['number_max']))
        range_form.addRow(self.range_maximum_label, self.number_max)

        stars_tab = QWidget(self)
        stars_layout = QVBoxLayout()
        stars_tab.setLayout(stars_layout)
        stars_form = QFormLayout()
        stars_layout.addLayout(stars_form)
        stars_layout.addStretch(1)
        self.rating_type_tabs.addTab(stars_tab, _('Star rating'))

        self.enable_half_stars = QCheckBox(_('Enable half stars'), self)
        self.enable_half_stars.setChecked(
            stored_star_granularity(prefs['output_format'], prefs['star_granularity'])
            == 'half'
        )
        use_placeholder_color_when_disabled(self.enable_half_stars)
        stars_form.addRow('', self.enable_half_stars)

        self.series_correction_enabled = QCheckBox(_('Enabled'), self)
        self.series_correction_enabled.setChecked(
            bool(prefs['series_correction_enabled'])
        )
        series_form.addRow(_('Series correction:'), self.series_correction_enabled)

        self.correction_strength = QComboBox(self)
        add_combo_item(self.correction_strength, _('Weak'), 0.25)
        add_combo_item(self.correction_strength, _('Normal'), 0.50)
        add_combo_item(self.correction_strength, _('Strong'), 0.75)
        add_combo_item(self.correction_strength, _('Complete'), 1.00)
        set_combo_data(self.correction_strength, prefs['correction_strength'])
        series_form.addRow(_('Correction strength:'), self.correction_strength)

        self.rerank_after_series_adjustment = QCheckBox(
            _('Rerank after series penalties'),
            self,
        )
        self.rerank_after_series_adjustment.setChecked(
            clean_text(prefs['percentile_adjustment_mode'])
            == ADJUSTMENT_ADJUSTED_RANK
        )
        series_form.addRow(
            _('Rating adjustment:'),
            self.rerank_after_series_adjustment,
        )
        set_tool_tip(
            self.rerank_after_series_adjustment,
            rerank_after_series_help_text(),
        )

        self.series_bias_table = QTableWidget(self)
        configure_series_bias_table(self.series_bias_table)
        set_tool_tip(self.series_bias_table, series_bias_help_text())
        series_layout.addWidget(self.series_bias_table)
        series_layout.addStretch(1)

        distribution_form = QFormLayout()
        distribution_layout.addLayout(distribution_form)

        self.distribution_type = QComboBox(self)
        add_combo_item(self.distribution_type, _('Uniform'), DISTRIBUTION_UNIFORM)
        add_combo_item(
            self.distribution_type,
            _('Bell curve'),
            DISTRIBUTION_BELL_CURVE,
        )
        add_combo_item(
            self.distribution_type,
            _('Positive skew'),
            DISTRIBUTION_POSITIVE_SKEW,
        )
        add_combo_item(self.distribution_type, _('J-Curve'), DISTRIBUTION_J_CURVE)
        set_combo_data(
            self.distribution_type,
            clean_text(prefs['distribution_type']) or DISTRIBUTION_UNIFORM,
        )
        distribution_form.addRow(_('Distribution type:'), self.distribution_type)

        self.distribution_tabs = QTabWidget(self)
        distribution_layout.addWidget(self.distribution_tabs)

        uniform_tab = QWidget(self)
        uniform_form = QFormLayout()
        uniform_tab.setLayout(uniform_form)
        self.distribution_tabs.addTab(uniform_tab, _('Uniform'))

        self.uniform_step_preset = QComboBox(self)
        add_numeric_preset_items(self.uniform_step_preset, UNIFORM_STEP_PRESETS)
        set_combo_data(
            self.uniform_step_preset,
            matching_numeric_preset(
                prefs['uniform_step'],
                UNIFORM_STEP_PRESETS,
                1.0,
            ),
        )
        uniform_form.addRow(_('Presets:'), self.uniform_step_preset)

        self.uniform_step_manual = QLineEdit(self)
        self.uniform_step_manual.setText(str(float(prefs['uniform_step'])))
        uniform_form.addRow(_('Step:'), self.uniform_step_manual)

        bell_curve_tab = QWidget(self)
        bell_curve_form = QFormLayout()
        bell_curve_tab.setLayout(bell_curve_form)
        self.distribution_tabs.addTab(bell_curve_tab, _('Bell curve'))

        self.bell_curve_variety = QComboBox(self)
        add_weighted_preset_items(self.bell_curve_variety, BELL_CURVE_PRESETS)
        set_combo_data(
            self.bell_curve_variety,
            weighted_preset_key(
                prefs['bell_curve_variety'],
                BELL_CURVE_PRESETS,
                BELL_CURVE_BALANCED,
            ),
        )
        bell_curve_form.addRow(_('Presets:'), self.bell_curve_variety)

        self.bell_curve_std_dev = QLineEdit(self)
        self.bell_curve_std_dev.setText(str(float(prefs['bell_curve_std_dev'])))
        bell_curve_form.addRow(_('Std dev:'), self.bell_curve_std_dev)

        self.bell_curve_peak_preset = QComboBox(self)
        add_numeric_preset_items(
            self.bell_curve_peak_preset,
            BELL_CURVE_PEAK_PRESETS,
        )
        set_combo_data(
            self.bell_curve_peak_preset,
            matching_numeric_preset(
                prefs['bell_curve_peak_percent'],
                BELL_CURVE_PEAK_PRESETS,
                50.0,
            ),
        )
        bell_curve_form.addRow(_('Peak preset:'), self.bell_curve_peak_preset)

        self.bell_curve_peak_percent = QLineEdit(self)
        self.bell_curve_peak_percent.setText(
            str(float(prefs['bell_curve_peak_percent']))
        )
        bell_curve_form.addRow(_('Peak:'), self.bell_curve_peak_percent)

        positive_skew_tab = QWidget(self)
        positive_skew_form = QFormLayout()
        positive_skew_tab.setLayout(positive_skew_form)
        self.distribution_tabs.addTab(positive_skew_tab, _('Positive skew'))

        self.positive_skew_level = QComboBox(self)
        add_weighted_preset_items(self.positive_skew_level, POSITIVE_SKEW_PRESETS)
        set_combo_data(
            self.positive_skew_level,
            weighted_preset_key(
                prefs['positive_skew_level'],
                POSITIVE_SKEW_PRESETS,
                POSITIVE_SKEW_MAINSTREAM,
            ),
        )
        positive_skew_form.addRow(_('Presets:'), self.positive_skew_level)

        self.positive_skew_percent = QLineEdit(self)
        self.positive_skew_percent.setText(
            str(float(prefs['positive_skew_percent']))
        )
        positive_skew_form.addRow(_('Percent:'), self.positive_skew_percent)

        j_curve_tab = QWidget(self)
        j_curve_form = QFormLayout()
        j_curve_tab.setLayout(j_curve_form)
        self.distribution_tabs.addTab(j_curve_tab, _('J-Curve'))

        self.j_curve_exclusivity = QComboBox(self)
        add_weighted_preset_items(self.j_curve_exclusivity, J_CURVE_PRESETS)
        set_combo_data(
            self.j_curve_exclusivity,
            weighted_preset_key(
                prefs['j_curve_exclusivity'],
                J_CURVE_PRESETS,
                J_CURVE_PRESTIGIOUS,
            ),
        )
        j_curve_form.addRow(_('Presets:'), self.j_curve_exclusivity)

        self.j_curve_power = QLineEdit(self)
        self.j_curve_power.setText(str(float(prefs['j_curve_power'])))
        j_curve_form.addRow(_('Curve power:'), self.j_curve_power)

        self.distribution_preview = DistributionPreviewWidget(self)
        distribution_layout.addWidget(self.distribution_preview)
        distribution_layout.addStretch(1)

        connect_signal(
            getattr(self.output_format, 'currentIndexChanged', None),
            self.on_output_format_changed,
        )
        connect_signal(
            getattr(self.rating_type_tabs, 'currentChanged', None),
            self.on_rating_type_tab_changed,
        )
        connect_signal(
            getattr(self.enable_half_stars, 'toggled', None),
            self.refresh_rating_field_options,
        )
        connect_signal(
            getattr(self.adjusted_rating_field, 'currentIndexChanged', None),
            self.on_rating_field_changed,
        )
        connect_signal(
            getattr(self.unlock_map_button, 'clicked', None),
            self.on_unlock_map_clicked,
        )
        connect_signal(
            getattr(self.series_correction_enabled, 'toggled', None),
            self.refresh_series_options,
        )
        connect_signal(
            getattr(self.correction_strength, 'currentIndexChanged', None),
            self.refresh_series_bias_table,
        )
        connect_signal(
            getattr(self.correction_strength, 'currentIndexChanged', None),
            self.refresh_locked_mapping_status,
        )
        connect_signal(
            getattr(self.rerank_after_series_adjustment, 'toggled', None),
            self.refresh_distribution_preview,
        )
        connect_signal(
            getattr(self.distribution_type, 'currentIndexChanged', None),
            self.on_distribution_type_changed,
        )
        connect_signal(
            getattr(self.distribution_tabs, 'currentChanged', None),
            self.on_distribution_tab_changed,
        )
        connect_signal(
            getattr(self.uniform_step_preset, 'currentIndexChanged', None),
            self.on_uniform_step_preset_changed,
        )
        connect_signal(
            getattr(self.uniform_step_manual, 'textChanged', None),
            self.refresh_distribution_preview,
        )
        connect_signal(
            getattr(self.bell_curve_variety, 'currentIndexChanged', None),
            self.on_bell_curve_variety_changed,
        )
        connect_signal(
            getattr(self.bell_curve_std_dev, 'textChanged', None),
            self.refresh_distribution_preview,
        )
        connect_signal(
            getattr(self.bell_curve_peak_preset, 'currentIndexChanged', None),
            self.on_bell_curve_peak_preset_changed,
        )
        connect_signal(
            getattr(self.bell_curve_peak_percent, 'textChanged', None),
            self.refresh_distribution_preview,
        )
        connect_signal(
            getattr(self.positive_skew_level, 'currentIndexChanged', None),
            self.on_positive_skew_level_changed,
        )
        connect_signal(
            getattr(self.positive_skew_percent, 'textChanged', None),
            self.refresh_distribution_preview,
        )
        connect_signal(
            getattr(self.j_curve_exclusivity, 'currentIndexChanged', None),
            self.on_j_curve_exclusivity_changed,
        )
        connect_signal(
            getattr(self.j_curve_power, 'textChanged', None),
            self.refresh_distribution_preview,
        )
        self.refresh_output_field_options()
        self.refresh_rating_field_options()
        self.refresh_locked_mapping_status()
        self.refresh_series_options()
        self.refresh_series_bias_table()
        self.sync_rating_type_tab_from_format()
        self.sync_distribution_tab_from_type()
        self.refresh_distribution_preview()

    def sizeHint(self):
        return config_dialog_size_from_prefs()

    def showEvent(self, event):
        try:
            QWidget.showEvent(self, event)
        except AttributeError:
            pass
        restore_config_dialog_position(self)

    def save_settings(self):
        rating_field = combo_data(self.adjusted_rating_field, '')
        output_format = selected_output_format(
            effective_rating_type_for_field(
                self.db,
                rating_field,
                combo_data(self.output_format, 'percentile'),
            ),
            self.enable_half_stars.isChecked(),
        )
        prefs['output_percentile_field'] = combo_data(
            self.output_percentile_field,
            '',
        )
        prefs['raw_percentile_field'] = ''
        prefs['adjusted_rating_field'] = rating_field
        prefs['output_format'] = output_format
        prefs['percentile_adjustment_mode'] = adjustment_mode_from_checkbox(
            self.rerank_after_series_adjustment,
            self.series_correction_enabled.isChecked(),
        )
        prefs['number_min'] = parse_float(self.number_min.text(), 0.0)
        prefs['number_max'] = parse_float(self.number_max.text(), 100.0)
        prefs['star_granularity'] = (
            'half' if self.enable_half_stars.isChecked() else 'whole'
        )
        prefs['distribution_type'] = combo_data(
            self.distribution_type,
            DISTRIBUTION_UNIFORM,
        )
        prefs['uniform_step'] = parse_float(
            self.uniform_step_manual.text(),
            preset_numeric_value(
                combo_data(self.uniform_step_preset, 1.0),
                1.0,
            ),
        )
        prefs['bell_curve_variety'] = combo_data(
            self.bell_curve_variety,
            BELL_CURVE_BALANCED,
        )
        prefs['bell_curve_std_dev'] = parse_float(
            self.bell_curve_std_dev.text(),
            preset_numeric_value(
                preset_numeric_data_for_key(
                    combo_data(self.bell_curve_variety, BELL_CURVE_BALANCED),
                    BELL_CURVE_PRESETS,
                    0.85,
                ),
                0.85,
            ),
        )
        prefs['bell_curve_peak_percent'] = parse_bounded_float(
            self.bell_curve_peak_percent.text(),
            preset_numeric_value(combo_data(self.bell_curve_peak_preset, 50.0), 50.0),
            10.0,
            90.0,
        )
        prefs['positive_skew_level'] = combo_data(
            self.positive_skew_level,
            POSITIVE_SKEW_MAINSTREAM,
        )
        prefs['positive_skew_percent'] = parse_float(
            self.positive_skew_percent.text(),
            preset_numeric_value(
                preset_numeric_data_for_key(
                    combo_data(self.positive_skew_level, POSITIVE_SKEW_MAINSTREAM),
                    POSITIVE_SKEW_PRESETS,
                    75.0,
                ),
                75.0,
            ),
        )
        prefs['j_curve_exclusivity'] = combo_data(
            self.j_curve_exclusivity,
            J_CURVE_PRESTIGIOUS,
        )
        prefs['j_curve_power'] = parse_float(
            self.j_curve_power.text(),
            preset_numeric_value(
                preset_numeric_data_for_key(
                    combo_data(self.j_curve_exclusivity, J_CURVE_PRESTIGIOUS),
                    J_CURVE_PRESETS,
                    3.5,
                ),
                3.5,
            ),
        )
        prefs['series_correction_enabled'] = (
            self.series_correction_enabled.isChecked()
        )
        prefs['correction_strength'] = float(
            combo_data(self.correction_strength, 0.50)
        )
        previous_per_library = bool(prefs['per_library_mapping_enabled'])
        prefs['per_library_mapping_enabled'] = (
            self.per_library_mapping_enabled.isChecked()
        )
        if prefs['per_library_mapping_enabled'] and not previous_per_library:
            seed_library_mapping_from_global(prefs, self.db)
        save_config_dialog_geometry(self)

    def validate(self):
        return True

    def refresh_output_field_options(self, *args):
        current = combo_data(
            self.output_percentile_field,
            prefs['output_percentile_field'],
        )
        output_format = selected_output_format(
            combo_data(self.output_format, 'percentile'),
            self.enable_half_stars.isChecked(),
        )
        refresh_field_combo(
            self.output_percentile_field,
            self.db,
            current,
            'output',
            'percentile',
            True,
        )

    def refresh_rating_field_options(self):
        current = combo_data_allow_empty(
            self.adjusted_rating_field,
            prefs['adjusted_rating_field'],
        )
        refresh_field_combo(
            self.adjusted_rating_field,
            self.db,
            current,
            'rating',
            selected_output_format(
                effective_rating_type_for_field(
                    self.db,
                    current,
                    combo_data(self.output_format, 'percentile'),
                ),
                self.enable_half_stars.isChecked(),
            ),
            False,
        )
        self.apply_rating_type_constraints()

    def on_output_format_changed(self, *args):
        self.sync_rating_type_tab_from_format()
        self.refresh_rating_field_options()

    def on_rating_type_tab_changed(self, *args):
        if self.locked_rating_type():
            self.apply_rating_type_constraints()
            return
        output_format = rating_type_for_index(current_tab_index(self.rating_type_tabs))
        if hasattr(self.output_format, 'blockSignals'):
            self.output_format.blockSignals(True)
            set_combo_data(self.output_format, output_format)
            self.output_format.blockSignals(False)
        else:
            set_combo_data(self.output_format, output_format)
        self.refresh_rating_field_options()

    def on_rating_field_changed(self, *args):
        self.apply_rating_type_constraints()

    def sync_rating_type_tab_from_format(self):
        set_current_tab_index(
            self.rating_type_tabs,
            rating_type_index_for_format(
                combo_data(self.output_format, 'percentile'),
            ),
        )

    def locked_rating_type(self):
        return locked_rating_type_for_field(
            self.db,
            combo_data(self.adjusted_rating_field, ''),
        )

    def apply_rating_type_constraints(self):
        current_rating_field = combo_data(self.adjusted_rating_field, '')
        locked_type = self.locked_rating_type()
        if locked_type:
            if hasattr(self.output_format, 'blockSignals'):
                self.output_format.blockSignals(True)
                set_combo_data(self.output_format, locked_type)
                self.output_format.blockSignals(False)
            else:
                set_combo_data(self.output_format, locked_type)
            set_current_tab_index(
                self.rating_type_tabs,
                rating_type_index_for_format(locked_type),
            )
        elif not rating_field_allows_star_tab(self.db, current_rating_field):
            if output_format_for_ui(combo_data(self.output_format, 'percentile')) == (
                OUTPUT_FORMAT_STARS
            ):
                if hasattr(self.output_format, 'blockSignals'):
                    self.output_format.blockSignals(True)
                    set_combo_data(self.output_format, 'percentile')
                    self.output_format.blockSignals(False)
                else:
                    set_combo_data(self.output_format, 'percentile')
                set_current_tab_index(
                    self.rating_type_tabs,
                    rating_type_index_for_format('percentile'),
                )
        star_allowed = rating_field_allows_star_tab(self.db, current_rating_field)
        set_widget_enabled(self.output_format, locked_type is None)
        set_tool_tip(
            self.output_format,
            rating_type_help_text(locked_type, star_allowed),
        )
        set_rating_type_tabs_enabled(
            self.rating_type_tabs,
            locked_type,
            star_allowed,
        )
        half_stars_enabled = self.selected_rating_field_supports_half_stars()
        if not half_stars_enabled and self.enable_half_stars.isChecked():
            if hasattr(self.enable_half_stars, 'blockSignals'):
                self.enable_half_stars.blockSignals(True)
                self.enable_half_stars.setChecked(False)
                self.enable_half_stars.blockSignals(False)
            else:
                self.enable_half_stars.setChecked(False)
        set_widget_enabled(self.enable_half_stars, half_stars_enabled)

    def selected_rating_field_supports_half_stars(self):
        return rating_field_supports_half_stars(
            self.db,
            combo_data(self.adjusted_rating_field, ''),
        )

    def refresh_series_options(self, *args):
        enabled = self.series_correction_enabled.isChecked()
        if hasattr(self.correction_strength, 'setEnabled'):
            self.correction_strength.setEnabled(enabled)
        set_widget_enabled(self.rerank_after_series_adjustment, enabled)
        self.refresh_locked_mapping_status()
        self.refresh_series_bias_table()
        self.refresh_distribution_preview()

    def refresh_series_bias_table(self, *args):
        locked_mapping = raw_locked_mapping(prefs, self.db) or {}
        mapping = saved_position_inflation(locked_mapping)
        curve = saved_score_percentile_curve(locked_mapping)
        rows = series_bias_rows(
            mapping,
            curve,
            self.series_correction_enabled.isChecked(),
            float(combo_data(self.correction_strength, 0.50)),
            percentile_penalty_pref(prefs['max_retention_penalty']),
        )
        set_series_bias_table_rows(self.series_bias_table, rows)

    def refresh_locked_mapping_status(self, *args):
        set_label_text(
            self.locked_map_status,
            locked_mapping_status_text(
                prefs,
                self.locked_mapping_status_settings(),
                self.db,
            ),
        )
        set_button_text(
            self.unlock_map_button,
            locked_mapping_action_text(prefs, self.db),
        )
        set_label_text(
            self.locked_map_detail,
            locked_mapping_detail_text(prefs, self.db),
        )
        set_widget_enabled(
            self.unlock_map_button,
            locked_mapping_action_enabled(prefs, self.db),
        )

    def locked_mapping_status_settings(self):
        settings = settings_from_prefs(self.db)
        settings.series_correction_enabled = (
            self.series_correction_enabled.isChecked()
        )
        settings.correction_strength = float(
            combo_data(self.correction_strength, 0.50)
        )
        return settings

    def on_unlock_map_clicked(self, *args):
        if update_locked_mapping_preferences(
            prefs,
            lambda: confirm_unlock_locked_mapping(self),
            self.db,
        ):
            self.refresh_locked_mapping_status()
            self.refresh_series_bias_table()

    def on_distribution_type_changed(self, *args):
        self.sync_distribution_tab_from_type()
        self.refresh_distribution_preview()

    def on_distribution_tab_changed(self, *args):
        distribution_type = distribution_type_for_index(
            current_tab_index(self.distribution_tabs),
        )
        if hasattr(self.distribution_type, 'blockSignals'):
            self.distribution_type.blockSignals(True)
            set_combo_data(self.distribution_type, distribution_type)
            self.distribution_type.blockSignals(False)
        else:
            set_combo_data(self.distribution_type, distribution_type)
        self.refresh_distribution_preview()

    def sync_distribution_tab_from_type(self):
        set_current_tab_index(
            self.distribution_tabs,
            distribution_index_for_type(
                combo_data(self.distribution_type, DISTRIBUTION_UNIFORM),
            ),
        )

    def on_uniform_step_preset_changed(self, *args):
        self.uniform_step_manual.setText(
            format_distribution_number(
                preset_numeric_value(combo_data(self.uniform_step_preset, 1.0), 1.0)
            )
        )
        self.refresh_distribution_preview()

    def on_bell_curve_variety_changed(self, *args):
        self.bell_curve_std_dev.setText(
            format_distribution_number(
                preset_numeric_value(
                    preset_numeric_data_for_key(
                        combo_data(self.bell_curve_variety, BELL_CURVE_BALANCED),
                        BELL_CURVE_PRESETS,
                        0.85,
                    ),
                    0.85,
                )
            )
        )
        self.refresh_distribution_preview()

    def on_bell_curve_peak_preset_changed(self, *args):
        self.bell_curve_peak_percent.setText(
            format_distribution_number(
                preset_numeric_value(combo_data(self.bell_curve_peak_preset, 50.0), 50.0)
            )
        )
        self.refresh_distribution_preview()

    def on_positive_skew_level_changed(self, *args):
        self.positive_skew_percent.setText(
            format_distribution_number(
                preset_numeric_value(
                    preset_numeric_data_for_key(
                        combo_data(self.positive_skew_level, POSITIVE_SKEW_MAINSTREAM),
                        POSITIVE_SKEW_PRESETS,
                        75.0,
                    ),
                    75.0,
                )
            )
        )
        self.refresh_distribution_preview()

    def on_j_curve_exclusivity_changed(self, *args):
        self.j_curve_power.setText(
            format_distribution_number(
                preset_numeric_value(
                    preset_numeric_data_for_key(
                        combo_data(self.j_curve_exclusivity, J_CURVE_PRESTIGIOUS),
                        J_CURVE_PRESETS,
                        3.5,
                    ),
                    3.5,
                )
            )
        )
        self.refresh_distribution_preview()

    def refresh_distribution_preview(self, *args):
        self.distribution_preview.set_bars(
            distribution_preview_bars(current_distribution_preview_settings(self))
        )


class DebugOptionsDialog(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(_('GRating Debug Options'))

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.debug_diagnostics = QCheckBox(_('Debug diagnostics'), self)
        self.debug_diagnostics.setChecked(bool(prefs['debug_diagnostics']))
        layout.addWidget(self.debug_diagnostics)

        buttons = create_dialog_buttons(self)
        connect_signal(getattr(buttons, 'accepted', None), self.accept)
        connect_signal(getattr(buttons, 'rejected', None), self.reject)
        layout.addWidget(buttons)

    def save_settings(self):
        prefs['debug_diagnostics'] = self.debug_diagnostics.isChecked()


def settings_from_prefs(db=None):
    output_format = clean_text(prefs['output_format']) or 'percentile'
    series_enabled = bool(prefs['series_correction_enabled'])
    adjustment_mode = (
        clean_text(prefs['percentile_adjustment_mode'])
        or ADJUSTMENT_DIRECT_PENALTY
    )
    if not series_enabled:
        adjustment_mode = ADJUSTMENT_DIRECT_PENALTY
    return RunSettings(
        output_percentile_field=clean_text(prefs['output_percentile_field']),
        raw_percentile_field='',
        adjusted_rating_field=clean_text(prefs['adjusted_rating_field']),
        output_format=output_format,
        number_min=float(prefs['number_min']),
        number_max=float(prefs['number_max']),
        star_granularity=stored_star_granularity(
            output_format,
            prefs['star_granularity'],
        ),
        distribution_type=clean_text(prefs['distribution_type']) or DISTRIBUTION_UNIFORM,
        percentile_adjustment_mode=adjustment_mode,
        uniform_step=float(prefs['uniform_step']),
        bell_curve_variety=weighted_preset_key(
            prefs['bell_curve_variety'],
            BELL_CURVE_PRESETS,
            BELL_CURVE_BALANCED,
        ),
        bell_curve_std_dev=float(prefs['bell_curve_std_dev']),
        bell_curve_peak_percent=parse_bounded_float(
            prefs['bell_curve_peak_percent'],
            50.0,
            10.0,
            90.0,
        ),
        positive_skew_level=weighted_preset_key(
            prefs['positive_skew_level'],
            POSITIVE_SKEW_PRESETS,
            POSITIVE_SKEW_MAINSTREAM,
        ),
        positive_skew_percent=float(prefs['positive_skew_percent']),
        j_curve_exclusivity=weighted_preset_key(
            prefs['j_curve_exclusivity'],
            J_CURVE_PRESETS,
            J_CURVE_PRESTIGIOUS,
        ),
        j_curve_power=float(prefs['j_curve_power']),
        series_correction_enabled=series_enabled,
        correction_strength=float(prefs['correction_strength']),
        retention_factor=0.0,
        max_retention_penalty=0.0,
        minimum_valid_ratings_warning=int(prefs['minimum_valid_ratings_warning']),
        minimum_series_pairs_warning=int(prefs['minimum_series_pairs_warning']),
        percentile_mapping_mode=get_percentile_mapping_mode(prefs, db),
        locked_curve_anchor_count=int(prefs['locked_curve_anchor_count']),
        locked_curve_endpoint_gap_fraction=float(
            prefs['locked_curve_endpoint_gap_fraction']
        ),
        debug_diagnostics=bool(prefs['debug_diagnostics']),
    )


def locked_mapping_is_present(config_prefs, db=None):
    return active_locked_mapping_is_present(config_prefs, db)


def locked_mapping_status_text(config_prefs, settings, db=None):
    mapping = load_locked_mapping(config_prefs, db)
    if mapping is None:
        raw_mapping = raw_locked_mapping(config_prefs, db)
        if isinstance(raw_mapping, dict) and raw_mapping:
            return _('invalid')
        return _('none')
    return _('active')


def format_locked_mapping_created_at(value):
    text = clean_text(value)
    if not text:
        return _('unknown')
    if 'T' in text:
        return text.split('T', 1)[0]
    return text


def locked_mapping_action_text(config_prefs, db=None):
    if locked_mapping_is_present(config_prefs, db):
        return _('Unlock map')
    return _('Lock map')


def locked_mapping_detail_text(config_prefs, db=None):
    raw_mapping = raw_locked_mapping(config_prefs, db)
    mapping = load_locked_mapping(config_prefs, db)
    if mapping is not None:
        return _('{} books, created {}').format(
            mapping.get('book_count', 0),
            format_locked_mapping_created_at(mapping.get('created_at', '')),
        )
    if isinstance(raw_mapping, dict) and raw_mapping:
        return _('Map version is incompatible')
    if get_percentile_mapping_mode(config_prefs, db) == REBUILD_AND_LOCK_MODE:
        return _('Next run a new map will be created')
    return ''


def locked_mapping_action_enabled(config_prefs, db=None):
    if locked_mapping_is_present(config_prefs, db):
        return True
    return get_percentile_mapping_mode(config_prefs, db) != REBUILD_AND_LOCK_MODE


def update_locked_mapping_preferences(config_prefs, confirm_callback=None, db=None):
    if not locked_mapping_is_present(config_prefs, db):
        set_percentile_mapping_mode(config_prefs, REBUILD_AND_LOCK_MODE, db)
        return True
    if callable(confirm_callback) and not confirm_callback():
        return False
    clear_locked_mapping(config_prefs, db)
    set_percentile_mapping_mode(config_prefs, REBUILD_AND_LOCK_MODE, db)
    return True


def confirm_unlock_locked_mapping(parent):
    try:
        from calibre.gui2 import question_dialog
        return question_dialog(
            parent,
            _('Unlock GRating map'),
            _('Clear the locked map? The next run will rebuild and lock a new map.'),
        )
    except Exception:
        return True


def current_distribution_preview_settings(widget):
    bell_curve_default = preset_numeric_value(
        preset_numeric_data_for_key(
            combo_data(widget.bell_curve_variety, BELL_CURVE_BALANCED),
            BELL_CURVE_PRESETS,
            0.85,
        ),
        0.85,
    )
    bell_curve_peak_default = preset_numeric_value(
        combo_data(widget.bell_curve_peak_preset, 50.0),
        50.0,
    )
    positive_skew_default = preset_numeric_value(
        preset_numeric_data_for_key(
            combo_data(widget.positive_skew_level, POSITIVE_SKEW_MAINSTREAM),
            POSITIVE_SKEW_PRESETS,
            75.0,
        ),
        75.0,
    )
    j_curve_default = preset_numeric_value(
        preset_numeric_data_for_key(
            combo_data(widget.j_curve_exclusivity, J_CURVE_PRESTIGIOUS),
            J_CURVE_PRESETS,
            3.5,
        ),
        3.5,
    )

    return RunSettings(
        output_percentile_field='',
        percentile_adjustment_mode=adjustment_mode_from_checkbox(
            getattr(widget, 'rerank_after_series_adjustment', None),
            checkbox_is_checked(
                getattr(widget, 'series_correction_enabled', None),
                True,
            ),
        ),
        distribution_type=combo_data(
            widget.distribution_type,
            DISTRIBUTION_UNIFORM,
        ),
        uniform_step=parse_float(
            widget.uniform_step_manual.text(),
            preset_numeric_value(combo_data(widget.uniform_step_preset, 1.0), 1.0),
        ),
        bell_curve_variety=weighted_preset_key(
            combo_data(widget.bell_curve_variety, BELL_CURVE_BALANCED),
            BELL_CURVE_PRESETS,
            BELL_CURVE_BALANCED,
        ),
        bell_curve_std_dev=parse_float(
            widget.bell_curve_std_dev.text(),
            bell_curve_default,
        ),
        bell_curve_peak_percent=parse_bounded_float(
            widget.bell_curve_peak_percent.text(),
            bell_curve_peak_default,
            10.0,
            90.0,
        ),
        positive_skew_level=weighted_preset_key(
            combo_data(widget.positive_skew_level, POSITIVE_SKEW_MAINSTREAM),
            POSITIVE_SKEW_PRESETS,
            POSITIVE_SKEW_MAINSTREAM,
        ),
        positive_skew_percent=parse_float(
            widget.positive_skew_percent.text(),
            positive_skew_default,
        ),
        j_curve_exclusivity=weighted_preset_key(
            combo_data(widget.j_curve_exclusivity, J_CURVE_PRESTIGIOUS),
            J_CURVE_PRESETS,
            J_CURVE_PRESTIGIOUS,
        ),
        j_curve_power=parse_float(widget.j_curve_power.text(), j_curve_default),
    )


def distribution_preview_bars(settings, bar_count=DISTRIBUTION_PREVIEW_BAR_COUNT):
    bar_count = max(1, int(bar_count))
    counts = [0] * bar_count
    sample_count = max(1, int(DISTRIBUTION_PREVIEW_SAMPLE_COUNT))
    denominator = max(1, sample_count - 1)
    bucket_width = 100.0 / float(bar_count)

    for index in range(sample_count):
        percentile = 100.0 * (float(index) / float(denominator))
        distributed = apply_distribution(percentile, settings)
        bucket_index = int(min(bar_count - 1, max(0, distributed // bucket_width)))
        counts[bucket_index] += 1

    maximum = max(counts) or 1
    return [float(count) / float(maximum) for count in counts]


def active_text_color(widget):
    palette = safe_call(widget, 'palette')
    if palette is not None and hasattr(palette, 'color'):
        color_group = palette_enum_value('ColorGroup', 'Active')
        color_role = palette_enum_value('ColorRole', 'WindowText')
        if color_role is None:
            color_role = palette_enum_value('ColorRole', 'Text')
        try:
            if color_group is not None and color_role is not None:
                return palette.color(color_group, color_role)
        except TypeError:
            pass
        try:
            if color_role is not None:
                return palette.color(color_role)
        except TypeError:
            pass
    return qt_black()


def use_placeholder_color_when_disabled(widget):
    palette = safe_call(widget, 'palette')
    if palette is None or not hasattr(palette, 'color'):
        return
    disabled_group = palette_enum_value('ColorGroup', 'Disabled')
    placeholder_role = palette_enum_value('ColorRole', 'PlaceholderText')
    if placeholder_role is None:
        return
    color = palette_color(palette, placeholder_role)
    if color is None:
        return
    for role_name in ('WindowText', 'Text', 'ButtonText'):
        role = palette_enum_value('ColorRole', role_name)
        if role is not None:
            set_palette_color(palette, disabled_group, role, color)
    if hasattr(widget, 'setPalette'):
        widget.setPalette(palette)


def palette_color(palette, role):
    active_group = palette_enum_value('ColorGroup', 'Active')
    if active_group is not None:
        try:
            return palette.color(active_group, role)
        except TypeError:
            pass
    try:
        return palette.color(role)
    except TypeError:
        return None


def set_palette_color(palette, color_group, role, color):
    if not hasattr(palette, 'setColor'):
        return
    if color_group is not None:
        try:
            palette.setColor(color_group, role, color)
            return
        except TypeError:
            pass
    try:
        palette.setColor(role, color)
    except TypeError:
        pass


def palette_enum_value(enum_name, member_name):
    enum = getattr(QPalette, enum_name, QPalette)
    return getattr(enum, member_name, None)


def qt_black():
    global_color = getattr(Qt, 'GlobalColor', None)
    if global_color is not None and hasattr(global_color, 'black'):
        return global_color.black
    return getattr(Qt, 'black', 0)


def widget_dimension(widget, name, default):
    try:
        value = getattr(widget, name)()
    except Exception:
        return default
    if value is None:
        return default
    return value


def add_combo_item(combo, label, data):
    if hasattr(combo, 'addItem'):
        combo.addItem(label, data)


def add_numeric_preset_items(combo, presets):
    for label, value in presets:
        add_combo_item(combo, label, value)


def add_weighted_preset_items(combo, presets):
    for label, key, value in presets:
        add_combo_item(combo, label, key)


def set_combo_data(combo, data):
    if not hasattr(combo, 'findData') or not hasattr(combo, 'setCurrentIndex'):
        return
    index = combo.findData(data)
    if index >= 0:
        combo.setCurrentIndex(index)


def combo_data(combo, default):
    if hasattr(combo, 'currentData'):
        value = combo.currentData()
        if value not in (None, ''):
            return value
    return default


def combo_data_allow_empty(combo, default):
    if hasattr(combo, 'currentData'):
        value = combo.currentData()
        if value is not None:
            return value
    return default


def checkbox_is_checked(checkbox, default=False):
    if checkbox is not None and hasattr(checkbox, 'isChecked'):
        return checkbox.isChecked()
    return bool(default)


def refresh_field_combo(combo, db, current, role, output_format, required):
    current = clean_text(current)
    if hasattr(combo, 'clear'):
        combo.clear()
    if hasattr(combo, 'setEditable'):
        combo.setEditable(db is None)
    if not required:
        add_combo_item(combo, _('-- None --'), '')

    fields = compatible_custom_columns(db, role, output_format)
    for field in fields:
        add_combo_item(combo, field['label'], field['lookup_name'])

    if current and not any(field['lookup_name'] == current for field in fields):
        add_combo_item(combo, _('{} (saved)').format(current), current)
    set_combo_data(combo, current)


def connect_signal(signal, slot):
    if hasattr(signal, 'connect'):
        signal.connect(slot)


def create_dialog_buttons(parent):
    try:
        standard_button = QDialogButtonBox.StandardButton
        ok = standard_button.Ok
        cancel = standard_button.Cancel
    except AttributeError:
        ok = getattr(QDialogButtonBox, 'Ok', 0)
        cancel = getattr(QDialogButtonBox, 'Cancel', 0)
    return QDialogButtonBox(ok | cancel, parent)


def config_dialog_size_from_prefs():
    return QSize(
        bounded_int(
            prefs['config_dialog_width'],
            dimension_value(CONFIG_DIALOG_DEFAULT_SIZE, 'width', 760),
            dimension_value(CONFIG_DIALOG_MINIMUM_SIZE, 'width', 620),
        ),
        bounded_int(
            prefs['config_dialog_height'],
            dimension_value(CONFIG_DIALOG_DEFAULT_SIZE, 'height', 640),
            dimension_value(CONFIG_DIALOG_MINIMUM_SIZE, 'height', 400),
        ),
    )


def save_config_dialog_geometry(widget):
    global SESSION_CONFIG_DIALOG_POSITION
    window = top_level_widget(widget)
    size = safe_call(window, 'size')
    pos = safe_call(window, 'pos')
    width = dimension_value(size, 'width', None)
    height = dimension_value(size, 'height', None)
    x_pos = dimension_value(pos, 'x', None)
    y_pos = dimension_value(pos, 'y', None)
    if width is not None and height is not None:
        prefs['config_dialog_width'] = bounded_int(
            width,
            dimension_value(CONFIG_DIALOG_DEFAULT_SIZE, 'width', 760),
            dimension_value(CONFIG_DIALOG_MINIMUM_SIZE, 'width', 620),
        )
        prefs['config_dialog_height'] = bounded_int(
            height,
            dimension_value(CONFIG_DIALOG_DEFAULT_SIZE, 'height', 640),
            dimension_value(CONFIG_DIALOG_MINIMUM_SIZE, 'height', 400),
        )
    if x_pos is not None and y_pos is not None:
        SESSION_CONFIG_DIALOG_POSITION = (int(x_pos), int(y_pos))


def restore_config_dialog_position(widget):
    if getattr(widget, '_position_restored', False):
        return
    if SESSION_CONFIG_DIALOG_POSITION is None:
        widget._position_restored = True
        return
    window = top_level_widget(widget)
    if hasattr(window, 'move'):
        try:
            window.move(SESSION_CONFIG_DIALOG_POSITION[0], SESSION_CONFIG_DIALOG_POSITION[1])
        except TypeError:
            pass
    widget._position_restored = True


def top_level_widget(widget):
    if hasattr(widget, 'window'):
        try:
            window = widget.window()
            if window is not None:
                return window
        except Exception:
            pass
    return widget


def safe_call(obj, name):
    if obj is None or not hasattr(obj, name):
        return None
    value = getattr(obj, name)
    if callable(value):
        try:
            return value()
        except Exception:
            return None
    return value


def dimension_value(obj, name, default):
    if obj is None:
        return default
    value = getattr(obj, name, default)
    if callable(value):
        try:
            value = value()
        except Exception:
            return default
    return default if value is None else value


def bounded_int(value, default, minimum):
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = int(default)
    return max(int(minimum), number)


def configure_series_bias_table(table):
    if hasattr(table, 'setColumnCount'):
        table.setColumnCount(3)
    if hasattr(table, 'setHorizontalHeaderLabels'):
        table.setHorizontalHeaderLabels([
            _('Position'),
            _('Bias @100'),
            _('Correction @100'),
        ])
    if hasattr(table, 'setEditTriggers'):
        edit_triggers = getattr(QTableWidget, 'EditTrigger', None)
        if edit_triggers is not None and hasattr(edit_triggers, 'NoEditTriggers'):
            table.setEditTriggers(edit_triggers.NoEditTriggers)
    if hasattr(table, 'setSelectionMode'):
        selection_mode = getattr(QTableWidget, 'SelectionMode', None)
        if selection_mode is not None and hasattr(selection_mode, 'NoSelection'):
            table.setSelectionMode(selection_mode.NoSelection)
    if hasattr(table, 'setVerticalScrollBarPolicy'):
        scroll_bar_policy = getattr(Qt, 'ScrollBarPolicy', Qt)
        always_off = getattr(scroll_bar_policy, 'ScrollBarAlwaysOff', None)
        if always_off is not None:
            table.setVerticalScrollBarPolicy(always_off)
    if hasattr(table, 'setAlternatingRowColors'):
        table.setAlternatingRowColors(True)
    if hasattr(table, 'verticalHeader'):
        header = table.verticalHeader()
        if header is not None and hasattr(header, 'setVisible'):
            header.setVisible(False)
    if hasattr(table, 'horizontalHeader'):
        header = table.horizontalHeader()
        if header is not None and hasattr(header, 'setSectionResizeMode'):
            resize_mode = getattr(QHeaderView, 'ResizeMode', QHeaderView)
            resize_to_contents = getattr(resize_mode, 'ResizeToContents', None)
            stretch = getattr(resize_mode, 'Stretch', None)
            if resize_to_contents is not None:
                header.setSectionResizeMode(0, resize_to_contents)
                header.setSectionResizeMode(1, resize_to_contents)
            if stretch is not None:
                header.setSectionResizeMode(2, stretch)
        if header is not None and hasattr(header, 'setStretchLastSection'):
            header.setStretchLastSection(True)


def saved_position_inflation(mapping):
    if not isinstance(mapping, dict):
        return {}
    position_inflation = mapping.get('position_inflation', {})
    if not isinstance(position_inflation, dict):
        return {}
    normalized = {}
    for position in series_bias_positions():
        if position not in position_inflation:
            continue
        try:
            normalized[position] = float(position_inflation[position])
        except (TypeError, ValueError):
            continue
    return normalized


def saved_score_percentile_curve(mapping):
    if not isinstance(mapping, dict):
        return []
    curve = mapping.get('score_percentile_curve', [])
    if not isinstance(curve, list):
        return []
    return curve


def series_bias_positions():
    return ['1', '2', '3', '4', '5', '6+']


def rerank_after_series_help_text():
    return _(
        'Enabled: rerank the Rating field after series penalties. Disabled: '
        'write direct penalty values.'
    )


def adjustment_mode_from_checkbox(checkbox, series_enabled=True):
    if not series_enabled:
        return ADJUSTMENT_DIRECT_PENALTY
    if checkbox is not None and hasattr(checkbox, 'isChecked'):
        if checkbox.isChecked():
            return ADJUSTMENT_ADJUSTED_RANK
    return ADJUSTMENT_DIRECT_PENALTY


def series_bias_help_text():
    return _(
        'Boosts use vote retention: 75-100% of book 1 = 0.75x, '
        '50-75% = 1.50x, 25-50% = 1.75x, and 0-25% = 1.25x '
        'only for positions 4+. If retention from the previous whole-number '
        'book is 0-25%, bias is multiplied by 0.25x. Books without vote '
        'counts receive no series bias. Correction shows base bias multiplied '
        'by correction strength; retention affects the multiplier only. '
        'The book-1 cap prevents penalties from lowering later books below '
        'book 1 and never raises books. Position 1 is never corrected.'
    )


def series_bias_rows(
    position_inflation,
    score_percentile_curve,
    enabled,
    strength,
    max_retention_penalty=0.0,
):
    rows = []
    correction_strength = float(strength) if enabled else 0.0
    for position in series_bias_positions():
        bias = position_inflation.get(position, None)
        correction = (
            None if bias is None
            else 0.0 if position == '1'
            else correction_strength * bias
        )
        rows.append((
            position,
            format_series_impact_value(bias),
            format_series_impact_value(correction),
        ))
    return rows


def format_series_impact_value(value):
    if value is None:
        return '--'
    return '{:.2f}'.format(float(value))


def set_series_bias_table_rows(table, rows):
    if hasattr(table, 'setRowCount'):
        table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            set_series_bias_table_item(table, row_index, column_index, value)
    resize_series_bias_table_columns(table)
    set_series_bias_table_content_height(table, len(rows))


def resize_series_bias_table_columns(table):
    if hasattr(table, 'resizeColumnToContents'):
        table.resizeColumnToContents(0)
        table.resizeColumnToContents(1)
    widen_series_bias_column(table)
    if hasattr(table, 'horizontalHeader'):
        header = table.horizontalHeader()
        if header is not None and hasattr(header, 'setStretchLastSection'):
            header.setStretchLastSection(True)


def widen_series_bias_column(table):
    if not hasattr(table, 'columnWidth') or not hasattr(table, 'setColumnWidth'):
        return
    try:
        width = int(table.columnWidth(1))
    except Exception:
        return
    table.setColumnWidth(1, width + SERIES_BIAS_COLUMN_EXTRA_WIDTH)


def set_series_bias_table_content_height(table, row_count):
    height = series_bias_table_content_height(table, row_count)
    set_fixed_table_height(table, height)


def series_bias_table_content_height(table, row_count):
    header_height = horizontal_header_height(table)
    rows_height = series_bias_rows_height(table, row_count)
    frame = table_dimension_call(table, 'frameWidth', None, 1)
    return int(
        header_height
        + rows_height
        + (frame * 2)
        + SERIES_BIAS_TABLE_VERTICAL_PADDING
    )


def horizontal_header_height(table):
    header_height = header_dimension(table, 'horizontalHeader', 'height')
    if header_height is not None:
        return header_height

    header = safe_call(table, 'horizontalHeader')
    if header is not None:
        size_hint = safe_call(header, 'sizeHint')
        hint_height = dimension_value(size_hint, 'height', None)
        if hint_height is not None:
            try:
                return int(hint_height)
            except (TypeError, ValueError):
                pass
    return SERIES_BIAS_TABLE_FALLBACK_HEADER_HEIGHT


def series_bias_rows_height(table, row_count):
    header = safe_call(table, 'verticalHeader')
    header_length = dimension_value(header, 'length', None)
    if header_length is not None:
        try:
            header_length = int(header_length)
        except (TypeError, ValueError):
            header_length = 0
        if header_length > 0:
            return header_length

    row_total = 0
    for row_index in range(max(0, int(row_count))):
        row_height = table_dimension_call(table, 'rowHeight', row_index, None)
        if row_height is None:
            row_height = table_dimension_call(
                table,
                'sizeHintForRow',
                row_index,
                SERIES_BIAS_TABLE_FALLBACK_ROW_HEIGHT,
            )
        row_total += row_height
    return row_total


def set_fixed_table_height(table, height):
    if hasattr(table, 'setFixedHeight'):
        table.setFixedHeight(height)
    else:
        if hasattr(table, 'setMinimumHeight'):
            table.setMinimumHeight(height)
        if hasattr(table, 'setMaximumHeight'):
            table.setMaximumHeight(height)


def header_dimension(table, header_name, dimension_name):
    header = safe_call(table, header_name)
    if header is None:
        return None
    value = dimension_value(header, dimension_name, None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def table_dimension_call(table, name, argument, default):
    if not hasattr(table, name):
        return int(default) if default is not None else None
    method = getattr(table, name)
    try:
        if argument is None:
            value = method()
        else:
            value = method(argument)
    except Exception:
        return int(default) if default is not None else None
    if value is None:
        return int(default) if default is not None else None
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default) if default is not None else None


def set_series_bias_table_item(table, row, column, value):
    if not hasattr(table, 'setItem'):
        return
    item = create_table_item(value)
    if item is not None:
        table.setItem(row, column, item)


def create_table_item(value):
    try:
        return QTableWidgetItem(str(value))
    except Exception:
        return None


def distribution_index_for_type(distribution_type):
    types = [
        DISTRIBUTION_UNIFORM,
        DISTRIBUTION_BELL_CURVE,
        DISTRIBUTION_POSITIVE_SKEW,
        DISTRIBUTION_J_CURVE,
    ]
    distribution_type = clean_text(distribution_type) or DISTRIBUTION_UNIFORM
    try:
        return types.index(distribution_type)
    except ValueError:
        return 0


def distribution_type_for_index(index):
    types = [
        DISTRIBUTION_UNIFORM,
        DISTRIBUTION_BELL_CURVE,
        DISTRIBUTION_POSITIVE_SKEW,
        DISTRIBUTION_J_CURVE,
    ]
    if 0 <= int(index) < len(types):
        return types[int(index)]
    return DISTRIBUTION_UNIFORM


def rating_type_index_for_format(output_format):
    formats = [
        'percentile',
        'decimal',
        'range',
        OUTPUT_FORMAT_STARS,
    ]
    output_format = output_format_for_ui(output_format)
    try:
        return formats.index(output_format)
    except ValueError:
        return 0


def rating_type_for_index(index):
    formats = [
        'percentile',
        'decimal',
        'range',
        OUTPUT_FORMAT_STARS,
    ]
    if 0 <= int(index) < len(formats):
        return formats[int(index)]
    return 'percentile'


def locked_rating_type_for_field(db, field):
    if field_datatype(db, field) == 'rating':
        return OUTPUT_FORMAT_STARS
    return None


def rating_field_allows_star_tab(db, field):
    field = clean_text(field)
    if not field:
        return True
    datatype = field_datatype(db, field)
    if not datatype:
        return True
    return datatype == 'rating'


def effective_rating_type_for_field(db, field, selected_rating_type):
    locked_type = locked_rating_type_for_field(db, field)
    if locked_type:
        return locked_type
    return selected_rating_type


def set_rating_type_tabs_enabled(tabs, locked_type, star_allowed=True):
    if not hasattr(tabs, 'setTabEnabled'):
        return
    allowed_index = None
    if locked_type:
        allowed_index = rating_type_index_for_format(locked_type)
    help_text = rating_type_help_text(locked_type, star_allowed)
    for index in range(4):
        enabled = allowed_index is None or index == allowed_index
        if index == rating_type_index_for_format(OUTPUT_FORMAT_STARS):
            enabled = enabled and bool(star_allowed)
        tabs.setTabEnabled(index, enabled)
        if hasattr(tabs, 'setTabToolTip'):
            tabs.setTabToolTip(index, '' if enabled else help_text)


def rating_type_help_text(locked_type=None, star_allowed=True):
    if locked_type:
        return rating_type_lock_help_text()
    if not star_allowed:
        return star_rating_unavailable_help_text()
    return ''


def rating_type_lock_help_text():
    return _(
        'The selected Rating field locks the rating type. Change Rating to '
        '-- None -- to choose a different rating type.'
    )


def star_rating_unavailable_help_text():
    return _(
        'The selected Rating field cannot store star ratings. Change Rating '
        'to -- None -- to choose Star rating.'
    )


def set_current_tab_index(tabs, index):
    if hasattr(tabs, 'setCurrentIndex'):
        tabs.setCurrentIndex(int(index))


def current_tab_index(tabs):
    if hasattr(tabs, 'currentIndex'):
        try:
            return int(tabs.currentIndex())
        except Exception:
            return 0
    return 0


def preset_numeric_value(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def weighted_preset_key(value, presets, default):
    valid_keys = {key for label, key, preset_value in presets}
    if value in valid_keys:
        return value
    try:
        numeric_key = int(value)
    except (TypeError, ValueError):
        return default
    if numeric_key in valid_keys:
        return numeric_key
    return default


def preset_numeric_data_for_key(selected_key, presets, default):
    selected_key = weighted_preset_key(selected_key, presets, None)
    for label, key, value in presets:
        if key == selected_key:
            return value
    return default


def matching_numeric_preset(value, presets, default):
    value = preset_numeric_value(value, default)
    for label, preset_value in presets:
        if float(preset_value) == value:
            return preset_value
    return float(default)


def format_distribution_number(value):
    value = float(value)
    if value == int(value):
        return str(int(value))
    return str(value)


def clean_text(value):
    return str(value or '').strip()


def output_format_for_ui(value):
    value = clean_text(value) or 'percentile'
    if value in ('stars_whole', 'stars_half'):
        return OUTPUT_FORMAT_STARS
    return value


def selected_output_format(value, half_stars_enabled):
    value = clean_text(value) or 'percentile'
    if value == OUTPUT_FORMAT_STARS:
        if half_stars_enabled:
            return 'stars_half'
        return 'stars_whole'
    return value


def stored_star_granularity(output_format, granularity):
    output_format = clean_text(output_format)
    if output_format == 'stars_whole':
        return 'whole'
    if output_format == 'stars_half':
        return 'half'
    granularity = clean_text(granularity)
    if granularity == 'whole':
        return 'whole'
    return 'half'


def set_widget_visible(widget, visible):
    if hasattr(widget, 'setVisible'):
        widget.setVisible(bool(visible))


def set_widget_enabled(widget, enabled):
    if hasattr(widget, 'setEnabled'):
        widget.setEnabled(bool(enabled))


def set_tool_tip(widget, text):
    if hasattr(widget, 'setToolTip'):
        widget.setToolTip(text)
    if hasattr(widget, 'viewport'):
        viewport = widget.viewport()
        if viewport is not None and hasattr(viewport, 'setToolTip'):
            viewport.setToolTip(text)


def set_label_text(label, text):
    if hasattr(label, 'setText'):
        label.setText(text)


def set_button_text(button, text):
    if hasattr(button, 'setText'):
        button.setText(text)


def set_fixed_widget_width(widget, width):
    if hasattr(widget, 'setFixedWidth'):
        widget.setFixedWidth(int(width))
        return
    if hasattr(widget, 'setMinimumWidth'):
        widget.setMinimumWidth(int(width))
    if hasattr(widget, 'setMaximumWidth'):
        widget.setMaximumWidth(int(width))


def parse_float(value, default):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def parse_bounded_float(value, default, minimum, maximum):
    value = parse_float(value, default)
    return max(float(minimum), min(float(maximum), float(value)))


def percentile_penalty_pref(value):
    value = float(value)
    if 0.0 < value <= 1.0:
        return value * 100.0
    return value
