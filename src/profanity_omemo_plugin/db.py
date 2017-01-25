# -*- coding: utf-8 -*-
#
# Copyright 2017 René `reneVolution` Calles <info@renevolution.com>
#
# This file is part of Profanity OMEMO plugin.
#
# The Profanity OMEMO plugin is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Profanity OMEMO plugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# the Profanity OMEMO plugin.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import os

from profanity_omemo_plugin.constants import XDG_DATA_HOME
from profanity_omemo_plugin.log import get_plugin_logger

log = get_plugin_logger(__name__)

try:
    import sqlite3
except ImportError:
    log.error('Could not import sqlite3')
    raise


def get_connection(user):
    """ Open in memory sqlite db and create a table. """
    db_path = _get_db_path(user)
    db_root = os.path.dirname(db_path)
    if not os.path.isdir(db_root):
        os.makedirs(db_root)
    log.info('Using database path {}'.format(db_path))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


def _get_local_data_path(user):
    if not user:
        raise RuntimeError('User cannot be None.')

    safe_username = user.replace('@', '_at_')

    return os.path.join(XDG_DATA_HOME, 'profanity', 'omemo', safe_username)


def _get_db_path(user):
    return os.path.join(_get_local_data_path(user), 'omemo.db')
