# -*- coding: utf-8 -*-
#
# Copyright 2015 Bahtiar `kalkin-` Gadimov <bahtiar@gadimov.de>
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
import time
from base64 import b64encode

from Crypto.Random import get_random_bytes
from axolotl.duplicatemessagexception import DuplicateMessageException
from axolotl.ecc.djbec import DjbECPublicKey
from axolotl.identitykey import IdentityKey
from axolotl.invalidmessageexception import InvalidMessageException
from axolotl.invalidversionexception import InvalidVersionException
from axolotl.nosessionexception import NoSessionException
from axolotl.protocol.prekeywhispermessage import PreKeyWhisperMessage
from axolotl.protocol.whispermessage import WhisperMessage
from axolotl.sessionbuilder import SessionBuilder
from axolotl.sessioncipher import SessionCipher
from axolotl.state.prekeybundle import PreKeyBundle
from axolotl.untrustedidentityexception import UntrustedIdentityException
from axolotl.util.keyhelper import KeyHelper

from .aes_gcm import NoValidSessions, decrypt, encrypt
from .liteaxolotlstore import (LiteAxolotlStore, DEFAULT_PREKEY_AMOUNT,
                               MIN_PREKEY_AMOUNT, SPK_CYCLE_TIME,
                               SPK_ARCHIVE_TIME)

log = logging.getLogger('gajim.plugin_system.omemo')
logAxolotl = logging.getLogger('axolotl')


UNTRUSTED = 0
TRUSTED = 1
UNDECIDED = 2


class OmemoState:
    def __init__(self, own_jid, connection, account, plugin):
        """ Instantiates an OmemoState object.

            :param connection: an :py:class:`sqlite3.Connection`
        """
        self.account = account
        self.plugin = plugin
        self.session_ciphers = {}
        self.own_jid = own_jid
        self.device_ids = {}
        self.own_devices = []
        self.store = LiteAxolotlStore(connection)
        self.encryption = self.store.encryptionStore
        for jid, device_id in self.store.getActiveDeviceTuples():
            if jid != own_jid:
                self.add_device(jid, device_id)
            else:
                self.add_own_device(device_id)

        log.info(self.account + ' => Roster devices after boot:' +
                 str(self.device_ids))
        log.info(self.account + ' => Own devices after boot:' +
                 str(self.own_devices))
        log.debug(self.account + ' => ' +
                  str(self.store.preKeyStore.getPreKeyCount()) +
                  ' PreKeys available')

    def build_session(self, recipient_id, device_id, bundle_dict):
        sessionBuilder = SessionBuilder(self.store, self.store, self.store,
                                        self.store, recipient_id, device_id)

        registration_id = self.store.getLocalRegistrationId()

        preKeyPublic = DjbECPublicKey(bundle_dict['preKeyPublic'][1:])

        signedPreKeyPublic = DjbECPublicKey(bundle_dict['signedPreKeyPublic'][
            1:])
        identityKey = IdentityKey(DjbECPublicKey(bundle_dict['identityKey'][
            1:]))

        prekey_bundle = PreKeyBundle(
            registration_id, device_id, bundle_dict['preKeyId'], preKeyPublic,
            bundle_dict['signedPreKeyId'], signedPreKeyPublic,
            bundle_dict['signedPreKeySignature'], identityKey)

        sessionBuilder.processPreKeyBundle(prekey_bundle)
        return self.get_session_cipher(recipient_id, device_id)

    def set_devices(self, name, devices):
        """ Return a an.

            Parameters
            ----------
            jid : string
                The contacts jid

            devices: [int]
                A list of devices
        """

        self.device_ids[name] = devices
        log.info(self.account + ' => Saved devices for ' + name)

    def add_device(self, name, device_id):
        if name not in self.device_ids:
            self.device_ids[name] = [device_id]
        elif device_id not in self.device_ids[name]:
            self.device_ids[name].append(device_id)

    def set_own_devices(self, devices):
        """ Overwrite the current :py:attribute:`OmemoState.own_devices` with
            the given devices.

            Parameters
            ----------
            devices : [int]
                A list of device_ids
        """
        self.own_devices = devices
        log.info(self.account + ' => Saved own devices')

    def add_own_device(self, device_id):
        if device_id not in self.own_devices:
            self.own_devices.append(device_id)

    @property
    def own_device_id(self):
        reg_id = self.store.getLocalRegistrationId()
        assert reg_id is not None, \
            "Requested device_id but there is no generated"

        return ((reg_id % 2147483646) + 1)

    def own_device_id_published(self):
        """ Return `True` only if own device id was added via
            :py:method:`OmemoState.set_own_devices()`.
        """
        return self.own_device_id in self.own_devices

    @property
    def bundle(self):
        self.checkPreKeyAmount()
        prekeys = [
            (k.getId(), b64encode(k.getKeyPair().getPublicKey().serialize()))
            for k in self.store.loadPreKeys()
        ]

        identityKeyPair = self.store.getIdentityKeyPair()

        self.cycleSignedPreKey(identityKeyPair)

        signedPreKey = self.store.loadSignedPreKey(
            self.store.getCurrentSignedPreKeyId())

        result = {
            'signedPreKeyId': signedPreKey.getId(),
            'signedPreKeyPublic':
            b64encode(signedPreKey.getKeyPair().getPublicKey().serialize()),
            'signedPreKeySignature': b64encode(signedPreKey.getSignature()),
            'identityKey':
            b64encode(identityKeyPair.getPublicKey().serialize()),
            'prekeys': prekeys
        }
        return result

    def decrypt_msg(self, msg_dict):
        own_id = self.own_device_id
        if msg_dict['sid'] == own_id:
            log.info('Received previously sent message by us')
            return
        if own_id not in msg_dict['keys']:
            log.warning('OMEMO message does not contain our device key')
            return

        iv = msg_dict['iv']
        sid = msg_dict['sid']
        sender_jid = msg_dict['sender_jid']
        payload = msg_dict['payload']

        encrypted_key = msg_dict['keys'][own_id]

        try:
            key = self.handlePreKeyWhisperMessage(sender_jid, sid,
                                                  encrypted_key)
        except (InvalidVersionException, InvalidMessageException):
            try:
                key = self.handleWhisperMessage(sender_jid, sid, encrypted_key)
            except (NoSessionException, InvalidMessageException) as e:
                log.warning('No Session found ' + e.message)
                log.warning('sender_jid =>  ' + str(sender_jid) + ' sid =>' +
                            str(sid))
                return
            except (DuplicateMessageException) as e:
                log.warning('Duplicate message found ' + str(e.args))
                return

        except (DuplicateMessageException) as e:
            log.warning('Duplicate message found ' + str(e.args))
            return

        result = decrypt(key, iv, payload)
        try:
            result = unicode(result)
        except NameError:  # Py3
            pass

        log.debug("Decrypted Message => " + result)
        return result

    def create_msg(self, from_jid, jid, plaintext):
        key = get_random_bytes(16)
        iv = get_random_bytes(16)
        encrypted_keys = {}

        devices_list = self.device_list_for(jid)
        if len(devices_list) == 0:
            log.error('No known devices')
            return

        payload, tag = encrypt(key, iv, plaintext)

        key += tag

        # Encrypt the message key with for each of receivers devices
        for device in devices_list:
            try:
                if self.isTrusted(jid, device) == TRUSTED:
                    cipher = self.get_session_cipher(jid, device)
                    cipher_key = cipher.encrypt(key)
                    prekey = isinstance(cipher_key, PreKeyWhisperMessage)
                    encrypted_keys[device] = (cipher_key.serialize(), prekey)
                else:
                    log.debug('Skipped Device because Trust is: ' +
                              str(self.isTrusted(jid, device)))
            except:
                log.warning('Failed to find key for device ' + str(device))

        if len(encrypted_keys) == 0:
            log.error('Encrypted keys empty')
            raise NoValidSessions('Encrypted keys empty')

        my_other_devices = set(self.own_devices) - set({self.own_device_id})
        # Encrypt the message key with for each of our own devices
        for device in my_other_devices:
            try:
                if self.isTrusted(from_jid, device) == TRUSTED:
                    cipher = self.get_session_cipher(from_jid, device)
                    cipher_key = cipher.encrypt(key)
                    prekey = isinstance(cipher_key, PreKeyWhisperMessage)
                    encrypted_keys[device] = (cipher_key.serialize(), prekey)
                else:
                    log.debug('Skipped own Device because Trust is: ' +
                              str(self.isTrusted(from_jid, device)))
            except:
                log.warning('Failed to find key for device ' + str(device))

        result = {'sid': self.own_device_id,
                  'keys': encrypted_keys,
                  'jid': jid,
                  'iv': iv,
                  'payload': payload}

        log.debug('Finished encrypting message')
        return result

    def create_gc_msg(self, from_jid, jid, plaintext):
        key = get_random_bytes(16)
        iv = get_random_bytes(16)
        encrypted_keys = {}
        room = jid
        encrypted_jids = []

        devices_list = self.device_list_for(jid, True)

        if len(devices_list) == 0:
            log.error('No known devices')
            return

        payload, tag = encrypt(key, iv, plaintext)

        key += tag

        for tup in devices_list:
            self.get_session_cipher(tup[0], tup[1])

        # Encrypt the message key with for each of receivers devices
        for nick in self.plugin.groupchat[room]:
            jid_to = self.plugin.groupchat[room][nick]
            if jid_to == self.own_jid:
                continue
            if jid_to in encrypted_jids:  # We already encrypted to this JID
                continue
            for rid, cipher in self.session_ciphers[jid_to].items():
                try:
                    if self.isTrusted(jid_to, rid) == TRUSTED:
                        cipher_key = cipher.encrypt(key)
                        prekey = isinstance(cipher_key, PreKeyWhisperMessage)
                        encrypted_keys[rid] = (cipher_key.serialize(), prekey)
                    else:
                        log.debug('Skipped Device because Trust is: ' +
                                  str(self.isTrusted(jid_to, rid)))
                except:
                    log.exception('ERROR:')
                    log.warning('Failed to find key for device ' +
                                str(rid))
            encrypted_jids.append(jid_to)
        if len(encrypted_keys) == 0:
            log_msg = 'Encrypted keys empty'
            log.error(log_msg)
            raise NoValidSessions(log_msg)

        my_other_devices = set(self.own_devices) - set({self.own_device_id})
        # Encrypt the message key with for each of our own devices
        for dev in my_other_devices:
            try:
                cipher = self.get_session_cipher(from_jid, dev)
                if self.isTrusted(from_jid, dev) == TRUSTED:
                    cipher_key = cipher.encrypt(key)
                    prekey = isinstance(cipher_key, PreKeyWhisperMessage)
                    encrypted_keys[dev] = (cipher_key.serialize(), prekey)
                else:
                    log.debug('Skipped own Device because Trust is: ' +
                              str(self.isTrusted(from_jid, dev)))
            except:
                log.exception('ERROR:')
                log.warning('Failed to find key for device ' + str(dev))

        result = {'sid': self.own_device_id,
                  'keys': encrypted_keys,
                  'jid': jid,
                  'iv': iv,
                  'payload': payload}

        log.debug('Finished encrypting message')
        return result

    def device_list_for(self, jid, gc=False):
        """ Return a list of known device ids for the specified jid.
            Parameters
            ----------
            jid : string
                The contacts jid
            gc : bool
                Groupchat Message
        """
        if gc:
            room = jid
            devicelist = []
            for nick in self.plugin.groupchat[room]:
                jid_to = self.plugin.groupchat[room][nick]
                if jid_to == self.own_jid:
                    continue
                for device in self.device_ids[jid_to]:
                    devicelist.append((jid_to, device))
            return devicelist

        if jid == self.own_jid:
            return set(self.own_devices) - set({self.own_device_id})
        if jid not in self.device_ids:
            return set()
        return set(self.device_ids[jid])

    def isTrusted(self, recipient_id, device_id):
        record = self.store.loadSession(recipient_id, device_id)
        identity_key = record.getSessionState().getRemoteIdentityKey()
        return self.store.isTrustedIdentity(recipient_id, identity_key)

    def getFingerprints(self, recipient_id):
        return self.store.getFingerprints(recipient_id)

    def getTrustedFingerprints(self, recipient_id):
        inactive = self.store.getInactiveSessionsKeys(recipient_id)
        trusted = self.store.getTrustedFingerprints(recipient_id)
        trusted = set(trusted) - set(inactive)

        return trusted

    def getUndecidedFingerprints(self, recipient_id):
        inactive = self.store.getInactiveSessionsKeys(recipient_id)
        undecided = self.store.getUndecidedFingerprints(recipient_id)
        undecided = set(undecided) - set(inactive)

        return undecided

    def devices_without_sessions(self, jid):
        """ List device_ids for the given jid which have no axolotl session.

            Parameters
            ----------
            jid : string
                The contacts jid

            Returns
            -------
            [int]
                A list of device_ids
        """
        known_devices = self.device_list_for(jid)
        missing_devices = [dev
                           for dev in known_devices
                           if not self.store.containsSession(jid, dev)]
        if missing_devices:
            log.info(self.account + ' => Missing device sessions for ' +
                     jid + ': ' + str(missing_devices))
        return missing_devices

    def get_session_cipher(self, jid, device_id):
        if jid not in self.session_ciphers:
            self.session_ciphers[jid] = {}

        if device_id not in self.session_ciphers[jid]:
            cipher = SessionCipher(self.store, self.store, self.store,
                                   self.store, jid, device_id)
            self.session_ciphers[jid][device_id] = cipher

        return self.session_ciphers[jid][device_id]

    def handlePreKeyWhisperMessage(self, recipient_id, device_id, key):
        preKeyWhisperMessage = PreKeyWhisperMessage(serialized=key)
        if not preKeyWhisperMessage.getPreKeyId():
            raise Exception("Received PreKeyWhisperMessage without PreKey =>" +
                            recipient_id)
        sessionCipher = self.get_session_cipher(recipient_id, device_id)
        try:
            log.debug(self.account +
                      " => Received PreKeyWhisperMessage from " +
                      recipient_id)
            key = sessionCipher.decryptPkmsg(preKeyWhisperMessage)
            # Publish new bundle after PreKey has been used
            # for building a new Session
            self.plugin.publish_bundle(self.account)
            self.add_device(recipient_id, device_id)
            return key
        except UntrustedIdentityException as e:
            log.info(self.account + " => Received WhisperMessage " +
                     "from Untrusted Fingerprint! => " + e.getName())

    def handleWhisperMessage(self, recipient_id, device_id, key):
        whisperMessage = WhisperMessage(serialized=key)
        log.debug(self.account + " => Received WhisperMessage from " +
                  recipient_id)
        if self.isTrusted(recipient_id, device_id):
            sessionCipher = self.get_session_cipher(recipient_id, device_id)
            key = sessionCipher.decryptMsg(whisperMessage)
            self.add_device(recipient_id, device_id)
            return key
        else:
            raise Exception("Received WhisperMessage "
                            "from Untrusted Fingerprint! => " + recipient_id)

    def checkPreKeyAmount(self):
        # Check if enough PreKeys are available
        preKeyCount = self.store.preKeyStore.getPreKeyCount()
        if preKeyCount < MIN_PREKEY_AMOUNT:
            newKeys = DEFAULT_PREKEY_AMOUNT - preKeyCount
            self.store.preKeyStore.generateNewPreKeys(newKeys)
            log.info(self.account + ' => ' + str(newKeys) +
                     ' PreKeys created')

    def cycleSignedPreKey(self, identityKeyPair):
        # Publish every SPK_CYCLE_TIME a new SignedPreKey
        # Delete all exsiting SignedPreKeys that are older
        # then SPK_ARCHIVE_TIME

        # Check if SignedPreKey exist and create if not
        if not self.store.getCurrentSignedPreKeyId():
            signedPreKey = KeyHelper.generateSignedPreKey(
                identityKeyPair, self.store.getNextSignedPreKeyId())
            self.store.storeSignedPreKey(signedPreKey.getId(), signedPreKey)
            log.debug(self.account +
                      ' => New SignedPreKey created, because none existed')

        # if SPK_CYCLE_TIME is reached, generate a new SignedPreKey
        now = int(time.time())
        timestamp = self.store.getSignedPreKeyTimestamp(
            self.store.getCurrentSignedPreKeyId())

        if int(timestamp) < now - SPK_CYCLE_TIME:
            signedPreKey = KeyHelper.generateSignedPreKey(
                identityKeyPair, self.store.getNextSignedPreKeyId())
            self.store.storeSignedPreKey(signedPreKey.getId(), signedPreKey)
            log.debug(self.account + ' => Cycled SignedPreKey')

        # Delete all SignedPreKeys that are older than SPK_ARCHIVE_TIME
        timestamp = now - SPK_ARCHIVE_TIME
        self.store.removeOldSignedPreKeys(timestamp)
