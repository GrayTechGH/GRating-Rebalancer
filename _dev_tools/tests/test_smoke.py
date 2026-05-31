#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


from __future__ import print_function

import importlib.util
import os
import sys
import types
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLUGIN_PACKAGE = 'calibre_plugins.GRating_Rebalancer'


def load_module(module_name, path):
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FakeJSONConfig(dict):

    created_namespaces = []

    def __init__(self, namespace):
        dict.__init__(self)
        self.namespace = namespace
        self.defaults = {}
        FakeJSONConfig.created_namespaces.append(namespace)

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        return self.defaults[key]


class FakeWidget(object):

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        def method(*args, **kwargs):
            if name.startswith('is') or name.startswith('has'):
                return False
            if name in ('text', 'currentData'):
                return ''
            if name == 'value':
                return 0
            if name == 'findData':
                return -1
            return None
        return method


class FakeSize(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height


class FakeDBPrefs(dict):

    def __bool__(self):
        raise AttributeError("'DBPrefs' object has no attribute '__bool__'")


class FakePalette(object):

    class ColorGroup(object):
        Active = 'active'
        Disabled = 'disabled'

    class ColorRole(object):
        PlaceholderText = 'placeholder'
        WindowText = 'window'
        Text = 'text'
        ButtonText = 'button'

    def __init__(self):
        self.colors = {('active', 'placeholder'): 'placeholder-color'}
        self.set_calls = []

    def color(self, group, role=None):
        if role is None:
            return self.colors.get(('active', group))
        return self.colors.get((group, role))

    def setColor(self, group, role, color):
        self.set_calls.append((group, role, color))
        self.colors[(group, role)] = color


class FakePaletteWidget(object):

    def __init__(self):
        self._palette = FakePalette()
        self.applied_palette = None

    def palette(self):
        return self._palette

    def setPalette(self, palette):
        self.applied_palette = palette


def install_fake_calibre_modules():
    calibre = sys.modules.setdefault('calibre', types.ModuleType('calibre'))
    customize = types.ModuleType('calibre.customize')
    gui2 = types.ModuleType('calibre.gui2')
    actions = types.ModuleType('calibre.gui2.actions')
    utils = types.ModuleType('calibre.utils')
    config = types.ModuleType('calibre.utils.config')

    class InterfaceActionBase(object):
        pass

    class InterfaceAction(object):
        pass

    customize.InterfaceActionBase = InterfaceActionBase
    actions.InterfaceAction = InterfaceAction
    config.JSONConfig = FakeJSONConfig
    gui2.actions = actions
    utils.config = config
    calibre.customize = customize
    calibre.gui2 = gui2
    calibre.utils = utils

    sys.modules['calibre.customize'] = customize
    sys.modules['calibre.gui2'] = gui2
    sys.modules['calibre.gui2.actions'] = actions
    sys.modules['calibre.utils'] = utils
    sys.modules['calibre.utils.config'] = config


def install_fake_qt_modules():
    qt = sys.modules.setdefault('qt', types.ModuleType('qt'))
    core = types.ModuleType('qt.core')

    for name in (
        'QApplication',
        'QCheckBox',
        'QDialog',
        'QDialogButtonBox',
        'QEvent',
        'QFormLayout',
        'QHeaderView',
        'QHBoxLayout',
        'QLabel',
        'QLineEdit',
        'QMenu',
        'QMessageBox',
        'QPainter',
        'QPalette',
        'QComboBox',
        'QSpinBox',
        'QTabWidget',
        'QTableWidget',
        'QTableWidgetItem',
        'QTimer',
        'QToolButton',
        'QVBoxLayout',
        'QWidget',
    ):
        setattr(core, name, FakeWidget)

    core.QApplication.keyboardModifiers = staticmethod(lambda: 0)
    core.QApplication.mouseButtons = staticmethod(lambda: 0)
    core.QTimer.singleShot = staticmethod(lambda delay, callback: callback())
    core.QToolButton.MenuButtonPopup = 1
    core.QSize = FakeSize
    core.QHeaderView.ResizeMode = types.SimpleNamespace(
        ResizeToContents=1,
        Stretch=2,
    )
    core.Qt = types.SimpleNamespace(
        GlobalColor=types.SimpleNamespace(black=0),
        TextFormat=types.SimpleNamespace(RichText=1),
        TextInteractionFlag=types.SimpleNamespace(TextBrowserInteraction=1),
        KeyboardModifier=types.SimpleNamespace(
            ControlModifier=1,
            ShiftModifier=2,
        ),
        MouseButton=types.SimpleNamespace(LeftButton=4),
    )
    core.QEvent.Type = types.SimpleNamespace(MouseButtonPress=1)
    qt.core = core
    sys.modules['qt.core'] = core


def install_plugin_package():
    sys.modules.setdefault('calibre_plugins', types.ModuleType('calibre_plugins'))
    package = sys.modules.setdefault(PLUGIN_PACKAGE, types.ModuleType(PLUGIN_PACKAGE))
    package.__path__ = [ROOT]
    return package


def release_file_candidates():
    ignored_dirs = {
        '_dev_tools',
        '_docs',
        '__pycache__',
        'resources',
        'translations',
    }
    ignored_suffixes = ('.pyc', '.pyo', '.pyd', '.zip')
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            name for name in dirnames
            if name not in ignored_dirs and not name.startswith('.')
        ]
        for filename in filenames:
            if filename.startswith('.'):
                continue
            if filename.endswith(ignored_suffixes):
                continue
            path = os.path.join(dirpath, filename)
            files.append(os.path.relpath(path, ROOT).replace(os.sep, '/'))
    return sorted(files)


class GRatingSmokeTests(unittest.TestCase):

    def setUp(self):
        install_fake_calibre_modules()
        install_fake_qt_modules()
        install_plugin_package()

    def test_wrapper_metadata_imports_without_qt_modules(self):
        sys.modules.pop('qt.core', None)

        module = load_module(
            PLUGIN_PACKAGE + '.__init__',
            os.path.join(ROOT, '__init__.py'),
        )

        self.assertEqual('GRating Rebalancer', module.GRatingRebalancerPlugin.name)
        self.assertEqual((1, 0, 0), module.GRatingRebalancerPlugin.version)

    def test_actual_plugin_uses_template_import_package(self):
        module = load_module(
            PLUGIN_PACKAGE + '.__init__',
            os.path.join(ROOT, '__init__.py'),
        )

        self.assertEqual(
            'calibre_plugins.GRating_Rebalancer.ui:InterfacePlugin',
            module.GRatingRebalancerPlugin.actual_plugin,
        )

    def test_toolbar_action_label_uses_short_icon_label(self):
        module = load_module(
            PLUGIN_PACKAGE + '.ui',
            os.path.join(ROOT, 'ui.py'),
        )

        self.assertEqual(
            'GRating RB',
            module.InterfacePlugin.action_spec[0],
        )

    def test_toolbar_action_widgets_resolve_associated_toolbar_button(self):
        module = load_module(
            PLUGIN_PACKAGE + '.ui',
            os.path.join(ROOT, 'ui.py'),
        )

        button = object()

        class FakeToolbar(object):

            def widgetForAction(self, action):
                return button

        class FakeAction(object):

            def associatedWidgets(self):
                return [toolbar]

        toolbar = FakeToolbar()
        action = FakeAction()

        self.assertEqual(
            [toolbar, button],
            module.action_widgets(action, types.SimpleNamespace()),
        )

    def test_toolbar_ctrl_shift_uses_keyboard_modifiers_only(self):
        module = load_module(
            PLUGIN_PACKAGE + '.ui',
            os.path.join(ROOT, 'ui.py'),
        )

        original_keyboard = module.QApplication.keyboardModifiers
        original_mouse = module.QApplication.mouseButtons
        try:
            module.QApplication.keyboardModifiers = staticmethod(lambda: 3)
            module.QApplication.mouseButtons = staticmethod(lambda: 0)
            self.assertTrue(module.ctrl_shift_icon_click())

            module.QApplication.keyboardModifiers = staticmethod(lambda: 2)
            self.assertFalse(module.ctrl_shift_icon_click())
        finally:
            module.QApplication.keyboardModifiers = original_keyboard
            module.QApplication.mouseButtons = original_mouse

    def test_config_uses_grating_json_namespace(self):
        install_fake_qt_modules()
        FakeJSONConfig.created_namespaces[:] = []

        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        self.assertIn('plugins/GRating_Rebalancer', FakeJSONConfig.created_namespaces)
        self.assertEqual('', module.prefs.defaults['output_percentile_field'])
        self.assertEqual('uniform', module.prefs.defaults['distribution_type'])
        self.assertEqual(
            'direct_penalty',
            module.prefs.defaults['percentile_adjustment_mode'],
        )
        self.assertEqual(0.01, module.prefs.defaults['uniform_step'])
        self.assertEqual(
            module.BELL_CURVE_BALANCED,
            module.prefs.defaults['bell_curve_variety'],
        )
        self.assertEqual(50.0, module.prefs.defaults['bell_curve_peak_percent'])
        self.assertEqual(
            module.POSITIVE_SKEW_MAINSTREAM,
            module.prefs.defaults['positive_skew_level'],
        )
        self.assertEqual(
            module.J_CURVE_PRESTIGIOUS,
            module.prefs.defaults['j_curve_exclusivity'],
        )
        self.assertTrue(module.prefs.defaults['series_correction_enabled'])
        self.assertEqual(0.50, module.prefs.defaults['correction_strength'])
        self.assertEqual(0.0, module.prefs.defaults['retention_factor'])
        self.assertEqual(0.0, module.prefs.defaults['max_retention_penalty'])
        self.assertEqual(21, module.prefs.defaults['locked_curve_anchor_count'])
        self.assertFalse(module.prefs.defaults['per_library_mapping_enabled'])
        self.assertEqual(
            {},
            module.prefs.defaults['locked_percentile_mappings_by_library'],
        )
        self.assertEqual(
            {},
            module.prefs.defaults['percentile_mapping_modes_by_library'],
        )

    def test_output_format_ui_helpers_fold_star_modes(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        self.assertEqual('stars', module.output_format_for_ui('stars_whole'))
        self.assertEqual('stars', module.output_format_for_ui('stars_half'))
        self.assertEqual(
            'stars_whole',
            module.selected_output_format('stars', False),
        )
        self.assertEqual(
            'stars_half',
            module.selected_output_format('stars', True),
        )
        self.assertEqual(0, module.rating_type_index_for_format('percentile'))
        self.assertEqual(1, module.rating_type_index_for_format('decimal'))
        self.assertEqual(2, module.rating_type_index_for_format('range'))
        self.assertEqual(3, module.rating_type_index_for_format('stars_half'))
        self.assertEqual('stars', module.rating_type_for_index(3))

    def test_output_combo_data_allow_empty_preserves_none_selection(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        self.assertEqual(
            '',
            module.combo_data_allow_empty(
                types.SimpleNamespace(currentData=lambda: ''),
                '#previous_rating',
            ),
        )
        self.assertEqual(
            '#previous_rating',
            module.combo_data_allow_empty(
                types.SimpleNamespace(currentData=lambda: None),
                '#previous_rating',
            ),
        )

    def test_rating_custom_column_locks_rating_type_to_stars(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        db = types.SimpleNamespace(field_metadata={
            'rating': {'name': 'Rating', 'datatype': 'rating', 'is_custom': False},
            '#grating_stars_half': {
                'name': 'Grating Stars 1/2',
                'datatype': 'rating',
                'is_custom': True,
            },
            '#score': {'name': 'Score', 'datatype': 'float', 'is_custom': True},
        })

        self.assertEqual(
            'stars',
            module.locked_rating_type_for_field(db, '#grating_stars_half'),
        )
        self.assertEqual(
            'stars',
            module.locked_rating_type_for_field(db, 'rating'),
        )
        self.assertIsNone(module.locked_rating_type_for_field(db, '#score'))
        self.assertEqual(
            'stars',
            module.effective_rating_type_for_field(
                db,
                '#grating_stars_half',
                'percentile',
            ),
        )
        self.assertEqual(
            'percentile',
            module.effective_rating_type_for_field(db, '#score', 'percentile'),
        )
        self.assertFalse(module.rating_field_allows_star_tab(db, '#score'))
        self.assertTrue(module.rating_field_allows_star_tab(db, '#grating_stars_half'))
        self.assertTrue(module.rating_field_allows_star_tab(db, ''))

    def test_non_star_rating_field_disables_star_rating_tab(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        class FakeTabs(object):

            def __init__(self):
                self.enabled = {}
                self.tooltips = {}

            def setTabEnabled(self, index, enabled):
                self.enabled[index] = enabled

            def setTabToolTip(self, index, tooltip):
                self.tooltips[index] = tooltip

        tabs = FakeTabs()

        module.set_rating_type_tabs_enabled(tabs, None, star_allowed=False)

        self.assertTrue(tabs.enabled[0])
        self.assertTrue(tabs.enabled[1])
        self.assertTrue(tabs.enabled[2])
        self.assertFalse(tabs.enabled[3])
        self.assertIn('-- None --', tabs.tooltips[3])
        self.assertIn('Star rating', tabs.tooltips[3])

    def test_locked_rating_type_tabs_have_unlock_tooltip(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        class FakeTabs(object):

            def __init__(self):
                self.enabled = {}
                self.tooltips = {}

            def setTabEnabled(self, index, enabled):
                self.enabled[index] = enabled

            def setTabToolTip(self, index, tooltip):
                self.tooltips[index] = tooltip

        tabs = FakeTabs()

        module.set_rating_type_tabs_enabled(tabs, 'stars')

        self.assertFalse(tabs.enabled[0])
        self.assertFalse(tabs.enabled[1])
        self.assertFalse(tabs.enabled[2])
        self.assertTrue(tabs.enabled[3])
        self.assertIn('-- None --', tabs.tooltips[0])
        self.assertIn('rating type', tabs.tooltips[1])
        self.assertIn('-- None --', tabs.tooltips[2])
        self.assertEqual('', tabs.tooltips[3])

    def test_locked_mapping_status_text_reports_state(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        settings = module.RunSettings(output_percentile_field='#output')
        compatible_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'created_at': '2026-05-30T12:34:56Z',
            'book_count': 371,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
            'settings_fingerprint': locked_mapping.settings_fingerprint(
                settings,
                'raw_rating',
            ),
        }
        old_version_mapping = dict(compatible_mapping)
        old_version_mapping['mapping_version'] = -1

        self.assertEqual(
            'none',
            module.locked_mapping_status_text({
                'percentile_mapping_mode': 'recalculate_each_run',
            }, settings),
        )
        self.assertEqual(
            'none',
            module.locked_mapping_status_text({
                'percentile_mapping_mode': 'rebuild_and_lock',
            }, settings),
        )
        self.assertEqual(
            'Next run a new map will be created',
            module.locked_mapping_detail_text({
                'percentile_mapping_mode': 'rebuild_and_lock',
            }),
        )
        self.assertEqual(
            'active',
            module.locked_mapping_status_text({
                'locked_percentile_mapping': compatible_mapping,
            }, settings),
        )
        self.assertEqual(
            '371 books, created 2026-05-30',
            module.locked_mapping_detail_text({
                'locked_percentile_mapping': compatible_mapping,
            }),
        )
        self.assertEqual(
            'invalid',
            module.locked_mapping_status_text({
                'locked_percentile_mapping': old_version_mapping,
            }, settings),
        )
        self.assertEqual(
            'Map version is incompatible',
            module.locked_mapping_detail_text({
                'locked_percentile_mapping': old_version_mapping,
            }),
        )

    def test_locked_mapping_compatibility_ignores_user_controls(self):
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        original_settings = results.RunSettings(
            output_percentile_field='#output',
            series_correction_enabled=True,
            correction_strength=0.25,
            locked_curve_anchor_count=21,
            locked_curve_endpoint_gap_fraction=0.025,
        )
        changed_settings = results.RunSettings(
            output_percentile_field='#output',
            series_correction_enabled=False,
            correction_strength=1.0,
            locked_curve_anchor_count=101,
            locked_curve_endpoint_gap_fraction=0.10,
        )
        mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
            'settings_fingerprint': locked_mapping.settings_fingerprint(
                original_settings,
                'raw_rating',
            ),
        }

        self.assertTrue(locked_mapping.locked_mapping_is_compatible(
            mapping,
            changed_settings,
            'raw_rating',
        ))

    def test_locked_mapping_helpers_use_global_when_per_library_disabled(self):
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        global_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
        }
        library_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[2.0, 0.0], [4.0, 100.0]],
        }
        db = types.SimpleNamespace(library_path='C:\\Calibre\\Library A')
        key = locked_mapping.library_mapping_key(db)
        prefs_data = {
            'per_library_mapping_enabled': False,
            'locked_percentile_mapping': dict(global_mapping),
            'percentile_mapping_mode': 'use_locked_mapping',
            'locked_percentile_mappings_by_library': {key: library_mapping},
            'percentile_mapping_modes_by_library': {
                key: 'rebuild_and_lock',
            },
        }

        self.assertEqual(
            global_mapping,
            locked_mapping.load_locked_mapping(prefs_data, db),
        )
        self.assertEqual(
            'use_locked_mapping',
            locked_mapping.get_percentile_mapping_mode(prefs_data, db),
        )

        replacement = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[1.0, 0.0], [5.0, 100.0]],
        }
        locked_mapping.set_locked_mapping(prefs_data, replacement, db)
        locked_mapping.set_percentile_mapping_mode(
            prefs_data,
            'recalculate_each_run',
            db,
        )

        self.assertEqual(replacement, prefs_data['locked_percentile_mapping'])
        self.assertEqual(
            library_mapping,
            prefs_data['locked_percentile_mappings_by_library'][key],
        )
        self.assertEqual(
            'recalculate_each_run',
            prefs_data['percentile_mapping_mode'],
        )

    def test_locked_mapping_helpers_use_current_library_when_enabled(self):
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        global_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
        }
        library_a_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[1.0, 0.0], [4.0, 100.0]],
        }
        library_b_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[2.0, 0.0], [5.0, 100.0]],
        }
        db_a = types.SimpleNamespace(library_path='C:\\Calibre\\Library A')
        db_b = types.SimpleNamespace(new_api=types.SimpleNamespace(
            backend=types.SimpleNamespace(library_path='C:\\Calibre\\Library B'),
        ))
        key_a = locked_mapping.library_mapping_key(db_a)
        key_b = locked_mapping.library_mapping_key(db_b)
        prefs_data = {
            'per_library_mapping_enabled': True,
            'locked_percentile_mapping': global_mapping,
            'percentile_mapping_mode': 'use_locked_mapping',
            'locked_percentile_mappings_by_library': {
                key_a: dict(library_a_mapping),
                key_b: dict(library_b_mapping),
            },
            'percentile_mapping_modes_by_library': {
                key_a: 'rebuild_and_lock',
                key_b: 'use_locked_mapping',
            },
        }

        self.assertEqual(
            library_a_mapping,
            locked_mapping.load_locked_mapping(prefs_data, db_a),
        )
        self.assertEqual(
            library_b_mapping,
            locked_mapping.load_locked_mapping(prefs_data, db_b),
        )
        self.assertEqual(
            'rebuild_and_lock',
            locked_mapping.get_percentile_mapping_mode(prefs_data, db_a),
        )
        self.assertEqual(
            'use_locked_mapping',
            locked_mapping.get_percentile_mapping_mode(prefs_data, db_b),
        )

        locked_mapping.clear_locked_mapping(prefs_data, db_a)
        locked_mapping.set_percentile_mapping_mode(
            prefs_data,
            'use_locked_mapping',
            db_a,
        )

        self.assertEqual({}, prefs_data['locked_percentile_mappings_by_library'][key_a])
        self.assertEqual(
            library_b_mapping,
            prefs_data['locked_percentile_mappings_by_library'][key_b],
        )
        self.assertEqual(
            'use_locked_mapping',
            prefs_data['percentile_mapping_modes_by_library'][key_a],
        )
        self.assertEqual(
            'use_locked_mapping',
            prefs_data['percentile_mapping_mode'],
        )

    def test_locked_mapping_helpers_fallback_to_global_without_library_key(self):
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        global_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
        }
        prefs_data = {
            'per_library_mapping_enabled': True,
            'locked_percentile_mapping': dict(global_mapping),
            'percentile_mapping_mode': 'use_locked_mapping',
            'locked_percentile_mappings_by_library': {},
            'percentile_mapping_modes_by_library': {},
        }
        db_without_path = types.SimpleNamespace()

        self.assertEqual(
            global_mapping,
            locked_mapping.load_locked_mapping(prefs_data, db_without_path),
        )
        self.assertEqual(
            'use_locked_mapping',
            locked_mapping.get_percentile_mapping_mode(
                prefs_data,
                db_without_path,
            ),
        )

    def test_enabling_per_library_mapping_copies_global_map_to_current_library(self):
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        global_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
        }
        db = types.SimpleNamespace(library_path='C:\\Calibre\\Library A')
        key = locked_mapping.library_mapping_key(db)
        prefs_data = {
            'per_library_mapping_enabled': True,
            'locked_percentile_mapping': dict(global_mapping),
            'percentile_mapping_mode': 'use_locked_mapping',
            'locked_percentile_mappings_by_library': {},
            'percentile_mapping_modes_by_library': {},
        }

        self.assertTrue(
            locked_mapping.seed_library_mapping_from_global(prefs_data, db)
        )
        self.assertEqual(global_mapping, prefs_data['locked_percentile_mapping'])
        self.assertEqual(
            global_mapping,
            prefs_data['locked_percentile_mappings_by_library'][key],
        )
        self.assertEqual(
            'use_locked_mapping',
            prefs_data['percentile_mapping_modes_by_library'][key],
        )

    def test_locked_mapping_action_can_schedule_first_lock(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        prefs_without_map = {'percentile_mapping_mode': 'recalculate_each_run'}

        self.assertEqual('Lock map', module.locked_mapping_action_text(prefs_without_map))
        self.assertTrue(module.locked_mapping_action_enabled(prefs_without_map))
        self.assertTrue(module.update_locked_mapping_preferences(prefs_without_map))
        self.assertEqual('rebuild_and_lock', prefs_without_map['percentile_mapping_mode'])
        self.assertEqual('Lock map', module.locked_mapping_action_text(prefs_without_map))
        self.assertFalse(module.locked_mapping_action_enabled(prefs_without_map))

    def test_unlock_locked_mapping_preferences_confirms_and_sets_rebuild(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )

        valid_mapping = {
            'mapping_version': locked_mapping.MAPPING_VERSION,
            'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]],
        }
        accepted = {
            'locked_percentile_mapping': dict(valid_mapping),
            'percentile_mapping_mode': 'use_locked_mapping',
        }
        rejected = {
            'locked_percentile_mapping': dict(valid_mapping),
            'percentile_mapping_mode': 'use_locked_mapping',
        }

        self.assertTrue(
            module.update_locked_mapping_preferences(accepted, lambda: True)
        )
        self.assertEqual({}, accepted['locked_percentile_mapping'])
        self.assertEqual('rebuild_and_lock', accepted['percentile_mapping_mode'])
        self.assertFalse(
            module.update_locked_mapping_preferences(rejected, lambda: False)
        )
        self.assertEqual(valid_mapping, rejected['locked_percentile_mapping'])
        self.assertEqual('use_locked_mapping', rejected['percentile_mapping_mode'])

    def test_distribution_helpers_match_requested_defaults(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        self.assertEqual(0, module.distribution_index_for_type('uniform'))
        self.assertEqual('bell_curve', module.distribution_type_for_index(1))
        self.assertEqual('75', module.format_distribution_number(75.0))
        self.assertEqual(
            0.01,
            module.matching_numeric_preset(0.01, module.UNIFORM_STEP_PRESETS, 1.0),
        )
        self.assertEqual(
            0.85,
            module.preset_numeric_data_for_key(
                module.BELL_CURVE_BALANCED,
                module.BELL_CURVE_PRESETS,
                0.65,
            ),
        )
        self.assertEqual(
            35.0,
            module.matching_numeric_preset(
                35.0,
                module.BELL_CURVE_PEAK_PRESETS,
                50.0,
            ),
        )
        self.assertEqual(
            50.0,
            module.matching_numeric_preset(
                50.0,
                module.BELL_CURVE_PEAK_PRESETS,
                50.0,
            ),
        )
        self.assertEqual(
            65.0,
            module.matching_numeric_preset(
                65.0,
                module.BELL_CURVE_PEAK_PRESETS,
                50.0,
            ),
        )
        self.assertEqual(
            80.0,
            module.preset_numeric_data_for_key(
                module.POSITIVE_SKEW_HIGH,
                module.POSITIVE_SKEW_PRESETS,
                75.0,
            ),
        )
        self.assertEqual(
            3.5,
            module.preset_numeric_data_for_key(
                module.J_CURVE_PRESTIGIOUS,
                module.J_CURVE_PRESETS,
                2.5,
            ),
        )

    def test_disabled_checkbox_uses_placeholder_text_color(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        widget = FakePaletteWidget()
        original_palette = module.QPalette
        module.QPalette = FakePalette

        try:
            module.use_placeholder_color_when_disabled(widget)
        finally:
            module.QPalette = original_palette

        self.assertIs(widget._palette, widget.applied_palette)
        self.assertEqual([
            ('disabled', 'window', 'placeholder-color'),
            ('disabled', 'text', 'placeholder-color'),
            ('disabled', 'button', 'placeholder-color'),
        ], widget._palette.set_calls)

    def test_distribution_preview_bars_model_synthetic_histogram(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        uniform = module.RunSettings(
            output_percentile_field='',
            distribution_type='uniform',
            uniform_step=0.01,
        )
        positive_skew = module.RunSettings(
            output_percentile_field='',
            distribution_type='positive_skew',
            positive_skew_percent=75.0,
        )
        bell_left = module.RunSettings(
            output_percentile_field='',
            distribution_type='bell_curve',
            bell_curve_peak_percent=35.0,
        )
        bell_right = module.RunSettings(
            output_percentile_field='',
            distribution_type='bell_curve',
            bell_curve_peak_percent=65.0,
        )
        j_curve = module.RunSettings(
            output_percentile_field='',
            distribution_type='j_curve',
            j_curve_power=3.5,
        )

        uniform_bars = module.distribution_preview_bars(uniform)
        positive_skew_bars = module.distribution_preview_bars(positive_skew)
        bell_left_bars = module.distribution_preview_bars(bell_left)
        bell_right_bars = module.distribution_preview_bars(bell_right)
        j_curve_bars = module.distribution_preview_bars(j_curve)

        self.assertEqual(9, len(uniform_bars))
        self.assertEqual(9, len(positive_skew_bars))
        self.assertEqual(9, len(bell_left_bars))
        self.assertEqual(9, len(bell_right_bars))
        self.assertEqual(9, len(j_curve_bars))
        self.assertLessEqual(max(uniform_bars) - min(uniform_bars), 0.1)
        self.assertGreater(sum(positive_skew_bars[-3:]), sum(positive_skew_bars[:3]))
        self.assertGreater(sum(bell_left_bars[:3]), sum(bell_right_bars[:3]))
        self.assertGreater(sum(bell_right_bars[-3:]), sum(bell_left_bars[-3:]))
        self.assertGreater(sum(j_curve_bars[:3]), sum(j_curve_bars[-3:]))

    def test_distribution_preview_settings_preserve_manual_peak_text(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        widget = types.SimpleNamespace(
            distribution_type=types.SimpleNamespace(currentData=lambda: 'bell_curve'),
            uniform_step_preset=types.SimpleNamespace(currentData=lambda: 1.0),
            uniform_step_manual=types.SimpleNamespace(text=lambda: '1.0'),
            bell_curve_variety=types.SimpleNamespace(
                currentData=lambda: module.BELL_CURVE_BALANCED,
            ),
            bell_curve_std_dev=types.SimpleNamespace(text=lambda: '0.85'),
            bell_curve_peak_preset=types.SimpleNamespace(currentData=lambda: 50.0),
            bell_curve_peak_percent=types.SimpleNamespace(text=lambda: '42.5'),
            positive_skew_level=types.SimpleNamespace(
                currentData=lambda: module.POSITIVE_SKEW_MAINSTREAM,
            ),
            positive_skew_percent=types.SimpleNamespace(text=lambda: '75.0'),
            j_curve_exclusivity=types.SimpleNamespace(
                currentData=lambda: module.J_CURVE_PRESTIGIOUS,
            ),
            j_curve_power=types.SimpleNamespace(text=lambda: '3.5'),
        )

        settings = module.current_distribution_preview_settings(widget)

        self.assertEqual(42.5, settings.bell_curve_peak_percent)
        self.assertEqual(module.BELL_CURVE_BALANCED, settings.bell_curve_variety)
        self.assertEqual(module.POSITIVE_SKEW_MAINSTREAM, settings.positive_skew_level)
        self.assertEqual(module.J_CURVE_PRESTIGIOUS, settings.j_curve_exclusivity)

    def test_series_bias_rows_handle_missing_map(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        rows = module.series_bias_rows({}, [], True, 0.50)

        self.assertEqual(
            [('1', '--', '--'), ('2', '--', '--'), ('3', '--', '--'),
             ('4', '--', '--'), ('5', '--', '--'), ('6+', '--', '--')],
            rows,
        )

    def test_series_bias_help_text_documents_boost_rules(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        text = module.series_bias_help_text()

        self.assertIn('75-100% of book 1 = 0.75x', text)
        self.assertIn('25-50% = 1.75x', text)
        self.assertIn('previous whole-number book is 0-25%', text)
        self.assertIn('Books without vote counts receive no series bias', text)
        self.assertIn('Correction shows base bias multiplied by correction strength', text)
        self.assertIn('retention affects the multiplier only', text)
        self.assertIn('book-1 cap prevents penalties', text)
        self.assertIn('never raises books', text)
        self.assertIn('Position 1 is never corrected', text)

    def test_series_rerank_checkbox_controls_adjustment_mode(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        checked = types.SimpleNamespace(isChecked=lambda: True)
        unchecked = types.SimpleNamespace(isChecked=lambda: False)

        self.assertEqual(
            'adjusted_rank',
            module.adjustment_mode_from_checkbox(checked, True),
        )
        self.assertEqual(
            'direct_penalty',
            module.adjustment_mode_from_checkbox(unchecked, True),
        )
        self.assertEqual(
            'direct_penalty',
            module.adjustment_mode_from_checkbox(checked, False),
        )
        self.assertEqual(
            'Enabled: rerank the Rating field after series penalties. '
            'Disabled: write direct penalty values.',
            module.rerank_after_series_help_text(),
        )

    def test_series_bias_rows_scale_correction_with_strength(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        rows = module.series_bias_rows(
            {'1': 0.0, '2': 20.0, '6+': 45.0},
            [[3.0, 0.0], [5.0, 100.0]],
            True,
            0.25,
            25.0,
        )
        disabled_rows = module.series_bias_rows(
            {'2': 20.0},
            [[3.0, 0.0], [5.0, 100.0]],
            False,
            1.0,
            25.0,
        )

        self.assertEqual(('1', '0.00', '0.00'), rows[0])
        self.assertEqual(('2', '20.00', '5.00'), rows[1])
        self.assertEqual(('6+', '45.00', '11.25'), rows[5])
        self.assertEqual(('2', '20.00', '0.00'), disabled_rows[1])

    def test_series_bias_rows_show_small_impact_variance(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        rows = module.series_bias_rows(
            {'2': 0.16},
            [[3.0, 0.0], [5.0, 100.0]],
            True,
            0.75,
        )

        self.assertEqual(('2', '0.16', '0.12'), rows[1])

    def test_series_bias_rows_do_not_need_locked_curve_for_percentile_impact(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        rows = module.series_bias_rows({'2': 0.4}, [], True, 0.25)

        self.assertEqual(('2', '0.40', '0.10'), rows[1])

    def test_series_bias_table_fallback_height_tracks_preview_rows(self):
        module = load_module(
            PLUGIN_PACKAGE + '.config',
            os.path.join(ROOT, 'config.py'),
        )

        height = module.series_bias_table_content_height(FakeWidget(), 6)

        self.assertEqual(218, height)

    def test_custom_column_options_filter_by_output_role(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        db = types.SimpleNamespace(field_metadata={
            '#bool': {'name': 'Flag', 'datatype': 'bool', 'is_custom': True},
            '#date': {'name': 'Date', 'datatype': 'datetime', 'is_custom': True},
            '#rawint': {'name': 'Raw Int', 'datatype': 'int', 'is_custom': True},
            '#raw_index': {
                'name': 'Raw Index',
                'datatype': 'float',
                'is_custom': True,
            },
            '#note': {'name': 'Note', 'datatype': 'text', 'is_custom': True},
            '#score': {'name': 'Score', 'datatype': 'float', 'is_custom': True},
            '#series': {'name': 'Series', 'datatype': 'series', 'is_custom': True},
            '#series_index': {
                'name': 'Series Index',
                'datatype': 'float',
                'is_custom': True,
            },
            '#stars': {'name': 'Stars', 'datatype': 'rating', 'is_custom': True},
            '#astars': {'name': 'A Stars', 'datatype': 'rating', 'is_custom': True},
            'rating': {'name': 'Rating', 'datatype': 'rating', 'is_custom': False},
            'title': {'name': 'Title', 'datatype': 'text', 'is_custom': False},
            '#tags': {
                'name': 'Tags',
                'datatype': 'text',
                'is_custom': True,
                'is_multiple': True,
            },
            '#template': {
                'name': 'Template',
                'datatype': 'composite',
                'is_custom': True,
            },
        })

        percentile_fields = metadata_io.compatible_custom_columns(
            db,
            'output',
            'percentile',
        )
        rating_percentile_fields = metadata_io.compatible_custom_columns(
            db,
            'rating',
            'percentile',
        )
        rating_stars_fields = metadata_io.compatible_custom_columns(
            db,
            'rating',
            'stars_half',
        )

        self.assertEqual(['#note', '#raw_index', '#rawint', '#score'], [
            field['lookup_name'] for field in percentile_fields
        ])
        self.assertEqual(['#note', '#raw_index', '#rawint', '#score'], [
            field['lookup_name'] for field in rating_percentile_fields
        ])
        self.assertEqual(['rating', '#astars', '#stars'], [
            field['lookup_name'] for field in rating_stars_fields
        ])
        self.assertTrue(metadata_io.field_is_compatible(
            db,
            'rating',
            'rating',
            'stars_half',
        ))
        self.assertFalse(metadata_io.field_is_compatible(
            db,
            'rating',
            'rating',
            'percentile',
        ))

        self.assertFalse(metadata_io.field_is_compatible(
            db,
            '#series_index',
            'output',
            'percentile',
        ))

    def test_rating_field_writes_use_calibre_half_star_ticks(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        writes = {}
        db = types.SimpleNamespace(
            field_metadata={
                'rating': {
                    'name': 'Rating',
                    'datatype': 'rating',
                    'is_custom': False,
                },
                '#stars': {
                    'name': 'Stars',
                    'datatype': 'rating',
                    'is_custom': True,
                },
            },
            set_field=lambda field, values: writes.setdefault(field, values),
        )

        failures = metadata_io.write_outputs(db, {
            '#stars': {
                1: 0.5,
                2: 4.5,
                3: 5.0,
            },
            'rating': {
                4: 3.5,
            },
        })

        self.assertEqual([], failures)
        self.assertEqual({1: 1, 2: 9, 3: 10}, writes['#stars'])
        self.assertEqual({4: 7}, writes['rating'])

    def test_rating_field_half_star_support_uses_column_metadata(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        db = types.SimpleNamespace(field_metadata={
            '#stars_full': {
                'name': 'Stars',
                'datatype': 'rating',
                'is_custom': True,
                'display': {'allow_half_stars': False},
            },
            '#stars_half': {
                'name': 'Stars 1/2',
                'datatype': 'rating',
                'is_custom': True,
                'display': {'allow_half_stars': True},
            },
            '#score': {
                'name': 'Score',
                'datatype': 'float',
                'is_custom': True,
            },
        })

        self.assertFalse(
            metadata_io.rating_field_supports_half_stars(db, '#stars_full')
        )
        self.assertTrue(
            metadata_io.rating_field_supports_half_stars(db, '#stars_half')
        )
        self.assertTrue(metadata_io.rating_field_supports_half_stars(db, '#score'))

    def test_series_search_key_does_not_bool_dbprefs(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        db = types.SimpleNamespace(prefs=FakeDBPrefs({
            'similar_series_search_key': '#mysaga',
        }))
        fallback_db = types.SimpleNamespace(prefs=FakeDBPrefs())
        empty_db = types.SimpleNamespace(prefs=FakeDBPrefs({
            'similar_series_search_key': '',
        }))

        self.assertEqual('#mysaga', metadata_io.series_search_key(db))
        self.assertEqual('series', metadata_io.series_search_key(fallback_db))
        self.assertEqual('series', metadata_io.series_search_key(empty_db))

    def test_series_search_keys_include_custom_series_columns(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        db = types.SimpleNamespace(
            prefs=FakeDBPrefs({'similar_series_search_key': '#reading_series'}),
            field_metadata={
                '#reading_series': {
                    'name': 'Reading Series',
                    'datatype': 'series',
                    'is_custom': True,
                },
                '#saga': {
                    'name': 'Saga',
                    'datatype': 'series',
                    'is_custom': True,
                },
                '#score': {
                    'name': 'Score',
                    'datatype': 'float',
                    'is_custom': True,
                },
            },
        )

        self.assertEqual(
            ['#reading_series', 'series', '#saga'],
            metadata_io.series_search_keys(db),
        )

    def test_series_search_keys_expand_grouped_search_terms(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        db = types.SimpleNamespace(
            prefs=FakeDBPrefs({
                'similar_series_search_key': 'all_series',
                'grouped_search_terms': {
                    'all_series': 'series,#subseries',
                },
            }),
            field_metadata={
                '#subseries': {
                    'name': 'Subseries',
                    'datatype': 'series',
                    'is_custom': True,
                },
            },
        )

        self.assertEqual(
            ['series', '#subseries'],
            metadata_io.series_search_keys(db),
        )

    def test_series_value_uses_first_source_with_name_and_index(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        metadata = {
            '#reading_series': 'Reading Order',
            'series': 'Published Order',
            'series_index': '2',
        }

        self.assertEqual(
            ('Published Order', 2.0),
            metadata_io.series_value_and_index(
                metadata,
                ['#reading_series', 'series'],
            ),
        )

    def test_series_value_reads_bundled_and_text_indexes(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        bundled = {'#mysaga': ('Saga', 2.5)}
        text_index = {'#mysaga': 'Saga [3]'}
        dict_value = {'#mysaga': {'#value#': 'Saga', '#extra#': 4}}

        self.assertEqual(
            ('Saga', 2.5),
            metadata_io.series_value_and_index(bundled, '#mysaga'),
        )
        self.assertEqual(
            ('Saga', 3.0),
            metadata_io.series_value_and_index(text_index, '#mysaga'),
        )
        self.assertEqual(
            ('Saga', 4.0),
            metadata_io.series_value_and_index(dict_value, '#mysaga'),
        )

    def test_library_inputs_read_grating_identifiers(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        metadata_by_id = {
            1: types.SimpleNamespace(identifiers={
                'goodreads': '1310692',
                'grrating': '3.36',
                'grvotes': '1,436',
            }),
            2: types.SimpleNamespace(identifiers={
                'grrating': '0',
                'grvotes': '0',
            }),
            3: types.SimpleNamespace(identifiers={
                'goodreads': '123',
            }),
        }
        db = types.SimpleNamespace(
            all_book_ids=lambda: [1, 2, 3],
            get_proxy_metadata=lambda book_id: metadata_by_id[book_id],
        )

        books, report = metadata_io.load_library_inputs(db)

        self.assertEqual(3, report.processed_books)
        self.assertEqual(2, report.valid_ratings)
        self.assertEqual(1, report.skipped_missing_ratings)
        self.assertNotIn(
            'No grrating identifiers were found in this library.',
            report.warnings,
        )
        self.assertEqual(3.36, books[0].rating)
        self.assertEqual(1436, books[0].votes)
        self.assertEqual(0.0, books[1].rating)
        self.assertEqual(0, books[1].votes)

    def test_library_inputs_debug_reports_series_sources(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        class FakeMetadata(dict):

            def __init__(self, identifiers, values):
                dict.__init__(self, values)
                self.identifiers = identifiers

        metadata_by_id = {
            1: FakeMetadata(
                {'grrating': '4.0', 'grvotes': '100'},
                {'series': 'Main', 'series_index': '1'},
            ),
            2: FakeMetadata(
                {'grrating': '4.5', 'grvotes': '50'},
                {'#subseries': ('Sub', 2)},
            ),
        }
        messages = []
        db = types.SimpleNamespace(
            prefs=FakeDBPrefs({
                'similar_series_search_key': 'all_series',
                'grouped_search_terms': {'all_series': 'series,#subseries'},
            }),
            field_metadata={
                '#subseries': {
                    'name': 'Subseries',
                    'datatype': 'series',
                    'is_custom': True,
                },
            },
            all_book_ids=lambda: [1, 2],
            get_proxy_metadata=lambda book_id: metadata_by_id[book_id],
        )

        books, report = metadata_io.load_library_inputs(
            db,
            debug_callback=messages.append,
        )

        self.assertEqual(2, len(books))
        self.assertIn('series_keys=series,#subseries', messages[0])
        self.assertIn('series_sources=#subseries:1,series:1', messages[0])
        self.assertIn('indexed_sources=#subseries:1,series:1', messages[0])

    def test_grating_inputs_do_not_fall_back_to_metadata_fields(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        class FakeMetadata(dict):
            identifiers = {}

        db = types.SimpleNamespace(
            all_book_ids=lambda: [1],
            get_proxy_metadata=lambda book_id: FakeMetadata({
                'grrating': '4.5',
                'grvotes': '1000',
            }),
        )

        books, report = metadata_io.load_library_inputs(db)

        self.assertEqual([], books)
        self.assertEqual(1, report.skipped_missing_ratings)
        self.assertEqual(
            [
                'No grrating identifiers were found in this library.',
                'To enable them, open Preferences > Metadata download, select the '
                'Goodreads metadata source, and click Configure selected source.',
                'In the Goodreads source options, enable "Get precise rating into '
                '\'grrating\' identifier" and "Get #votes for rating into '
                '\'grvotes\' identifier", then download metadata again for the '
                'affected books.',
            ],
            report.warnings,
        )

    def test_grating_identifier_probe_uses_search_index_first(self):
        metadata_io = load_module(
            PLUGIN_PACKAGE + '.metadata_io',
            os.path.join(ROOT, 'metadata_io.py'),
        )

        searches = []

        class SearchDB(object):

            def search_getting_ids(self, query, **kwargs):
                searches.append((query, kwargs))
                return {7}

            def all_book_ids(self):
                raise AssertionError('identifier probe should not scan books')

        self.assertTrue(metadata_io.has_grating_identifier(SearchDB()))
        self.assertEqual(
            'identifiers:=grrating:',
            searches[0][0],
        )
        self.assertFalse(searches[0][1].get('use_virtual_library', True))

    def test_grating_identifier_probe_stops_before_write_confirm(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        class FakeMetadata(dict):
            identifiers = {}

        class FakeSelectionModel(object):

            def selectedRows(self):
                return [0]

        class FakeLibraryView(object):

            def selectionModel(self):
                return FakeSelectionModel()

            def model(self):
                return self

            def id(self, row):
                return row + 1

        class FakeStatusBar(object):

            def __init__(self):
                self.messages = []

            def show_message(self, message, timeout=5000):
                self.messages.append(message)

        status_bar = FakeStatusBar()
        db = types.SimpleNamespace(
            all_book_ids=lambda: [1],
            search_getting_ids=lambda query, **kwargs: set(),
            get_proxy_metadata=lambda book_id: FakeMetadata({
                'grrating': '4.5',
            }),
        )
        gui = types.SimpleNamespace(
            current_db=db,
            library_view=FakeLibraryView(),
            status_bar=status_bar,
        )
        errors = []
        confirm_called = []

        original_settings = main.settings_from_prefs
        original_validate = main.validate_output_fields
        original_confirm = main.confirm_write
        original_show_error = main.show_error
        try:
            main.settings_from_prefs = lambda db=None: results.RunSettings(
                output_percentile_field='#output',
            )
            main.validate_output_fields = lambda db, settings: []
            main.confirm_write = lambda gui, db, settings: (
                confirm_called.append(True) or True
            )
            main.show_error = lambda gui, title, message: errors.append(
                (title, message)
            )

            main.GRatingActionRunner(gui).perform_action()
        finally:
            main.settings_from_prefs = original_settings
            main.validate_output_fields = original_validate
            main.confirm_write = original_confirm
            main.show_error = original_show_error

        self.assertEqual([], confirm_called)
        self.assertEqual('GRating identifiers not found', errors[0][0])
        self.assertIn(
            'No grrating identifiers were found in this library.',
            errors[0][1],
        )
        self.assertIn('Checking GRating identifiers...', status_bar.messages)

    def test_confirm_write_happens_before_selected_id_enumeration(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        class FakeSelectionModel(object):

            def __init__(self):
                self.confirmed = False
                self.selected_rows_called = 0

            def hasSelection(self):
                return True

            def selectedRows(self):
                self.selected_rows_called += 1
                if not self.confirmed:
                    raise AssertionError('selected IDs were enumerated too early')
                return [0]

        class FakeLibraryView(object):

            def __init__(self, selection_model):
                self.selection_model = selection_model

            def selectionModel(self):
                return self.selection_model

            def model(self):
                return self

            def id(self, row):
                return row + 1

        selection_model = FakeSelectionModel()
        db = types.SimpleNamespace(
            search_getting_ids=lambda query, **kwargs: {1},
        )
        gui = types.SimpleNamespace(
            current_db=db,
            library_view=FakeLibraryView(selection_model),
        )
        confirm_messages = []

        original_settings = main.settings_from_prefs
        original_validate = main.validate_output_fields
        original_confirm = main.confirm_write
        original_load_inputs = main.load_library_inputs
        original_calculate = main.calculate_scores
        original_mapping_for_run = main.GRatingActionRunner.percentile_mapping_for_run
        original_write_outputs = main.write_outputs
        try:
            main.settings_from_prefs = lambda db=None: results.RunSettings(
                output_percentile_field='#output',
            )
            main.validate_output_fields = lambda db, settings: []

            def fake_confirm(gui, db, settings):
                confirm_messages.append(settings.output_percentile_field)
                selection_model.confirmed = True
                return False

            main.confirm_write = fake_confirm
            main.load_library_inputs = lambda db, debug_callback=None: (
                [],
                results.RunReport(),
            )
            main.calculate_scores = lambda *args, **kwargs: ({}, {}, results.RunReport())
            main.GRatingActionRunner.percentile_mapping_for_run = (
                lambda *args, **kwargs: {}
            )
            main.write_outputs = lambda db, output_by_field: []

            main.GRatingActionRunner(gui).perform_action()
        finally:
            main.settings_from_prefs = original_settings
            main.validate_output_fields = original_validate
            main.confirm_write = original_confirm
            main.load_library_inputs = original_load_inputs
            main.calculate_scores = original_calculate
            main.GRatingActionRunner.percentile_mapping_for_run = original_mapping_for_run
            main.write_outputs = original_write_outputs

        self.assertEqual(['#output'], confirm_messages)
        self.assertEqual(0, selection_model.selected_rows_called)

    def test_confirm_write_message_uses_column_headings_for_both_outputs(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        db = types.SimpleNamespace(field_metadata={
            '#grrating_percentile': {
                'name': 'GRating Percentile',
                'datatype': 'float',
                'is_custom': True,
            },
            '#grating_stars': {
                'column_heading': 'GRating Stars',
                'datatype': 'float',
                'is_custom': True,
            },
        })
        settings = results.RunSettings(
            output_percentile_field='#grrating_percentile',
            adjusted_rating_field='#grating_stars',
        )

        self.assertEqual(
            'GRating Percentile, GRating Stars',
            main.confirm_write_field_text(db, settings),
        )

    def test_series_correction_can_be_disabled(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.5, votes=40, series='A', series_index=2.0),
        ]
        settings = results.RunSettings(
            output_percentile_field='#score',
            series_correction_enabled=False,
        )

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
        )

        self.assertEqual({1: 0.0, 2: 100.0}, position_inflation)
        self.assertEqual(0, report.books_with_series_correction)
        self.assertEqual(2, report.books_without_series_correction)
        self.assertEqual(4.5, scores[2].series_adjusted_rating)

    def test_series_bias_is_not_applied_without_current_votes(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        messages = []
        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.5, votes=None, series='A', series_index=2.0),
        ]
        settings = results.RunSettings(output_percentile_field='#score')

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
            debug_callback=messages.append,
        )

        self.assertEqual({1: 0.0, 2: 100.0}, position_inflation)
        self.assertEqual(0, report.books_with_series_correction)
        self.assertEqual(2, report.books_without_series_correction)
        self.assertEqual(4.5, scores[2].series_adjusted_rating)
        self.assertIn(
            'series current_settings enabled=1 strength=0.5000 '
            'retention_factor=0.0000 max_retention=0.0000 '
            'buckets=2:n=1,base=0.0000,mult=0.0000,pos=0.0000,'
            'ret=0.0000,total=0.0000,cap=100.0000,capped=0,applied=0.0000,'
            'book1_ret=-,prev_ret=-',
            messages,
        )

    def test_series_penalty_cap_never_raises_book_to_book_one(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.1, votes=60, series='A', series_index=2.0),
            results.BookInput(3, 4.5, votes=60, series='B', series_index=1.0),
            results.BookInput(4, 4.0, votes=60, series='B', series_index=2.0),
        ]
        settings = results.RunSettings(
            output_percentile_field='#score',
            correction_strength=1.0,
        )
        locked_mapping = {'position_inflation': {'1': 0.0, '2': 100.0}}

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
            locked_mapping=locked_mapping,
        )

        self.assertEqual(100.0, position_inflation[2])
        self.assertEqual(scores[1].raw_percentile, scores[2].penalty_adjusted_percentile)
        self.assertLess(scores[4].raw_percentile, scores[3].raw_percentile)
        self.assertEqual(0.0, scores[4].series_bias_penalty)
        self.assertEqual(scores[4].raw_percentile, scores[4].penalty_adjusted_percentile)
        self.assertLess(scores[4].penalty_adjusted_percentile, scores[3].raw_percentile)

    def test_series_learning_warns_when_no_usable_pairs(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.5, votes=40, series='B', series_index=2.0),
        ]
        settings = results.RunSettings(
            output_percentile_field='#score',
            series_correction_enabled=True,
            minimum_series_pairs_warning=10,
        )

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
        )

        self.assertEqual({1: 0.0}, position_inflation)
        self.assertIn(
            'Only 0 usable series-position pairs were found.',
            report.warnings,
        )

    def test_series_learning_debug_reports_pair_buckets(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        messages = []
        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.5, votes=40, series='A', series_index=2.0),
        ]
        settings = results.RunSettings(output_percentile_field='#score')

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
            debug_callback=messages.append,
        )

        self.assertEqual({1: 0.0, 2: 100.0}, position_inflation)
        self.assertIn(
            'series groups=1 groups_with_book1=1 usable_pairs=1 '
            'pair_buckets=2:1 bias_buckets=1:0.0000,2:100.0000',
            messages,
        )
        self.assertIn(
            'series delta_stats=2:n=1,pos=1,zero=0,neg=0,avg=100.0000,'
            'wavg=100.0000,min=100.0000,max=100.0000',
            messages,
        )
        self.assertIn(
            'series book1_retention_delta=2[25-50:n=1,pos=1,zero=0,'
            'neg=0,avg=100.0000,wavg=100.0000]',
            messages,
        )
        self.assertIn(
            'series prev_retention_delta=2[25-50:n=1,pos=1,zero=0,'
            'neg=0,avg=100.0000,wavg=100.0000]',
            messages,
        )
        self.assertIn(
            'series current_settings enabled=1 strength=0.5000 '
            'retention_factor=0.0000 max_retention=0.0000 '
            'buckets=2:n=1,base=100.0000,mult=1.7500,pos=175.0000,'
            'ret=0.0000,total=175.0000,cap=100.0000,capped=0,applied=87.5000,'
            'book1_ret=0.4000,prev_ret=0.4000',
            messages,
        )

    def test_series_learning_debug_reports_delta_distribution(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        messages = []
        books = [
            results.BookInput(1, 4.0, votes=10, series='A', series_index=1.0),
            results.BookInput(2, 4.5, votes=10, series='A', series_index=2.0),
            results.BookInput(3, 4.0, votes=10, series='B', series_index=1.0),
            results.BookInput(4, 3.8, votes=10, series='B', series_index=2.0),
            results.BookInput(5, 4.0, votes=10, series='C', series_index=1.0),
            results.BookInput(6, 4.0, votes=10, series='C', series_index=2.0),
        ]
        settings = results.RunSettings(output_percentile_field='#score')

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
            debug_callback=messages.append,
        )

        self.assertAlmostEqual(0.0, position_inflation[2], places=8)
        self.assertIn(
            'series delta_stats=2:n=3,pos=1,zero=1,neg=1,avg=-20.0000,'
            'wavg=-20.0000,min=-80.0000,max=20.0000',
            messages,
        )

    def test_series_learning_debug_splits_book1_and_previous_retention(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        messages = []
        books = [
            results.BookInput(1, 4.0, votes=100, series='A', series_index=1.0),
            results.BookInput(2, 4.2, votes=90, series='A', series_index=2.0),
            results.BookInput(3, 4.5, votes=45, series='A', series_index=3.0),
        ]
        settings = results.RunSettings(output_percentile_field='#score')

        scores, position_inflation, report = scoring.calculate_scores(
            books,
            settings,
            debug_callback=messages.append,
        )

        self.assertAlmostEqual(50.0, position_inflation[2], places=8)
        self.assertAlmostEqual(100.0, position_inflation[3], places=8)
        self.assertIn(
            'series book1_retention_delta=2[75-100:n=1,pos=1,zero=0,'
            'neg=0,avg=50.0000,wavg=50.0000];'
            '3[25-50:n=1,pos=1,zero=0,neg=0,avg=100.0000,wavg=100.0000]',
            messages,
        )
        self.assertIn(
            'series prev_retention_delta=2[75-100:n=1,pos=1,zero=0,'
            'neg=0,avg=50.0000,wavg=50.0000];'
            '3[50-75:n=1,pos=1,zero=0,neg=0,avg=100.0000,wavg=100.0000]',
            messages,
        )

    def test_output_field_uses_raw_percentile(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        runner = main.GRatingActionRunner(types.SimpleNamespace())
        settings = results.RunSettings(
            output_percentile_field='#output',
            adjusted_rating_field='#rating',
            output_format='percentile',
            percentile_adjustment_mode='adjusted_rank',
        )
        scores = {
            1: results.BookScore(
                book_id=1,
                rating=4.0,
                votes=100,
                raw_percentile=25.5,
                series_adjusted_rating=3.8,
                adjusted_percentile=90.0,
                penalty_adjusted_percentile=25.5,
            ),
        }

        output = runner.output_values_for_selection([1], scores, settings)

        self.assertEqual(25.5, output['#output'][1])
        self.assertEqual(90.0, output['#rating'][1])

    def test_direct_penalty_adjustment_uses_raw_percentile_minus_own_penalty(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        runner = main.GRatingActionRunner(types.SimpleNamespace())
        settings = results.RunSettings(
            output_percentile_field='#output',
            adjusted_rating_field='#rating',
            output_format='percentile',
            percentile_adjustment_mode='direct_penalty',
        )
        scores = {
            1: results.BookScore(
                book_id=1,
                rating=4.0,
                votes=100,
                raw_percentile=33.29,
                series_adjusted_rating=3.8,
                adjusted_percentile=49.20,
                penalty_adjusted_percentile=23.29,
                series_bias_penalty=0.2,
            ),
        }
        mapping = {'score_percentile_curve': [[3.0, 0.0], [5.0, 100.0]]}

        output = runner.output_values_for_selection(
            [1],
            scores,
            settings,
            mapping,
        )

        self.assertEqual(33.29, output['#output'][1])
        self.assertEqual(23.29, output['#rating'][1])

    def test_direct_penalty_adjustment_keeps_raw_percentile_without_penalty(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        runner = main.GRatingActionRunner(types.SimpleNamespace())
        settings = results.RunSettings(
            output_percentile_field='#output',
            adjusted_rating_field='#rating',
            output_format='percentile',
            percentile_adjustment_mode='direct_penalty',
        )
        scores = {
            1: results.BookScore(
                book_id=1,
                rating=4.0,
                votes=100,
                raw_percentile=33.29,
                series_adjusted_rating=4.0,
                adjusted_percentile=49.20,
                penalty_adjusted_percentile=33.29,
                series_bias_penalty=0.0,
            ),
        }

        output = runner.output_values_for_selection([1], scores, settings)

        self.assertEqual(33.29, output['#output'][1])
        self.assertEqual(33.29, output['#rating'][1])

    def test_output_ignores_distribution_and_rating_type(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        runner = main.GRatingActionRunner(types.SimpleNamespace())
        settings = results.RunSettings(
            output_percentile_field='#output',
            adjusted_rating_field='#rating',
            output_format='stars_half',
            distribution_type='positive_skew',
            positive_skew_percent=85.0,
            percentile_adjustment_mode='adjusted_rank',
        )
        scores = {
            1: results.BookScore(
                book_id=1,
                rating=4.0,
                votes=100,
                raw_percentile=25.5,
                series_adjusted_rating=3.8,
                adjusted_percentile=50.0,
                penalty_adjusted_percentile=25.5,
            ),
        }

        output = runner.output_values_for_selection([1], scores, settings)

        self.assertEqual(25.5, output['#output'][1])
        self.assertEqual(4.5, output['#rating'][1])

    def test_successful_write_count_gates_locked_mapping_persistence(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        output_by_field = {
            '#output': {1: 10.0, 2: 20.0},
            '#rating': {1: 1.0, 2: 2.0},
            '#empty': {},
        }

        self.assertEqual(4, main.successful_write_count(output_by_field, []))
        self.assertEqual(
            2,
            main.successful_write_count(output_by_field, [
                (1, '#output failed'),
                (2, '#output failed'),
            ]),
        )
        self.assertEqual(
            0,
            main.successful_write_count(output_by_field, [
                (1, '#output failed'),
                (2, '#output failed'),
                (1, '#rating failed'),
                (2, '#rating failed'),
            ]),
        )
        self.assertEqual(0, main.successful_write_count({'#output': {}}, []))
        self.assertEqual(4, main.attempted_write_count(output_by_field))

        settings = results.RunSettings(
            output_percentile_field='#output',
            percentile_mapping_mode='recalculate_each_run',
        )
        rebuild_settings = results.RunSettings(
            output_percentile_field='#output',
            percentile_mapping_mode='rebuild_and_lock',
        )

        self.assertTrue(
            main.should_prompt_to_lock_mapping(settings, False, 1)
        )
        self.assertFalse(
            main.should_prompt_to_lock_mapping(settings, True, 1)
        )
        self.assertFalse(
            main.should_prompt_to_lock_mapping(settings, False, 0)
        )
        self.assertFalse(
            main.should_prompt_to_lock_mapping(rebuild_settings, False, 1)
        )

    def test_debug_printer_is_none_when_disabled(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )

        self.assertIsNone(main.debug_printer(False))
        self.assertTrue(callable(main.debug_printer(True)))

    def test_unlocked_runs_still_apply_a_calculated_mapping(self):
        main = load_module(
            PLUGIN_PACKAGE + '.main',
            os.path.join(ROOT, 'main.py'),
        )
        locked_mapping = load_module(
            PLUGIN_PACKAGE + '.locked_mapping',
            os.path.join(ROOT, 'locked_mapping.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        runner = main.GRatingActionRunner(types.SimpleNamespace())
        settings = results.RunSettings(output_percentile_field='#output')
        scores = {
            1: results.BookScore(1, 3.9, 100, 0.0, 3.9, 0.0),
            2: results.BookScore(2, 4.0, 90, 50.0, 4.0, 50.0),
            3: results.BookScore(3, 5.0, 80, 100.0, 5.0, 100.0),
        }

        mapping = runner.percentile_mapping_for_run(
            settings,
            scores,
            position_inflation={},
            locked_mapping=None,
        )
        runner.apply_locked_mapping(scores, mapping)

        self.assertTrue(mapping['score_percentile_curve'])
        self.assertEqual(
            locked_mapping.settings_fingerprint(
                settings,
                'raw_rating',
            ),
            mapping['settings_fingerprint'],
        )
        self.assertEqual(50.0, scores[2].adjusted_percentile)

    def test_distribution_behaviors_use_adjusted_percentile_source(self):
        percentiles = load_module(
            PLUGIN_PACKAGE + '.percentiles',
            os.path.join(ROOT, 'percentiles.py'),
        )
        results = load_module(
            PLUGIN_PACKAGE + '.results',
            os.path.join(ROOT, 'results.py'),
        )

        uniform = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='uniform',
            uniform_step=5.0,
        )
        bell_curve = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='bell_curve',
            bell_curve_std_dev=0.45,
        )
        bell_curve_left_peak = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='bell_curve',
            bell_curve_peak_percent=35.0,
        )
        bell_curve_right_peak = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='bell_curve',
            bell_curve_peak_percent=65.0,
        )
        positive_skew = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='positive_skew',
            positive_skew_percent=75.0,
        )
        j_curve = results.RunSettings(
            output_percentile_field='#output',
            distribution_type='j_curve',
            j_curve_power=3.5,
        )

        self.assertEqual(15.0, percentiles.apply_distribution(12.6, uniform))
        self.assertAlmostEqual(
            67.36448,
            percentiles.apply_distribution(84.1344746, bell_curve),
            places=4,
        )
        self.assertAlmostEqual(
            percentiles.apply_bell_curve_distribution(84.1344746, 0.45),
            percentiles.apply_bell_curve_distribution(84.1344746, 0.45, 50.0),
            places=8,
        )
        self.assertAlmostEqual(
            35.0,
            percentiles.apply_distribution(50.0, bell_curve_left_peak),
            places=6,
        )
        self.assertAlmostEqual(
            65.0,
            percentiles.apply_distribution(50.0, bell_curve_right_peak),
            places=6,
        )
        self.assertEqual(75.0, percentiles.apply_distribution(50.0, positive_skew))
        self.assertAlmostEqual(
            8.83883476,
            percentiles.apply_distribution(50.0, j_curve),
            places=6,
        )

    def test_about_text_renders_grating_metadata(self):
        text = load_module(
            PLUGIN_PACKAGE + '.about',
            os.path.join(ROOT, 'about.py'),
        ).build_about_text()

        self.assertIn('GRating Rebalancer', text)
        self.assertIn('Version 1.0.0', text)
        self.assertIn('GrayTechGH', text)

    def test_release_candidates_exclude_local_and_old_project_artifacts(self):
        files = release_file_candidates()

        self.assertIn('__init__.py', files)
        self.assertIn('ui.py', files)
        self.assertIn('percentiles.py', files)
        self.assertIn('scoring.py', files)
        self.assertIn('images/plugin_icon.png', files)
        self.assertFalse(any(name.startswith('_docs/') for name in files))
        self.assertFalse(any(name.startswith('_dev_tools/') for name in files))
        self.assertFalse(any(name.startswith('translations/') for name in files))
        self.assertFalse(any(name.startswith('resources/') for name in files))
        old_markers = ('Good' + 'reads', 'good' + 'reads')
        self.assertFalse(any(any(marker in name for marker in old_markers) for name in files))

    def test_percentiles_use_zero_to_one_hundred_float_range(self):
        percentiles = load_module(
            PLUGIN_PACKAGE + '.percentiles',
            os.path.join(ROOT, 'percentiles.py'),
        )

        result = percentiles.calculate_percentiles([
            (1, 3.0),
            (2, 4.0),
            (3, 4.0),
            (4, 5.0),
        ])

        self.assertEqual(0.0, result[1])
        self.assertAlmostEqual(66.6666666667, result[2], places=8)
        self.assertAlmostEqual(66.6666666667, result[3], places=8)
        self.assertEqual(100.0, result[4])

    def test_star_conversion_keeps_zero_as_unrated_only(self):
        percentiles = load_module(
            PLUGIN_PACKAGE + '.percentiles',
            os.path.join(ROOT, 'percentiles.py'),
        )

        self.assertEqual(0.0, percentiles.convert_percentile(0.0, 'stars_half'))
        self.assertEqual(0.5, percentiles.convert_percentile(0.01, 'stars_half'))
        self.assertEqual(0.5, percentiles.convert_percentile(5.0, 'stars_half'))
        self.assertEqual(1.0, percentiles.convert_percentile(0.01, 'stars_whole'))
        self.assertEqual(1.0, percentiles.convert_percentile(10.0, 'stars_whole'))

    def test_locked_curve_uses_endpoint_dense_twenty_one_anchor_shape(self):
        percentiles = load_module(
            PLUGIN_PACKAGE + '.percentiles',
            os.path.join(ROOT, 'percentiles.py'),
        )

        positions = percentiles.normalized_anchor_positions(21, 0.025)

        self.assertEqual(21, len(positions))
        self.assertEqual(0.0, positions[0])
        self.assertEqual(0.025, positions[1])
        self.assertIn(0.5, positions)
        self.assertEqual(0.975, positions[-2])
        self.assertEqual(1.0, positions[-1])

    def test_locked_curve_handles_fewer_than_twenty_one_unique_scores(self):
        percentiles = load_module(
            PLUGIN_PACKAGE + '.percentiles',
            os.path.join(ROOT, 'percentiles.py'),
        )

        curve = percentiles.build_score_percentile_curve(
            [4.0, 4.0, 4.2, 4.2, 4.4],
            21,
            0.025,
        )
        same_score_curve = percentiles.build_score_percentile_curve(
            [4.0, 4.0, 4.0],
            21,
            0.025,
        )

        self.assertEqual(21, len(curve))
        self.assertEqual([[4.0, 50.0]], same_score_curve)
        self.assertEqual(
            50.0,
            percentiles.apply_score_percentile_curve(same_score_curve, 4.0),
        )

    def test_fractional_series_buckets_match_plan(self):
        scoring = load_module(
            PLUGIN_PACKAGE + '.scoring',
            os.path.join(ROOT, 'scoring.py'),
        )

        self.assertIsNone(scoring.bucket_series_index(0.5))
        self.assertEqual(2, scoring.bucket_series_index(1.5))
        self.assertEqual(3, scoring.bucket_series_index(2.25))
        self.assertEqual(6, scoring.bucket_series_index(5.5))


if __name__ == '__main__':
    unittest.main(verbosity=2)
