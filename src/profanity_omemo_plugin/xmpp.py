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
from __future__ import absolute_import
from __future__ import unicode_literals

import random
import uuid
from base64 import b64decode, b64encode

from profanity_omemo_plugin.constants import NS_OMEMO, NS_DEVICE_LIST, \
    NS_DEVICE_LIST_NOTIFY, NS_BUNDLES
from profanity_omemo_plugin.errors import StanzaNodeNotFound
from profanity_omemo_plugin.log import get_plugin_logger
from profanity_omemo_plugin.prof_omemo_state import ProfOmemoState, \
    ProfOmemoUser

try:
    from lxml import etree as ET
except ImportError:
    # fallback to the default ElementTree module
    import xml.etree.ElementTree as ET

logger = get_plugin_logger(__name__)


################################################################################
# Helper
################################################################################

def stanza_as_xml(stanza):
    try:
        xml = ET.fromstring(stanza)
    except UnicodeEncodeError:
        xml = ET.fromstring(stanza.encode('utf-8'))

    return xml


def find_node(xml, name, ns=None):
    node = None

    if ns:
        node = xml.find('.//{%s}%s' % (ns, name))

    if node is None:
        # ChatSecure seems to use the wrong xml namespace
        # use a fallback here with the custom namespace for some nodes
        node = xml.find('.//{%s}%s' % ('jabber:client', name))

    if node is None:
        raise StanzaNodeNotFound('Node {0} not found.')

    return node


def encrypt_stanza(stanza):
    msg_xml = stanza_as_xml(stanza)
    fulljid = msg_xml.attrib.get('from', ProfOmemoUser().fulljid)
    jid = msg_xml.attrib['to']
    account = jid.rsplit('/', 1)[0]
    msg_id = msg_xml.attrib['id']
    body_node = msg_xml.find('.//body')
    plaintext = body_node.text

    try:
        plaintext = plaintext.encode('utf-8')
    except:
        pass

    return create_encrypted_message(fulljid, account, plaintext, msg_id=msg_id)


def update_devicelist(from_jid, recipient, devices):
    omemo_state = ProfOmemoState()

    logger.debug('Update devices for account: {0}'.format(from_jid))
    logger.info('Adding Device ID\'s: {0} for {1}.'.format(devices, recipient))
    if devices:
        if from_jid == recipient:
            logger.info('Adding own devices')
            omemo_state.set_own_devices(devices)
        else:
            logger.info('Adding recipients devices')
            omemo_state.set_devices(recipient, devices)

        omemo_state.store.sessionStore.setActiveState(devices, from_jid)
        logger.info('Device List update done.')


def get_recipient(stanza):
    try:
        xml = stanza_as_xml(stanza)
        recipient = xml.attrib['to']
    except:
        return None

    return recipient


def get_root_attrib(stanza, attrib):
    try:
        xml = stanza_as_xml(stanza)
        result = xml.attrib[attrib]
    except KeyError:
        logger.error('Stanza has not attrib {0}'.format(attrib))
        return None
    except Exception as e:
        logger.error('Failed to parse stanza: {0}'.format(stanza))
        logger.error('{0}: {1}'.format(type(e).__name__, e.message))
        return None

    return result


################################################################################
# Stanza validation
################################################################################

def stanza_is_valid_xml(stanza):
    """ Validates a given stanza to be valid xml"""
    try:
        _ = stanza_as_xml(stanza)
    except Exception as e:
        logger.error('Stanza is not valid xml. {0}'.format(e))
        logger.error(stanza)
        return False

    return True


def is_devicelist_update(stanza):
    return NS_DEVICE_LIST in stanza and not NS_DEVICE_LIST_NOTIFY in stanza


def is_bundle_update(stanza):
    return NS_BUNDLES in stanza


def is_encrypted_message(stanza):
    # TODO: check in NS_OMEMO only
    return 'encrypted' in stanza


def is_xmpp_message(stanza):
    stanza = stanza or ''
    is_valid = all([NS_OMEMO in stanza, 'body' in stanza])
    return is_valid


def is_xmpp_plaintext_message(stanza):
    stanza = stanza or ''
    return 'body' in stanza


################################################################################
# Unwrapping XMPP stanzas
################################################################################

def unpack_bundle_info(stanza):
    logger.info('Unwrapping bundle info.')
    bundle_xml = stanza_as_xml(stanza)

    try:
        sender = bundle_xml.attrib['from'].rsplit('/', 1)[0]
    except KeyError:
        # we assume bundle updates without sender to be own bundles for
        # different devices
        sender = ProfOmemoUser.account

    try:
        items_node = find_node(bundle_xml, 'items', ns='http://jabber.org/protocol/pubsub')
        device_id = items_node.attrib['node'].split(':')[-1]

        bundle_node = find_node(bundle_xml, 'bundle', ns=NS_OMEMO)

        signedPreKeyPublic_node = find_node(bundle_node, 'signedPreKeyPublic', ns=NS_OMEMO)
        signedPreKeyPublic = signedPreKeyPublic_node.text

        signedPreKeyId = int(signedPreKeyPublic_node.attrib['signedPreKeyId'])

        signedPreKeySignature_node = find_node(bundle_node, 'signedPreKeySignature', ns=NS_OMEMO)
        signedPreKeySignature = signedPreKeySignature_node.text

        identityKey_node = find_node(bundle_node, 'identityKey', ns=NS_OMEMO)
        identityKey = identityKey_node.text

        prekeys_node = find_node(bundle_node, 'prekeys', ns=NS_OMEMO)
        prekeys = [(int(n.attrib['preKeyId']), n.text) for n in prekeys_node]

        picked_key_tuple = random.SystemRandom().choice(prekeys)
        preKeyId, preKeyPublic = picked_key_tuple

        if not preKeyId:
            logger.warning('OMEMO PreKey has no id set')
            return

        if not preKeyPublic:
            return
    except StanzaNodeNotFound as e:
        logger.warning('Could not unpack bundle info. {0}'.format(e))
        return

    bundle_dict = {
        'sender': sender,
        'device': device_id,
        'signedPreKeyId': signedPreKeyId,
        'signedPreKeyPublic': b64decode(signedPreKeyPublic),
        'signedPreKeySignature': b64decode(signedPreKeySignature),
        'identityKey': b64decode(identityKey),
        'preKeyId': preKeyId,
        'preKeyPublic': b64decode(preKeyPublic)
    }

    return bundle_dict


def unpack_encrypted_stanza(encrypted_stanza):
    """
    <message id="8d966c20-1690-46eb-b1cd-a7ddcc419fde" to="renevolution@yakshed.org" type="chat" from="testvolution@yakshed.org/conversations">
    <encrypted xmlns="eu.siacs.conversations.axolotl">
        <header sid="1461841909">
            <key rid="1260459496">MwiS5dwDEiEFWjz44O8EezFsoc9bt/o85UIUw4zyXxwX5Fk80dpsvmgaIQVnrk8XTORiGHq2TYRM
                wS1/WWY+zhN9z1fmazuEOgtfRyJSMwohBe7cHe4zeNI3p4R60hEzY3vwaiPCCDQrr01A+BsyvI0V
                EAEYACIgAnkiHmEFyNec2UNZi7wRswx36qUYfWYnHcN3qEUQFDYLe51RMqf+NSj134e5BTAB
            </key>
            <iv>PnZsChVPjwI6jTL6fpkz5Q==</iv>
        </header>
        <payload>5eCvRJz6ASe8YzCyhB6W3JozxHec</payload>
    </encrypted>
    <markable xmlns="urn:xmpp:chat-markers:0"/>
    <store xmlns="urn:xmpp:hints"/></message>

    :param encrypted_stanza:
    :return:
    """

    xml = ET.fromstring(encrypted_stanza)
    if '<forwarded' in encrypted_stanza:
        xml = xml.find('.//{jabber:client}message')

    sender_fulljid = xml.attrib['from']
    sender, resource = sender_fulljid.rsplit('/', 1)

    encrypted_node = xml.find('.//{%s}encrypted' % NS_OMEMO)

    header_node = encrypted_node.find('.//{%s}header' % NS_OMEMO)

    sid = int(header_node.attrib['sid'])

    iv_node = header_node.find('.//{%s}iv' % NS_OMEMO)
    iv = iv_node.text

    payload_node = encrypted_node.find('.//{%s}payload' % NS_OMEMO)
    payload = payload_node.text

    keys = {}
    for node in header_node.iter():
        if node.tag == '{%s}key' % NS_OMEMO:
            keys[int(node.attrib['rid'])] = b64decode(node.text)

    msg_dict = {
        'sender_jid': sender,
        'sender_resource': resource,
        'sid': sid,
        'iv': b64decode(iv),
        'keys': keys,
        'payload': b64decode(payload)
    }

    return msg_dict


def unpack_devicelist_info(stanza):
    xml = stanza_as_xml(stanza)

    try:
        sender_jid = xml.attrib.get('from')
    except AttributeError:
        sender_jid = None

    if sender_jid is None:
        event_node = xml.find('./{%s}event' % 'http://jabber.org/protocol/pubsub#event')
        try:
            sender_jid = event_node.attrib.get('from')
        except AttributeError:
            # device list info is result of a request for our own account
            sender_jid = ProfOmemoUser().account

    item_list = xml.find('.//{%s}list' % NS_OMEMO)
    if item_list is not None:
        device_ids = [int(d.attrib['id']) for d in item_list]
    else:
        device_ids = []

    msg_dict = {'from': sender_jid,
                'devices': device_ids}

    return msg_dict


################################################################################
# Create XMPP stanzas
################################################################################

def create_own_bundle_stanza():
    announce_template = ('<iq from="{from_jid}" type="set" id="{req_id}">'
                         '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                         '<publish node="{bundles_ns}:{device_id}">'
                         '<item>'
                         '<bundle xmlns="{omemo_ns}">'
                         '</bundle>'
                         '</item>'
                         '</publish>'
                         '</pubsub>'
                         '</iq>')

    omemo_state = ProfOmemoState()
    own_bundle = omemo_state.bundle
    own_jid = omemo_state.own_jid
    bundle_msg = announce_template.format(from_jid=own_jid,
                                          req_id=str(uuid.uuid4()),
                                          device_id=omemo_state.own_device_id,
                                          bundles_ns=NS_BUNDLES,
                                          omemo_ns=NS_OMEMO)

    bundle_xml = ET.fromstring(bundle_msg)

    # to be appended to announce_template
    find_str = './/{%s}bundle' % NS_OMEMO
    bundle_node = bundle_xml.find(find_str)
    pre_key_signed_node = ET.SubElement(bundle_node, 'signedPreKeyPublic',
                                        attrib={'signedPreKeyId': str(
                                            own_bundle['signedPreKeyId'])})
    pre_key_signed_node.text = own_bundle.get('signedPreKeyPublic')

    signedPreKeySignature_node = ET.SubElement(bundle_node,
                                               'signedPreKeySignature')
    signedPreKeySignature_node.text = own_bundle.get('signedPreKeySignature')

    identityKey_node = ET.SubElement(bundle_node, 'identityKey')
    identityKey_node.text = own_bundle.get('identityKey')

    prekeys_node = ET.SubElement(bundle_node, 'prekeys')
    for key_id, key in own_bundle.get('prekeys', []):
        key_node = ET.SubElement(prekeys_node, 'preKeyPublic',
                                 attrib={'preKeyId': str(key_id)})
        key_node.text = key

    # reconvert xml to stanza
    bundle_stanza = ET.tostring(bundle_xml, encoding='utf-8', method='html')
    # prof.cons_show(bundle_stanza)

    return bundle_stanza


def create_bundle_request_stanza(account, recipient, deviceid):
    logger.info('Fetching bundle for device id {0} of {1}'.format(deviceid, recipient))

    bundle_req_root = ET.Element('iq')
    bundle_req_root.set('type', 'get')
    bundle_req_root.set('from', account)
    bundle_req_root.set('to', recipient)
    bundle_req_root.set('id', str(uuid.uuid4()))
    pubsub_node = ET.SubElement(bundle_req_root, 'pubsub')
    pubsub_node.set('xmlns', 'http://jabber.org/protocol/pubsub')
    items_node = ET.SubElement(pubsub_node, 'items')
    items_node.set('node', '{0}:{1}'.format(NS_BUNDLES, deviceid))

    stanza = ET.tostring(bundle_req_root, encoding='utf-8', method='html')

    return stanza


def create_encrypted_message(from_jid, to_jid, plaintext, msg_id=None):

    OMEMO_MSG = ('<message to="{to}" from="{from}" id="{id}" type="chat">'
                 '<body>I sent you an OMEMO encrypted message.</body>'
                 '<encrypted xmlns="{omemo_ns}">'
                 '<header sid="{sid}">'
                 '{keys}'
                 '<iv>{iv}</iv>'
                 '</header>'
                 '<payload>{enc_body}</payload>'
                 '</encrypted>'
                 '<markable xmlns="urn:xmpp:chat-markers:0"/>'
                 '<request xmlns="urn:xmpp:receipts"/>'
                 '<store xmlns="urn:xmpp:hints"/>'
                 '</message>')

    omemo_state = ProfOmemoState()
    account = ProfOmemoUser.account
    msg_data = omemo_state.create_msg(account, to_jid, plaintext)

    # build encrypted message from here
    keys_dict = msg_data['keys']

    # key is now a tuple of (key, is_prekey)
    keys_str = ''
    for rid, key_info in keys_dict.items():
        key, is_prekey = key_info
        if is_prekey:
            tpl = '<key prekey="true" rid="{0}">{1}</key>'
        else:
            tpl = '<key rid="{0}">{1}</key>'
        keys_str += tpl.format(rid, b64encode(key))

    msg_dict = {'to': to_jid,
                'from': from_jid,
                'id': msg_id or str(uuid.uuid4()),
                'omemo_ns': NS_OMEMO,
                'sid': msg_data['sid'],
                'keys': keys_str,
                'iv': b64encode(msg_data['iv']),
                'enc_body': b64encode(msg_data['payload'])}

    enc_msg = OMEMO_MSG.format(**msg_dict)

    return enc_msg


def create_devicelist_update_msg(fulljid):
    QUERY_MSG = ('<iq type="set" from="{from}" id="{id}">'
                 '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                 '<publish node="{devicelist_ns}">'
                 '<item id="1">'
                 '<list xmlns="{omemo_ns}">'
                 '{devices}'
                 '</list>'
                 '</item>'
                 '</publish>'
                 '</pubsub>'
                 '</iq>')

    omemo_state = ProfOmemoState()

    own_devices = set(omemo_state.own_devices + [omemo_state.own_device_id])
    device_nodes = ['<device id="{0}"/>'.format(d) for d in own_devices]

    msg_dict = {'from': fulljid,
                'devices': ''.join(device_nodes),
                'id': str(uuid.uuid4()),
                'omemo_ns': NS_OMEMO,
                'devicelist_ns': NS_DEVICE_LIST}

    query_msg = QUERY_MSG.format(**msg_dict)

    return query_msg


def create_devicelist_query_msg(sender, recipient):
    QUERY_MSG = ('<iq type="get" from="{from}" to="{to}" id="{id}">'
                 '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                 '<items node="{device_list_ns}" />'
                 '</pubsub>'
                 '</iq>')

    msg_dict = {
        'from': sender,
        'to': recipient,
        'id': str(uuid.uuid4()),
        'device_list_ns': NS_DEVICE_LIST
        }

    query_msg = QUERY_MSG.format(**msg_dict)

    logger.info('Sending Device List Query: {0}'.format(query_msg))

    return query_msg
