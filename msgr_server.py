from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import argparse
import json
import logging
import sys
from select import select

from common.utils import get_message, send_message
from common.variables import (DEFAULT_PORT, MAX_CONNECTIONS, ACTION, TIME, USER,
ACCOUNT_NAME, SENDER, PRESENCE, ERROR, MESSAGE, MESSAGE_TEXT, RESPONSE_400,
DESTINATION, RESPONSE_200, EXIT)
from errors import IncorrectDataRecivedError
from log import server_log_config


server_logger = logging.getLogger('messenger.server')


def check_greeting_and_form_response(message, messages_list, client, clients, names):
    '''
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клиента, проверяет корректность,
    возвращает словарь-ответ для клиента

    @param message: dict  received message
    @param messages_list:
    @param client:
    @param clients:
    @param names:
    @return: dict  message for sending to client
    '''
    server_logger.info(f'Разбор сообщения от клиента: {message}')
    if ACTION in message and message[ACTION] == PRESENCE and \
            TIME in message and USER in message:
        # Если такой пользователь ещё не зарегистрирован,
        # регистрируем, иначе отправляем ответ и завершаем соединение.
        if message[USER][ACCOUNT_NAME] not in names.keys():
            names[message[USER][ACCOUNT_NAME]] = client
            send_message(client, RESPONSE_200)
        else:
            response = RESPONSE_400
            response[ERROR] = 'Имя пользователя уже занято.'
            send_message(client, response)
            clients.remove(client)
            client.close()
        return
    # Если это сообщение, то добавляем его в очередь сообщений.
    # Ответ не требуется.
    elif ACTION in message and message[ACTION] == MESSAGE and \
            DESTINATION in message and TIME in message \
            and SENDER in message and MESSAGE_TEXT in message:
        messages_list.append(message)
        return
    # Если клиент выходит
    elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
        clients.remove(names[message[ACCOUNT_NAME]])
        names[message[ACCOUNT_NAME]].close()
        del names[message[ACCOUNT_NAME]]
        return
    # Иначе отдаём Bad request
    else:
        response = RESPONSE_400
        response[ERROR] = 'Запрос некорректен.'
        send_message(client, response)
        return


def process_message(message, names, listen_socks):
    """
    Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
    список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
    :param message:
    :param names:
    :param listen_socks:
    :return:
    """
    if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
        send_message(names[message[DESTINATION]], message)
        server_logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                    f'от пользователя {message[SENDER]}.')
    elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
        raise ConnectionError
    else:
        server_logger.error(
            f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
            f'отправка сообщения невозможна.')


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    if not 1023 < listen_port < 65536:
        server_logger.critical(f'Попытка запуска сервера с указанием неподходящего порта: {listen_port}. Допустимы адреса с 1024 до 65535.')
        sys.exit(1)
    return listen_address, listen_port


def main():
    '''
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    :return:
    '''
    listen_address, listen_port = arg_parser()

    server_logger.info(f'''Запущен сервер, порт для подключений: {listen_port},
        адрес с которого принимаются подключения: {listen_address}.
        Если адрес не указан, принимаются соединения с любых адресов.''')

    with socket(AF_INET, SOCK_STREAM) as SERV_SOCK:
        SERV_SOCK.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        SERV_SOCK.bind((listen_address, listen_port))
        SERV_SOCK.settimeout(0.5)

        # список клиентов , очередь сообщений
        clients = []
        messages = []
        names = dict()

        # Слушаем порт
        SERV_SOCK.listen(MAX_CONNECTIONS)

        # try:
        while True:
            try:
                client, ADDR = SERV_SOCK.accept()
            except OSError as err:
                print(err.errno)
                pass
            else:
                server_logger.info(f'Установлено соединение с {ADDR}.')
                clients.append(client)
            finally:
                recv_data_lst = []
                send_data_lst = []
                err_lst = []
                # Проверяем на наличие ждущих клиентов
                try:
                    if clients:
                        recv_data_lst, send_data_lst, err_lst = select(clients, clients, [], 0)
                except OSError:
                    pass

                if recv_data_lst:
                    for client_with_msg in recv_data_lst:
                        try:
                            check_greeting_and_form_response(get_message(client_with_msg), messages, client_with_msg, clients, names)
                        except:
                            server_logger.info(f'Клиент {client_with_msg.getpeername()} отключился от сервера.')
                            clients.remove(client_with_msg)

                if messages and send_data_lst:
                    for i in messages:
                        try:
                            process_message(i, names, send_data_lst)
                        except Exception:
                            server_logger.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                            clients.remove(names[i[DESTINATION]])
                            del names[i[DESTINATION]]
                    messages.clear()


if __name__ == '__main__':
    main()
