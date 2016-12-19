# -*- coding: utf-8 -*-
import logging
import os
import sys
import uuid

import prof

sys.path.append('/Applications/PyCharm.app/Contents/debug-eggs/pycharm-debug.egg')

try:
    import sqlite3
except ImportError:
    prof.log_error('Could not import sqlite3')
    raise

try:
    from lxml import etree as ET
except ImportError:
    # fallback to the default ElementTree module
    import xml.etree.ElementTree as ET

try:
    from omemo.state import OmemoState
except ImportError:
    prof.cons_show('Could not import OmemoState')
    raise


class ProfLogHandler(logging.Handler):

    def __init__(self):
        super(ProfLogHandler, self).__init__()

    def emit(self, record):

        level_fn_map = {
            10: prof.log_debug,  # DEBUG
            20: prof.log_info,  # INFO
            30: prof.log_warning,  # WARNING
            40: prof.log_error  # ERROR
        }

        try:
            msg = u'{0}: {1}'.format(record.name, record.msg)
            level_fn_map[record.levelno](msg)
        except:
            pass

omemo_logger = logging.getLogger('omemo')
omemo_logger.setLevel(logging.DEBUG)
omemo_log_handler = ProfLogHandler()
omemo_logger.addHandler(omemo_log_handler)

""" Plugin to allow to encrypt/decrypt messages using axolotl

Workflow:

- Init
    Create Keypair if not existent
    Create sqlite db if necessary
    Announce own device to support OMEMO

- Receive Messages
    - Get devicelist updates and cache them
    - If a device receives an update  -> check if own device is still announced.
      If not re-announce

    Furthermore, a device MUST announce it’s IdentityKey, a signed PreKey,
    and a list of PreKeys in a separate, per-device PEP node.
    The list SHOULD contain 100 PreKeys, but MUST contain no less than 20.

- Build a Session
    - fetch their bundle

- Sending a Message
    In order to send a chat message, its <body> first has to be encrypted.
    The client MUST use fresh, randomly generated key/IV pairs with AES-128 in
    Galois/Counter Mode (GCM). For each intended recipient device, i.e. both
    own devices as well as devices associated with the contact, this key is
    encrypted using the corresponding long-standing axolotl session.
    Each encrypted payload key is tagged with the recipient device’s ID.
    This is all serialized into a MessageElement,
    which is transmitted in a <message> as follows:


- Sending a key
    The client may wish to transmit keying material to the contact. This
    first has to be generated. The client MUST generate a fresh, randomly
    generated key/IV pair. For each intended recipient device, i.e. both own
    devices as well as devices associated with the contact, this key is
    encrypted using the corresponding long-standing axolotl session.
    Each encrypted payload key is tagged with the recipient device’s ID.
    This is all serialized into a KeyTransportElement,
    omitting the <payload> as follows:

"""
HOME = os.path.expanduser("~")
XDG_DATA_HOME = os.environ.get("XDG_DATA_HOME",
                               os.path.join(HOME, ".local", "share"))

# OMEMO static namespace vars
NS_OMEMO = 'eu.siacs.conversations.axolotl'
NS_DEVICE_LIST = NS_OMEMO + '.devicelist'
NS_DEVICE_LIST_NOTIFY = NS_DEVICE_LIST + '+notify'
NS_BUNDLES = NS_OMEMO + '.bundles'

SETTINGS_GROUP = 'omemo'


################################################################################
# Convenience methods
################################################################################


def db():
    """ Open in memory sqlite db and create a table. """
    db_path = _get_db_path()
    db_root = os.path.dirname(db_path)
    if not os.path.isdir(db_root):
        os.makedirs(db_root)
    prof.log_info('Using database path {}'.format(db_path))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


def _get_local_data_path():
    current_user, _ = get_current_user()
    if not current_user:
        raise RuntimeError('No User Login detected.')

    safe_username = current_user.replace('@', '_at_')

    return os.path.join(XDG_DATA_HOME, 'profanity', 'omemo', safe_username)


def _get_db_path():
    return os.path.join(_get_local_data_path(), 'omemo.db')


def send_stanza(stanza):
    """ Sends a stanza via profanity

    Ensures the stanza is valid XML before sending.
    """

    try:
        _ = ET.fromstring(stanza)
    except Exception as e:
        prof.log_error('Stanza is not valid. {}'.format(e))
        prof.log_error(stanza)
        return

    prof.log_info('Sending Stanza: {}'.format(stanza))
    prof.send_stanza(stanza)


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
            keys[int(node.attrib['rid'])] = node.text

    result = {'sid': sid, 'iv': iv, 'keys': keys, 'payload': payload}
    return result


################################################################################
# OMEMO helper
################################################################################


def get_omemo_state():
    return OmemoState(db())


def get_own_bundle():
    state = get_omemo_state()
    return state.bundle


def _init_omemo():
    account_name, _ = get_current_user()

    # subscribe to devicelist updates
    prof.log_info('Adding Disco Feature {0}.'.format(NS_DEVICE_LIST_NOTIFY))
    prof.disco_add_feature(NS_DEVICE_LIST_NOTIFY)

    prof.log_info('Announcing own bundle info.')
    _announce_devicelist()
    _announce_bundle()
    query_device_list(account_name)


def test_send():

    _announce_bundle()


def _build_bundle_dict(bundle_xml):
    prof.log_info('Unwrapping bundle info.')

    bundle_node = bundle_xml.find('.//{%s}bundle' % NS_OMEMO)

    signedPreKeyPublic_node = bundle_node.find('.//{%s}signedPreKeyPublic' % NS_OMEMO)
    signedPreKeyPublic = signedPreKeyPublic_node.text
    signedPreKeyId = int(signedPreKeyPublic_node.attrib['signedPreKeyId'])

    signedPreKeySignature_node = bundle_node.find('.//{%s}signedPreKeySignature' % NS_OMEMO)
    signedPreKeySignature = signedPreKeySignature_node.text

    identityKey_node = bundle_node.find('.//{%s}identityKey' % NS_OMEMO)
    identityKey = identityKey_node.text

    prekeys_node = bundle_node.find('.//{%s}prekeys' % NS_OMEMO)

    prekeys = [(int(n.attrib['preKeyId']), n.text) for n in prekeys_node]

    result = {
        'signedPreKeyId': signedPreKeyId,
        'signedPreKeyPublic': signedPreKeyPublic,
        'signedPreKeySignature': signedPreKeySignature,
        'identityKey': identityKey,
        'prekeys': prekeys
    }

    return result


def _announce_bundle():
    """ announce bundle info

    """
    # TODO: move it to wrap/unwrap methods
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

    omemo_state = get_omemo_state()
    account_name, _ = get_current_user()
    own_bundle = omemo_state.bundle
    bundle_msg = announce_template.format(from_jid=account_name,
                                          req_id=str(uuid.uuid4()),
                                          device_id=omemo_state.own_device_id,
                                          bundles_ns=NS_BUNDLES,
                                          omemo_ns=NS_OMEMO)

    bundle_xml = ET.fromstring(bundle_msg)

    # to be appended to announce_template
    find_str = './/{%s}bundle' % NS_OMEMO
    bundle_node = bundle_xml.find(find_str)
    pre_key_signed_node = ET.SubElement(bundle_node, 'signedPreKeyPublic',
                                        attrib={'signedPreKeyId': str(own_bundle['signedPreKeyId'])})
    pre_key_signed_node.text = own_bundle.get('signedPreKeyPublic')

    signedPreKeySignature_node = ET.SubElement(bundle_node,
                                               'signedPreKeySignature')
    signedPreKeySignature_node.text = own_bundle.get('signedPreKeySignature')

    identityKey_node = ET.SubElement(bundle_node, 'identityKey')
    identityKey_node.text = own_bundle.get('identityKey')

    prekeys_node = ET.SubElement(bundle_node, 'prekeys')
    for key_id, key in own_bundle.get('prekeys',[]):
        key_node = ET.SubElement(prekeys_node, 'preKeyPublic',
                                 attrib={'preKeyId': str(key_id)})
        key_node.text = key

    # reconvert xml to stanza
    bundle_stanza = ET.tostring(bundle_xml, encoding='utf8', method='xml')
    # prof.cons_show(bundle_stanza)

    send_stanza(bundle_stanza)


def _start_omemo_session(jid):
    # should be started before the first message is sent.
    prof.log_info('Query Devicelist for {0}'.format(jid))
    query_device_list(jid)
    prof.log_info('Query bundle info for {0}'.format(jid))
    _fetch_bundle(jid)


def get_current_user():
    account = prof.settings_get_string(SETTINGS_GROUP, 'account', None)
    fulljid = prof.settings_get_string(SETTINGS_GROUP, 'fulljid', None)

    return account, fulljid


def set_current_user(account_name, fulljid):
    prof.settings_string_set(SETTINGS_GROUP, 'account', account_name)
    prof.settings_string_set(SETTINGS_GROUP, 'fulljid', fulljid)


def clear_current_user():
    prof.settings_string_set(SETTINGS_GROUP, 'account', None)
    prof.settings_string_set(SETTINGS_GROUP, 'fulljid', None)


################################################################################
# Error Handling
################################################################################


class NoOmemoMessage(Exception):
    pass


class UnhandledOmemoMessage(Exception):
    pass

################################################################################
# Stanza handling
################################################################################


def _fetch_bundle(recipient):
    omemo_state = get_omemo_state()
    account_name, _ = get_current_user()
    recipient_devices = omemo_state.device_list_for(recipient)
    prof.log_info('Fetching bundle for devices {0} of {1}'.format(recipient_devices, recipient))

    for device_id in recipient_devices:
        bundle_req_root = ET.Element('iq')
        bundle_req_root.set('type', 'get')
        bundle_req_root.set('from', account_name)
        bundle_req_root.set('to', recipient)
        bundle_req_root.set('id', str(uuid.uuid4()))
        pubsub_node = ET.SubElement(bundle_req_root, 'pubsub')
        pubsub_node.set('xmlns', 'http://jabber.org/protocol/pubsub')
        items_node = ET.SubElement(pubsub_node, 'items')
        items_node.set('node', '{0}:{1}'.format(NS_BUNDLES, device_id))

        stanza = ET.tostring(bundle_req_root, encoding='utf8', method='xml')
        send_stanza(stanza)


def _handle_devicelist_update(stanza):
    """
    <message from='juliet@capulet.lit'
        to='romeo@montague.lit'
        type='headline'
        id='update_01'>
        <event xmlns='http://jabber.org/protocol/pubsub#event'>
            <items node='urn:xmpp:omemo:0:devicelist'>
            <item>
                <list xmlns='urn:xmpp:omemo:0'>
                <device id='12345' />
                <device id='4223' />
                </list>
            </item>
            </items>
        </event>
    </message>



    NS_DEVICELIST
    <message to="renevolution@yakshed.org/profanity"
           type="headline" from="bascht@yakshed.org"><event
           xmlns="http://jabber.org/protocol/pubsub#event"><items
           node="eu.siacs.conversations.axolotl.devicelist"><item
           id="1"><list
           xmlns="eu.siacs.conversations.axolotl"><device
           id="259621345"/><device
           id="584672103"/></list></item></items></event></message>

    """
    omemo_state = get_omemo_state()
    xml = ET.fromstring(stanza)

    try:
        sender_jid = xml.attrib.get('from')
    except AttributeError:
        sender_jid = None

    if sender_jid is None:
        event_node = xml.find('./{%s}event' % 'http://jabber.org/protocol/pubsub#event')
        try:
            sender_jid = event_node.attrib.get('from')
        except AttributeError:
            prof.log_error('Could not find Sender in stanza: {0}'.format(stanza))
            return

    item_list = xml.find('.//{%s}list' % NS_OMEMO)
    if item_list is None or len(item_list) <= 0:
        prof.log_error('pubsub node not found.')
        prof.log_error(stanza)
        return

    device_ids = [d.attrib['id'] for d in list(item_list)]

    if device_ids:
        prof.log_info('Adding Device ID\'s: {0} for {1}.'.format(device_ids,
                                                                 sender_jid))

        omemo_state.add_devices(sender_jid, device_ids)

        prof.log_info('Device List update done.')

    add_recipient_to_completer(sender_jid)


def add_recipient_to_completer(recipient):
    prof.completer_add('/omemo start', [recipient])
    prof.completer_add('/omemo show_devices', [recipient])


def _handle_bundle_update(stanza):
    prof.log_info('Bundle Information received.')
    omemo_state = get_omemo_state()
    bundle_xml = ET.fromstring(stanza)
    bundle_info = _build_bundle_dict(bundle_xml)
    sender = bundle_xml.attrib['from'].rsplit('/', 1)[0]

    items_node = bundle_xml.find(
        './/{%s}items' % 'http://jabber.org/protocol/pubsub')
    device_id = items_node.attrib['node'].split(':')[-1]
    try:
        omemo_state.build_session(sender, device_id, bundle_info)
    except Exception as e:
        msg = 'Could not build session with {0}:{1}. {2}:{3} '
        prof.log_error(msg.format(sender, device_id, type(e), str(e)))

    prof.log_info('Session built with user: {0} '.format(sender))


def _handle_omemo_message(encrypted_node):
    pass


def _announce_devicelist():

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

    omemo_state = get_omemo_state()
    _, fulljid = get_current_user()
    # TODO: This looks weird - there could be more than one device id
    device_nodes = ['<device id="{0}"/>'.format(d) for d in [omemo_state.own_device_id]]

    msg_dict = {'from': fulljid,
                'devices': ''.join(device_nodes),
                'id': str(uuid.uuid4()),
                'omemo_ns': NS_OMEMO,
                'devicelist_ns': NS_DEVICE_LIST}

    query_msg = QUERY_MSG.format(**msg_dict)

    prof.log_info('Sending Device List Update: {0}'.format(query_msg))
    send_stanza(query_msg)


def query_device_list(contact_jid):
    prof.log_info('Query Device List for {0}'.format(contact_jid))

    QUERY_MSG = ('<iq type="get" from="{from}" to="{to}" id="{id}">'
                 '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                 '<items node="{device_list_ns}" />'
                 '</pubsub>'
                 '</iq>')

    _, fulljid = get_current_user()
    msg_dict = {'from': fulljid,
                'to': contact_jid,
                'id': str(uuid.uuid4()),
                'device_list_ns': NS_DEVICE_LIST}

    query_msg = QUERY_MSG.format(**msg_dict)

    prof.log_info('Sending Device List Query: {0}'.format(query_msg))
    send_stanza(query_msg)


def encrypted_from_stanza(stanza):
    _, fulljid = get_current_user()
    msg_xml = ET.fromstring(stanza)
    jid = msg_xml.attrib['to']
    raw_jid = jid.rsplit('/', 1)[0]

    body_node = msg_xml.find('.//body')
    plaintext = body_node.text

    return encrypted(fulljid, raw_jid, plaintext)


def encrypted(from_jid, to_jid, plaintext):

    OMEMO_MSG = ('<message to="{to}" from="{from}" id="{id}" type="chat">'
                 '<encrypted xmlns="{omemo_ns}">'
                 '<header sid="{sid}">'
                 '{keys}'
                 '<iv>{iv}</iv>'
                 '</header>'
                 '<payload>{enc_body}</payload>'
                 '</encrypted>'
                 '<store xmlns="urn:xmpp:hints"/>'
                 '</message>')

    omemo_state = get_omemo_state()
    msg_dict = omemo_state.create_msg(from_jid, to_jid, plaintext)

    # build encrypted message from here
    keys_tpl = '<key rid="{0}">{1}</key>'
    keys_dict = msg_dict['keys']
    keys_str = ''.join([keys_tpl.format(rid, key) for rid, key in keys_dict.iteritems()])

    msg_dict = {'to': to_jid,
                'from': from_jid,
                'id': str(uuid.uuid4()),
                'omemo_ns': NS_OMEMO,
                'sid': msg_dict['sid'],
                'keys': keys_str,
                'iv': msg_dict['iv'],
                'enc_body': msg_dict['payload']}

    enc_msg = OMEMO_MSG.format(**msg_dict)

    return enc_msg


################################################################################
# Sending hooks
################################################################################


def prof_on_message_stanza_send(stanza):
    if 'body' in stanza:
        encrypted_stanza = encrypted_from_stanza(stanza)
        prof.log_info(encrypted_stanza)
        return encrypted_stanza

    return None


def prof_on_presence_stanza_send(stanza):
    pass


def prof_on_iq_stanza_send(stanza):
    pass

################################################################################
# Receiving hooks
################################################################################


def prof_on_message_stanza_receive(stanza):
    """ <message to="renevolution@yakshed.org/profanity" type="headline"
           from="bascht@yakshed.org"><event
           xmlns="http://jabber.org/protocol/pubsub#event"><items
           node="eu.siacs.conversations.axolotl.devicelist"><item id="1"><list
           xmlns="eu.siacs.conversations.axolotl"><device id="259621345"/><device
           id="584672103"/></list></item></items></event></message> """

    prof.log_info('Received Message: {0}'.format(stanza))
    if NS_DEVICE_LIST in stanza:
        prof.log_info('Device List update detected.')
        _handle_devicelist_update(stanza)
        return False

    if 'encrypted' in stanza:
        # TODO: check in NS_OMEMO only
        omemo_state = get_omemo_state()
        xml = ET.fromstring(stanza)
        sender_fulljid = xml.attrib['from']
        sender, resource = sender_fulljid.rsplit('/', 1)
        try:
            msg_dict = unpack_encrypted_stanza(stanza)
            msg_dict['sender_jid'] = sender

            plain_msg = omemo_state.decrypt_msg(msg_dict)
            prof.log_info('Received Plain Message: {}'.format(plain_msg))
            if plain_msg:
                prefixed_msg = '[*OMEMO*] {}'.format(plain_msg)
                prof.incoming_message(sender, resource, prefixed_msg)
            return False
        except Exception as e:
            # maybe not OMEMO encrypted, profanity will take care then
            prof.log_error('Could not decrypt message.')
            raise

    return True


def prof_on_presence_stanza_receive(stanza):
    # prof_incoming_message() and return FALSE
    # prof.log_info(stanza)
    return True


def prof_on_iq_stanza_receive(stanza):
    # prof_incoming_message() and return FALSE
    prof.log_info('Received IQ: {0}'.format(stanza))

    if NS_BUNDLES in stanza:  # bundle information received
        prof.log_info('Bundle update detected.')
        _handle_bundle_update(stanza)
        return False

    elif NS_DEVICE_LIST in stanza and not NS_DEVICE_LIST_NOTIFY in stanza:
        # TODO: find a better way to check for devicelist updates
        prof.log_info('Device List update detected.')
        _handle_devicelist_update(stanza)
        return False

    return True

################################################################################
# Plugin Entry Point
################################################################################


def _parse_args(arg1=None, arg2=None):
    """ Parse arguments given in command window

    arg1: start || end
    arg2: muc || jid (optional)

    Starts or ends an encrypted chat session

    """
    account_name, fulljid = get_current_user()

    if arg1 == "announce":
        _announce_bundle()
    elif arg1 == "start" :
        # ensure we are in a chat window
        if arg2:
            prof.send_line('/msg {0}'.format(arg2))

        muc = prof.get_current_muc() or prof.get_current_recipient()
        prof.log_info('Start OMEMO session with: {0}'.format(muc))
        if muc:
            # prof.win_show(win_name, 'Starting OMEMO Session')
            _start_omemo_session(muc)

    elif arg1 == "account":
        prof.cons_show('Account: {0}'.format(account_name))
    elif arg1 == "fulljid":
        prof.cons_show('Current JID: {0}'.format(fulljid))
    elif arg1 == "show_devices" and arg2 is not None:
        omemo_state = get_omemo_state()
        prof.cons_show('Requesting Devices...')
        devices = omemo_state.device_list_for(arg2)
        prof.cons_show('Devices: {0}'.format(devices))
        prof.cons_show('{0}: {1}'.format(arg2, ', '.join(devices)))
    elif arg1 == "test":
        test_send()

################################################################################
# Plugin State Changes
################################################################################


def prof_init(version, status, account_name, fulljid):

    synopsis = [
        "/omemo",
        "/omemo start|end [jid]",
        "/omemo announce",
        "/omemo account",
        "/omemo fulljid",
        "/omemo show_devices"
    ]

    description = "Plugin to enable OMEMO encryption"
    args = [
        ["start|end <jid>", ("Start an OMEMO based conversation with <jid> "
                             "window or current window.")],
        ["account", "Show current account name"],
        ["fulljid", "Show current <full-jid>"]
    ]

    examples = []

    # ensure the plugin is not registered if python-omemo is not available
    prof.register_command("/omemo", 1, 2,
                          synopsis, description, args, examples, _parse_args)

    prof.completer_add("/omemo", ["start", "end", "announce", "account", "fulljid", "show_devices"])

    if account_name and fulljid:
        set_current_user(account_name, fulljid)
        _init_omemo()


def prof_on_shutdown():
    clear_current_user()


def prof_on_unload():
    clear_current_user()


def prof_on_connect(account_name, fulljid):
    prof.log_info('Initializing Profanity OMEMO Plugin...')
    set_current_user(account_name, fulljid)
    _init_omemo()


def prof_on_disconnect(account_name, fulljid):
    clear_current_user()

