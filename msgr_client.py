import argparse
import dis
import json
import logging
import sys
import threading
import time
from socket import socket, AF_INET, SOCK_STREAM

from common.utils import get_message, send_message
from common.variables import *
from decors import log
from errors import ReqFieldMissingError, ServerError, IncorrectDataRecivedError
from log import client_log_config
from metaclasses import ClientVerifier


client_logger = logging.getLogger('messenger.client')


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    def create_message(self):
        """Функция запрашивает текст сообщения и возвращает его.
        Так же завершает работу при вводе подобной комманды.
        """
        to_user = input('Введите получателя сообщения: ')
        message = input("Введите сообщение для отправки или 'exit' для завершения работы: ")
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            TIME: time.time(),
            DESTINATION: to_user,
            MESSAGE_TEXT: message
        }
        client_logger.info(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            client_logger.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            client_logger.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    def user_interactive(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                try:
                    send_message(self.sock, self.create_exit_message())
                except:
                    pass
                print('Завершение соединения.')
                client_logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def print_help(self):
        """Функция выводящая справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    def message_from_server(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:'
                          f'\n{message[MESSAGE_TEXT]}')
                    client_logger.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                f'\n{message[MESSAGE_TEXT]}')
                else:
                    client_logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                client_logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                client_logger.critical(f'Потеряно соединение с сервером.')
                break


def create_presence(account_name):
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
    client_logger.info(f"Разбор сообщения от сервера: {message}.")
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        return f'400 : {message[ERROR]}'
    raise ReqFieldMissingError(RESPONSE)


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
    parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name

    if not 1023 < server_port < 65536:
        client_logger.critical(f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
        sys.exit(1)
    return server_address, server_port, client_name


def main():
    '''Загружаем параметы коммандной строки'''
    server_address, server_port, client_name = arg_parser()

    if not client_name:
        client_name = input("Введите имя пользователя: ")
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    client_logger.info(f'Запущен клиент с параметрами: адрес сервера: {server_address}, порт: {server_port}, имя пользователя: {client_name}')

    try:
        CLIENT_SOCK = socket(AF_INET, SOCK_STREAM)
        CLIENT_SOCK.connect((server_address, server_port))
        MSG = create_presence(client_name)
        client_logger.info(f"Сформировано сообщение {MSG}.")
        send_message(CLIENT_SOCK, MSG)
        received_message = get_message(CLIENT_SOCK)
        client_logger.info(f"Получено сообщение {received_message}.")
        resp = decipher_server_msg(received_message)
        client_logger.info(f"Разобран ответ от сервера {resp}.")
    except json.JSONDecodeError:
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
        receiver = ClientReader(client_name, CLIENT_SOCK)
        receiver.daemon = True
        receiver.start()

        user_interface = ClientSender(client_name, CLIENT_SOCK)
        user_interface.daemon = True
        user_interface.start()

        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
