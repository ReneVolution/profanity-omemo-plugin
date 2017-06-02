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

from __future__ import unicode_literals

import logging
import traceback

PROFANITY_IS_HOST = True

try:
    import prof
except ImportError:
    PROFANITY_IS_HOST = False


class ProfLogHandler(logging.Handler):

    def __init__(self, prefix=None):
        super(ProfLogHandler, self).__init__()

        if prefix:
            fmt_str = '{0} - %(message)s'.format(prefix)
        else:
            fmt_str = '%(name)s - %(message)s'

        self.prof_formatter = logging.Formatter(fmt_str)
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
                log_message = self.format(record)
                if record.levelno == 40 and record.exc_info:
                    tb_info = record.exc_info
                    log_message += '\n' + traceback.print_exception(*tb_info)

                level_fn_map[record.levelno](log_message)
            except Exception as e:
                prof.log_error('Could not log last message. {0}'.format(e.message))


python_omemo_logger = logging.getLogger('omemo')
python_omemo_logger.setLevel(logging.DEBUG)
python_omemo_logger.addHandler(ProfLogHandler())


def get_plugin_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(ProfLogHandler(prefix='ProfOmemoPlugin'))

    return logger
