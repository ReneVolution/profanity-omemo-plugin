import os

HOME = os.path.expanduser('~')
XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.join(HOME, '.local', 'share'))

LOGGER_NAME = 'ProfOmemoLogger'
SETTINGS_GROUP = 'omemo'
