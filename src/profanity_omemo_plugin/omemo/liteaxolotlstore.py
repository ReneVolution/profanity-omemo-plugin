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

import logging

from axolotl.state.axolotlstore import AxolotlStore
from axolotl.util.keyhelper import KeyHelper

from .encryption import EncryptionState
from .liteidentitykeystore import LiteIdentityKeyStore
from .liteprekeystore import LitePreKeyStore
from .litesessionstore import LiteSessionStore
from .litesignedprekeystore import LiteSignedPreKeyStore
from .sql import SQLDatabase

log = logging.getLogger('gajim.plugin_system.omemo')

DEFAULT_PREKEY_AMOUNT = 100
MIN_PREKEY_AMOUNT = 80
SPK_ARCHIVE_TIME = 86400 * 15  # 15 Days
SPK_CYCLE_TIME = 86400         # 24 Hours


class LiteAxolotlStore(AxolotlStore):
    def __init__(self, connection):
        try:
            connection.text_factory = bytes
        except(AttributeError):
            raise AssertionError('Expected a sqlite3.Connection got ' +
                                 str(connection))

        self.sql = SQLDatabase(connection)
        self.identityKeyStore = LiteIdentityKeyStore(connection)
        self.preKeyStore = LitePreKeyStore(connection)
        self.signedPreKeyStore = LiteSignedPreKeyStore(connection)
        self.sessionStore = LiteSessionStore(connection)
        self.encryptionStore = EncryptionState(connection)

        if not self.getLocalRegistrationId():
            log.info("Generating Axolotl keys")
            self._generate_axolotl_keys()

    def _generate_axolotl_keys(self):
        identityKeyPair = KeyHelper.generateIdentityKeyPair()
        registrationId = KeyHelper.generateRegistrationId()
        preKeys = KeyHelper.generatePreKeys(KeyHelper.getRandomSequence(),
                                            DEFAULT_PREKEY_AMOUNT)
        self.storeLocalData(registrationId, identityKeyPair)

        signedPreKey = KeyHelper.generateSignedPreKey(
            identityKeyPair, KeyHelper.getRandomSequence(65536))

        self.storeSignedPreKey(signedPreKey.getId(), signedPreKey)

        for preKey in preKeys:
            self.storePreKey(preKey.getId(), preKey)

    def getIdentityKeyPair(self):
        return self.identityKeyStore.getIdentityKeyPair()

    def storeLocalData(self, registrationId, identityKeyPair):
        self.identityKeyStore.storeLocalData(registrationId, identityKeyPair)

    def getLocalRegistrationId(self):
        return self.identityKeyStore.getLocalRegistrationId()

    def saveIdentity(self, recepientId, identityKey):
        self.identityKeyStore.saveIdentity(recepientId, identityKey)

    def deleteIdentity(self, recipientId, identityKey):
        self.identityKeyStore.deleteIdentity(recipientId, identityKey)

    def isTrustedIdentity(self, recepientId, identityKey):
        return self.identityKeyStore.isTrustedIdentity(recepientId,
                                                       identityKey)

    def setTrust(self, identityKey, trust):
        return self.identityKeyStore.setTrust(identityKey, trust)

    def getTrustedFingerprints(self, jid):
        return self.identityKeyStore.getTrustedFingerprints(jid)

    def getUndecidedFingerprints(self, jid):
        return self.identityKeyStore.getUndecidedFingerprints(jid)

    def setShownFingerprints(self, jid):
        return self.identityKeyStore.setShownFingerprints(jid)

    def getNewFingerprints(self, jid):
        return self.identityKeyStore.getNewFingerprints(jid)

    def loadPreKey(self, preKeyId):
        return self.preKeyStore.loadPreKey(preKeyId)

    def loadPreKeys(self):
        return self.preKeyStore.loadPendingPreKeys()

    def storePreKey(self, preKeyId, preKeyRecord):
        self.preKeyStore.storePreKey(preKeyId, preKeyRecord)

    def containsPreKey(self, preKeyId):
        return self.preKeyStore.containsPreKey(preKeyId)

    def removePreKey(self, preKeyId):
        self.preKeyStore.removePreKey(preKeyId)

    def loadSession(self, recepientId, deviceId):
        return self.sessionStore.loadSession(recepientId, deviceId)

    def getActiveDeviceTuples(self):
        return self.sessionStore.getActiveDeviceTuples()

    def getInactiveSessionsKeys(self, recipientId):
        return self.sessionStore.getInactiveSessionsKeys(recipientId)

    def getSubDeviceSessions(self, recepientId):
        # TODO Reuse this
        return self.sessionStore.getSubDeviceSessions(recepientId)

    def getJidFromDevice(self, device_id):
        return self.sessionStore.getJidFromDevice(device_id)

    def storeSession(self, recepientId, deviceId, sessionRecord):
        self.sessionStore.storeSession(recepientId, deviceId, sessionRecord)

    def containsSession(self, recepientId, deviceId):
        return self.sessionStore.containsSession(recepientId, deviceId)

    def deleteSession(self, recepientId, deviceId):
        self.sessionStore.deleteSession(recepientId, deviceId)

    def deleteAllSessions(self, recepientId):
        self.sessionStore.deleteAllSessions(recepientId)

    def getSessionsFromJid(self, recipientId):
        return self.sessionStore.getSessionsFromJid(recipientId)

    def getSessionsFromJids(self, recipientId):
        return self.sessionStore.getSessionsFromJids(recipientId)

    def getAllSessions(self):
        return self.sessionStore.getAllSessions()

    def loadSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.loadSignedPreKey(signedPreKeyId)

    def loadSignedPreKeys(self):
        return self.signedPreKeyStore.loadSignedPreKeys()

    def storeSignedPreKey(self, signedPreKeyId, signedPreKeyRecord):
        self.signedPreKeyStore.storeSignedPreKey(signedPreKeyId,
                                                 signedPreKeyRecord)

    def containsSignedPreKey(self, signedPreKeyId):
        return self.signedPreKeyStore.containsSignedPreKey(signedPreKeyId)

    def removeSignedPreKey(self, signedPreKeyId):
        self.signedPreKeyStore.removeSignedPreKey(signedPreKeyId)

    def getNextSignedPreKeyId(self):
        return self.signedPreKeyStore.getNextSignedPreKeyId()

    def getCurrentSignedPreKeyId(self):
        return self.signedPreKeyStore.getCurrentSignedPreKeyId()

    def getSignedPreKeyTimestamp(self, signedPreKeyId):
        return self.signedPreKeyStore.getSignedPreKeyTimestamp(signedPreKeyId)

    def removeOldSignedPreKeys(self, timestamp):
        self.signedPreKeyStore.removeOldSignedPreKeys(timestamp)
