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

import prof

from db import get_connection
from log import get_plugin_logger

logger = get_plugin_logger(__name__)

try:
    from omemo.state import OmemoState

    def _isTrusted(self, recipient_id, device_id):
        return True

    OmemoState.isTrusted = _isTrusted

except ImportError:
    logger.error('Could not import OmemoState')
    raise


class ProfOmemoState(object):
    """ ProfOmemoState Singleton """

    __states = {}

    def __new__(cls, *args, **kwargs):
        own_jid = ProfOmemoUser().account
        if not own_jid:
            raise RuntimeError('No User connected.')

        if own_jid not in cls.__states:
            # create the OmemoState for the current user
            connection = get_connection(own_jid)
            new_state = OmemoState(own_jid, connection, own_jid, None)
            cls.__states[own_jid] = new_state

        return cls.__states[own_jid]


class ProfActiveOmemoChats(object):

    __active = set()

    @classmethod
    def active(cls):
        return cls.__active

    @classmethod
    def add(cls, contact_jid):
        raw_jid = cls.as_raw_jid(contact_jid)
        cls.__active.add(raw_jid)
        prof.log_info('Added {0} to active chats'.format(raw_jid))

    @classmethod
    def remove(cls, contact_jid):
        raw_jid = cls.as_raw_jid(contact_jid)
        try:
            cls.__active.remove(raw_jid)
        except KeyError:
            pass

    @classmethod
    def account_is_active(cls, contact_jid):
        raw_jid = cls.as_raw_jid(contact_jid)
        prof.log_info('Active Chats: [{0}]'.format(', '.join(cls.active())))
        return raw_jid in cls.active()

    @classmethod
    def reset(cls):
        cls.__active = set()

    @staticmethod
    def as_raw_jid(contact_jid):
        raw_jid = None
        if contact_jid:
            raw_jid = contact_jid.rsplit('/', 1)[0]

        return raw_jid


class ProfOmemoUser(object):
    """ ProfOmemoUser Singleton """

    account = None
    fulljid = None

    @classmethod
    def set_user(cls, account, fulljid):
        cls.account = account
        cls.fulljid = fulljid

    @classmethod
    def reset(cls):
        cls.account = None
        cls.fulljid = None
