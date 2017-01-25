from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import sqlite3

import pytest
from mock import patch

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import NS_DEVICE_LIST, NS_OMEMO
from profanity_omemo_plugin.prof_omemo_state import ProfOmemoUser, \
    ProfOmemoState


def get_test_db_connection():
    print('Using In-Memory Database')
    return sqlite3.connect(':memory:', check_same_thread=False)


class TestUnpackingXMPP(object):

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_unpack_bundle_info(self, mockdb):
        mockdb.return_value = get_test_db_connection()
        pytest.skip('WIP')

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_unpack_devicelist_update(self, mockdb):
        mockdb.return_value = get_test_db_connection()
        test_stanza = (
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

        msg_dict = xmpp.unpack_devicelist_info(test_stanza)
        expected_msg_dict = {'from': 'juliet@capulet.lit',
                             'devices': [12345, 4223]}

        assert msg_dict == expected_msg_dict

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_unpack_devicelist_request_result_for_own_devices(self, mockdb):
        mockdb.return_value = get_test_db_connection()
        test_stanza = ('<iq id="0x011" to="romeo@montague.lit/profanity" type="result">'
                           '<pubsub xmlns="http://jabber.org/protocol/pubsub">'
                               '<items node="{0}">'
                                '<item id="1">'
                                    '<list xmlns="{1}">'
                                        '<device id="1426586702"/>'
                                    '</list>'
                                '</item>'
                               '</items>'
                           '</pubsub>'
                       '</iq>'
        ).format(NS_DEVICE_LIST, NS_OMEMO)

        current_user = 'romeo@montague.lit'
        ProfOmemoUser.set_user(current_user, current_user + '/profanity')

        msg_dict = xmpp.unpack_devicelist_info(test_stanza)
        expected_msg_dict = {'from': current_user,
                             'devices': [1426586702]}

        assert msg_dict == expected_msg_dict

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_upack_encrypted_message(self, mockdb):
        pytest.skip('Skip for now ... needs to be done properly at some point.')
        mockdb.return_value = get_test_db_connection()

        msg_stanza = (
            '<message id="msg1" to="juliet@capulet.lit" type="chat" from="romeo@montague.lit/profanity">'
            '<body>Some default body if encryption fails.</body>'
            '<encrypted xmlns="{0}">'
            '<header sid="1461841909">'
            '<key rid="1260459496">dummy</key>'
            '<iv>PnZsChVPjwI6jTL6fpkz5Q==</iv>'
            '</header>'
            '<payload>5eCvRJz6ASe8YzCyhB6W3JozxHec</payload>'
            '</encrypted>'
            '<markable xmlns="urn:xmpp:chat-markers:0"/>'
            '<request xmlns="urn:xmpp:receipts"/>'
            '<store xmlns="urn:xmpp:hints"/>'
            '</message>'
        ).format(NS_OMEMO)

        msg_dict = xmpp.unpack_encrypted_stanza(msg_stanza)
        expected_msg_dict = {'sender_jid': 'romeo@montague.lit',
                             'sender_resource': 'profanity',
                             'sid': 1461841909,
                             'iv': 'PnZsChVPjwI6jTL6fpkz5Q==',
                             'keys': {1260459496: 'dummy'},
                             'payload': '5eCvRJz6ASe8YzCyhB6W3JozxHec'}

        assert msg_dict == expected_msg_dict

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_encrypt_stanza(self, mockdb):
        pytest.skip('Work in Progress')
        mockdb.return_value = get_test_db_connection()

        current_user = 'romeo@montague.lit'
        ProfOmemoUser.set_user(current_user, current_user + '/profanity')

        recipient = 'juliet@capulet.lit'
        omemo_state = ProfOmemoState()
        omemo_state.set_devices(recipient, [4711, 995746])

        raw_stanza = ('<message id="msg0x001" to="{0}" type="chat">'
                        '<body>Hollo</body>'
                        '<active xmlns="http://jabber.org/protocol/chatstates"/>'
                      '</message>'
                      ).format(recipient)

        encrypted = xmpp.encrypt_stanza(raw_stanza)