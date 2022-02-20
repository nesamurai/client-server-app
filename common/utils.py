import json

from common.variables import MAX_PACKAGE_LENGTH, ENCODING


def get_message(client):
    """
    Утилита приёма и декодирования сообщения
    принимает байты выдаёт словарь, если принято
    что-то другое отдаёт ошибку значения
    @param client: client socket
    @return: received message as dict
    """

    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError


def send_message(sock, message):
    """
    This function is used for sending json string
    @sock: client socket
    @message: dict  message for sending
    """
    if not isinstance(message, dict):
        raise TypeError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
