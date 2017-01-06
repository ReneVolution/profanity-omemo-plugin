# -*- coding: utf-8 -*-

# TODO: Plugin on/off states if a user is connected or not - global -
# TODO: /omemo start/stop handling per user

# This file will be copied to the profanity plugins install location
import prof

import profanity_omemo_plugin as omemo_plugin
from profanity_omemo_plugin.constants import NS_DEVICE_LIST_NOTIFY
from profanity_omemo_plugin.log import get_logger
from profanity_omemo_plugin.omemo import get_omemo_state
from profanity_omemo_plugin.xmpp import (stanza_is_valid_xml,
                                         get_own_bundle_stanza,
                                         get_bundle_request_stanza,
                                         get_devicelist_query_stanza,
                                         create_devicelist_update_msg,
                                         encrypted_from_stanza)

log = omemo_plugin.log.get_logger()

# Global state vars
OMEMO_CURRENT_ACCOUNT = None
OMEMO_CURRENT_FULLJID = None

# Constants


################################################################################
# Convenience methods
################################################################################

def send_stanza(stanza):
    """ Sends a stanza via profanity

    Ensures the stanza is valid XML before sending.
    """

    if stanza_is_valid_xml(stanza):
        prof.log_info('Sending Stanza: {}'.format(stanza))
        prof.send_stanza(stanza)

################################################################################
# OMEMO helper
################################################################################


def _init_omemo():
    account_name, _ = get_current_user()
    if account_name:
        # subscribe to devicelist updates
        prof.log_info('Adding Disco Feature {0}.'.format(NS_DEVICE_LIST_NOTIFY))
        prof.disco_add_feature(NS_DEVICE_LIST_NOTIFY)

        prof.log_info('Announcing own bundle info.')
        _announce_devicelist()
        _announce_bundle()
        query_device_list(account_name)


def _announce_bundle():
    """ announce bundle info

    """
    own_bundle_stanza = get_own_bundle_stanza()
    send_stanza(own_bundle_stanza)


def _start_omemo_session(jid):
    # should be started before the first message is sent.
    prof.log_info('Query Devicelist for {0}'.format(jid))
    query_device_list(jid)
    prof.log_info('Query bundle info for {0}'.format(jid))
    _fetch_bundle(jid)


def get_current_user():
    global OMEMO_CURRENT_ACCOUNT
    global OMEMO_CURRENT_FULLJID
    prof.log_info(('Get current user account. '
                   'Account Name: {0}, '
                   'Full-JID: {0}').format(OMEMO_CURRENT_ACCOUNT,
                                           OMEMO_CURRENT_FULLJID))

    return OMEMO_CURRENT_ACCOUNT, OMEMO_CURRENT_FULLJID


def set_current_user(account_name, fulljid):
    prof.log_info(('Set current user account. '
                   'Account Name: {0}, '
                   'Full-JID: {0}').format(account_name, fulljid))
    global OMEMO_CURRENT_ACCOUNT
    global OMEMO_CURRENT_FULLJID

    OMEMO_CURRENT_ACCOUNT = account_name
    OMEMO_CURRENT_FULLJID = fulljid


def clear_current_user():
    prof.log_info('Clearing current user account.')
    global OMEMO_CURRENT_ACCOUNT
    global OMEMO_CURRENT_FULLJID

    OMEMO_CURRENT_ACCOUNT = None
    OMEMO_CURRENT_FULLJID = None


################################################################################
# Stanza handling
################################################################################

def _fetch_bundle(recipient):

    bundle_request_stanza = get_bundle_request_stanza(recipient)
    send_stanza(bundle_request_stanza)


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
    own_account, _ = get_current_user()
    if not omemo_state or not own_account:
        return

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

    device_ids = [int(d.attrib['id']) for d in list(item_list)]

    if device_ids:
        prof.log_info('Adding Device ID\'s: {0} for {1}.'.format(device_ids, sender_jid))
        if sender_jid == own_account:
            prof.log_info('Adding own devices')
            omemo_state.set_own_devices(device_ids)
        else:
            prof.log_info('Adding recipients devices')
            omemo_state.set_devices(sender_jid, device_ids)

        prof.log_info('Device List update done.')

    add_recipient_to_completer(sender_jid)


def add_recipient_to_completer(recipient):
    prof.log_info('Adding {} to the completer.'.format(recipient))
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


def _announce_devicelist():
    _, fulljid = get_current_user()
    query_msg = create_devicelist_update_msg(fulljid)
    prof.log_info('Sending Device List Update: {0}'.format(query_msg))
    send_stanza(query_msg)


def query_device_list(contact_jid):

    query_msg = get_devicelist_query_stanza(contact_jid)
    send_stanza(query_msg)

################################################################################
# Sending hooks
################################################################################


def prof_on_message_stanza_send(stanza):
    if 'body' in stanza:
        encrypted_stanza = encrypted_from_stanza(stanza)
        prof.log_info(encrypted_stanza)
        if stanza_is_valid_xml(encrypted_stanza):
            return encrypted_stanza

    return None


# def prof_on_presence_stanza_send(stanza):
#     pass


# def prof_on_iq_stanza_send(stanza):
#     pass

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


# def prof_on_presence_stanza_receive(stanza):
#     return True


def prof_on_iq_stanza_receive(stanza):
    # prof_incoming_message() and return FALSE
    prof.log_info('Received IQ: {0}'.format(stanza))

    if NS_BUNDLES in stanza:  # bundle information received
        _handle_bundle_update(stanza)
        prof.log_info('Bundle update detected.')
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

################################################################################
# Plugin State Changes
################################################################################


def prof_init(version, status, account_name, fulljid):

    prof.log_info('prof_init() called')
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

    # set user and init omemo only if account_name and fulljid provided
    prof.log_info(account_name)
    prof.log_info(fulljid)
    if account_name is not None and fulljid is not None:
        set_current_user(account_name, fulljid)
        _init_omemo()
    else:
        prof.log_warning('No User logged in on plugin.prof_init()')


def prof_on_unload():
    prof.log_info('prof_on_unload() called')
    clear_current_user()
    # TODO: Obsolete once a proper singleton is in place
    global OMEMO_CURRENT_STATE
    OMEMO_CURRENT_STATE = None


def prof_on_connect(account_name, fulljid):
    prof.log_info('prof_on_connect() called')
    set_current_user(account_name, fulljid)
    _init_omemo()


def prof_on_disconnect(account_name, fulljid):
    prof.log_info('prof_on_disconnect() called')
    clear_current_user()

    # TODO: Obsolete once a proper singleton is in place
    global OMEMO_CURRENT_STATE
    OMEMO_CURRENT_STATE = None


def prof_on_shutdown():
    prof.log_info('prof_on_shutdown() called')
    clear_current_user()
