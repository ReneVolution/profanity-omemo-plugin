import os

HOME = os.path.expanduser('~')
XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.join(HOME, '.local', 'share'))

LOGGER_NAME = 'ProfOmemoLogger'
SETTINGS_GROUP = 'omemo'
OMEMO_DEFAULT_ENABLED = True

# OMEMO namespace constants
NS_OMEMO = 'eu.siacs.conversations.axolotl'
NS_DEVICE_LIST = NS_OMEMO + '.devicelist'
NS_DEVICE_LIST_NOTIFY = NS_DEVICE_LIST + '+notify'
NS_BUNDLES = NS_OMEMO + '.bundles'
