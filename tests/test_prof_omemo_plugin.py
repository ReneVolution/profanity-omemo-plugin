import os
import sys

from mock import MagicMock

here = os.path.abspath(os.path.dirname(__file__))
deploy_root = os.path.join(here, '..', 'deploy')
sys.path.append(deploy_root)

# we need to mock the prof module as it is not available outside profanity
sys.modules['prof'] = MagicMock()
import prof_omemo_plugin as plugin
from profanity_omemo_plugin.constants import NS_OMEMO, NS_DEVICE_LIST


class TestPluginHooks(object):

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
