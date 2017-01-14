from db import get_connection
from log import get_plugin_logger

logger = get_plugin_logger()

try:
    from omemo.state import OmemoState
except ImportError:
    logger.error('Could not import OmemoState')
    raise


class ProfOmemoState(object):
    """ ProfOmemoState Singleton """

    __states = {}

    def __new__(cls, *args, **kwargs):
        own_jid = ProfOmemoUser().account
        if not own_jid:
            raise RuntimeError('No User connected.')

        if own_jid not in cls.__states:
            # create the OmemoState for the current user
            connection = get_connection(own_jid)
            new_state = OmemoState(own_jid, connection, own_jid, None)
            cls.__states[own_jid] = new_state

        return cls.__states[own_jid]


class ProfActiveOmemoChats(object):

    __sessions = {}

    @classmethod
    def sessions(cls):
        return cls.__sessions

    @classmethod
    def add(cls, jid, session):
        account = jid.rsplit('/', 1)[0]
        cls.__sessions[account] = session

    @classmethod
    def remove(cls, account):
        try:
            del cls.__sessions[account]
        except KeyError:
            logger.warning('Tried to delete an unknown session.')

    @classmethod
    def get_session(cls, account):
        return cls.__sessions.get(account)

    @classmethod
    def has_session(cls, account):
        return account in cls.__sessions.keys()

    @classmethod
    def reset(cls):
        cls.__sessions = {}


class ProfOmemoUser(object):
    """ ProfOmemoUser Singleton """

    account = None
    fulljid = None

    @classmethod
    def set_user(cls, account, fulljid):
        cls.account = account
        cls.fulljid = fulljid

    @classmethod
    def reset(cls):
        cls.account = None
        cls.fulljid = None
