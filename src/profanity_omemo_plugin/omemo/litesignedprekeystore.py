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

from axolotl.invalidkeyidexception import InvalidKeyIdException
from axolotl.state.signedprekeyrecord import SignedPreKeyRecord
from axolotl.state.signedprekeystore import SignedPreKeyStore
from axolotl.util.medium import Medium


class LiteSignedPreKeyStore(SignedPreKeyStore):
    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

    def loadSignedPreKey(self, signedPreKeyId):
        q = "SELECT record FROM signed_prekeys WHERE prekey_id = ?"

        cursor = self.dbConn.cursor()
        cursor.execute(q, (signedPreKeyId, ))

        result = cursor.fetchone()
        if not result:
            raise InvalidKeyIdException("No such signedprekeyrecord! %s " %
                                        signedPreKeyId)

        return SignedPreKeyRecord(serialized=result[0])

    def loadSignedPreKeys(self):
        q = "SELECT record FROM signed_prekeys"

        cursor = self.dbConn.cursor()
        cursor.execute(q, )
        result = cursor.fetchall()
        results = []
        for row in result:
            results.append(SignedPreKeyRecord(serialized=row[0]))

        return results

    def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        q = "INSERT INTO signed_prekeys (prekey_id, record) VALUES(?,?)"
        cursor = self.dbConn.cursor()
        cursor.execute(q, (signedPreKeyId, signedPreKeyRecord.serialize()))
        self.dbConn.commit()

    def containsSignedPreKey(self, signedPreKeyId):
        q = "SELECT record FROM signed_prekeys WHERE prekey_id = ?"
        cursor = self.dbConn.cursor()
        cursor.execute(q, (signedPreKeyId, ))
        return cursor.fetchone() is not None

    def removeSignedPreKey(self, signedPreKeyId):
        q = "DELETE FROM signed_prekeys WHERE prekey_id = ?"
        cursor = self.dbConn.cursor()
        cursor.execute(q, (signedPreKeyId, ))
        self.dbConn.commit()

    def getNextSignedPreKeyId(self):
        result = self.getCurrentSignedPreKeyId()
        if not result:
            return 1  # StartId if no SignedPreKeys exist
        else:
            return (result % (Medium.MAX_VALUE - 1)) + 1

    def getCurrentSignedPreKeyId(self):
        q = "SELECT MAX(prekey_id) FROM signed_prekeys"

        cursor = self.dbConn.cursor()
        cursor.execute(q)
        result = cursor.fetchone()
        if not result:
            return None
        else:
            return result[0]

    def getSignedPreKeyTimestamp(self, signedPreKeyId):
        q = "SELECT strftime('%s', timestamp) FROM " \
            "signed_prekeys WHERE prekey_id = ?"

        cursor = self.dbConn.cursor()
        cursor.execute(q, (signedPreKeyId, ))

        result = cursor.fetchone()
        if not result:
            raise InvalidKeyIdException("No such signedprekeyrecord! %s " %
                                        signedPreKeyId)

        return result[0]

    def removeOldSignedPreKeys(self, timestamp):
        q = "DELETE FROM signed_prekeys " \
            "WHERE timestamp < datetime(?, 'unixepoch')"
        cursor = self.dbConn.cursor()
        cursor.execute(q, (timestamp, ))
        self.dbConn.commit()
