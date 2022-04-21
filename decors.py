import logging
import sys

from log import client_log_config, server_log_config


if sys.argv[0].find('messenger.client') == -1:
    logger = logging.getLogger('messenger.server')
else:
    logger = logging.getLogger('messenger.client')


def log(func_to_log):
    def log_saver(*args , **kwargs):
        logger.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args} , {kwargs}. Вызов из модуля {func_to_log.__module__}')
        ret = func_to_log(*args , **kwargs)
        return ret
    return log_saver
