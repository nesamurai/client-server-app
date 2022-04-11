import logging

from log import server_log_config
from sys import exit


server_logger = logging.getLogger('messenger.server')


class PortDescriptor:

    def __set__(self, obj, value):
        if not 1023 < value < 65536:
            server_logger.critical(f'Попытка запуска сервера с указанием неподходящего порта: {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        obj.__dict__[self.port] = value

    def __set_name__(self, obj_type, port):
        self.port = port
