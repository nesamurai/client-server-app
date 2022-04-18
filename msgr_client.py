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
from client_database import ClientDatabase


client_logger = logging.getLogger('messenger.client')

# Объект блокировки сокета и работы с базой данных
sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    def create_message(self):
        to_user = input('Введите получателя сообщения: ')
        message = input("Введите сообщение для отправки или 'exit' для завершения работы: ")
        # Проверим, что получатель существует
        with database_lock:
            if not self.database.check_user(to_user):
                logger.error(f'Попытка отправить сообщение '
                             f'незарегистрированому получателю: {to_user}')
                return
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.account_name,
            TIME: time.time(),
            DESTINATION: to_user,
            MESSAGE_TEXT: message
        }
        client_logger.info(f'Сформирован словарь сообщения: {message_dict}')
        # Сохраняем сообщения для истории
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock:
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
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message())
                    except:
                        pass
                    print('Завершение соединения.')
                    client_logger.info('Завершение работы по команде пользователя.')
                    # Задержка неоходима, чтобы успело уйти сообщение о выходе
                    time.sleep(0.5)
                    break
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts()

            # история сообщений.
            elif command == 'history':
                self.print_history()
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def print_help(self):
        """Функция выводящая справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')

    # Функция выводящяя историю сообщений
    def print_history(self):
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} '
                          f'от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} '
                          f'от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]},'
                          f' пользователю {message[1]} '
                          f'от {message[3]}\n{message[2]}')

    # Функция изменеия контактов
    def edit_contacts(self):
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    client_logger.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except ServerError:
                        client_logger.error('Не удалось отправить информацию на сервер.')


class ClientReader(threading.Thread, metaclass=ClientVerifier):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)
                    # Принято некорректное сообщение
                except IncorrectDataRecivedError:
                    client_logger.error(f'Не удалось декодировать полученное сообщение.')
                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        client_logger.critical(f'Потеряно соединение с сервером.')
                        break
                # Проблемы с соединением
                except (ConnectionError,
                        ConnectionAbortedError,
                        ConnectionResetError,
                        json.JSONDecodeError):
                    client_logger.critical(f'Потеряно соединение с сервером.')
                    break
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if ACTION in message and message[ACTION] == MESSAGE \
                            and SENDER in message \
                            and DESTINATION in message \
                            and MESSAGE_TEXT in message \
                            and message[DESTINATION] == self.account_name:
                        print(f'\n Получено сообщение от пользователя '
                              f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER],
                                                           self.account_name,
                                                           message[MESSAGE_TEXT])
                            except Exception as e:
                                print(e)
                                client_logger.error('Ошибка взаимодействия с базой данных')

                        client_logger.info(f'Получено сообщение от пользователя '
                                    f'{message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        client_logger.error(f'Получено некорректное сообщение с сервера: {message}')


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


# Функция запрос контакт листа
def contacts_list_request(sock, name):
    client_logger.debug(f'Запрос контакт листа для пользователя {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        USER: name
    }
    client_logger.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    client_logger.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция добавления пользователя в контакт лист
def add_contact(sock, username, contact):
    client_logger.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка создания контакта')
    print('Удачное создание контакта.')


# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    client_logger.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        raise ServerError


# Функция удаления пользователя из списка контактов
def remove_contact(sock, username, contact):
    client_logger.debug(f'Создание контакта {contact}')
    req = {
        ACTION: REMOVE_CONTACT,
        TIME: time.time(),
        USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        raise ServerError('Ошибка удаления клиента')
    print('Удачное удаление')


# Функция инициализатор базы данных.
# Запускается при запуске, загружает данные в базу с сервера.
def database_load(sock, database, username):
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except ServerError:
        client_logger.error('Ошибка запроса списка известных пользователей.')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except ServerError:
        client_logger.error('Ошибка запроса списка контактов.')
    else:
        for contact in contacts_list:
            database.add_contact(contact)


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
        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)

        user_interface = ClientSender(client_name, CLIENT_SOCK, database)
        user_interface.daemon = True
        user_interface.start()

        receiver = ClientReader(client_name, CLIENT_SOCK, database)
        receiver.daemon = True
        receiver.start()

        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
