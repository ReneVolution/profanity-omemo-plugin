try:
    from omemo.state import OmemoState
except ImportError:
    prof.log_error('Could not import OmemoState')
    raise

from db import get_connection
from log import get_logger

# TODO: Use proper Singleton Pattern
OMEMO_CURRENT_STATE = None

logger = get_logger()


def get_omemo_state(account):
    global OMEMO_CURRENT_STATE

    if not OMEMO_CURRENT_STATE:
        logger.info('Initializing OMEMO state.')
        connection = get_connection(account)
        OMEMO_CURRENT_STATE = OmemoState(account, connection)

    return OMEMO_CURRENT_STATE