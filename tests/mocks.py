from mock import Mock
import base64
import decorator
import requests


class MockRequest(object):
    def __init__(self, status_code, text='', jsonc={}):
        self.status_code = status_code
        self.text = text
        self.jsonc = jsonc

    def json(self):
        return self.jsonc


class RequestsMock(object):
    def get_public_key(self, func):

        def func_wrapper(func, *args, **kwargs):
            requests.get = Mock(return_value=MockRequest(
                200, 'public_key_111111111111'
            ))
            return func(*args, **kwargs)

        return decorator.decorator(func_wrapper, func)

    def get_oauth_access_url(self, func):

        def func_wrapper(func, *args, **kwargs):
            requests.get = Mock(return_value=MockRequest(
                200, jsonc={
                    'ok': True,
                    'team_id': 1
                })
            )
            return func(*args, **kwargs)

        return decorator.decorator(func_wrapper, func)


class PasswordScaleCMDMock(object):
    secrets = ['aws', 'sendgrid']
    token = 'QAZWSX'

    def _generate_cmd_decorator(self, func, cmd, return_value):
        def func_wrapper(func, *args, **kwargs):
            self.app.cmd.__setattr__(cmd, Mock(return_value=return_value))
            return func(*args, **kwargs)
        return decorator.decorator(func_wrapper, func)

    def generate_insert_token(self, func):
        return self._generate_cmd_decorator(
            func, 'generate_insert_token', 'QAZWSX')

    def insert(self, func):
        return self._generate_cmd_decorator(func, 'insert', None)

    def empty_list(self, func):
        return self._generate_cmd_decorator(func, 'list', '')

    def full_list(self, func):
        return self._generate_cmd_decorator(
            func, 'list', '\n├─ '.join([''] + self.secrets)[1:])

    def remove_success(self, func):
        return self._generate_cmd_decorator(func, 'remove', True)

    def remove_failure(self, func):
        return self._generate_cmd_decorator(func, 'remove', False)

    def show_success(self, func):
        return self._generate_cmd_decorator(
            func, 'show', 'https://link-to-the-secret.com')

    def show_failure(self, func):
        return self._generate_cmd_decorator(func, 'show', None)

    def __init__(self, app):
        self.app = app


class CacheMock(object):
    token = 'VALID'
    invalid_token = 'INVLD'

    def has_token(self, func):
        def func_wrapper(func, *args, **kwargs):
            self.app.cache = dict()
            self.app.cache[self.token] = {
                'path': '',
                'team_id': 1
            }
            return func(*args, **kwargs)
        return decorator.decorator(func_wrapper, func)

    def __init__(self, app):
        self.app = app


class CryptoMock(object):

    def encrypt(self, func):
        def func_wrapper(func, *args, **kwargs):
            self.app.encrypt = Mock(
                return_value=base64.b64encode(bytes('ok', 'utf-8')))
            return func(*args, **kwargs)

        return decorator.decorator(func_wrapper, func)

    def __init__(self, app):
        self.app = app
