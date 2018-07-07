import os
import sys
import pytest
import random
import string
from mocks import RequestsMock, PasswordScaleCMDMock

VERIFICATION_TOKEN = '111111111111111111111111'
SITE = 'https://scale.talpor.com'
SLACK_APP_ID = '1111111111.111111111111'

os.environ['BIP39'] = (
    'music always draft before scatter capital '
    'will bulk between host discover task'
)
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['DEMO_SERVER'] = 'https://11111111.talpor.com'
os.environ['SENTRY_DSN'] = ''
os.environ['SITE'] = SITE
os.environ['SLACK_APP_ID'] = SLACK_APP_ID
os.environ['SLACK_APP_SECRET'] = '11111111111111111111111111111111'
os.environ['VERIFICATION_TOKEN'] = VERIFICATION_TOKEN

sys.path.insert(0, '')
import proxy_server as server  # noqa

requests_mock = RequestsMock()


@pytest.fixture
def client_fixture():
    server.server.config['TESTING'] = True
    client = server.server.test_client()

    with server.server.app_context():
        server.db.create_all()

    yield client


class RequestData(object):

    @requests_mock.get_public_key
    def add_team(self, register=False):
        self.team_id = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=9))

        new_team = server.Team(team_id=self.team_id)
        server.db.session.add(new_team)
        server.db.session.commit()

        if register:
            if self.client is None:
                raise Exception('client is required for register')
            self.client.post('/slack/command', data={
                **vars(self),
                **{'text': 'register https://dummy-password-server.com'}
            })

    def __init__(
            self, client=None, token=VERIFICATION_TOKEN, team_id='', text='',
            add_team=False, add_team_server=False):
        self.client = client
        self.token = token
        self.channel_id = 'QAZWSX'
        self.team_domain = ''
        self.team_id = team_id
        self.text = text
        if add_team:
            self.add_team(register=add_team_server)
