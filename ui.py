#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

if False:
    get_icons = None
    load_translations = None
    _ = None

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
    QApplication,
    QEvent,
    QMenu,
    QMessageBox,
    Qt,
    QTimer,
    QToolButton,
)

from calibre.gui2.actions import InterfaceAction
from calibre_plugins.GRating_Rebalancer.about import build_about_text
from calibre_plugins.GRating_Rebalancer.config import DebugOptionsDialog, prefs
from calibre_plugins.GRating_Rebalancer.main import GRatingActionRunner


class InterfacePlugin(InterfaceAction):

    name = 'GRating Rebalancer'
    popup_type = QToolButton.MenuButtonPopup

    action_spec = (
        'GRating RB',
        None,
        _('Run GRating Rebalancer'),
        None
    )

    def genesis(self):
        self.current_runner = None
        icon = get_icons('images/plugin_icon.png', _('GRating Rebalancer'))

        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.toolbar_action_triggered)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self.install_toolbar_button_filter()
        schedule_once(self.install_toolbar_button_filter)

        self.run_action = self.menu.addAction(_('Run'))
        self.run_action.triggered.connect(self.run_grating_rebalancer)

        self.config_action = self.menu.addAction(_('Customize plugin...'))
        self.config_action.triggered.connect(self.show_config)

        self.about_action = self.menu.addAction(_('About'))
        self.about_action.triggered.connect(self.show_about)

    def toolbar_action_triggered(self, *args):
        if ctrl_shift_icon_click():
            self.show_debug_options()
            return
        self.run_grating_rebalancer()

    def install_toolbar_button_filter(self):
        for widget in action_widgets(self.qaction, self.gui):
            if hasattr(widget, 'installEventFilter'):
                widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if is_ctrl_shift_left_press(event):
            self.show_debug_options()
            return True
        try:
            return InterfaceAction.eventFilter(self, obj, event)
        except AttributeError:
            return False

    def run_grating_rebalancer(self):
        self.current_runner = GRatingActionRunner(
            self.gui,
            finished_callback=self.clear_current_runner,
        )
        self.current_runner.run_for_selection()

    def clear_current_runner(self):
        self.current_runner = None

    def show_about(self):
        dialog = QMessageBox(self.gui)
        dialog.setWindowTitle(_('About GRating Rebalancer'))
        dialog.setTextFormat(Qt.TextFormat.RichText)
        dialog.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        dialog.setText(build_about_text())
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        dialog.exec()

    def show_config(self):
        self.interface_action_base_plugin.do_user_config(parent=self.gui)

    def show_debug_options(self):
        dialog = DebugOptionsDialog(self.gui)
        if dialog.exec():
            dialog.save_settings()
            self.apply_settings()

    def apply_settings(self):
        if prefs['debug_diagnostics']:
            print('GRating Rebalancer settings applied.', flush=True)


def ctrl_shift_icon_click():
    try:
        modifiers = QApplication.keyboardModifiers()
    except Exception:
        return False
    return (
        flag_is_set(modifiers, qt_enum_value('KeyboardModifier', 'ControlModifier'))
        and flag_is_set(modifiers, qt_enum_value('KeyboardModifier', 'ShiftModifier'))
    )


def action_widgets(action, gui):
    widgets = []
    if hasattr(action, 'associatedWidgets'):
        try:
            associated = action.associatedWidgets()
        except Exception:
            associated = []
        for widget in associated:
            widgets.append(widget)
            action_widget = widget_for_action(widget, action)
            if action_widget is not None:
                widgets.append(action_widget)
    for name in ('tool_bar', 'toolbar'):
        toolbar = getattr(gui, name, None)
        if toolbar is not None:
            widget = widget_for_action(toolbar, action)
            if widget is not None:
                widgets.append(widget)

    unique = []
    for widget in widgets:
        if widget not in unique:
            unique.append(widget)
    return unique


def widget_for_action(container, action):
    if container is None or not hasattr(container, 'widgetForAction'):
        return None
    try:
        return container.widgetForAction(action)
    except Exception:
        return None


def schedule_once(callback):
    try:
        QTimer.singleShot(0, callback)
    except Exception:
        pass


def is_ctrl_shift_left_press(event):
    if event is None or not hasattr(event, 'type'):
        return False
    try:
        event_type = event.type()
    except Exception:
        return False
    if event_type != qt_event_type('MouseButtonPress'):
        return False
    try:
        modifiers = event.modifiers()
        button = event.button()
    except Exception:
        return False
    return (
        flag_is_set(modifiers, qt_enum_value('KeyboardModifier', 'ControlModifier'))
        and flag_is_set(modifiers, qt_enum_value('KeyboardModifier', 'ShiftModifier'))
        and flag_is_set(button, qt_enum_value('MouseButton', 'LeftButton'))
    )


def qt_event_type(value_name):
    group = getattr(QEvent, 'Type', None)
    if group is not None and hasattr(group, value_name):
        return getattr(group, value_name)
    return getattr(QEvent, value_name, 0)


def qt_enum_value(group_name, value_name):
    group = getattr(Qt, group_name, None)
    if group is not None and hasattr(group, value_name):
        return getattr(group, value_name)
    return getattr(Qt, value_name, 0)


def flag_is_set(value, flag):
    if not flag:
        return False
    try:
        return bool(value & flag)
    except TypeError:
        return value == flag
