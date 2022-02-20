import json
import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from common.utils import get_message, send_message
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                               RESPONSE, ERROR, RESPONDEFAULT_IP_ADDRESSSE,
                               ENCODING)


class TestSocket:
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, msg_to_send):
        json_test_msg = json.dumps(self.test_dict)
        self.encoded_message = json_test_msg.encode(ENCODING)
        self.received_message = msg_to_send

    def recv(self, max_len):
        json_test_msg = json.dumps(self.test_dict)
        return json_test_msg.encode(ENCODING)


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.dict_send = {ACTION: PRESENCE, TIME: 11.11, USER: {ACCOUNT_NAME: 'Guest_test'}}
        self.dict_recv_ok = {RESPONSE: 200}
        self.dict_recv_err = {RESPONDEFAULT_IP_ADDRESSSE: 400, ERROR: 'Bad Request'}

    def test_right_send_msg(self):
        test_socket = TestSocket(self.dict_send)
        send_message(test_socket, self.dict_send)
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)

    def test_wrong_send_msg(self):
        test_socket = TestSocket(self.dict_send)
        send_message(test_socket, self.dict_send)
        self.assertRaises(TypeError, send_message, test_socket, "wrong_dictionary")

    def test_right_get_msg(self):
        test_sock_ok = TestSocket(self.dict_recv_ok)
        self.assertEqual(get_message(test_sock_ok), self.dict_recv_ok)

    def test_wrong_get_msg(self):
        test_sock_err = TestSocket(self.dict_recv_err)
        self.assertEqual(get_message(test_sock_err), self.dict_recv_err)
