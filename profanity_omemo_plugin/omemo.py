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
        current_account = ProfOmemoUser().account
        if not current_account:
            raise RuntimeError('No User connected.')

        if current_account not in cls.__states:
            # create the OmemoState for the current user
            connection = get_connection(current_account)
            new_state = OmemoState(current_account, connection)
            cls.__states[current_account] = new_state

        return cls.__states[current_account]


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

    def __repr__(self):
        return '{0} <{1}>'.format(self.account, self.fulljid)
