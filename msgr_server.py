from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import json
import sys

from common.utils import get_message, send_message
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                              RESPONSE, ERROR, RESPONDEFAULT_IP_ADDRESSSE,
                              DEFAULT_PORT, MAX_CONNECTIONS)


def check_greeting_and_form_response(message):
    '''
    Обработчик сообщений от клиентов, принимает словарь -
    сообщение от клинта, проверяет корректность,
    возвращает словарь-ответ для клиента

    @param message: dict  received message
    @return: dict  message for sending to client
    '''
    if ACTION in message and message[ACTION] == PRESENCE and TIME in message \
            and USER in message and message[USER][ACCOUNT_NAME] == 'Guest':
        return {RESPONSE: 200}
    return {
        RESPONDEFAULT_IP_ADDRESSSE: 400,
        ERROR: 'Bad Request'
    }


def main():
    '''
    Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    Сначала обрабатываем порт:
    server.py -p 8888 -a 127.0.0.1
    :return:
    '''

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = DEFAULT_PORT
        if listen_port < 1024 or listen_port > 65535:
            raise ValueError
    except IndexError:
        print('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)
    except ValueError:
        print(
            'В качастве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    # Затем загружаем какой адрес слушать

    try:
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
        else:
            listen_address = ''

    except IndexError:
        print(
            'После параметра \'a\'- необходимо указать адрес, который будет слушать сервер.')
        sys.exit(1)

    SERV_SOCK = socket(AF_INET, SOCK_STREAM)
    SERV_SOCK.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    SERV_SOCK.bind((listen_address, listen_port))
    SERV_SOCK.listen(MAX_CONNECTIONS)

    try:
        while True:
            CLIENT_SOCK, ADDR = SERV_SOCK.accept()
            try:
                DATA = get_message(CLIENT_SOCK)
                print(DATA)
                SOMERESP = check_greeting_and_form_response(DATA)
                print(SOMERESP)
                send_message(CLIENT_SOCK, SOMERESP)
                CLIENT_SOCK.close()
            except (ValueError, json.JSONDecodeError):
                print("Принято некорректное сообщение от клиента.")
                CLIENT_SOCK.close()
    finally:
        SERV_SOCK.close()


if __name__ == '__main__':
    main()
