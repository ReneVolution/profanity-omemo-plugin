import sqlite3

import pytest
from mock import patch

from profanity_omemo_plugin.prof_omemo_state import ProfOmemoUser, \
    ProfOmemoState, ProfActiveOmemoChats


def get_test_db_connection():
    print('Using In-Memory Database')
    return sqlite3.connect(':memory:', check_same_thread=False)


class TestProfOmemoUtils(object):

    def teardown_method(self, test_method):
        ProfOmemoUser.reset()
        ProfActiveOmemoChats.reset()

    def test_prof_omemo_user_is_singleton(self):
        assert ProfOmemoUser().account == ProfOmemoUser().account
        assert ProfOmemoUser().fulljid == ProfOmemoUser().fulljid

    def test_initial_user_is_not_set(self):
        omemo_user = ProfOmemoUser()

        assert omemo_user.account is None
        assert omemo_user.fulljid is None

    def test_set_omemo_user(self):
        account = 'me@there.com'
        fulljid = 'me@there.com/profanity'

        ProfOmemoUser().account is None
        ProfOmemoUser().fulljid is None

        ProfOmemoUser.set_user(account, fulljid)

        ProfOmemoUser().account == account
        ProfOmemoUser().fulljid == fulljid

    def test_reset_omemo_user(self):
        account = 'me@there.com'
        fulljid = 'me@there.com/profanity'

        ProfOmemoUser.set_user(account, fulljid)

        ProfOmemoUser().account == account
        ProfOmemoUser().fulljid == fulljid

        ProfOmemoUser.reset()

        ProfOmemoUser().account is None
        ProfOmemoUser().fulljid is None

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_omemo_state_returns_singleton(self, mockdb):
        mockdb.return_value = get_test_db_connection()
        account = 'me@there.com'
        fulljid = 'me@there.com/profanity'

        ProfOmemoUser.set_user(account, fulljid)

        state = ProfOmemoState()

        new_state = ProfOmemoState()

        assert state == new_state

    @patch('profanity_omemo_plugin.db.get_connection')
    def test_omemo_state_raises_runtime_error_if_not_connected(self, mockdb):
        mockdb.return_value = get_test_db_connection()

        ProfOmemoUser.reset()

        with pytest.raises(RuntimeError):
            _ = ProfOmemoState()

    def test_omemo_acitve_chat_is_singleton(self):
        account = 'juliet@capulet.lit'

        active_chats_instance = ProfActiveOmemoChats
        ProfActiveOmemoChats.add(account)

        new_active_chats_instance = ProfActiveOmemoChats

        assert active_chats_instance._active == new_active_chats_instance._active

    def test_omemo_chat_adds_accounts_uniquely(self):
        account = 'juliet@capulet.lit'
        assert len(ProfActiveOmemoChats._active) == 0

        ProfActiveOmemoChats.add(account)
        assert len(ProfActiveOmemoChats._active) == 1

        ProfActiveOmemoChats.add(account)
        assert len(ProfActiveOmemoChats._active) == 1

    def test_omemo_chat_remove_account(self):
        account = 'juliet@capulet.lit'
        assert len(ProfActiveOmemoChats._active) == 0

        ProfActiveOmemoChats.add(account)
        assert len(ProfActiveOmemoChats._active) == 1

        ProfActiveOmemoChats.remove(account)
        assert len(ProfActiveOmemoChats._active) == 0

    def test_prof_active_chats_finds_active_chats(self):
        account = 'juliet@capulet.lit'
        account2 = 'romeo@montague.lit'

        ProfActiveOmemoChats.add(account)
        ProfActiveOmemoChats.add(account2)

        assert ProfActiveOmemoChats.account_is_active(account) is True
        assert ProfActiveOmemoChats.account_is_active(account2) is True

        ProfActiveOmemoChats.remove(account)
        assert ProfActiveOmemoChats.account_is_active(account) is False

        ProfActiveOmemoChats.remove(account2)
        assert ProfActiveOmemoChats.account_is_active(account2) is False
