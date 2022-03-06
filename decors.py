from datetime import datetime
import logging
import sys
import traceback

from log import client_log_config, server_log_config


if sys.argv[0].find('msgr_client.py') == -1:
    common_logger = logging.getLogger('messenger.server')
else:
    common_logger = logging.getLogger('messenger.client')


def log(f):
    def wrapper(*args, **kwargs):
        response = f(*args, **kwargs)
        common_logger.info(f"""
        Вызвана функция {f.__name__} со следующими параметрами args={args}, kwargs={kwargs} из модуля {f.__module__}.\r
        <{datetime.now()}> Функция {f} вызвана из функции {traceback.format_stack()[0].strip().split()[-1]}.
        """)

        return response
    return wrapper
