# -*- coding: utf-8 -*-
#
# Copyright 2015 Bahtiar `kalkin-` Gadimov <bahtiar@gadimov.de>
# Copyright 2015 Daniel Gultsch <daniel@cgultsch.de>
#
# This file is part of Gajim-OMEMO plugin.
#
# The Gajim-OMEMO plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Gajim-OMEMO is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# the Gajim-OMEMO plugin.  If not, see <http://www.gnu.org/licenses/>.
#


class EncryptionState():
    """ Used to store if OMEMO is enabled or not between gajim restarts """

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

    def activate(self, jid):
        q = """INSERT OR REPLACE INTO encryption_state (jid, encryption)
               VALUES (?, 1) """

        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
        self.dbConn.commit()

    def deactivate(self, jid):
        q = """INSERT OR REPLACE INTO encryption_state (jid, encryption)
               VALUES (?, 0)"""

        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
        self.dbConn.commit()

    def is_active(self, jid):
        q = 'SELECT encryption FROM encryption_state where jid = ?;'
        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
        result = c.fetchone()
        if result is None:
            return False
        return result[0]

    def exist(self, jid):
        q = 'SELECT encryption FROM encryption_state where jid = ?;'
        c = self.dbConn.cursor()
        c.execute(q, (jid, ))
        result = c.fetchone()
        if result is None:
            return False
        else:
            return True
