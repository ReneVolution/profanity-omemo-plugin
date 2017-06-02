# -*- coding: utf-8 -*-
#
# Copyright 2015 Tarek Galal <tare2.galal@gmail.com>
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

from axolotl.state.sessionrecord import SessionRecord
from axolotl.state.sessionstore import SessionStore


class LiteSessionStore(SessionStore):
    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

    def loadSession(self, recipientId, deviceId):
        q = "SELECT record FROM sessions WHERE recipient_id = ? AND device_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId, deviceId))
        result = c.fetchone()

        if result:
            return SessionRecord(serialized=result[0])
        else:
            return SessionRecord()

    def getSubDeviceSessions(self, recipientId):
        q = "SELECT device_id from sessions WHERE recipient_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId, ))
        result = c.fetchall()

        deviceIds = [r[0] for r in result]
        return deviceIds

    def getJidFromDevice(self, device_id):
        q = "SELECT recipient_id from sessions WHERE device_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (device_id, ))
        result = c.fetchone()

        return result[0]

    def getActiveDeviceTuples(self):
        q = "SELECT recipient_id, device_id FROM sessions WHERE active = 1"
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q):
            result.append((row[0], row[1]))
        return result

    def storeSession(self, recipientId, deviceId, sessionRecord):
        self.deleteSession(recipientId, deviceId)

        q = "INSERT INTO sessions(recipient_id, device_id, record) VALUES(?,?,?)"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId, deviceId, sessionRecord.serialize()))
        self.dbConn.commit()

    def containsSession(self, recipientId, deviceId):
        q = "SELECT record FROM sessions WHERE recipient_id = ? AND device_id = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId, deviceId))
        result = c.fetchone()

        return result is not None

    def deleteSession(self, recipientId, deviceId):
        q = "DELETE FROM sessions WHERE recipient_id = ? AND device_id = ?"
        self.dbConn.cursor().execute(q, (recipientId, deviceId))
        self.dbConn.commit()

    def deleteAllSessions(self, recipientId):
        q = "DELETE FROM sessions WHERE recipient_id = ?"
        self.dbConn.cursor().execute(q, (recipientId, ))
        self.dbConn.commit()

    def getAllSessions(self):
        q = "SELECT _id, recipient_id, device_id, record, active from sessions"
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q):
            result.append((row[0], row[1], row[2], row[3], row[4]))
        return result

    def getSessionsFromJid(self, recipientId):
        q = "SELECT _id, recipient_id, device_id, record, active from sessions" \
            " WHERE recipient_id = ?"
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q, (recipientId,)):
            result.append((row[0], row[1], row[2], row[3], row[4]))
        return result

    def getSessionsFromJids(self, recipientId):
        q = "SELECT _id, recipient_id, device_id, record, active from sessions" \
            " WHERE recipient_id IN ({})" \
            .format(', '.join(['?'] * len(recipientId)))
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q, recipientId):
            result.append((row[0], row[1], row[2], row[3], row[4]))
        return result

    def setActiveState(self, deviceList, jid):
        c = self.dbConn.cursor()

        q = "UPDATE sessions SET active = {} " \
            "WHERE recipient_id = '{}' AND device_id IN ({})" \
            .format(1, jid, ', '.join(['?'] * len(deviceList)))
        c.execute(q, deviceList)

        q = "UPDATE sessions SET active = {} " \
            "WHERE recipient_id = '{}' AND device_id NOT IN ({})" \
            .format(0, jid, ', '.join(['?'] * len(deviceList)))
        c.execute(q, deviceList)
        self.dbConn.commit()

    def getInactiveSessionsKeys(self, recipientId):
        q = "SELECT record FROM sessions WHERE active = 0 AND recipient_id = ?"
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q, (recipientId,)):
            public_key = (SessionRecord(serialized=row[0]).
                          getSessionState().getRemoteIdentityKey().
                          getPublicKey())
            result.append(public_key.serialize())
        return result
