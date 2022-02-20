import os
import sys
import unittest

sys.path.append(os.path.join(os.getcwd(), '..'))
from msgr_server import check_greeting_and_form_response
from common.variables import (ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME,
                               RESPONSE, ERROR, RESPONDEFAULT_IP_ADDRESSSE)


class TestServer(unittest.TestCase):
    def setUp(self):
        self.positive = {RESPONSE: 200}
        self.negative = {RESPONDEFAULT_IP_ADDRESSSE: 400, ERROR: 'Bad Request'}

    def test_forming_positive_response(self):
        self.assertEqual(check_greeting_and_form_response(
        {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.positive)

    def test_no_action(self):
        self.assertEqual(check_greeting_and_form_response(
        {TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.negative)

    def test_different_action(self):
        self.assertEqual(check_greeting_and_form_response(
        {ACTION: 'absence', TIME: 1.1, USER: {ACCOUNT_NAME: 'Guest'}}), self.negative)

    def test_no_time(self):
        self.assertEqual(check_greeting_and_form_response(
        {ACTION: PRESENCE, USER: {ACCOUNT_NAME: 'Guest'}}), self.negative)

    def test_no_user(self):
        self.assertEqual(check_greeting_and_form_response({ACTION: PRESENCE, TIME: 1.1}), self.negative)

    def test_different_user(self):
        self.assertEqual(check_greeting_and_form_response(
        {ACTION: PRESENCE, TIME: 1.1, USER: {ACCOUNT_NAME: 'Host'}}), self.negative)
