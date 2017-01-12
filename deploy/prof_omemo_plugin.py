# -*- coding: utf-8 -*-

# TODO: Plugin on/off states if a user is connected or not - global -
# TODO: /omemo start/stop handling per user
# TODO: Allow user to prefix OMEMO encrypted/decrypted messages

# This file will be copied to the profanity plugins install location
from functools import wraps

import prof

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import NS_DEVICE_LIST_NOTIFY, SETTINGS_GROUP
from profanity_omemo_plugin.log import get_plugin_logger
from profanity_omemo_plugin.prof_omemo_state import (ProfOmemoState,
                                                     ProfOmemoUser,
                                                     ProfOmemoSessions)

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
# Decorators
################################################################################

def has_session(attrib, else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(stanza):
            recipient = xmpp.get_root_attrib(stanza, attrib)
            try:
                account = recipient.rsplit('/', 1)[0]
            except AttributeError:
                logger.error('Recipient nor valid.')
                return else_return

            if ProfOmemoSessions.has_session(account):
                return func(stanza)

            logger.warning('No Session found for user: {0}.'.format(recipient))
            return else_return

        return func_wrapper
    return wrapper


def omemo_enabled(else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            enabled = prof.settings_boolean_get(SETTINGS_GROUP, 'enabled', False)
            if enabled is True:
                return func(*args, **kwargs)

            return else_return

        return func_wrapper
    return wrapper


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

    # we store the jid in ProfOmemoSessions as the user at least intends to use
    # OMEMO encryption. The respecting methods should then not ignore sending
    # OMEMO messages and fail if no session was created then.
    ProfOmemoSessions.add(jid, None)

    logger.debug('Query Devicelist for {0}'.format(jid))
    _query_device_list(jid)
    logger.debug('Query bundle info for {0}'.format(jid))
    _fetch_bundle(jid)


def _end_omemo_session(jid):
    ProfOmemoSessions.remove(jid)


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
        session = omemo_state.build_session(sender, device_id, bundle_info)
        ProfOmemoSessions.add(sender, session)
        prof.completer_add('/omemo end', [sender])
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

@omemo_enabled()
@has_session('to')
def prof_on_message_stanza_send(stanza):
    if xmpp.is_xmpp_plaintext_message(stanza):
        encrypted_stanza = xmpp.encrypt_stanza(stanza)
        if xmpp.stanza_is_valid_xml(encrypted_stanza):
            return encrypted_stanza

    return None


################################################################################
# Receiving hooks
################################################################################

@omemo_enabled(else_return=True)
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


@omemo_enabled(else_return=True)
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
    elif arg1 == "on":
        prof.settings_boolean_set(SETTINGS_GROUP, "enabled", True)
    elif arg1 == "off":
        prof.settings_boolean_set(SETTINGS_GROUP, "enabled", False)
    elif arg1 == "start":
        # ensure we are in a chat window
        jid = prof.get_current_muc() or prof.get_current_recipient()

        if arg2 and arg2 != jid:
            prof.send_line('/msg {0}'.format(arg2))

        logger.info('Start OMEMO session with: {0}'.format(jid))
        if jid:
            _start_omemo_session(jid)

    elif arg1 == "end":
        # ensure we are in a chat window
        jid = arg2 or prof.get_current_muc() or prof.get_current_recipient()
        logger.info('Ending OMEMO session with: {0}'.format(jid))
        if jid:
            _end_omemo_session(jid)

    elif arg1 == "account":
        prof.cons_show('Account: {0}'.format(account))

    elif arg1 == "status":
        enabled = prof.settings_boolean_get(SETTINGS_GROUP, 'enabled', False)
        prof.cons_show('OMEMO PLugin Enabled: {0}'.format(enabled))

    elif arg1 == "fulljid":
        prof.cons_show('Current JID: {0}'.format(fulljid))

    elif arg1 == "show_devices" and arg2 is not None:
        account = arg2
        omemo_state = ProfOmemoState()
        prof.cons_show('Requesting Devices...')
        devices = omemo_state.device_list_for(account)
        prof.cons_show('Devices: {0}'.format(devices))
        prof.cons_show('{0}: {1}'.format(account, ', '.join(devices)))
    else:
        prof.cons_show('Argument {0} not supported.'.format(arg1))


################################################################################
# Plugin State Changes
################################################################################


def prof_init(version, status, account_name, fulljid):
    logger.info('prof_init() called')
    synopsis = [
        "/omemo",
        "/omemo on|off",
        "/omemo status",
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
        ["on|off", "Enable/Disable the Profanity OMEMO Plugin"],
        ["status", "Display the current Profanity OMEMO PLugin stauts."],
        ["account", "Show current account name"],
        ["fulljid", "Show current <full-jid>"]
    ]

    examples = []

    # ensure the plugin is not registered if python-omemo is not available
    prof.register_command("/omemo", 1, 2,
                          synopsis, description, args, examples, _parse_args)

    prof.completer_add("/omemo", ["on", "off", "status", "start", "end", "announce",
                                  "account", "fulljid", "show_devices"])

    # set user and init omemo only if account_name and fulljid provided
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
