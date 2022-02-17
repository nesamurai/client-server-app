import json
import sys
import time
from socket import socket, AF_INET, SOCK_STREAM

from common.utils import get_message, send_message
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                               RESPONSE, ERROR, DEFAULT_PORT, DEFAULT_IP_ADDRESS)


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
    return out


def decipher_server_msg(message):
    '''
    Функция разбирает ответ сервера
    @param message: dict  received message
    @return: success or error code
    '''
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        return f'400 : {message[ERROR]}'
    raise ValueError


def main():
    '''Загружаем параметы коммандной строки'''
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
    except ValueError:
        print('В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    CLIENT_SOCK = socket(AF_INET, SOCK_STREAM)
    CLIENT_SOCK.connect((server_address, server_port))
    MSG = create_presence()
    print(MSG)
    send_message(CLIENT_SOCK, MSG)
    try:
        received_message = get_message(CLIENT_SOCK)
        print(received_message)
        resp = decipher_server_msg(received_message)
        print(resp)
    except (ValueError, json.JSONDecodeError):
        print('Не удалось декодировать сообщение сервера.')
    CLIENT_SOCK.close()


if __name__ == '__main__':
    main()
