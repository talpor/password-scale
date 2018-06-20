from contrib.crypto import decrypt

import requests
import random
import string

ERRMSG = 'Communication problem with the remote server'


class PasswordScaleError(Exception):
    def __init__(self, message):
        self.message = message


class PasswordScaleCMD(object):

    def register(self, team):
        try:
            response = requests.get(team.api('public_key'))
        except requests.exceptions.ConnectionError:
            raise PasswordScaleError('Timeout: {}'.format(ERRMSG))

        if response.status_code == requests.codes.ok:
            team.public_key = response.text
        else:
            raise PasswordScaleError(
                'Error {}: {}'.format(response.status_code, ERRMSG))

        self.db.session.add(team)
        self.db.session.commit()

    def list(self, team, channel):
        try:
            response = requests.post(team.api('list/{}'.format(channel)))
        except requests.exceptions.ConnectionError:
            raise PasswordScaleError('Timeout: {}'.format(ERRMSG))

        msg = decrypt(response.text, self.private_key)
        if msg == b'':
            return '<empty>'
        elif msg is None:
            raise PasswordScaleError('Decryption error')

        return msg.decode('utf-8').replace('{}/'.format(channel), '├── ')

    def generate_insert_token(self, team, channel, app):
        token = ''.join(random.SystemRandom().choice(
            string.ascii_uppercase + string.digits) for _ in range(6))

        self.cache.set(token, {
            'path': '{}/{}'.format(channel, app),
            'team_id': team.id,
            'url': team.api('insert')
        }, expire=900)  # expires in 15 minutes

        return token

    def insert(self, token, secret):
        path = self.cache[token]['path']
        url = self.cache[token]['url']
        response = requests.post(url, data={'path': path, 'secret': secret})

        if response.status_code != requests.codes.ok:
            raise PasswordScaleError(
                'Error {}: {}'.format(response.status_code, ERRMSG))
        del self.cache[token]

    def remove(self, team, channel, app):
        response = requests.post(
            team.api('remove'),
            data={'channel': channel, 'app': app})

        if response.status_code != requests.codes.ok:
            raise PasswordScaleError(
                'Error {}: {}'.format(response.status_code, ERRMSG))

    def show(self, team, channel, app):
        response = requests.post(
            team.api('onetime_link'),
            data={'secret': '{}/{}'.format(channel, app)})

        if response.status_code == requests.codes.ok:
            return decrypt(
                response.text, self.private_key).decode('utf-8')
        elif response.status_code == requests.codes.not_found:
            return None

        raise PasswordScaleError('Unexpected error')

    def __init__(self, db, cache, private_key):
        self.db = db
        self.cache = cache
        self.private_key = private_key
