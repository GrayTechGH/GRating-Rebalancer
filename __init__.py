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

from calibre.customize import InterfaceActionBase


class GRatingRebalancerPlugin(InterfaceActionBase):
    '''
    Calibre loads this lightweight wrapper to discover plugin metadata.
    Keep GUI imports in ui.py or delayed methods so command-line Calibre
    utilities can inspect the plugin without loading Qt.
    '''

    name = 'GRating Rebalancer'
    description = _('Rebalance Goodreads ratings into library-relative scores')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'GrayTechGH'
    version = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)

    actual_plugin = 'calibre_plugins.GRating_Rebalancer.ui:InterfacePlugin'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.GRating_Rebalancer.config import ConfigWidget
        actual_plugin = getattr(self, 'actual_plugin_', None)
        gui = getattr(actual_plugin, 'gui', None)
        return ConfigWidget(getattr(gui, 'current_db', None))

    def save_settings(self, config_widget):
        config_widget.save_settings()

        actual_plugin = self.actual_plugin_
        if actual_plugin is not None:
            actual_plugin.apply_settings()
