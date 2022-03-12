from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import argparse
import json
import logging
import sys
from select import select

from common.utils import get_message, send_message
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                              RESPONSE, ERROR, RESPONDEFAULT_IP_ADDRESSSE,
                              DEFAULT_PORT, MAX_CONNECTIONS, MESSAGE)
from errors import IncorrectDataRecivedError
from log import server_log_config


server_logger = logging.getLogger('messenger.server')


def check_greeting_and_form_response(message, messages_list, client):
    '''
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клиента, проверяет корректность,
    возвращает словарь-ответ для клиента

    @param message: dict  received message
    @param messages_list:
    @param client:
    @return: dict  message for sending to client
    '''
    server_logger.info(f'Разбор сообщения от клиента: {message}')
    if (ACTION in message and message[ACTION] == PRESENCE and TIME in message
    and USER in message and message[USER][ACCOUNT_NAME] == 'Guest'):
        send_message(client, {RESPONSE: 200})
        return
    elif (ACTION in message and message[ACTION] == MESSAGE and TIME in message
    and MESSAGE_TEXT in message):
        messages_list.append((message[ACCOUNT_NAME]), message[MESSAGE_TEXT])
        return
    else:
        send_message(client, {RESPONDEFAULT_IP_ADDRESSSE: 400, ERROR: 'Bad Request'})
        return


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

    SERV_SOCK = socket(AF_INET, SOCK_STREAM)
    SERV_SOCK.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    SERV_SOCK.bind((listen_address, listen_port))
    SERV_SOCK.settimeout(0.5)

    # список клиентов , очередь сообщений
    clients = []
    messages = []

    # Слушаем порт
    SERV_SOCK.listen(MAX_CONNECTIONS)

    try:
        while True:
            try:
                client, ADDR = SERV_SOCK.accept()
            except OSError as err:
                print(err.errno)
                pass
            else:
                server_logger.info(f'Установлено соединение с {ADDR}.')
                clients.append(client)

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
                        check_greeting_and_form_response(get_message(client_with_msg), messages, client_with_msg)
                    except:
                        server_logger.info(f'Клиент {client_with_msg.getpeername()} отключился от сервера.')
                        clients.remove(client_with_msg)

            if messages and send_data_lst:
                message = {
                    ACTION: MESSAGE,
                    SENDER: messages[0][0],
                    TIME: time.time(),
                    MESSAGE_TEXT: messages[0][1]
                }
                del messages[0]
                for waiting_client in send_data_lst:
                    try:
                        send_message(waiting_client, message)
                    except:
                        server_logger.info(f'Клиент {waiting_client.getpeername()} отключился от сервера.')
                        waiting_client.close()
                        clients.remove(waiting_client)

    finally:
        SERV_SOCK.close()


if __name__ == '__main__':
    main()
