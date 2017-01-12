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
from profanity_omemo_plugin.prof_omemo_state import ProfOmemoSessions


class TestPluginHooks(object):

    def teardown_method(self, test_method):
        ProfOmemoSessions.reset()

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

    def test_has_session_decorator_returns_func_result(self):

        @plugin.has_session('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'

        ProfOmemoSessions.add(recipient, 'SOMEMAGICKEY')

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    def test_has_session_decorator_returns_func_result_on_none_session(self):

        @plugin.has_session('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'

        ProfOmemoSessions.add(recipient, None)

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    def test_has_session_decorator_returns_default_if_no_session(self):
        @plugin.has_session('to')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) is None

    def test_has_session_decorator_returns_custom_return_if_no_session(self):
        @plugin.has_session('to', else_return='whatever')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) is 'whatever'

    def test_has_session_decorator_returns_default_on_error(self):
        @plugin.has_session('not_valid_attrib')
        def func(x):
            return x

        recipient = 'juliet@capulet.lit'
        ProfOmemoSessions.add(recipient, 'SOMEMAGICKEY')

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
        @plugin.has_session('to', else_return='session_second')
        def func(x):
            return x

        settings_boolean_get.return_value = True
        recipient = 'juliet@capulet.lit'
        ProfOmemoSessions.add(recipient, 'SOMEMAGICKEY')

        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == stanza

    @patch('prof.settings_boolean_get')
    def test_stacked_decorators_omemo_enabled_priority(self, settings_boolean_get):
        @plugin.omemo_enabled(else_return='enabled_first')
        @plugin.has_session('to', else_return='session_second')
        def func(x):
            return x

        settings_boolean_get.return_value = False
        recipient = 'juliet@capulet.lit'
        stanza = '<message to="{}"></message>'.format(recipient)

        assert func(stanza) == 'enabled_first'
