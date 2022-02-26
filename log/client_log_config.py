import logging
import os


PATH = os.path.dirname(os.path.abspath(__file__))
logfile = os.path.join(PATH, 'client.log')
FORMAT = logging.Formatter('%(asctime)s - %(levelname)-8s - %(module)s - %(message)s')

client_handler = logging.FileHandler(logfile, encoding='utf-8')
client_handler.setFormatter(FORMAT)
client_handler.setLevel(logging.INFO)

logger = logging.getLogger('messenger.client')
logger.addHandler(client_handler)
logger.setLevel(logging.INFO)

if __name__ == '__main__':
    logger.info('Client logger test passed!')
