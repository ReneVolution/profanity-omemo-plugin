# -*- coding: utf-8 -*-

# TODO: Plugin on/off states if a user is connected or not - global -
# TODO: /omemo start/stop handling per user
# TODO: Allow user to prefix OMEMO encrypted/decrypted messages

# This file will be copied to the profanity plugins install location
import prof

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import NS_DEVICE_LIST_NOTIFY
from profanity_omemo_plugin.log import get_plugin_logger
from profanity_omemo_plugin.prof_omemo_state import ProfOmemoState, ProfOmemoUser

logger = get_plugin_logger()


################################################################################
# Convenience methods
################################################################################

def send_stanza(stanza):
    """ Sends a stanza via profanity

    Ensures the stanza is valid XML before sending.
    """

    if xmpp.stanza_is_valid_xml(stanza):
        logger.debug('Sending Stanza: {}'.format(stanza))
        prof.send_stanza(stanza)
        return True

    return False


################################################################################
# OMEMO helper
################################################################################


def _init_omemo():
    account = ProfOmemoUser().account
    if account:
        # subscribe to devicelist updates
        logger.info('Adding Disco Feature {0}.'.format(NS_DEVICE_LIST_NOTIFY))
        # subscribe to device list updates
        prof.disco_add_feature(NS_DEVICE_LIST_NOTIFY)

        logger.debug('Announcing own bundle info.')
        _announce_own_devicelist()  # announce own device list
        _announce_own_bundle()  # announce own bundle

        # we query our own devices to add possible other devices we own
        _query_device_list(account)


def _announce_own_bundle():
    account = ProfOmemoUser().account
    own_bundle_stanza = xmpp.create_own_bundle_stanza(account)
    send_stanza(own_bundle_stanza)


def _start_omemo_session(jid):
    # should be started before the first message is sent.
    logger.debug('Query Devicelist for {0}'.format(jid))
    _query_device_list(jid)
    logger.debug('Query bundle info for {0}'.format(jid))
    _fetch_bundle(jid)


################################################################################
# Stanza handling
################################################################################

def _fetch_bundle(recipient):
    account = ProfOmemoUser().account
    stanza = xmpp.create_bundle_request_stanza(account, recipient)
    send_stanza(stanza)


def _handle_devicelist_update(stanza):
    account = ProfOmemoUser().account
    msg_dict = xmpp.unpack_devicelist_info(stanza)
    sender_jid = msg_dict['from']
    xmpp.update_devicelist(account, sender_jid, msg_dict['devices'])

    add_recipient_to_completer(sender_jid)


def add_recipient_to_completer(recipient):
    logger.info('Adding {} to the completer.'.format(recipient))
    prof.completer_add('/omemo start', [recipient])
    prof.completer_add('/omemo show_devices', [recipient])


def _handle_bundle_update(stanza):
    logger.info('Bundle Information received.')
    omemo_state = ProfOmemoState()
    bundle_info = xmpp.unpack_bundle_info(stanza)

    sender = bundle_info.get('sender')
    device_id = bundle_info.get('device')

    try:
        omemo_state.build_session(sender, device_id, bundle_info)
    except Exception as e:
        msg = 'Could not build session with {0}:{1}. {2}:{3} '
        logger.error(msg.format(sender, device_id, type(e), str(e)))

    logger.info('Session built with user: {0} '.format(sender))


def _announce_own_devicelist():
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_update_msg(fulljid)
    logger.info('Sending Device List Update: {0}'.format(query_msg))
    send_stanza(query_msg)


def _query_device_list(contact_jid):
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_query_msg(fulljid, contact_jid)
    send_stanza(query_msg)


################################################################################
# Sending hooks
################################################################################


def prof_on_message_stanza_send(stanza):
    if xmpp.is_xmpp_message(stanza):
        encrypted_stanza = xmpp.encrypt_stanza(stanza)
        if xmpp.stanza_is_valid_xml(encrypted_stanza):
            return encrypted_stanza

    return None


################################################################################
# Receiving hooks
################################################################################


def prof_on_message_stanza_receive(stanza):
    logger.info('Received Message: {0}'.format(stanza))
    if xmpp.is_devicelist_update(stanza):
        logger.info('Device List update detected.')
        _handle_devicelist_update(stanza)
        return False

    if xmpp.is_encrypted_message(stanza):
        omemo_state = ProfOmemoState()

        try:
            msg_dict = xmpp.unpack_encrypted_stanza(stanza)
            sender = msg_dict['sender_jid']
            resource = msg_dict['sender_resource']

            plain_msg = omemo_state.decrypt_msg(msg_dict)
            logger.info(u'Received Plain Message: {}'.format(plain_msg))
            if plain_msg:
                prefixed_msg = u'[*OMEMO*] {}'.format(plain_msg)
                prof.incoming_message(sender, resource, prefixed_msg)
            return False
        except Exception as e:
            # maybe not OMEMO encrypted, profanity will take care then
            logger.error('Could not decrypt message. {0}'.format(str(e)))
            raise

    return True


def prof_on_iq_stanza_receive(stanza):
    # prof_incoming_message() and return FALSE
    logger.info('Received IQ: {0}'.format(stanza))

    if xmpp.is_bundle_update(stanza):  # bundle information received
        _handle_bundle_update(stanza)
        logger.info('Bundle update detected.')
        return False

    elif xmpp.is_devicelist_update(stanza):
        logger.info('Device List update detected.')
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
    account = ProfOmemoUser().account
    fulljid = ProfOmemoUser().fulljid

    if arg1 == "announce":
        _announce_own_bundle()
    elif arg1 == "start":
        # ensure we are in a chat window
        if arg2:
            prof.send_line('/msg {0}'.format(arg2))

        muc = prof.get_current_muc() or prof.get_current_recipient()
        logger.info('Start OMEMO session with: {0}'.format(muc))
        if muc:
            _start_omemo_session(muc)

    elif arg1 == "account":
        prof.cons_show('Account: {0}'.format(account))
    elif arg1 == "fulljid":
        prof.cons_show('Current JID: {0}'.format(fulljid))
    elif arg1 == "show_devices" and arg2 is not None:
        account = arg2
        omemo_state = ProfOmemoState()
        prof.cons_show('Requesting Devices...')
        devices = omemo_state.device_list_for(account)
        prof.cons_show('Devices: {0}'.format(devices))
        prof.cons_show('{0}: {1}'.format(account, ', '.join(devices)))


################################################################################
# Plugin State Changes
################################################################################


def prof_init(version, status, account_name, fulljid):
    logger.info('prof_init() called')
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

    prof.completer_add("/omemo", ["start", "end", "announce", "account",
                                  "fulljid", "show_devices"])

    # set user and init omemo only if account_name and fulljid provided
    logger.info(account_name)
    logger.info(fulljid)
    if account_name is not None and fulljid is not None:
        ProfOmemoUser.set_user(account_name, fulljid)
        _init_omemo()
    else:
        logger.warning('No User logged in on plugin.prof_init()')


def prof_on_unload():
    logger.debug('prof_on_unload() called')
    ProfOmemoUser.reset()


def prof_on_connect(account_name, fulljid):
    logger.debug('prof_on_connect() called')
    ProfOmemoUser.set_user(account_name, fulljid)
    _init_omemo()


def prof_on_disconnect(account_name, fulljid):
    logger.debug('prof_on_disconnect() called')
    ProfOmemoUser.reset()


def prof_on_shutdown():
    logger.debug('prof_on_shutdown() called')
    ProfOmemoUser.reset()
