import logging
from logging.handlers import TimedRotatingFileHandler
import os


PATH = os.path.dirname(os.path.abspath(__file__))
logfile = os.path.join(PATH, 'server.log')
FORMAT = logging.Formatter('%(asctime)s - %(levelname)-8s - %(module)s - %(message)s')

server_handler = TimedRotatingFileHandler(logfile, when='D', interval=1, encoding='utf-8')
server_handler.setFormatter(FORMAT)
server_handler.setLevel(logging.INFO)

logger = logging.getLogger('messenger.server')
logger.addHandler(server_handler)
logger.setLevel(logging.INFO)

if __name__ == '__main__':
    logger.info('Server logger test passed!')
