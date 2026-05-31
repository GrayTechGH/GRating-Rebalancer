#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

from html import escape

try:
    load_translations()
except NameError:
    pass

try:
    _
except NameError:
    def _(text):
        return text


def build_about_text():
    from calibre_plugins.GRating_Rebalancer.__init__ import GRatingRebalancerPlugin

    version = '.'.join(str(part) for part in GRatingRebalancerPlugin.version)
    minimum = '.'.join(
        str(part) for part in GRatingRebalancerPlugin.minimum_calibre_version
    )

    return ''.join([
        '<h3>{}</h3>'.format(escape(GRatingRebalancerPlugin.name)),
        '<p>{}</p>'.format(
            escape(_('Created by {}').format(GRatingRebalancerPlugin.author))
        ),
        '<p>{}<br>{}</p>'.format(
            escape(_('Version {}').format(version)),
            escape(_('Requires calibre >= {}').format(minimum)),
        ),
        '<p>{}</p>'.format(
            escape(_(
                'Creates library-relative Goodreads scores without changing '
                'the raw Goodreads rating or vote fields.'
            ))
        ),
    ])
