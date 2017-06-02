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
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import wraps

import prof

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import (NS_DEVICE_LIST_NOTIFY,
                                              SETTINGS_GROUP,
                                              OMEMO_DEFAULT_ENABLED,
                                              OMEMO_DEFAULT_MESSAGE_CHAR,
                                              PLUGIN_NAME)
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


def show_chat_info(barejid, message):
    prof.chat_show_themed(
        barejid,
        PLUGIN_NAME,
        'info',
        'cyan',
        None,
        message
    )


def show_chat_warning(barejid, message):
    prof.chat_show_themed(
        barejid,
        PLUGIN_NAME,
        'warning',
        'bold_yellow',
        None,
        message
    )


def show_chat_critical(barejid, message):
    prof.chat_show_themed(
        barejid,
        PLUGIN_NAME,
        'critical',
        'bold_red',
        None,
        message
    )


def ensure_unicode_stanza(stanza):
    if isinstance(stanza, (str, bytes)):
        try:
            u_stanza = stanza.decode('utf-8')
            return u_stanza
        except AttributeError:  # Python 3 here
            pass

    return stanza


def _get_omemo_enabled_setting():
    return prof.settings_boolean_get(
        SETTINGS_GROUP, 'enabled', OMEMO_DEFAULT_ENABLED)


def _set_omemo_enabled_setting(enabled):
    msg = 'Plugin enabled: {0}'.format(enabled)
    log.debug(msg)
    prof.cons_show(msg)
    prof.settings_boolean_set(SETTINGS_GROUP, 'enabled', enabled)


def _get_omemo_message_char():
    return prof.settings_string_get(
        SETTINGS_GROUP, 'message_char', OMEMO_DEFAULT_MESSAGE_CHAR)


def _set_omemo_message_char(char):
    msg = 'OMEMO Message Prefix: {0}'.format(char)
    log.debug(msg)
    prof.cons_show(msg)
    prof.settings_string_set(SETTINGS_GROUP, 'message_char', char)


################################################################################
# Decorators
################################################################################

def require_sessions_for_all_devices(attrib, else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(stanza):
            stanza = ensure_unicode_stanza(stanza)

            recipient = xmpp.get_root_attrib(stanza, attrib)
            try:
                contat_jid = recipient.rsplit('/', 1)[0]
            except AttributeError:
                log.error('Recipient not valid.')
                return else_return

            log.info('Checking Sessions for {0}'.format(recipient))
            state = ProfOmemoState()
            uninitialized_devices = state.devices_without_sessions(contat_jid)

            own_jid = ProfOmemoUser.account
            own_uninitialized = state.devices_without_sessions(own_jid)

            uninitialized_devices += own_uninitialized

            if not uninitialized_devices:
                log.info('Recipient {0} has all sessions set up.'.format(recipient))
                return func(stanza)

            _query_device_list(contat_jid)
            _query_device_list(own_jid)
            log.warning('No Session found for user: {0}.'.format(recipient))
            prof.notify('Failed to send last Message.', 5000, 'Profanity Omemo Plugin')
            return else_return

        return func_wrapper
    return wrapper


def omemo_enabled(else_return=None):
    def wrapper(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            log.debug('Check if Plugins is enabled')
            enabled = _get_omemo_enabled_setting()

            if enabled is True:
                log.debug('Plugin is enabled')
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


def _show_no_trust_mgmt_header(jid):
    show_chat_warning(jid, '###############################################')
    show_chat_warning(jid, '#                                             #')
    show_chat_warning(jid, '#                   CAUTION                   #')
    show_chat_warning(jid, '#    This plugin does not support any form    #')
    show_chat_warning(jid, '#             of Trust Management             #')
    show_chat_warning(jid, '#      All Devices are trusted *blindly*      #')
    show_chat_warning(jid, '#                                             #')
    show_chat_warning(jid, '###############################################')


def _start_omemo_session(jid):
    # should be started before the first message is sent.

    # we store the jid in ProfActiveOmemoChats as the user at least intends to
    # use OMEMO encryption. The respecting methods should then not ignore
    # sending OMEMO messages and fail if no session was created then.
    ProfActiveOmemoChats.add(jid)

    # ensure we have no running OTR session
    prof.encryption_reset(jid)

    # Visualize that OMEMO is now running
    prof.chat_set_titlebar_enctext(jid, 'OMEMO')

    message_char = _get_omemo_message_char()
    prof.chat_set_outgoing_char(jid, message_char)

    show_chat_info(jid, 'OMEMO Session started.')
    _show_no_trust_mgmt_header(jid)

    log.info('Query Devicelist for {0}'.format(jid))
    _query_device_list(jid)


def _end_omemo_session(jid):
    ProfActiveOmemoChats.remove(jid)

    # Release OMEMO from titlebar
    prof.chat_unset_titlebar_enctext(jid)

    prof.chat_unset_incoming_char(jid)
    prof.chat_unset_outgoing_char(jid)
    show_chat_info(jid, 'OMEMO Session ended.')


################################################################################
# Stanza handling
################################################################################

def _handle_devicelist_update(stanza):
    own_jid = ProfOmemoUser().account
    omemo_state = ProfOmemoState()
    msg_dict = xmpp.unpack_devicelist_info(stanza)
    sender_jid = msg_dict['from']
    log.info('Received devicelist update from {0}'.format(sender_jid))

    known_devices = omemo_state.device_list_for(sender_jid)
    new_devices = msg_dict['devices']

    added_devices = set(new_devices) - known_devices

    if added_devices:
        device_str = ', '.join([str(d) for d in added_devices])
        msg = '{0} added devices with IDs {1}'.format(sender_jid, device_str)
        show_chat_warning(sender_jid, msg)
        xmpp.update_devicelist(own_jid, sender_jid, new_devices)

    if not omemo_state.own_device_id_published():
        _announce_own_devicelist()

    if sender_jid != own_jid:
        add_recipient_to_completer(sender_jid)


def add_recipient_to_completer(recipient):
    log.info('Adding {} to the completer.'.format(recipient))
    prof.completer_add('/omemo start', [recipient])
    prof.completer_add('/omemo show_devices', [recipient])
    prof.completer_add('/omemo reset_devicelist', [recipient])


def _handle_bundle_update(stanza):
    log.info('Bundle Information received.')
    omemo_state = ProfOmemoState()
    bundle_info = xmpp.unpack_bundle_info(stanza)

    sender = bundle_info.get('sender')
    device_id = bundle_info.get('device')

    try:
        omemo_state.build_session(sender, device_id, bundle_info)
        log.info('Session built with user: {0}:{1}'.format(sender, device_id))
        prof.completer_add('/omemo end', [sender])
    except Exception as e:
        msg_tmpl = 'Could not build session with {0}:{1}. {2}:{3}'
        msg = msg_tmpl.format(sender, device_id, type(e).__name__, str(e))
        log.error(msg)
        return


def _announce_own_devicelist():
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_update_msg(fulljid)
    log.info('Announce own device list.')
    log.info(query_msg)
    send_stanza(query_msg)


def _query_bundle_info_for(recipient, deviceid):
    log.info('Query Bundle for {0}:{1}'.format(recipient, deviceid))
    account = ProfOmemoUser().account
    stanza = xmpp.create_bundle_request_stanza(account, recipient, deviceid)
    send_stanza(stanza)


def _query_device_list(contact_jid):
    log.info('Query Device list for {0}'.format(contact_jid))
    fulljid = ProfOmemoUser().fulljid
    query_msg = xmpp.create_devicelist_query_msg(fulljid, contact_jid)
    send_stanza(query_msg)


################################################################################
# Sending hooks
################################################################################

@omemo_enabled()
@require_sessions_for_all_devices('to')
def prof_on_message_stanza_send(stanza):
    stanza = ensure_unicode_stanza(stanza)

    contact_jid = xmpp.get_recipient(stanza)
    if not ProfActiveOmemoChats.account_is_active(contact_jid):
        log.debug('Chat not activated for {0}'.format(contact_jid))
        return None

    try:
        if xmpp.is_xmpp_plaintext_message(stanza):
            encrypted_stanza = xmpp.encrypt_stanza(stanza)
            if xmpp.stanza_is_valid_xml(encrypted_stanza):
                return encrypted_stanza
    except Exception as e:
        log.exception('Could not encrypt message')

    show_chat_critical(contact_jid, 'Last message was sent unencrypted.')
    return None


def prof_pre_chat_message_send(barejid, message):
    """ Called before a chat message is sent

    :returns: the new message to send, returning None stops the message
              from being sent
    """

    plugin_enabled = _get_omemo_enabled_setting()
    if not plugin_enabled:
        return message

    if not ProfActiveOmemoChats.account_is_active(barejid):
        log.info('Chat not activated for {0}'.format(barejid))
        return message

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
    stanza = ensure_unicode_stanza(stanza)

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
                msg = 'Could not decrypt Messages. {0}: {1}'
                log.error(msg.format(e.__class__.__name__, e.message))
                return False

            if plain_msg is None:
                log.info('Could not decrypt Message')
                return True

            if plain_msg:
                # only mark the message if it was an OMEMO encrypted message
                try:
                    message_char = _get_omemo_message_char()
                    prof.chat_set_incoming_char(sender, message_char)
                    prof.incoming_message(sender, resource, plain_msg)
                finally:
                    prof.chat_unset_incoming_char(sender)
            return False

        except Exception as e:
            # maybe not OMEMO encrypted, profanity will take care then
            log.error('Could not handle encrypted message. {0}'.format(str(e)))

    return True


@omemo_enabled(else_return=True)
def prof_on_iq_stanza_receive(stanza):
    stanza = ensure_unicode_stanza(stanza)
    log.info('Received IQ: {0}'.format(stanza))

    if xmpp.is_bundle_update(stanza):  # bundle information received
        log.info('Bundle update detected.')
        _handle_bundle_update(stanza)
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
                _set_omemo_message_char(arg3)

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

    elif arg1 == 'reset_devicelist' and arg2 is not None:
        contact_jid = arg2
        if contact_jid != ProfOmemoUser.account:
            omemo_state = ProfOmemoState()
            omemo_state.set_devices(contact_jid, [])
            _query_device_list(contact_jid)

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
        '/omemo reset_devicelist'
    ]

    description = 'Plugin to enable OMEMO encryption'
    args = [
        ['on|off', 'Enable/Disable the Profanity OMEMO Plugin'],
        ['start|end <jid>', ('Start an OMEMO based conversation with <jid> '
                             'window or current window.')],
        ['set', 'Set Settings like Message Prefix'],
        ['status', 'Display the current Profanity OMEMO PLugin stauts.'],
        ['account', 'Show current account name'],
        ['reset_devicelist <jid>', 'Manually reset a contacts devicelist.'],
        ['fulljid', 'Show current <full-jid>']
    ]

    examples = []

    # ensure the plugin is not registered if python-omemo is not available
    prof.register_command('/omemo', 1, 3,
                          synopsis, description, args, examples, _parse_args)

    prof.completer_add('/omemo', ['on', 'off', 'status', 'start', 'end', 'set'
                                  'account', 'fulljid', 'show_devices', 'reset_devicelist'])

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
