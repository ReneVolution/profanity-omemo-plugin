import pytest

import profanity_omemo_plugin.xmpp as xmpp
from profanity_omemo_plugin.constants import NS_DEVICE_LIST, NS_OMEMO


def test_unpack_bundle_info():
    pytest.skip('WIP')


def test_unpack_devicelist_update():
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


def test_upack_encrypted_message():
    msg_stanza = (
        '<message id="msg1" to="juliet@capulet.lit" type="chat" from="romeo@montague.lit/profanity">'
            '<encrypted xmlns="{0}">'
                '<header sid="1461841909">'
                    '<key rid="1260459496">dummy</key>'
                    '<iv>PnZsChVPjwI6jTL6fpkz5Q==</iv>'
                    '</header>'
                    '<payload>5eCvRJz6ASe8YzCyhB6W3JozxHec</payload>'
            '</encrypted>'
            '<markable xmlns="urn:xmpp:chat-markers:0"/>'
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