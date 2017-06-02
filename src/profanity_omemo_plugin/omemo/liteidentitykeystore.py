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

from axolotl.ecc.djbec import DjbECPrivateKey, DjbECPublicKey
from axolotl.identitykey import IdentityKey
from axolotl.identitykeypair import IdentityKeyPair
from axolotl.state.identitykeystore import IdentityKeyStore

UNDECIDED = 2
TRUSTED = 1
UNTRUSTED = 0


class LiteIdentityKeyStore(IdentityKeyStore):
    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn

    def getIdentityKeyPair(self):
        q = "SELECT public_key, private_key FROM identities " + \
            "WHERE recipient_id = -1"
        c = self.dbConn.cursor()
        c.execute(q)
        result = c.fetchone()

        publicKey, privateKey = result
        return IdentityKeyPair(
            IdentityKey(DjbECPublicKey(publicKey[1:])),
            DjbECPrivateKey(privateKey))

    def getLocalRegistrationId(self):
        q = "SELECT registration_id FROM identities WHERE recipient_id = -1"
        c = self.dbConn.cursor()
        c.execute(q)
        result = c.fetchone()
        return result[0] if result else None

    def storeLocalData(self, registrationId, identityKeyPair):
        q = "INSERT INTO identities( " + \
            "recipient_id, registration_id, public_key, private_key) " + \
            "VALUES(-1, ?, ?, ?)"
        c = self.dbConn.cursor()
        c.execute(q,
                  (registrationId,
                   identityKeyPair.getPublicKey().getPublicKey().serialize(),
                   identityKeyPair.getPrivateKey().serialize()))

        self.dbConn.commit()

    def saveIdentity(self, recipientId, identityKey):
        q = "INSERT INTO identities (recipient_id, public_key, trust) " \
            "VALUES(?, ?, ?)"
        c = self.dbConn.cursor()

        if not self.getIdentity(recipientId, identityKey):
            c.execute(q, (recipientId,
                          identityKey.getPublicKey().serialize(),
                          UNDECIDED))
            self.dbConn.commit()

    def getIdentity(self, recipientId, identityKey):
        q = "SELECT * FROM identities WHERE recipient_id = ? " \
            "AND public_key = ?"
        c = self.dbConn.cursor()

        c.execute(q, (recipientId, identityKey.getPublicKey().serialize()))
        result = c.fetchone()

        return result is not None

    def deleteIdentity(self, recipientId, identityKey):
        q = "DELETE FROM identities WHERE recipient_id = ? AND public_key = ?"
        c = self.dbConn.cursor()
        c.execute(q, (recipientId,
                      identityKey.getPublicKey().serialize()))
        self.dbConn.commit()

    def isTrustedIdentity(self, recipientId, identityKey):
        q = "SELECT trust FROM identities WHERE recipient_id = ? " \
            "AND public_key = ?"
        c = self.dbConn.cursor()

        c.execute(q, (recipientId, identityKey.getPublicKey().serialize()))
        result = c.fetchone()

        states = [UNTRUSTED, TRUSTED, UNDECIDED]

        if result and result[0] in states:
            return result[0]
        else:
            return True

    def getAllFingerprints(self):
        q = "SELECT _id, recipient_id, public_key, trust FROM identities " \
            "WHERE recipient_id != -1 ORDER BY recipient_id ASC"
        c = self.dbConn.cursor()

        result = []
        for row in c.execute(q):
            result.append((row[0], row[1], row[2], row[3]))
        return result

    def getFingerprints(self, jid):
        q = "SELECT _id, recipient_id, public_key, trust FROM identities " \
            "WHERE recipient_id =? ORDER BY trust ASC"
        c = self.dbConn.cursor()

        result = []
        c.execute(q, (jid,))
        rows = c.fetchall()
        for row in rows:
            result.append((row[0], row[1], row[2], row[3]))
        return result

    def getTrustedFingerprints(self, jid):
        q = "SELECT public_key FROM identities WHERE recipient_id = ? AND trust = ?"
        c = self.dbConn.cursor()

        result = []
        c.execute(q, (jid, TRUSTED))
        rows = c.fetchall()
        for row in rows:
            result.append(row[0])
        return result

    def getUndecidedFingerprints(self, jid):
        q = "SELECT trust FROM identities WHERE recipient_id = ? AND trust = ?"
        c = self.dbConn.cursor()

        result = []
        c.execute(q, (jid, UNDECIDED))
        result = c.fetchall()

        return result

    def getNewFingerprints(self, jid):
        q = "SELECT _id FROM identities WHERE shown = 0 AND " \
            "recipient_id = ?"
        c = self.dbConn.cursor()
        result = []
        for row in c.execute(q, (jid,)):
            result.append(row[0])
        return result

    def setShownFingerprints(self, fingerprints):
        q = "UPDATE identities SET shown = 1 WHERE _id IN ({})" \
            .format(', '.join(['?'] * len(fingerprints)))
        c = self.dbConn.cursor()
        c.execute(q, fingerprints)
        self.dbConn.commit()

    def setTrust(self, identityKey, trust):
        q = "UPDATE identities SET trust = ? WHERE public_key = ?"
        c = self.dbConn.cursor()
        c.execute(q, (trust, identityKey.getPublicKey().serialize()))
        self.dbConn.commit()
