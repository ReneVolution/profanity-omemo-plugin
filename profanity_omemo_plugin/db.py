import os
from log import get_plugin_logger
from constants import XDG_DATA_HOME
log = get_plugin_logger()

try:
    import sqlite3
except ImportError:
    log.error('Could not import sqlite3')
    raise


def get_connection(user):
    """ Open in memory sqlite db and create a table. """
    db_path = _get_db_path(user)
    db_root = os.path.dirname(db_path)
    if not os.path.isdir(db_root):
        os.makedirs(db_root)
    log.info('Using database path {}'.format(db_path))
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


def _get_local_data_path(user):
    if not user:
        raise RuntimeError('User cannot be None.')

    safe_username = user.replace('@', '_at_')

    return os.path.join(XDG_DATA_HOME, 'profanity', 'omemo', safe_username)


def _get_db_path(user):
    return os.path.join(_get_local_data_path(user), 'omemo.db')
