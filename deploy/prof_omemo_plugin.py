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

# This file will be copied to the profanity plugins install location
from functools import wraps

import prof

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import (NS_DEVICE_LIST_NOTIFY,
                                              SETTINGS_GROUP,
                                              OMEMO_DEFAULT_ENABLED,
                                              OMEMO_DEFAULT_MESSAGE_PREFIX)
from profanity_omemo_plugin.log import get_plugin_logger
from profanity_omemo_plugin.prof_omemo_state import (ProfOmemoState,
                                                     ProfOmemoUser,
                                                     ProfActiveOmemoChats)

log = get_plugin_logger(__name__)


################################################################################
# Convenience methods
################################################################################

def send_stanza(stanza):
    """ Sends a stanza via profanity

    Ensures the stanza is valid XML before sending.
    """

    if xmpp.stanza_is_valid_xml(stanza):
        log.debug('Sending Stanza: {}'.format(stanza))
        prof.send_stanza(stanza)
        return True

    return False


def _get_omemo_enabled_setting():
    return prof.settings_boolean_get(
        SETTINGS_GROUP, 'enabled', OMEMO_DEFAULT_ENABLED)


def _set_omemo_enabled_setting(enabled):
    msg = 'Plugin enabled: {0}'.format(enabled)
    log.debug(msg)
    prof.cons_show(msg)
    prof.settings_boolean_set(SETTINGS_GROUP, 'enabled', enabled)


def _get_omemo_decrypted_message_prefix():
    return prof.settings_string_get(
        SETTINGS_GROUP, 'message_prefix', OMEMO_DEFAULT_MESSAGE_PREFIX)


def _set_omemo_decrypted_message_prefix(prefix):
    msg = 'OMEMO Message Prefix: {0}'.format(prefix)
    log.debug(msg)
    prof.cons_show(msg)
    prof.settings_string_set(SETTINGS_GROUP, 'message_prefix', prefix)


################################################################################
# Decorators
################################################################################

def require_sessions_for_all_devices(attrib, else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(stanza):
            recipient = xmpp.get_root_attrib(stanza, attrib)
            try:
                contat_jid = recipient.rsplit('/', 1)[0]
            except AttributeError:
                log.error('Recipient not valid.')
                return else_return

            log.info('Checking Sessions for {0}'.format(recipient))
            state = ProfOmemoState()
            uninitialized_devices = state.devices_without_sessions(contat_jid)
            own_uninitialized = state.devices_without_sessions(ProfOmemoUser.account)

            uninitialized_devices += own_uninitialized

            if not uninitialized_devices:
                log.info('Recipient {0} has all sessions set up.'.format(recipient))
                return func(stanza)

            _query_device_list(contat_jid)
            log.warning('No Session found for user: {0}.'.format(recipient))
            prof.notify('Failed to send last Message.', 5000, 'Profanity Omemo Plugin')
            return else_return

        return func_wrapper
    return wrapper


def omemo_enabled(else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            log.info('Check if Plugins is enabled')
            enabled = _get_omemo_enabled_setting()

            if enabled is True:
                log.info('Plugin is enabled')
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
        log.info('Adding Disco Feature {0}.'.format(NS_DEVICE_LIST_NOTIFY))
        # subscribe to device list updates
        prof.disco_add_feature(NS_DEVICE_LIST_NOTIFY)

        log.debug('Announcing own bundle info.')
        _announce_own_devicelist()  # announce own device list
        _announce_own_bundle()  # announce own bundle

        # we query our own devices to add possible other devices we own
        _query_device_list(account)


def _announce_own_bundle():
    own_bundle_stanza = xmpp.create_own_bundle_stanza()
    send_stanza(own_bundle_stanza)


def _start_omemo_session(jid):
    # should be started before the first message is sent.

    # we store the jid in ProfActiveOmemoChats as the user at least intends to
    # use OMEMO encryption. The respecting methods should then not ignore
    # sending OMEMO messages and fail if no session was created then.
    ProfActiveOmemoChats.add(jid)

    log.debug('Query Devicelist for {0}'.format(jid))
    _query_device_list(jid)


def _end_omemo_session(jid):
    ProfActiveOmemoChats.remove(jid)


################################################################################
# Stanza handling
################################################################################

def _handle_devicelist_update(stanza):
    account = ProfOmemoUser().account
    msg_dict = xmpp.unpack_devicelist_info(stanza)
    sender_jid = msg_dict['from']
    xmpp.update_devicelist(account, sender_jid, msg_dict['devices'])

    add_recipient_to_completer(sender_jid)


def add_recipient_to_completer(recipient):
    log.info('Adding {} to the completer.'.format(recipient))
    prof.completer_add('/omemo start', [recipient])
    prof.completer_add('/omemo show_devices', [recipient])


def _handle_bundle_update(stanza):
    log.info('Bundle Information received.')
    omemo_state = ProfOmemoState()
    bundle_info = xmpp.unpack_bundle_info(stanza)

    sender = bundle_info.get('sender')
    device_id = bundle_info.get('device')

    try:
        omemo_state.build_session(sender, device_id, bundle_info)
        prof.completer_add('/omemo end', [sender])
    except Exception as e:
        msg_tmpl = 'Could not build session with {0}:{1}. {2}:{3}'
        msg = msg_tmpl.format(sender, device_id, e.__class__.__name__, str(e))
        log.error(msg)
        return

    log.info('Session built with user: {0} '.format(sender))


def _announce_own_devicelist():
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_update_msg(fulljid)
    log.info('Announce own device list.')
    send_stanza(query_msg)


def _query_bundle_info_for(recipient, deviceid):
    log.info('Query Bundle for {0}:{1}'.format(recipient, deviceid))
    account = ProfOmemoUser().account
    stanza = xmpp.create_bundle_request_stanza(account, recipient, deviceid)
    send_stanza(stanza)


def _query_device_list(contact_jid):
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_query_msg(fulljid, contact_jid)
    send_stanza(query_msg)


################################################################################
# Sending hooks
################################################################################

@omemo_enabled()
@require_sessions_for_all_devices('to')
def prof_on_message_stanza_send(stanza):
    # TODO: Should we ensure all devices have sessions before we encrypt???
    contact_jid = xmpp.get_recipient(stanza)
    if not ProfActiveOmemoChats.account_is_active(contact_jid):
        prof.log_info('Chat not activated for {0}'.format(contact_jid))
        return None

    if xmpp.is_xmpp_plaintext_message(stanza):
        encrypted_stanza = xmpp.encrypt_stanza(stanza)
        if xmpp.stanza_is_valid_xml(encrypted_stanza):
            return encrypted_stanza

    return None


@omemo_enabled()
def prof_pre_chat_message_send(barejid, message):
    """ Called before a chat message is sent

    :returns: the new message to send, or None to preserve the original message
    """

    if not ProfActiveOmemoChats.account_is_active(barejid):
        prof.log_info('Chat not activated for {0}'.format(barejid))
        return None

    omemo_state = ProfOmemoState()
    uninitialzed_devices = omemo_state.devices_without_sessions(barejid)

    if uninitialzed_devices:
        d_str = ', '.join([str(d) for d in uninitialzed_devices])
        msg = 'Requesting bundles for missing devices {0}'.format(d_str)

        log.info(msg)
        prof.notify(msg, 5000, 'Profanity Omemo Plugin')

        for device in uninitialzed_devices:
            _query_bundle_info_for(barejid, device)

    own_jid = ProfOmemoUser.account
    own_uninitialized = omemo_state.devices_without_sessions(own_jid)

    if own_uninitialized:
        d_str = ', '.join([str(d) for d in own_uninitialized])
        msg = 'Requesting own bundles for missing devices {0}'.format(d_str)

        log.info(msg)
        prof.notify(msg, 5000, 'Profanity Omemo Plugin')

        for device in own_uninitialized:
            _query_bundle_info_for(own_jid, device)

    return message


################################################################################
# Receiving hooks
################################################################################

@omemo_enabled(else_return=True)
def prof_on_message_stanza_receive(stanza):
    log.info('Received Message: {0}'.format(stanza))
    if xmpp.is_devicelist_update(stanza):
        log.info('Device List update detected.')
        _handle_devicelist_update(stanza)
        return False

    if xmpp.is_encrypted_message(stanza):
        log.info('Received OMEMO encrypted message.')
        omemo_state = ProfOmemoState()

        try:
            msg_dict = xmpp.unpack_encrypted_stanza(stanza)
            sender = msg_dict['sender_jid']
            resource = msg_dict['sender_resource']

            try:
                plain_msg = omemo_state.decrypt_msg(msg_dict)
            except Exception as e:
                msg = u'Could not decrypt Messages. {0}: {1}'
                log.error(msg.format(e.__class__.__name__, str(e)))
                return False

            if plain_msg is None:
                log.info('Could not decrypt Message')
                return True

            if plain_msg:
                prefix = _get_omemo_decrypted_message_prefix()
                log.info(u'Appending Message Prefix {0}'.format(prefix))
                prefixed_msg = u'{0} {1}'.format(prefix, plain_msg)
                prof.incoming_message(sender, resource, prefixed_msg)
            return False

        except Exception as e:
            # maybe not OMEMO encrypted, profanity will take care then
            log.error('Could not decrypt message. {0}'.format(str(e)))

    return True


@omemo_enabled(else_return=True)
def prof_on_iq_stanza_receive(stanza):
    # prof_incoming_message() and return FALSE
    log.info('Received IQ: {0}'.format(stanza))

    if xmpp.is_bundle_update(stanza):  # bundle information received
        _handle_bundle_update(stanza)
        log.info('Bundle update detected.')
        return False

    elif xmpp.is_devicelist_update(stanza):
        log.info('Device List update detected.')
        _handle_devicelist_update(stanza)
        return False

    return True


################################################################################
# Plugin Entry Point
################################################################################


def _parse_args(arg1=None, arg2=None, arg3=None):
    """ Parse arguments given in command window

    arg1: start || end
    arg2: muc || jid (optional)

    Starts or ends an encrypted chat session

    """
    account = ProfOmemoUser().account
    fulljid = ProfOmemoUser().fulljid

    if arg1 == 'on':
        _set_omemo_enabled_setting(True)

    elif arg1 == 'off':
        _set_omemo_enabled_setting(False)

    elif arg1 == 'start':
        # ensure we are in a chat window

        current_recipient = prof.get_current_recipient()

        if not current_recipient and arg2 != current_recipient:
            log.info('Opening Chat Window for {0}'.format(arg2))
            prof.send_line('/msg {0}'.format(arg2))

        recipient = arg2 or current_recipient
        if recipient:
            log.info('Start OMEMO session with: {0}'.format(recipient))
            _start_omemo_session(recipient)

    elif arg1 == 'end':
        # ensure we are in a chat window
        jid = arg2 or prof.get_current_muc() or prof.get_current_recipient()
        log.info('Ending OMEMO session with: {0}'.format(jid))
        if jid:
            _end_omemo_session(jid)

    elif arg1 == 'set':
        if arg2 == 'message_prefix':
            if arg3 is not None:
                _set_omemo_decrypted_message_prefix(arg3)

    elif arg1 == 'account':
        prof.cons_show('Account: {0}'.format(account))

    elif arg1 == 'status':
        enabled = _get_omemo_enabled_setting()
        prof.cons_show('OMEMO PLugin Enabled: {0}'.format(enabled))

    elif arg1 == 'fulljid':
        prof.cons_show('Current JID: {0}'.format(fulljid))

    elif arg1 == 'show_devices' and arg2 is not None:
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
    log.info('prof_init() called')
    synopsis = [
        '/omemo',
        '/omemo on|off',
        '/omemo start|end [jid]',
        '/omemo set'
        '/omemo status',
        '/omemo account',
        '/omemo fulljid',
        '/omemo show_devices'
    ]

    description = 'Plugin to enable OMEMO encryption'
    args = [
        ['on|off', 'Enable/Disable the Profanity OMEMO Plugin'],
        ['start|end <jid>', ('Start an OMEMO based conversation with <jid> '
                             'window or current window.')],
        ['set', 'Set Settings like Message Prefix'],
        ['status', 'Display the current Profanity OMEMO PLugin stauts.'],
        ['account', 'Show current account name'],
        ['fulljid', 'Show current <full-jid>']
    ]

    examples = []

    # ensure the plugin is not registered if python-omemo is not available
    prof.register_command('/omemo', 1, 3,
                          synopsis, description, args, examples, _parse_args)

    prof.completer_add('/omemo', ['on', 'off', 'status', 'start', 'end', 'set'
                                  'account', 'fulljid', 'show_devices'])

    prof.completer_add('/omemo set', ['message_prefix'])

    # set user and init omemo only if account_name and fulljid provided
    if account_name is not None and fulljid is not None:
        ProfOmemoUser.set_user(account_name, fulljid)
        _init_omemo()
    else:
        log.warning('No User logged in on plugin.prof_init()')


def prof_on_unload():
    log.debug('prof_on_unload() called')
    ProfOmemoUser.reset()


def prof_on_connect(account_name, fulljid):
    log.debug('prof_on_connect() called')
    ProfOmemoUser.set_user(account_name, fulljid)
    _init_omemo()


def prof_on_disconnect(account_name, fulljid):
    log.debug('prof_on_disconnect() called')
    ProfOmemoUser.reset()


def prof_on_shutdown():
    log.debug('prof_on_shutdown() called')
    ProfOmemoUser.reset()
