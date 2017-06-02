# -*- coding: utf-8 -*-
#
# Copyright 2015 Bahtiar `kalkin-` Gadimov <bahtiar@gadimov.de>
#
# This file is part of python-omemo library.
#
# The python-omemo library is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# python-omemo is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# the python-omemo library.  If not, see <http://www.gnu.org/licenses/>.
#


import logging
import os

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers.modes import GCM

# On Windows we have to import a specific backend because the
# default_backend() mechanism doesnt work in Gajim for Windows.
# Its because of how Gajim is build with cx_freeze

if os.name == 'nt':
    from cryptography.hazmat.backends.openssl import backend
else:
    from cryptography.hazmat.backends import default_backend

log = logging.getLogger('gajim.plugin_system.omemo')

def aes_decrypt(_key, iv, payload):
    """ Use AES128 GCM with the given key and iv to decrypt the payload. """
    if len(_key) >= 32:
        # XEP-0384
        log.debug('XEP Compliant Key/Tag')
        data = payload
        key = _key[:16]
        tag = _key[16:]
    else:
        # Legacy
        log.debug('Legacy Key/Tag')
        data = payload[:-16]
        key = _key
        tag = payload[-16:]
    if os.name == 'nt':
        _backend = backend
    else:
        _backend = default_backend()
    decryptor = Cipher(
        algorithms.AES(key),
        GCM(iv, tag=tag),
        backend=_backend).decryptor()
    return decryptor.update(data) + decryptor.finalize()


def aes_encrypt(key, iv, plaintext):
    """ Use AES128 GCM with the given key and iv to encrypt the plaintext. """
    if os.name == 'nt':
        _backend = backend
    else:
        _backend = default_backend()
    encryptor = Cipher(
        algorithms.AES(key),
        GCM(iv),
        backend=_backend).encryptor()
    return encryptor.update(plaintext) + encryptor.finalize(), encryptor.tag
