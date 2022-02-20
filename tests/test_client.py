import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from msgr_client import create_presence, decipher_server_msg
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                               RESPONSE, ERROR, RESPONDEFAULT_IP_ADDRESSSE)


class TestClient(unittest.TestCase):
    def test_creation_presence(self):
        presence = create_presence()
        presence[TIME] = 1.1
        self.assertEqual(presence, {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}})

    def test_200(self):
        self.assertEqual(decipher_server_msg({RESPONSE: 200}), '200 : OK')

    def test_400(self):
        self.assertEqual(decipher_server_msg({
            RESPONSE: 400, ERROR: 'Bad Request'}), '400 : Bad Request')

    def test_no_response(self):
        self.assertRaises(ValueError, decipher_server_msg, {ERROR: 'Bad Request'})
