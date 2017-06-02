from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os
import sys

from mock import MagicMock, patch

here = os.path.abspath(os.path.dirname(__file__))
deploy_root = os.path.join(here, '..', 'deploy')
sys.path.append(deploy_root)

# we need to mock the prof module as it is not available outside profanity
sys.modules['prof'] = MagicMock()
import prof_omemo_plugin as plugin
from profanity_omemo_plugin.constants import NS_OMEMO, NS_DEVICE_LIST
from profanity_omemo_plugin.prof_omemo_state import ProfActiveOmemoChats, ProfOmemoUser


class TestPluginHooks(object):

    def setup_method(self, test_method):
        account = 'me@there.com'
        fulljid = 'me@there.com/profanity'

        ProfOmemoUser.set_user(account, fulljid)


    def teardown_method(self, test_method):
        ProfActiveOmemoChats.reset()
        ProfOmemoUser.reset()

    def test_ensure_valid_stanza(self):
        assert plugin.send_stanza(None) is False

        simple_stanza = '<iq></iq>'

        assert plugin.send_stanza(simple_stanza) is True

        test_message = (
            '<message from="juliet@capulet.lit" to="romeo@montague.lit" type="headline" id="update_01">'
            '<event xmlns="http://jabber.org/protocol/pubsub#event">'
            '<items node="{0}">'
            '<item>'
            '<list xmlns="{1}">'
            '<device id="12345" />'
            '<device id="4223" />'
            '</list>'
            '</item>'
            '</items>'
            '</event>'
            '</message>'
        ).format(NS_DEVICE_LIST, NS_OMEMO)

        assert plugin.send_stanza(test_message) is True

    def test_prof_on_message_stanza_send_ignores_none(self):
        ret_val = plugin.prof_on_message_stanza_send(None)

        assert ret_val is None

    def test_prof_on_message_stanza_send_rejects_non_omemo_message(self):
        msg = '<message from="me@there.com"><body>Hello World</body></message>'
        ret_val = plugin.prof_on_message_stanza_send(msg)

        assert ret_val is None

    @patch('profanity_omemo_plugin.omemo.state.OmemoState.devices_without_sessions')
    def test_has_session_decorator_returns_func_result(self, devices_mock):

        devices_mock.return_value = []

        @plugin.require_sessions_for_all_devices('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    @patch('profanity_omemo_plugin.omemo.state.OmemoState.devices_without_sessions')
    def test_has_session_decorator_returns_func_result_on_none_session(self, devices_mock):
        devices_mock.return_value = []

        @plugin.require_sessions_for_all_devices('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'

        ProfActiveOmemoChats.add(recipient)

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    @patch('profanity_omemo_plugin.omemo.state.OmemoState.devices_without_sessions')
    def test_has_session_decorator_returns_default_if_no_session(self, devices_mock):
        devices_mock.return_value = [223, 445]

        @plugin.require_sessions_for_all_devices('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) is None

    @patch('profanity_omemo_plugin.omemo.state.OmemoState.devices_without_sessions')
    def test_has_session_decorator_returns_custom_return_if_no_session(self, devices_mock):
        devices_mock.return_value = [4711, 1290]

        @plugin.require_sessions_for_all_devices('to', else_return='whatever')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) is 'whatever'

    def test_has_session_decorator_returns_default_on_error(self):
        @plugin.require_sessions_for_all_devices('not_valid_attrib')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        ProfActiveOmemoChats.add(recipient)

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) is None

    @patch('prof.settings_boolean_get')
    def test_omemo_enabled_decorator_returns_func_if_enabled(self, settings_boolean_get):
        @plugin.omemo_enabled()
        def func(x):
            return x

        settings_boolean_get.return_value = True
        stanza = '<message></message>'

        assert func(stanza) == stanza

    @patch('prof.settings_boolean_get')
    def test_omemo_enabled_decorator_returns_default_if_disabled(self, settings_boolean_get):
        @plugin.omemo_enabled(else_return='magic_default')
        def func(x):
            return x

        settings_boolean_get.return_value = False
        stanza = '<message></message>'

        assert func(stanza) == 'magic_default'

    @patch('prof.settings_boolean_get')
    def test_stacked_decorators(self, settings_boolean_get):
        @plugin.omemo_enabled(else_return='enabled_first')
        @plugin.require_sessions_for_all_devices('to', else_return='session_second')
        def func(x):
            return x

        settings_boolean_get.return_value = True
        recipient = 'juliet@capulet.lit'
        ProfActiveOmemoChats.add(recipient)

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    @patch('prof.settings_boolean_get')
    def test_stacked_decorators_omemo_enabled_priority(self, settings_boolean_get):
        @plugin.omemo_enabled(else_return='enabled_first')
        @plugin.require_sessions_for_all_devices('to', else_return='session_second')
        def func(x):
            return x

        settings_boolean_get.return_value = False
        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == 'enabled_first'
