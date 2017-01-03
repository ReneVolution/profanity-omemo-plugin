import logging
from constants import LOGGER_NAME

PROFANITY_IS_HOST = True

try:
    import prof
except ImportError:
    PROFANITY_IS_HOST = False


class ProfLogHandler(logging.Handler):

    def __init__(self):
        super(ProfLogHandler, self).__init__()

    def emit(self, record):

        if PROFANITY_IS_HOST:
            level_fn_map = {
                10: prof.log_debug,  # DEBUG
                20: prof.log_info,  # INFO
                30: prof.log_warning,  # WARNING
                40: prof.log_error  # ERROR
            }

            try:
                msg = u'{0}: {1}'.format(record.name, record.msg)
                level_fn_map[record.levelno](msg)
            except:
                prof.log_error('Could not log last message.')

python_omemo_logger = logging.getLogger('omemo')
python_omemo_logger.setLevel(logging.DEBUG)
python_omemo_logger.addHandler(ProfLogHandler())


def get_logger():
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(ProfLogHandler())

    return logger
