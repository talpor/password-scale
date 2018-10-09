import os
import sys

from mocks import CacheMock, RequestsMock, PasswordScaleCMDMock, CryptoMock
from urllib.parse import urlencode
from fixtures import (
    client_fixture, RequestData, VERIFICATION_TOKEN, SITE, SLACK_CLIENT_ID
)

sys.path.insert(0, os.path.join(sys.path[0], '..', 'proxy_server'))  # noqa
import insert
import slack_command
from server import public_key

cache_mock = CacheMock(insert)
crypto_mock = CryptoMock(insert)
password_scale_cmd_mock = PasswordScaleCMDMock(slack_command)
requests_mock = RequestsMock()

client = client_fixture


def test__public_key_endpoint(client):
    rv = client.get('/public_key')
    assert rv.data == public_key


def test__api_endpoint__require_post(client):
    rv = client.get('/slack/command')
    assert rv.status_code == 405


def test__api_endpoint__required_data(client):
    required_fields = ['text', 'team_id', 'team_domain', 'channel_id']
    for field in required_fields:
        data = vars(RequestData())
        del data[field]
        rv = client.post('/slack/command', data=data)
        assert rv.status_code == 400


def test__api_endpoint__require_valid_verification_token(client):
    rv = client.post('/slack/command', data=vars(RequestData(token='')))
    assert rv.status_code == 404

    valid_data = vars(RequestData())
    assert valid_data['token'] == VERIFICATION_TOKEN
    rv = client.post('/slack/command', data=valid_data)
    assert rv.status_code == 200


def test__api_endpoint__require_valid_team(client):
    rv = client.post('/slack/command', data=vars(RequestData()))
    assert b'You are not registered in our proxy server' in rv.data


def test__api_endpoint__require_password_server(client):
    data = RequestData(add_team=True)
    rv = client.post('/slack/command', data=vars(data))
    assert b'team does not have a password server registered' in rv.data


@requests_mock.get_public_key
def test__api_endpoint__register(client):
    data = RequestData(text='register https://my-password-server.com',
                       add_team=True)

    rv = client.post('/slack/command', data=vars(data))
    assert b'team successfully registered' in rv.data


@requests_mock.get_public_key
def test__api_endpoint__register_multiple_times(client):
    data1 = RequestData(text='register https://my-password-server.com',
                        add_team=True)
    data2 = RequestData(text='register https://my-new-password-server.com')
    data2.team_id = data1.team_id

    client.post('/slack/command', data=vars(data1))
    rv = client.post('/slack/command', data=vars(data2))

    assert b'This team is already registered, you want to replace' in rv.data


def test__api_endpoint__register_using_bad_url(client):
    data1 = RequestData(text='register this-is-not-an-url', add_team=True)
    data2 = RequestData(text='register url-without-protocol.io', add_team=True)

    rv = client.post('/slack/command', data=vars(data1))
    assert b'Invalid URL format' in rv.data

    rv = client.post('/slack/command', data=vars(data2))
    assert b'Invalid URL format' in rv.data


def test__api_endpoint__help(client):
    data = RequestData(text='help', add_team=True)
    rv = client.post('/slack/command', data=vars(data))
    assert b'Usage:' in rv.data


@password_scale_cmd_mock.full_list
def test__api_endpoint__list(client):
    data = RequestData(client, add_team=True, add_team_server=True)

    for command in ['', 'list']:
        data.text = command

        rv = client.post('/slack/command', data=vars(data))
        assert bytes('Password Store', 'utf-8') in rv.data
        for secret in password_scale_cmd_mock.secrets:
            assert bytes(secret, 'utf-8') in rv.data


@password_scale_cmd_mock.empty_list
def test__api_endpoint__list_empty_bucket(client):
    data = RequestData(client, add_team=True, add_team_server=True)

    for command in ['', 'list']:
        data.text = command

        rv = client.post('/slack/command', data=vars(data))
        assert b'You have not passwords created for this channel' in rv.data


@password_scale_cmd_mock.generate_insert_token
def test__api_endpoint__insert(client):
    data = RequestData(client, text='insert secret',
                       add_team=True, add_team_server=True)

    rv = client.post('/slack/command', data=vars(data))
    assert b'Adding password' in rv.data
    assert bytes('{}/insert/{}'.format(
        SITE, password_scale_cmd_mock.token), 'utf-8') in rv.data


@password_scale_cmd_mock.remove_success
def test__api_endpoint__remove_success(client):
    secret = password_scale_cmd_mock.secrets[0]

    data = RequestData(client, text='remove {}'.format(secret),
                       add_team=True, add_team_server=True)

    rv = client.post('/slack/command', data=vars(data))
    assert bytes('the password *{}* is unreachable'.format(
        secret), 'utf-8') in rv.data


@password_scale_cmd_mock.remove_failure
def test__api_endpoint__remove_failure(client):
    secret = password_scale_cmd_mock.secrets[0]

    data = RequestData(client, text='remove {}'.format(secret),
                       add_team=True, add_team_server=True)

    rv = client.post('/slack/command', data=vars(data))
    assert bytes('this secret is not in your repository'.format(
        secret), 'utf-8') in rv.data


@password_scale_cmd_mock.show_success
def test__api_endpoint__show_success(client):
    secret = password_scale_cmd_mock.secrets[0]
    data = RequestData(client, add_team=True, add_team_server=True)

    for command in ['', 'show ']:
        data.text = '{}{}'.format(command, secret)
        rv = client.post('/slack/command', data=vars(data))
        assert bytes('Password for *{}*'.format(secret), 'utf-8') in rv.data
        assert bytes('secret will be valid for 15 minutes', 'utf-8') in rv.data


@password_scale_cmd_mock.show_failure
def test__api_endpoint__show_failure(client):
    secret = 'not-found-secret'
    data = RequestData(client, add_team=True, add_team_server=True)

    for command in ['', 'show ']:
        data.text = '{}{}'.format(command, secret)
        rv = client.post('/slack/command', data=vars(data))
        assert bytes('*{}* is not in the password store.'.format(secret),
                     'utf-8') in rv.data


@cache_mock.has_token
def test__insert_get__require_valid_token(client):
    rv = client.get('/insert/{}'.format(cache_mock.invalid_token))
    assert rv.status_code == 404

    rv = client.get('/insert/{}'.format(cache_mock.token))
    assert rv.status_code == 200


@cache_mock.has_token
def test__insert_get__render_editor(client):
    rv = client.get('/insert/{}'.format(cache_mock.token))
    assert bytes('<div id="Insert"', 'utf-8') in rv.data
    assert bytes('Paste the password or secret', 'utf-8') in rv.data


@cache_mock.has_token
@crypto_mock.encrypt
@password_scale_cmd_mock.insert
def test__insert_post__require_valid_token(client):
    rv = client.post('/insert/{}'.format(cache_mock.invalid_token))
    assert rv.status_code == 400

    rv = client.post('/insert/{}'.format(cache_mock.token), data={
        'secret': 'secret'
    })
    assert rv.status_code == 200


@cache_mock.has_token
@crypto_mock.encrypt
@password_scale_cmd_mock.insert
def test__insert_post__show_success_message(client):
    rv = client.post('/insert/{}'.format(cache_mock.token), data={
        'secret': 'secret'
    })
    assert bytes('Your secret was securely stored!', 'utf-8') in rv.data


@requests_mock.get_oauth_access_url
def test__oauth_endpoint__require_get(client):
    rv = client.post('/slack/oauth')
    assert rv.status_code == 405

    rv = client.get('/slack/oauth?code=12345')
    assert rv.status_code == 200


@requests_mock.get_oauth_access_url
def test__oauth_endpoint__require_code(client):
    rv = client.get('/slack/oauth')
    assert rv.status_code == 400


@requests_mock.get_oauth_access_url
def test__oauth_endpoint__success_message(client):
    rv = client.get('/slack/oauth?code=12345')
    assert bytes('application was installed successfully', 'utf-8') in rv.data


def test__landing__render(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert bytes('<title>Password Scale', 'utf-8') in rv.data


def test__landing__deny_post(client):
    rv = client.post('/')
    assert rv.status_code == 405


def test__landing__show_add_to_slack_button(client):
    rv = client.get('/')
    assert bytes('https://slack.com/oauth/authorize?{}'.format(urlencode({
            'client_id': SLACK_CLIENT_ID
        })), 'utf-8') in rv.data


def test__privacy__render(client):
    rv = client.get('/privacy')
    assert rv.status_code == 200
    assert bytes('Privacy Policy', 'utf-8') in rv.data


def test__privacy__deny_post(client):
    rv = client.post('/privacy')
    assert rv.status_code == 405


def test__not_found__render(client):
    rv = client.post('/404')
    assert rv.status_code == 404
    assert bytes('<h1>404</h1>', 'utf-8') in rv.data
