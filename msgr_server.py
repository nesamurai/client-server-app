import argparse
import json
import logging
import sys
import time
from select import select
from socket import socket, AF_INET, SOCK_STREAM

from common.utils import get_message, send_message
from common.variables import *
from decors import log
from descr_port import PortDescriptor
from errors import IncorrectDataRecivedError
from log import server_log_config
from metaclasses import ServerVerifier


server_logger = logging.getLogger('messenger.server')


@log
def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p
    return listen_address, listen_port


class Server(metaclass=ServerVerifier):
    port = PortDescriptor()

    def __init__(self, listen_address, listen_port):
        self.addr = listen_address
        self.port = listen_port

        # список клиентов, очередь сообщений
        self.clients = []
        self.messages = []
        self.names = dict()

    def init_socket(self):
        server_logger.info(f'''Запущен сервер, порт для подключений: {self.port},
            адрес с которого принимаются подключения: {self.addr}.
            Если адрес не указан, принимаются соединения с любых адресов.''')
        SERV_SOCK = socket(AF_INET, SOCK_STREAM)
        SERV_SOCK.bind((self.addr, self.port))
        SERV_SOCK.settimeout(0.5)

        # Слушаем порт
        self.sock = SERV_SOCK
        self.sock.listen(MAX_CONNECTIONS)

    def main_loop(self):
        self.init_socket()

        while True:
            try:
                client, ADDR = self.sock.accept()
            except OSError as err:
                print(err.errno)
                pass
            else:
                server_logger.info(f'Установлено соединение с {ADDR}.')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            if recv_data_lst:
                for client_with_msg in recv_data_lst:
                    try:
                        self.check_greeting_and_form_response(get_message(client_with_msg), client_with_msg)
                    except:
                        server_logger.info(f'Клиент {client_with_msg.getpeername()} отключился от сервера.')
                        self.clients.remove(client_with_msg)

            if messages and send_data_lst:
                for i in self.messages:
                    try:
                        self.process_message(i, send_data_lst)
                    except Exception:
                        server_logger.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                        self.clients.remove(self.names[i[DESTINATION]])
                        del self.names[i[DESTINATION]]
                self.messages.clear()

    def process_message(self, message, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        """
        if message[DESTINATION] in self.names and self.names[message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            server_logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                        f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            server_logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    def check_greeting_and_form_response(self, message, client):
        '''
        Обработчик сообщений от клиентов, принимает словарь -
        сообщение от клиента, проверяет корректность,
        возвращает словарь-ответ для клиента
        '''
        server_logger.info(f'Разбор сообщения от клиента: {message}')
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован,
            # регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[ACCOUNT_NAME])
            self.names[ACCOUNT_NAME].close()
            del self.names[ACCOUNT_NAME]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def main():
    '''
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    '''
    listen_address, listen_port = arg_parser()
    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()
