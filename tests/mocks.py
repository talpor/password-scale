from mock import Mock
import decorator
import requests


class RequestsMock(object):
    def get_public_key(self, func):
        class MockRequest(object):
            status_code = 200
            text = 'public_key_111111111111'

        def func_wrapper(func, *args, **kwargs):
            requests.get = Mock(return_value=MockRequest())
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
