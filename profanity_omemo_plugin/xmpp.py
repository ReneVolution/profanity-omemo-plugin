import uuid

from constants import NS_OMEMO, NS_DEVICE_LIST, NS_BUNDLES
from omemo import get_omemo_state

try:
    from lxml import etree as ET
except ImportError:
    # fallback to the default ElementTree module
    import xml.etree.ElementTree as ET



def stanza_is_valid_xml(stanza):
    """ Validates a given stanza to be valid xml"""
    try:
        _ = ET.fromstring(stanza)
    except Exception as e:
        prof.log_error('Stanza is not valid xml. {}'.format(e))
        prof.log_error(stanza)
        return False

    return True





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

def get_own_bundle_stanza():
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

    account_name, _ = get_current_user()
    omemo_state = get_omemo_state()
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
    bundle_stanza = ET.tostring(bundle_xml, encoding='utf8', method='html')
    # prof.cons_show(bundle_stanza)

    return bundle_stanza


def get_bundle_request_stanza(recipient):
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

        stanza = ET.tostring(bundle_req_root, encoding='utf8', method='html')
        return stanza

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


def get_devicelist_query_stanza(sender, recipient):
    QUERY_MSG = ('<iq type="get" from="{from}" to="{to}" id="{id}">'
                 '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                 '<items node="{device_list_ns}" />'
                 '</pubsub>'
                 '</iq>')

    msg_dict = {'from': sender,
                'to': recipient,
                'id': str(uuid.uuid4()),
                'device_list_ns': NS_DEVICE_LIST}

    query_msg = QUERY_MSG.format(**msg_dict)

    prof.log_info('Sending Device List Query: {0}'.format(query_msg))
    return query_msg


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

    account = fulljid.rsplit('/', 1)[0]
    omemo_state = get_omemo_state(account)

    # TODO: This looks weird - there could be more than one device id
    device_nodes = ['<device id="{0}"/>'.format(d) for d in [omemo_state.own_device_id]]

    msg_dict = {'from': fulljid,
                'devices': ''.join(device_nodes),
                'id': str(uuid.uuid4()),
                'omemo_ns': NS_OMEMO,
                'devicelist_ns': NS_DEVICE_LIST}

    query_msg = QUERY_MSG.format(**msg_dict)

    return query_msg