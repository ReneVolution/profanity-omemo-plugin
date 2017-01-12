import sqlite3

import pytest
from mock import patch

from profanity_omemo_plugin.prof_omemo_state import ProfOmemoUser, \
    ProfOmemoState, ProfOmemoSessions


def get_test_db_connection():
    print "Using In-Memory Database"
    return sqlite3.connect(':memory:', check_same_thread=False)


class TestProfOmemoUtils(object):

    def teardown_method(self, test_method):
        ProfOmemoUser.reset()
        ProfOmemoSessions.reset()

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

    def test_omemo_sessions_is_singleton(self):
        account = 'juliet@capulet.lit'
        session = 'FEKLNWKLNGERKLNGLRKWENGKNWKGRWNKGNWKNG'

        omemo_session = ProfOmemoSessions()
        omemo_session.add(account, session)

        new_omemo_session = ProfOmemoSessions()

        assert omemo_session.sessions() == new_omemo_session.sessions()

    def test_omemo_sessions_has_no_session_for_user(self):
        assert ProfOmemoSessions.has_session('youdontknowme@web.io') is False

    def test_omemo_session_finds_existing_session(self):
        account = 'juliet@capulet.lit'
        session = 'FEKLNWKLNGERKLNGLRKWENGKNWKGRWNKGNWKNG'

        ProfOmemoSessions.add(account, session)

        assert ProfOmemoSessions.has_session(account) is True

    def test_omemo_session_remove_session(self):
        account = 'juliet@capulet.lit'
        session = 'FEKLNWKLNGERKLNGLRKWENGKNWKGRWNKGNWKNG'

        ProfOmemoSessions.add(account, session)

        assert ProfOmemoSessions.has_session(account) is True

        ProfOmemoSessions.remove(account)

        assert ProfOmemoSessions.has_session(account) is False

    def test_omemo_new_session_overwrites_old_session(self):
        jid = 'juliet@capulet.lit/conversations'
        account = 'juliet@capulet.lit'
        session = 'FEKLNWKLNGERKLNGLRKWENGKNWKGRWNKGNWKNG'

        # omemo_sessions = ProfOmemoSessions()
        ProfOmemoSessions.add(jid, session)

        new_session = 'DHEWVFHVWEKBFVWKJCBELJBVEJLWBVJLWBVJWEB'
        ProfOmemoSessions.add(account, new_session)

        assert len(ProfOmemoSessions.sessions()) == 1
        assert ProfOmemoSessions.get_session(account) == new_session

    def test_omemo_reset_prof_omemo_sessions(self):
        jid = 'juliet@capulet.lit/profanity'
        session = 'FEKLNWKLNGERKLNGLRKWENGKNWKGRWNKGNWKNG'

        ProfOmemoSessions.add(jid, session)

        assert len(ProfOmemoSessions.sessions()) == 1

        ProfOmemoSessions.reset()

        assert len(ProfOmemoSessions.sessions()) == 0

    def test_omemo_has_none_session(self):
        account = 'juliet@capulet.lit'
        ProfOmemoSessions.add(account, None)

        assert ProfOmemoSessions.has_session(account) is True
