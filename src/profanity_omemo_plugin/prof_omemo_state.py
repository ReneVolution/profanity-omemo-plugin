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

from db import get_connection
from log import get_plugin_logger

logger = get_plugin_logger()

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

    __sessions = {}

    @classmethod
    def sessions(cls):
        return cls.__sessions

    @classmethod
    def add(cls, jid, session):
        account = jid.rsplit('/', 1)[0]
        cls.__sessions[account] = session

    @classmethod
    def remove(cls, account):
        try:
            del cls.__sessions[account]
        except KeyError:
            logger.warning('Tried to delete an unknown session.')

    @classmethod
    def get_session(cls, account):
        return cls.__sessions.get(account)

    @classmethod
    def has_session(cls, account):
        return account in cls.__sessions.keys()

    @classmethod
    def reset(cls):
        cls.__sessions = {}


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
