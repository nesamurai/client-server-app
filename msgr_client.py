import argparse
import json
import logging
import sys
import time
from socket import socket, AF_INET, SOCK_STREAM

from common.utils import get_message, send_message
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                               RESPONSE, ERROR, DEFAULT_PORT, DEFAULT_IP_ADDRESS,
                               MESSAGE, MESSAGE_TEXT)
from errors import ReqFieldMissingError, ServerError
from log import client_log_config


client_logger = logging.getLogger('messenger.client')

def create_presence(account_name='Guest'):
    '''
    Функция генерирует запрос о присутствии клиента
    @param account_name: user name
    @return: dict for sending
    '''
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        USER: {
            ACCOUNT_NAME: account_name
        }
    }
    client_logger.info(f"Сформировано {PRESENCE} сообщение для пользователя {account_name}.")
    return out


def decipher_server_msg(message):
    '''
    Функция разбирает ответ сервера
    @param message: dict  received message
    @return: success or error code
    '''
    client_logger.info(f"Разбор сообщения от сервера: {message}.")
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        return f'400 : {message[ERROR]}'
    raise ReqFieldMissingError(RESPONSE)


def main():
    '''Загружаем параметы коммандной строки'''
    server_address, server_port, client_mode = arg_parser()

    client_logger.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, порт: {server_port}, режим работы: {client_mode}')

    try:
        CLIENT_SOCK = socket(AF_INET, SOCK_STREAM)
        CLIENT_SOCK.connect((server_address, server_port))
        MSG = create_presence()
        client_logger.info(f"Сформировано сообщение {MSG}.")
        send_message(CLIENT_SOCK, MSG)
        received_message = get_message(CLIENT_SOCK)
        client_logger.info(f"Получено сообщение {received_message}.")
        resp = decipher_server_msg(received_message)
        client_logger.info(f"Разобран ответ от сервера {resp}.")
    except (ValueError, json.JSONDecodeError):
        client_logger.error('Не удалось декодировать сообщение сервера.')
        sys.exit(1)
    except ServerError as error:
        client_logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except ConnectionRefusedError:
        client_logger.critical(f"Не удалось подключиться к серверу {server_address}:{server_port}.")
        sys.exit(1)
    except ReqFieldMissingError as e:
        client_logger.error(f"В ответе сервера отсутствует необходимое поле {e.missing_field}.")
        sys.exit(1)
    else:
        if client_mode == 'send':
            print('Режим работы - отправка сообщений.')
        else:
            print('Режим работы - приём сообщений.')
        while True:
            if client_mode == 'send':
                try:
                    send_message(CLIENT_SOCK, create_message(CLIENT_SOCK))
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    client_logger.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)
            elif client_mode == 'listen':
                try:
                    message_from_server(get_message(CLIENT_SOCK))
                except (ConnectionResetError, ConnectionError, ConnectionAbortedError):
                    client_logger.error(f'Соединение с сервером {server_address} было потеряно.')
                    sys.exit(1)
    CLIENT_SOCK.close()


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-m', '--mode', default='listen', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode

    if not 1023 < server_port < 65536:
        client_logger.critical(f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
        sys.exit(1)
    if client_mode not in ('listen', 'send'):
        client_logger.critical(f'Указан недопустимый режим работы {client_mode}, допустимые режимы: listen , send')
        sys.exit(1)
    return server_address, server_port, client_mode


def create_message(sock, account_name='Guest'):
    """Функция запрашивает текст сообщения и возвращает его.
    Так же завершает работу при вводе подобной комманды.
    """
    message = input("Введите сообщение для отправки или 'exit' для завершения работы: ")
    if message == 'exit':
        sock.close()
        client_logger.info('Завершение работы по команде пользователя.')
        print('Спасибо за использование нашего сервиса!')
        sys.exit(0)
    message_dict = {
        ACTION: MESSAGE,
        TIME: time.time(),
        ACCOUNT_NAME: account_name,
        MESSAGE_TEXT: message
    }
    client_logger.info(f'Сформирован словарь сообщения: {message_dict}')
    return message_dict


def message_from_server(msg):
    """
    Функция-обработчик сообщений других пользователей, поступающих с сервера
    """
    if ACTION in msg and msg[ACTION] == MESSAGE and SENDER in msg and MESSAGE_TEXT in msg:
        print(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
        client_logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
    else:
        client_logger.error(f'Получено некорректное сообщение с сервера: {message}')


if __name__ == '__main__':
    main()
