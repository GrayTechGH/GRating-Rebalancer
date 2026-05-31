#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai


__license__ = 'GPL v3'
__copyright__ = '2026, GRating Rebalancer contributors'
__docformat__ = 'restructuredtext en'

import re


TAG_RE = re.compile(r'<[^>]+>')


def cleanup_value(value):
    if value is None:
        return ''
    text = TAG_RE.sub('', str(value))
    text = text.replace('&nbsp;', ' ')
    return ' '.join(text.split())


def format_authors(authors):
    if not authors:
        return 'Unknown Author'
    return ' & '.join(cleanup_value(author) for author in authors if cleanup_value(author))
