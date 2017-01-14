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

import logging

from constants import LOGGER_NAME

PROFANITY_IS_HOST = True

try:
    import prof
except ImportError:
    PROFANITY_IS_HOST = False


class ProfLogHandler(logging.Handler):

    def __init__(self):
        super(ProfLogHandler, self).__init__()
        self.prof_formatter = logging.Formatter('%(name)s - %(message)s')
        self.setFormatter(self.prof_formatter)

    def emit(self, record):

        if PROFANITY_IS_HOST:
            level_fn_map = {
                10: prof.log_debug,  # DEBUG
                20: prof.log_info,  # INFO
                30: prof.log_warning,  # WARNING
                40: prof.log_error  # ERROR
            }

            try:
                level_fn_map[record.levelno](self.format(record))
            except Exception as e:
                prof.log_error(u'Could not log last message. {0}'.format(str(e)))

python_omemo_logger = logging.getLogger('omemo')
python_omemo_logger.setLevel(logging.DEBUG)
python_omemo_logger.addHandler(ProfLogHandler())


def get_plugin_logger():
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(ProfLogHandler())

    return logger
