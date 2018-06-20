import requests
from requests.auth import HTTPBasicAuth

URL = 'https://onetimesecret.com'


class OneTimeCli(object):

    def create_link(self, secret):
        response = requests.post(
            '{}/api/v1/share'.format(URL),
            data={'secret': secret, 'ttl': 900},  # live for 15 minutes
            auth=HTTPBasicAuth(self.user, self.key))

        return '{}/secret/{}'.format(URL, response.json()['secret_key'])

    def __init__(self, user, key):
        self.user = user
        self.key = key
