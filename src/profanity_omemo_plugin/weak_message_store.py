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

from prof_omemo_state import ProfOmemoState


class WeakMessageStore(object):

    def __init__(self):
        # - maybe max store size (10 Messages FIFO drop)
        # - configure timeout
        # - run a checker thread
        # - use wait on empty store to save cpu
        self._messages = []

    def add(self, message_dict):
        """ Adds a Message dict to the store.

        :message_dict: {'from': 'romeo@montague.lit',
                        'to': 'juliet@capulet.lit',
                        'message': 'Some Message',}

        - adds a timestamp to the dict
        - tries to post immediately

        """
        pass

    def post_message(self, stanza):
        # post the encrypted message, e.g. prof.send_message(stanza)
        pass

    def trigger(self):
        """
        Gets triggered from the outside to check all messages if
        they are ready to encrypt and calls post_message.

        Or -> requests the missing bundles.

        """

    def on_timeout(self):
        # posts some information to the ui if the bundle is not received yet
        # or a device is not trusted."
        pass